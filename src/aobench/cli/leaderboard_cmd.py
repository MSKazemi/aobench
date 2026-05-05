"""aobench leaderboard — Build leaderboard from benchmark result files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

leaderboard_app = typer.Typer(
    help="Build and export leaderboard tables from benchmark results.",
    no_args_is_help=True,
)


@leaderboard_app.command("build")
def build(
    results_dir: Path = typer.Argument(
        ...,
        help="Root directory whose subdirectories are per-model result folders.",
    ),
    output_dir: Optional[Path] = typer.Option(
        None,
        help="Output directory (default: RESULTS_DIR/leaderboard/).",
    ),
    reliability_k: int = typer.Option(8, help="k for pass^k reliability column."),
    pass_threshold: float = typer.Option(0.5, help="Minimum score counted as a pass."),
    no_heatmap: bool = typer.Option(False, help="Skip writing the heatmap CSV."),
    fmt: str = typer.Option(
        "all",
        "--format",
        help="Output format: json, csv, or all (default: all).",
    ),
    append: Optional[Path] = typer.Option(
        None,
        help="Merge results into an existing leaderboard JSON before writing.",
    ),
) -> None:
    """Build a CLEAR leaderboard from per-model result JSON files.

    \b
    Reads:   RESULTS_DIR/<model_name>/<task_id>_result.json
    Writes:  OUTPUT_DIR/leaderboard.json  (--format json or all)
             OUTPUT_DIR/leaderboard.csv   (--format csv or all)
             OUTPUT_DIR/heatmap.csv       (unless --no-heatmap)
    """
    from aobench.reports.leaderboard import (
        load_results_dir,
        write_heatmap_csv,
        write_leaderboard_csv,
    )
    from aobench.reports.clear_report import build_clear_report, write_clear_report

    if not results_dir.exists():
        typer.echo(f"ERROR: results directory not found: {results_dir}", err=True)
        raise typer.Exit(code=1)

    out_dir = output_dir or results_dir / "leaderboard"
    out_dir.mkdir(parents=True, exist_ok=True)

    typer.echo(f"Loading results from {results_dir} ...")
    model_results = load_results_dir(results_dir)
    if not model_results:
        typer.echo("WARNING: no BenchmarkResult files found.", err=True)
        raise typer.Exit(code=1)

    total = sum(len(v) for v in model_results.values())
    typer.echo(f"  Loaded {total} results across {len(model_results)} model(s).")

    # Optionally merge an existing leaderboard JSON
    existing_report: dict | None = None
    if append and append.exists():
        try:
            existing_report = json.loads(append.read_text(encoding="utf-8"))
            typer.echo(f"  Merging with existing leaderboard: {append}")
        except Exception as exc:
            typer.echo(f"WARNING: could not read --append file: {exc}", err=True)

    typer.echo("Building CLEAR report ...")
    report = build_clear_report(
        model_results,
        reliability_k=reliability_k,
        pass_threshold=pass_threshold,
    )

    if existing_report:
        existing_models = {e["model"] for e in existing_report.get("leaderboard", [])}
        new_entries = [e for e in report["leaderboard"] if e["model"] not in existing_models]
        report["leaderboard"] = existing_report.get("leaderboard", []) + new_entries
        for m, s in report.get("models", {}).items():
            existing_report.setdefault("models", {})[m] = s
        report["models"] = existing_report["models"]

    if fmt in ("json", "all"):
        json_path = out_dir / "leaderboard.json"
        json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        typer.echo(f"  Wrote {json_path}")

    if fmt in ("csv", "all"):
        csv_path = out_dir / "leaderboard.csv"
        write_leaderboard_csv(report, csv_path, model_results=model_results,
                              pass_threshold=pass_threshold)
        typer.echo(f"  Wrote {csv_path}")

    if not no_heatmap:
        heatmap_path = out_dir / "heatmap.csv"
        write_heatmap_csv(
            model_results,
            heatmap_path,
            pass_threshold=pass_threshold,
        )
        typer.echo(f"  Wrote {heatmap_path}")

    # Summary
    typer.echo("\nLeaderboard:")
    for entry in report.get("leaderboard", []):
        score = entry.get("clear_score")
        score_str = f"{score:.4f}" if score is not None else "n/a"
        typer.echo(f"  {entry['rank']:2}. {entry['model']:40} CLEAR={score_str}")
