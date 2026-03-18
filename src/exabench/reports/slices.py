"""Slices — role × category score tables from a run summary."""

from __future__ import annotations

from typing import Any


def role_category_table(summary: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return a nested dict: role → qcat → {mean_score, count, hard_fails}.

    *summary* is the dict produced by :func:`~exabench.reports.json_report.build_run_summary`.
    The qcat is inferred from the task_id prefix (e.g. ``JOB_USR_001`` → ``JOB``).
    """
    from collections import defaultdict

    # {role: {qcat: [scores]}}
    buckets: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    fails: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for row in summary.get("tasks", []):
        role = row.get("role", "unknown")
        task_id = row.get("task_id", "")
        qcat = task_id.split("_")[0] if task_id else "unknown"
        score = row.get("aggregate_score")
        if score is not None:
            buckets[role][qcat].append(score)
        if row.get("hard_fail"):
            fails[role][qcat] += 1

    table: dict[str, dict[str, Any]] = {}
    for role, cats in sorted(buckets.items()):
        table[role] = {}
        for qcat, scores in sorted(cats.items()):
            table[role][qcat] = {
                "mean_score": round(sum(scores) / len(scores), 4),
                "count": len(scores),
                "hard_fails": fails[role][qcat],
            }
    return table


def format_table_text(table: dict[str, dict[str, Any]]) -> str:
    """Render the role × category table as plain text for CLI output."""
    if not table:
        return "(no results)"

    # Collect all qcats
    all_qcats = sorted({qcat for cats in table.values() for qcat in cats})
    col_width = 14
    header = f"{'Role':<20}" + "".join(f"{q:>{col_width}}" for q in all_qcats)
    sep = "-" * len(header)
    lines = [header, sep]
    for role, cats in sorted(table.items()):
        row = f"{role:<20}"
        for qcat in all_qcats:
            if qcat in cats:
                cell = f"{cats[qcat]['mean_score']:.3f} (n={cats[qcat]['count']})"
            else:
                cell = "-"
            row += f"{cell:>{col_width}}"
        lines.append(row)
    return "\n".join(lines)
