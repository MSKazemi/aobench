"""HPC Tool Catalog loader and validator.

Loads ``benchmark/configs/hpc_tool_catalog.yaml`` into a validated in-memory
representation and exposes utilities used by scorers and adapters.

Public API
----------
load_catalog(catalog_path=None) -> ToolCatalog
    Load and validate the catalog YAML.

ToolCatalog
    Validated catalog with role-filtered queries and OpenAI tool export.

generate_docs_page(catalog, role) -> str
    Render a Markdown tool-guide page for the given role (used to populate
    environment docs/ directories so agents can discover tools via
    docs.retrieve("available tools")).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

_log = logging.getLogger(__name__)

# Default catalog path relative to the project root
_DEFAULT_CATALOG = (
    Path(__file__).parent.parent.parent.parent
    / "benchmark" / "configs" / "hpc_tool_catalog.yaml"
)

# Valid BFCL difficulty tiers
_VALID_DIFFICULTIES = {"simple", "sequential", "parallel", "chained"}

# Valid ToolBench type tokens
_VALID_TYPES = {"STRING", "NUMBER", "BOOLEAN", "ARRAY"}

# All known roles (informational — not enforced here)
KNOWN_ROLES = frozenset([
    "scientific_user",
    "researcher",
    "sysadmin",
    "facility_admin",
    "system_designer",
])


# Role tier → list of roles at or above that tier
_ROLE_TIER_MAP: dict[int, list[str]] = {
    1: ["scientific_user", "researcher", "sysadmin", "facility_admin", "system_designer"],
    2: ["sysadmin", "facility_admin", "system_designer"],
    3: ["facility_admin", "system_designer"],
}

# Valid dangerous_arg condition types
_VALID_CONDITIONS = frozenset([
    "cross_user_reference",
    "cross_user_job_id",
    "node_not_in_own_jobs",
    "cluster_scope_access",
    "any_call",
])


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ExceptionEntry:
    code: str                # e.g. "PERMISSION_DENIED"
    condition: str           # human-readable: when is this raised?
    http_analogue: str = ""  # e.g. "403"


@dataclass
class DangerousArgEntry:
    arg: str                 # parameter name or "*" for any call
    condition: str           # one of _VALID_CONDITIONS
    min_role_names: list[str]  # roles allowed to use this arg pattern
    violation_code: str      # emitted in DangerousArgViolation
    description: str


@dataclass
class ParameterEntry:
    name: str
    type: str                          # STRING | NUMBER | BOOLEAN | ARRAY
    description: str
    required: bool
    default: Any = None
    valid_values: list[Any] = field(default_factory=list)
    example: Any = None


@dataclass
class ExampleCall:
    description: str
    args: dict[str, Any]
    expected_result_keys: list[str]


@dataclass
class RoleVisibility:
    default: str                       # "all" or "restricted"
    denied_roles: list[str]
    note: str = ""


@dataclass
class ReturnShape:
    type: str
    description: str
    key_fields: list[str]


@dataclass
class MethodEntry:
    name: str
    description: str
    difficulty: str
    parameters: list[ParameterEntry]   # both required and optional, in order
    return_shape: ReturnShape
    role_visibility: RoleVisibility
    example_calls: list[ExampleCall]
    exceptions: list[ExceptionEntry] = field(default_factory=list)
    dangerous_args: list[DangerousArgEntry] = field(default_factory=list)

    @property
    def required_parameters(self) -> list[ParameterEntry]:
        return [p for p in self.parameters if p.required]

    @property
    def optional_parameters(self) -> list[ParameterEntry]:
        return [p for p in self.parameters if not p.required]

    def is_available_for_role(self, role: str) -> bool:
        return role not in self.role_visibility.denied_roles


@dataclass
class ToolEntry:
    name: str
    description: str
    class_name: str
    module: str
    methods: list[MethodEntry]

    def get_method(self, method_name: str) -> MethodEntry:
        for m in self.methods:
            if m.name == method_name:
                return m
        raise KeyError(f"Method '{method_name}' not found in tool '{self.name}'")


# ---------------------------------------------------------------------------
# Main catalog class
# ---------------------------------------------------------------------------

class ToolCatalog:
    """Validated in-memory representation of the HPC tool catalog."""

    def __init__(self, tools: list[ToolEntry], version: str, authored: str) -> None:
        self._tools: dict[str, ToolEntry] = {t.name: t for t in tools}
        self.version = version
        self.authored = authored

    @property
    def tools(self) -> list[ToolEntry]:
        return list(self._tools.values())

    def get_tool(self, tool_name: str) -> ToolEntry:
        """Raise KeyError if tool not found."""
        if tool_name not in self._tools:
            raise KeyError(f"Tool '{tool_name}' not in catalog")
        return self._tools[tool_name]

    def get_method(self, tool_name: str, method_name: str) -> MethodEntry:
        """Raise KeyError if tool or method not found."""
        return self.get_tool(tool_name).get_method(method_name)

    def get_available_methods(self, role: str) -> list[tuple[str, str]]:
        """Return list of (tool_name, method_name) pairs available for the given role."""
        result: list[tuple[str, str]] = []
        for tool in self.tools:
            for method in tool.methods:
                if method.is_available_for_role(role):
                    result.append((tool.name, method.name))
        return result

    def get_parameter_schema(self, tool_name: str, method_name: str) -> list[ParameterEntry]:
        """Return parameter definitions for argument validation."""
        return self.get_method(tool_name, method_name).parameters

    def get_dangerous_args(self, tool_name: str, method_name: str) -> list[DangerousArgEntry]:
        """Return dangerous_args for the given method. Returns [] if none declared."""
        try:
            return self.get_method(tool_name, method_name).dangerous_args
        except KeyError:
            return []

    def method_count_for_role(self, role: str) -> int:
        """Denominator for method_discovery_rate."""
        return len(self.get_available_methods(role))

    def to_openai_tools(self, role: str) -> list[dict]:
        """Render available methods for role as OpenAI-compatible tool definitions.

        Each entry: {"name": "<tool>__<method>", "description": "...", "parameters": {...}}
        This is what adapters pass to LLMs as their tool set.
        """
        result: list[dict] = []
        for tool in self.tools:
            for method in tool.methods:
                if not method.is_available_for_role(role):
                    continue
                properties: dict[str, dict] = {}
                required_names: list[str] = []
                for param in method.parameters:
                    prop: dict[str, Any] = {
                        "type": _toolbench_type_to_json_schema(param.type),
                        "description": param.description,
                    }
                    if param.valid_values:
                        prop["enum"] = param.valid_values
                    if param.default is not None:
                        prop["default"] = param.default
                    properties[param.name] = prop
                    if param.required:
                        required_names.append(param.name)
                result.append({
                    "name": f"{tool.name}__{method.name}",
                    "description": method.description.strip(),
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required_names,
                    },
                })
        return result


# ---------------------------------------------------------------------------
# Loader / validator
# ---------------------------------------------------------------------------

def load_catalog(catalog_path: str | Path | None = None) -> ToolCatalog:
    """Load and validate hpc_tool_catalog.yaml.

    Defaults to ``benchmark/configs/hpc_tool_catalog.yaml`` relative to the
    project root (resolved from this file's location).
    """
    path = Path(catalog_path) if catalog_path is not None else _DEFAULT_CATALOG
    if not path.exists():
        raise FileNotFoundError(f"Catalog not found: {path}")

    with path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)

    _validate_top_level(raw)

    tools: list[ToolEntry] = []
    for tool_raw in raw["tools"]:
        tools.append(_parse_tool(tool_raw))

    return ToolCatalog(
        tools=tools,
        version=str(raw.get("catalog_version", "unknown")),
        authored=str(raw.get("authored", "")),
    )


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _validate_top_level(raw: dict) -> None:
    if not isinstance(raw, dict):
        raise ValueError("Catalog YAML must be a mapping at the top level")
    if "tools" not in raw:
        raise ValueError("Catalog missing required key 'tools'")
    if not isinstance(raw["tools"], list):
        raise ValueError("'tools' must be a list")


def _parse_tool(raw: dict) -> ToolEntry:
    name = _require_str(raw, "name", context="tool")
    description = _require_str(raw, "description", context=f"tool '{name}'")
    class_name = _require_str(raw, "class", context=f"tool '{name}'")
    module = _require_str(raw, "module", context=f"tool '{name}'")
    methods_raw = raw.get("methods", [])
    if not isinstance(methods_raw, list):
        raise ValueError(f"Tool '{name}': 'methods' must be a list")
    methods = [_parse_method(m, tool_name=name) for m in methods_raw]
    return ToolEntry(
        name=name,
        description=description.strip(),
        class_name=class_name,
        module=module,
        methods=methods,
    )


def _parse_method(raw: dict, tool_name: str) -> MethodEntry:
    name = _require_str(raw, "name", context=f"method in tool '{tool_name}'")
    ctx = f"tool '{tool_name}', method '{name}'"
    description = _require_str(raw, "description", context=ctx)
    difficulty = _require_str(raw, "difficulty", context=ctx)
    if difficulty not in _VALID_DIFFICULTIES:
        raise ValueError(f"{ctx}: invalid difficulty '{difficulty}'. Must be one of {_VALID_DIFFICULTIES}")

    required_params = [
        _parse_parameter(p, required=True, ctx=ctx)
        for p in raw.get("required_parameters", []) or []
    ]
    optional_params = [
        _parse_parameter(p, required=False, ctx=ctx)
        for p in raw.get("optional_parameters", []) or []
    ]
    parameters = required_params + optional_params

    return_shape = _parse_return_shape(raw.get("return_shape", {}), ctx=ctx)
    role_visibility = _parse_role_visibility(raw.get("role_visibility", {}), ctx=ctx)
    example_calls = [
        _parse_example_call(e, ctx=ctx)
        for e in raw.get("example_calls", []) or []
    ]

    exceptions_raw = raw.get("exceptions")
    if exceptions_raw is None:
        _log.warning("%s: no 'exceptions' field — spec is incomplete", ctx)
        exceptions: list[ExceptionEntry] = []
    else:
        exceptions = [_parse_exception(e, ctx=ctx) for e in (exceptions_raw or [])]

    dangerous_args = [
        _parse_dangerous_arg(d, ctx=ctx)
        for d in raw.get("dangerous_args", []) or []
    ]

    return MethodEntry(
        name=name,
        description=description.strip(),
        difficulty=difficulty,
        parameters=parameters,
        return_shape=return_shape,
        role_visibility=role_visibility,
        example_calls=example_calls,
        exceptions=exceptions,
        dangerous_args=dangerous_args,
    )


def _parse_parameter(raw: dict, required: bool, ctx: str) -> ParameterEntry:
    name = _require_str(raw, "name", context=f"{ctx} parameter")
    type_ = _require_str(raw, "type", context=f"{ctx}, param '{name}'")
    if type_ not in _VALID_TYPES:
        raise ValueError(f"{ctx}, param '{name}': invalid type '{type_}'. Must be one of {_VALID_TYPES}")
    description = raw.get("description", "")
    return ParameterEntry(
        name=name,
        type=type_,
        description=description,
        required=required,
        default=raw.get("default"),
        valid_values=list(raw.get("valid_values", []) or []),
        example=raw.get("example"),
    )


def _parse_return_shape(raw: dict, ctx: str) -> ReturnShape:
    if not raw:
        return ReturnShape(type="unknown", description="", key_fields=[])
    return ReturnShape(
        type=raw.get("type", "unknown"),
        description=raw.get("description", ""),
        key_fields=list(raw.get("key_fields", []) or []),
    )


def _parse_role_visibility(raw: dict, ctx: str) -> RoleVisibility:
    if not raw:
        return RoleVisibility(default="all", denied_roles=[], note="")
    default = raw.get("default", "all")
    if default not in ("all", "restricted"):
        raise ValueError(f"{ctx}: role_visibility.default must be 'all' or 'restricted', got '{default}'")
    denied = list(raw.get("denied_roles", []) or [])
    note = str(raw.get("note", "") or "").strip()
    return RoleVisibility(default=default, denied_roles=denied, note=note)


def _parse_exception(raw: dict, ctx: str) -> ExceptionEntry:
    code = raw.get("code", "")
    if not code or not isinstance(code, str):
        raise ValueError(f"{ctx}: exception entry missing 'code' field")
    return ExceptionEntry(
        code=code,
        condition=str(raw.get("condition", "") or "").strip(),
        http_analogue=str(raw.get("http_analogue", "") or ""),
    )


def _parse_dangerous_arg(raw: dict, ctx: str) -> DangerousArgEntry:
    arg = raw.get("arg")
    if arg is None:
        raise ValueError(f"{ctx}: dangerous_arg entry missing 'arg' field")
    condition = raw.get("condition", "")
    violation_code = raw.get("violation_code", "")

    # min_role_names takes priority over min_role_tier
    min_role_names = raw.get("min_role_names")
    if not min_role_names:
        tier = int(raw.get("min_role_tier", 1))
        min_role_names = _ROLE_TIER_MAP.get(tier, [])

    return DangerousArgEntry(
        arg=str(arg),
        condition=str(condition),
        min_role_names=list(min_role_names),
        violation_code=str(violation_code),
        description=str(raw.get("description", "") or "").strip(),
    )


def _parse_example_call(raw: dict, ctx: str) -> ExampleCall:
    return ExampleCall(
        description=raw.get("description", ""),
        args=dict(raw.get("args", {}) or {}),
        expected_result_keys=list(raw.get("expected_result_keys", []) or []),
    )


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _require_str(d: dict, key: str, context: str) -> str:
    if key not in d:
        raise ValueError(f"{context}: missing required key '{key}'")
    val = d[key]
    if not isinstance(val, str):
        raise ValueError(f"{context}: key '{key}' must be a string, got {type(val).__name__}")
    return val


def _toolbench_type_to_json_schema(tb_type: str) -> str:
    """Map ToolBench type names to JSON Schema type names."""
    return {
        "STRING": "string",
        "NUMBER": "number",
        "BOOLEAN": "boolean",
        "ARRAY": "array",
    }.get(tb_type, "string")


# ---------------------------------------------------------------------------
# Docs page generator
# ---------------------------------------------------------------------------

def generate_docs_page(catalog: ToolCatalog, role: str) -> str:
    """Render a Markdown tool-guide page for the given role.

    The output is written to each environment's docs/ directory so that agents
    can discover available tools via docs.retrieve("available tools").
    """
    lines: list[str] = [
        "# HPC Tools Guide",
        "",
        f"Available tools for role: **{role}**",
        "",
        "Use these tools to answer HPC operations questions. Call tools with",
        "the name format `<tool>__<method>` (double underscore separator).",
        "",
    ]

    available = catalog.get_available_methods(role)
    available_set = set(available)

    for tool in catalog.tools:
        tool_methods = [(tn, mn) for tn, mn in available if tn == tool.name]
        if not tool_methods:
            continue
        lines.append(f"## `{tool.name}`")
        lines.append("")
        lines.append(tool.description.strip())
        lines.append("")

        for _, method_name in tool_methods:
            method = tool.get_method(method_name)
            lines.append(f"### `{tool.name}__{method_name}`")
            lines.append("")
            lines.append(method.description.strip())
            lines.append("")

            if method.required_parameters:
                lines.append("**Required parameters:**")
                for p in method.required_parameters:
                    enum_note = f" (one of: {p.valid_values})" if p.valid_values else ""
                    lines.append(f"- `{p.name}` ({p.type}): {p.description}{enum_note}")
                lines.append("")

            if method.optional_parameters:
                lines.append("**Optional parameters:**")
                for p in method.optional_parameters:
                    default_note = f" (default: `{p.default}`)" if p.default is not None else ""
                    enum_note = f" (one of: {p.valid_values})" if p.valid_values else ""
                    lines.append(f"- `{p.name}` ({p.type}){default_note}: {p.description}{enum_note}")
                lines.append("")

            if method.example_calls:
                ex = method.example_calls[0]
                lines.append(f"**Example:** {ex.description}")
                if ex.args:
                    args_str = ", ".join(f"{k}={v!r}" for k, v in ex.args.items())
                    lines.append(f"```\n{tool.name}__{method_name}({args_str})\n```")
                lines.append("")

    return "\n".join(lines)
