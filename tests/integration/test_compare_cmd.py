"""Integration tests for `aobench compare runs`."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from typer.testing import CliRunner

from aobench.cli.main import app


def _build_result_json(task_id, role, score, hard_fail, run_id, env_id="env01"):
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
            role=t.get("role", "sysadmin"),
            score=t["score"],
            hard_fail=t.get("hard_fail", False),
            run_id=run_id,
        )
        (results_dir / f"{t['task_id']}_result.json").write_text(json.dumps(data))
    return run_dir


# Run A: 5 tasks, scores [0.5, 0.6, 0.7, 0.8, 0.4], task[0] has hard_fail=True
# Run B: 5 tasks, same tasks, scores [0.6, 0.5, 0.7, 0.9, 0.3], task[0] now passes
_TASKS_A = [
    {"task_id": "JOB_ADM_001", "role": "sysadmin", "score": 0.5, "hard_fail": True},
    {"task_id": "JOB_ADM_002", "role": "sysadmin", "score": 0.6, "hard_fail": False},
    {"task_id": "JOB_USR_001", "role": "user", "score": 0.7, "hard_fail": False},
    {"task_id": "JOB_USR_002", "role": "user", "score": 0.8, "hard_fail": False},
    {"task_id": "JOB_USR_003", "role": "user", "score": 0.4, "hard_fail": False},
]

_TASKS_B = [
    {"task_id": "JOB_ADM_001", "role": "sysadmin", "score": 0.6, "hard_fail": False},  # resolved, improved
    {"task_id": "JOB_ADM_002", "role": "sysadmin", "score": 0.5, "hard_fail": False},  # regressed
    {"task_id": "JOB_USR_001", "role": "user", "score": 0.7, "hard_fail": False},      # unchanged
    {"task_id": "JOB_USR_002", "role": "user", "score": 0.9, "hard_fail": False},      # improved
    {"task_id": "JOB_USR_003", "role": "user", "score": 0.3, "hard_fail": False},      # regressed
]


def test_compare_runs_full(tmp_path):
    run_dir_a = _make_run_dir(tmp_path, "run_a", _TASKS_A)
    run_dir_b = _make_run_dir(tmp_path, "run_b", _TASKS_B)
    out = tmp_path / "diff.json"

    runner = CliRunner()
    result = runner.invoke(app, ["compare", "runs", str(run_dir_a), str(run_dir_b), "--output", str(out)])
    assert result.exit_code == 0, result.output

    output_json = json.loads(out.read_text())

    assert output_json["summary"]["improved"] == 2
    assert output_json["summary"]["regressed"] == 2
    assert output_json["summary"]["unchanged"] == 1
    assert output_json["summary"]["resolved_hard_fails"] == 1
    assert output_json["summary"]["new_hard_fails"] == 0
    assert "slices_a" in output_json
    assert "slices_b" in output_json


def test_compare_runs_stdout_contains_header(tmp_path):
    run_dir_a = _make_run_dir(tmp_path, "run_a", _TASKS_A)
    run_dir_b = _make_run_dir(tmp_path, "run_b", _TASKS_B)

    runner = CliRunner()
    result = runner.invoke(app, ["compare", "runs", str(run_dir_a), str(run_dir_b)])
    assert result.exit_code == 0
    assert "Baseline" in result.output
    assert "Compare" in result.output
    assert "Mean score" in result.output
    assert "Hard-fail count" in result.output


def test_compare_runs_label_override(tmp_path):
    run_dir_a = _make_run_dir(tmp_path, "run_a", _TASKS_A)
    run_dir_b = _make_run_dir(tmp_path, "run_b", _TASKS_B)
    out = tmp_path / "diff.json"

    runner = CliRunner()
    result = runner.invoke(app, [
        "compare", "runs", str(run_dir_a), str(run_dir_b),
        "--label-a", "GPT-4o", "--label-b", "Claude-Sonnet-4.6",
        "--output", str(out),
    ])
    assert result.exit_code == 0
    assert "GPT-4o" in result.output
    assert "Claude-Sonnet-4.6" in result.output

    data = json.loads(out.read_text())
    assert data["run_a"] == "GPT-4o"
    assert data["run_b"] == "Claude-Sonnet-4.6"


def test_compare_runs_qcat_filter(tmp_path):
    tasks_a = _TASKS_A + [{"task_id": "PERF_ADM_001", "role": "sysadmin", "score": 0.9}]
    tasks_b = _TASKS_B + [{"task_id": "PERF_ADM_001", "role": "sysadmin", "score": 0.5}]
    run_dir_a = _make_run_dir(tmp_path, "run_a", tasks_a)
    run_dir_b = _make_run_dir(tmp_path, "run_b", tasks_b)
    out = tmp_path / "diff.json"

    runner = CliRunner()
    result = runner.invoke(app, [
        "compare", "runs", str(run_dir_a), str(run_dir_b),
        "--qcat", "JOB", "--output", str(out),
    ])
    assert result.exit_code == 0

    data = json.loads(out.read_text())
    assert data["filter_qcat"] == "JOB"
    assert data["task_count_a"] == 5
    assert data["task_count_b"] == 5
    # PERF task should not be in results
    task_ids = [t["task_id"] for t in data["tasks"]]
    assert "PERF_ADM_001" not in task_ids


def test_compare_runs_show_dims(tmp_path):
    run_dir_a = _make_run_dir(tmp_path, "run_a", _TASKS_A)
    run_dir_b = _make_run_dir(tmp_path, "run_b", _TASKS_B)

    runner = CliRunner()
    result = runner.invoke(app, ["compare", "runs", str(run_dir_a), str(run_dir_b), "--show-dims"])
    assert result.exit_code == 0
    assert "Per-dimension deltas" in result.output
    assert "outcome" in result.output


def test_compare_runs_show_slices(tmp_path):
    run_dir_a = _make_run_dir(tmp_path, "run_a", _TASKS_A)
    run_dir_b = _make_run_dir(tmp_path, "run_b", _TASKS_B)

    runner = CliRunner()
    result = runner.invoke(app, ["compare", "runs", str(run_dir_a), str(run_dir_b), "--show-slices"])
    assert result.exit_code == 0
    assert "Role × QCAT" in result.output
