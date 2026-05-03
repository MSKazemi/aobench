"""compute_stats.py — Statistical analysis for the v0.2 paper.

Sections:
  A. Bootstrap 95% CI per robustness task (10 scores each).
  B. Bootstrap 95% CI on dev-set mean aggregate score per model (59 tasks).
  C. Wilcoxon signed-rank test: GPT-4o vs direct_qa, paired by task.
  D. Wilson score 95% CI on pass^8 per robustness task.

Inputs:
  data/robustness/v02/gpt-4o_*.json
  data/runs/v02_dev/<model>/run_*/results/*.json

Output: Markdown tables printed to stdout.
"""

from __future__ import annotations

import json
import math
import pathlib

import numpy as np
from scipy import stats

# ── Paths ─────────────────────────────────────────────────────────────────────
ROB_DIR   = pathlib.Path("data/robustness/v02")
V02_BASE  = pathlib.Path("data/runs/v02_dev")

TASK_META = {
    "JOB_USR_001":    ("JOB",    "easy"),
    "JOB_SYS_002":    ("JOB",    "medium"),
    "MON_SYS_003":    ("MON",    "medium"),
    "ENERGY_FAC_003": ("ENERGY", "hard"),
    "MON_SYS_006":    ("MON",    "hard"),
}
TASK_ORDER = ["JOB_USR_001", "JOB_SYS_002", "MON_SYS_003", "ENERGY_FAC_003", "MON_SYS_006"]

N_BOOT = 1000
SEED   = 42


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


def load_task_scores(model_token: str) -> dict[str, float]:
    """Return {task_id: aggregate_score} from the most recent run for a model."""
    model_dir = V02_BASE / model_token
    run_dirs = sorted(model_dir.glob("run_*"))
    if not run_dirs:
        return {}
    latest = run_dirs[-1]
    scores = {}
    for f in sorted(latest.glob("results/*.json")):
        try:
            r = json.loads(f.read_text(encoding="utf-8"))
            if r.get("aggregate_score") is not None:
                scores[r["task_id"]] = float(r["aggregate_score"])
        except (json.JSONDecodeError, OSError):
            pass
    return scores


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
    d = json.loads((ROB_DIR / f"gpt-4o_{task_id}.json").read_text())
    qcat, diff = TASK_META[task_id]
    scores = d["scores"]
    lo, hi = bootstrap_mean_ci(scores, rng=rng)
    mean = d["mean_score"]
    print(
        f"| {task_id} | {qcat} | {diff} | "
        f"{fmt(mean)} | {fmt(lo)} | {fmt(hi)} | {fmt(hi - lo)} |"
    )

# ── Section B — Bootstrap CI on dev-set mean per model ───────────────────────

print("\n\n## B. Bootstrap 95% CI on dev-set mean aggregate score (59 tasks)\n")
print(f"Bootstrap iterations: {N_BOOT} | seed: {SEED}\n")

header = "| Model | n | mean | CI_lo | CI_hi | CI_width |"
sep    = "|-------|---|------|-------|-------|----------|"
print(header)
print(sep)

model_tokens = [("GPT-4o", "gpt-4o"), ("GPT-4o-mini", "gpt-4o-mini"), ("direct_qa", "direct_qa")]

paired_scores: dict[str, dict[str, float]] = {}
for label, token in model_tokens:
    task_scores = load_task_scores(token)
    paired_scores[label] = task_scores
    values = list(task_scores.values())
    if not values:
        print(f"| {label} | 0 | — | — | — | — |")
        continue
    mean = sum(values) / len(values)
    lo, hi = bootstrap_mean_ci(values, rng=rng)
    print(f"| {label} | {len(values)} | {fmt(mean)} | {fmt(lo)} | {fmt(hi)} | {fmt(hi - lo)} |")

# ── Section C — Wilcoxon signed-rank test ─────────────────────────────────────

print("\n\n## C. Wilcoxon signed-rank test (paired by task, α=0.05)\n")

baseline = paired_scores["direct_qa"]
print("| Comparison | n_paired | Mean diff | W-statistic | p-value | Significant |")
print("|-----------|----------|-----------|-------------|---------|-------------|")

for label, token in [("GPT-4o", "gpt-4o"), ("GPT-4o-mini", "gpt-4o-mini")]:
    model_scores = paired_scores[label]
    common = sorted(set(model_scores) & set(baseline))
    if len(common) < 2:
        print(f"| {label} vs direct_qa | {len(common)} | — | — | — | — |")
        continue
    diffs = [model_scores[t] - baseline[t] for t in common]
    mean_diff = sum(diffs) / len(diffs)
    stat, pval = stats.wilcoxon(diffs, alternative="greater")
    sig = "yes" if pval < 0.05 else "no"
    print(f"| {label} vs direct_qa | {len(common)} | {fmt(mean_diff)} | {stat:.1f} | {pval:.4f} | {sig} |")

print(
    f"\n*Paired Wilcoxon signed-rank test (one-sided: model > baseline), α=0.05, "
    f"over 59-task dev split.*"
)

# ── Section D — Wilson score CI on pass^8 ─────────────────────────────────────

print("\n\n## D. Wilson score 95% CI on pass^8 (GPT-4o, n=10, pass_threshold=0.5)\n")

header = "| Task | QCAT | Difficulty | n_pass | n | pass^8 | CI_lo | CI_hi |"
sep    = "|------|------|------------|--------|---|--------|-------|-------|"
print(header)
print(sep)

for task_id in TASK_ORDER:
    d = json.loads((ROB_DIR / f"gpt-4o_{task_id}.json").read_text())
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
