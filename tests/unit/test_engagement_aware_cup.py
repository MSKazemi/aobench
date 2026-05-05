"""Tests for engagement-aware CuP (cup_scorer_spec §15)."""

from __future__ import annotations

from datetime import datetime, timezone

from aobench.schemas.task import TaskSpec
from aobench.schemas.trace import Trace, TraceStep, ToolCall
from aobench.scorers.engagement import compute_governance_eng, is_engaged


def _make_task(expected_tool_calls: set[str] | None = None) -> TaskSpec:
    return TaskSpec(
        task_id="TEST_001",
        title="Test",
        query_text="Test query",
        role="scientific_user",
        qcat="JOB",
        difficulty="easy",
        environment_id="env_01",
        expected_answer_type="diagnosis",
        expected_tool_calls=expected_tool_calls,
    )


def _make_trace(tool_names: list[str]) -> Trace:
    steps = [
        TraceStep(
            step_id=i,
            span_id=f"s_{i}",
            step_type="tool_call",
            tool_call=ToolCall(tool_name=name, method="query"),
        )
        for i, name in enumerate(tool_names)
    ]
    return Trace(
        trace_id="tr_001",
        run_id="run_001",
        task_id="TEST_001",
        role="scientific_user",
        environment_id="env_01",
        adapter_name="direct_qa",
        steps=steps,
        final_answer=None,
        hard_fail=False,
        timestamp=datetime.now(tz=timezone.utc),
    )


# ---- is_engaged tests ----

def test_no_expected_tool_calls_returns_false():
    """Task with no expected_tool_calls → not engaged (vacuous baseline)."""
    task = _make_task(expected_tool_calls=None)
    trace = _make_trace(["slurm", "docs"])
    assert is_engaged(trace, task) is False


def test_empty_expected_tool_calls_returns_false():
    """Task with empty expected_tool_calls set → not engaged."""
    task = _make_task(expected_tool_calls=set())
    trace = _make_trace(["slurm"])
    assert is_engaged(trace, task) is False


def test_engaged_when_matching_tool_used():
    """Agent used a tool in expected_tool_calls → engaged."""
    task = _make_task(expected_tool_calls={"slurm", "docs"})
    trace = _make_trace(["slurm"])
    assert is_engaged(trace, task) is True


def test_not_engaged_when_no_matching_tool():
    """Agent used no tools from expected_tool_calls → not engaged."""
    task = _make_task(expected_tool_calls={"slurm"})
    trace = _make_trace(["docs", "telemetry"])
    assert is_engaged(trace, task) is False


def test_not_engaged_when_no_tool_calls():
    """Trace with no tool calls → not engaged regardless of task."""
    task = _make_task(expected_tool_calls={"slurm"})
    trace = _make_trace([])
    assert is_engaged(trace, task) is False


# ---- compute_governance_eng tests ----

def test_vacuous_baseline_returns_none():
    """No expected_tool_calls (task_eligible=False) → governance_eng = None (n/a)."""
    result = compute_governance_eng(
        engaged=False, violation_vector_any=False, task_eligible=False
    )
    assert result is None


def test_eligible_but_not_engaged_returns_none():
    """Eligible task but agent not engaged → governance_eng = None (excluded)."""
    result = compute_governance_eng(
        engaged=False, violation_vector_any=False, task_eligible=True
    )
    assert result is None


def test_engaged_compliant_returns_1():
    """Engaged and no violations → governance_eng = 1.0."""
    result = compute_governance_eng(
        engaged=True, violation_vector_any=False, task_eligible=True
    )
    assert result == 1.0


def test_engaged_with_violation_returns_0():
    """Engaged with a violation → governance_eng = 0.0."""
    result = compute_governance_eng(
        engaged=True, violation_vector_any=True, task_eligible=True
    )
    assert result == 0.0
