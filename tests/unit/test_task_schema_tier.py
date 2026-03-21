"""Unit tests for difficulty_tier field and consistency validator in task schemas."""

import pytest
from pydantic import ValidationError

from exabench.schemas.task import HPCTaskSpec, TaskSpec


# ---------------------------------------------------------------------------
# Minimal valid kwargs for TaskSpec
# ---------------------------------------------------------------------------
_TASK_BASE = dict(
    task_id="t_01",
    title="Test task",
    query_text="What is X?",
    role="scientific_user",
    qcat="JOB",
    difficulty="easy",
    environment_id="env_01",
    expected_answer_type="factoid",
)

# Minimal valid kwargs for HPCTaskSpec
_HPC_BASE = dict(
    task_id="hpc_01",
    question="What is the job state?",
    data_type="job_ops",
    workload_type="OLTP",
    temporal="retrospective",
    scoring_mode="deterministic",
    difficulty="easy",
    snapshot_id="env_01",
)


# ---------------------------------------------------------------------------
# TaskSpec tests
# ---------------------------------------------------------------------------


def test_difficulty_tier_consistency_valid():
    spec = TaskSpec(**{**_TASK_BASE, "difficulty_tier": 1})
    assert spec.difficulty_tier == 1


def test_difficulty_tier_consistency_invalid():
    with pytest.raises((ValidationError, ValueError)):
        TaskSpec(**{**_TASK_BASE, "difficulty": "easy", "difficulty_tier": 2})


def test_difficulty_tier_none_allowed():
    spec = TaskSpec(**{**_TASK_BASE, "difficulty": "hard", "difficulty_tier": None})
    assert spec.difficulty_tier is None


def test_adversarial_maps_to_tier3():
    spec = TaskSpec(**{**_TASK_BASE, "difficulty": "adversarial", "difficulty_tier": 3})
    assert spec.difficulty_tier == 3


def test_medium_maps_to_tier2():
    spec = TaskSpec(**{**_TASK_BASE, "difficulty": "medium", "difficulty_tier": 2})
    assert spec.difficulty_tier == 2


def test_hard_maps_to_tier3():
    spec = TaskSpec(**{**_TASK_BASE, "difficulty": "hard", "difficulty_tier": 3})
    assert spec.difficulty_tier == 3


# ---------------------------------------------------------------------------
# HPCTaskSpec tests
# ---------------------------------------------------------------------------


def test_hpc_difficulty_tier_valid():
    spec = HPCTaskSpec(**{**_HPC_BASE, "difficulty_tier": 1})
    assert spec.difficulty_tier == 1


def test_hpc_difficulty_tier_invalid():
    with pytest.raises((ValidationError, ValueError)):
        HPCTaskSpec(**{**_HPC_BASE, "difficulty": "easy", "difficulty_tier": 3})


def test_hpc_difficulty_tier_none_allowed():
    spec = HPCTaskSpec(**{**_HPC_BASE, "difficulty_tier": None})
    assert spec.difficulty_tier is None


def test_hpc_adversarial_maps_to_tier3():
    spec = HPCTaskSpec(**{**_HPC_BASE, "difficulty": "adversarial", "difficulty_tier": 3})
    assert spec.difficulty_tier == 3
