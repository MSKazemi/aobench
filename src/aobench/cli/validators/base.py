"""Validator base types — CheckResult and TaskValidityResult dataclasses.

These are the core data structures used by all T1–T10 checkers and the
validity report generator (T10).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class CheckResult:
    """Result of a single checker (T1–T9) for one task."""

    status: Literal["PASS", "WARN", "FAIL", "SKIP"]
    detail: str
    fix_suggestion: str | None = None  # populated on FAIL/WARN


@dataclass
class TaskValidityResult:
    """Aggregated validity result for one task across all checks."""

    task_id: str
    overall: Literal["PASS", "WARN", "FAIL"]
    checks: dict[str, CheckResult] = field(default_factory=dict)  # keys: "t1".."t9"

    @property
    def release_ready(self) -> bool:
        """True when overall is PASS.  WARN does not block release by default."""
        return self.overall == "PASS"


def aggregate_overall(
    checks: dict[str, CheckResult],
    strict: bool = False,
) -> Literal["PASS", "WARN", "FAIL"]:
    """Derive an overall status from a mapping of check results.

    Parameters
    ----------
    checks:
        Dict of check-name -> CheckResult.
    strict:
        When True, WARN is treated as FAIL.

    Returns
    -------
    "FAIL" if any check is FAIL.
    "WARN" if any check is WARN (and strict=False).
    "PASS" otherwise (all PASS or SKIP).
    """
    statuses = {r.status for r in checks.values()}
    if "FAIL" in statuses:
        return "FAIL"
    if "WARN" in statuses:
        return "FAIL" if strict else "WARN"
    return "PASS"
