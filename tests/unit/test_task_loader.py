"""Unit tests for task loader."""

from aobench.loaders.task_loader import load_task, load_tasks_from_dir
from aobench.schemas.task import TaskSpec


def test_load_single_task(test_task_path):
    task = load_task(test_task_path)
    assert isinstance(task, TaskSpec)
    assert task.task_id == "TEST_USR_001"


def test_load_tasks_from_dir(benchmark_root):
    tasks = load_tasks_from_dir(benchmark_root / "tasks" / "specs")
    assert len(tasks) >= 1
    ids = [t.task_id for t in tasks]
    assert "JOB_USR_001" in ids


def test_load_task_not_found(tmp_path):
    import pytest
    with pytest.raises(FileNotFoundError):
        load_task(tmp_path / "nonexistent.json")
