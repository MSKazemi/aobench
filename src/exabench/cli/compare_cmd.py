"""exabench compare — diff two benchmark run directories."""

from __future__ import annotations

from typing import Annotated

import typer

compare_app = typer.Typer(help="Compare two benchmark run directories.")


@compare_app.command("runs")
def compare_runs(
    run_a: Annotated[str, typer.Argument(help="Baseline run directory (e.g. data/runs/run_…)")],
    run_b: Annotated[str, typer.Argument(help="Comparison run directory (e.g. data/runs/run_…)")],
    output: Annotated[str | None, typer.Option("--output", "-o", help="Write diff JSON to this path")] = None,
) -> None:
    """Show score deltas between two runs (run_b minus run_a).

    Positive delta means run_b improved on that task; negative means regression.
    """
    import json
    from pathlib import Path

    from exabench.reports.json_report import build_run_summary

    summary_a = build_run_summary(run_a)
    summary_b = build_run_summary(run_b)

    tasks_a = {t["task_id"]: t for t in summary_a["tasks"]}
    tasks_b = {t["task_id"]: t for t in summary_b["tasks"]}

    all_tasks = sorted(tasks_a.keys() | tasks_b.keys())
    dims = ["outcome", "tool_use", "grounding", "governance", "efficiency", "aggregate_score"]

    rows = []
    for task_id in all_tasks:
        ta = tasks_a.get(task_id)
        tb = tasks_b.get(task_id)
        if ta is None:
            status = "new"
        elif tb is None:
            status = "removed"
        else:
            agg_a = ta.get("aggregate_score")
            agg_b = tb.get("aggregate_score")
            delta = round(agg_b - agg_a, 4) if (agg_a is not None and agg_b is not None) else None
            if delta is None:
                status = "unknown"
            elif delta > 0.005:
                status = "improved"
            elif delta < -0.005:
                status = "regressed"
            else:
                status = "unchanged"

        dim_deltas = {}
        for d in dims:
            va = ta.get(d) if ta else None
            vb = tb.get(d) if tb else None
            dim_deltas[d] = round(vb - va, 4) if (va is not None and vb is not None) else None

        rows.append({
            "task_id": task_id,
            "status": status,
            "score_a": ta.get("aggregate_score") if ta else None,
            "score_b": tb.get("aggregate_score") if tb else None,
            "delta": dim_deltas.get("aggregate_score"),
            "dim_deltas": dim_deltas,
        })

    # Print table
    mean_a = summary_a.get("mean_aggregate_score")
    mean_b = summary_b.get("mean_aggregate_score")
    mean_delta = round(mean_b - mean_a, 4) if (mean_a is not None and mean_b is not None) else None
    delta_str = f"{mean_delta:+.4f}" if mean_delta is not None else "n/a"

    typer.echo(f"\nBaseline : {summary_a['run_id']}")
    typer.echo(f"Compare  : {summary_b['run_id']}")
    typer.echo(f"Mean score: {mean_a} → {mean_b}  ({delta_str})\n")

    col = 20
    typer.echo(f"{'Task':<20} {'Status':<12} {'Score A':>8} {'Score B':>8} {'Delta':>8}")
    typer.echo("-" * 60)
    for r in rows:
        status_sym = {"improved": "▲", "regressed": "▼", "unchanged": "=", "new": "+", "removed": "-"}.get(r["status"], "?")
        sa = f"{r['score_a']:.4f}" if r["score_a"] is not None else "  n/a "
        sb = f"{r['score_b']:.4f}" if r["score_b"] is not None else "  n/a "
        delta = f"{r['delta']:+.4f}" if r["delta"] is not None else "  n/a "
        typer.echo(f"{r['task_id']:<20} {status_sym} {r['status']:<10} {sa:>8} {sb:>8} {delta:>8}")

    improved = sum(1 for r in rows if r["status"] == "improved")
    regressed = sum(1 for r in rows if r["status"] == "regressed")
    typer.echo(f"\nImproved: {improved}  Regressed: {regressed}  Unchanged: {len(rows) - improved - regressed}")

    if output:
        result = {
            "run_a": summary_a["run_id"],
            "run_b": summary_b["run_id"],
            "mean_score_a": mean_a,
            "mean_score_b": mean_b,
            "mean_delta": mean_delta,
            "tasks": rows,
        }
        Path(output).write_text(json.dumps(result, indent=2))
        typer.echo(f"\nDiff written: {output}")
