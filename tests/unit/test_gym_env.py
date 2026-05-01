"""Tests for ExaBenchEnv gymnasium-compatible environment (gymnasium_env_spec §11)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from exabench.gym.exabench_env import ExaBenchEnv
from exabench.gym.spaces import ACTION_SPACE, OBSERVATION_SPACE, DictSpace


# ---- Space tests ----

def test_observation_space_is_dict():
    assert isinstance(OBSERVATION_SPACE, DictSpace)
    assert "task_query" in OBSERVATION_SPACE.spaces
    assert "step_count" in OBSERVATION_SPACE.spaces


def test_action_space_is_dict():
    assert isinstance(ACTION_SPACE, DictSpace)
    assert "type" in ACTION_SPACE.spaces
    assert "tool_name" in ACTION_SPACE.spaces
    assert "finish_answer" in ACTION_SPACE.spaces


# ---- ExaBenchEnv attribute tests (no reset needed) ----

def test_env_has_spaces():
    env = ExaBenchEnv()
    assert env.observation_space is OBSERVATION_SPACE
    assert env.action_space is ACTION_SPACE


def test_step_before_reset_raises():
    env = ExaBenchEnv()
    with pytest.raises(RuntimeError, match="reset"):
        env.step({"type": "finish", "finish_answer": "done"})


# ---- Reset / step tests using test fixtures ----

_TASK_DIR = Path(__file__).parent.parent / "data" / "tasks"
_ENV_DIR = Path(__file__).parent.parent / "data" / "environments"


def _make_minimal_task(tmp_dir: Path, task_id: str = "TEST_GYM_001",
                        expected_tool_calls: list[str] | None = None) -> Path:
    """Write a minimal task spec JSON into tmp_dir."""
    spec = {
        "task_id": task_id,
        "title": "Gym test task",
        "query_text": "Why did my job fail?",
        "role": "scientific_user",
        "qcat": "JOB",
        "difficulty": "easy",
        "environment_id": "test_env_01",
        "expected_answer_type": "diagnosis",
        "eval_criteria": {"gold_answer": "OOM kill"},
        "allowed_tools": ["slurm", "docs"],
    }
    if expected_tool_calls is not None:
        spec["expected_tool_calls"] = expected_tool_calls
    task_path = tmp_dir / f"{task_id}.json"
    task_path.write_text(json.dumps(spec))
    return tmp_dir


def test_reset_returns_obs_and_info():
    with tempfile.TemporaryDirectory() as tmp:
        task_dir = Path(tmp)
        _make_minimal_task(task_dir)
        env = ExaBenchEnv(task_dir=task_dir, env_dir=_ENV_DIR)
        obs, info = env.reset(task_id="TEST_GYM_001", seed=42)

    assert isinstance(obs, dict)
    assert "task_query" in obs
    assert "step_count" in obs
    assert obs["step_count"] == 0
    assert obs["task_query"] == "Why did my job fail?"

    assert isinstance(info, dict)
    assert "engaged" in info
    assert info["engaged"] is False
    assert info["task_id"] == "TEST_GYM_001"


def test_finish_action_terminates():
    with tempfile.TemporaryDirectory() as tmp:
        task_dir = Path(tmp)
        _make_minimal_task(task_dir)
        env = ExaBenchEnv(task_dir=task_dir, env_dir=_ENV_DIR)
        env.reset(task_id="TEST_GYM_001", seed=0)

        action = {"type": "finish", "finish_answer": "OOM kill"}
        obs, reward, terminated, truncated, info = env.step(action)

    assert terminated is True
    assert truncated is False
    assert isinstance(reward, float)
    assert "FINISHED" in obs["last_tool_result"]


def test_step_after_terminate_raises():
    with tempfile.TemporaryDirectory() as tmp:
        task_dir = Path(tmp)
        _make_minimal_task(task_dir)
        env = ExaBenchEnv(task_dir=task_dir, env_dir=_ENV_DIR)
        env.reset(task_id="TEST_GYM_001", seed=0)
        env.step({"type": "finish", "finish_answer": "done"})
        with pytest.raises(RuntimeError, match="terminated"):
            env.step({"type": "message", "message": "more"})


def test_message_action_increments_step():
    with tempfile.TemporaryDirectory() as tmp:
        task_dir = Path(tmp)
        _make_minimal_task(task_dir)
        env = ExaBenchEnv(task_dir=task_dir, env_dir=_ENV_DIR)
        env.reset(task_id="TEST_GYM_001", seed=0)

        obs, reward, terminated, truncated, info = env.step({"type": "message", "message": "hello"})

    assert obs["step_count"] == 1
    assert terminated is False
    assert reward == 0.0


def test_engaged_flag_set_when_expected_tool_called():
    """info[engaged] becomes True when agent calls a tool in expected_tool_calls."""
    with tempfile.TemporaryDirectory() as tmp:
        task_dir = Path(tmp)
        _make_minimal_task(task_dir, expected_tool_calls=["slurm"])
        env = ExaBenchEnv(task_dir=task_dir, env_dir=_ENV_DIR)
        obs, info = env.reset(task_id="TEST_GYM_001", seed=0)
        assert info["engaged"] is False

        # A non-expected tool call should not set engaged
        _, _, _, _, info2 = env.step({"type": "tool_call", "tool_name": "docs", "method": "search", "arguments": "{}"})
        assert info2["engaged"] is False

        # Now call a tool in expected_tool_calls
        _, _, _, _, info3 = env.step({"type": "tool_call", "tool_name": "slurm", "method": "query_jobs", "arguments": "{}"})
        assert info3["engaged"] is True


def test_not_engaged_when_no_expected_tool_calls():
    """Task with no expected_tool_calls → engaged stays False regardless of tool calls."""
    with tempfile.TemporaryDirectory() as tmp:
        task_dir = Path(tmp)
        _make_minimal_task(task_dir, expected_tool_calls=None)
        env = ExaBenchEnv(task_dir=task_dir, env_dir=_ENV_DIR)
        env.reset(task_id="TEST_GYM_001", seed=0)
        _, _, _, _, info = env.step({"type": "tool_call", "tool_name": "slurm", "method": "query_jobs", "arguments": "{}"})
        assert info["engaged"] is False


def test_seed_determinism():
    """Same seed should produce same observation after reset."""
    with tempfile.TemporaryDirectory() as tmp:
        task_dir = Path(tmp)
        _make_minimal_task(task_dir)
        env = ExaBenchEnv(task_dir=task_dir, env_dir=_ENV_DIR)
        obs1, _ = env.reset(task_id="TEST_GYM_001", seed=99)
        obs2, _ = env.reset(task_id="TEST_GYM_001", seed=99)
        assert obs1 == obs2


def test_close_clears_state():
    with tempfile.TemporaryDirectory() as tmp:
        task_dir = Path(tmp)
        _make_minimal_task(task_dir)
        env = ExaBenchEnv(task_dir=task_dir, env_dir=_ENV_DIR)
        env.reset(task_id="TEST_GYM_001", seed=0)
        env.close()
        assert env._task is None
        assert env._registry is None
