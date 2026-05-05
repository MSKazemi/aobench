"""task_pipeline.py — Stage 1 orchestrator for AOBench-Lite selection.

Runs T1–T10 validity checks on all task specs and produces a structured
``validate_results`` dict consumable by ``lite_selector.run_stage1()``.

This module bridges ``validate_tasks.py`` (the T1–T10 CLI tool) and
``lite_selector.py`` (the 3-stage Lite pipeline).

Usage
-----
    from aobench.validation.task_pipeline import run_validation_pipeline

    validate_results = run_validation_pipeline(
        task_file="benchmark/tasks/task_set_v1.json",
        snapshot_dir="benchmark/environments/",
        catalog_path="benchmark/configs/hpc_tool_catalog.yaml",
    )
    # validate_results = {"JOB_USR_001": {"overall": "PASS", "checks": {...}}, ...}
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional


def run_validation_pipeline(
    task_file: str = "benchmark/tasks/task_set_v1.json",
    snapshot_dir: str = "benchmark/environments/",
    catalog_path: str = "benchmark/configs/hpc_tool_catalog.yaml",
    checks: Optional[list[str]] = None,
    strict: bool = False,
) -> dict[str, dict[str, Any]]:
    """Run T1–T10 checks and return per-task results keyed by task_id.

    Calls the validator framework used by ``validate_tasks.py`` and
    returns a dict suitable for passing to ``lite_selector.run_stage1()``.

    Parameters
    ----------
    task_file:
        Path to the HPC task corpus JSON (``task_set_v1.json``).
    snapshot_dir:
        Path to the environments directory (for T2, T3, T5, T6, T7).
    catalog_path:
        Path to the tool catalog YAML (for T1, T5).
    checks:
        Subset of checks to run (default: all T1–T9).
    strict:
        When True, WARN results are treated as FAIL.

    Returns
    -------
    dict[str, dict[str, Any]]
        ``{task_id: {"overall": "PASS"|"WARN"|"FAIL", "checks": {...}}}``.
    """
    from aobench.tasks.task_loader import load_hpc_task_set
    from aobench.cli.validators.base import TaskValidityResult, aggregate_overall
    from aobench.cli.validators.t1_tool_versions import check_tool_version_pinning
    from aobench.cli.validators.t2_tool_setup import check_tool_setup
    from aobench.cli.validators.t3_oracle_solvability import check_oracle_solvability
    from aobench.cli.validators.t4_residual_state import check_residual_state_policy
    from aobench.cli.validators.t5_gt_isolation import check_ground_truth_isolation
    from aobench.cli.validators.t6_env_freeze import check_environment_freeze
    from aobench.cli.validators.t7_gt_correctness import check_ground_truth_correctness
    from aobench.cli.validators.t8_ambiguity import check_task_ambiguity
    from aobench.cli.validators.t9_shortcuts import check_shortcut_prevention

    _ALL_CHECKS = ["t1", "t2", "t3", "t4", "t5", "t6", "t7", "t8", "t9"]
    enabled = checks if checks else _ALL_CHECKS

    task_file_path = Path(task_file)
    snapshot_dir_path = Path(snapshot_dir)
    catalog_path_obj = Path(catalog_path)

    all_tasks = load_hpc_task_set(task_file_path)

    # Load catalog for T1 and T5
    catalog = None
    if any(c in enabled for c in ("t1", "t5")):
        try:
            from aobench.tools.catalog_loader import load_catalog
            catalog = load_catalog(catalog_path_obj if catalog_path_obj.exists() else None)
        except Exception:
            pass

    # T6 is corpus-level — run once
    t6_result = None
    if "t6" in enabled:
        t6_result = check_environment_freeze(snapshot_dir_path)

    results: dict[str, dict[str, Any]] = {}

    for task in all_tasks:
        task_checks: dict[str, Any] = {}

        if "t1" in enabled:
            if catalog is not None:
                task_checks["t1"] = check_tool_version_pinning(task, catalog)
            else:
                from aobench.cli.validators.base import CheckResult
                task_checks["t1"] = CheckResult(status="SKIP", detail="Catalog not loaded.")

        if "t2" in enabled:
            task_checks["t2"] = check_tool_setup(task, snapshot_dir_path)

        if "t3" in enabled:
            task_checks["t3"] = check_oracle_solvability(task, snapshot_dir_path)

        if "t4" in enabled:
            task_checks["t4"] = check_residual_state_policy(task)

        if "t5" in enabled:
            if catalog is not None:
                task_checks["t5"] = check_ground_truth_isolation(task, catalog, snapshot_dir_path)
            else:
                from aobench.cli.validators.base import CheckResult
                task_checks["t5"] = CheckResult(status="SKIP", detail="Catalog not loaded.")

        if "t6" in enabled and t6_result is not None:
            task_checks["t6"] = t6_result

        if "t7" in enabled:
            task_checks["t7"] = check_ground_truth_correctness(task, snapshot_dir_path, judge=None)

        if "t8" in enabled:
            task_checks["t8"] = check_task_ambiguity(task)

        if "t9" in enabled:
            task_checks["t9"] = check_shortcut_prevention(task, all_tasks)

        overall = aggregate_overall(task_checks, strict=strict)
        results[task.task_id] = {
            "overall": overall,
            "checks": {
                k: {"status": v.status, "detail": v.detail}
                for k, v in task_checks.items()
                if hasattr(v, "status")
            },
        }

    return results
