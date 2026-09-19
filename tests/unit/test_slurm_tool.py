"""Unit tests for MockSlurmTool."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aobench.tools.slurm_tool import MockSlurmTool

ENV_ROOT = str(Path(__file__).parent.parent / "data" / "environments" / "test_env_01")
CORPUS_ROOT = Path(__file__).resolve().parents[2] / "benchmark" / "environments"


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


@pytest.mark.parametrize("env_id", ["env_01", "env_04", "env_09", "env_19"])
def test_job_details_preserve_corpus_shapes(env_id):
    env = CORPUS_ROOT / env_id
    raw = json.loads((env / "slurm/job_details.json").read_text(encoding="utf-8"))
    tool = MockSlurmTool(str(env), role="sysadmin")
    loaded = tool._load_json("slurm/job_details.json")
    assert type(loaded) is type(raw)
    assert loaded == raw
    records = raw if isinstance(raw, list) else [raw]
    for record in records:
        result = tool.call("job_details", job_id=str(record["job_id"]))
        assert result.success
        assert result.data == record
    assert not tool.call("job_details", job_id="not-a-corpus-job").success


@pytest.mark.parametrize("env", sorted(CORPUS_ROOT.glob("*/slurm/slurm_state.json")))
def test_state_snapshots_are_mappings(env):
    tool = MockSlurmTool(str(env.parent.parent), role="sysadmin")
    state = tool._load_json("slurm/slurm_state.json")
    assert isinstance(state, dict)
    assert state == json.loads(env.read_text(encoding="utf-8"))
    assert tool.call("query_jobs").data == state.get("jobs", [])


def test_missing_slurm_snapshots_remain_empty(tmp_path):
    tool = MockSlurmTool(str(tmp_path), role="sysadmin")
    assert tool._load_json("slurm/slurm_state.json") == {}
    assert tool._load_json("slurm/job_details.json") == {}
    assert tool.call("query_jobs").data == []
    assert not tool.call("job_details", job_id="missing").success
