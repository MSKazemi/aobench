"""exabench run — run a benchmark task against an environment."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from exabench.utils.logging import configure_logging

run_app = typer.Typer(help="Run benchmark tasks.")


def _build_adapter(name: str):
    """Instantiate an adapter by name using the prefix registry."""
    from exabench.adapters.direct_qa_adapter import DirectQAAdapter
    from exabench.adapters.openai_adapter import OpenAIAdapter
    from exabench.adapters.mcp_client_adapter import MCPClientAdapter

    def _make_direct_qa(_n: str):
        return DirectQAAdapter()

    def _make_openai(n: str):
        model = n.split(":", 1)[1] if ":" in n else "gpt-4o"
        return OpenAIAdapter(model=model)

    def _make_anthropic(n: str):
        from exabench.adapters.anthropic_adapter import AnthropicAdapter
        model = n.split(":", 1)[1] if ":" in n else "claude-sonnet-4-6"
        return AnthropicAdapter(model=model)

    def _make_mcp(n: str):
        # "mcp:stdio:python server.py" → server_spec = "stdio:python server.py"
        # "mcp:sse:http://..."         → server_spec = "sse:http://..."
        server_spec = n[len("mcp:"):] if ":" in n else ""
        return MCPClientAdapter(server=server_spec)

    _REGISTRY = {
        "direct_qa": _make_direct_qa,
        "openai": _make_openai,
        "anthropic": _make_anthropic,
        "mcp": _make_mcp,
    }

    prefix = name.split(":")[0]
    factory = _REGISTRY.get(prefix)
    if factory is None:
        known = ", ".join(_REGISTRY)
        raise ValueError(f"Unknown adapter {name!r}. Known prefixes: {known}")
    return factory(name)


def _build_exporter(langfuse: bool):
    """Instantiate a LangfuseExporter when --langfuse is set, else return None."""
    if not langfuse:
        return None
    from exabench.exporters.langfuse_exporter import LangfuseExporter
    try:
        return LangfuseExporter()
    except (ImportError, ValueError) as exc:
        typer.echo(f"Langfuse error: {exc}", err=True)
        raise typer.Exit(1)


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


def _check_fidelity_gate(env_id: str, fidelity_root: str = "data/fidelity") -> None:
    """Informational V0 fidelity gate check.

    Reads data/fidelity/index.json and warns if the environment's fidelity
    report failed. Does not hard-fail — the gate is informational in V0.
    If index.json is missing, silently skips the check.
    """
    index_path = Path(fidelity_root) / "index.json"
    if not index_path.exists():
        return

    try:
        import json

        entries = json.loads(index_path.read_text())
        for entry in entries:
            if entry.get("env_id") == env_id:
                if not entry.get("passed", True):
                    typer.echo(
                        f"[fidelity-gate] WARNING: environment '{env_id}' did not pass "
                        f"fidelity validation (see data/fidelity/{env_id}.md). "
                        "Continuing anyway (V0 gate is informational).",
                        err=True,
                    )
                return
    except Exception:  # noqa: BLE001
        pass  # Never block the run due to a fidelity-check error


def _load_split_ids(split: str, benchmark_root: str) -> set[str] | None:
    """Return the set of task IDs for the requested split, or None (= all tasks).

    Raises typer.Exit with an error message for the 'test' split (locked).
    """
    if split == "all":
        return None

    import sys
    sys.path.insert(0, str(Path(benchmark_root).parent))
    try:
        from benchmark.tasks.dataset_splits import (
            TEST_TASK_IDS, LITE_TASK_IDS, get_split
        )
        from exabench.loaders.task_loader import load_tasks_from_dir
    except ImportError:
        typer.echo("Could not import dataset_splits. Run from the repo root.", err=True)
        raise typer.Exit(1)
    finally:
        sys.path.pop(0)

    if split == "test":
        typer.echo(
            "Error: Test split is locked. "
            "Inspect outputs/specs/task_lite_spec.md §4.4 for access rules.",
            err=True,
        )
        raise typer.Exit(1)

    if split == "lite":
        ids = set(LITE_TASK_IDS)
        if not ids:
            typer.echo(
                "Warning: LITE_TASK_IDS is empty. "
                "Run `exabench lite select` first to populate the Lite manifest.",
                err=True,
            )
        return ids

    if split == "dev":
        specs_dir = Path(benchmark_root) / "tasks" / "specs"
        all_ids = {t.task_id for t in load_tasks_from_dir(specs_dir)}
        return all_ids - set(TEST_TASK_IDS)

    typer.echo(f"Unknown split '{split}'. Use: all | dev | lite | test", err=True)
    raise typer.Exit(1)


@run_app.command("all")
def run_all(
    adapter: Annotated[str, typer.Option("--adapter", "-a", help="Adapter name")] = "direct_qa",
    benchmark_root: Annotated[str, typer.Option("--benchmark", help="Path to benchmark/")] = "benchmark",
    output_root: Annotated[str, typer.Option("--output", "-o", help="Output directory for runs")] = "data/runs",
    split: Annotated[str, typer.Option("--split", "-s", help="Task split: all | dev | lite | test")] = "all",
    report: Annotated[bool, typer.Option("--report/--no-report", help="Auto-generate JSON + HTML reports after run")] = True,
    langfuse: Annotated[bool, typer.Option("--langfuse/--no-langfuse", help="Export traces and scores to Langfuse")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable DEBUG logging")] = False,
) -> None:
    """Run all benchmark tasks. Uses each task's environment_id from its spec.

    Creates one run directory with traces and results for every task.
    Use --split lite|dev|all to filter which tasks are run.
    """
    configure_logging("DEBUG" if verbose else "WARNING")

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
    all_tasks = load_tasks_from_dir(specs_dir)
    if not all_tasks:
        typer.echo(f"No tasks found in {specs_dir}", err=True)
        raise typer.Exit(1)

    split_ids = _load_split_ids(split, benchmark_root)
    if split_ids is not None:
        tasks = [t for t in all_tasks if t.task_id in split_ids]
        typer.echo(f"Split '{split}': {len(tasks)}/{len(all_tasks)} tasks selected.")
    else:
        tasks = all_tasks
    if not tasks:
        typer.echo(f"No tasks match split '{split}'.", err=True)
        raise typer.Exit(1)

    exporter = _build_exporter(langfuse)
    run_id = make_run_id()
    runner = BenchmarkRunner(
        adapter=adapter_obj,
        benchmark_root=Path(benchmark_root),
        output_root=Path(output_root),
        exporter=exporter,
    )

    from exabench.runners.run_artifacts import write_run_manifest, finalize_run_artifacts

    run_dir = Path(output_root) / run_id
    write_run_manifest(
        run_dir,
        model=adapter.split(":", 1)[1] if ":" in adapter else adapter,
        adapter=adapter,
        split=split,
    )

    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn

    results = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("•"),
        TimeElapsedColumn(),
        TextColumn("{task.fields[status]}"),
        transient=False,
    ) as progress:
        task_bar = progress.add_task(
            f"run_id={run_id}  adapter={adapter}",
            total=len(tasks),
            status=f"0/{len(tasks)} done",
        )
        for bench_task in tasks:
            progress.update(task_bar, description=f"[bold blue]{bench_task.task_id}[/bold blue]")
            _check_fidelity_gate(bench_task.environment_id)
            try:
                result = runner.run(
                    bench_task.task_id,
                    bench_task.environment_id,
                    run_id=run_id,
                )
                results.append((bench_task.task_id, result))
                score_str = f"[green]score={result.aggregate_score:.4f}[/green]"
            except Exception as e:
                results.append((bench_task.task_id, None))
                score_str = f"[red]FAILED: {e}[/red]"
            succeeded = sum(1 for _, r in results if r is not None)
            progress.update(
                task_bar,
                advance=1,
                status=f"{succeeded}/{len(tasks)} done  last={score_str}",
            )

    finalize_run_artifacts(run_dir, results)

    typer.echo(f"\nRun ID: {run_id}")
    succeeded = sum(1 for _, r in results if r is not None)
    typer.echo(f"Completed: {succeeded}/{len(tasks)} tasks")

    if exporter:
        exporter.flush()

    if report:
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
    langfuse: Annotated[bool, typer.Option("--langfuse/--no-langfuse", help="Export traces and scores to Langfuse")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable DEBUG logging")] = False,
) -> None:
    """Run a single benchmark task."""
    configure_logging("DEBUG" if verbose else "WARNING")

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

    exporter = _build_exporter(langfuse)
    runner = BenchmarkRunner(
        adapter=adapter_obj,
        benchmark_root=Path(benchmark_root),
        output_root=Path(output_root),
        exporter=exporter,
    )

    from exabench.runners.run_artifacts import write_run_manifest, finalize_run_artifacts
    from exabench.utils.ids import make_run_id

    single_run_id = make_run_id()
    single_run_dir = Path(output_root) / single_run_id
    write_run_manifest(
        single_run_dir,
        model=adapter.split(":", 1)[1] if ":" in adapter else adapter,
        adapter=adapter,
        split="single",
    )

    _check_fidelity_gate(env_id)
    typer.echo(f"Running task={task_id}  env={env_id}  adapter={adapter}")
    result = runner.run(task_id, env_id, run_id=single_run_id)

    finalize_run_artifacts(single_run_dir, [result])

    if exporter:
        exporter.flush()

    typer.echo(f"\nResult: aggregate_score={result.aggregate_score:.4f}  hard_fail={result.hard_fail}")
    d = result.dimension_scores
    typer.echo(f"  outcome={d.outcome}  tool_use={d.tool_use}  "
               f"governance={d.governance}  efficiency={d.efficiency}")
    typer.echo(f"\nRun ID: {result.run_id}")

    if report:
        run_dir = Path(output_root) / result.run_id
        typer.echo("\nGenerating reports...")
        _generate_reports(run_dir)
