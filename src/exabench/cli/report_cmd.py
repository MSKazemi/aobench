"""exabench report — generate reports from a completed benchmark run."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

report_app = typer.Typer(help="Generate reports from a benchmark run directory.")


@report_app.command("json")
def report_json(
    run_dir: Annotated[str, typer.Argument(help="Path to the run directory (e.g. data/runs/run_…)")],
    output: Annotated[str | None, typer.Option("--output", "-o", help="Output file path (default: <run_dir>/run_summary.json)")] = None,
) -> None:
    """Write a JSON summary of all results in a run directory."""
    from exabench.reports.json_report import write_run_summary

    out_path = write_run_summary(run_dir)
    if output:
        import shutil
        shutil.copy(out_path, output)
        out_path = Path(output)

    typer.echo(f"Report written: {out_path}")

    # Print a quick summary to stdout
    import json
    with out_path.open() as fh:
        summary = json.load(fh)
    typer.echo(f"\nRun ID  : {summary['run_id']}")
    typer.echo(f"Tasks   : {summary['task_count']}")
    typer.echo(f"Mean score : {summary['mean_aggregate_score']}")
    typer.echo(f"Hard fails : {summary['hard_fail_count']}")


@report_app.command("html")
def report_html(
    run_dir: Annotated[str, typer.Argument(help="Path to the run directory")],
) -> None:
    """Write a self-contained HTML report for a run directory."""
    from exabench.reports.html_report import write_html_report

    out_path = write_html_report(run_dir)
    typer.echo(f"HTML report written: {out_path}")


@report_app.command("slices")
def report_slices(
    run_dir: Annotated[str, typer.Argument(help="Path to the run directory")],
) -> None:
    """Print a role × category score table for a run."""
    from exabench.reports.json_report import build_run_summary
    from exabench.reports.slices import format_table_text, role_category_table

    summary = build_run_summary(run_dir)
    table = role_category_table(summary)
    typer.echo(f"\nRole × Category scores  (run: {summary['run_id']})\n")
    typer.echo(format_table_text(table))
    typer.echo()
