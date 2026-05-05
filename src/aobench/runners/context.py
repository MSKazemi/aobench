"""Execution context — bundles all inputs needed for one task run."""

from __future__ import annotations

from dataclasses import dataclass, field

from aobench.schemas.environment import EnvironmentBundle
from aobench.schemas.task import TaskSpec
from aobench.tools.registry import ToolRegistry
from aobench.utils.ids import make_run_id


@dataclass
class ExecutionContext:
    """Everything the adapter needs to run a task."""

    task: TaskSpec
    env: EnvironmentBundle
    tools: ToolRegistry
    run_id: str = field(default="")

    def __post_init__(self) -> None:
        if not self.run_id:
            self.run_id = make_run_id()
