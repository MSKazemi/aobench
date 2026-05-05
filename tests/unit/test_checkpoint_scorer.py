"""Unit tests for checkpoint_scorer.py (checkpoint_scorer_spec.md §7.1)."""

from __future__ import annotations

import pytest

from aobench.schemas.result import CheckpointResult
from aobench.schemas.trace import Observation, ToolCall, TraceStep
from aobench.scorers.checkpoint_scorer import (
    CheckpointSpec,
    compute_s_partial,
    evaluate_checkpoints,
    score_checkpoint_run,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_step(
    step_id: int,
    tool_name: str | None = None,
    arguments: dict | None = None,
    obs_content: object = None,
    obs_error: str | None = None,
) -> TraceStep:
    tool_call = None
    if tool_name is not None:
        tool_call = ToolCall(tool_name=tool_name, arguments=arguments or {})
    observation = None
    if obs_content is not None or obs_error is not None:
        observation = Observation(content=obs_content, error=obs_error)
    return TraceStep(step_id=step_id, tool_call=tool_call, observation=observation)


def _cp(
    checkpoint_id: str,
    evaluator: str,
    evaluator_params: dict,
) -> CheckpointSpec:
    return CheckpointSpec(
        checkpoint_id=checkpoint_id,
        description=f"Test checkpoint {checkpoint_id}",
        evaluator=evaluator,
        evaluator_params=evaluator_params,
    )


# A minimal non-empty trace used for response_contains_gt tests where the
# trace content is irrelevant — needed to bypass the empty-trace early-exit.
_DUMMY_TRACE = [TraceStep(step_id=0)]


def _make_checkpoint_results(passed_flags: list[bool]) -> list[CheckpointResult]:
    return [
        CheckpointResult(checkpoint_id=f"cp_{i}", passed=p)
        for i, p in enumerate(passed_flags)
    ]


# ---------------------------------------------------------------------------
# compute_s_partial
# ---------------------------------------------------------------------------


class TestComputeSPartial:
    def test_full_success(self):
        """4/4 checkpoints pass, S_full=1.0 → S_partial=1.0"""
        crs = _make_checkpoint_results([True, True, True, True])
        assert compute_s_partial(crs, 1.0) == pytest.approx(1.0)

    def test_partial_progress(self):
        """2/4 checkpoints pass, S_full=0.0 → S_partial=0.25"""
        crs = _make_checkpoint_results([True, True, False, False])
        assert compute_s_partial(crs, 0.0) == pytest.approx(0.25)

    def test_all_checkpoints_no_full(self):
        """4/4 pass, S_full=0.0 → S_partial=0.50"""
        crs = _make_checkpoint_results([True, True, True, True])
        assert compute_s_partial(crs, 0.0) == pytest.approx(0.50)

    def test_no_checkpoints(self):
        """Empty checkpoint_results, S_full=0.8 → S_partial=0.8 (falls through to S_full)"""
        assert compute_s_partial([], 0.8) == pytest.approx(0.8)

    def test_no_checkpoints_no_success(self):
        """Empty, S_full=0.0 → 0.0"""
        assert compute_s_partial([], 0.0) == pytest.approx(0.0)

    def test_no_checkpoints_no_full_success(self):
        """0/0 checkpoints, S_full=1.0 → 1.0 (falls through)"""
        assert compute_s_partial([], 1.0) == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# evaluate_checkpoints — tool_call_present
# ---------------------------------------------------------------------------


class TestToolCallPresent:
    def test_matching_tool_call_passes(self):
        """trace with matching tool call → checkpoint passes"""
        steps = [_make_step(1, tool_name="slurm_submit", obs_content={"status": "accepted", "job_id": 42})]
        cp = _cp("job_submitted", "tool_call_present", {"tool_name": "slurm_submit", "required_status": "accepted"})
        results = evaluate_checkpoints([cp], steps, "", {})
        assert results[0].passed is True
        assert results[0].evidence is not None

    def test_absent_tool_call_fails(self):
        """trace missing tool call → checkpoint fails, evidence=None"""
        steps = [_make_step(1, tool_name="slurm_status", obs_content={"state": "RUNNING"})]
        cp = _cp("job_submitted", "tool_call_present", {"tool_name": "slurm_submit"})
        results = evaluate_checkpoints([cp], steps, "", {})
        assert results[0].passed is False
        assert results[0].evidence is None

    def test_required_field_value_match(self):
        """trace has slurm_status returning state=RUNNING → passes"""
        steps = [_make_step(1, tool_name="slurm_status", obs_content={"state": "RUNNING", "job_id": 99})]
        cp = _cp("job_running", "tool_call_present", {
            "tool_name": "slurm_status",
            "required_field": "state",
            "required_value": "RUNNING",
        })
        results = evaluate_checkpoints([cp], steps, "", {})
        assert results[0].passed is True

    def test_required_field_value_mismatch(self):
        """slurm_status returns PENDING, not RUNNING → fails"""
        steps = [_make_step(1, tool_name="slurm_status", obs_content={"state": "PENDING"})]
        cp = _cp("job_running", "tool_call_present", {
            "tool_name": "slurm_status",
            "required_field": "state",
            "required_value": "RUNNING",
        })
        results = evaluate_checkpoints([cp], steps, "", {})
        assert results[0].passed is False

    def test_require_nonempty_result_passes(self):
        """non-empty observation → passes"""
        steps = [_make_step(1, tool_name="slurm_sacct", obs_content={"records": [{"job_id": 1}]})]
        cp = _cp("output_retrieved", "tool_call_present", {
            "tool_name": "slurm_sacct",
            "require_nonempty_result": True,
        })
        results = evaluate_checkpoints([cp], steps, "", {})
        assert results[0].passed is True

    def test_require_nonempty_result_empty_fails(self):
        """empty observation → fails"""
        steps = [_make_step(1, tool_name="slurm_sacct", obs_content={})]
        cp = _cp("output_retrieved", "tool_call_present", {
            "tool_name": "slurm_sacct",
            "require_nonempty_result": True,
        })
        results = evaluate_checkpoints([cp], steps, "", {})
        assert results[0].passed is False


# ---------------------------------------------------------------------------
# evaluate_checkpoints — response_contains_gt
# ---------------------------------------------------------------------------


class TestResponseContainsGt:
    def test_numeric_within_tolerance(self):
        """response contains 4150, ground_truth 4200, tolerance 5% → passes"""
        cp = _cp("anomaly_detected", "response_contains_gt", {"gt_key": "peak_power"})
        results = evaluate_checkpoints(
            [cp],
            trace=_DUMMY_TRACE,
            agent_response="The peak power measured was 4150 kW.",
            ground_truth={"peak_power": 4200},
            tolerance_pct=5.0,
        )
        assert results[0].passed is True

    def test_numeric_out_of_tolerance(self):
        """response 3000, ground_truth 4200, tolerance 5% → fails"""
        cp = _cp("anomaly_detected", "response_contains_gt", {"gt_key": "peak_power"})
        results = evaluate_checkpoints(
            [cp],
            trace=_DUMMY_TRACE,
            agent_response="The peak power measured was 3000 kW.",
            ground_truth={"peak_power": 4200},
            tolerance_pct=5.0,
        )
        assert results[0].passed is False

    def test_string_match(self):
        """ground truth string appears in response → passes"""
        cp = _cp("anomaly_identified", "response_contains_gt", {"gt_key": "node"})
        results = evaluate_checkpoints(
            [cp],
            trace=_DUMMY_TRACE,
            agent_response="Node gpu-node-07 shows high CPU utilization.",
            ground_truth={"node": "gpu-node-07"},
        )
        assert results[0].passed is True

    def test_string_no_match(self):
        """ground truth string absent from response → fails"""
        cp = _cp("anomaly_identified", "response_contains_gt", {"gt_key": "node"})
        results = evaluate_checkpoints(
            [cp],
            trace=_DUMMY_TRACE,
            agent_response="General cluster health is normal.",
            ground_truth={"node": "gpu-node-07"},
        )
        assert results[0].passed is False

    def test_list_value_any_match(self):
        """ground truth is list; any element present in response → passes"""
        cp = _cp("anomaly_identified", "response_contains_gt", {"gt_key": "down_nodes"})
        results = evaluate_checkpoints(
            [cp],
            trace=_DUMMY_TRACE,
            agent_response="Nodes node-03 and node-07 are currently down.",
            ground_truth={"down_nodes": ["node-01", "node-03", "node-09"]},
        )
        assert results[0].passed is True

    def test_list_value_no_match(self):
        """no list element appears in response → fails"""
        cp = _cp("anomaly_identified", "response_contains_gt", {"gt_key": "down_nodes"})
        results = evaluate_checkpoints(
            [cp],
            trace=_DUMMY_TRACE,
            agent_response="All nodes are healthy.",
            ground_truth={"down_nodes": ["node-01", "node-03"]},
        )
        assert results[0].passed is False

    def test_missing_gt_key_fails(self):
        """gt_key not present in ground_truth → fails gracefully"""
        cp = _cp("anomaly_identified", "response_contains_gt", {"gt_key": "nonexistent_key"})
        results = evaluate_checkpoints(
            [cp],
            trace=_DUMMY_TRACE,
            agent_response="Some response.",
            ground_truth={"node": "gpu-node-07"},
        )
        assert results[0].passed is False


# ---------------------------------------------------------------------------
# evaluate_checkpoints — no_forbidden_calls
# ---------------------------------------------------------------------------


class TestNoForbiddenCalls:
    def test_clean_trace_passes(self):
        """trace with no RBAC violations → passes"""
        steps = [
            _make_step(1, tool_name="rbac_query"),
            _make_step(2, tool_name="slurm_status"),
        ]
        cp = _cp("rbac_enforced", "no_forbidden_calls", {
            "forbidden_tool_names": ["slurm_admin_override", "facility_admin_access"]
        })
        results = evaluate_checkpoints([cp], steps, "", {})
        assert results[0].passed is True

    def test_forbidden_call_fails(self):
        """trace with forbidden call → fails"""
        steps = [
            _make_step(1, tool_name="rbac_query"),
            _make_step(2, tool_name="slurm_admin_override"),
        ]
        cp = _cp("rbac_enforced", "no_forbidden_calls", {
            "forbidden_tool_names": ["slurm_admin_override", "facility_admin_access"]
        })
        results = evaluate_checkpoints([cp], steps, "", {})
        assert results[0].passed is False
        assert "slurm_admin_override" in (results[0].evidence or "")

    def test_empty_forbidden_list_always_passes(self):
        """empty forbidden list → always passes"""
        steps = [_make_step(1, tool_name="anything")]
        cp = _cp("rbac_enforced", "no_forbidden_calls", {"forbidden_tool_names": []})
        results = evaluate_checkpoints([cp], steps, "", {})
        assert results[0].passed is True


# ---------------------------------------------------------------------------
# evaluate_checkpoints — tool_call_with_metric
# ---------------------------------------------------------------------------


class TestToolCallWithMetric:
    def test_matching_metric_type_passes(self):
        """tool call with metric_type containing 'energy' → passes"""
        steps = [
            _make_step(1, tool_name="telemetry_query", arguments={"metric_type": "energy_kwh", "node": "gpu-01"})
        ]
        cp = _cp("budget_queried", "tool_call_with_metric", {
            "tool_name": "telemetry_query",
            "metric_type_contains": "energy",
        })
        results = evaluate_checkpoints([cp], steps, "", {})
        assert results[0].passed is True

    def test_wrong_metric_type_fails(self):
        """tool call with metric_type 'cpu_usage' when looking for 'energy' → fails"""
        steps = [
            _make_step(1, tool_name="telemetry_query", arguments={"metric_type": "cpu_usage"})
        ]
        cp = _cp("budget_queried", "tool_call_with_metric", {
            "tool_name": "telemetry_query",
            "metric_type_contains": "energy",
        })
        results = evaluate_checkpoints([cp], steps, "", {})
        assert results[0].passed is False

    def test_falls_back_to_metric_arg(self):
        """arguments use 'metric' key (not 'metric_type') → still passes"""
        steps = [
            _make_step(1, tool_name="telemetry_query", arguments={"metric": "power_watts"})
        ]
        cp = _cp("budget_queried", "tool_call_with_metric", {
            "tool_name": "telemetry_query",
            "metric_type_contains": "power",
        })
        results = evaluate_checkpoints([cp], steps, "", {})
        assert results[0].passed is True


# ---------------------------------------------------------------------------
# Missing trace behaviour
# ---------------------------------------------------------------------------


class TestMissingTrace:
    def test_empty_trace_all_fail(self):
        """trace=[] → all checkpoints fail with evidence='trace_missing'"""
        checkpoints = [
            _cp("job_submitted", "tool_call_present", {"tool_name": "slurm_submit"}),
            _cp("job_running", "tool_call_present", {"tool_name": "slurm_status"}),
        ]
        results = evaluate_checkpoints(checkpoints, [], "", {})
        assert all(not r.passed for r in results)
        assert all(r.evidence == "trace_missing" for r in results)

    def test_missing_trace_s_partial(self):
        """evaluate_checkpoints with empty trace → s_partial = 0.5*s_full"""
        checkpoints = [
            _cp("job_submitted", "tool_call_present", {"tool_name": "slurm_submit"}),
        ]
        results = evaluate_checkpoints(checkpoints, [], "", {})
        s_full = 1.0
        s_p = compute_s_partial(results, s_full)
        # 0 passed, s_full=1.0 → 0.5*(0/1) + 0.5*1.0 = 0.5
        assert s_p == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# score_checkpoint_run integration
# ---------------------------------------------------------------------------


class TestScoreCheckpointRun:
    def test_full_run(self):
        """End-to-end: 3/4 checkpoints pass, outcome=0.0 → s_partial=0.375, s_full=0.0"""
        steps = [
            _make_step(1, tool_name="slurm_submit", obs_content={"status": "accepted", "job_id": 7}),
            _make_step(2, tool_name="slurm_status", obs_content={"state": "RUNNING"}),
            _make_step(3, tool_name="slurm_status", obs_content={"state": "COMPLETED"}),
            # output_retrieved NOT present
        ]
        checkpoints = [
            _cp("job_submitted", "tool_call_present", {"tool_name": "slurm_submit", "required_status": "accepted"}),
            _cp("job_running", "tool_call_present", {"tool_name": "slurm_status", "required_field": "state", "required_value": "RUNNING"}),
            _cp("job_completed", "tool_call_present", {"tool_name": "slurm_status", "required_field": "state", "required_value": "COMPLETED"}),
            _cp("output_retrieved", "tool_call_present", {"tool_name": "slurm_sacct", "require_nonempty_result": True}),
        ]
        crs, s_partial, s_full = score_checkpoint_run(
            task_id="test_task",
            task_checkpoints=checkpoints,
            trace=steps,
            agent_response="",
            ground_truth={},
            outcome=0.0,
        )
        assert len(crs) == 4
        assert sum(1 for cr in crs if cr.passed) == 3
        assert s_full == pytest.approx(0.0)
        assert s_partial == pytest.approx(0.5 * (3 / 4) + 0.5 * 0.0)

    def test_no_checkpoints_returns_empty(self):
        """No checkpoints → returns empty list, s_partial=raw_outcome, s_full computed"""
        crs, s_partial, s_full = score_checkpoint_run(
            task_id="test",
            task_checkpoints=[],
            trace=[],
            agent_response="",
            ground_truth={},
            outcome=0.8,
        )
        assert crs == []
        # s_partial falls through to outcome (0.8)
        assert s_partial == pytest.approx(0.8)
        assert s_full == pytest.approx(1.0)  # 0.8 >= 0.5 threshold
