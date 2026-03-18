"""Robustness scorer — measures score variance across repeated runs of the same task."""

from __future__ import annotations

import math
from typing import Any

from exabench.schemas.result import BenchmarkResult


def compute_robustness(results: list[BenchmarkResult]) -> dict[str, Any]:
    """Compute robustness statistics from N repeated runs of the same task.

    Args:
        results: A list of BenchmarkResult objects for the **same** task_id.
                 Must have at least 2 entries.

    Returns a dict with:
    - ``task_id``          : the shared task identifier
    - ``n_runs``           : number of runs
    - ``mean_score``       : mean aggregate_score across runs
    - ``std_dev``          : population standard deviation of aggregate scores
    - ``min_score``        : minimum aggregate_score
    - ``max_score``        : maximum aggregate_score
    - ``range``            : max − min
    - ``robustness_score`` : 1.0 − std_dev  (1.0 = perfectly consistent)
    - ``scores``           : raw list of aggregate scores (one per run)

    Raises:
        ValueError: if fewer than 2 results are supplied, or task_ids differ.
    """
    if len(results) < 2:
        raise ValueError("Robustness requires at least 2 results for the same task.")

    task_ids = {r.task_id for r in results}
    if len(task_ids) > 1:
        raise ValueError(
            f"All results must be for the same task_id; got: {sorted(task_ids)}"
        )

    scores = [r.aggregate_score for r in results if r.aggregate_score is not None]
    if not scores:
        raise ValueError("No aggregate scores available in results.")

    n = len(scores)
    mean = sum(scores) / n
    variance = sum((s - mean) ** 2 for s in scores) / n
    std_dev = math.sqrt(variance)
    robustness = max(0.0, round(1.0 - std_dev, 4))

    return {
        "task_id": results[0].task_id,
        "n_runs": n,
        "mean_score": round(mean, 4),
        "std_dev": round(std_dev, 4),
        "min_score": round(min(scores), 4),
        "max_score": round(max(scores), 4),
        "range": round(max(scores) - min(scores), 4),
        "robustness_score": robustness,
        "scores": [round(s, 4) for s in scores],
    }


def compute_robustness_suite(
    results_by_task: dict[str, list[BenchmarkResult]],
) -> dict[str, Any]:
    """Compute robustness statistics for multiple tasks.

    Args:
        results_by_task: mapping of task_id → list of BenchmarkResult (≥2 each).

    Returns a summary dict with per-task stats and an overall mean robustness score.
    """
    task_stats = {}
    for task_id, task_results in results_by_task.items():
        if len(task_results) < 2:
            continue
        task_stats[task_id] = compute_robustness(task_results)

    if not task_stats:
        return {"tasks": {}, "mean_robustness_score": None}

    mean_robustness = round(
        sum(s["robustness_score"] for s in task_stats.values()) / len(task_stats), 4
    )

    return {
        "tasks": task_stats,
        "mean_robustness_score": mean_robustness,
    }
