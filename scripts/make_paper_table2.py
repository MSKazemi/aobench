"""make_paper_table2.py — Table 2: CLEAR scorecard for all models (v0.2 paper).

Input:  data/reports/v02_clear_report_merged.json
Output: Markdown + LaTeX table with CLEAR dimensions per model.

Two column groups:
  Group A (all models): E, A, R, L_norm
  Group B (API models only): CLEAR composite, C_norm, CNA, CPS
Ollama models show \\,--- in Group B columns.
direct_qa baseline shows \\,--- for A (engagement-aware governance is vacuous
for a zero-tool agent) and \\,--- for Group B columns (no API cost).

Usage:
    uv run python scripts/make_paper_table2.py
"""

import json
import pathlib

CLEAR_PATH = pathlib.Path("data/reports/v02_clear_report_merged.json")

MODEL_LABELS: dict[str, str] = {
    "gpt-4o":                  "GPT-4o",
    "gpt-4o-mini":             "GPT-4o-mini",
    "qwen3.6:35b-a3b":         "Qwen3.6 35B-A3B (MoE)",
    "qwen3.5:122b":            "Qwen3.5 122B",
    "mistral-nemo:latest":     "Mistral Nemo 12B",
    "GLM-4.7-Flash:latest":    "GLM-4.7-Flash",
    "nemotron-3-super:latest": "Nemotron-3 Super 253B",
    "nemotron3:33b":           "Nemotron3 33B",
    "devstral-small-2:24b":    "Devstral Small 2 24B",
    "qwen3-coder-next:latest": "Qwen3 Coder Next 235B",
    "gemma4:e4b":              "Gemma4 E4B",
    "gpt-oss:latest":          "GPT-OSS",
    "gpt-oss:20b":             "GPT-OSS 20B",
    "mistral-small:24b":       "Mistral Small 24B",
    "gemma4:31b":              "Gemma4 31B",
    "direct_qa":               "Direct QA (baseline)",
}

OLLAMA_TOKENS: set[str] = {
    "qwen3.6:35b-a3b", "qwen3.5:122b", "mistral-nemo:latest", "GLM-4.7-Flash:latest",
    "nemotron-3-super:latest", "nemotron3:33b", "devstral-small-2:24b",
    "qwen3-coder-next:latest", "gemma4:e4b", "gpt-oss:latest", "gpt-oss:20b",
    "mistral-small:24b", "gemma4:31b",
}


def fmt(v: float | None, decimals: int = 3) -> str:
    if v is None:
        return r"\,---"
    return f"{v:.{decimals}f}"


def fmt_md(v: float | None, decimals: int = 3) -> str:
    if v is None:
        return "N/A"
    return f"{v:.{decimals}f}"


data = json.loads(CLEAR_PATH.read_text(encoding="utf-8"))
models_data = data["models"]

# Build rows from leaderboard order (already sorted: API-CLEAR, then Ollama by E, baseline last)
rows = []
for entry in data["leaderboard"]:
    token = entry["model"]
    m = models_data.get(token, {})
    is_baseline = token == "direct_qa"
    is_ollama   = token in OLLAMA_TOKENS
    rows.append({
        "token":       token,
        "label":       MODEL_LABELS.get(token, token),
        "is_baseline": is_baseline,
        "is_ollama":   is_ollama,
        # Group A — all models
        "E":       m.get("E"),
        "A":       None if is_baseline else m.get("A"),   # vacuous for zero-tool agent
        "R":       m.get("R"),
        "L_norm":  m.get("L_norm"),
        # Group B — API models only
        "clear_score": m.get("clear_score"),
        "C_norm":      m.get("C_norm"),
        "CNA":         m.get("CNA"),
        "CPS":         m.get("CPS"),
    })

# ── Markdown ─────────────────────────────────────────────────────────────────
HEADERS_MD = ["Model", "E", "A", "R", "L", "CLEAR", "C_norm", "CNA", "CPS($)"]
hdr = "| " + " | ".join(HEADERS_MD) + " |"
sep = "|" + "|".join(["---"] * len(HEADERS_MD)) + "|"

print("## Table 2 — CLEAR Scorecard\n")
print(hdr)
print(sep)
for r in rows:
    cells = [
        r["label"],
        fmt_md(r["E"]),
        fmt_md(r["A"]),
        fmt_md(r["R"]),
        fmt_md(r["L_norm"]),
        fmt_md(r["clear_score"]),
        fmt_md(r["C_norm"]),
        fmt_md(r["CNA"], 1),
        fmt_md(r["CPS"], 4),
    ]
    print("| " + " | ".join(cells) + " |")

# ── LaTeX ─────────────────────────────────────────────────────────────────────
print("\n\n## LaTeX\n")
print(r"\begin{table}[t]")
print(r"\centering")
print(r"\small")
print(
    r"\caption{CLEAR scorecard for AOBench v0.2 dev set (59 tasks). "
    r"\textit{E}~=~Efficacy, \textit{A}~=~Assurance, \textit{R}~=~Reliability, "
    r"\textit{L}~=~Latency (min-max normalised, higher~=~faster). "
    r"CLEAR, C\textsubscript{norm}, CNA, and CPS are reported only for API-billed "
    r"models; local-inference cost is hardware-dependent and not directly comparable.}"
)
print(r"\label{tab:clear}")
print(r"\begin{tabular}{lrrrrrrrr}")
print(r"\toprule")
print(r"& \multicolumn{4}{c}{All models} & \multicolumn{4}{c}{API models only} \\")
print(r"\cmidrule(lr){2-5}\cmidrule(lr){6-9}")
print(
    r"Model & E & A & R & L"
    r" & CLEAR & C\textsubscript{norm} & CNA & CPS(\$) \\"
)
print(r"\midrule")

prev_was_ollama   = False
prev_was_baseline = False
first_ollama      = True
first_baseline    = True

for r in rows:
    is_ollama   = r["is_ollama"]
    is_baseline = r["is_baseline"]

    # Separator before first Ollama block
    if is_ollama and not is_baseline and first_ollama and rows[0]["token"] not in OLLAMA_TOKENS:
        print(r"\midrule")
        first_ollama = False

    # Separator before baseline
    if is_baseline and first_baseline:
        print(r"\midrule")
        first_baseline = False

    cells = [
        r["label"],
        fmt(r["E"]),
        fmt(r["A"]),
        fmt(r["R"]),
        fmt(r["L_norm"]),
        fmt(r["clear_score"]),
        fmt(r["C_norm"]),
        fmt(r["CNA"], 1),
        fmt(r["CPS"], 4),
    ]
    print(" & ".join(cells) + r" \\")

print(r"\bottomrule")
print(r"\end{tabular}")
print(r"\end{table}")
