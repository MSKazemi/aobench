"""Unit tests for Pydantic schemas."""

import pytest
from pydantic import ValidationError

from exabench.schemas.task import TaskSpec


def test_task_spec_minimal():
    data = {
        "task_id": "TEST_001",
        "title": "Test",
        "query_text": "What failed?",
        "role": "scientific_user",
        "qcat": "JOB",
        "difficulty": "easy",
        "environment_id": "env_01",
        "expected_answer_type": "diagnosis",
    }
    task = TaskSpec.model_validate(data)
    assert task.task_id == "TEST_001"
    assert task.role == "scientific_user"


def test_task_spec_invalid_role():
    data = {
        "task_id": "TEST_001",
        "title": "Test",
        "query_text": "?",
        "role": "god_mode",  # invalid
        "qcat": "JOB",
        "difficulty": "easy",
        "environment_id": "env_01",
        "expected_answer_type": "diagnosis",
    }
    with pytest.raises(ValidationError):
        TaskSpec.model_validate(data)


def test_task_spec_invalid_qcat():
    data = {
        "task_id": "TEST_001",
        "title": "Test",
        "query_text": "?",
        "role": "scientific_user",
        "qcat": "UNKNOWN",  # invalid
        "difficulty": "easy",
        "environment_id": "env_01",
        "expected_answer_type": "diagnosis",
    }
    with pytest.raises(ValidationError):
        TaskSpec.model_validate(data)
