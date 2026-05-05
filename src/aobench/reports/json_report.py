"""JSON report — aggregates all results from a run directory into a summary."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aobench.reports.error_taxonomy import classify_error
from aobench.schemas.result import BenchmarkResult


def _build_tool_use_block(r: BenchmarkResult) -> dict[str, Any]:
    """Build the per-task tool_use sub-block including gold-trajectory metrics."""
    base_score = r.dimension_scores.tool_use
    detail = getattr(r, "tool_use_detail", None)

    if detail is None:
        return {"tool_use_score": base_score}

    block: dict[str, Any] = {
        "tool_selection_score": getattr(detail, "tool_selection_score", None),
        "argument_correctness_score": getattr(detail, "argument_correctness_score", None),
        "forbidden_call_penalty": getattr(detail, "forbidden_call_penalty", None),
        "tool_use_score": getattr(detail, "tool_use_score", base_score),
        "node_f1": getattr(detail, "node_f1", None),
        "ned": getattr(detail, "ned", None),
        "step_accuracy": getattr(detail, "step_accuracy", None),
        "sequence_violations": getattr(detail, "sequence_violations", None),
        "sequence_penalty_applied": getattr(detail, "sequence_penalty_applied", None),
        "hard_fail_triggered": getattr(detail, "hard_fail_triggered", None),
        "clear_T": getattr(detail, "clear_T", base_score),
    }
    return block


def build_run_summary(run_dir: str | Path) -> dict[str, Any]:
    """Read all result JSON files from *run_dir* and return a summary dict.

    Expected layout::

        run_dir/
          results/
            JOB_USR_001_result.json
            JOB_USR_002_result.json
            ...

    Returns a dict suitable for JSON serialisation.
    """
    run_dir = Path(run_dir)
    results_dir = run_dir / "results"
    if not results_dir.exists():
        raise FileNotFoundError(f"No results/ directory found in {run_dir}")

    result_files = sorted(results_dir.glob("*_result.json"))
    if not result_files:
        raise FileNotFoundError(f"No *_result.json files found in {results_dir}")

    results: list[BenchmarkResult] = []
    for f in result_files:
        with f.open() as fh:
            results.append(BenchmarkResult.model_validate(json.load(fh)))

    scores = [r.aggregate_score for r in results if r.aggregate_score is not None]
    mean_score = round(sum(scores) / len(scores), 4) if scores else None

    task_rows = [
        {
            "task_id": r.task_id,
            "role": r.role,
            "environment_id": r.environment_id,
            "adapter_name": r.adapter_name,
            "model_name": r.model_name,
            "hard_fail": r.hard_fail,
            "hard_fail_reason": r.hard_fail_reason,
            "error_category": classify_error(r),
            "aggregate_score": r.aggregate_score,
            "outcome": r.dimension_scores.outcome,
            "tool_use": r.dimension_scores.tool_use,
            "tool_use_detail": _build_tool_use_block(r),
            "governance": r.dimension_scores.governance,
            "efficiency": r.dimension_scores.efficiency,
            "grounding": r.dimension_scores.grounding,
            "robustness": r.dimension_scores.robustness,
            "prompt_tokens": r.prompt_tokens,
            "completion_tokens": r.completion_tokens,
            "total_tokens": r.total_tokens,
            "cost_estimate_usd": r.cost_estimate_usd,
            "latency_seconds": r.latency_seconds,
        }
        for r in results
    ]

    # Error taxonomy summary
    category_counts: dict[str, int] = {}
    for row in task_rows:
        cat = row["error_category"]
        category_counts[cat] = category_counts.get(cat, 0) + 1

    total_cost = sum(r.cost_estimate_usd for r in results if r.cost_estimate_usd is not None)
    total_tokens = sum(r.total_tokens for r in results if r.total_tokens is not None)
    latencies = [r.latency_seconds for r in results if r.latency_seconds is not None]
    mean_latency = round(sum(latencies) / len(latencies), 3) if latencies else None

    # QCAT aggregates for gold-trajectory metrics (spec §5.3)
    qcat_aggregates = _build_qcat_aggregates(results)

    return {
        "run_id": results[0].run_id if results else run_dir.name,
        "task_count": len(results),
        "mean_aggregate_score": mean_score,
        "hard_fail_count": sum(1 for r in results if r.hard_fail),
        "total_cost_usd": round(total_cost, 6) if total_cost else None,
        "total_tokens": total_tokens or None,
        "mean_latency_seconds": mean_latency,
        "error_taxonomy": category_counts,
        "qcat_aggregates": qcat_aggregates,
        "tasks": task_rows,
    }


def _build_qcat_aggregates(results: list[BenchmarkResult]) -> dict[str, Any]:
    """Build per-QCAT aggregate stats for gold-trajectory metrics (spec §5.3).

    QCAT is inferred from the task_id prefix (e.g. JOB_USR_001 → JOB).
    Tasks without a gold_trajectory (detail is None or metrics are None) are
    excluded from the trajectory metric aggregates, not treated as 0.
    """
    from collections import defaultdict

    buckets: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    hard_fails: dict[str, int] = defaultdict(int)

    for r in results:
        qcat = r.task_id.split("_")[0] if r.task_id else "unknown"
        detail = getattr(r, "tool_use_detail", None)
        if detail is None:
            continue
        if getattr(detail, "node_f1", None) is not None:
            buckets[qcat]["node_f1"].append(detail.node_f1)
        if getattr(detail, "ned", None) is not None:
            buckets[qcat]["ned"].append(detail.ned)
        if getattr(detail, "step_accuracy", None) is not None:
            buckets[qcat]["step_accuracy"].append(detail.step_accuracy)
        if getattr(detail, "hard_fail_triggered", None):
            hard_fails[qcat] += 1

    aggregates: dict[str, Any] = {}
    all_qcats = set(buckets.keys()) | set(hard_fails.keys())
    for qcat in sorted(all_qcats):
        entry: dict[str, Any] = {}
        for metric in ("node_f1", "ned", "step_accuracy"):
            vals = buckets[qcat].get(metric, [])
            entry[f"mean_{metric}"] = round(sum(vals) / len(vals), 4) if vals else None
        entry["total_hard_fails"] = hard_fails.get(qcat, 0)
        aggregates[qcat] = entry

    return aggregates


def write_run_summary(run_dir: str | Path) -> Path:
    """Write ``run_summary.json`` into *run_dir* and return its path."""
    run_dir = Path(run_dir)
    summary = build_run_summary(run_dir)
    out = run_dir / "run_summary.json"
    with out.open("w") as fh:
        json.dump(summary, fh, indent=2, default=str)
    return out
