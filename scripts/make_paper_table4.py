"""make_paper_table4.py — Generate Table 4 (reliability / pass^k) for the v0.1 paper.

Input:  data/robustness/v01_*.json  (15 files: 5 tasks × 3 models)
Output: Markdown table to stdout (or --output file)

File name convention:  v01_{model}_{TASK_ID}.json
  where model ∈ {claude, gpt4o, gpt4o_mini}

Usage:
    python3 scripts/make_paper_table4.py
    python3 scripts/make_paper_table4.py --output paper/table4.md
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


DEFAULT_ROB_DIR = "data/robustness"

# Tasks in the robustness suite (§4.2)
ROBUSTNESS_TASKS = [
    "JOB_USR_001",
    "JOB_SYS_002",
    "MON_SYS_003",
    "ENERGY_FAC_003",
    "MON_SYS_006",
]

TASK_DIFFICULTY = {
    "JOB_USR_001": "easy",
    "JOB_SYS_002": "medium",
    "MON_SYS_003": "medium",
    "ENERGY_FAC_003": "hard",
    "MON_SYS_006": "hard",
}

MODEL_SLUG_MAP = {
    "claude": "Claude-Sonnet-4.6",
    "gpt4o_mini": "GPT-4o-mini",
    "gpt4o": "GPT-4o",
}

K = 8  # pass^k we report in the main table


def load_robustness_files(rob_dir: str) -> dict[str, dict[str, dict]]:
    """Return {task_id: {model_label: stats}} from v01_*.json files."""
    base = Path(rob_dir)
    result: dict[str, dict[str, dict]] = {t: {} for t in ROBUSTNESS_TASKS}

    for f in sorted(base.glob("v01_*.json")):
        stem = f.stem  # e.g. v01_claude_JOB_USR_001
        parts = stem.split("_", maxsplit=2)  # ["v01", "claude", "JOB_USR_001"]
        if len(parts) < 3:
            continue
        model_slug = parts[1]  # "claude" / "gpt4o" / "gpt4o_mini"
        # Handle gpt4o_mini: "v01_gpt4o_mini_JOB_USR_001" → parts[1]="gpt4o", parts[2]="mini_JOB_USR_001"
        # Need to re-parse for two-word model names.
        raw = stem[len("v01_"):]  # "claude_JOB_USR_001" or "gpt4o_mini_JOB_USR_001"
        for slug in sorted(MODEL_SLUG_MAP.keys(), key=len, reverse=True):
            if raw.startswith(slug + "_"):
                model_slug = slug
                task_id = raw[len(slug) + 1:]
                break
        else:
            continue

        if task_id not in ROBUSTNESS_TASKS:
            continue

        stats = json.loads(f.read_text(encoding="utf-8"))
        label = MODEL_SLUG_MAP.get(model_slug, model_slug)
        result[task_id][label] = stats

    return result


def get_pass_k(stats: dict, k: int) -> float | None:
    """Extract pass^k from robustness stats dict."""
    pass_k = stats.get("pass_k", {})
    # pass_k keys may be int or str
    v = pass_k.get(k) or pass_k.get(str(k))
    return round(float(v), 4) if v is not None else None


def make_markdown_table(data: dict[str, dict[str, dict]]) -> str:
    models = list(MODEL_SLUG_MAP.values())
    headers = ["Task", "Difficulty"] + [f"{m} pass^{K}" for m in models]
    col_w = [max(len(h), 8) for h in headers]

    sep = "| " + " | ".join("-" * w for w in col_w) + " |"
    header_row = "| " + " | ".join(h.ljust(col_w[i]) for i, h in enumerate(headers)) + " |"

    lines = [header_row, sep]
    for task_id in ROBUSTNESS_TASKS:
        difficulty = TASK_DIFFICULTY.get(task_id, "?")
        cells = [task_id.ljust(col_w[0]), difficulty.ljust(col_w[1])]
        for i, model in enumerate(models):
            stats = data[task_id].get(model, {})
            v = get_pass_k(stats, K)
            cell = f"{v:.4f}" if v is not None else "N/A"
            cells.append(cell.ljust(col_w[i + 2]))
        lines.append("| " + " | ".join(cells) + " |")

    return "\n".join(lines)


def make_latex_table(data: dict[str, dict[str, dict]]) -> str:
    models = list(MODEL_SLUG_MAP.values())
    n_cols = 2 + len(models)
    cols = "ll" + "r" * len(models)
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Reliability (pass\textsuperscript{" + str(K) + r"}) on 5 representative tasks.}",
        r"\label{tab:reliability}",
        r"\begin{tabular}{" + cols + r"}",
        r"\toprule",
        "Task & Difficulty & " + " & ".join(f"{m} pass\\textsuperscript{{{K}}}" for m in models) + r" \\",
        r"\midrule",
    ]
    for task_id in ROBUSTNESS_TASKS:
        difficulty = TASK_DIFFICULTY.get(task_id, "?")
        cells = [task_id.replace("_", r"\_"), difficulty]
        for model in models:
            stats = data[task_id].get(model, {})
            v = get_pass_k(stats, K)
            cells.append(f"{v:.4f}" if v is not None else "--")
        lines.append(" & ".join(cells) + r" \\")
    lines += [
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--rob-dir",
        default=DEFAULT_ROB_DIR,
        help=f"Directory containing v01_*.json robustness files (default: {DEFAULT_ROB_DIR})",
    )
    parser.add_argument("--output", "-o", default="-", help="Output file (default: stdout)")
    args = parser.parse_args(argv)

    data = load_robustness_files(args.rob_dir)

    missing = [t for t in ROBUSTNESS_TASKS if not data[t]]
    if missing:
        print(f"Warning: no robustness data for tasks: {missing}", file=sys.stderr)

    output_lines = [
        "# Table 4 — Reliability (pass^k)",
        f"Robustness: {K} repeated runs per task  |  {len(ROBUSTNESS_TASKS)} representative tasks",
        "",
        "## Markdown",
        "",
        make_markdown_table(data),
        "",
        "## LaTeX",
        "",
        make_latex_table(data),
        "",
    ]

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
