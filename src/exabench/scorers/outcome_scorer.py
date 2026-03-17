"""Outcome scorer — checks if the agent produced a non-empty final answer."""

from __future__ import annotations

from exabench.schemas.task import TaskSpec
from exabench.schemas.trace import Trace
from exabench.scorers.base import BaseScorer, ScorerOutput


class OutcomeScorer(BaseScorer):
    """Alpha-0 implementation: awards 1.0 if a non-empty final_answer was produced.

    A full implementation would use eval_criteria (exact_match, semantic_match, etc.)
    from the task spec. This stub ensures the pipeline is runnable before gold answers
    are populated.
    """

    dimension = "outcome"

    def score(self, task: TaskSpec, trace: Trace) -> ScorerOutput:
        if trace.hard_fail:
            return ScorerOutput(dimension=self.dimension, score=0.0,
                                hard_fail=True, hard_fail_reason=trace.hard_fail_reason)

        if not trace.final_answer or not trace.final_answer.strip():
            return ScorerOutput(dimension=self.dimension, score=0.0,
                                notes="No final answer produced")

        # If gold answer is available, do exact match
        if task.eval_criteria and task.eval_criteria.gold_answer:
            gold = task.eval_criteria.gold_answer.strip().lower()
            pred = trace.final_answer.strip().lower()
            score = 1.0 if pred == gold else 0.0
            return ScorerOutput(dimension=self.dimension, score=score)

        # No gold answer yet — give partial credit for producing any answer
        return ScorerOutput(dimension=self.dimension, score=0.5,
                             notes="Gold answer not set; partial credit for non-empty answer")
