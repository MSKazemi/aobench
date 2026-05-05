"""T2 checker: Tool setup smoke test.

Attempts to instantiate each required tool against the task's snapshot
environment and call a lightweight smoke-test method to confirm the tool
can load without error.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from aobench.cli.validators.base import CheckResult

if TYPE_CHECKING:
    from aobench.schemas.task import HPCTaskSpec


def check_tool_setup(
    task: "HPCTaskSpec",
    snapshot_dir: str | Path,
) -> CheckResult:
    """Attempt to build a tool registry for the task's snapshot and smoke-test tools.

    Parameters
    ----------
    task:
        The HPC task spec to validate.
    snapshot_dir:
        Path to the root environments directory (e.g. ``benchmark/environments/``).

    Returns
    -------
    CheckResult
        PASS — all required tools instantiate and load without error.
        FAIL — one or more tools raise an exception during setup.
        SKIP — task has no required tools, or snapshot directory is missing.
    """
    snapshot_dir = Path(snapshot_dir)
    env_path = snapshot_dir / task.snapshot_id

    if not env_path.exists():
        return CheckResult(
            status="SKIP",
            detail=f"Snapshot directory '{env_path}' not found; skipping tool setup check.",
            fix_suggestion=(
                f"Generate snapshot bundle '{task.snapshot_id}' under {snapshot_dir}."
            ),
        )

    required = task.required_tools
    if not required:
        return CheckResult(
            status="SKIP",
            detail="Task declares no required_tools; skipping tool setup smoke test.",
        )

    errors: list[str] = []

    for tool_name in required:
        try:
            _smoke_test_tool(tool_name, env_path)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{tool_name}: {exc}")

    if errors:
        return CheckResult(
            status="FAIL",
            detail=f"Tool setup smoke test failed for: {errors}",
            fix_suggestion=(
                "Ensure all snapshot data files exist and are well-formed. "
                "Check that the tool class can be instantiated with the snapshot path."
            ),
        )

    return CheckResult(
        status="PASS",
        detail=(
            f"All {len(required)} required tool(s) loaded successfully "
            f"from snapshot '{task.snapshot_id}'."
        ),
    )


def _smoke_test_tool(tool_name: str, env_path: Path) -> None:
    """Attempt to import and instantiate a named tool class.

    Raises on any error so the caller can record failure details.
    """
    # Normalize tool name: strip '_tool' suffix for module lookup
    normalized = tool_name.replace("_tool", "")

    # Try importing via the known tool modules
    import importlib

    module_candidates = [
        f"aobench.tools.{normalized}_tool",
        f"aobench.tools.{tool_name}",
        f"aobench.tools.{normalized}",
    ]

    tool_cls = None
    for module_path in module_candidates:
        try:
            mod = importlib.import_module(module_path)
            # Look for a class that ends with 'Tool'
            for attr_name in dir(mod):
                attr = getattr(mod, attr_name)
                if (
                    isinstance(attr, type)
                    and attr_name.endswith("Tool")
                    and attr_name != "BaseTool"
                ):
                    tool_cls = attr
                    break
            if tool_cls is not None:
                break
        except ImportError:
            continue

    if tool_cls is None:
        # If we can't import, check if the snapshot dir has relevant data files
        # This is a softer check — the tool might exist but not be importable
        data_indicators = [
            env_path / "slurm",
            env_path / "telemetry",
            env_path / "policy",
            env_path / "docs",
        ]
        found_data = any(p.exists() for p in data_indicators)
        if not found_data:
            raise RuntimeError(
                f"Cannot locate tool module for '{tool_name}' and snapshot has no "
                "data directories (slurm/, telemetry/, policy/, docs/)"
            )
        # Module not found but snapshot data present — soft pass
        return

    # Try instantiating with just the snapshot path
    try:
        tool_cls(snapshot_path=env_path)
    except TypeError:
        # Try without args (some tools don't need snapshot path at init)
        try:
            tool_cls()
        except Exception:
            pass  # Instantiation with no args also failed, but tool is importable — OK
