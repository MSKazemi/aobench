"""BenchmarkRunner — orchestrates the full task execution pipeline."""

from __future__ import annotations

from pathlib import Path

from exabench.adapters.base import BaseAdapter
from exabench.loaders.env_loader import load_environment
from exabench.loaders.task_loader import load_task
from exabench.runners.context import ExecutionContext
from exabench.runners.trace_writer import TraceWriter
from exabench.schemas.result import BenchmarkResult
from exabench.schemas.trace import Trace
from exabench.scorers.aggregate import AggregateScorer
from exabench.tools.docs_tool import MockDocsTool
from exabench.tools.rbac_tool import MockRBACTool
from exabench.tools.registry import ToolRegistry
from exabench.tools.slurm_tool import MockSlurmTool
from exabench.tools.telemetry_tool import MockTelemetryTool


class BenchmarkRunner:
    """Runs a benchmark task against an environment snapshot using a given adapter."""

    def __init__(
        self,
        adapter: BaseAdapter,
        benchmark_root: str | Path,
        output_root: str | Path,
    ) -> None:
        self._adapter = adapter
        self._benchmark_root = Path(benchmark_root)
        self._output_root = Path(output_root)

    def run(
        self,
        task_id: str,
        env_id: str,
        run_id: str | None = None,
    ) -> BenchmarkResult:
        # 1. Load task and environment
        task = load_task(self._benchmark_root / "tasks" / "specs" / f"{task_id}.json")
        env = load_environment(self._benchmark_root / "environments" / env_id)

        # 2. Build role-aware tool set
        tools = self._build_tools(env.root_path, task.role)

        # 3. Assemble execution context
        ctx = ExecutionContext(
            task=task, env=env, tools=tools,
            run_id=run_id or "",
        )

        # 4. Run adapter → trace
        trace: Trace = self._adapter.run(ctx)

        # 5. Write trace to disk
        writer = TraceWriter(self._output_root / ctx.run_id)
        writer.write_trace(trace)

        # 6. Score
        scorer = AggregateScorer(self._benchmark_root / "configs" / "scoring_profiles.yaml")
        result = scorer.score(task, trace, run_id=ctx.run_id)

        # 7. Write result to disk
        writer.write_result(result)

        return result

    def _build_tools(self, env_root: str, role: str) -> ToolRegistry:
        tools = [
            MockSlurmTool(env_root, role=role),
            MockDocsTool(env_root, role=role),
            MockRBACTool(env_root, role=role),
            MockTelemetryTool(env_root, role=role),
        ]
        return ToolRegistry(tools, role=role)
