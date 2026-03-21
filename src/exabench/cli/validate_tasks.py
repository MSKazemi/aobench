"""validate_tasks.py — Run T1–T10 task validity checks on the HPC task corpus.

Usage
-----
    python -m exabench.cli.validate_tasks [OPTIONS] [TASK_IDS...]

Options
-------
    --task-file PATH       Task corpus JSON (default: benchmark/tasks/task_set_v1.json)
    --snapshot-dir PATH    Environments directory (default: benchmark/environments/)
    --catalog PATH         Tool catalog YAML (default: benchmark/configs/hpc_tool_catalog.yaml)
    --checks TEXT          Comma-separated subset of checks to run (default: all)
    --output PATH          Output report path (default: stdout with '-')
    --format TEXT          Output format: json | text | csv (default: json)
    --fail-fast            Stop after first task failure (default: False)
    --oracle-judge         Run oracle solvability check using LLM judge for rubric tasks
    --strict               Any WARN result is treated as FAIL (default: False)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

_DEFAULT_TASK_FILE = "benchmark/tasks/task_set_v1.json"
_DEFAULT_SNAPSHOT_DIR = "benchmark/environments/"
_DEFAULT_CATALOG = "benchmark/configs/hpc_tool_catalog.yaml"

_ALL_CHECKS = ["t1", "t2", "t3", "t4", "t5", "t6", "t7", "t8", "t9"]


def main(argv: Optional[list[str]] = None) -> int:
    """Entry point for validate_tasks.  Returns 0 on success, 1 on failure."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    # Resolve paths
    task_file = Path(args.task_file)
    snapshot_dir = Path(args.snapshot_dir)
    catalog_path = Path(args.catalog)
    output_path = args.output
    fmt = args.format.lower()
    strict = args.strict
    fail_fast = args.fail_fast
    task_id_filter = set(args.task_ids) if args.task_ids else None

    # Determine which checks to run
    if args.checks and args.checks.lower() != "all":
        enabled_checks = [c.strip().lower() for c in args.checks.split(",")]
    else:
        enabled_checks = list(_ALL_CHECKS)

    # --- Load task corpus ---
    if not task_file.exists():
        print(f"ERROR: Task file not found: '{task_file}'", file=sys.stderr)
        return 1

    try:
        from exabench.tasks.task_loader import load_hpc_task_set
        all_tasks = load_hpc_task_set(task_file)
    except Exception as exc:
        print(f"ERROR: Failed to load task file '{task_file}': {exc}", file=sys.stderr)
        return 1

    if task_id_filter:
        tasks = [t for t in all_tasks if t.task_id in task_id_filter]
        unknown = task_id_filter - {t.task_id for t in tasks}
        if unknown:
            print(
                f"WARNING: Unknown task IDs (skipped): {sorted(unknown)}",
                file=sys.stderr,
            )
    else:
        tasks = all_tasks

    if not tasks:
        print("ERROR: No tasks to validate.", file=sys.stderr)
        return 1

    # --- Load catalog (for T1, T5) ---
    catalog = None
    if any(c in enabled_checks for c in ("t1", "t5")):
        try:
            from exabench.tools.catalog_loader import load_catalog
            catalog = load_catalog(catalog_path if catalog_path.exists() else None)
        except Exception as exc:
            print(
                f"WARNING: Could not load catalog '{catalog_path}': {exc}. "
                "T1 and T5 checks will be SKIPped.",
                file=sys.stderr,
            )

    print(
        f"Validating {len(tasks)} task(s) with checks: {enabled_checks}",
        file=sys.stderr,
    )

    # --- Run checks ---
    from exabench.cli.validators.base import TaskValidityResult, aggregate_overall
    from exabench.cli.validators.t1_tool_versions import check_tool_version_pinning
    from exabench.cli.validators.t2_tool_setup import check_tool_setup
    from exabench.cli.validators.t3_oracle_solvability import check_oracle_solvability
    from exabench.cli.validators.t4_residual_state import check_residual_state_policy
    from exabench.cli.validators.t5_gt_isolation import check_ground_truth_isolation
    from exabench.cli.validators.t6_env_freeze import check_environment_freeze
    from exabench.cli.validators.t7_gt_correctness import check_ground_truth_correctness
    from exabench.cli.validators.t8_ambiguity import check_task_ambiguity
    from exabench.cli.validators.t9_shortcuts import check_shortcut_prevention
    from exabench.cli.validators.t10_reporting import (
        format_csv_report,
        format_text_report,
        generate_validity_report,
    )

    task_results: list[TaskValidityResult] = []
    had_failure = False

    # T6 is corpus-level (not per-task) — run once
    t6_result = None
    if "t6" in enabled_checks:
        t6_result = check_environment_freeze(snapshot_dir)

    for task in tasks:
        checks = {}

        if "t1" in enabled_checks:
            if catalog is not None:
                checks["t1"] = check_tool_version_pinning(task, catalog)
            else:
                from exabench.cli.validators.base import CheckResult
                checks["t1"] = CheckResult(
                    status="SKIP",
                    detail="Catalog not loaded; T1 skipped.",
                )

        if "t2" in enabled_checks:
            checks["t2"] = check_tool_setup(task, snapshot_dir)

        if "t3" in enabled_checks:
            checks["t3"] = check_oracle_solvability(task, snapshot_dir)

        if "t4" in enabled_checks:
            checks["t4"] = check_residual_state_policy(task)

        if "t5" in enabled_checks:
            if catalog is not None:
                checks["t5"] = check_ground_truth_isolation(task, catalog, snapshot_dir)
            else:
                from exabench.cli.validators.base import CheckResult
                checks["t5"] = CheckResult(
                    status="SKIP",
                    detail="Catalog not loaded; T5 skipped.",
                )

        # T6 result is shared across all tasks
        if "t6" in enabled_checks and t6_result is not None:
            checks["t6"] = t6_result

        if "t7" in enabled_checks:
            judge = None  # LLM judge not implemented here
            checks["t7"] = check_ground_truth_correctness(task, snapshot_dir, judge=judge)

        if "t8" in enabled_checks:
            checks["t8"] = check_task_ambiguity(task)

        if "t9" in enabled_checks:
            checks["t9"] = check_shortcut_prevention(task, all_tasks)

        overall = aggregate_overall(checks, strict=strict)
        result = TaskValidityResult(
            task_id=task.task_id,
            overall=overall,
            checks=checks,
        )
        task_results.append(result)

        status_icon = {"PASS": ".", "WARN": "W", "FAIL": "F"}[overall]
        print(status_icon, end="", flush=True, file=sys.stderr)

        if overall == "FAIL":
            had_failure = True
            if fail_fast:
                print("\nFail-fast: stopping after first failure.", file=sys.stderr)
                break

    print("", file=sys.stderr)  # newline after progress dots

    # --- Generate report ---
    report = generate_validity_report(task_results, output_path=None, strict=strict)

    # Format and output
    if fmt == "json":
        formatted = json.dumps(report, indent=2)
    elif fmt == "text":
        formatted = format_text_report(report)
    elif fmt == "csv":
        formatted = format_csv_report(report)
    else:
        print(f"ERROR: Unknown format '{fmt}'. Use: json | text | csv", file=sys.stderr)
        return 1

    if output_path and output_path != "-":
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(formatted + "\n", encoding="utf-8")
        print(f"Report written to: {out_path}", file=sys.stderr)
    else:
        print(formatted)

    # Summary line
    s = report["summary"]
    print(
        f"\nSummary: {s['total_tasks']} tasks — "
        f"PASS={s['pass']} WARN={s['warn']} FAIL={s['fail']} "
        f"({'VALID' if report['corpus_valid'] else 'INVALID'})",
        file=sys.stderr,
    )

    return 1 if (had_failure or not report["corpus_valid"]) else 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="validate_tasks",
        description="Run T1–T10 task validity checks on the HPC task corpus.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "task_ids",
        nargs="*",
        metavar="TASK_ID",
        help="Optional task IDs to validate (default: all tasks in task-file)",
    )
    parser.add_argument(
        "--task-file",
        default=_DEFAULT_TASK_FILE,
        metavar="PATH",
        help="Task corpus JSON file",
    )
    parser.add_argument(
        "--snapshot-dir",
        default=_DEFAULT_SNAPSHOT_DIR,
        metavar="PATH",
        help="Environments root directory",
    )
    parser.add_argument(
        "--catalog",
        default=_DEFAULT_CATALOG,
        metavar="PATH",
        help="Tool catalog YAML",
    )
    parser.add_argument(
        "--checks",
        default="all",
        metavar="TEXT",
        help="Comma-separated checks to run, e.g. 't1,t3,t8' (default: all)",
    )
    parser.add_argument(
        "--output",
        default=None,
        metavar="PATH",
        help="Output report path (default: stdout)",
    )
    parser.add_argument(
        "--format",
        default="json",
        choices=["json", "text", "csv"],
        help="Output format",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        default=False,
        help="Stop after first task failure",
    )
    parser.add_argument(
        "--oracle-judge",
        action="store_true",
        default=False,
        help="Run oracle solvability check using LLM judge for rubric tasks",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        default=False,
        help="Treat WARN as FAIL",
    )
    return parser


if __name__ == "__main__":
    sys.exit(main())
