"""Pure Trace → span-tree converter (spec-0005 R8) — no OpenTelemetry dependency.

Produces a list of ``SpanData`` (a plain dataclass) that ``exporter.py`` maps to
real OTLP spans. Keeping this pure makes the full span tree + attributes unit-
testable without the ``otel`` extra installed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from aobench.exporters.otel import semconv as sc
from aobench.schemas.result import DIMENSION_NAMES, BenchmarkResult
from aobench.schemas.trace import Trace


@dataclass
class SpanData:
    name: str
    kind: str = sc.KIND_INTERNAL
    attributes: dict[str, Any] = field(default_factory=dict)
    children: list["SpanData"] = field(default_factory=list)

    def walk(self) -> list["SpanData"]:
        """Depth-first flatten (self first), for assertions/emission."""
        out = [self]
        for c in self.children:
            out.extend(c.walk())
        return out


def _provider_from_adapter(adapter_name: str) -> str:
    a = (adapter_name or "").lower()
    if "openai" in a or a.startswith("gpt") or "azure" in a:
        return "openai"
    if "anthropic" in a or "claude" in a:
        return "anthropic"
    if "ollama" in a:
        return "ollama"
    return a or "unknown"


#: Every scored dimension, from the schema — see aobench.schemas.result.DIMENSION_NAMES.
_DIMENSIONS = DIMENSION_NAMES


def trace_to_spans(
    trace: Trace,
    result: Optional[BenchmarkResult] = None,
    *,
    env_manifest_sha256: Optional[str] = None,
    split: Optional[str] = None,
    seed: Optional[int] = None,
    replay: str = "live",
    capture_content: bool = False,
) -> SpanData:
    """Convert one run's Trace (+ optional scored result) into a span tree.

    Returns the root ``aobench.task_run`` span. See spec-0005 R1–R4.
    """
    root_attrs: dict[str, Any] = {
        sc.CONVERSATION_ID: trace.run_id,
        sc.AO_TASK_ID: trace.task_id,
        sc.AO_ROLE: trace.role,
        sc.AO_ENV_ID: trace.environment_id,
        sc.AO_SEMCONV_VERSION: sc.SEMCONV_VERSION,
        sc.AO_REPLAY_MODE: replay,
    }
    if env_manifest_sha256:
        root_attrs[sc.AO_ENV_MANIFEST_SHA] = env_manifest_sha256
    if split:
        root_attrs[sc.AO_SPLIT] = split
    if seed is not None:
        root_attrs[sc.AO_REPLAY_SEED] = seed
    if trace.cost_estimate_usd is not None:
        root_attrs[sc.AO_COST_USD] = trace.cost_estimate_usd
    root_attrs[sc.AO_GOVERNANCE_HARD_FAIL] = bool(trace.hard_fail)

    root = SpanData(name=sc.ROOT_SPAN, kind=sc.KIND_SERVER, attributes=root_attrs)

    # ----- invoke_agent subtree -----
    agent_span = SpanData(
        name=f"{sc.OP_INVOKE_AGENT} {trace.adapter_name}",
        kind=sc.KIND_INTERNAL,
        attributes={
            sc.OP_NAME: sc.OP_INVOKE_AGENT,
            sc.AGENT_NAME: trace.adapter_name,
            sc.AGENT_ID: trace.run_id,
            sc.PROVIDER_NAME: _provider_from_adapter(trace.adapter_name),
        },
    )

    # A single chat span carrying token usage (Trace has run-level totals).
    chat_attrs: dict[str, Any] = {
        sc.OP_NAME: sc.OP_CHAT,
        sc.PROVIDER_NAME: _provider_from_adapter(trace.adapter_name),
    }
    if trace.model_name:
        chat_attrs[sc.REQUEST_MODEL] = trace.model_name
        chat_attrs[sc.RESPONSE_MODEL] = trace.model_name
    if trace.prompt_tokens is not None:
        chat_attrs[sc.USAGE_INPUT_TOKENS] = trace.prompt_tokens
    if trace.completion_tokens is not None:
        chat_attrs[sc.USAGE_OUTPUT_TOKENS] = trace.completion_tokens
    if capture_content and trace.final_answer:
        chat_attrs[sc.OUTPUT_MESSAGES] = trace.final_answer
    agent_span.children.append(
        SpanData(name=f"{sc.OP_CHAT} {trace.model_name or trace.adapter_name}",
                 kind=sc.KIND_CLIENT, attributes=chat_attrs)
    )

    # One execute_tool span per tool_call step.
    for step in trace.steps:
        if step.step_type == "tool_call" and step.tool_call is not None:
            tool_attrs: dict[str, Any] = {
                sc.OP_NAME: sc.OP_EXECUTE_TOOL,
                sc.TOOL_NAME: step.tool_call.tool_name,
                sc.TOOL_CALL_ID: step.span_id or f"step_{step.step_id}",
            }
            if capture_content and step.reasoning:
                tool_attrs[sc.INPUT_MESSAGES] = step.reasoning
            agent_span.children.append(
                SpanData(name=f"{sc.OP_EXECUTE_TOOL} {step.tool_call.tool_name}",
                         kind=sc.KIND_INTERNAL, attributes=tool_attrs)
            )

    root.children.append(agent_span)

    # ----- score subtree -----
    if result is not None:
        score_attrs: dict[str, Any] = {sc.AO_GOVERNANCE_HARD_FAIL: bool(result.hard_fail)}
        if result.task_category:
            root.attributes[sc.AO_QCAT] = result.task_category
        for dim in _DIMENSIONS:
            val = getattr(result.dimension_scores, dim, None)
            if val is not None:
                score_attrs[sc.score_attr(dim)] = val
                root.attributes[sc.score_attr(dim)] = val
        if result.cost_estimate_usd is not None:
            root.attributes[sc.AO_COST_USD] = result.cost_estimate_usd
        root.children.append(
            SpanData(name=sc.SCORE_SPAN, kind=sc.KIND_INTERNAL, attributes=score_attrs)
        )

    return root
