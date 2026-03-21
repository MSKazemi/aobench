"""exabench compare — diff two benchmark run directories."""

from __future__ import annotations

from typing import Annotated

import typer

compare_app = typer.Typer(help="Compare two benchmark run directories.")

_DIMS = ["outcome", "tool_use", "grounding", "governance", "efficiency", "aggregate_score"]


def filter_tasks(rows: list[dict], qcat: str | None, role: str | None) -> list[dict]:
    if qcat:
        rows = [r for r in rows if r["task_id"].startswith(qcat + "_")]
    if role:
        rows = [r for r in rows if r.get("role") == role]
    return rows


@compare_app.command("runs")
def compare_runs(
    run_a: Annotated[str, typer.Argument(help="Baseline run directory (e.g. data/runs/run_…)")],
    run_b: Annotated[str, typer.Argument(help="Comparison run directory (e.g. data/runs/run_…)")],
    output: Annotated[str | None, typer.Option("--output", "-o", help="Write diff JSON to this path")] = None,
    delta_threshold: Annotated[float, typer.Option("--delta-threshold", help="Min |delta| to count as improved/regressed")] = 0.005,
    qcat: Annotated[str | None, typer.Option("--qcat", help="Filter to tasks in this QCAT only (e.g. JOB, PERF, MON)")] = None,
    role: Annotated[str | None, typer.Option("--role", help="Filter to tasks for this role only (e.g. sysadmin, scientific_user)")] = None,
    show_dims: Annotated[bool, typer.Option("--show-dims", help="Print per-dimension delta table")] = False,
    show_slices: Annotated[bool, typer.Option("--show-slices", help="Print role×QCAT slice comparison table")] = False,
    label_a: Annotated[str | None, typer.Option("--label-a", help="Label for run_a in output")] = None,
    label_b: Annotated[str | None, typer.Option("--label-b", help="Label for run_b in output")] = None,
) -> None:
    """Show score deltas between two runs (run_b minus run_a).

    Positive delta means run_b improved on that task; negative means regression.
    """
    import json
    from pathlib import Path

    from exabench.reports.json_report import build_run_summary
    from exabench.reports.slices import role_category_table

    summary_a = build_run_summary(run_a)
    summary_b = build_run_summary(run_b)

    label_a_str = label_a or summary_a["run_id"]
    label_b_str = label_b or summary_b["run_id"]

    # Apply filters to task lists before merging
    filtered_tasks_a = filter_tasks(summary_a["tasks"], qcat, role)
    filtered_tasks_b = filter_tasks(summary_b["tasks"], qcat, role)

    tasks_a = {t["task_id"]: t for t in filtered_tasks_a}
    tasks_b = {t["task_id"]: t for t in filtered_tasks_b}

    all_tasks = sorted(tasks_a.keys() | tasks_b.keys())

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
            elif delta > delta_threshold:
                status = "improved"
            elif delta < -delta_threshold:
                status = "regressed"
            else:
                status = "unchanged"

        dim_deltas = {}
        for d in _DIMS:
            va = ta.get(d) if ta else None
            vb = tb.get(d) if tb else None
            dim_deltas[d] = round(vb - va, 4) if (va is not None and vb is not None) else None

        # Hard-fail delta
        hard_fail_a = ta.get("hard_fail", False) if ta else False
        hard_fail_b = tb.get("hard_fail", False) if tb else False
        if not hard_fail_a and hard_fail_b:
            hard_fail_changed = "new_fail"
        elif hard_fail_a and not hard_fail_b:
            hard_fail_changed = "resolved"
        else:
            hard_fail_changed = None

        rows.append({
            "task_id": task_id,
            "role": (tb or ta or {}).get("role"),
            "status": status,
            "hard_fail_changed": hard_fail_changed,
            "score_a": ta.get("aggregate_score") if ta else None,
            "score_b": tb.get("aggregate_score") if tb else None,
            "delta": dim_deltas.get("aggregate_score"),
            "dim_deltas": dim_deltas,
        })

    # Compute aggregates
    scores_a = [r["score_a"] for r in rows if r["score_a"] is not None]
    scores_b = [r["score_b"] for r in rows if r["score_b"] is not None]
    mean_a = round(sum(scores_a) / len(scores_a), 4) if scores_a else None
    mean_b = round(sum(scores_b) / len(scores_b), 4) if scores_b else None
    mean_delta = round(mean_b - mean_a, 4) if (mean_a is not None and mean_b is not None) else None
    delta_str = f"{mean_delta:+.4f}" if mean_delta is not None else "n/a"

    improved = sum(1 for r in rows if r["status"] == "improved")
    regressed = sum(1 for r in rows if r["status"] == "regressed")
    unchanged = sum(1 for r in rows if r["status"] == "unchanged")
    new_tasks = sum(1 for r in rows if r["status"] == "new")
    removed_tasks = sum(1 for r in rows if r["status"] == "removed")
    new_hard_fails = sum(1 for r in rows if r["hard_fail_changed"] == "new_fail")
    resolved_hard_fails = sum(1 for r in rows if r["hard_fail_changed"] == "resolved")

    hard_fail_count_a = sum(1 for t in filtered_tasks_a if t.get("hard_fail"))
    hard_fail_count_b = sum(1 for t in filtered_tasks_b if t.get("hard_fail"))

    # Print header
    typer.echo(f"\nBaseline : {label_a_str}")
    typer.echo(f"Compare  : {label_b_str}")
    filter_parts = []
    if qcat:
        filter_parts.append(f"QCAT={qcat}")
    if role:
        filter_parts.append(f"Role={role}")
    if filter_parts:
        typer.echo(f"Filter   : {('  '.join(filter_parts))}")
    typer.echo(f"Threshold: {delta_threshold}")
    typer.echo(f"\nMean score: {mean_a} → {mean_b}  ({delta_str})")
    typer.echo(f"Hard-fail count: {hard_fail_count_a} → {hard_fail_count_b}  ({resolved_hard_fails} resolved, {new_hard_fails} new)\n")

    # Print per-task table
    typer.echo(f"{'Task':<20} {'Status':<14} {'Score A':>8} {'Score B':>8} {'Delta':>8}")
    typer.echo("-" * 62)
    for r in rows:
        status_sym = {"improved": "▲", "regressed": "▼", "unchanged": "=", "new": "+", "removed": "-"}.get(r["status"], "?")
        warn = "⚠" if r["hard_fail_changed"] == "new_fail" else " "
        sa = f"{r['score_a']:.4f}" if r["score_a"] is not None else "  n/a "
        sb = f"{r['score_b']:.4f}" if r["score_b"] is not None else "  n/a "
        d = f"{r['delta']:+.4f}" if r["delta"] is not None else "  n/a "
        status_col = f"{warn}{status_sym} {r['status']}"
        typer.echo(f"{r['task_id']:<20} {status_col:<14} {sa:>8} {sb:>8} {d:>8}")

    typer.echo(f"\nImproved: {improved}   Regressed: {regressed}   Unchanged: {unchanged}")
    if new_hard_fails:
        typer.echo(f"New hard-fails (RBAC violations): {new_hard_fails} task(s) — review governance_scorer output")

    # --show-dims table
    if show_dims:
        dim_cols = ["outcome", "tool_use", "grounding", "governance", "efficiency", "robustness"]
        col_w = 12
        header = f"\n{'Per-dimension deltas (run_b − run_a):'}"
        typer.echo(header)
        typer.echo(f"{'Task':<20}" + "".join(f"{d:>{col_w}}" for d in dim_cols))
        typer.echo("-" * (20 + col_w * len(dim_cols)))
        for r in rows:
            if r["status"] in ("new", "removed"):
                continue
            row_str = f"{r['task_id']:<20}"
            for d in dim_cols:
                v = r["dim_deltas"].get(d)
                if v is None:
                    cell = "n/a"
                else:
                    warn = "⚠" if (d == "governance" and r["hard_fail_changed"] == "new_fail") else ""
                    cell = f"{warn}{v:+.3f}"
                row_str += f"{cell:>{col_w}}"
            typer.echo(row_str)

    # --show-slices table
    if show_slices:
        slices_a = role_category_table({"tasks": filtered_tasks_a})
        slices_b = role_category_table({"tasks": filtered_tasks_b})

        all_roles = sorted(slices_a.keys() | slices_b.keys())
        all_qcats = sorted(
            {q for cats in slices_a.values() for q in cats}
            | {q for cats in slices_b.values() for q in cats}
        )

        col_w = 18
        typer.echo(f"\nRole × QCAT mean score comparison (run_b − run_a):")
        typer.echo(f"{'':20}" + "".join(f"{q:>{col_w}}" for q in all_qcats))
        typer.echo("-" * (20 + col_w * len(all_qcats)))
        for r_role in all_roles:
            row_str = f"{r_role:<20}"
            for r_qcat in all_qcats:
                cell_a = slices_a.get(r_role, {}).get(r_qcat)
                cell_b = slices_b.get(r_role, {}).get(r_qcat)
                if cell_a and cell_b:
                    d = round(cell_b["mean_score"] - cell_a["mean_score"], 3)
                    n = cell_b["count"]
                    cell = f"{d:+.3f} (n={n})"
                else:
                    cell = "n/a"
                row_str += f"{cell:>{col_w}}"
            typer.echo(row_str)

    # Build slices for JSON (always)
    slices_a_json = role_category_table({"tasks": filtered_tasks_a})
    slices_b_json = role_category_table({"tasks": filtered_tasks_b})

    if output:
        result = {
            "run_a": label_a_str,
            "run_b": label_b_str,
            "mean_score_a": mean_a,
            "mean_score_b": mean_b,
            "mean_delta": mean_delta,
            "filter_qcat": qcat,
            "filter_role": role,
            "delta_threshold": delta_threshold,
            "task_count_a": len(filtered_tasks_a),
            "task_count_b": len(filtered_tasks_b),
            "tasks": rows,
            "summary": {
                "improved": improved,
                "regressed": regressed,
                "unchanged": unchanged,
                "new": new_tasks,
                "removed": removed_tasks,
                "new_hard_fails": new_hard_fails,
                "resolved_hard_fails": resolved_hard_fails,
            },
            "slices_a": slices_a_json,
            "slices_b": slices_b_json,
        }
        from pathlib import Path
        Path(output).write_text(json.dumps(result, indent=2))
        typer.echo(f"\nDiff written: {output}")
