#!/usr/bin/env python3
"""E5 ablation: stratify outcome score by task difficulty with 95% bootstrap CIs.

Reads every data/runs/v02_dev/<model>/results.jsonl for all model subdirs found.
Stratifies by 'difficulty' field (easy/medium/hard).  The 'difficulty' string is
taken directly from the JSON record when present; otherwise it is inferred from
'task_difficulty_tier' (1→easy, 2→medium, 3→hard).

Bootstrap uses random.Random(seed=42) with n=10,000 resamples over tasks.
Outputs data/ablations/difficulty.json.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

DIFFICULTIES = ["easy", "medium", "hard"]

# Map numeric tier → difficulty string
_TIER_TO_DIFFICULTY = {1: "easy", 2: "medium", 3: "hard"}

BOOTSTRAP_N = 10_000
BOOTSTRAP_SEED = 42


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_results_jsonl(path: Path) -> list[dict]:
    """Load a results.jsonl file, skipping malformed lines."""
    records: list[dict] = []
    with path.open(encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                warnings.warn(f"{path}:{lineno}: skipping malformed JSON line: {exc}")
    return records


def _get_difficulty(record: dict) -> str | None:
    """Extract difficulty string from a result record.

    Checks 'difficulty' key first; falls back to mapping 'task_difficulty_tier'
    integer (1→easy, 2→medium, 3→hard).  Returns None when neither is present.
    """
    diff = record.get("difficulty")
    if diff in DIFFICULTIES:
        return diff
    # Some records may carry extra string values like "adversarial" — treat as hard
    if diff == "adversarial":
        return "hard"
    tier = record.get("task_difficulty_tier")
    if tier is not None:
        return _TIER_TO_DIFFICULTY.get(int(tier))
    return None


def _get_score(record: dict) -> float | None:
    """Extract the primary outcome score from a result record."""
    score = record.get("aggregate_score")
    if score is not None:
        return float(score)
    # Fallback to dimension_scores.outcome
    dim = record.get("dimension_scores") or {}
    outcome = dim.get("outcome")
    if outcome is not None:
        return float(outcome)
    return None


def _bootstrap_ci(
    values: list[float],
    n_resamples: int,
    rng: random.Random,
    confidence: float = 0.95,
) -> tuple[float, float]:
    """Compute bootstrap confidence interval for the mean.

    Args:
        values:     Sample of float scores.
        n_resamples: Number of bootstrap resamples.
        rng:        Seeded random.Random instance for reproducibility.
        confidence: Desired confidence level (default 0.95).

    Returns:
        (lower, upper) CI bounds, both rounded to 4 decimal places.
    """
    n = len(values)
    boot_means: list[float] = []
    for _ in range(n_resamples):
        sample = [values[rng.randint(0, n - 1)] for _ in range(n)]
        boot_means.append(sum(sample) / n)
    boot_means.sort()
    alpha = 1.0 - confidence
    lo_idx = int(alpha / 2 * n_resamples)
    hi_idx = int((1 - alpha / 2) * n_resamples) - 1
    lo_idx = max(0, min(lo_idx, n_resamples - 1))
    hi_idx = max(0, min(hi_idx, n_resamples - 1))
    return (round(boot_means[lo_idx], 4), round(boot_means[hi_idx], 4))


# ---------------------------------------------------------------------------
# Main computation
# ---------------------------------------------------------------------------


def compute_difficulty_ablation(runs_dir: Path) -> dict:
    """Compute difficulty-stratified scores with bootstrap CIs from a runs directory."""
    # Discover model subdirs
    model_dirs: list[Path] = []
    if runs_dir.exists():
        model_dirs = sorted(
            [d for d in runs_dir.iterdir() if d.is_dir() and (d / "results.jsonl").exists()]
        )

    if not model_dirs:
        warnings.warn(
            f"No model subdirs with results.jsonl found under {runs_dir}. "
            "Writing empty output."
        )
        return {
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
            "difficulties": DIFFICULTIES,
            "models": [],
            "mean_scores": {d: {} for d in DIFFICULTIES},
            "ci_95": {d: {} for d in DIFFICULTIES},
        }

    model_names = [d.name for d in model_dirs]

    # Load and stratify records per model
    # model_strata[model][difficulty] = list of scores
    model_strata: dict[str, dict[str, list[float]]] = {
        m: {d: [] for d in DIFFICULTIES} for m in model_names
    }
    for d in model_dirs:
        records = _load_results_jsonl(d / "results.jsonl")
        for rec in records:
            diff = _get_difficulty(rec)
            score = _get_score(rec)
            if diff in DIFFICULTIES and score is not None:
                model_strata[d.name][diff].append(score)

    # Compute mean scores and bootstrap CIs
    rng = random.Random(BOOTSTRAP_SEED)

    mean_scores: dict[str, dict[str, float | None]] = {d: {} for d in DIFFICULTIES}
    ci_95: dict[str, dict[str, list[float | None]]] = {d: {} for d in DIFFICULTIES}

    for model in model_names:
        for diff in DIFFICULTIES:
            vals = model_strata[model][diff]
            if not vals:
                mean_scores[diff][model] = None
                ci_95[diff][model] = [None, None]
            else:
                mean_val = round(sum(vals) / len(vals), 4)
                mean_scores[diff][model] = mean_val
                lo, hi = _bootstrap_ci(vals, BOOTSTRAP_N, rng)
                ci_95[diff][model] = [lo, hi]

    return {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "difficulties": DIFFICULTIES,
        "models": model_names,
        "mean_scores": mean_scores,
        "ci_95": ci_95,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "E5 ablation: stratify outcome score by task difficulty "
            "(easy/medium/hard) with 95%% bootstrap confidence intervals."
        )
    )
    parser.add_argument(
        "--runs",
        default="data/runs/v02_dev/",
        help="Directory containing per-model run subdirs (default: data/runs/v02_dev/)",
    )
    parser.add_argument(
        "--output",
        default="data/ablations/difficulty.json",
        help="Output JSON path (default: data/ablations/difficulty.json)",
    )
    args = parser.parse_args(argv)

    runs_dir = Path(args.runs)
    output_path = Path(args.output)

    if not runs_dir.exists():
        warnings.warn(f"Runs directory does not exist: {runs_dir}. Writing empty output.")

    result = compute_difficulty_ablation(runs_dir)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Written: {output_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
