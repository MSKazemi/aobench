"""Base scorer interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from exabench.schemas.task import TaskSpec
from exabench.schemas.trace import Trace


@dataclass
class ScorerOutput:
    dimension: str
    score: float          # 0.0 – 1.0
    hard_fail: bool = False
    hard_fail_reason: str | None = None
    notes: str | None = None
    # DangerousArgViolation objects from GovernanceScorer (untyped to avoid circular import)
    dangerous_arg_violations: list = field(default_factory=list)
    # ViolationVector from GovernanceScorer (untyped to avoid circular import)
    violation_vector: Any = None
    # ToolUseResult from ToolUseScorer (untyped to avoid circular import)
    tool_use_detail: Any = None


class BaseScorer(ABC):
    dimension: str  # Must be set as class attribute

    @abstractmethod
    def score(self, task: TaskSpec, trace: Trace) -> ScorerOutput:
        ...
