"""T7 checker: Ground-truth correctness (deterministic path).

For deterministic tasks with a ``derivation_query``, executes the query
against the snapshot and compares the result to the declared ground truth,
applying the task's ``tolerance_pct`` for numeric comparisons.

For tasks without a ``derivation_query``, performs a structural sanity
check: verifies that all expected GT fields are present and non-null.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from exabench.cli.validators.base import CheckResult

if TYPE_CHECKING:
    from exabench.schemas.task import HPCTaskSpec


def check_ground_truth_correctness(
    task: "HPCTaskSpec",
    snapshot_dir: str | Path,
    judge: Any = None,  # Reserved for future LLM-judge path
) -> CheckResult:
    """Verify ground-truth values against snapshot data.

    Parameters
    ----------
    task:
        The HPC task spec to validate.
    snapshot_dir:
        Root environments directory.
    judge:
        Optional LLM judge (reserved; not used for deterministic tasks).

    Returns
    -------
    CheckResult
        PASS — GT values match derivation query result (within tolerance).
        FAIL — GT values differ from derivation query result.
        WARN — GT defined but no derivation_query; structural check only.
        SKIP — rubric task, no GT defined, or snapshot missing.
    """
    if task.scoring_mode == "rubric":
        return CheckResult(
            status="SKIP",
            detail="Rubric-scored task; GT correctness check not applicable.",
        )

    if task.ground_truth is None:
        return CheckResult(
            status="SKIP",
            detail="No ground_truth defined; skipping GT correctness check.",
        )

    snapshot_dir = Path(snapshot_dir)
    env_path = snapshot_dir / task.snapshot_id

    if not env_path.exists():
        return CheckResult(
            status="SKIP",
            detail=f"Snapshot '{task.snapshot_id}' not found; skipping GT correctness check.",
        )

    derivation_query = task.ground_truth.derivation_query

    if not derivation_query:
        # No query — do structural sanity check
        return _structural_check(task)

    # Execute derivation query
    try:
        from exabench.cli.validators.t3_oracle_solvability import _eval_query
        queried_result = _eval_query(derivation_query, env_path)
    except Exception as exc:  # noqa: BLE001
        return CheckResult(
            status="FAIL",
            detail=f"Derivation query execution failed: {exc}",
            fix_suggestion="Fix the derivation_query syntax or verify snapshot data files.",
        )

    if queried_result is None:
        return CheckResult(
            status="FAIL",
            detail=(
                f"Derivation query returned None for task '{task.task_id}'. "
                "Cannot verify GT correctness."
            ),
            fix_suggestion="Check the derivation_query path matches the snapshot data.",
        )

    # Compare queried result to declared GT
    gt_dict = task.ground_truth.model_dump(
        exclude={"comparison_mode", "derivation_query"}
    )
    # Remove None values
    gt_dict = {k: v for k, v in gt_dict.items() if v is not None}

    comparison_mode = task.ground_truth.comparison_mode or "exact"
    tolerance_pct = task.tolerance_pct

    mismatches = _compare_values(
        expected=gt_dict,
        actual=queried_result,
        mode=comparison_mode,
        tolerance_pct=tolerance_pct,
    )

    if mismatches:
        return CheckResult(
            status="FAIL",
            detail=(
                f"GT correctness check failed for task '{task.task_id}': {mismatches[:3]}"
                + (" ..." if len(mismatches) > 3 else "")
            ),
            fix_suggestion=(
                "Update ground_truth to match the derivation_query result, or fix "
                "the derivation_query to point to the correct snapshot field."
            ),
        )

    return CheckResult(
        status="PASS",
        detail=(
            f"GT values match derivation query result for task '{task.task_id}' "
            f"(mode={comparison_mode}, tolerance={tolerance_pct}%)."
        ),
    )


def _structural_check(task: "HPCTaskSpec") -> CheckResult:
    """Sanity-check: verify GT fields are non-null and non-empty."""
    gt_dict = task.ground_truth.model_dump(  # type: ignore[union-attr]
        exclude={"comparison_mode", "derivation_query"}
    )
    non_none = {k: v for k, v in gt_dict.items() if v is not None}

    if not non_none:
        return CheckResult(
            status="WARN",
            detail=(
                f"Task '{task.task_id}' has an empty ground_truth (all fields null). "
                "Cannot verify GT correctness."
            ),
            fix_suggestion=(
                "Populate ground_truth with expected answer values, or add a "
                "derivation_query for automated verification."
            ),
        )

    return CheckResult(
        status="WARN",
        detail=(
            f"GT structural check passed for task '{task.task_id}' "
            f"({len(non_none)} non-null field(s): {list(non_none)[:5]}). "
            "No derivation_query; cannot verify against snapshot."
        ),
        fix_suggestion=(
            "Add a derivation_query to ground_truth for full automated GT correctness "
            "verification against the snapshot data."
        ),
    )


def _compare_values(
    expected: dict[str, Any],
    actual: Any,
    mode: str,
    tolerance_pct: float,
) -> list[str]:
    """Compare expected GT dict against the derivation query result.

    Returns a list of mismatch descriptions (empty = match).
    """
    mismatches: list[str] = []

    if not isinstance(actual, dict):
        # If query returned a scalar, check against the first GT value
        if len(expected) == 1:
            key, exp_val = next(iter(expected.items()))
            mismatch = _compare_scalar(key, exp_val, actual, mode, tolerance_pct)
            if mismatch:
                mismatches.append(mismatch)
        else:
            mismatches.append(
                f"Expected dict with keys {list(expected)}, got scalar: {actual!r}"
            )
        return mismatches

    for key, exp_val in expected.items():
        if key not in actual:
            mismatches.append(f"Key '{key}' missing from query result")
            continue
        act_val = actual[key]
        mismatch = _compare_scalar(key, exp_val, act_val, mode, tolerance_pct)
        if mismatch:
            mismatches.append(mismatch)

    return mismatches


def _compare_scalar(
    key: str,
    expected: Any,
    actual: Any,
    mode: str,
    tolerance_pct: float,
) -> str | None:
    """Compare a single key-value pair.  Returns mismatch string or None."""
    if mode == "exact":
        if str(expected) != str(actual):
            return f"'{key}': expected={expected!r}, actual={actual!r} (exact match failed)"

    elif mode == "numeric_tolerance":
        try:
            exp_f = float(expected)
            act_f = float(actual)
            if exp_f == 0:
                if act_f != 0:
                    return f"'{key}': expected=0, actual={act_f} (numeric tolerance)"
            else:
                pct_diff = abs(exp_f - act_f) / abs(exp_f) * 100
                if pct_diff > tolerance_pct:
                    return (
                        f"'{key}': expected={exp_f}, actual={act_f}, "
                        f"diff={pct_diff:.1f}% > {tolerance_pct}% tolerance"
                    )
        except (TypeError, ValueError):
            if str(expected) != str(actual):
                return f"'{key}': non-numeric mismatch: expected={expected!r}, actual={actual!r}"

    elif mode == "set_equal":
        exp_set = set(expected) if isinstance(expected, list) else {expected}
        act_set = set(actual) if isinstance(actual, list) else {actual}
        if exp_set != act_set:
            return f"'{key}': set mismatch: expected={exp_set}, actual={act_set}"

    elif mode == "regex":
        import re
        if not re.fullmatch(str(expected), str(actual)):
            return f"'{key}': regex mismatch: pattern={expected!r}, actual={actual!r}"

    else:
        # Default: exact
        if str(expected) != str(actual):
            return f"'{key}': expected={expected!r}, actual={actual!r}"

    return None
