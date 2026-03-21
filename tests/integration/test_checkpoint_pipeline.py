"""Integration test for the full checkpoint pipeline (checkpoint_scorer_spec.md §7.3)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from exabench.schemas.result import BenchmarkResult, CheckpointResult, DimensionScores
from exabench.schemas.trace import Observation, ToolCall, TraceStep
from exabench.scorers.checkpoint_scorer import CheckpointSpec, score_checkpoint_run


# ---------------------------------------------------------------------------
# Fixture: JOB task with 4 checkpoints, trace satisfying 3/4
# ---------------------------------------------------------------------------


JOB_CHECKPOINTS = [
    CheckpointSpec(
        checkpoint_id="job_submitted",
        description="Agent issued a valid SLURM submission",
        evaluator="tool_call_present",
        evaluator_params={"tool_name": "slurm_submit", "required_status": "accepted"},
        qcat="JOB",
    ),
    CheckpointSpec(
        checkpoint_id="job_running",
        description="Job reached RUNNING state",
        evaluator="tool_call_present",
        evaluator_params={"tool_name": "slurm_status", "required_field": "state", "required_value": "RUNNING"},
        qcat="JOB",
    ),
    CheckpointSpec(
        checkpoint_id="job_completed",
        description="Job reached COMPLETED state",
        evaluator="tool_call_present",
        evaluator_params={"tool_name": "slurm_status", "required_field": "state", "required_value": "COMPLETED"},
        qcat="JOB",
    ),
    CheckpointSpec(
        checkpoint_id="output_retrieved",
        description="Agent retrieved job output or accounting data",
        evaluator="tool_call_present",
        evaluator_params={"tool_name": "slurm_sacct", "require_nonempty_result": True},
        qcat="JOB",
    ),
]


def _make_step(
    step_id: int,
    tool_name: str | None = None,
    arguments: dict | None = None,
    obs_content: object = None,
) -> TraceStep:
    tc = ToolCall(tool_name=tool_name, arguments=arguments or {}) if tool_name else None
    obs = Observation(content=obs_content) if obs_content is not None else None
    return TraceStep(step_id=step_id, tool_call=tc, observation=obs)


# Fixture trace: 3 out of 4 checkpoints satisfied (output_retrieved missing)
FIXTURE_TRACE: list[TraceStep] = [
    _make_step(1, "slurm_submit", obs_content={"status": "accepted", "job_id": 12345}),
    _make_step(2, "slurm_status", obs_content={"state": "RUNNING", "job_id": 12345}),
    _make_step(3, "slurm_status", obs_content={"state": "COMPLETED", "job_id": 12345}),
    # slurm_sacct intentionally absent → output_retrieved fails
]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCheckpointPipeline:
    def test_s_partial_value(self):
        """s_partial == 0.5 * 0.75 + 0.5 * 0.0 == 0.375"""
        crs, s_partial, s_full = score_checkpoint_run(
            task_id="job_ops_test",
            task_checkpoints=JOB_CHECKPOINTS,
            trace=FIXTURE_TRACE,
            agent_response="Job 12345 has completed.",
            ground_truth={"job_id": 12345},
            outcome=0.0,
            pass_threshold=0.5,
        )
        assert s_partial == pytest.approx(0.5 * (3 / 4) + 0.5 * 0.0)
        assert s_partial == pytest.approx(0.375)

    def test_checkpoint_results_count(self):
        """checkpoint_results has 4 items, 3 passed"""
        crs, _, _ = score_checkpoint_run(
            task_id="job_ops_test",
            task_checkpoints=JOB_CHECKPOINTS,
            trace=FIXTURE_TRACE,
            agent_response="",
            ground_truth={},
            outcome=0.0,
        )
        assert len(crs) == 4
        assert sum(1 for cr in crs if cr.passed) == 3

    def test_correct_checkpoint_fails(self):
        """output_retrieved checkpoint should be the one that fails"""
        crs, _, _ = score_checkpoint_run(
            task_id="job_ops_test",
            task_checkpoints=JOB_CHECKPOINTS,
            trace=FIXTURE_TRACE,
            agent_response="",
            ground_truth={},
            outcome=0.0,
        )
        by_id = {cr.checkpoint_id: cr for cr in crs}
        assert by_id["job_submitted"].passed is True
        assert by_id["job_running"].passed is True
        assert by_id["job_completed"].passed is True
        assert by_id["output_retrieved"].passed is False

    def test_s_full_reflects_outcome_threshold(self):
        """outcome=0.0 < 0.5 threshold → s_full=0.0"""
        _, _, s_full = score_checkpoint_run(
            task_id="job_ops_test",
            task_checkpoints=JOB_CHECKPOINTS,
            trace=FIXTURE_TRACE,
            agent_response="",
            ground_truth={},
            outcome=0.0,
            pass_threshold=0.5,
        )
        assert s_full == pytest.approx(0.0)

    def test_benchmark_result_s_partial_populated(self):
        """BenchmarkResult s_partial field can be populated from checkpoint scorer output."""
        crs, s_partial, s_full = score_checkpoint_run(
            task_id="job_ops_test",
            task_checkpoints=JOB_CHECKPOINTS,
            trace=FIXTURE_TRACE,
            agent_response="",
            ground_truth={},
            outcome=0.0,
        )
        result = BenchmarkResult(
            result_id="r1",
            run_id="run1",
            task_id="job_ops_test",
            role="sysadmin",
            environment_id="env_01",
            adapter_name="test",
            dimension_scores=DimensionScores(outcome=s_partial),
            aggregate_score=s_partial,
            timestamp=datetime.now(tz=timezone.utc),
            checkpoint_results=crs,
            s_partial=s_partial,
            s_full=s_full,
        )
        assert result.s_partial == pytest.approx(0.375)
        assert result.checkpoint_results is not None
        assert len(result.checkpoint_results) == 4


class TestAllCheckpointsPassing:
    """Full success: all 4 checkpoints pass and outcome=1.0 → s_partial=1.0"""

    def test_all_pass_s_partial_is_one(self):
        full_trace = FIXTURE_TRACE + [
            _make_step(4, "slurm_sacct", obs_content={"records": [{"job_id": 12345, "elapsed": "00:05:00"}]})
        ]
        crs, s_partial, s_full = score_checkpoint_run(
            task_id="job_ops_test",
            task_checkpoints=JOB_CHECKPOINTS,
            trace=full_trace,
            agent_response="",
            ground_truth={},
            outcome=1.0,
            pass_threshold=0.5,
        )
        assert len(crs) == 4
        assert all(cr.passed for cr in crs)
        assert s_full == pytest.approx(1.0)
        assert s_partial == pytest.approx(1.0)
