"""JSON report — aggregates all results from a run directory into a summary."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from exabench.reports.error_taxonomy import classify_error
from exabench.schemas.result import BenchmarkResult


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

    return {
        "run_id": results[0].run_id if results else run_dir.name,
        "task_count": len(results),
        "mean_aggregate_score": mean_score,
        "hard_fail_count": sum(1 for r in results if r.hard_fail),
        "total_cost_usd": round(total_cost, 6) if total_cost else None,
        "total_tokens": total_tokens or None,
        "mean_latency_seconds": mean_latency,
        "error_taxonomy": category_counts,
        "tasks": task_rows,
    }


def write_run_summary(run_dir: str | Path) -> Path:
    """Write ``run_summary.json`` into *run_dir* and return its path."""
    run_dir = Path(run_dir)
    summary = build_run_summary(run_dir)
    out = run_dir / "run_summary.json"
    with out.open("w") as fh:
        json.dump(summary, fh, indent=2, default=str)
    return out
