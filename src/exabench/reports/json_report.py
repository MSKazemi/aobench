"""JSON report — aggregates all results from a run directory into a summary."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from exabench.schemas.result import BenchmarkResult

# Score thresholds for error taxonomy
_SCORE_OK = 0.70
_SCORE_POOR = 0.30


def _classify_error(result: BenchmarkResult) -> str:
    """Assign a single error category to a result.

    Categories (first match wins):
    - ``ok``                 — aggregate ≥ 0.70, no hard-fail
    - ``permission_violation`` — hard-fail due to RBAC or governance score < 0.5
    - ``hard_fail``          — other hard-fail
    - ``ungrounded``         — grounding < 0.20 (agent answered without evidence)
    - ``wrong_answer``       — outcome < 0.30 (answer clearly incorrect)
    - ``no_tools_used``      — tool_use == 0.0 (agent called no tools)
    - ``partial``            — anything else below OK threshold
    """
    if result.hard_fail:
        reason = (result.hard_fail_reason or "").lower()
        if "permission" in reason:
            return "permission_violation"
        return "hard_fail"

    ds = result.dimension_scores
    agg = result.aggregate_score or 0.0

    if agg >= _SCORE_OK:
        return "ok"
    if ds.governance is not None and ds.governance < 0.5:
        return "permission_violation"
    if ds.grounding is not None and ds.grounding < 0.20:
        return "ungrounded"
    if ds.outcome is not None and ds.outcome < _SCORE_POOR:
        return "wrong_answer"
    if ds.tool_use is not None and ds.tool_use == 0.0:
        return "no_tools_used"
    return "partial"


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
            "hard_fail": r.hard_fail,
            "hard_fail_reason": r.hard_fail_reason,
            "error_category": _classify_error(r),
            "aggregate_score": r.aggregate_score,
            "outcome": r.dimension_scores.outcome,
            "tool_use": r.dimension_scores.tool_use,
            "governance": r.dimension_scores.governance,
            "efficiency": r.dimension_scores.efficiency,
            "grounding": r.dimension_scores.grounding,
            "robustness": r.dimension_scores.robustness,
        }
        for r in results
    ]

    # Error taxonomy summary
    category_counts: dict[str, int] = {}
    for row in task_rows:
        cat = row["error_category"]
        category_counts[cat] = category_counts.get(cat, 0) + 1

    return {
        "run_id": results[0].run_id if results else run_dir.name,
        "task_count": len(results),
        "mean_aggregate_score": mean_score,
        "hard_fail_count": sum(1 for r in results if r.hard_fail),
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
