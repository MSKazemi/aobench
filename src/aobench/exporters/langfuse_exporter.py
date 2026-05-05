"""LangfuseExporter — sends AOBench traces and scores to a Langfuse backend.

Written for Langfuse Python SDK v4 (OpenTelemetry-based).
The v4 SDK replaced the v2/v3 stateful `.trace()` / `.span()` API with
context-manager observations backed by OpenTelemetry spans.
"""

from __future__ import annotations

import os
from typing import Any

from aobench.exporters.base_exporter import BaseExporter
from aobench.schemas.result import BenchmarkResult
from aobench.schemas.task import TaskSpec
from aobench.schemas.trace import Trace
from aobench.utils.logging import get_logger

logger = get_logger(__name__)


class LangfuseExporter(BaseExporter):
    """Export a completed AOBench run to Langfuse (SDK v4).

    Each exported run becomes one Langfuse *trace* (root span) with:
    - One *tool* or *span* child per :class:`~aobench.schemas.trace.TraceStep`
    - One *generation* child capturing overall token usage
    - Six *scores* for the AOBench scoring dimensions + weighted aggregate

    Credentials are read from constructor arguments; falls back to environment
    variables when arguments are ``None``:
    - ``LANGFUSE_PUBLIC_KEY``
    - ``LANGFUSE_SECRET_KEY``
    - ``LANGFUSE_HOST`` or ``LANGFUSE_BASE_URL`` (either is accepted)

    Args:
        public_key: Langfuse project public key.
        secret_key: Langfuse project secret key.
        host:       Langfuse server URL (e.g. ``http://localhost:3000``).
                    Defaults to ``https://cloud.langfuse.com``.
    """

    def __init__(
        self,
        public_key: str | None = None,
        secret_key: str | None = None,
        host: str | None = None,
    ) -> None:
        try:
            from langfuse import Langfuse  # type: ignore[import-untyped]
        except ImportError as exc:
            raise ImportError(
                "langfuse is not installed. Run: pip install 'aobench[langfuse]'"
            ) from exc

        resolved_public = public_key or os.environ.get("LANGFUSE_PUBLIC_KEY", "")
        resolved_secret = secret_key or os.environ.get("LANGFUSE_SECRET_KEY", "")
        # SDK v4 accepts `host`; UI shows LANGFUSE_BASE_URL — support both env var names
        resolved_host = (
            host
            or os.environ.get("LANGFUSE_HOST")
            or os.environ.get("LANGFUSE_BASE_URL")
        )

        if not resolved_public or not resolved_secret:
            raise ValueError(
                "Langfuse credentials missing. "
                "Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY env vars, "
                "or pass them to LangfuseExporter()."
            )

        kwargs: dict[str, Any] = {
            "public_key": resolved_public,
            "secret_key": resolved_secret,
        }
        if resolved_host:
            kwargs["host"] = resolved_host

        self._lf = Langfuse(**kwargs)
        logger.debug("LangfuseExporter initialised host=%s", resolved_host or "cloud")

    # ------------------------------------------------------------------
    # BaseExporter interface
    # ------------------------------------------------------------------

    def export(self, trace: Trace, result: BenchmarkResult, task: TaskSpec) -> None:
        """Push one completed task run to Langfuse using the SDK v4 API."""
        from langfuse import LangfuseOtelSpanAttributes  # type: ignore[import-untyped]

        logger.debug("langfuse export trace_id=%s task_id=%s", trace.trace_id, trace.task_id)

        tags = [t for t in [trace.role, task.qcat, task.difficulty] if t]
        metadata: dict[str, Any] = {
            "adapter_name": trace.adapter_name,
            "model_name": trace.model_name,
            "environment_id": trace.environment_id,
            "hard_fail": trace.hard_fail,
            "hard_fail_reason": trace.hard_fail_reason,
            "weight_profile": result.weight_profile_name,
            "cost_estimate_usd": result.cost_estimate_usd,
            "latency_seconds": result.latency_seconds,
            # Duplicated here as fallback in case OTel attributes don't render
            "session_id": trace.run_id,
            "role": trace.role,
        }

        # AOBench trace IDs (trace_YYYYMMDD_HHMMSS_HEX8) are not valid Langfuse v4 trace IDs
        # (which require 32 lowercase hex chars). Store the AOBench ID in metadata for
        # correlation and let Langfuse auto-generate a valid trace ID.
        metadata["aobench_trace_id"] = trace.trace_id

        with self._lf.start_as_current_observation(
            name=trace.task_id,
            as_type="span",
            input={"query": task.query_text, "role": trace.role},
            output=trace.final_answer,
            metadata=metadata,
        ) as root_span:

            # Set session_id, user_id, tags via OTel span attributes (v4 native)
            try:
                otel_span = root_span._span  # type: ignore[attr-defined]
                otel_span.set_attribute(LangfuseOtelSpanAttributes.TRACE_SESSION_ID, trace.run_id)
                otel_span.set_attribute(LangfuseOtelSpanAttributes.TRACE_USER_ID, trace.role)
                if tags:
                    otel_span.set_attribute(LangfuseOtelSpanAttributes.TRACE_TAGS, tags)
            except Exception:
                logger.debug("Could not set OTel trace attributes — session/user will be in metadata")

            # --- one child span per agent step ---------------------------
            for step in trace.steps:
                as_type = "tool" if step.tool_call else "span"
                step_name = f"step-{step.step_id}"
                if step.tool_call:
                    step_name += f":{step.tool_call.tool_name}"

                step_meta: dict[str, Any] | None = None
                if step.tool_call:
                    step_meta = {
                        "tool_name": step.tool_call.tool_name,
                        "arguments": step.tool_call.arguments,
                    }

                step_output: Any = None
                if step.observation is not None:
                    obs = step.observation
                    if obs.permission_denied:
                        step_output = {"permission_denied": True}
                    elif obs.error:
                        step_output = {"error": obs.error}
                    else:
                        step_output = obs.content

                with root_span.start_as_current_observation(
                    name=step_name,
                    as_type=as_type,
                    input=step.reasoning,
                    output=step_output,
                    metadata=step_meta,
                ):
                    pass

            # --- one generation for overall LLM token usage --------------
            if trace.total_tokens:
                usage: dict[str, int] = {}
                if trace.prompt_tokens is not None:
                    usage["input"] = trace.prompt_tokens
                if trace.completion_tokens is not None:
                    usage["output"] = trace.completion_tokens

                with root_span.start_as_current_observation(
                    name="llm",
                    as_type="generation",
                    model=trace.model_name or "unknown",
                    usage_details=usage,
                    output=trace.final_answer,
                ):
                    pass

            # --- attach dimension scores to the trace --------------------
            scores = result.dimension_scores.model_dump()
            for dim_name, value in scores.items():
                if value is not None:
                    root_span.score_trace(name=dim_name, value=float(value))

            if result.aggregate_score is not None:
                root_span.score_trace(name="aggregate", value=float(result.aggregate_score))

        n_scores = sum(1 for v in scores.values() if v is not None) + (
            1 if result.aggregate_score is not None else 0
        )
        logger.debug(
            "langfuse export done trace_id=%s steps=%d scores=%d",
            trace.trace_id, len(trace.steps), n_scores,
        )

    def flush(self) -> None:
        """Flush buffered Langfuse events to the server."""
        self._lf.flush()
        logger.debug("LangfuseExporter flushed")
