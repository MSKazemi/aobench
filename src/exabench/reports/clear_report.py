"""CLEAR metrics — multi-dimensional evaluation scorecard.

Implements the CLEAR framework (Mehta 2025, arXiv:2511.14136) adapted for ExaBench:

  C — Cost      (min-max normalised API spend, lower=better)
  L — Latency   (min-max normalised wall-clock time, lower=better)
  E — Efficacy  (mean outcome score, 0–1)
  A — Assurance (mean governance/RBAC score, 0–1)
  R — Reliability (pass^k)

CLEAR composite: CLEAR = 0.2×C_norm + 0.2×L_norm + 0.2×E + 0.2×A + 0.2×R
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from exabench.schemas.result import BenchmarkResult


def compute_cna(result: BenchmarkResult) -> float | None:
    """Compute Cost-Normalised Accuracy for a single result.

    CNA = (outcome_score / cost_estimate_usd) × 100

    Returns None if cost is missing or zero, or if outcome is missing.
    Higher is better (more accuracy per dollar).
    """
    cost = result.cost_estimate_usd
    outcome = result.dimension_scores.outcome
    if cost is None or cost == 0.0 or outcome is None:
        return None
    return (outcome / cost) * 100.0


def compute_cps(
    results: list[BenchmarkResult],
    pass_threshold: float = 0.5,
) -> float | None:
    """Compute Cost Per Success for a list of results from the same model.

    CPS = total_cost_usd / n_successful

    Returns None if no successful runs.
    Lower is better (cheaper per successful task).
    """
    total_cost = sum(
        r.cost_estimate_usd for r in results if r.cost_estimate_usd is not None
    )
    n_successful = sum(
        1
        for r in results
        if r.aggregate_score is not None and r.aggregate_score >= pass_threshold
    )
    if n_successful == 0:
        return None
    return total_cost / n_successful


def normalise_min_max(
    values: list[float | None],
    invert: bool = False,
) -> list[float | None]:
    """Min-max normalise a list of values to [0, 1].

    Args:
        values: List of float values (None entries are preserved as None).
        invert: If True, lower raw values map to higher scores (use for cost/latency).

    Returns a list of the same length. None inputs map to None outputs.
    If all valid values are equal, all outputs are 1.0 (no spread case).
    """
    valid = [v for v in values if v is not None]
    if not valid:
        return [None] * len(values)

    vmin = min(valid)
    vmax = max(valid)

    result = []
    for v in values:
        if v is None:
            result.append(None)
        elif vmax == vmin:
            result.append(1.0)
        else:
            norm = (v - vmin) / (vmax - vmin)
            result.append(round(1.0 - norm if invert else norm, 4))
    return result


def compute_clear_scores(
    model_results: dict[str, list[BenchmarkResult]],
    reliability_k: int = 1,
    pass_threshold: float = 0.5,
    robustness_by_model: dict[str, dict] | None = None,
) -> dict[str, dict[str, Any]]:
    """Compute CLEAR dimension scores and composite for each model.

    Args:
        model_results:       model_name → list of BenchmarkResult.
        reliability_k:       k for pass^k reliability (1, 2, 4, 8).
        pass_threshold:      Min aggregate_score to count as passing.
        robustness_by_model: Optional model_name → robustness_suite dict
                             (from ``compute_robustness_suite``). Provides
                             pre-computed pass^k values for R.

    Returns:
        model_name → {
            clear_score, C_norm, L_norm, E, A, R,
            mean_cost_usd, mean_latency_s, CNA, CPS,
            n_tasks, n_successful
        }

    Cost and latency are normalised *across* all models in model_results, so
    C_norm and L_norm are only meaningful when ≥ 2 models are compared.
    """
    from exabench.scorers.robustness_scorer import compute_pass_k  # noqa: PLC0415

    model_names = list(model_results.keys())
    per_model: dict[str, dict[str, Any]] = {}

    for model in model_names:
        results = model_results[model]
        n = len(results)

        # E — Efficacy: mean outcome score
        outcomes = [
            r.dimension_scores.outcome
            for r in results
            if r.dimension_scores.outcome is not None
        ]
        E = round(sum(outcomes) / len(outcomes), 4) if outcomes else None

        # A — Assurance: mean governance score
        govs = [
            r.dimension_scores.governance
            for r in results
            if r.dimension_scores.governance is not None
        ]
        A = round(sum(govs) / len(govs), 4) if govs else None

        # Raw cost and latency (normalised across models later)
        costs = [r.cost_estimate_usd for r in results if r.cost_estimate_usd is not None]
        mean_cost = round(sum(costs) / len(costs), 6) if costs else None

        latencies = [r.latency_seconds for r in results if r.latency_seconds is not None]
        mean_latency = round(sum(latencies) / len(latencies), 3) if latencies else None

        # R — Reliability: pass^k
        rob_data = (robustness_by_model or {}).get(model)
        if rob_data and "mean_pass_k" in rob_data:
            R = rob_data["mean_pass_k"].get(reliability_k)
            if R is not None:
                R = round(R, 4)
        else:
            # Compute pass^k from results grouped by task_id
            by_task: dict[str, list[BenchmarkResult]] = defaultdict(list)
            for r in results:
                by_task[r.task_id].append(r)

            pass_k_values = []
            for task_results in by_task.values():
                if len(task_results) >= reliability_k:
                    try:
                        pk = compute_pass_k(
                            task_results, k=reliability_k, pass_threshold=pass_threshold
                        )
                        pass_k_values.append(pk)
                    except ValueError:
                        pass

            if pass_k_values:
                R = round(sum(pass_k_values) / len(pass_k_values), 4)
            else:
                # Fallback: simple success rate (pass^1 approximation)
                passing = sum(
                    1
                    for r in results
                    if r.aggregate_score is not None
                    and r.aggregate_score >= pass_threshold
                )
                R = round(passing / n, 4) if n > 0 else None

        n_successful = sum(
            1
            for r in results
            if r.aggregate_score is not None and r.aggregate_score >= pass_threshold
        )

        # CNA: mean CNA across all results that have both outcome and cost
        cna_values = [v for r in results if (v := compute_cna(r)) is not None]
        mean_cna = round(sum(cna_values) / len(cna_values), 2) if cna_values else None

        # CPS
        cps = compute_cps(results, pass_threshold=pass_threshold)

        per_model[model] = {
            "E": E,
            "A": A,
            "R": R,
            "mean_cost_usd": mean_cost,
            "mean_latency_s": mean_latency,
            "CNA": mean_cna,
            "CPS": round(cps, 6) if cps is not None else None,
            "n_tasks": n,
            "n_successful": n_successful,
            # filled after cross-model normalisation:
            "C_norm": None,
            "L_norm": None,
            "clear_score": None,
        }

    # Cross-model normalisation of cost and latency (lower=better → invert=True)
    cost_values = [per_model[m]["mean_cost_usd"] for m in model_names]
    latency_values = [per_model[m]["mean_latency_s"] for m in model_names]
    c_norms = normalise_min_max(cost_values, invert=True)
    l_norms = normalise_min_max(latency_values, invert=True)

    for model, c_norm, l_norm in zip(model_names, c_norms, l_norms):
        per_model[model]["C_norm"] = c_norm
        per_model[model]["L_norm"] = l_norm

        E = per_model[model]["E"]
        A = per_model[model]["A"]
        R = per_model[model]["R"]

        if all(v is not None for v in (c_norm, l_norm, E, A, R)):
            clear = round(0.2 * c_norm + 0.2 * l_norm + 0.2 * E + 0.2 * A + 0.2 * R, 4)
        else:
            clear = None
        per_model[model]["clear_score"] = clear

    return per_model


def build_clear_report(
    model_results: dict[str, list[BenchmarkResult]],
    reliability_k: int = 1,
    pass_threshold: float = 0.5,
    robustness_by_model: dict[str, dict] | None = None,
) -> dict[str, Any]:
    """Build a full CLEAR report dict suitable for JSON serialisation.

    Returns a dict with shape::

        {
            "generated_at": "<ISO-8601>",
            "task_count": <int>,
            "pass_threshold": <float>,
            "reliability_k": <int>,
            "models": { <model_name>: { clear_score, C_norm, ... } },
            "leaderboard": [ {"rank": 1, "model": ..., "clear_score": ..., "CNA": ...} ]
        }

    The leaderboard is sorted by clear_score descending.
    """
    scores = compute_clear_scores(
        model_results,
        reliability_k=reliability_k,
        pass_threshold=pass_threshold,
        robustness_by_model=robustness_by_model,
    )

    task_count = max(len(v) for v in model_results.values()) if model_results else 0

    # Build leaderboard sorted by clear_score descending (None last)
    leaderboard = sorted(
        [
            {"rank": 0, "model": m, "clear_score": s["clear_score"], "CNA": s["CNA"]}
            for m, s in scores.items()
        ],
        key=lambda x: (x["clear_score"] is None, -(x["clear_score"] or 0.0)),
    )
    for i, entry in enumerate(leaderboard, start=1):
        entry["rank"] = i

    return {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "task_count": task_count,
        "pass_threshold": pass_threshold,
        "reliability_k": reliability_k,
        "models": scores,
        "leaderboard": leaderboard,
    }


def write_clear_report(
    model_results: dict[str, list[BenchmarkResult]],
    output_path: str | Path,
    reliability_k: int = 1,
    pass_threshold: float = 0.5,
    robustness_by_model: dict[str, dict] | None = None,
) -> Path:
    """Build and write a CLEAR report to *output_path*. Returns the path written."""
    output_path = Path(output_path)
    report = build_clear_report(
        model_results,
        reliability_k=reliability_k,
        pass_threshold=pass_threshold,
        robustness_by_model=robustness_by_model,
    )
    output_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    return output_path
