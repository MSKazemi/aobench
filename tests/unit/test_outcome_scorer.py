"""Unit tests for OutcomeScorer."""

from __future__ import annotations

import pytest

from exabench.schemas.task import EvalCriteria, TaskSpec
from exabench.schemas.trace import Trace
from exabench.scorers.outcome_scorer import OutcomeScorer


def _task(gold: str | None = None, mode: str = "semantic_match") -> TaskSpec:
    criteria = EvalCriteria(evaluation_mode=mode, gold_answer=gold) if gold or mode != "semantic_match" else None  # type: ignore[arg-type]
    return TaskSpec(
        task_id="TST_001",
        title="Test task",
        query_text="What failed?",
        role="scientific_user",
        qcat="JOB",
        difficulty="easy",
        environment_id="env_01",
        expected_answer_type="diagnosis",
        eval_criteria=EvalCriteria(evaluation_mode=mode, gold_answer=gold),  # type: ignore[arg-type]
    )


def _trace(answer: str | None = "some answer", hard_fail: bool = False) -> Trace:
    return Trace(
        trace_id="t1", run_id="r1", task_id="TST_001",
        role="scientific_user", environment_id="env_01",
        adapter_name="direct_qa",
        final_answer=answer,
        hard_fail=hard_fail,
    )


scorer = OutcomeScorer()


def test_exact_match_hit():
    result = scorer.score(_task(gold="OOM kill", mode="exact_match"), _trace("OOM kill"))
    assert result.score == 1.0


def test_exact_match_miss():
    result = scorer.score(_task(gold="OOM kill", mode="exact_match"), _trace("timeout"))
    assert result.score == 0.0


def test_exact_match_case_insensitive():
    result = scorer.score(_task(gold="OOM kill", mode="exact_match"), _trace("oom kill"))
    assert result.score == 1.0


def test_semantic_match_similar():
    result = scorer.score(
        _task(gold="Job 891234 failed due to out-of-memory", mode="semantic_match"),
        _trace("Job 891234 failed: OOM kill"),
    )
    # Fuzzy partial_ratio should give a decent score for similar strings
    assert result.score > 0.5


def test_semantic_match_completely_different():
    result = scorer.score(
        _task(gold="Job 891234 failed due to out-of-memory", mode="semantic_match"),
        _trace("The weather is fine today"),
    )
    assert result.score < 0.5


def test_numeric_tolerance_within():
    result = scorer.score(
        _task(gold="3.14 kW average", mode="semantic_match"),
        _trace("The average power is 3.15 kW"),
    )
    # numeric part 3.14 vs 3.15 — within 5% tolerance
    assert result.score > 0.3


def test_no_gold_answer_partial_credit():
    task = TaskSpec(
        task_id="TST_002", title="T", query_text="Q",
        role="sysadmin", qcat="MON", difficulty="medium",
        environment_id="env_02", expected_answer_type="diagnosis",
        eval_criteria=EvalCriteria(evaluation_mode="semantic_match", gold_answer=None),
    )
    result = scorer.score(task, _trace("some answer"))
    assert result.score == 0.5


def test_empty_answer_scores_zero():
    result = scorer.score(_task(gold="OOM kill", mode="exact_match"), _trace(""))
    assert result.score == 0.0


def test_hard_fail_scores_zero():
    result = scorer.score(_task(gold="OOM kill", mode="exact_match"), _trace(hard_fail=True))
    assert result.score == 0.0
    assert result.hard_fail is True
