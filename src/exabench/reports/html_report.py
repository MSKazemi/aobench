"""HTML report — generates a self-contained HTML benchmark summary from a run directory."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from exabench.reports.json_report import build_run_summary
from exabench.reports.slices import role_category_table


def _score_colour(score: float | None) -> str:
    """Return a CSS colour class based on score value."""
    if score is None:
        return "score-na"
    if score >= 0.75:
        return "score-high"
    if score >= 0.50:
        return "score-mid"
    return "score-low"


def _fmt(val: float | None) -> str:
    if val is None:
        return "—"
    return f"{val:.3f}"


def _task_rows(tasks: list[dict[str, Any]]) -> str:
    rows = []
    for t in tasks:
        agg = t.get("aggregate_score")
        cls = _score_colour(agg)
        hard_fail = "✗" if t.get("hard_fail") else ""
        rows.append(
            f"<tr class='{cls}'>"
            f"<td>{t['task_id']}</td>"
            f"<td>{t['role']}</td>"
            f"<td>{t['environment_id']}</td>"
            f"<td>{t['adapter_name']}</td>"
            f"<td class='num'>{_fmt(t.get('outcome'))}</td>"
            f"<td class='num'>{_fmt(t.get('tool_use'))}</td>"
            f"<td class='num'>{_fmt(t.get('grounding'))}</td>"
            f"<td class='num'>{_fmt(t.get('governance'))}</td>"
            f"<td class='num'>{_fmt(t.get('efficiency'))}</td>"
            f"<td class='num agg'>{_fmt(agg)}</td>"
            f"<td class='fail'>{hard_fail}</td>"
            f"</tr>"
        )
    return "\n".join(rows)


def _slice_table(table: dict[str, dict[str, Any]]) -> str:
    if not table:
        return "<p>No slice data.</p>"
    all_qcats = sorted({q for cats in table.values() for q in cats})
    header = "<tr><th>Role</th>" + "".join(f"<th>{q}</th>" for q in all_qcats) + "</tr>"
    rows = []
    for role, cats in sorted(table.items()):
        cells = f"<tr><td><strong>{role}</strong></td>"
        for qcat in all_qcats:
            if qcat in cats:
                s = cats[qcat]["mean_score"]
                cls = _score_colour(s)
                cells += f"<td class='num {cls}'>{s:.3f}<br><small>n={cats[qcat]['count']}</small></td>"
            else:
                cells += "<td class='num score-na'>—</td>"
        cells += "</tr>"
        rows.append(cells)
    return f"<table class='slice-table'><thead>{header}</thead><tbody>{''.join(rows)}</tbody></table>"


def build_html_report(run_dir: str | Path) -> str:
    """Return a self-contained HTML string summarising the run."""
    run_dir = Path(run_dir)
    summary = build_run_summary(run_dir)
    table = role_category_table(summary)

    run_id = summary["run_id"]
    n_tasks = summary["task_count"]
    mean = _fmt(summary.get("mean_aggregate_score"))
    hard_fails = summary["hard_fail_count"]

    task_rows_html = _task_rows(summary["tasks"])
    slice_html = _slice_table(table)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ExaBench Report — {run_id}</title>
<style>
  body {{ font-family: system-ui, sans-serif; margin: 2rem; color: #222; background: #fafafa; }}
  h1 {{ color: #1a1a2e; }}
  h2 {{ color: #16213e; border-bottom: 2px solid #e0e0e0; padding-bottom: .3rem; margin-top: 2rem; }}
  .meta {{ display: flex; gap: 2rem; flex-wrap: wrap; margin: 1rem 0 2rem; }}
  .meta-card {{ background: #fff; border: 1px solid #ddd; border-radius: 6px; padding: .8rem 1.4rem; min-width: 120px; }}
  .meta-card .label {{ font-size: .75rem; color: #888; text-transform: uppercase; letter-spacing: .05em; }}
  .meta-card .value {{ font-size: 1.6rem; font-weight: 700; color: #1a1a2e; }}
  table {{ border-collapse: collapse; width: 100%; background: #fff; border-radius: 6px; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,.08); }}
  th {{ background: #1a1a2e; color: #fff; padding: .5rem .8rem; text-align: left; font-size: .8rem; }}
  td {{ padding: .45rem .8rem; border-bottom: 1px solid #f0f0f0; font-size: .85rem; }}
  tr:last-child td {{ border-bottom: none; }}
  .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  .agg {{ font-weight: 700; }}
  .fail {{ text-align: center; color: #c00; font-weight: bold; }}
  .score-high td, tr.score-high {{ background: #f0fff4; }}
  .score-mid td, tr.score-mid {{ background: #fffbf0; }}
  .score-low td, tr.score-low {{ background: #fff5f5; }}
  .score-na {{ color: #aaa; }}
  .score-high.num {{ color: #2d6a4f; }}
  .score-mid.num {{ color: #b7791f; }}
  .score-low.num {{ color: #c53030; }}
  .slice-table th {{ font-size: .85rem; }}
  .slice-table td small {{ color: #888; font-size: .75rem; }}
  footer {{ margin-top: 3rem; font-size: .75rem; color: #aaa; text-align: center; }}
</style>
</head>
<body>
<h1>ExaBench Benchmark Report</h1>
<p style="color:#666">Run ID: <code>{run_id}</code></p>

<div class="meta">
  <div class="meta-card"><div class="label">Tasks</div><div class="value">{n_tasks}</div></div>
  <div class="meta-card"><div class="label">Mean Score</div><div class="value">{mean}</div></div>
  <div class="meta-card"><div class="label">Hard Fails</div><div class="value" style="color:{'#c00' if hard_fails else '#2d6a4f'}">{hard_fails}</div></div>
</div>

<h2>Role × Category</h2>
{slice_html}

<h2>Per-Task Scores</h2>
<table>
<thead>
<tr>
  <th>Task</th><th>Role</th><th>Env</th><th>Adapter</th>
  <th>Outcome</th><th>Tool Use</th><th>Grounding</th><th>Governance</th><th>Efficiency</th>
  <th>Aggregate</th><th>Fail</th>
</tr>
</thead>
<tbody>
{task_rows_html}
</tbody>
</table>

<footer>Generated by ExaBench &mdash; <a href="https://github.com/MSKazemi/ExaBench">github.com/MSKazemi/ExaBench</a></footer>
</body>
</html>
"""


def write_html_report(run_dir: str | Path) -> Path:
    """Write ``report.html`` into *run_dir* and return its path."""
    run_dir = Path(run_dir)
    html = build_html_report(run_dir)
    out = run_dir / "report.html"
    out.write_text(html, encoding="utf-8")
    return out
