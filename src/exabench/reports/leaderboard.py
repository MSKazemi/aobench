"""Leaderboard CSV export for CLEAR reports.

Writes a CSV with columns:
    rank, model, clear_score, E, A, R, C_norm, L_norm, CNA, CPS,
    tier1_acc, tier2_acc, tier3_acc
"""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any

_CSV_COLUMNS = [
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


def leaderboard_to_csv(report: dict[str, Any]) -> str:
    """Convert a CLEAR report dict to a CSV string.

    The input is the dict returned by ``build_clear_report()``.
    Returns a CSV string with header row + one row per model, sorted by rank.
    """
    leaderboard = report.get("leaderboard", [])
    buf = io.StringIO()
    writer = csv.DictWriter(
        buf,
        fieldnames=_CSV_COLUMNS,
        extrasaction="ignore",
        lineterminator="\n",
    )
    writer.writeheader()
    for entry in leaderboard:
        writer.writerow(entry)
    return buf.getvalue()


def write_leaderboard_csv(
    report: dict[str, Any],
    output_path: str | Path,
) -> Path:
    """Write leaderboard CSV to *output_path*. Returns the path written."""
    output_path = Path(output_path)
    output_path.write_text(leaderboard_to_csv(report), encoding="utf-8")
    return output_path
