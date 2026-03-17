"""Execution context — bundles all inputs needed for one task run."""

from __future__ import annotations

from dataclasses import dataclass, field

from exabench.schemas.environment import EnvironmentBundle
from exabench.schemas.task import TaskSpec
from exabench.tools.registry import ToolRegistry
from exabench.utils.ids import make_run_id


@dataclass
class ExecutionContext:
    """Everything the adapter needs to run a task."""

    task: TaskSpec
    env: EnvironmentBundle
    tools: ToolRegistry
    run_id: str = field(default_factory=make_run_id)
