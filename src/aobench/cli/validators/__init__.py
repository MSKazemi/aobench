"""AOBench task validator package.

Exports all check functions (T1–T9) and the report generator (T10),
plus the base dataclasses used across all checkers.
"""

from aobench.cli.validators.base import (
    CheckResult,
    TaskValidityResult,
    aggregate_overall,
)
from aobench.cli.validators.t1_tool_versions import check_tool_version_pinning
from aobench.cli.validators.t2_tool_setup import check_tool_setup
from aobench.cli.validators.t3_oracle_solvability import check_oracle_solvability
from aobench.cli.validators.t4_residual_state import check_residual_state_policy
from aobench.cli.validators.t5_gt_isolation import check_ground_truth_isolation
from aobench.cli.validators.t6_env_freeze import check_environment_freeze
from aobench.cli.validators.t7_gt_correctness import check_ground_truth_correctness
from aobench.cli.validators.t8_ambiguity import check_task_ambiguity
from aobench.cli.validators.t9_shortcuts import check_shortcut_prevention
from aobench.cli.validators.t10_reporting import (
    format_csv_report,
    format_text_report,
    generate_validity_report,
)

__all__ = [
    # Base
    "CheckResult",
    "TaskValidityResult",
    "aggregate_overall",
    # Checkers
    "check_tool_version_pinning",
    "check_tool_setup",
    "check_oracle_solvability",
    "check_residual_state_policy",
    "check_ground_truth_isolation",
    "check_environment_freeze",
    "check_ground_truth_correctness",
    "check_task_ambiguity",
    "check_shortcut_prevention",
    # Report generator
    "generate_validity_report",
    "format_text_report",
    "format_csv_report",
]
