"""T10: Validity report generator.

Aggregates per-task CheckResult dicts into a structured JSON report.
The report records per-task pass/warn/fail status, overall corpus
statistics, and a summary suitable for CI gate decisions.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aobench.cli.validators.base import CheckResult, TaskValidityResult, aggregate_overall


def generate_validity_report(
    task_results: list[TaskValidityResult],
    output_path: str | Path | None = None,
    strict: bool = False,
) -> dict[str, Any]:
    """Aggregate per-task results into a validity report.

    Parameters
    ----------
    task_results:
        List of TaskValidityResult objects, one per task.
    output_path:
        Optional file path to write the JSON report.  If None, report is
        returned as a dict and not written to disk.
    strict:
        When True, WARN counts are included in the failure count.

    Returns
    -------
    dict
        The full validity report as a plain Python dict.
    """
    n_pass = sum(1 for r in task_results if r.overall == "PASS")
    n_warn = sum(1 for r in task_results if r.overall == "WARN")
    n_fail = sum(1 for r in task_results if r.overall == "FAIL")
    n_total = len(task_results)

    # Aggregate per-check statistics
    check_summary: dict[str, dict[str, int]] = {}
    for result in task_results:
        for check_name, check_result in result.checks.items():
            if check_name not in check_summary:
                check_summary[check_name] = {"PASS": 0, "WARN": 0, "FAIL": 0, "SKIP": 0}
            check_summary[check_name][check_result.status] += 1

    # Corpus-level overall
    if strict:
        corpus_pass = n_pass == n_total
    else:
        corpus_pass = n_fail == 0

    report: dict[str, Any] = {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "schema_version": "1.0",
        "corpus_valid": corpus_pass,
        "strict_mode": strict,
        "summary": {
            "total_tasks": n_total,
            "pass": n_pass,
            "warn": n_warn,
            "fail": n_fail,
            "pass_rate": round(n_pass / n_total, 4) if n_total > 0 else 0.0,
        },
        "check_summary": check_summary,
        "tasks": [
            _task_result_to_dict(r)
            for r in sorted(task_results, key=lambda r: r.task_id)
        ],
    }

    if output_path is not None:
        _write_report(report, output_path)

    return report


def _task_result_to_dict(result: TaskValidityResult) -> dict[str, Any]:
    """Convert a TaskValidityResult to a JSON-serialisable dict."""
    return {
        "task_id": result.task_id,
        "overall": result.overall,
        "release_ready": result.release_ready,
        "checks": {
            name: {
                "status": cr.status,
                "detail": cr.detail,
                "fix_suggestion": cr.fix_suggestion,
            }
            for name, cr in result.checks.items()
        },
    }


def _write_report(report: dict[str, Any], output_path: str | Path) -> None:
    """Write the report dict to a JSON file or stdout."""
    output_path = Path(output_path)
    if str(output_path) == "-":
        json.dump(report, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def format_text_report(report: dict[str, Any]) -> str:
    """Render a human-readable text summary of the validity report."""
    lines: list[str] = []
    s = report["summary"]
    lines.append(
        f"Task Validity Report  ({report['generated_at']})"
    )
    lines.append("=" * 60)
    lines.append(
        f"Total: {s['total_tasks']}  "
        f"PASS: {s['pass']}  WARN: {s['warn']}  FAIL: {s['fail']}  "
        f"Pass rate: {s['pass_rate']:.1%}"
    )
    lines.append(
        f"Corpus valid: {'YES' if report['corpus_valid'] else 'NO'}"
    )
    lines.append("")
    lines.append("Check breakdown:")
    for check_name, counts in sorted(report["check_summary"].items()):
        lines.append(
            f"  {check_name:8s}  "
            f"PASS={counts.get('PASS', 0):3d}  "
            f"WARN={counts.get('WARN', 0):3d}  "
            f"FAIL={counts.get('FAIL', 0):3d}  "
            f"SKIP={counts.get('SKIP', 0):3d}"
        )
    lines.append("")

    # List failing tasks
    failing = [t for t in report["tasks"] if t["overall"] == "FAIL"]
    if failing:
        lines.append(f"Failing tasks ({len(failing)}):")
        for t in failing:
            lines.append(f"  {t['task_id']}:")
            for check_name, cr in t["checks"].items():
                if cr["status"] == "FAIL":
                    lines.append(f"    [{check_name}] {cr['detail']}")
    else:
        lines.append("No failing tasks.")

    return "\n".join(lines)


def format_csv_report(report: dict[str, Any]) -> str:
    """Render the report as a flat CSV string."""
    import csv
    import io

    output = io.StringIO()
    writer = csv.writer(output)

    # Collect all check names from all tasks
    all_checks: list[str] = []
    for t in report["tasks"]:
        for cn in t["checks"]:
            if cn not in all_checks:
                all_checks.append(cn)
    all_checks.sort()

    header = ["task_id", "overall", "release_ready"] + [
        f"{cn}_status" for cn in all_checks
    ]
    writer.writerow(header)

    for t in report["tasks"]:
        row: list[str] = [
            t["task_id"],
            t["overall"],
            str(t["release_ready"]),
        ]
        for cn in all_checks:
            cr = t["checks"].get(cn)
            row.append(cr["status"] if cr else "SKIP")
        writer.writerow(row)

    return output.getvalue()
