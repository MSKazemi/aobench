"""make_paper_table1.py — Table 1: main results for the v0.2 paper.

Input:  data/runs/v02_dev/<model>/run_*/results/*.json
Output: Markdown + LaTeX table with per-model dimension scores.
"""

import json
import pathlib
import statistics

V02_BASE = pathlib.Path("data/runs/v02_dev")

MODEL_ORDER = ["gpt-4o", "gpt-4o-mini", "direct_qa"]
MODEL_LABELS = {
    "gpt-4o":      "GPT-4o",
    "gpt-4o-mini": "GPT-4o-mini",
    "direct_qa":   "Direct QA (baseline)",
}

DIMS        = ["aggregate_score", "outcome", "tool_use", "governance", "efficiency", "grounding"]
DIM_HEADERS = ["Aggregate", "Outcome", "Tool Use", "Governance", "Efficiency", "Grounding"]


def load_results(model_token: str) -> list[dict]:
    """Load results from the most recent run directory for the given model."""
    model_dir = V02_BASE / model_token
    run_dirs = sorted(model_dir.glob("run_*"))
    if not run_dirs:
        return []
    latest = run_dirs[-1]
    results = []
    for f in sorted(latest.glob("results/*.json")):
        try:
            results.append(json.loads(f.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            pass
    return results


def build_row(label: str, results: list[dict]) -> dict:
    row = {"label": label, "n": len(results)}
    for dim in DIMS:
        if dim == "aggregate_score":
            vals = [r[dim] for r in results if r.get(dim) is not None]
        else:
            vals = [r["dimension_scores"][dim]
                    for r in results
                    if r.get("dimension_scores") and r["dimension_scores"].get(dim) is not None]
        row[dim] = statistics.mean(vals) if vals else None
    rob_vals = [r["dimension_scores"]["robustness"]
                for r in results
                if r.get("dimension_scores") and r["dimension_scores"].get("robustness") is not None]
    row["robustness"] = statistics.mean(rob_vals) if rob_vals else None
    return row


def fmt(v) -> str:
    return f"{v:.3f}" if v is not None else "—"


rows = []
for token in MODEL_ORDER:
    results = load_results(token)
    if results:
        rows.append(build_row(MODEL_LABELS[token], results))

all_dims    = DIMS + ["robustness"]
all_headers = DIM_HEADERS + ["Robustness"]

# ── Markdown ────────────────────────────────────────────────────────────────
header = "| Model | n | " + " | ".join(all_headers) + " |"
sep    = "|" + "|".join(["---"] * (len(all_headers) + 2)) + "|"

print("## Table 1 — Main Results (dev set, 59 tasks)\n")
print(header)
print(sep)
for r in rows:
    cells = [fmt(r[d]) for d in all_dims]
    print(f"| {r['label']} | {r['n']} | " + " | ".join(cells) + " |")

# ── LaTeX ────────────────────────────────────────────────────────────────────
cols = "l" + "r" * (len(all_headers) + 1)
print("\n\n## LaTeX\n")
print(r"\begin{table}[t]")
print(r"\centering")
print(r"\caption{Main results on the AOBench v0.2 dev set (59 tasks).}")
print(r"\label{tab:main_results}")
print(f"\\begin{{tabular}}{{{cols}}}")
print(r"\toprule")
print("Model & $n$ & " + " & ".join(all_headers) + r" \\")
print(r"\midrule")
for r in rows:
    cells = [r["label"], str(r["n"])] + [fmt(r[d]) for d in all_dims]
    print(" & ".join(cells) + r" \\")
print(r"\bottomrule")
print(r"\end{tabular}")
print(r"\end{table}")
