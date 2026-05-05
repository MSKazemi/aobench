"""HPC Task Set v1 loader and validator.

Loads ``task_set_v1.json`` and validates each entry against the
``HPCTaskSpec`` Pydantic model, failing fast on any malformed task.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Union

from aobench.schemas.task import HPCTaskSpec


def load_hpc_task_set(path: Union[str, Path]) -> list[HPCTaskSpec]:
    """Load and validate all tasks from ``task_set_v1.json``.

    Parameters
    ----------
    path:
        Path to ``task_set_v1.json``.  May be absolute or relative to the
        current working directory.

    Returns
    -------
    list[HPCTaskSpec]
        Validated task objects, one per JSON entry.

    Raises
    ------
    FileNotFoundError
        If ``path`` does not exist.
    json.JSONDecodeError
        If the file is not valid JSON.
    pydantic.ValidationError
        If any task fails schema validation (fail-fast — first bad task wins).
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Task set file not found: {path}")

    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(
            f"Expected a JSON array at the top level of {path}, got {type(raw).__name__}"
        )

    tasks: list[HPCTaskSpec] = []
    for i, item in enumerate(raw):
        try:
            tasks.append(HPCTaskSpec.model_validate(item))
        except Exception as exc:
            task_id = item.get("task_id", f"<index {i}>")
            raise ValueError(
                f"Validation failed for task '{task_id}' at index {i}: {exc}"
            ) from exc

    return tasks


def load_hpc_task(task_id: str, path: Union[str, Path]) -> HPCTaskSpec:
    """Load a single task by ID from ``task_set_v1.json``.

    Parameters
    ----------
    task_id:
        The ``task_id`` string to look up (e.g. ``"telemetry_04"``).
    path:
        Path to ``task_set_v1.json``.

    Returns
    -------
    HPCTaskSpec
        The validated task matching ``task_id``.

    Raises
    ------
    KeyError
        If no task with the given ``task_id`` is found.
    """
    tasks = load_hpc_task_set(path)
    index: dict[str, HPCTaskSpec] = {t.task_id: t for t in tasks}
    if task_id not in index:
        raise KeyError(
            f"Task '{task_id}' not found in {path}. "
            f"Available IDs: {sorted(index)}"
        )
    return index[task_id]
