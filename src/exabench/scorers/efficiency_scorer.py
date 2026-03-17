"""Efficiency scorer — measures tool call count and token usage."""

from __future__ import annotations

from exabench.schemas.task import TaskSpec
from exabench.schemas.trace import Trace
from exabench.scorers.base import BaseScorer, ScorerOutput

# Thresholds for full score
_MAX_STEPS_FULL_SCORE = 5
_MAX_STEPS_ZERO_SCORE = 20


class EfficiencyScorer(BaseScorer):
    dimension = "efficiency"

    def score(self, task: TaskSpec, trace: Trace) -> ScorerOutput:
        n_steps = len(trace.steps)
        if n_steps <= _MAX_STEPS_FULL_SCORE:
            score = 1.0
        elif n_steps >= _MAX_STEPS_ZERO_SCORE:
            score = 0.0
        else:
            score = 1.0 - (n_steps - _MAX_STEPS_FULL_SCORE) / (
                _MAX_STEPS_ZERO_SCORE - _MAX_STEPS_FULL_SCORE
            )
        return ScorerOutput(dimension=self.dimension, score=round(score, 4),
                             notes=f"{n_steps} steps")
