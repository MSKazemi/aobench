"""make_paper_table2.py — Table 2: CLEAR scorecard for the v0.2 paper.

Input:  data/reports/v02_clear_report.json
Output: Markdown + LaTeX table with CLEAR dimensions per model.
"""

import json
import pathlib

CLEAR_PATH = pathlib.Path("data/reports/v02_clear_report.json")

MODEL_ORDER  = ["gpt-4o", "gpt-4o-mini", "direct_qa"]
MODEL_LABELS = {"gpt-4o": "GPT-4o", "gpt-4o-mini": "GPT-4o-mini", "direct_qa": "Direct QA (baseline)"}

COLS = ["clear_score", "E", "A", "R", "C_norm", "L_norm", "CNA", "CPS"]
HEADERS = ["Model", "CLEAR", "E (Efficacy)", "A (Assurance)", "R (Reliability)",
           "C_norm", "L_norm", "CNA", "CPS($)"]


def fmt(v, decimals=3) -> str:
    if v is None:
        return "N/A"
    return f"{v:.{decimals}f}"


data = json.loads(CLEAR_PATH.read_text())
models = data["models"]

rows = []
for model_id in MODEL_ORDER:
    m = models.get(model_id, {})
    rows.append({
        "label":      MODEL_LABELS.get(model_id, model_id),
        "clear_score": m.get("clear_score"),
        "E":          m.get("E"),
        "A":          m.get("A"),
        "R":          m.get("R"),
        "C_norm":     m.get("C_norm"),
        "L_norm":     m.get("L_norm"),
        "CNA":        m.get("CNA"),
        "CPS":        m.get("CPS"),
    })

# ── Markdown ─────────────────────────────────────────────────────────────────
header = "| " + " | ".join(HEADERS) + " |"
sep    = "|" + "|".join(["---"] * len(HEADERS)) + "|"

print("## Table 2 — CLEAR Scorecard\n")
print(header)
print(sep)
for r in rows:
    cells = [r["label"]] + [fmt(r[c]) for c in COLS]
    print("| " + " | ".join(cells) + " |")

# ── LaTeX ─────────────────────────────────────────────────────────────────────
cols_spec = "l" + "r" * len(COLS)
latex_header = " & ".join(HEADERS)

print("\n\n## LaTeX\n")
print(r"\begin{table}[t]")
print(r"\centering")
print(r"\caption{CLEAR scorecard for ExaBench v0.2 dev set (59 tasks).}")
print(r"\label{tab:clear}")
print(f"\\begin{{tabular}}{{{cols_spec}}}")
print(r"\toprule")
print(latex_header + r" \\")
print(r"\midrule")
for r in rows:
    cells = [r["label"]] + [fmt(r[c]) for c in COLS]
    print(" & ".join(cells) + r" \\")
print(r"\bottomrule")
print(r"\end{tabular}")
print(r"\end{table}")
