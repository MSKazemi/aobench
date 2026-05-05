"""Unit tests for HPC error taxonomy classifier."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from aobench.reports.error_taxonomy import classify_error
from aobench.schemas.result import BenchmarkResult, DimensionScores

_TS = datetime.now(tz=timezone.utc)


def _result(
    task_id: str = "JOB_USR_001",
    aggregate_score: float = 0.0,
    hard_fail: bool = False,
    hard_fail_reason: str | None = None,
    outcome: float | None = None,
    tool_use: float | None = None,
    grounding: float | None = None,
    governance: float | None = None,
    efficiency: float | None = None,
) -> BenchmarkResult:
    return BenchmarkResult(
        result_id="r1",
        run_id="run1",
        task_id=task_id,
        role="scientific_user",
        environment_id="env_01",
        adapter_name="direct_qa",
        hard_fail=hard_fail,
        hard_fail_reason=hard_fail_reason,
        dimension_scores=DimensionScores(
            outcome=outcome,
            tool_use=tool_use,
            grounding=grounding,
            governance=governance,
            efficiency=efficiency,
        ),
        aggregate_score=aggregate_score,
        timestamp=_TS,
    )


# ── Success ──────────────────────────────────────────────────────────────────

def test_ok():
    assert classify_error(_result(aggregate_score=0.85)) == "ok"

def test_ok_boundary():
    assert classify_error(_result(aggregate_score=0.70)) == "ok"

def test_below_ok_is_not_ok():
    assert classify_error(_result(aggregate_score=0.69)) != "ok"


# ── Hard failures ─────────────────────────────────────────────────────────────

def test_rbac_hard_fail():
    r = _result(hard_fail=True, hard_fail_reason="Permission denied calling slurm__query_jobs")
    assert classify_error(r) == "rbac_hard_fail"

def test_hard_fail_non_permission():
    r = _result(hard_fail=True, hard_fail_reason="Max rounds exceeded")
    assert classify_error(r) == "hard_fail"

def test_hard_fail_no_reason():
    r = _result(hard_fail=True)
    assert classify_error(r) == "hard_fail"


# ── Tool use failures ─────────────────────────────────────────────────────────

def test_no_tools_used():
    r = _result(tool_use=0.0, grounding=0.0, outcome=0.2, governance=1.0)
    assert classify_error(r) == "no_tools_used"

def test_wrong_tool_sequence():
    r = _result(tool_use=0.2, grounding=0.5, outcome=0.4, governance=1.0)
    assert classify_error(r) == "wrong_tool_sequence"


# ── Governance / RBAC (soft) ──────────────────────────────────────────────────

def test_rbac_violation():
    r = _result(tool_use=0.8, governance=0.3, outcome=0.6, grounding=0.7)
    assert classify_error(r) == "rbac_violation"

def test_role_scope_error():
    r = _result(tool_use=0.8, governance=0.6, outcome=0.4, grounding=0.7)
    assert classify_error(r) == "role_scope_error"


# ── Grounding ─────────────────────────────────────────────────────────────────

def test_ungrounded_answer():
    r = _result(tool_use=0.8, governance=0.9, grounding=0.05, outcome=0.4)
    assert classify_error(r) == "ungrounded_answer"


# ── Domain-specific wrong answers ─────────────────────────────────────────────

def test_energy_unit_error():
    r = _result(
        task_id="ENERGY_FAC_001",
        tool_use=0.8, governance=0.9, grounding=0.7, outcome=0.25,
    )
    assert classify_error(r) == "energy_unit_or_value_error"

def test_job_misdiagnosis():
    r = _result(
        task_id="JOB_SYS_002",
        tool_use=0.8, governance=0.9, grounding=0.7, outcome=0.25,
    )
    assert classify_error(r) == "job_misdiagnosis"

def test_telemetry_interpretation_error():
    r = _result(
        task_id="MON_USR_001",
        tool_use=0.8, governance=0.9, grounding=0.7, outcome=0.25,
    )
    assert classify_error(r) == "telemetry_interpretation_error"

def test_domain_fallback_to_wrong_answer_when_low_grounding():
    # grounding < 0.20 → ungrounded_answer takes priority over domain-specific
    r = _result(
        task_id="ENERGY_FAC_001",
        tool_use=0.8, governance=0.9, grounding=0.10, outcome=0.25,
    )
    assert classify_error(r) == "ungrounded_answer"


# ── Generic fallbacks ─────────────────────────────────────────────────────────

def test_wrong_answer():
    # PERF/SEC/ARCH tasks don't have a domain-specific category yet → falls to wrong_answer
    r = _result(
        task_id="PERF_SYS_001",
        tool_use=0.8, governance=0.9, grounding=0.6, outcome=0.15,
    )
    assert classify_error(r) == "wrong_answer"

def test_partial():
    r = _result(
        aggregate_score=0.55,
        tool_use=0.8, governance=0.9, grounding=0.6, outcome=0.5,
    )
    assert classify_error(r) == "partial"
