"""Robustness scorer — measures score variance and pass^k across repeated runs."""

from __future__ import annotations

import math
from typing import Any

from exabench.schemas.result import BenchmarkResult

# k values reported by default in compute_robustness()
_DEFAULT_K_VALUES = (1, 2, 4, 8)


def compute_pass_k(
    results: list[BenchmarkResult],
    k: int,
    pass_threshold: float = 0.5,
) -> float:
    """Compute pass^k: probability that ALL k independent runs of a task succeed.

    Uses the unbiased combinatorial estimator from τ-bench (Yao et al., 2024):

        pass^k = C(c, k) / C(n, k) = ∏_{i=0}^{k-1} (c − i) / (n − i)

    where:
        n = total number of runs
        c = number of passing runs  (aggregate_score >= pass_threshold)
        k = the k parameter

    Returns 0.0 when c < k (fewer passing runs than required).
    pass^1  == pass@1 == simple success rate.
    pass^8  is the key production-reliability threshold from CLEAR (ρ=0.83).

    Args:
        results:        List of BenchmarkResult for the **same** task_id.
        k:              Number of runs that must all pass.
        pass_threshold: Minimum aggregate_score to count a run as passing.

    Raises:
        ValueError: if k > len(results).
    """
    n = len(results)
    if k > n:
        raise ValueError(
            f"k={k} exceeds number of runs n={n}. "
            f"Run the task at least {k} times."
        )

    c = sum(
        1 for r in results
        if r.aggregate_score is not None and r.aggregate_score >= pass_threshold
    )

    if c < k:
        return 0.0

    # C(c, k) / C(n, k)  computed incrementally to avoid overflow
    result = 1.0
    for i in range(k):
        result *= (c - i) / (n - i)

    return round(result, 4)


def compute_robustness(
    results: list[BenchmarkResult],
    pass_threshold: float = 0.5,
) -> dict[str, Any]:
    """Compute robustness statistics from N repeated runs of the same task.

    Args:
        results:        BenchmarkResult objects for the **same** task_id (≥ 2).
        pass_threshold: Minimum aggregate_score to count a run as passing
                        when computing pass^k values.

    Returns a dict with:
    - ``task_id``          : the shared task identifier
    - ``n_runs``           : number of runs
    - ``pass_threshold``   : threshold used for pass^k
    - ``n_passing``        : runs with aggregate_score >= pass_threshold
    - ``pass_k``           : dict of pass^k values for k in (1, 2, 4, 8)
                             — only computed for k <= n_runs
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

    n_passing = sum(1 for s in scores if s >= pass_threshold)
    pass_k = {
        k: compute_pass_k(results, k, pass_threshold)
        for k in _DEFAULT_K_VALUES
        if k <= n
    }

    costs = [r.cost_estimate_usd for r in results if r.cost_estimate_usd is not None]
    latencies = [r.latency_seconds for r in results if r.latency_seconds is not None]

    return {
        "task_id": results[0].task_id,
        "n_runs": n,
        "pass_threshold": pass_threshold,
        "n_passing": n_passing,
        "pass_k": pass_k,
        "mean_score": round(mean, 4),
        "std_dev": round(std_dev, 4),
        "min_score": round(min(scores), 4),
        "max_score": round(max(scores), 4),
        "range": round(max(scores) - min(scores), 4),
        "robustness_score": robustness,
        "scores": [round(s, 4) for s in scores],
        "total_cost_usd": round(sum(costs), 6) if costs else None,
        "mean_latency_seconds": round(sum(latencies) / len(latencies), 3) if latencies else None,
    }


def compute_robustness_suite(
    results_by_task: dict[str, list[BenchmarkResult]],
    pass_threshold: float = 0.5,
) -> dict[str, Any]:
    """Compute robustness statistics for multiple tasks.

    Args:
        results_by_task: mapping of task_id → list of BenchmarkResult (≥2 each).
        pass_threshold:  Minimum aggregate_score to count a run as passing.

    Returns a summary dict with per-task stats, mean robustness, and mean pass^k
    values across all tasks.
    """
    task_stats = {}
    for task_id, task_results in results_by_task.items():
        if len(task_results) < 2:
            continue
        task_stats[task_id] = compute_robustness(task_results, pass_threshold)

    if not task_stats:
        return {"tasks": {}, "mean_robustness_score": None, "mean_pass_k": {}}

    mean_robustness = round(
        sum(s["robustness_score"] for s in task_stats.values()) / len(task_stats), 4
    )

    # Mean pass^k across tasks, for each k value present
    all_k = set()
    for s in task_stats.values():
        all_k.update(s["pass_k"].keys())

    mean_pass_k = {}
    for k in sorted(all_k):
        values = [s["pass_k"][k] for s in task_stats.values() if k in s["pass_k"]]
        mean_pass_k[k] = round(sum(values) / len(values), 4) if values else None

    all_costs = [s["total_cost_usd"] for s in task_stats.values() if s["total_cost_usd"] is not None]
    all_latencies = [s["mean_latency_seconds"] for s in task_stats.values() if s["mean_latency_seconds"] is not None]

    return {
        "tasks": task_stats,
        "mean_robustness_score": mean_robustness,
        "mean_pass_k": mean_pass_k,
        "total_cost_usd": round(sum(all_costs), 6) if all_costs else None,
        "mean_latency_seconds": round(sum(all_latencies) / len(all_latencies), 3) if all_latencies else None,
    }
