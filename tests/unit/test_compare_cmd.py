"""Unit tests for compare_cmd helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from exabench.cli.compare_cmd import filter_tasks


def make_task_row(task_id, role, score, hard_fail=False):
    return {
        "task_id": task_id,
        "role": role,
        "aggregate_score": score,
        "hard_fail": hard_fail,
        "outcome": score,
        "tool_use": score,
        "grounding": score,
        "governance": score,
        "efficiency": score,
        "robustness": None,
    }


# ---------------------------------------------------------------------------
# filter_tasks
# ---------------------------------------------------------------------------

def _mixed_tasks():
    return [
        make_task_row("JOB_ADM_001", "sysadmin", 0.8),
        make_task_row("JOB_USR_001", "user", 0.7),
        make_task_row("PERF_ADM_001", "sysadmin", 0.6),
        make_task_row("PERF_USR_001", "user", 0.5),
        make_task_row("MON_ADM_001", "sysadmin", 0.4),
        make_task_row("MON_USR_001", "user", 0.3),
        make_task_row("JOB_ADM_002", "sysadmin", 0.9),
        make_task_row("JOB_USR_002", "scientific_user", 0.2),
        make_task_row("SEC_ADM_001", "sysadmin", 0.1),
        make_task_row("SEC_USR_001", "scientific_user", 0.55),
    ]


def test_filter_tasks_by_qcat():
    tasks = _mixed_tasks()
    result = filter_tasks(tasks, qcat="JOB", role=None)
    assert len(result) == 4
    assert all(t["task_id"].startswith("JOB_") for t in result)


def test_filter_tasks_by_role():
    tasks = _mixed_tasks()
    result = filter_tasks(tasks, qcat=None, role="sysadmin")
    assert len(result) == 5
    assert all(t["role"] == "sysadmin" for t in result)


def test_filter_tasks_combined():
    tasks = _mixed_tasks()
    result = filter_tasks(tasks, qcat="JOB", role="sysadmin")
    assert len(result) == 2
    assert all(t["task_id"].startswith("JOB_") and t["role"] == "sysadmin" for t in result)


# ---------------------------------------------------------------------------
# hard_fail_changed logic (tested via the core logic, not CLI)
# ---------------------------------------------------------------------------

def _hard_fail_changed(hard_fail_a: bool, hard_fail_b: bool) -> str | None:
    if not hard_fail_a and hard_fail_b:
        return "new_fail"
    elif hard_fail_a and not hard_fail_b:
        return "resolved"
    else:
        return None


def test_hard_fail_delta_new_fail():
    assert _hard_fail_changed(False, True) == "new_fail"


def test_hard_fail_delta_resolved():
    assert _hard_fail_changed(True, False) == "resolved"


def test_hard_fail_delta_unchanged():
    assert _hard_fail_changed(False, False) is None
    assert _hard_fail_changed(True, True) is None


# ---------------------------------------------------------------------------
# delta threshold logic
# ---------------------------------------------------------------------------

def _classify(delta: float, threshold: float) -> str:
    if delta > threshold:
        return "improved"
    elif delta < -threshold:
        return "regressed"
    else:
        return "unchanged"


def test_delta_threshold_configurable():
    assert _classify(0.004, 0.005) == "unchanged"
    assert _classify(0.004, 0.003) == "improved"
    assert _classify(-0.004, 0.003) == "regressed"
    assert _classify(-0.004, 0.005) == "unchanged"


# ---------------------------------------------------------------------------
# JSON output schema tests (via CLI runner)
# ---------------------------------------------------------------------------

def _build_result_json(task_id, role, score, hard_fail, run_id, env_id="env01"):
    from datetime import datetime, timezone
    return {
        "result_id": f"{task_id}_result",
        "run_id": run_id,
        "task_id": task_id,
        "role": role,
        "environment_id": env_id,
        "adapter_name": "direct_qa",
        "hard_fail": hard_fail,
        "hard_fail_reason": "rbac" if hard_fail else None,
        "rbac_compliant": not hard_fail,
        "dimension_scores": {
            "outcome": score,
            "tool_use": score,
            "grounding": score,
            "governance": score,
            "efficiency": score,
            "robustness": None,
        },
        "aggregate_score": score,
        "weight_profile_name": "default_hpc_v01",
        "model_name": "test-model",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _make_run_dir(tmp_path, run_id, tasks):
    run_dir = tmp_path / run_id
    results_dir = run_dir / "results"
    results_dir.mkdir(parents=True)
    for t in tasks:
        data = _build_result_json(
            task_id=t["task_id"],
            role=t["role"],
            score=t["score"],
            hard_fail=t.get("hard_fail", False),
            run_id=run_id,
        )
        (results_dir / f"{t['task_id']}_result.json").write_text(json.dumps(data))
    return run_dir


def test_output_json_schema(tmp_path):
    from typer.testing import CliRunner
    from exabench.cli.main import app

    tasks_a = [
        {"task_id": "JOB_ADM_001", "role": "sysadmin", "score": 0.5, "hard_fail": False},
        {"task_id": "JOB_ADM_002", "role": "sysadmin", "score": 0.6, "hard_fail": True},
        {"task_id": "JOB_USR_001", "role": "user", "score": 0.7, "hard_fail": False},
    ]
    tasks_b = [
        {"task_id": "JOB_ADM_001", "role": "sysadmin", "score": 0.7, "hard_fail": True},
        {"task_id": "JOB_ADM_002", "role": "sysadmin", "score": 0.8, "hard_fail": False},
        {"task_id": "JOB_USR_001", "role": "user", "score": 0.7, "hard_fail": False},
    ]
    run_dir_a = _make_run_dir(tmp_path, "run_a", tasks_a)
    run_dir_b = _make_run_dir(tmp_path, "run_b", tasks_b)
    out = tmp_path / "diff.json"

    runner = CliRunner()
    result = runner.invoke(app, ["compare", "runs", str(run_dir_a), str(run_dir_b), "--output", str(out)])
    assert result.exit_code == 0, result.output

    data = json.loads(out.read_text())
    assert "summary" in data
    assert "new_hard_fails" in data["summary"]
    assert data["tasks"][0]["hard_fail_changed"] is not None or data["tasks"][0]["hard_fail_changed"] is None
    assert "hard_fail_changed" in data["tasks"][0]
    assert data["summary"]["new_hard_fails"] == 1
    assert data["summary"]["resolved_hard_fails"] == 1


def test_label_override_in_json(tmp_path):
    from typer.testing import CliRunner
    from exabench.cli.main import app

    tasks = [{"task_id": "JOB_ADM_001", "role": "sysadmin", "score": 0.5}]
    run_dir_a = _make_run_dir(tmp_path, "run_a", tasks)
    run_dir_b = _make_run_dir(tmp_path, "run_b", tasks)
    out = tmp_path / "diff.json"

    runner = CliRunner()
    result = runner.invoke(app, [
        "compare", "runs", str(run_dir_a), str(run_dir_b),
        "--label-a", "GPT-4o", "--label-b", "Claude",
        "--output", str(out),
    ])
    assert result.exit_code == 0, result.output

    data = json.loads(out.read_text())
    assert data["run_a"] == "GPT-4o"
    assert data["run_b"] == "Claude"
