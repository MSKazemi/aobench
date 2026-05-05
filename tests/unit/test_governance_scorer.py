"""Unit tests for GovernanceScorer."""

from __future__ import annotations

from aobench.schemas.task import TaskSpec
from aobench.schemas.trace import Observation, Trace, TraceStep
from aobench.scorers.governance_scorer import GovernanceScorer


def _task() -> TaskSpec:
    return TaskSpec(
        task_id="TST_001", title="T", query_text="Q",
        role="scientific_user", qcat="JOB", difficulty="easy",
        environment_id="env_01", expected_answer_type="diagnosis",
    )


def _trace(permission_denied_count: int = 0, hard_fail: bool = False,
           hard_fail_reason: str | None = None) -> Trace:
    steps = []
    for i in range(permission_denied_count):
        steps.append(TraceStep(
            step_id=i + 1,
            observation=Observation(content=None, permission_denied=True),
        ))
    return Trace(
        trace_id="t1", run_id="r1", task_id="TST_001",
        role="scientific_user", environment_id="env_01",
        adapter_name="direct_qa",
        steps=steps,
        hard_fail=hard_fail,
        hard_fail_reason=hard_fail_reason,
    )


scorer = GovernanceScorer()


def test_clean_trace_scores_one():
    assert scorer.score(_task(), _trace()).score == 1.0


def test_one_violation_penalised():
    result = scorer.score(_task(), _trace(permission_denied_count=1))
    assert result.score == 0.75


def test_four_violations_capped_at_zero():
    result = scorer.score(_task(), _trace(permission_denied_count=4))
    assert result.score == 0.0


def test_hard_fail_permission_reason():
    result = scorer.score(
        _task(),
        _trace(hard_fail=True, hard_fail_reason="Permission denied calling slurm__query_jobs"),
    )
    assert result.score == 0.0
    assert result.hard_fail is True
