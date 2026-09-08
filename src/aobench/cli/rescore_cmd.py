"""aobench rescore — Re-score existing traces under the current scorer logic.

Reads ``*_trace.json`` files from a completed run directory and genuinely replays
each one through the full ``AggregateScorer`` — the same scorer used by
``BenchmarkRunner`` — writing fresh ``BenchmarkResult`` files. No agent calls are
made; only the scorers run. This is the correct way to recompute scores after a
scorer bug fix (e.g. the 2026-06-11 governance ``tool__method`` normalization)
without re-invoking any model.
"""

from __future__ import annotations

from pathlib import Path

import typer

from aobench.loaders.task_loader import load_task
from aobench.schemas.trace import Trace
from aobench.scorers.aggregate import AggregateScorer

app = typer.Typer(help="Re-score existing traces through the current AggregateScorer.")


@app.command()
def rescore(
    run_dir: str = typer.Argument(..., help="Path to an existing run directory"),
    output: str = typer.Option(..., "--output", "-o", help="Output directory for rescored results"),
    benchmark_root: str = typer.Option(
        "benchmark", "--benchmark-root", help="Benchmark root holding tasks/specs + configs."
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate inputs without scoring"),
) -> None:
    """Re-score every trace in RUN_DIR through the current ``AggregateScorer``.

    Reads each ``*_trace.json`` under ``RUN_DIR/traces/``, reloads the matching
    ``TaskSpec`` from ``BENCHMARK_ROOT/tasks/specs/``, replays it through the full
    scorer stack, and writes new ``*_result.json`` files (serialized
    ``BenchmarkResult``) to ``OUTPUT/results/``. No agent calls are made.
    """
    from aobench.cli._common import resolve_root

    run_path = Path(run_dir)
    out_path = Path(output)
    broot = resolve_root(benchmark_root)

    if not run_path.is_dir():
        typer.echo(f"Error: run_dir '{run_dir}' is not a directory.", err=True)
        raise typer.Exit(code=2)

    traces_dir = run_path / "traces"
    if not traces_dir.is_dir():
        typer.echo(f"No 'traces/' subdirectory found in '{run_dir}'.", err=True)
        typer.echo("This run may not have been recorded with trace output.", err=True)
        raise typer.Exit(code=2)

    trace_files = sorted(traces_dir.glob("*_trace.json"))
    if not trace_files:
        typer.echo(f"No *_trace.json files found in '{traces_dir}'.", err=True)
        raise typer.Exit(code=2)

    specs_dir = broot / "tasks" / "specs"
    profile_path = broot / "configs" / "scoring_profiles.yaml"

    typer.echo(f"Run dir: {run_path}")
    typer.echo(f"Benchmark root: {broot}")
    typer.echo(f"Traces found: {len(trace_files)}")
    typer.echo(f"Output dir: {out_path}")

    if dry_run:
        typer.echo("[dry-run] No scoring performed.")
        raise typer.Exit(code=0)

    out_path.mkdir(parents=True, exist_ok=True)
    results_dir = out_path / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    scorer = AggregateScorer(profile_path)

    n_ok = 0
    n_fail = 0
    for trace_path in trace_files:
        task_id = trace_path.stem.removesuffix("_trace")
        try:
            trace = Trace.model_validate_json(trace_path.read_text(encoding="utf-8"))
            task = load_task(specs_dir / f"{task_id}.json")
            result = scorer.score(task, trace, run_id=trace.run_id)
            out_file = results_dir / f"{task_id}_result.json"
            out_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
            n_ok += 1
        except Exception as exc:
            typer.echo(f"  ERROR {task_id}: {exc}", err=True)
            n_fail += 1

    typer.echo(f"Rescore complete: {n_ok} ok, {n_fail} failed -> {results_dir}")
    if n_fail > 0:
        raise typer.Exit(code=1)
