"""Load and validate task specs from JSON files."""

from __future__ import annotations

import json
from pathlib import Path

from exabench.schemas.task import TaskSpec


def load_task(path: str | Path) -> TaskSpec:
    """Load a single task spec from a JSON file, validating against the schema."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Task spec not found: {path}")
    with path.open() as f:
        data = json.load(f)
    return TaskSpec.model_validate(data)


def load_tasks_from_dir(specs_dir: str | Path) -> list[TaskSpec]:
    """Load all *.json task specs from a directory."""
    specs_dir = Path(specs_dir)
    tasks = []
    for p in sorted(specs_dir.glob("*.json")):
        tasks.append(load_task(p))
    return tasks
