"""Unit tests for MockSlurmTool."""

from __future__ import annotations

from pathlib import Path

import pytest

from exabench.tools.slurm_tool import MockSlurmTool

ENV_ROOT = str(Path(__file__).parent.parent / "data" / "environments" / "test_env_01")


def test_query_jobs_returns_list():
    tool = MockSlurmTool(ENV_ROOT, role="sysadmin")
    result = tool.call("query_jobs")
    assert result.success
    assert isinstance(result.data, list)


def test_scientific_user_sees_own_jobs_only():
    tool = MockSlurmTool(ENV_ROOT, role="scientific_user", requester_user="alice")
    result = tool.call("query_jobs")
    assert result.success
    for job in result.data:
        assert job["user"] == "alice"


def test_query_jobs_state_filter():
    tool = MockSlurmTool(ENV_ROOT, role="sysadmin")
    result = tool.call("query_jobs", state="FAILED")
    assert result.success
    for job in result.data:
        assert job["state"] == "FAILED"


def test_unknown_method_returns_error():
    tool = MockSlurmTool(ENV_ROOT, role="sysadmin")
    result = tool.call("nonexistent_method")
    assert not result.success
    assert result.error is not None
