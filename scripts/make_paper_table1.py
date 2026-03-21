"""make_paper_table1.py — Generate Table 1 (main results) for the v0.1 paper.

Input:  data/runs/v01_dev_*/run_summary.json  (one per model)
Output: Markdown table + LaTeX snippet to stdout (or --output file)

Usage:
    python3 scripts/make_paper_table1.py
    python3 scripts/make_paper_table1.py --output paper/table1.md
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


# ── Defaults ──────────────────────────────────────────────────────────────────

DEFAULT_RUN_DIRS = [
    "data/runs/v01_dev_claude_sonnet",
    "data/runs/v01_dev_gpt4o",
    "data/runs/v01_dev_gpt4o_mini",
]

MODEL_LABELS: dict[str, str] = {
    "claude-sonnet-4-6": "Claude-Sonnet-4.6",
    "gpt-4o": "GPT-4o",
    "gpt-4o-mini": "GPT-4o-mini",
    "direct_qa": "Direct-QA (baseline)",
}

DIMS = ["aggregate_score", "outcome", "tool_use", "governance", "efficiency", "grounding"]
DIM_HEADERS = ["Aggregate", "Outcome", "Tool Use", "Governance", "Efficiency", "Grounding"]


# ── Helpers ───────────────────────────────────────────────────────────────────

def find_summary(run_dir: str) -> Path | None:
    """Return the run_summary.json inside run_dir (looks one level deep)."""
    base = Path(run_dir)
    # Direct: run_dir/run_summary.json
    direct = base / "run_summary.json"
    if direct.exists():
        return direct
    # Nested: run_dir/<run_id>/run_summary.json
    for child in sorted(base.iterdir()):
        candidate = child / "run_summary.json"
        if candidate.exists():
            return candidate
    return None


def load_summary(run_dir: str) -> dict:
    path = find_summary(run_dir)
    if path is None:
        raise FileNotFoundError(f"No run_summary.json found in {run_dir}")
    return json.loads(path.read_text(encoding="utf-8"))


def mean_dim(tasks: list[dict], dim: str) -> float | None:
    vals = [t.get(dim) for t in tasks if t.get(dim) is not None]
    if not vals:
        return None
    return round(sum(vals) / len(vals), 4)


def label_for_summary(summary: dict) -> str:
    model = summary.get("model_name") or summary.get("adapter_name") or "unknown"
    return MODEL_LABELS.get(model, model)


# ── Markdown ──────────────────────────────────────────────────────────────────

def make_markdown_table(rows: list[dict]) -> str:
    col_w = [max(len(h), 6) for h in ["Model"] + DIM_HEADERS]
    header = "| " + " | ".join(
        ["Model"] + [h.ljust(col_w[i + 1]) for i, h in enumerate(DIM_HEADERS)]
    ) + " |"
    sep = "|-" + "-|-".join(["-" * w for w in col_w]) + "-|"
    lines = [header, sep]
    for row in rows:
        cells = [row["label"].ljust(col_w[0])]
        for i, dim in enumerate(DIMS):
            v = row.get(dim)
            cell = f"{v:.4f}" if v is not None else "N/A"
            cells.append(cell.ljust(col_w[i + 1]))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


# ── LaTeX ─────────────────────────────────────────────────────────────────────

def make_latex_table(rows: list[dict]) -> str:
    cols = "l" + "r" * len(DIMS)
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Main results on the ExaBench v0.1 dev set (21 tasks).}",
        r"\label{tab:main_results}",
        r"\begin{tabular}{" + cols + r"}",
        r"\toprule",
        "Model & " + " & ".join(DIM_HEADERS) + r" \\",
        r"\midrule",
    ]
    for row in rows:
        cells = [row["label"]]
        for dim in DIMS:
            v = row.get(dim)
            cells.append(f"{v:.4f}" if v is not None else "--")
        lines.append(" & ".join(cells) + r" \\")
    lines += [
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ]
    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "run_dirs",
        nargs="*",
        default=DEFAULT_RUN_DIRS,
        help="Run directories containing run_summary.json (default: v01_dev_*)",
    )
    parser.add_argument("--output", "-o", default="-", help="Output file (default: stdout)")
    args = parser.parse_args(argv)

    rows = []
    for run_dir in args.run_dirs:
        try:
            summary = load_summary(run_dir)
        except FileNotFoundError as e:
            print(f"Warning: {e}", file=sys.stderr)
            continue

        tasks = summary.get("tasks", [])
        row: dict = {"label": label_for_summary(summary), "run_dir": run_dir}
        for dim in DIMS:
            row[dim] = mean_dim(tasks, dim) if dim != "aggregate_score" else summary.get("mean_aggregate_score")
        rows.append(row)

    if not rows:
        print("Error: no run summaries loaded.", file=sys.stderr)
        return 1

    # Sort by aggregate score descending
    rows.sort(key=lambda r: r.get("aggregate_score") or 0.0, reverse=True)

    output_lines = [
        "# Table 1 — Main Results",
        f"Dev set: 21 tasks  |  Models: {len(rows)}",
        "",
        "## Markdown",
        "",
        make_markdown_table(rows),
        "",
        "## LaTeX",
        "",
        make_latex_table(rows),
        "",
        "## Raw values",
        "",
    ]
    for row in rows:
        output_lines.append(f"  {row['label']}: {row}")

    text = "\n".join(output_lines) + "\n"

    if args.output == "-":
        print(text)
    else:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"Written: {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
