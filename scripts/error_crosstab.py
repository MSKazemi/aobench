"""error_crosstab.py — Error cross-tabulation for the v0.1 paper.

Sections:
  A. pass^8 tier × error_category (5 robustness tasks; 3 are in the dev split).
  B. Score tier × error_category (all 21 GPT-4o dev tasks).
  C. Score tier × violation_vector flags (all 21 GPT-4o dev tasks).

Inputs:
  data/robustness/v01_gpt4o_*.json
  data/runs/v01_dev_gpt4o/run_20260321_192110_d2854175/run_summary.json
  data/runs/v01_dev_gpt4o/run_20260321_192110_d2854175/results/*.json

Output: Markdown tables printed to stdout.
"""

from __future__ import annotations

import json
import pathlib
from collections import defaultdict

# ── Paths ─────────────────────────────────────────────────────────────────────
ROB_DIR     = pathlib.Path("data/robustness")
GPT4O_RUN   = pathlib.Path(
    "data/runs/v01_dev_gpt4o/run_20260321_192110_d2854175"
)
RESULTS_DIR = GPT4O_RUN / "results"

TASK_META = {
    "JOB_USR_001":    ("JOB",    "easy"),
    "JOB_SYS_002":    ("JOB",    "medium"),
    "MON_SYS_003":    ("MON",    "medium"),
    "ENERGY_FAC_003": ("ENERGY", "hard"),
    "MON_SYS_006":    ("MON",    "hard"),
}
TASK_ORDER = ["JOB_USR_001", "JOB_SYS_002", "MON_SYS_003", "ENERGY_FAC_003", "MON_SYS_006"]

PASS_THRESHOLD = 0.5

VIOLATION_FLAGS = [
    "forbidden_tool_call",
    "data_scope_breach",
    "role_boundary_crossing",
    "dangerous_args_invoked",
    "policy_undefined_action",
]


# ── Load data ─────────────────────────────────────────────────────────────────

# error_category is in run_summary.json (not in individual result files)
summary = json.loads((GPT4O_RUN / "run_summary.json").read_text())
summary_by_task: dict[str, dict] = {t["task_id"]: t for t in summary["tasks"]}

# violation_vector is in individual result files
results_by_task: dict[str, dict] = {}
for path in sorted(RESULTS_DIR.glob("*_result.json")):
    r = json.loads(path.read_text())
    results_by_task[r["task_id"]] = r

all_task_ids = sorted(summary_by_task.keys())


# ── Section A — pass^8 tier × error_category (5 robustness tasks) ─────────────

print("## A. pass^8 tier × error_category (5 robustness tasks)\n")
print("Tier: `fail` = pass^8 of 0.0 — `pass` = pass^8 of 1.0")
print("Note: JOB_SYS_002 and MON_SYS_003 are not in the 21-task dev split; "
      "error_category is not available for them.\n")

rob_rows = []
for task_id in TASK_ORDER:
    d    = json.loads((ROB_DIR / f"v01_gpt4o_{task_id}.json").read_text())
    p8   = d["pass_k"]["8"]
    tier = "pass" if p8 >= 1.0 else "fail"
    qcat, diff = TASK_META[task_id]
    # error_category only available for tasks in the dev split
    if task_id in summary_by_task:
        cat   = summary_by_task[task_id].get("error_category", "unknown")
        score = summary_by_task[task_id].get("aggregate_score")
    else:
        cat   = "n/a (not in dev split)"
        score = None
    rob_rows.append({
        "task_id":        task_id,
        "qcat":           qcat,
        "difficulty":     diff,
        "pass8_tier":     tier,
        "pass8":          p8,
        "error_category": cat,
        "score":          score,
    })

print("| Task | QCAT | Difficulty | pass^8 | Tier | error_category | aggregate_score |")
print("|------|------|------------|--------|------|----------------|-----------------|")
for r in rob_rows:
    score = f"{r['score']:.3f}" if r["score"] is not None else "—"
    print(
        f"| {r['task_id']} | {r['qcat']} | {r['difficulty']} | "
        f"{r['pass8']:.1f} | {r['pass8_tier']} | {r['error_category']} | {score} |"
    )

# Cross-tab for tasks that are in the dev split only
dev_rob_rows = [r for r in rob_rows if r["error_category"] != "n/a (not in dev split)"]
all_cats_a = sorted({r["error_category"] for r in dev_rob_rows})
tiers_a    = ["fail", "pass"]
counts_a: dict[str, dict[str, int]] = {t: defaultdict(int) for t in tiers_a}
for row in dev_rob_rows:
    counts_a[row["pass8_tier"]][row["error_category"]] += 1

if all_cats_a:
    print(f"\n**Cross-tab (n=3 tasks in dev split):**\n")
    header_a = "| Tier | " + " | ".join(all_cats_a) + " | Total |"
    sep_a    = "|" + "|".join(["---"] * (len(all_cats_a) + 2)) + "|"
    print(header_a)
    print(sep_a)
    for tier in tiers_a:
        cells = [str(counts_a[tier][c]) for c in all_cats_a]
        total = sum(counts_a[tier].values())
        print(f"| {tier} | " + " | ".join(cells) + f" | {total} |")

# ── Section B — score tier × error_category (all dev tasks) ──────────────────

print("\n\n## B. Score tier × error_category (all GPT-4o dev tasks)\n")
print(f"Tier: `pass` = aggregate_score ≥ {PASS_THRESHOLD} — `fail` = below {PASS_THRESHOLD}\n")

def score_tier(score: float | None) -> str:
    if score is None:
        return "unknown"
    return "pass" if score >= PASS_THRESHOLD else "fail"

all_cats_b = sorted({
    t.get("error_category", "unknown")
    for t in summary_by_task.values()
})
tiers_b = ["pass", "fail"]

counts_b: dict[str, dict[str, int]] = {t: defaultdict(int) for t in tiers_b}
tier_task_lists: dict[str, list[str]] = {"pass": [], "fail": []}

for task_id, t in summary_by_task.items():
    tier = score_tier(t.get("aggregate_score"))
    cat  = t.get("error_category", "unknown")
    if tier in counts_b:
        counts_b[tier][cat] += 1
        tier_task_lists[tier].append(task_id)

header_b = "| Tier | " + " | ".join(all_cats_b) + " | Total |"
sep_b    = "|" + "|".join(["---"] * (len(all_cats_b) + 2)) + "|"
print(header_b)
print(sep_b)
for tier in tiers_b:
    cells = [str(counts_b[tier][c]) for c in all_cats_b]
    total = sum(counts_b[tier].values())
    print(f"| {tier} | " + " | ".join(cells) + f" | {total} |")

pass_scores = [summary_by_task[t]["aggregate_score"] for t in tier_task_lists["pass"]
               if summary_by_task[t].get("aggregate_score") is not None]
fail_scores = [summary_by_task[t]["aggregate_score"] for t in tier_task_lists["fail"]
               if summary_by_task[t].get("aggregate_score") is not None]

if pass_scores:
    print(f"\nPass tasks (n={len(pass_scores)}): mean={sum(pass_scores)/len(pass_scores):.3f}")
if fail_scores:
    print(f"Fail tasks (n={len(fail_scores)}): mean={sum(fail_scores)/len(fail_scores):.3f}")

# ── Section C — score tier × violation_vector flags ──────────────────────────

print("\n\n## C. Score tier × violation_vector flags (all 21 GPT-4o dev tasks)\n")
print(
    "Flag is counted as set if its value is `true` in `violation_vector`. "
    "A task may have multiple flags set.\n"
)

flag_counts: dict[str, dict[str, int]] = {
    flag: {"pass": 0, "fail": 0} for flag in VIOLATION_FLAGS
}
tier_totals = {"pass": 0, "fail": 0}

for task_id, res in results_by_task.items():
    score = res.get("aggregate_score")
    tier  = score_tier(score)
    if tier not in tier_totals:
        continue
    tier_totals[tier] += 1
    vv = res.get("violation_vector") or {}
    for flag in VIOLATION_FLAGS:
        if vv.get(flag):
            flag_counts[flag][tier] += 1

print(f"Task totals — pass: {tier_totals['pass']}, fail: {tier_totals['fail']}\n")

header_c = (
    f"| Violation flag | fail tasks (n={tier_totals['fail']}) "
    f"| pass tasks (n={tier_totals['pass']}) | total |"
)
sep_c = "|----------------|-------------------|-------------------|-------|"
print(header_c)
print(sep_c)
for flag in VIOLATION_FLAGS:
    f_cnt = flag_counts[flag]["fail"]
    p_cnt = flag_counts[flag]["pass"]
    tot   = f_cnt + p_cnt
    f_pct = f"{100*f_cnt/tier_totals['fail']:.0f}%" if tier_totals["fail"] else "—"
    p_pct = f"{100*p_cnt/tier_totals['pass']:.0f}%" if tier_totals["pass"] else "—"
    print(f"| `{flag}` | {f_cnt} ({f_pct}) | {p_cnt} ({p_pct}) | {tot} |")
