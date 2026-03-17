"""Base scorer interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from exabench.schemas.task import TaskSpec
from exabench.schemas.trace import Trace


@dataclass
class ScorerOutput:
    dimension: str
    score: float          # 0.0 – 1.0
    hard_fail: bool = False
    hard_fail_reason: str | None = None
    notes: str | None = None


class BaseScorer(ABC):
    dimension: str  # Must be set as class attribute

    @abstractmethod
    def score(self, task: TaskSpec, trace: Trace) -> ScorerOutput:
        ...
