"""make_paper_table1.py — Table 1: main results for the v0.1 paper.

Input:
  data/runs/v01_dev_gpt4o/run_20260321_192110_d2854175/run_summary.json
  data/runs/v01_smoke_direct_qa/<latest>/run_summary.json

Output: Markdown + LaTeX table with per-model dimension scores.
"""

import json
import pathlib
import statistics

RUN_DIRS = [
    ("GPT-4o",    pathlib.Path("data/runs/v01_dev_gpt4o/run_20260321_192110_d2854175")),
    ("direct_qa", sorted(pathlib.Path("data/runs/v01_smoke_direct_qa").iterdir())[-1]),
]

DIMS        = ["aggregate_score", "outcome", "tool_use", "governance", "efficiency", "grounding"]
DIM_HEADERS = ["Aggregate", "Outcome", "Tool Use", "Governance", "Efficiency", "Grounding"]


def load_row(label: str, run_dir: pathlib.Path) -> dict:
    summary = json.loads((run_dir / "run_summary.json").read_text())
    tasks = summary["tasks"]
    row = {"label": label}
    for dim in DIMS:
        vals = [t[dim] for t in tasks if t.get(dim) is not None]
        row[dim] = statistics.mean(vals) if vals else None
    rob_vals = [t["robustness"] for t in tasks if t.get("robustness") is not None]
    row["robustness"] = statistics.mean(rob_vals) if rob_vals else None
    return row


def fmt(v) -> str:
    return f"{v:.3f}" if v is not None else "—"


rows = [load_row(label, path) for label, path in RUN_DIRS]
all_dims = DIMS + ["robustness"]
all_headers = DIM_HEADERS + ["Robustness"]

# ── Markdown ────────────────────────────────────────────────────────────────
header = "| Model | " + " | ".join(all_headers) + " |"
sep    = "|" + "|".join(["---"] * (len(all_headers) + 1)) + "|"

print("## Table 1 — Main Results (dev set, 21 tasks)\n")
print(header)
print(sep)
for r in rows:
    cells = [fmt(r[d]) for d in all_dims]
    print(f"| {r['label']} | " + " | ".join(cells) + " |")

# ── LaTeX ────────────────────────────────────────────────────────────────────
cols = "l" + "r" * len(all_headers)
print("\n\n## LaTeX\n")
print(r"\begin{table}[t]")
print(r"\centering")
print(r"\caption{Main results on the ExaBench v0.1 dev set (21 tasks).}")
print(r"\label{tab:main_results}")
print(f"\\begin{{tabular}}{{{cols}}}")
print(r"\toprule")
print("Model & " + " & ".join(all_headers) + r" \\")
print(r"\midrule")
for r in rows:
    cells = [r["label"]] + [fmt(r[d]) for d in all_dims]
    print(" & ".join(cells) + r" \\")
print(r"\bottomrule")
print(r"\end{tabular}")
print(r"\end{table}")
