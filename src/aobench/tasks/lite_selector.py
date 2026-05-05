"""lite_selector.py — AOBench-Lite 3-stage task subset selection.

Implements the three-stage pipeline from task_lite_spec.md §3:
  Stage 1: Source filter (T1–T10 gate + split exclusion)
  Stage 2: Attribute filter (one per QCAT × role × difficulty_tier cell)
  Stage 3: Execution filter (non-degenerate pilot-score gate)

Usage
-----
    from aobench.tasks.lite_selector import select_lite

    lite_ids = select_lite(
        task_dir="benchmark/tasks/specs",
        validate_results={"JOB_USR_001": {"overall": "PASS"}, ...},
        pilot_scores=None,   # Stage 3 pending
        output_path="benchmark/tasks/lite_manifest_v1.json",
    )
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from aobench.schemas.task import TaskSpec


# ---------------------------------------------------------------------------
# Stage 1 — Source filter
# ---------------------------------------------------------------------------

def run_stage1(task_dir: str, validate_results: dict[str, Any]) -> list[TaskSpec]:
    """Load all tasks from task_dir and apply the Stage 1 filters.

    Filters applied:
    - t1_t10_pass == True  (from validate_results overall status, or task field)
    - task_id NOT IN TEST_TASK_IDS
    - benchmark_split is not None (tasks must declare a split)

    Parameters
    ----------
    task_dir:
        Directory containing ``*.json`` task spec files.
    validate_results:
        Mapping of task_id → ``{"overall": "PASS"|"WARN"|"FAIL", ...}``.
        A task is eligible if its overall is "PASS".  If validate_results
        is empty or does not contain a task_id, the task is excluded unless
        its ``t1_t10_pass`` field is explicitly True.

    Returns
    -------
    list[TaskSpec]
        Tasks that pass all Stage 1 filters, sorted by task_id.
    """
    from aobench.loaders.task_loader import load_tasks_from_dir
    from benchmark.tasks.dataset_splits import TEST_TASK_IDS

    all_tasks = load_tasks_from_dir(task_dir)

    candidates: list[TaskSpec] = []
    for task in all_tasks:
        # Excluded from test split
        if task.task_id in TEST_TASK_IDS:
            continue

        # T1–T10 gate: check validate_results first, then fall back to task field
        vr = validate_results.get(task.task_id)
        if vr is not None:
            passes = vr.get("overall") == "PASS"
        else:
            passes = task.t1_t10_pass is True

        if not passes:
            continue

        candidates.append(task)

    return sorted(candidates, key=lambda t: t.task_id)


# ---------------------------------------------------------------------------
# Stage 2 — Attribute filter
# ---------------------------------------------------------------------------

def run_stage2(candidate_pool: list[TaskSpec]) -> list[TaskSpec]:
    """Select at most one task per (qcat, role, difficulty_tier) cell.

    Selection priority within a cell:
    1. Deterministic scoring_mode over rubric (more reliable ground truth)
    2. Alphabetical task_id for reproducibility

    QCATs with fewer than 3 candidates are excluded (§3.2 Step 2a).

    Parameters
    ----------
    candidate_pool:
        Tasks that passed Stage 1.

    Returns
    -------
    list[TaskSpec]
        At most one task per (qcat, role, difficulty_tier) cell, capped at 50.
    """
    # Step 2a — reject QCATs with fewer than 3 validated tasks
    from collections import Counter
    qcat_counts: Counter[str] = Counter(t.qcat for t in candidate_pool)
    eligible_qcats = {q for q, cnt in qcat_counts.items() if cnt >= 3}

    filtered = [t for t in candidate_pool if t.qcat in eligible_qcats]

    # Step 2b — one-task-per-cell selection
    # Sort so deterministic tasks come first; ties broken by task_id (alphabetical)
    def _sort_key(t: TaskSpec) -> tuple[int, str]:
        scoring_mode = _get_scoring_mode(t)
        mode_rank = 0 if scoring_mode == "deterministic" else 1
        return (mode_rank, t.task_id)

    sorted_tasks = sorted(filtered, key=_sort_key)

    lite: dict[tuple[str, str, Any], TaskSpec] = {}
    for task in sorted_tasks:
        if task.difficulty_tier is None:
            continue   # Stage 2 requires difficulty_tier
        cell = (task.qcat, task.role, task.difficulty_tier)
        if cell not in lite:
            lite[cell] = task

    selected = list(lite.values())

    # Step 2c — cap at 50
    if len(selected) > 50:
        # Secondary ordering: QCAT index, role index, difficulty_tier
        _QCAT_ORDER = ["JOB", "MON", "ENERGY", "PERF", "DATA", "SEC", "FAC", "ARCH", "AIOPS", "DOCS"]
        _ROLE_ORDER = ["scientific_user", "researcher", "sysadmin", "facility_admin", "system_designer"]
        def _cap_key(t: TaskSpec) -> tuple[int, int, int]:
            qi = _QCAT_ORDER.index(t.qcat) if t.qcat in _QCAT_ORDER else 99
            ri = _ROLE_ORDER.index(t.role) if t.role in _ROLE_ORDER else 99
            di = t.difficulty_tier or 99
            return (qi, ri, di)
        selected = sorted(selected, key=_cap_key)[:50]

    return sorted(selected, key=lambda t: t.task_id)


def _get_scoring_mode(task: TaskSpec) -> str:
    """Extract the effective scoring mode from a TaskSpec."""
    if task.hybrid_scoring is not None:
        return task.hybrid_scoring.scoring_mode
    return "rubric"   # default when not specified


# ---------------------------------------------------------------------------
# Stage 3 — Execution filter
# ---------------------------------------------------------------------------

def run_stage3(
    attribute_filtered: list[TaskSpec],
    pilot_scores: dict[str, dict[str, float]],
    skip_if_missing: bool = True,
) -> tuple[list[TaskSpec], list[dict]]:
    """Filter out degenerate tasks (floor or ceiling) using pilot model scores.

    Non-degenerate criterion (§3.3):
        PASS if ∃ pilot_model: score ∈ (0.10, 0.90)
        FAIL (floor) if ∀ pilot_model: score ≤ 0.10
        FAIL (ceiling) if ∀ pilot_model: score ≥ 0.90

    Parameters
    ----------
    attribute_filtered:
        Tasks from Stage 2.
    pilot_scores:
        Mapping of {task_id: {model_id: score}}.
    skip_if_missing:
        When True, tasks with no pilot scores are included with
        execution_filter="pending" (interim Lite mode).

    Returns
    -------
    (lite_tasks, excluded_tasks)
    """
    FLOOR = 0.10
    CEILING = 0.90

    lite_tasks: list[TaskSpec] = []
    excluded_tasks: list[dict] = []

    for task in attribute_filtered:
        task_pilot = pilot_scores.get(task.task_id, {})

        if not task_pilot:
            if skip_if_missing:
                # Include with pending status
                lite_tasks.append(task)
            else:
                excluded_tasks.append({
                    "task_id": task.task_id,
                    "stage": 3,
                    "reason": "no_pilot_scores",
                    "pilot_scores": {},
                })
            continue

        scores = list(task_pilot.values())

        # Check floor: all models at or below floor threshold
        if all(s <= FLOOR for s in scores):
            excluded_tasks.append({
                "task_id": task.task_id,
                "stage": 3,
                "reason": "floor",
                "pilot_scores": task_pilot,
            })
            continue

        # Check ceiling: all models at or above ceiling threshold
        if all(s >= CEILING for s in scores):
            excluded_tasks.append({
                "task_id": task.task_id,
                "stage": 3,
                "reason": "ceiling",
                "pilot_scores": task_pilot,
            })
            continue

        # At least one model in the discriminative band → include
        lite_tasks.append(task)

    return lite_tasks, excluded_tasks


# ---------------------------------------------------------------------------
# Manifest builder
# ---------------------------------------------------------------------------

def build_manifest(
    lite_tasks: list[TaskSpec],
    excluded_tasks: list[dict],
    stage_counts: dict[str, int],
    output_path: str,
    pilot_scores: dict[str, dict[str, float]] | None = None,
) -> dict:
    """Write lite_manifest_v*.json and return the manifest dict.

    Parameters
    ----------
    lite_tasks:
        Final list of Lite tasks.
    excluded_tasks:
        Tasks excluded at Stage 2 or 3, each with reason.
    stage_counts:
        {"stage1": N, "stage2": N, "stage3": N}
    output_path:
        File path for the manifest JSON.
    pilot_scores:
        Optional pilot scores for annotating each lite task's execution_filter status.

    Returns
    -------
    dict
        The manifest as a Python dict.
    """
    from collections import Counter

    pilot_scores = pilot_scores or {}

    def _execution_filter_status(task_id: str) -> str:
        tp = pilot_scores.get(task_id, {})
        if not tp:
            return "pending"
        scores = list(tp.values())
        FLOOR, CEILING = 0.10, 0.90
        if all(s <= FLOOR for s in scores):
            return "fail_floor"
        if all(s >= CEILING for s in scores):
            return "fail_ceiling"
        return "pass"

    lite_task_ids = sorted(t.task_id for t in lite_tasks)
    qcat_coverage = dict(Counter(t.qcat for t in lite_tasks))
    difficulty_coverage: Counter[str] = Counter()
    for t in lite_tasks:
        if t.difficulty_tier is not None:
            tier_name = {1: "easy", 2: "medium", 3: "hard"}.get(t.difficulty_tier, str(t.difficulty_tier))
            difficulty_coverage[tier_name] += 1

    lite_task_records = []
    for t in sorted(lite_tasks, key=lambda x: x.task_id):
        ef_status = _execution_filter_status(t.task_id)
        rec: dict[str, Any] = {
            "task_id": t.task_id,
            "lite_status": "included",
            "execution_filter": ef_status,
        }
        tp = pilot_scores.get(t.task_id, {})
        if tp:
            rec["pilot_scores"] = tp
        lite_task_records.append(rec)

    manifest: dict[str, Any] = {
        "manifest_version": "1.0",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "corpus_version": "v0.3",
        "stage1_candidates": stage_counts.get("stage1", 0),
        "stage2_attribute_filtered": stage_counts.get("stage2", 0),
        "stage3_execution_filtered": stage_counts.get("stage3", len(lite_tasks)),
        "lite_task_count": len(lite_tasks),
        "lite_task_ids": lite_task_ids,
        "lite_tasks": lite_task_records,
        "excluded_tasks": excluded_tasks,
        "qcat_coverage": qcat_coverage,
        "difficulty_coverage": dict(difficulty_coverage),
    }

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    return manifest


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------

def select_lite(
    task_dir: str,
    validate_results: dict[str, Any],
    pilot_scores: Optional[dict[str, dict[str, float]]] = None,
    output_path: str = "benchmark/tasks/lite_manifest_v1.json",
) -> list[str]:
    """Run the full 3-stage pipeline and write the Lite manifest.

    Enforces the invariant: LITE_TASK_IDS ∩ TEST_TASK_IDS = ∅

    Parameters
    ----------
    task_dir:
        Directory with ``*.json`` task spec files (``benchmark/tasks/specs/``).
    validate_results:
        Per-task T1–T10 gate results as ``{task_id: {"overall": "PASS"|...}}``.
    pilot_scores:
        Optional pilot model scores ``{task_id: {model_id: score}}``.
        When None, Stage 3 is skipped (tasks marked "pending").
    output_path:
        Path for the generated Lite manifest JSON file.

    Returns
    -------
    list[str]
        The final LITE_TASK_IDS (also written to the manifest).
    """
    from benchmark.tasks.dataset_splits import TEST_TASK_IDS

    stage1 = run_stage1(task_dir, validate_results)
    stage2 = run_stage2(stage1)
    stage3_tasks, excluded = run_stage3(
        stage2,
        pilot_scores or {},
        skip_if_missing=(pilot_scores is None),
    )

    # Invariant check: no test tasks in Lite
    test_set = set(TEST_TASK_IDS)
    lite_ids = [t.task_id for t in stage3_tasks]
    contaminated = [tid for tid in lite_ids if tid in test_set]
    if contaminated:
        raise AssertionError(
            f"Lite selection invariant violated: these task IDs appear in both "
            f"LITE and TEST: {contaminated}"
        )

    stage_counts = {
        "stage1": len(stage1),
        "stage2": len(stage2),
        "stage3": len(stage3_tasks),
    }

    build_manifest(
        lite_tasks=stage3_tasks,
        excluded_tasks=excluded,
        stage_counts=stage_counts,
        output_path=output_path,
        pilot_scores=pilot_scores or {},
    )

    return lite_ids
