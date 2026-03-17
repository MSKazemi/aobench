"""exabench run — run a benchmark task against an environment."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

run_app = typer.Typer(help="Run benchmark tasks.")


@run_app.command("task")
def run_task(
    task_id: Annotated[str, typer.Option("--task", "-t", help="Task ID, e.g. JOB_USR_001")],
    env_id: Annotated[str, typer.Option("--env", "-e", help="Environment ID, e.g. env_01")],
    adapter: Annotated[str, typer.Option("--adapter", "-a", help="Adapter name")] = "direct_qa",
    benchmark_root: Annotated[str, typer.Option("--benchmark", help="Path to benchmark/")] = "benchmark",
    output_root: Annotated[str, typer.Option("--output", "-o", help="Output directory for runs")] = "data/runs",
) -> None:
    """Run a single benchmark task."""
    from exabench.adapters.direct_qa_adapter import DirectQAAdapter
    from exabench.runners.runner import BenchmarkRunner

    def _build_adapter(name: str):
        if name == "direct_qa":
            return DirectQAAdapter()
        if name.startswith("openai"):
            from exabench.adapters.openai_adapter import OpenAIAdapter
            model = name.split(":", 1)[1] if ":" in name else "gpt-4o-mini"
            return OpenAIAdapter(model=model)
        raise ValueError(name)

    try:
        adapter_obj = _build_adapter(adapter)
    except ValueError:
        typer.echo(
            f"Unknown adapter '{adapter}'. "
            "Available: direct_qa, openai, openai:gpt-4o, openai:gpt-4o-mini",
            err=True,
        )
        raise typer.Exit(1)

    runner = BenchmarkRunner(
        adapter=adapter_obj,
        benchmark_root=Path(benchmark_root),
        output_root=Path(output_root),
    )

    typer.echo(f"Running task={task_id}  env={env_id}  adapter={adapter}")
    result = runner.run(task_id, env_id)

    typer.echo(f"\nResult: aggregate_score={result.aggregate_score:.4f}  hard_fail={result.hard_fail}")
    d = result.dimension_scores
    typer.echo(f"  outcome={d.outcome}  tool_use={d.tool_use}  "
               f"governance={d.governance}  efficiency={d.efficiency}")
    typer.echo(f"\nRun ID: {result.run_id}")
