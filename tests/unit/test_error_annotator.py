"""Unit tests for error_annotator — auto-detection heuristics and metrics."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from unittest.mock import MagicMock

import pytest

from exabench.schemas.task import EvalCriteria, TaskSpec
from exabench.schemas.trace import Observation, Trace, TraceStep, ToolCall
from exabench.schemas.trace_annotation import ErrorAnnotation, HolisticScores, TraceAnnotation
from exabench.scorers.error_annotator import (
    _args_hash,
    _span_id,
    _try_parse_float,
    auto_detect_errors,
    category_f1,
    joint_accuracy,
    load_taxonomy,
    location_accuracy,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_task(
    allowed_tools: list[str] | None = None,
    gold_answer: str | None = None,
    evaluation_mode: str = "semantic_match",
) -> TaskSpec:
    return TaskSpec(
        task_id="JOB_USR_001",
        title="Test task",
        query_text="What caused job 12345 to fail?",
        role="sysadmin",
        qcat="JOB",
        difficulty="easy",
        environment_id="env_01",
        expected_answer_type="diagnosis",
        allowed_tools=allowed_tools,
        eval_criteria=EvalCriteria(
            evaluation_mode=evaluation_mode,
            gold_answer=gold_answer,
        ) if gold_answer or evaluation_mode != "semantic_match" else None,
    )


def _make_trace(steps: list[TraceStep], final_answer: str | None = None) -> Trace:
    return Trace(
        trace_id="trace_001",
        run_id="run_001",
        task_id="JOB_USR_001",
        role="sysadmin",
        environment_id="env_01",
        adapter_name="test",
        steps=steps,
        final_answer=final_answer,
        total_tokens=1000,
        model_name="test-model",
    )


def _tool_step(step_id: int, tool_name: str, args: dict[str, Any] | None = None) -> TraceStep:
    return TraceStep(
        step_id=step_id,
        tool_call=ToolCall(tool_name=tool_name, arguments=args or {}),
        observation=Observation(content={"status": "ok"}),
    )


def _error_step(step_id: int, tool_name: str, error_msg: str) -> TraceStep:
    return TraceStep(
        step_id=step_id,
        tool_call=ToolCall(tool_name=tool_name, arguments={}),
        observation=Observation(content=None, error=error_msg),
    )


def _denied_step(step_id: int, tool_name: str) -> TraceStep:
    return TraceStep(
        step_id=step_id,
        tool_call=ToolCall(tool_name=tool_name, arguments={}),
        observation=Observation(content=None, permission_denied=True),
    )


def _make_annotation(
    task_id: str = "JOB_USR_001",
    run_id: str = "run_001",
    categories: list[str] | None = None,
    locations: list[str] | None = None,
) -> TraceAnnotation:
    errors = []
    cats = categories or []
    locs = locations or ["step_001_tool_call"] * len(cats)
    for cat, loc in zip(cats, locs):
        errors.append(ErrorAnnotation(
            category=cat,
            location=loc,
            evidence="test evidence",
            description="test",
            impact="MEDIUM",
            source="auto",
        ))
    return TraceAnnotation(
        task_id=task_id,
        run_id=run_id,
        role="sysadmin",
        snapshot_id="env_01",
        errors=errors,
    )


# ---------------------------------------------------------------------------
# Taxonomy loading
# ---------------------------------------------------------------------------

def test_load_taxonomy_returns_24_leaves():
    # Spec §12 summary says 22 but the actual YAML (§7) defines 24 leaf nodes —
    # the YAML is authoritative. Breakdown: 2 halluc + 4 info + 2 decision +
    # 4 output + 2 config + 2 tool_errors + 2 resource + 2 context + 4 task = 24.
    tax = load_taxonomy()
    all_ids: list[str] = []
    for top in tax["categories"].values():
        for sub in top["subcategories"].values():
            all_ids.extend(sub["leaf_nodes"].keys())
    assert len(all_ids) == 24


def test_taxonomy_contains_required_categories():
    tax = load_taxonomy()
    all_ids: list[str] = []
    for top in tax["categories"].values():
        for sub in top["subcategories"].values():
            all_ids.extend(sub["leaf_nodes"].keys())
    required = {
        "hpc.halluc.metric", "hpc.halluc.tool",
        "hpc.info.wrong_metric", "hpc.info.wrong_time_range",
        "hpc.info.wrong_node_filter", "hpc.info.misread_output",
        "hpc.decision.wrong_tool", "hpc.decision.wrong_task",
        "hpc.output.unit_error", "hpc.output.arithmetic_drift",
        "hpc.output.format", "hpc.output.noncompliance",
        "hpc.system.tool_miscfg", "hpc.system.env_missing",
        "hpc.system.tool_timeout", "hpc.system.tool_error",
        "hpc.system.context_overflow", "hpc.system.tool_abuse",
        "hpc.plan.context_loss", "hpc.plan.state_confusion",
        "hpc.plan.goal_drift", "hpc.plan.role_violation",
    }
    missing = required - set(all_ids)
    assert not missing, f"Missing taxonomy categories: {missing}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def test_span_id_tool_call():
    step = _tool_step(5, "slurm")
    assert _span_id(step) == "step_005_tool_call"


def test_span_id_reasoning():
    step = TraceStep(step_id=3, reasoning="thinking...")
    assert _span_id(step) == "step_003_reasoning"


def test_args_hash_deterministic():
    h1 = _args_hash({"a": 1, "b": 2})
    h2 = _args_hash({"b": 2, "a": 1})
    assert h1 == h2


def test_try_parse_float():
    assert _try_parse_float("4200 kWh") == 4200.0
    assert _try_parse_float("4.2 MWh") == pytest.approx(4.2)
    assert _try_parse_float("no number here") is None


# ---------------------------------------------------------------------------
# Auto-detect: tool_abuse
# ---------------------------------------------------------------------------

def test_tool_abuse_detected_at_threshold():
    steps = [_tool_step(i, "slurm", {"method": "job_details", "job_id": "123"}) for i in range(1, 4)]
    trace = _make_trace(steps)
    errors = auto_detect_errors(trace, _make_task())
    abuse = [e for e in errors if e.category == "hpc.system.tool_abuse"]
    assert len(abuse) == 1
    assert abuse[0].first_or_last == "last"
    assert abuse[0].source == "auto"


def test_tool_abuse_not_triggered_below_threshold():
    steps = [_tool_step(i, "slurm", {"method": "job_details", "job_id": "123"}) for i in range(1, 3)]
    trace = _make_trace(steps)
    errors = auto_detect_errors(trace, _make_task())
    assert not any(e.category == "hpc.system.tool_abuse" for e in errors)


def test_tool_abuse_different_args_no_flag():
    steps = [
        _tool_step(1, "slurm", {"job_id": "100"}),
        _tool_step(2, "slurm", {"job_id": "200"}),
        _tool_step(3, "slurm", {"job_id": "300"}),
    ]
    trace = _make_trace(steps)
    errors = auto_detect_errors(trace, _make_task())
    assert not any(e.category == "hpc.system.tool_abuse" for e in errors)


# ---------------------------------------------------------------------------
# Auto-detect: tool_error and tool_timeout
# ---------------------------------------------------------------------------

def test_tool_error_detected():
    steps = [_error_step(1, "slurm", "Internal server error")]
    trace = _make_trace(steps)
    errors = auto_detect_errors(trace, _make_task())
    err_cats = [e.category for e in errors]
    assert "hpc.system.tool_error" in err_cats


def test_tool_timeout_detected():
    steps = [_error_step(1, "telemetry", "Request timed out after 30s")]
    trace = _make_trace(steps)
    errors = auto_detect_errors(trace, _make_task())
    err_cats = [e.category for e in errors]
    assert "hpc.system.tool_timeout" in err_cats
    assert "hpc.system.tool_error" not in err_cats


# ---------------------------------------------------------------------------
# Auto-detect: role_violation
# ---------------------------------------------------------------------------

def test_role_violation_via_disallowed_tool():
    steps = [_tool_step(1, "admin_override")]
    trace = _make_trace(steps)
    task = _make_task(allowed_tools=["slurm", "telemetry"])
    errors = auto_detect_errors(trace, task)
    violations = [e for e in errors if e.category == "hpc.plan.role_violation"]
    assert len(violations) == 1
    assert violations[0].impact == "HIGH"


def test_role_violation_via_permission_denied():
    steps = [_denied_step(1, "slurm")]
    trace = _make_trace(steps)
    task = _make_task(allowed_tools=["slurm"])
    errors = auto_detect_errors(trace, task)
    violations = [e for e in errors if e.category == "hpc.plan.role_violation"]
    assert len(violations) == 1


def test_no_role_violation_when_allowed_tools_none():
    steps = [_tool_step(1, "any_tool")]
    trace = _make_trace(steps)
    task = _make_task(allowed_tools=None)
    errors = auto_detect_errors(trace, task)
    assert not any(e.category == "hpc.plan.role_violation" for e in errors)


# ---------------------------------------------------------------------------
# Auto-detect: format error
# ---------------------------------------------------------------------------

def test_format_error_detected_for_non_json():
    steps = [_tool_step(1, "slurm")]
    trace = _make_trace(steps, final_answer="The job failed due to OOM")
    task = _make_task(evaluation_mode="structured_output")
    errors = auto_detect_errors(trace, task)
    assert any(e.category == "hpc.output.format" for e in errors)


def test_no_format_error_for_valid_json():
    steps = [_tool_step(1, "slurm")]
    trace = _make_trace(steps, final_answer='{"diagnosis": "OOM", "job_id": "123"}')
    task = _make_task(evaluation_mode="structured_output")
    errors = auto_detect_errors(trace, task)
    assert not any(e.category == "hpc.output.format" for e in errors)


# ---------------------------------------------------------------------------
# Auto-detect: unit_error
# ---------------------------------------------------------------------------

def test_unit_error_kwh_mwh_detected():
    # Gold is 4200 kWh, agent says 4.2 (MWh) — off by 1000×
    steps = [_tool_step(1, "telemetry")]
    trace = _make_trace(steps, final_answer="The total energy was 4.2")
    task = _make_task(gold_answer="4200 kWh")
    errors = auto_detect_errors(trace, task)
    assert any(e.category == "hpc.output.unit_error" for e in errors)


def test_no_unit_error_when_close_to_gold():
    steps = [_tool_step(1, "telemetry")]
    trace = _make_trace(steps, final_answer="4201 kWh")
    task = _make_task(gold_answer="4200")
    errors = auto_detect_errors(trace, task)
    assert not any(e.category == "hpc.output.unit_error" for e in errors)


# ---------------------------------------------------------------------------
# HolisticScores
# ---------------------------------------------------------------------------

def test_holistic_scores_overall_is_mean():
    hs = HolisticScores.from_components(4.0, 5.0, 3.0, 2.0)
    assert hs.overall == pytest.approx(3.5)


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    __import__("importlib").util.find_spec("sklearn") is None,
    reason="scikit-learn not installed",
)
def test_category_f1_perfect():
    cats = ["hpc.info.wrong_metric", "hpc.output.unit_error"]
    gt = [_make_annotation(categories=cats)]
    pred = [_make_annotation(categories=cats)]
    score = category_f1(gt, pred)
    assert score == pytest.approx(1.0)


@pytest.mark.skipif(
    __import__("importlib").util.find_spec("sklearn") is None,
    reason="scikit-learn not installed",
)
def test_category_f1_zero():
    gt = [_make_annotation(categories=["hpc.info.wrong_metric"])]
    pred = [_make_annotation(categories=["hpc.output.format"])]
    score = category_f1(gt, pred)
    assert score == pytest.approx(0.0)


def test_location_accuracy_perfect():
    cats = ["hpc.info.wrong_metric"]
    locs = ["step_001_tool_call"]
    gt = [_make_annotation(categories=cats, locations=locs)]
    pred = [_make_annotation(categories=cats, locations=locs)]
    assert location_accuracy(gt, pred) == pytest.approx(1.0)


def test_location_accuracy_no_overlap():
    gt = [_make_annotation(categories=["hpc.output.format"], locations=["step_001_tool_call"])]
    pred = [_make_annotation(categories=["hpc.output.format"], locations=["step_002_tool_call"])]
    assert location_accuracy(gt, pred) == pytest.approx(0.0)


def test_joint_accuracy_requires_both_match():
    gt = [_make_annotation(categories=["hpc.output.format"], locations=["step_001_tool_call"])]
    # Right location, wrong category
    pred_wrong_cat = [_make_annotation(
        categories=["hpc.info.wrong_metric"], locations=["step_001_tool_call"]
    )]
    assert joint_accuracy(gt, pred_wrong_cat) == pytest.approx(0.0)
    # Right category, wrong location
    pred_wrong_loc = [_make_annotation(
        categories=["hpc.output.format"], locations=["step_002_tool_call"]
    )]
    assert joint_accuracy(gt, pred_wrong_loc) == pytest.approx(0.0)
    # Both correct
    pred_correct = [_make_annotation(
        categories=["hpc.output.format"], locations=["step_001_tool_call"]
    )]
    assert joint_accuracy(gt, pred_correct) == pytest.approx(1.0)


def test_joint_accuracy_empty_gt():
    gt = [_make_annotation(categories=[])]
    pred = [_make_annotation(categories=[])]
    assert joint_accuracy(gt, pred) == pytest.approx(1.0)
