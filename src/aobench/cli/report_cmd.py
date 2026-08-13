"""aobench report — generate reports from a completed benchmark run."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

report_app = typer.Typer(help="Generate reports from a benchmark run directory.")


def _available_run_dirs(run_dir: Path) -> list[Path]:
    """Return sibling run directories in a stable order."""
    if not run_dir.parent.is_dir():
        return []
    return sorted(path for path in run_dir.parent.iterdir() if path.is_dir())


def _report_missing_run_dir(run_dir: Path) -> None:
    """Print an actionable error for a run directory that does not exist."""
    if run_dir.exists():
        typer.echo(f"Error: run directory '{run_dir}' is not a directory.", err=True)
    else:
        typer.echo(f"Error: run directory '{run_dir}' does not exist.", err=True)
    available_runs = _available_run_dirs(run_dir)
    if available_runs:
        typer.echo("\nAvailable runs:", err=True)
        for available_run in available_runs[:10]:
            typer.echo(f"  {available_run}", err=True)
        if len(available_runs) > 10:
            typer.echo(f"  … and {len(available_runs) - 10} more", err=True)
    raise typer.Exit(code=2)


def _report_empty_run(run_dir: Path) -> None:
    """Print an actionable error for a run that has no completed results."""
    typer.echo(f"Error: run '{run_dir}' contains no results.", err=True)
    typer.echo("This usually means the run failed before any task completed.", err=True)
    typer.echo(f"Check {run_dir}/ for a log, or re-run with:", err=True)
    typer.echo("  aobench run all --adapter direct_qa --split dev", err=True)
    raise typer.Exit(code=2)


def _require_completed_run(run_dir: str | Path) -> None:
    """Guard shared by every ``report`` subcommand; exit 2 if the run is unusable.

    The report builders raise ``FileNotFoundError`` for both cases, which Typer
    renders as a traceback. Checking here keeps the two situations distinct and
    exits 2 the way the other run-directory commands do (see ``rescore_cmd``).
    """
    run_path = Path(run_dir)
    if not run_path.is_dir():
        _report_missing_run_dir(run_path)
    results_dir = run_path / "results"
    if not results_dir.is_dir() or not any(results_dir.glob("*_result.json")):
        _report_empty_run(run_path)


@report_app.command("json")
def report_json(
    run_dir: Annotated[
        str, typer.Argument(help="Path to the run directory (e.g. data/runs/run_…)")
    ],
    output: Annotated[
        str | None,
        typer.Option(
            "--output", "-o", help="Output file path (default: <run_dir>/run_summary.json)"
        ),
    ] = None,
    as_json: Annotated[bool, typer.Option("--json", help="Emit JSON instead of a table.")] = False,
) -> None:
    """Write a JSON summary of all results in a run directory."""
    from aobench.reports.json_report import write_run_summary

    _require_completed_run(run_dir)

    out_path = write_run_summary(run_dir)
    if output:
        import shutil

        shutil.copy(out_path, output)
        out_path = Path(output)

    import json

    with out_path.open() as fh:
        summary = json.load(fh)

    if as_json:
        typer.echo(json.dumps(summary))
        return

    typer.echo(f"Report written: {out_path}")

    # Print a quick summary to stdout
    typer.echo(f"\nRun ID  : {summary['run_id']}")
    typer.echo(f"Tasks   : {summary['task_count']}")
    typer.echo(f"Mean score : {summary['mean_aggregate_score']}")
    typer.echo(f"Hard fails : {summary['hard_fail_count']}")


@report_app.command("html")
def report_html(
    run_dir: Annotated[str, typer.Argument(help="Path to the run directory")],
) -> None:
    """Write a self-contained HTML report for a run directory."""
    from aobench.reports.html_report import write_html_report

    _require_completed_run(run_dir)

    out_path = write_html_report(run_dir)
    typer.echo(f"HTML report written: {out_path}")


@report_app.command("governance")
def report_governance(
    run_dir: Annotated[str, typer.Argument(help="Path to the run directory")],
    output: Annotated[
        str | None,
        typer.Option(
            "--output", "-o", help="Output file path (default: <run_dir>/governance_report.md)"
        ),
    ] = None,
    title: Annotated[str | None, typer.Option("--title", help="Report title override")] = None,
    no_baselines: Annotated[
        bool, typer.Option("--no-baselines", help="Omit paper baseline comparison rows")
    ] = False,
) -> None:
    """Write a Markdown governance profiler report for a run directory.

    Produces three sections: governance score + 95% CI, per-task tradeoff table,
    and plain-language interpretation. Suitable for sharing with HPC operators
    evaluating AI agent deployment. Use --no-langfuse for customer runs to keep
    RBAC policy data local.
    """
    from aobench.reports.governance_report import write_governance_report

    _require_completed_run(run_dir)

    out_path = write_governance_report(
        run_dir,
        output=output,
        title=title,
        include_baselines=not no_baselines,
    )
    typer.echo(f"Governance report written: {out_path}")


@report_app.command("slices")
def report_slices(
    run_dir: Annotated[str, typer.Argument(help="Path to the run directory")],
) -> None:
    """Print a role × category score table for a run."""
    from aobench.reports.json_report import build_run_summary
    from aobench.reports.slices import format_table_text, role_category_table

    _require_completed_run(run_dir)

    summary = build_run_summary(run_dir)
    table = role_category_table(summary)
    typer.echo(f"\nRole × Category scores  (run: {summary['run_id']})\n")
    typer.echo(format_table_text(table))
    typer.echo()
