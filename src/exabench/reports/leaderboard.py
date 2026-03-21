"""Leaderboard CSV export for CLEAR reports.

Writes a CSV with columns:
    rank, model, clear_score, E, A, R, C_norm, L_norm, CNA, CPS,
    tier1_acc, tier2_acc, tier3_acc, pass_rate_<CATEGORY>...
"""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any

from exabench.reports.clear_report import compute_pass_k_by_category
from exabench.schemas.result import BenchmarkResult

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
