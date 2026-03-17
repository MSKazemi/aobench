"""In-memory registry for tasks and environments."""

from __future__ import annotations

from pathlib import Path

from exabench.loaders.env_loader import load_environment
from exabench.loaders.task_loader import load_tasks_from_dir
from exabench.schemas.environment import EnvironmentBundle
from exabench.schemas.task import TaskSpec


class BenchmarkRegistry:
    """Loads and indexes all tasks and environments from the benchmark data directory."""

    def __init__(self, benchmark_root: str | Path) -> None:
        self._root = Path(benchmark_root)
        self._tasks: dict[str, TaskSpec] = {}
        self._envs: dict[str, EnvironmentBundle] = {}

    def load_all(self) -> None:
        specs_dir = self._root / "tasks" / "specs"
        for task in load_tasks_from_dir(specs_dir):
            self._tasks[task.task_id] = task

        envs_dir = self._root / "environments"
        for env_dir in sorted(envs_dir.iterdir()):
            if env_dir.is_dir() and (env_dir / "metadata.yaml").exists():
                bundle = load_environment(env_dir)
                self._envs[bundle.metadata.environment_id] = bundle

    def get_task(self, task_id: str) -> TaskSpec:
        if task_id not in self._tasks:
            raise KeyError(f"Task not found: '{task_id}'")
        return self._tasks[task_id]

    def get_environment(self, env_id: str) -> EnvironmentBundle:
        if env_id not in self._envs:
            raise KeyError(f"Environment not found: '{env_id}'")
        return self._envs[env_id]

    @property
    def task_ids(self) -> list[str]:
        return list(self._tasks)

    @property
    def environment_ids(self) -> list[str]:
        return list(self._envs)
