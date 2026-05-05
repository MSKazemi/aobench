"""Unit tests for Pydantic schemas."""

import pytest
from pydantic import ValidationError

from aobench.schemas.task import TaskSpec


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


def test_task_spec_new_roles():
    base = {
        "task_id": "TEST_002",
        "title": "Test",
        "query_text": "?",
        "difficulty": "easy",
        "environment_id": "env_01",
        "expected_answer_type": "diagnosis",
        "qcat": "PERF",
    }
    for role in ("researcher", "system_designer"):
        task = TaskSpec.model_validate({**base, "role": role})
        assert task.role == role


def test_task_spec_knowledge_source_scope():
    data = {
        "task_id": "TEST_003",
        "title": "Test",
        "query_text": "?",
        "role": "sysadmin",
        "qcat": "SEC",
        "difficulty": "medium",
        "environment_id": "env_01",
        "expected_answer_type": "lookup",
        "knowledge_source_scope": ["OPS_DOC", "POLICY"],
    }
    task = TaskSpec.model_validate(data)
    assert task.knowledge_source_scope == ["OPS_DOC", "POLICY"]


def test_task_spec_capabilities_and_access_tier():
    data = {
        "task_id": "TEST_004",
        "title": "Test",
        "query_text": "?",
        "role": "facility_admin",
        "qcat": "ENERGY",
        "difficulty": "hard",
        "environment_id": "env_01",
        "expected_answer_type": "diagnosis",
        "required_capabilities": ["telemetry_querying", "energy_awareness", "diagnostic_reasoning"],
        "access_tier": "tier2_privileged",
    }
    task = TaskSpec.model_validate(data)
    assert "energy_awareness" in task.required_capabilities
    assert task.access_tier == "tier2_privileged"


def test_task_spec_invalid_capability():
    data = {
        "task_id": "TEST_005",
        "title": "Test",
        "query_text": "?",
        "role": "sysadmin",
        "qcat": "MON",
        "difficulty": "easy",
        "environment_id": "env_01",
        "expected_answer_type": "lookup",
        "required_capabilities": ["magic_power"],  # invalid
    }
    with pytest.raises(ValidationError):
        TaskSpec.model_validate(data)


def test_task_spec_invalid_access_tier():
    data = {
        "task_id": "TEST_006",
        "title": "Test",
        "query_text": "?",
        "role": "sysadmin",
        "qcat": "MON",
        "difficulty": "easy",
        "environment_id": "env_01",
        "expected_answer_type": "lookup",
        "access_tier": "tier99_god",  # invalid
    }
    with pytest.raises(ValidationError):
        TaskSpec.model_validate(data)
