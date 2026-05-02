"""compute_stats.py — Statistical analysis for the v0.1 paper.

Sections:
  A. Bootstrap 95% CI per robustness task (10 scores each).
  B. Bootstrap 95% CI on dev-set mean aggregate score per model (21 tasks).
  C. Wilcoxon signed-rank test: GPT-4o vs direct_qa, paired by task.
  D. Wilson score 95% CI on pass^8 per robustness task.

Inputs:
  data/robustness/v01_gpt4o_*.json
  data/runs/v01_dev_gpt4o/run_20260321_192110_d2854175/run_summary.json
  data/runs/v01_smoke_direct_qa/<latest>/run_summary.json

Output: Markdown tables printed to stdout.
"""

from __future__ import annotations

import json
import math
import pathlib

import numpy as np
from scipy import stats

# ── Paths ─────────────────────────────────────────────────────────────────────
ROB_DIR = pathlib.Path("data/robustness")
GPT4O_RUN = pathlib.Path(
    "data/runs/v01_dev_gpt4o/run_20260321_192110_d2854175"
)
DQA_RUN = sorted(pathlib.Path("data/runs/v01_smoke_direct_qa").iterdir())[-1]

TASK_META = {
    "JOB_USR_001":    ("JOB",    "easy"),
    "JOB_SYS_002":    ("JOB",    "medium"),
    "MON_SYS_003":    ("MON",    "medium"),
    "ENERGY_FAC_003": ("ENERGY", "hard"),
    "MON_SYS_006":    ("MON",    "hard"),
}
TASK_ORDER = ["JOB_USR_001", "JOB_SYS_002", "MON_SYS_003", "ENERGY_FAC_003", "MON_SYS_006"]

N_BOOT = 1000
SEED = 42


# ── Helpers ────────────────────────────────────────────────────────────────────

def bootstrap_mean_ci(
    values: list[float],
    n_boot: int = N_BOOT,
    alpha: float = 0.05,
    rng: np.random.Generator | None = None,
) -> tuple[float, float]:
    """Return (lo, hi) bootstrap percentile CI on the mean."""
    rng = rng or np.random.default_rng(SEED)
    arr = np.array(values)
    boot_means = np.array([
        np.mean(rng.choice(arr, size=len(arr), replace=True))
        for _ in range(n_boot)
    ])
    return float(np.percentile(boot_means, 100 * alpha / 2)), float(
        np.percentile(boot_means, 100 * (1 - alpha / 2))
    )


def wilson_ci(n_pass: int, n_total: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion."""
    if n_total == 0:
        return 0.0, 0.0
    p = n_pass / n_total
    denom = 1 + z ** 2 / n_total
    centre = (p + z ** 2 / (2 * n_total)) / denom
    margin = z * math.sqrt(p * (1 - p) / n_total + z ** 2 / (4 * n_total ** 2)) / denom
    return max(0.0, centre - margin), min(1.0, centre + margin)


def load_task_scores(run_dir: pathlib.Path) -> dict[str, float]:
    """Return {task_id: aggregate_score} from a run_summary.json."""
    summary = json.loads((run_dir / "run_summary.json").read_text())
    return {
        t["task_id"]: t["aggregate_score"]
        for t in summary["tasks"]
        if t.get("aggregate_score") is not None
    }


def fmt(v: float | None, d: int = 3) -> str:
    return f"{v:.{d}f}" if v is not None else "—"


# ── Section A — Bootstrap CI per robustness task ──────────────────────────────

rng = np.random.default_rng(SEED)

print("## A. Bootstrap 95% CI on per-task mean score (GPT-4o, n=10 runs each)\n")
print(f"Bootstrap iterations: {N_BOOT} | seed: {SEED}\n")

header = "| Task | QCAT | Difficulty | mean | CI_lo | CI_hi | CI_width |"
sep    = "|------|------|------------|------|-------|-------|----------|"
print(header)
print(sep)

for task_id in TASK_ORDER:
    d = json.loads((ROB_DIR / f"v01_gpt4o_{task_id}.json").read_text())
    qcat, diff = TASK_META[task_id]
    scores = d["scores"]
    lo, hi = bootstrap_mean_ci(scores, rng=rng)
    mean = d["mean_score"]
    print(
        f"| {task_id} | {qcat} | {diff} | "
        f"{fmt(mean)} | {fmt(lo)} | {fmt(hi)} | {fmt(hi - lo)} |"
    )

# ── Section B — Bootstrap CI on dev-set mean per model ───────────────────────

print("\n\n## B. Bootstrap 95% CI on dev-set mean aggregate score (21 tasks)\n")
print(f"Bootstrap iterations: {N_BOOT} | seed: {SEED}\n")

header = "| Model | mean | CI_lo | CI_hi | CI_width |"
sep    = "|-------|------|-------|-------|----------|"
print(header)
print(sep)

model_data = [
    ("GPT-4o",    GPT4O_RUN),
    ("direct_qa", DQA_RUN),
]

paired_scores: dict[str, dict[str, float]] = {}
for label, run_dir in model_data:
    task_scores = load_task_scores(run_dir)
    paired_scores[label] = task_scores
    values = list(task_scores.values())
    mean = sum(values) / len(values)
    lo, hi = bootstrap_mean_ci(values, rng=rng)
    print(f"| {label} | {fmt(mean)} | {fmt(lo)} | {fmt(hi)} | {fmt(hi - lo)} |")

# ── Section C — Wilcoxon signed-rank test ─────────────────────────────────────

print("\n\n## C. Wilcoxon signed-rank test: GPT-4o vs direct_qa (paired by task)\n")

gpt4o_scores = paired_scores["GPT-4o"]
dqa_scores   = paired_scores["direct_qa"]

common_tasks = sorted(set(gpt4o_scores) & set(dqa_scores))
diffs = [gpt4o_scores[t] - dqa_scores[t] for t in common_tasks]

print(f"Paired tasks: {len(common_tasks)}")
print(f"Mean difference (GPT-4o − direct_qa): {fmt(sum(diffs)/len(diffs))}\n")

stat, pval = stats.wilcoxon(diffs, alternative="greater")
sig = "yes" if pval < 0.05 else "no"

print("| Test | W-statistic | p-value | α=0.05 significant |")
print("|------|------------|---------|-------------------|")
print(f"| GPT-4o > direct_qa | {stat:.1f} | {pval:.4f} | {sig} |")

print(
    f"\n*All statistical comparisons use the paired Wilcoxon signed-rank test "
    f"(α=0.05) over the 21-task dev split.*"
)

# ── Section D — Wilson score CI on pass^8 ─────────────────────────────────────

print("\n\n## D. Wilson score 95% CI on pass^8 (GPT-4o, n=10, pass_threshold=0.5)\n")

header = "| Task | QCAT | Difficulty | n_pass | n | pass^8 | CI_lo | CI_hi |"
sep    = "|------|------|------------|--------|---|--------|-------|-------|"
print(header)
print(sep)

for task_id in TASK_ORDER:
    d = json.loads((ROB_DIR / f"v01_gpt4o_{task_id}.json").read_text())
    qcat, diff = TASK_META[task_id]
    n_pass = d["n_passing"]
    n      = d["n_runs"]
    p8     = d["pass_k"]["8"]
    lo, hi = wilson_ci(n_pass, n)
    print(
        f"| {task_id} | {qcat} | {diff} | "
        f"{n_pass} | {n} | {fmt(p8)} | {fmt(lo)} | {fmt(hi)} |"
    )

print(
    f"\n*Pass^k confidence intervals use the Wilson score method (z=1.96).*"
)
