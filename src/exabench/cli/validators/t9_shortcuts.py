"""T9 checker: Shortcut prevention.

Checks that the benchmark corpus does not accidentally encode shortcuts:
if a single canonical value (job_id, node_id, or username) appears in
more than 30% of tasks, an agent could guess the answer without
reasoning.

Threshold: > 30% frequency for any single value in the corpus.
"""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

from exabench.cli.validators.base import CheckResult

if TYPE_CHECKING:
    from exabench.schemas.task import HPCTaskSpec

_SHORTCUT_THRESHOLD = 0.30  # 30%

# Ground-truth field names that could enable shortcuts
_SHORTCUT_FIELDS = ["job_id", "node_id", "username", "user", "node"]


def check_shortcut_prevention(
    task: "HPCTaskSpec",
    task_corpus: list["HPCTaskSpec"],
) -> CheckResult:
    """Check that no canonical value dominates the corpus.

    Counts how often each value appears in the shortcut fields across all
    tasks in the corpus.  If any value appears in more than 30% of tasks,
    an agent could short-circuit reasoning by always returning that value.

    Parameters
    ----------
    task:
        The task being validated (used for task_id in the report).
    task_corpus:
        The full list of tasks in the benchmark corpus.

    Returns
    -------
    CheckResult
        PASS — no single value exceeds the 30% threshold.
        WARN — one or more values approach the threshold (> 20%).
        FAIL — one or more values exceed the 30% threshold.
        SKIP — corpus is too small (< 3 tasks) to meaningfully check.
    """
    n_tasks = len(task_corpus)

    if n_tasks < 3:
        return CheckResult(
            status="SKIP",
            detail=f"Corpus too small ({n_tasks} tasks) for shortcut check.",
        )

    value_counts: dict[str, Counter] = {field: Counter() for field in _SHORTCUT_FIELDS}

    for t in task_corpus:
        if t.ground_truth is None:
            continue
        gt_dict = t.ground_truth.model_dump(
            exclude={"comparison_mode", "derivation_query"}
        )
        for field_name in _SHORTCUT_FIELDS:
            val = gt_dict.get(field_name)
            if val is not None:
                value_counts[field_name][str(val)] += 1

    failures: list[str] = []
    warnings: list[str] = []

    for field_name, counter in value_counts.items():
        if not counter:
            continue
        for value, count in counter.most_common(3):
            freq = count / n_tasks
            if freq > _SHORTCUT_THRESHOLD:
                failures.append(
                    f"field='{field_name}' value='{value}' appears in "
                    f"{count}/{n_tasks} tasks ({freq:.0%}) — exceeds {_SHORTCUT_THRESHOLD:.0%} threshold"
                )
            elif freq > 0.20:
                warnings.append(
                    f"field='{field_name}' value='{value}' appears in "
                    f"{count}/{n_tasks} tasks ({freq:.0%}) — approaching threshold"
                )

    if failures:
        return CheckResult(
            status="FAIL",
            detail=f"Shortcut risk in corpus (checked from task '{task.task_id}'): {failures}",
            fix_suggestion=(
                "Diversify the ground-truth values across the corpus. "
                "No single job_id, node_id, or username should appear in more than "
                f"{_SHORTCUT_THRESHOLD:.0%} of tasks."
            ),
        )

    if warnings:
        return CheckResult(
            status="WARN",
            detail=(
                f"Potential shortcut risk (> 20% frequency) in corpus: {warnings}"
            ),
            fix_suggestion=(
                "Consider diversifying ground-truth values to reduce the risk "
                "of agents exploiting frequency shortcuts."
            ),
        )

    return CheckResult(
        status="PASS",
        detail=(
            f"No shortcut risk detected across {n_tasks} corpus tasks "
            f"(all canonical values below {_SHORTCUT_THRESHOLD:.0%} threshold)."
        ),
    )
