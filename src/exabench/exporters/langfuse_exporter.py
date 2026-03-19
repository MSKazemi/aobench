"""LangfuseExporter — sends ExaBench traces and scores to a Langfuse backend."""

from __future__ import annotations

import os
from typing import Any

from exabench.exporters.base_exporter import BaseExporter
from exabench.schemas.result import BenchmarkResult
from exabench.schemas.task import TaskSpec
from exabench.schemas.trace import Trace
from exabench.utils.logging import get_logger

logger = get_logger(__name__)


class LangfuseExporter(BaseExporter):
    """Export a completed ExaBench run to Langfuse.

    Each exported run becomes one Langfuse *trace* with:
    - One *span* per :class:`~exabench.schemas.trace.TraceStep`
    - One *generation* capturing overall token usage
    - Six *scores* for the ExaBench scoring dimensions
    - One *score* for the weighted aggregate

    Reads credentials from constructor arguments; falls back to the
    ``LANGFUSE_PUBLIC_KEY``, ``LANGFUSE_SECRET_KEY``, and ``LANGFUSE_HOST``
    environment variables when arguments are ``None``.

    Args:
        public_key: Langfuse project public key.
        secret_key: Langfuse project secret key.
        host:       Langfuse server URL. Defaults to ``https://cloud.langfuse.com``
                    or ``LANGFUSE_HOST`` env var.  Use ``http://localhost:3000``
                    for a self-hosted instance.
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
                "langfuse is not installed. Run: pip install 'exabench[langfuse]'"
            ) from exc

        resolved_public = public_key or os.environ.get("LANGFUSE_PUBLIC_KEY", "")
        resolved_secret = secret_key or os.environ.get("LANGFUSE_SECRET_KEY", "")
        # Support both LANGFUSE_HOST (ExaBench convention) and LANGFUSE_BASE_URL (Langfuse UI default)
        resolved_host = host or os.environ.get("LANGFUSE_HOST") or os.environ.get("LANGFUSE_BASE_URL")

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
        """Push one completed task run to Langfuse."""
        logger.debug("langfuse export trace_id=%s task_id=%s", trace.trace_id, trace.task_id)

        tags = [trace.role, task.qcat, task.difficulty]

        lf_trace = self._lf.trace(
            id=trace.trace_id,
            name=trace.task_id,
            session_id=trace.run_id,
            user_id=trace.role,
            metadata={
                "adapter_name": trace.adapter_name,
                "model_name": trace.model_name,
                "environment_id": trace.environment_id,
                "hard_fail": trace.hard_fail,
                "hard_fail_reason": trace.hard_fail_reason,
                "weight_profile": result.weight_profile_name,
                "cost_estimate_usd": result.cost_estimate_usd,
                "latency_seconds": result.latency_seconds,
            },
            tags=[t for t in tags if t],  # drop None/empty
        )

        # --- one span per agent step ----------------------------------
        for step in trace.steps:
            span_meta: dict[str, Any] = {}
            span_input: str | None = step.reasoning

            if step.tool_call is not None:
                span_meta["tool_name"] = step.tool_call.tool_name
                span_meta["arguments"] = step.tool_call.arguments

            span_output: Any = None
            if step.observation is not None:
                obs = step.observation
                if obs.permission_denied:
                    span_output = {"permission_denied": True}
                elif obs.error:
                    span_output = {"error": obs.error}
                else:
                    span_output = obs.content

            span = lf_trace.span(
                name=f"step-{step.step_id}" + (
                    f":{step.tool_call.tool_name}" if step.tool_call else ""
                ),
                input=span_input,
                metadata=span_meta if span_meta else None,
                start_time=step.timestamp,
            )
            span.end(output=span_output, end_time=step.timestamp)

        # --- one generation for overall LLM token usage ---------------
        if trace.total_tokens:
            usage: dict[str, int] = {}
            if trace.prompt_tokens is not None:
                usage["input"] = trace.prompt_tokens
            if trace.completion_tokens is not None:
                usage["output"] = trace.completion_tokens

            lf_trace.generation(
                name="llm",
                model=trace.model_name or "unknown",
                usage=usage,
                input=None,   # prompt not stored in trace for privacy
                output=trace.final_answer,
                start_time=trace.start_time,
                end_time=trace.end_time,
            )

        # --- attach dimension scores ----------------------------------
        scores = result.dimension_scores.model_dump()
        for dim_name, value in scores.items():
            if value is not None:
                lf_trace.score(name=dim_name, value=float(value))

        if result.aggregate_score is not None:
            lf_trace.score(name="aggregate", value=float(result.aggregate_score))

        logger.debug(
            "langfuse export done trace_id=%s steps=%d scores=%d",
            trace.trace_id,
            len(trace.steps),
            sum(1 for v in scores.values() if v is not None) + (1 if result.aggregate_score is not None else 0),
        )

    def flush(self) -> None:
        """Flush buffered Langfuse events to the server."""
        self._lf.flush()
        logger.debug("LangfuseExporter flushed")
