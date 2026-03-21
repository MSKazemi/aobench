"""T5 checker: Ground-truth isolation.

Verifies that ground-truth answer values are not trivially discoverable
from the files and tool paths that the agent can access.

Specifically:
1. For diagnostic tasks: checks that any files listed in
   ``ground_truth_files_excluded`` are actually absent from agent-visible
   tool paths.
2. For all tasks with ground truth: checks that the raw ground-truth
   value does not appear verbatim in agent-visible snapshot files
   (incident logs, etc.).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from exabench.cli.validators.base import CheckResult

if TYPE_CHECKING:
    from exabench.schemas.task import HPCTaskSpec
    from exabench.tools.catalog_loader import ToolCatalog

# Subdirectories that agents can typically read via tool calls
_AGENT_VISIBLE_DIRS = ["docs", "slurm", "telemetry"]

# Subdirectories that are considered restricted / not agent-visible
_RESTRICTED_DIRS = ["incidents", "policy"]


def check_ground_truth_isolation(
    task: "HPCTaskSpec",
    catalog: "ToolCatalog",
    snapshot_dir: str | Path,
) -> CheckResult:
    """Check that ground-truth values are not trivially discoverable by the agent.

    Parameters
    ----------
    task:
        The HPC task spec to validate.
    catalog:
        Loaded ToolCatalog (used to determine which tool paths are agent-visible).
    snapshot_dir:
        Root environments directory.

    Returns
    -------
    CheckResult
        PASS — no ground-truth leakage detected.
        WARN — ground-truth file exclusion list is empty for a diagnostic task.
        FAIL — excluded files are present in agent-visible paths, or GT value
               appears verbatim in an agent-accessible file.
        SKIP — no ground truth defined, or snapshot missing.
    """
    if task.ground_truth is None:
        return CheckResult(
            status="SKIP",
            detail="Task has no ground_truth defined; skipping isolation check.",
        )

    snapshot_dir = Path(snapshot_dir)
    env_path = snapshot_dir / task.snapshot_id

    if not env_path.exists():
        return CheckResult(
            status="SKIP",
            detail=f"Snapshot '{task.snapshot_id}' not found; skipping isolation check.",
        )

    issues: list[str] = []

    # --- Check 1: ground_truth_files_excluded ---
    excluded_files = task.ground_truth_files_excluded
    if not excluded_files and task.data_type in ("rbac", "dataflow"):
        # Diagnostic / policy tasks should declare exclusions
        issues.append(
            "Diagnostic task has no ground_truth_files_excluded declared; "
            "agent may be able to read the answer directly from policy/incident files."
        )

    for rel_path in excluded_files:
        # The file should NOT be in agent-visible directories
        for visible_dir in _AGENT_VISIBLE_DIRS:
            visible_path = env_path / visible_dir / rel_path
            if visible_path.exists():
                issues.append(
                    f"Excluded file '{rel_path}' is present in agent-visible "
                    f"directory '{visible_dir}/' — agent can access the answer directly."
                )

    # --- Check 2: GT value leakage in agent-visible files ---
    gt_values = _extract_gt_string_values(task)
    if gt_values:
        leaks = _check_value_leakage(gt_values, env_path)
        issues.extend(leaks)

    if issues:
        # Distinguish FAIL (hard leakage) from WARN (soft / advisory)
        hard_issues = [i for i in issues if "is present in agent-visible" in i]
        if hard_issues:
            return CheckResult(
                status="FAIL",
                detail=f"Ground-truth isolation failures: {issues}",
                fix_suggestion=(
                    "Move or remove excluded files from agent-visible directories, "
                    "or redact ground-truth values from agent-accessible snapshot files."
                ),
            )
        return CheckResult(
            status="WARN",
            detail=f"Ground-truth isolation warnings: {issues}",
            fix_suggestion=(
                "Declare ground_truth_files_excluded for diagnostic tasks, or verify "
                "that ground-truth values are not trivially discoverable."
            ),
        )

    return CheckResult(
        status="PASS",
        detail=(
            f"No ground-truth leakage detected for task '{task.task_id}'."
        ),
    )


def _extract_gt_string_values(task: "HPCTaskSpec") -> list[str]:
    """Extract scalar string/int values from ground_truth for leakage checks."""
    if task.ground_truth is None:
        return []

    values: list[str] = []
    # HPCGroundTruth uses extra="allow", so extra fields are in __pydantic_extra__
    gt_dict = task.ground_truth.model_dump(exclude={"comparison_mode", "derivation_query"})

    def _collect(obj: object) -> None:
        if isinstance(obj, str) and len(obj) > 3:
            values.append(obj)
        elif isinstance(obj, int) and obj > 100:
            values.append(str(obj))
        elif isinstance(obj, dict):
            for v in obj.values():
                _collect(v)
        elif isinstance(obj, list):
            for item in obj:
                _collect(item)

    _collect(gt_dict)
    return values


def _check_value_leakage(gt_values: list[str], env_path: Path) -> list[str]:
    """Check if any GT value appears verbatim in agent-visible JSON/text files."""
    leaks: list[str] = []

    for visible_dir in _AGENT_VISIBLE_DIRS:
        dir_path = env_path / visible_dir
        if not dir_path.exists():
            continue

        for data_file in dir_path.rglob("*.json"):
            try:
                content = data_file.read_text(encoding="utf-8")
            except Exception:  # noqa: BLE001
                continue

            for gt_val in gt_values:
                # Only flag exact value matches that would make the task trivial
                # (i.e., the GT value is the _entire_ field value, not just a substring)
                if f'"{gt_val}"' in content or f": {gt_val}," in content:
                    rel = data_file.relative_to(env_path)
                    leaks.append(
                        f"GT value '{gt_val}' appears verbatim in agent-visible "
                        f"file '{rel}'"
                    )
                    break  # one leak per file is enough

    return leaks
