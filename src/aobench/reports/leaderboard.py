"""Leaderboard CSV export and result loading for CLEAR reports.

Writes a CSV with columns:
    rank, model, clear_score, E, A, R, C_norm, L_norm, CNA, CPS,
    tier1_acc, tier2_acc, tier3_acc, pass_rate_<CATEGORY>...

Also provides:
  - load_results_dir()   — scan results_dir/<model>/*.json for BenchmarkResult files
  - write_heatmap_csv()  — per-task×model reliability heatmap CSV
"""

from __future__ import annotations

import csv
import io
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

from aobench.reports.clear_report import compute_pass_k_by_category
from aobench.schemas.result import BenchmarkResult

_BASE_CSV_COLUMNS = [
    "rank",
    "model",
    "clear_score",
    "E",
    "A",
    "R",
    "C_norm",
    "L_norm",
    "CNA",
    "CPS",
    "tier1_acc",
    "tier2_acc",
    "tier3_acc",
]


def _category_col(category: str) -> str:
    return f"pass_rate_{category}"


def leaderboard_to_csv(
    report: dict[str, Any],
    model_results: dict[str, list[BenchmarkResult]] | None = None,
    pass_threshold: float = 0.5,
) -> str:
    """Convert a CLEAR report dict to a CSV string.

    The input is the dict returned by ``build_clear_report()``.
    Returns a CSV string with header row + one row per model, sorted by rank.

    Args:
        report:         Dict returned by ``build_clear_report()``.
        model_results:  Optional model_name → results mapping. When supplied,
                        per-category pass rates are computed and appended as
                        extra columns (``pass_rate_<CATEGORY>``).
        pass_threshold: Passed to ``compute_pass_k_by_category``.
    """
    leaderboard = report.get("leaderboard", [])

    # Compute per-category pass rates and collect all category names
    category_rates: dict[str, dict[str, float]] = {}
    all_categories: list[str] = []
    if model_results:
        seen: set[str] = set()
        for model, results in model_results.items():
            rates = compute_pass_k_by_category(results, pass_threshold=pass_threshold)
            category_rates[model] = rates
            for cat in rates:
                if cat not in seen:
                    seen.add(cat)
                    all_categories.append(cat)
        all_categories.sort()

    fieldnames = _BASE_CSV_COLUMNS + [_category_col(c) for c in all_categories]

    buf = io.StringIO()
    writer = csv.DictWriter(
        buf,
        fieldnames=fieldnames,
        extrasaction="ignore",
        lineterminator="\n",
    )
    writer.writeheader()
    for entry in leaderboard:
        row = dict(entry)
        model = entry.get("model", "")
        for cat in all_categories:
            row[_category_col(cat)] = category_rates.get(model, {}).get(cat)
        writer.writerow(row)
    return buf.getvalue()


def write_leaderboard_csv(
    report: dict[str, Any],
    output_path: str | Path,
    model_results: dict[str, list[BenchmarkResult]] | None = None,
    pass_threshold: float = 0.5,
) -> Path:
    """Write leaderboard CSV to *output_path*. Returns the path written.

    Args:
        report:         Dict returned by ``build_clear_report()``.
        output_path:    Destination file path.
        model_results:  Optional model_name → results mapping. When supplied,
                        per-category pass rates are appended as extra columns.
        pass_threshold: Minimum score counted as a pass for category columns.
    """
    output_path = Path(output_path)
    output_path.write_text(
        leaderboard_to_csv(report, model_results=model_results, pass_threshold=pass_threshold),
        encoding="utf-8",
    )
    return output_path


# ---------------------------------------------------------------------------
# Result loading
# ---------------------------------------------------------------------------

def load_results_dir(
    results_dir: str | Path,
) -> dict[str, list[BenchmarkResult]]:
    """Scan *results_dir* for BenchmarkResult JSON files, grouped by model.

    Expected layout::

        results_dir/
            <model_name>/
                <task_id>_result.json
                ...

    Any JSON file that can be parsed as a BenchmarkResult is included.
    Files that fail validation are silently skipped.

    Args:
        results_dir: Root directory to scan.

    Returns:
        dict mapping model_name → list of BenchmarkResult, sorted by task_id.
    """
    results_dir = Path(results_dir)
    model_results: dict[str, list[BenchmarkResult]] = {}

    for model_dir in sorted(results_dir.iterdir()):
        if not model_dir.is_dir():
            continue
        model_name = model_dir.name
        results: list[BenchmarkResult] = []
        for json_file in sorted(model_dir.glob("*.json")):
            try:
                data = json.loads(json_file.read_text(encoding="utf-8"))
                results.append(BenchmarkResult.model_validate(data))
            except Exception:
                pass
        if results:
            model_results[model_name] = results

    return model_results


# ---------------------------------------------------------------------------
# Heatmap CSV
# ---------------------------------------------------------------------------

_HEATMAP_COLUMNS = [
    "task_id",
    "qcat",
    "role",
    "difficulty",
    "model",
    "n_runs",
    "n_passed",
    "pass_at_1",
    "pass_at_2",
    "pass_at_4",
    "pass_at_8",
    "all_pass_at_8",
    "mean",
    "std",
]


def _safe_pass_k(results: list[BenchmarkResult], k: int, threshold: float) -> float | None:
    """Compute pass^k, returning None when k > n (instead of raising)."""
    n = len(results)
    if k > n:
        return None
    c = sum(
        1 for r in results
        if (r.cup_score if r.cup_score is not None else r.aggregate_score) is not None
        and (r.cup_score if r.cup_score is not None else r.aggregate_score) >= threshold  # type: ignore[operator]
    )
    if c < k:
        return 0.0
    # Unbiased combinatorial estimator
    result = 1.0
    for i in range(k):
        result *= (c - i) / (n - i)
    return round(result, 4)


def write_heatmap_csv(
    model_results: dict[str, list[BenchmarkResult]],
    output_path: str | Path,
    k_values: list[int] | None = None,
    pass_threshold: float = 0.5,
) -> Path:
    """Write a per-task × model reliability heatmap CSV.

    Each row represents one (task_id, model) pair. Columns include pass@k for
    each k in *k_values* (default [1, 2, 4, 8]), plus mean and std of scores.

    Args:
        model_results:  dict model_name → list of BenchmarkResult.
        output_path:    Destination CSV path.
        k_values:       List of k values for pass^k columns (default [1,2,4,8]).
        pass_threshold: Minimum score to count as a pass.

    Returns:
        The path written.
    """
    if k_values is None:
        k_values = [1, 2, 4, 8]

    # Group results by (task_id, model)
    by_task_model: dict[tuple[str, str], list[BenchmarkResult]] = defaultdict(list)
    for model, results in model_results.items():
        for r in results:
            by_task_model[(r.task_id, model)].append(r)

    # Collect per-task metadata (first result wins)
    task_meta: dict[str, dict] = {}
    for (task_id, model), results in by_task_model.items():
        if task_id not in task_meta:
            r0 = results[0]
            task_meta[task_id] = {
                "qcat": r0.task_category or "",
                "role": r0.role or "",
                "difficulty_tier": r0.task_difficulty_tier,
            }

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=_HEATMAP_COLUMNS, lineterminator="\n")
    writer.writeheader()

    for (task_id, model) in sorted(by_task_model.keys()):
        results = by_task_model[(task_id, model)]
        meta = task_meta.get(task_id, {})
        scores = [
            (r.cup_score if r.cup_score is not None else r.aggregate_score)
            for r in results
            if (r.cup_score if r.cup_score is not None else r.aggregate_score) is not None
        ]
        n_passed = sum(1 for s in scores if s >= pass_threshold)  # type: ignore[operator]
        tier = meta.get("difficulty_tier")
        difficulty_str = str(tier) if tier is not None else ""

        row: dict[str, Any] = {
            "task_id": task_id,
            "qcat": meta.get("qcat", ""),
            "role": meta.get("role", ""),
            "difficulty": difficulty_str,
            "model": model,
            "n_runs": len(results),
            "n_passed": n_passed,
            "mean": round(statistics.mean(scores), 4) if scores else None,
            "std": round(statistics.stdev(scores), 4) if len(scores) >= 2 else None,
            "all_pass_at_8": (n_passed == len(results) and len(results) >= 8),
        }
        for k in k_values:
            col = f"pass_at_{k}"
            row[col] = _safe_pass_k(results, k, pass_threshold)

        writer.writerow(row)

    output_path.write_text(buf.getvalue(), encoding="utf-8")
    return output_path
