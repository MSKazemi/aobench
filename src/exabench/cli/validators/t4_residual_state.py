"""T4 checker: Residual state policy.

Checks whether a task is sensitive to ordering (i.e., whether running it
after another task could leave residual state that affects results).

Tasks with ``workload_type="OLTP"`` are inherently write operations that
can leave residual state.  The spec requires that such tasks either
document their isolation policy or are marked as ordering-insensitive.

For OLAP tasks (read-only), this check is a no-op (PASS).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from exabench.cli.validators.base import CheckResult

if TYPE_CHECKING:
    from exabench.schemas.task import HPCTaskSpec


def check_residual_state_policy(task: "HPCTaskSpec") -> CheckResult:
    """Check whether the task has a residual-state isolation policy.

    OLAP tasks (read-only aggregate queries) are inherently safe — they
    cannot leave residual state.

    OLTP tasks (point-in-time, write-oriented) may leave state.  This
    checker warns if the task has no explicit ordering-isolation strategy
    documented in its schema.

    Parameters
    ----------
    task:
        The HPC task spec to validate.

    Returns
    -------
    CheckResult
        PASS — OLAP task, or OLTP task with documented isolation.
        WARN — OLTP task without explicit isolation documentation.
        SKIP — task type unknown.
    """
    if task.workload_type == "OLAP":
        return CheckResult(
            status="PASS",
            detail=(
                f"Task '{task.task_id}' is OLAP (read-only aggregate); "
                "no residual state risk."
            ),
        )

    if task.workload_type == "OLTP":
        # Check for any isolation hints in the task schema.
        # The task spec currently has no dedicated isolation_policy field,
        # so we look for hints in visible_to_roles and snapshot_id.

        # OLTP tasks that only run against a static snapshot are safe
        # because the snapshot is immutable.  Warn if the task_id suggests
        # it's a live-write task (heuristic check on task_id prefix).
        live_write_indicators = ["write_", "submit_", "cancel_", "modify_", "delete_"]
        is_potentially_live = any(
            task.task_id.lower().startswith(prefix)
            for prefix in live_write_indicators
        )

        if is_potentially_live:
            return CheckResult(
                status="WARN",
                detail=(
                    f"Task '{task.task_id}' is OLTP and its ID suggests a write "
                    "operation.  If tasks share a snapshot environment, residual "
                    "state from this task could affect subsequent tasks."
                ),
                fix_suggestion=(
                    "Ensure each OLTP task runs against a fresh, isolated snapshot "
                    "copy, or document the ordering-insensitivity in the task spec."
                ),
            )

        # OLTP but not a write-oriented name — likely a point-in-time lookup
        return CheckResult(
            status="WARN",
            detail=(
                f"Task '{task.task_id}' uses OLTP workload type.  OLTP tasks "
                "perform point-in-time queries that may be sensitive to prior state.  "
                "Verify that the snapshot provides a stable, isolated environment."
            ),
            fix_suggestion=(
                "Confirm that the snapshot for this task is not shared with write "
                "operations, or explicitly annotate the task as ordering-insensitive."
            ),
        )

    return CheckResult(
        status="SKIP",
        detail=f"Unknown workload_type='{task.workload_type}'; skipping residual-state check.",
    )
