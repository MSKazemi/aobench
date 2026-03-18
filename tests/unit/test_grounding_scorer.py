"""Unit tests for GroundingScorer."""

from __future__ import annotations

from exabench.schemas.task import TaskSpec
from exabench.schemas.trace import Observation, ToolCall, Trace, TraceStep
from exabench.scorers.grounding_scorer import GroundingScorer


def _task() -> TaskSpec:
    return TaskSpec(
        task_id="TST_001", title="T", query_text="Q",
        role="scientific_user", qcat="JOB", difficulty="easy",
        environment_id="env_01", expected_answer_type="diagnosis",
    )


def _trace(
    final_answer: str | None,
    obs_contents: list[str | None] = (),
    hard_fail: bool = False,
) -> Trace:
    steps = []
    for i, content in enumerate(obs_contents):
        steps.append(TraceStep(
            step_id=i + 1,
            tool_call=ToolCall(tool_name="slurm__query_jobs", arguments={}),
            observation=Observation(content=content, error=None if content else "no data"),
        ))
    return Trace(
        trace_id="t1", run_id="r1", task_id="TST_001",
        role="scientific_user", environment_id="env_01",
        adapter_name="openai", steps=steps,
        final_answer=final_answer, hard_fail=hard_fail,
    )


scorer = GroundingScorer()


def test_no_answer_scores_zero():
    result = scorer.score(_task(), _trace(final_answer=None))
    assert result.score == 0.0


def test_no_observations_scores_zero():
    result = scorer.score(_task(), _trace(final_answer="Job 891234 failed"))
    assert result.score == 0.0


def test_hard_fail_scores_zero():
    result = scorer.score(_task(), _trace(final_answer="x", hard_fail=True))
    assert result.score == 0.0
    assert result.hard_fail is True


def test_answer_tokens_in_observations_high_score():
    # Observation contains "891234" and "failed" — answer mentions same tokens
    result = scorer.score(
        _task(),
        _trace(
            final_answer="Job 891234 failed",
            obs_contents=["job_id 891234 state FAILED oom_kill true"],
        ),
    )
    assert result.score >= 0.5


def test_answer_tokens_not_in_observations_low_score():
    result = scorer.score(
        _task(),
        _trace(
            final_answer="Job 891234 failed with OOM",
            obs_contents=["cluster utilisation normal, no anomalies detected"],
        ),
    )
    # "891234" and "failed" and "oom" not in observations → low overlap
    assert result.score < 0.5


def test_vague_answer_gets_partial_credit():
    # Answer with no extractable key tokens (no numbers, no status words, no HPC entities)
    result = scorer.score(
        _task(),
        _trace(
            final_answer="Something went wrong",
            obs_contents=["job_id 891234 FAILED"],
        ),
    )
    assert result.score == 0.3


def test_error_observations_ignored():
    # Error observations should not count as evidence
    trace = Trace(
        trace_id="t1", run_id="r1", task_id="TST_001",
        role="scientific_user", environment_id="env_01",
        adapter_name="openai",
        steps=[
            TraceStep(
                step_id=1,
                tool_call=ToolCall(tool_name="slurm__job_details", arguments={}),
                observation=Observation(content=None, error="Job not found"),
            )
        ],
        final_answer="Job 891234 failed",
    )
    result = scorer.score(_task(), trace)
    assert result.score == 0.0
