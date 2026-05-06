"""make_paper_table1.py — Table 1: main results for the v0.2 paper.

Reads from both data/runs/v02_dev/ (GPT models) and
data/runs/v02_dev_ollama/ (open-source models via Ollama).
Rows sorted by aggregate score descending; baseline pinned to bottom.
Output: Markdown + LaTeX table with per-model dimension scores.
"""

import json
import pathlib
import statistics

V02_DEV        = pathlib.Path("data/runs/v02_dev")
V02_DEV_OLLAMA = pathlib.Path("data/runs/v02_dev_ollama")

# (token, run_base, display_label, is_baseline)
MODELS = [
    # GPT models
    ("gpt-4o",                  V02_DEV,        "GPT-4o",                   False),
    ("gpt-4o-mini",             V02_DEV,        "GPT-4o-mini",              False),
    # Ollama open-source models
    ("qwen3.6:35b-a3b",         V02_DEV_OLLAMA, "Qwen3.6 35B-A3B (MoE)",    False),
    ("qwen3.5:122b",            V02_DEV_OLLAMA, "Qwen3.5 122B",             False),
    ("mistral-nemo:latest",     V02_DEV_OLLAMA, "Mistral Nemo 12B",         False),
    ("GLM-4.7-Flash:latest",    V02_DEV_OLLAMA, "GLM-4.7-Flash",            False),
    ("nemotron-3-super:latest", V02_DEV_OLLAMA, "Nemotron-3 Super 253B",    False),
    ("nemotron3:33b",           V02_DEV_OLLAMA, "Nemotron3 33B",            False),
    ("devstral-small-2:24b",    V02_DEV_OLLAMA, "Devstral Small 2 24B",     False),
    ("qwen3-coder-next:latest", V02_DEV_OLLAMA, "Qwen3 Coder Next 235B",    False),
    ("gemma4:e4b",              V02_DEV_OLLAMA, "Gemma4 E4B",               False),
    ("gpt-oss:latest",          V02_DEV_OLLAMA, "GPT-OSS",                  False),
    ("gpt-oss:20b",             V02_DEV_OLLAMA, "GPT-OSS 20B",              False),
    ("mistral-small:24b",       V02_DEV_OLLAMA, "Mistral Small 24B",        False),
    ("gemma4:31b",              V02_DEV_OLLAMA, "Gemma4 31B",               False),
    # Baseline (pinned last)
    ("direct_qa",               V02_DEV,        "Direct QA (baseline)",     True),
]

DIMS        = ["aggregate_score", "outcome", "tool_use", "governance", "efficiency", "grounding"]
DIM_HEADERS = ["Aggregate", "Outcome", "Tool Use", "Governance", "Efficiency", "Grounding"]


def load_results(token: str, base: pathlib.Path) -> list[dict]:
    model_dir = base / token
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


def build_row(label: str, results: list[dict], is_baseline: bool) -> dict:
    row = {"label": label, "n": len(results), "is_baseline": is_baseline}
    for dim in DIMS:
        if dim == "aggregate_score":
            vals = [r[dim] for r in results if r.get(dim) is not None]
        else:
            vals = [r["dimension_scores"][dim]
                    for r in results
                    if r.get("dimension_scores") and r["dimension_scores"].get(dim) is not None]
        row[dim] = statistics.mean(vals) if vals else None
    return row


def fmt(v) -> str:
    return f"{v:.3f}" if v is not None else "—"


# Build rows — sort agentic models by aggregate desc, baseline last
rows_agentic = []
row_baseline = None

for token, base, label, is_baseline in MODELS:
    results = load_results(token, base)
    if not results:
        continue
    row = build_row(label, results, is_baseline)
    if is_baseline:
        row_baseline = row
    else:
        rows_agentic.append(row)

rows_agentic.sort(key=lambda r: r["aggregate_score"] or 0, reverse=True)
rows = rows_agentic + ([row_baseline] if row_baseline else [])

# ── Markdown ─────────────────────────────────────────────────────────────────
header = "| Model | n | " + " | ".join(DIM_HEADERS) + " |"
sep    = "|" + "|".join(["---"] * (len(DIM_HEADERS) + 2)) + "|"

print("## Table 1 — Main Results (dev set, 59 tasks)\n")
print(header)
print(sep)
for r in rows:
    cells = [fmt(r[d]) for d in DIMS]
    print(f"| {r['label']} | {r['n']} | " + " | ".join(cells) + " |")

# ── LaTeX ─────────────────────────────────────────────────────────────────────
cols = "l" + "r" * (len(DIM_HEADERS) + 1)
print("\n\n## LaTeX\n")
print(r"\begin{table*}[t]")
print(r"\centering")
print(r"\caption{Main results on the AOBench v0.2 dev set (59 tasks). "
      r"Models sorted by aggregate score. Baseline pinned last.}")
print(r"\label{tab:main_results}")
print(f"\\begin{{tabular}}{{{cols}}}")
print(r"\toprule")
print("Model & $n$ & " + " & ".join(DIM_HEADERS) + r" \\")
print(r"\midrule")
prev_baseline = False
for r in rows:
    if r["is_baseline"] and not prev_baseline:
        print(r"\midrule")
    cells = [r["label"], str(r["n"])] + [fmt(r[d]) for d in DIMS]
    print(" & ".join(cells) + r" \\")
    prev_baseline = r["is_baseline"]
print(r"\bottomrule")
print(r"\end{tabular}")
print(r"\end{table*}")
