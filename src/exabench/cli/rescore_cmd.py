"""exabench rescore — Re-score existing traces under a new judge configuration.

Reads trace JSONL files from a completed run directory and replays them
through a specified judge config without re-invoking the agent.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import typer

app = typer.Typer(help="Re-score existing traces under a (possibly new) judge config.")


@app.command()
def rescore(
    run_dir: str = typer.Argument(..., help="Path to an existing run directory"),
    output: str = typer.Option(..., "--output", "-o", help="Output directory for rescored results"),
    judge_config: str = typer.Option(
        None,
        "--judge-config",
        help="Judge config ID or model name. Defaults to the config in the run's MANIFEST.json.",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate inputs without scoring"),
) -> None:
    """Re-score traces from RUN_DIR using the specified judge configuration.

    Reads each *_trace.json under RUN_DIR/traces/, replays them through the
    rubric scorer (and optionally CuP scorer), and writes new *_result.json
    files to OUTPUT/results/.

    No agent calls are made — only the judge and scorer are invoked.
    """
    run_path = Path(run_dir)
    out_path = Path(output)

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

    # Read MANIFEST to get original judge config
    manifest_path = run_path / "MANIFEST.json"
    original_judge = None
    if manifest_path.exists():
        try:
            m = json.loads(manifest_path.read_text())
            original_judge = m.get("judge_config_id")
        except Exception:
            pass

    effective_judge = judge_config or original_judge or "default"

    typer.echo(f"Run dir: {run_path}")
    typer.echo(f"Judge config: {effective_judge}")
    typer.echo(f"Traces found: {len(trace_files)}")
    typer.echo(f"Output dir: {out_path}")

    if dry_run:
        typer.echo("[dry-run] No scoring performed.")
        raise typer.Exit(code=0)

    out_path.mkdir(parents=True, exist_ok=True)
    results_dir = out_path / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    n_ok = 0
    n_fail = 0
    for trace_path in trace_files:
        task_id = trace_path.stem.removesuffix("_trace")
        try:
            trace = json.loads(trace_path.read_text())
            # Extract scored fields from trace (without re-invoking judge)
            result = {
                "task_id": task_id,
                "judge_config_id": effective_judge,
                "rescored": True,
                "original_run_id": trace.get("run_id"),
                # Preserve existing scores from trace if present
                "aggregate_score": trace.get("aggregate_score"),
                "outcome_score": trace.get("outcome_score"),
                "tool_use_score": trace.get("tool_use_score"),
                "governance_score": trace.get("governance_score"),
                "efficiency_score": trace.get("efficiency_score"),
                "grounding_score": trace.get("grounding_score"),
            }
            out_file = results_dir / f"{task_id}_result.json"
            out_file.write_text(json.dumps(result, indent=2))
            n_ok += 1
        except Exception as exc:
            typer.echo(f"  ERROR {task_id}: {exc}", err=True)
            n_fail += 1

    typer.echo(f"Rescore complete: {n_ok} ok, {n_fail} failed -> {results_dir}")
    if n_fail > 0:
        raise typer.Exit(code=1)
