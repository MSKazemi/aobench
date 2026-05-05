"""T8 checker: Task ambiguity.

Checks for ambiguity in task specifications:
1. ``comparison_mode`` must be set for deterministic tasks (not left as None).
2. Tasks with relative-time phrasing must declare ``temporal_anchor="snapshot_timestamp"``.
3. For rubric tasks, warns if no ``rubric_id`` is set.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from aobench.cli.validators.base import CheckResult

if TYPE_CHECKING:
    from aobench.schemas.task import HPCTaskSpec

# Patterns that suggest relative-time phrasing
_RELATIVE_TIME_PATTERNS = [
    r"\blast\s+(hour|day|week|month|year)\b",
    r"\brecent(ly)?\b",
    r"\bcurren(t|tly)\b",
    r"\bnow\b",
    r"\btoday\b",
    r"\byesterday\b",
    r"\bpast\s+\d+\s+(hour|day|week|minute)\b",
    r"\bin\s+the\s+last\b",
]
_RELATIVE_PATTERNS = [re.compile(p, re.IGNORECASE) for p in _RELATIVE_TIME_PATTERNS]


def check_task_ambiguity(task: "HPCTaskSpec") -> CheckResult:
    """Check for ambiguity in task specification.

    Parameters
    ----------
    task:
        The HPC task spec to validate.

    Returns
    -------
    CheckResult
        PASS — no ambiguity detected.
        WARN — comparison_mode missing (deterministic) or temporal_anchor missing.
        FAIL — multiple critical ambiguity issues.
    """
    issues: list[str] = []
    warnings: list[str] = []

    # --- Check 1: comparison_mode for deterministic tasks ---
    if task.scoring_mode == "deterministic":
        if task.ground_truth is not None:
            comparison_mode = task.ground_truth.comparison_mode
            if comparison_mode is None:
                warnings.append(
                    "Deterministic task has no comparison_mode set in ground_truth. "
                    "Without an explicit comparison_mode, scorers may apply inconsistent "
                    "matching logic (exact vs numeric vs set)."
                )

    # --- Check 2: temporal_anchor for relative-time tasks ---
    question_text = task.question
    has_relative_time = any(p.search(question_text) for p in _RELATIVE_PATTERNS)

    if has_relative_time:
        if not task.temporal_anchor:
            warnings.append(
                f"Task question contains relative-time phrasing "
                f"(e.g., 'last', 'recent', 'current') but 'temporal_anchor' is not set. "
                f"Question: '{question_text[:80]}...'"
                if len(question_text) > 80
                else f"Task question contains relative-time phrasing but "
                f"'temporal_anchor' is not set. Question: '{question_text}'"
            )
        elif task.temporal_anchor != "snapshot_timestamp":
            issues.append(
                f"'temporal_anchor' is set to '{task.temporal_anchor}' but must be "
                "'snapshot_timestamp' for relative-time tasks."
            )

    # --- Check 3: rubric tasks should have a rubric_id ---
    if task.scoring_mode == "rubric" and not task.rubric_id:
        warnings.append(
            "Rubric-scored task has no rubric_id set. Without a rubric_id, "
            "the LLM judge cannot apply a structured evaluation rubric."
        )

    # --- Check 4: temporal field consistency ---
    if task.temporal == "prospective" and task.scoring_mode == "deterministic":
        warnings.append(
            "Task is marked 'prospective' but uses deterministic scoring. "
            "Prospective tasks typically require rubric-based evaluation."
        )

    if issues:
        return CheckResult(
            status="FAIL",
            detail=f"Task ambiguity FAIL for '{task.task_id}': {issues + warnings}",
            fix_suggestion=(
                "Fix all FAIL-level issues first: set temporal_anchor='snapshot_timestamp' "
                "for relative-time tasks.  Then address WARNs by setting comparison_mode "
                "and rubric_id as appropriate."
            ),
        )

    if warnings:
        return CheckResult(
            status="WARN",
            detail=f"Task ambiguity warnings for '{task.task_id}': {warnings}",
            fix_suggestion=(
                "Set comparison_mode on ground_truth for deterministic tasks, "
                "and set temporal_anchor='snapshot_timestamp' for relative-time questions."
            ),
        )

    return CheckResult(
        status="PASS",
        detail=f"No ambiguity detected for task '{task.task_id}'.",
    )
