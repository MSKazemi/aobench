"""make_paper_table4.py — Table 4: reliability (pass^8) for the v0.2 paper.

Input:  data/robustness/v02/gpt-4o_*.json  (5 tasks, n=10 each)
Output: Markdown table with n_runs, n_passed, pass^8, mean_score, std_dev.
"""

import json
import pathlib

ROB_DIR = pathlib.Path("data/robustness/v02")

TASK_META = {
    "JOB_USR_001":    ("JOB",    "easy"),
    "JOB_SYS_002":    ("JOB",    "medium"),
    "MON_SYS_003":    ("MON",    "medium"),
    "ENERGY_FAC_003": ("ENERGY", "hard"),
    "MON_SYS_006":    ("MON",    "hard"),
}
TASK_ORDER = ["JOB_USR_001", "JOB_SYS_002", "MON_SYS_003", "ENERGY_FAC_003", "MON_SYS_006"]


def fmt(v, decimals=3) -> str:
    return f"{v:.{decimals}f}" if v is not None else "—"


rows = []
for task_id in TASK_ORDER:
    d = json.loads((ROB_DIR / f"gpt-4o_{task_id}.json").read_text())
    qcat, diff = TASK_META[task_id]
    rows.append({
        "task_id":    task_id,
        "qcat":       qcat,
        "difficulty": diff,
        "n_runs":     d["n_runs"],
        "n_passed":   d["n_passing"],
        "pass8":      d["pass_k"]["8"],
        "mean_score": d["mean_score"],
        "std_dev":    d["std_dev"],
    })

# ── Markdown ────────────────────────────────────────────────────────────────
header = "| Task | QCAT | Difficulty | n_runs | n_passed | pass^8 | mean_score | std_dev |"
sep    = "|------|------|------------|--------|----------|--------|------------|---------|"

print("## Table 4 — Reliability (GPT-4o, n=10, pass_threshold=0.5)\n")
print(header)
print(sep)
for r in rows:
    print(f"| {r['task_id']} | {r['qcat']} | {r['difficulty']} | "
          f"{r['n_runs']} | {r['n_passed']} | {fmt(r['pass8'])} | "
          f"{fmt(r['mean_score'])} | {fmt(r['std_dev'])} |")

p8s = [r["pass8"] for r in rows]
spread = max(p8s) - min(p8s)
print(f"\npass^8 spread (max − min): {max(p8s):.3f} − {min(p8s):.3f} = **{spread:.3f}**")
print(f"Gate V4 (spread ≥ 0.30): {'PASS' if spread >= 0.30 else 'FAIL'}")
