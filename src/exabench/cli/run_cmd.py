"""exabench run — run a benchmark task against an environment."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

run_app = typer.Typer(help="Run benchmark tasks.")


def _build_adapter(name: str):
    if name == "direct_qa":
        from exabench.adapters.direct_qa_adapter import DirectQAAdapter
        return DirectQAAdapter()
    if name.startswith("openai"):
        from exabench.adapters.openai_adapter import OpenAIAdapter
        model = name.split(":", 1)[1] if ":" in name else "gpt-4o"
        return OpenAIAdapter(model=model)
    if name.startswith("mcp:") or name.startswith("mcp"):
        from exabench.adapters.mcp_client_adapter import MCPClientAdapter
        # "mcp:stdio:python server.py" → server_spec = "stdio:python server.py"
        # "mcp:sse:http://..."         → server_spec = "sse:http://..."
        server_spec = name[len("mcp:"):] if name.startswith("mcp:") else ""
        return MCPClientAdapter(server=server_spec)
    raise ValueError(name)


def _generate_reports(run_dir: Path) -> None:
    from exabench.reports.html_report import write_html_report
    from exabench.reports.json_report import write_run_summary
    from exabench.reports.slices import format_table_text, role_category_table
    from exabench.reports.json_report import build_run_summary

    json_path = write_run_summary(str(run_dir))
    typer.echo(f"  JSON report : {json_path}")
    html_path = write_html_report(str(run_dir))
    typer.echo(f"  HTML report : {html_path}")
    summary = build_run_summary(str(run_dir))
    table = role_category_table(summary)
    typer.echo(f"\nRole × Category scores  (run: {summary['run_id']})\n")
    typer.echo(format_table_text(table))


@run_app.command("all")
def run_all(
    adapter: Annotated[str, typer.Option("--adapter", "-a", help="Adapter name")] = "direct_qa",
    benchmark_root: Annotated[str, typer.Option("--benchmark", help="Path to benchmark/")] = "benchmark",
    output_root: Annotated[str, typer.Option("--output", "-o", help="Output directory for runs")] = "data/runs",
    report: Annotated[bool, typer.Option("--report/--no-report", help="Auto-generate JSON + HTML reports after run")] = True,
) -> None:
    """Run all benchmark tasks. Uses each task's environment_id from its spec.

    Creates one run directory with traces and results for every task.
    """
    from exabench.loaders.task_loader import load_tasks_from_dir
    from exabench.runners.runner import BenchmarkRunner
    from exabench.utils.ids import make_run_id

    try:
        adapter_obj = _build_adapter(adapter)
    except ValueError:
        typer.echo(
            f"Unknown adapter '{adapter}'. "
            "Available: direct_qa, openai, openai:gpt-4o, mcp:stdio:CMD, mcp:sse:URL",
            err=True,
        )
        raise typer.Exit(1)

    specs_dir = Path(benchmark_root) / "tasks" / "specs"
    tasks = load_tasks_from_dir(specs_dir)
    if not tasks:
        typer.echo(f"No tasks found in {specs_dir}", err=True)
        raise typer.Exit(1)

    run_id = make_run_id()
    runner = BenchmarkRunner(
        adapter=adapter_obj,
        benchmark_root=Path(benchmark_root),
        output_root=Path(output_root),
    )

    typer.echo(f"Running {len(tasks)} tasks with adapter={adapter} (run_id={run_id})\n")
    results = []
    for i, task in enumerate(tasks, 1):
        typer.echo(f"[{i}/{len(tasks)}] {task.task_id} @ {task.environment_id} ...", nl=False)
        try:
            result = runner.run(
                task.task_id,
                task.environment_id,
                run_id=run_id,
            )
            results.append((task.task_id, result))
            typer.echo(f" score={result.aggregate_score:.4f}")
        except Exception as e:
            typer.echo(f" FAILED: {e}", err=True)
            results.append((task.task_id, None))

    typer.echo(f"\nRun ID: {run_id}")
    succeeded = sum(1 for _, r in results if r is not None)
    typer.echo(f"Completed: {succeeded}/{len(tasks)} tasks")

    if report:
        run_dir = Path(output_root) / run_id
        typer.echo("\nGenerating reports...")
        _generate_reports(run_dir)


@run_app.command("task")
def run_task(
    task_id: Annotated[str, typer.Option("--task", "-t", help="Task ID, e.g. JOB_USR_001")],
    env_id: Annotated[str, typer.Option("--env", "-e", help="Environment ID, e.g. env_01")],
    adapter: Annotated[str, typer.Option("--adapter", "-a", help="Adapter name")] = "direct_qa",
    benchmark_root: Annotated[str, typer.Option("--benchmark", help="Path to benchmark/")] = "benchmark",
    output_root: Annotated[str, typer.Option("--output", "-o", help="Output directory for runs")] = "data/runs",
    report: Annotated[bool, typer.Option("--report/--no-report", help="Auto-generate JSON + HTML reports after run")] = True,
) -> None:
    """Run a single benchmark task."""
    from exabench.runners.runner import BenchmarkRunner

    try:
        adapter_obj = _build_adapter(adapter)
    except ValueError:
        typer.echo(
            f"Unknown adapter '{adapter}'. "
            "Available: direct_qa, openai, openai:gpt-4o, mcp:stdio:CMD, mcp:sse:URL",
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

    if report:
        run_dir = Path(output_root) / result.run_id
        typer.echo("\nGenerating reports...")
        _generate_reports(run_dir)
