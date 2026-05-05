"""aobench lite — AOBench-Lite subset selection commands."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import typer

lite_app = typer.Typer(help="AOBench-Lite subset selection.")


@lite_app.command("select")
def lite_select(
    task_dir: Annotated[str, typer.Option("--task-dir", help="Task specs directory")] = "benchmark/tasks/specs",
    pilot_scores: Annotated[Optional[str], typer.Option("--pilot-scores", help="JSON file with pilot model scores {task_id: {model: score}}")] = None,
    output: Annotated[str, typer.Option("--output", "-o", help="Output manifest path")] = "benchmark/tasks/lite_manifest_v1.json",
    task_file: Annotated[str, typer.Option("--task-file", help="Task corpus JSON for T1–T10 validation")] = "benchmark/tasks/task_set_v1.json",
    snapshot_dir: Annotated[str, typer.Option("--snapshot-dir", help="Environments directory")] = "benchmark/environments/",
    catalog: Annotated[str, typer.Option("--catalog", help="Tool catalog YAML")] = "benchmark/configs/hpc_tool_catalog.yaml",
    skip_validation: Annotated[bool, typer.Option("--skip-validation/--no-skip-validation", help="Skip T1–T10 checks (use task.t1_t10_pass field)")] = False,
) -> None:
    """Run the 3-stage AOBench-Lite selection pipeline.

    Stage 1: T1–T10 gate + split exclusion
    Stage 2: Attribute filter (one per QCAT × role × difficulty_tier cell)
    Stage 3: Execution filter (non-degenerate pilot-score gate, or 'pending')

    Outputs benchmark/tasks/lite_manifest_v1.json.
    """
    import json

    from aobench.tasks.lite_selector import select_lite

    # Load validate_results
    validate_results: dict = {}
    if not skip_validation:
        typer.echo(f"Running T1–T10 validation on {task_file}...")
        try:
            from aobench.validation.task_pipeline import run_validation_pipeline
            validate_results = run_validation_pipeline(
                task_file=task_file,
                snapshot_dir=snapshot_dir,
                catalog_path=catalog,
            )
            pass_count = sum(1 for v in validate_results.values() if v["overall"] == "PASS")
            typer.echo(f"  Validation complete: {pass_count}/{len(validate_results)} tasks passed T1–T10.")
        except Exception as exc:
            typer.echo(f"  Warning: T1–T10 validation failed ({exc}). Falling back to task.t1_t10_pass field.", err=True)

    # Load pilot scores
    pilot: dict | None = None
    if pilot_scores:
        ps_path = Path(pilot_scores)
        if not ps_path.exists():
            typer.echo(f"Pilot scores file not found: {ps_path}", err=True)
            raise typer.Exit(1)
        pilot = json.loads(ps_path.read_text(encoding="utf-8"))
        typer.echo(f"  Loaded pilot scores for {len(pilot)} tasks from {ps_path}.")
    else:
        typer.echo("  No pilot scores provided — Stage 3 will mark tasks as 'execution_filter: pending'.")

    typer.echo(f"Running 3-stage Lite selection from {task_dir}...")
    try:
        lite_ids = select_lite(
            task_dir=task_dir,
            validate_results=validate_results,
            pilot_scores=pilot,
            output_path=output,
        )
    except AssertionError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)

    typer.echo(f"AOBench-Lite: {len(lite_ids)} tasks selected → {output}")
    if lite_ids:
        typer.echo(f"  IDs: {', '.join(sorted(lite_ids))}")
