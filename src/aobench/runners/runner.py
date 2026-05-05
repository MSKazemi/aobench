"""BenchmarkRunner — orchestrates the full task execution pipeline."""

from __future__ import annotations

from pathlib import Path

from aobench.adapters.base import BaseAdapter
from aobench.environment.snapshot_loader import build_tool_registry
from aobench.exporters.base_exporter import BaseExporter
from aobench.loaders.env_loader import load_environment
from aobench.loaders.task_loader import load_task
from aobench.runners.context import ExecutionContext
from aobench.runners.trace_writer import TraceWriter
from aobench.schemas.result import BenchmarkResult
from aobench.schemas.trace import Trace
from aobench.scorers.aggregate import AggregateScorer
from aobench.tools.registry import ToolRegistry
from aobench.utils.logging import get_logger

logger = get_logger(__name__)


class BenchmarkRunner:
    """Runs a benchmark task against an environment snapshot using a given adapter."""

    def __init__(
        self,
        adapter: BaseAdapter,
        benchmark_root: str | Path,
        output_root: str | Path,
        exporter: BaseExporter | None = None,
    ) -> None:
        self._adapter = adapter
        self._benchmark_root = Path(benchmark_root)
        self._output_root = Path(output_root)
        self._exporter = exporter

    def run(
        self,
        task_id: str,
        env_id: str,
        run_id: str | None = None,
    ) -> BenchmarkResult:
        logger.info("run start  task=%s env=%s adapter=%s", task_id, env_id, self._adapter.__class__.__name__)

        # 1. Load task and environment
        task = load_task(self._benchmark_root / "tasks" / "specs" / f"{task_id}.json")
        env = load_environment(self._benchmark_root / "environments" / env_id)
        logger.debug("loaded task=%s env=%s role=%s", task.task_id, env.metadata.environment_id, task.role)

        # 2. Build role-aware tool set from snapshot bundle
        tools = build_tool_registry(env, role=task.role, allowed_tools=task.allowed_tools)
        logger.debug("tools registered: %s", tools.available_tool_names)

        # 3. Assemble execution context
        ctx = ExecutionContext(
            task=task, env=env, tools=tools,
            run_id=run_id or "",
        )

        # 4. Run adapter → trace
        trace: Trace = self._adapter.run(ctx)
        logger.debug("trace complete steps=%d tokens=%d hard_fail=%s",
                     len(trace.steps), trace.total_tokens, trace.hard_fail)

        # 5. Write trace to disk
        writer = TraceWriter(self._output_root / ctx.run_id)
        writer.write_trace(trace)

        # 6. Score
        scorer = AggregateScorer(self._benchmark_root / "configs" / "scoring_profiles.yaml")
        result = scorer.score(task, trace, run_id=ctx.run_id)
        logger.info("run done   task=%s score=%.4f hard_fail=%s", task_id, result.aggregate_score, result.hard_fail)

        # 7. Write result to disk
        writer.write_result(result)

        # 8. Export to observability backend (optional)
        if self._exporter is not None:
            try:
                self._exporter.export(trace, result, task)
            except Exception:
                logger.exception("exporter failed — continuing without export")

        return result

