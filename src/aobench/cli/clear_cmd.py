"""aobench clear — compute CLEAR scorecard across run directories.

CLEAR = Cost / Latency / Efficacy / Assurance / Reliability
Source: Mehta (2025), arXiv:2511.14136
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

clear_app = typer.Typer(
    help="Compute CLEAR (Cost/Latency/Efficacy/Assurance/Reliability) scorecard.",
)


@clear_app.command()
def run(  # noqa: A001
    run_dirs: Annotated[
        list[str],
        typer.Option(
            "--run-dir",
            "-d",
            help="Run directory containing results/ (repeat for multiple models).",
        ),
    ],
    output: Annotated[
        str,
        typer.Option("--output", "-o", help="Write CLEAR report to this JSON file"),
    ] = "clear_report.json",
    pass_threshold: Annotated[
        float,
        typer.Option("--pass-threshold", help="Min aggregate_score to count as passing"),
    ] = 0.5,
    reliability_k: Annotated[
        int,
        typer.Option("--reliability-k", help="k for pass^k reliability (1, 2, 4, 8)"),
    ] = 1,
    robustness_json: Annotated[
        str | None,
        typer.Option(
            "--robustness-json",
            help="Optional: robustness_suite.json for pass^k > 1",
        ),
    ] = None,
) -> None:
    """Compute CLEAR scorecard across one or more run directories.

    Each --run-dir is a benchmark run output (contains results/).
    Runs are grouped by model_name (from result.model_name).

    Example workflow:

    \\b
        aobench run all --adapter openai:gpt-4o
        aobench robustness all --adapter openai:gpt-4o --n 8 \\
            --output data/robustness_gpt4o.json
        aobench clear run \\
            --run-dir data/runs/run_20260319/ \\
            --robustness-json data/robustness_gpt4o.json \\
            --reliability-k 8 \\
            --output data/clear_report.json

    Multi-model comparison:

    \\b
        aobench clear run \\
            --run-dir data/runs/run_gpt4o/ \\
            --run-dir data/runs/run_claude/ \\
            --output data/clear_report.json
    """
    from collections import defaultdict  # noqa: PLC0415

    from aobench.reports.clear_report import build_clear_report  # noqa: PLC0415
    from aobench.schemas.result import BenchmarkResult  # noqa: PLC0415

    # ── Load results from all run directories ──────────────────────────────────
    model_results: dict[str, list[BenchmarkResult]] = defaultdict(list)
    total_loaded = 0

    for run_dir_str in run_dirs:
        run_dir = Path(run_dir_str)
        results_dir = run_dir / "results"
        if not results_dir.exists():
            typer.echo(f"Warning: no results/ directory in {run_dir}", err=True)
            continue

        result_files = sorted(results_dir.glob("*_result.json"))
        if not result_files:
            typer.echo(f"Warning: no *_result.json files in {results_dir}", err=True)
            continue

        for f in result_files:
            result = BenchmarkResult.model_validate(
                json.loads(f.read_text(encoding="utf-8"))
            )
            key = result.model_name or result.adapter_name
            model_results[key].append(result)
            total_loaded += 1

    if not model_results:
        typer.echo("No results loaded. Check the --run-dir paths.", err=True)
        raise typer.Exit(1)

    typer.echo(
        f"\nLoaded {total_loaded} result(s) across {len(model_results)} model(s)."
    )

    # ── Load optional robustness data ──────────────────────────────────────────
    robustness_by_model: dict[str, dict] | None = None
    if robustness_json:
        rob_path = Path(robustness_json)
        if not rob_path.exists():
            typer.echo(f"Error: robustness file not found: {rob_path}", err=True)
            raise typer.Exit(1)
        rob_data = json.loads(rob_path.read_text(encoding="utf-8"))
        # Apply to all models (single-model workflow; for multi-model, re-run per adapter)
        robustness_by_model = {m: rob_data for m in model_results}
        typer.echo(f"Loaded robustness data from: {rob_path}")

    # ── Build CLEAR report ─────────────────────────────────────────────────────
    report = build_clear_report(
        model_results=dict(model_results),
        reliability_k=reliability_k,
        pass_threshold=pass_threshold,
        robustness_by_model=robustness_by_model,
    )

    # ── Print summary table ────────────────────────────────────────────────────
    _print_clear_table(report)

    # ── Write JSON ─────────────────────────────────────────────────────────────
    out_path = Path(output)
    out_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    typer.echo(f"CLEAR report written: {out_path}")


def _print_clear_table(report: dict) -> None:
    """Print CLEAR scorecard table to stdout."""
    models = report.get("models", {})
    if not models:
        return

    header = (
        f"\n{'Model':<22} {'CLEAR':>6}  {'E':>6}  {'A':>6}  {'R':>6}"
        f"  {'C_norm':>6}  {'L_norm':>6}  {'CNA':>9}  {'CPS($)':>9}"
    )
    sep = "─" * (len(header) - 1)  # -1 for leading \n
    typer.echo(header)
    typer.echo(sep)

    sorted_models = sorted(
        models.items(),
        key=lambda x: (x[1]["clear_score"] is None, -(x[1]["clear_score"] or 0.0)),
    )

    def _fmt(v: float | None, d: int = 3) -> str:
        return f"{v:.{d}f}" if v is not None else "N/A"

    for model, s in sorted_models:
        row = (
            f"{model[:22]:<22} "
            f"{_fmt(s['clear_score']):>6}  "
            f"{_fmt(s['E']):>6}  "
            f"{_fmt(s['A']):>6}  "
            f"{_fmt(s['R']):>6}  "
            f"{_fmt(s['C_norm']):>6}  "
            f"{_fmt(s['L_norm']):>6}  "
            f"{_fmt(s['CNA'], 1):>9}  "
            f"{_fmt(s['CPS'], 4):>9}"
        )
        typer.echo(row)

    typer.echo()
    typer.echo(
        f"Tasks: {report['task_count']}  "
        f"pass_threshold: {report['pass_threshold']}  "
        f"reliability_k: {report['reliability_k']}"
    )
