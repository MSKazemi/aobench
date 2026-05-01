"""Tests for scripts/create_task_stubs.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pyarrow.parquet as pq
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
import create_task_stubs as cts


# ---------------------------------------------------------------------------
# create_stub — individual stubs
# ---------------------------------------------------------------------------

def test_stub_json_generic(tmp_path: Path) -> None:
    p = tmp_path / "foo.json"
    cts.create_stub(p)
    assert p.exists()
    data = json.loads(p.read_text())
    assert data["__stub__"] is True


def test_stub_slurm_state(tmp_path: Path) -> None:
    p = tmp_path / "slurm" / "slurm_state.json"
    cts.create_stub(p)
    assert p.exists()
    data = json.loads(p.read_text())
    assert "partitions" in data
    assert isinstance(data["partitions"], list)


def test_stub_job_details(tmp_path: Path) -> None:
    p = tmp_path / "slurm" / "job_details.json"
    cts.create_stub(p)
    assert p.exists()
    data = json.loads(p.read_text())
    assert "jobs" in data
    assert len(data["jobs"]) >= 1
    assert "job_id" in data["jobs"][0]


def test_stub_parquet_generic(tmp_path: Path) -> None:
    p = tmp_path / "telemetry" / "some_metric.parquet"
    cts.create_stub(p)
    assert p.exists()
    table = pq.read_table(str(p))
    assert table.num_rows == 0
    assert "timestamp" in table.schema.names


def test_stub_rbac_audit_log_parquet(tmp_path: Path) -> None:
    p = tmp_path / "rbac" / "audit_log_30d.parquet"
    cts.create_stub(p)
    assert p.exists()
    table = pq.read_table(str(p))
    assert table.num_rows == 0
    assert "user" in table.schema.names
    assert "role" in table.schema.names


def test_stub_thermal_alerts_parquet(tmp_path: Path) -> None:
    p = tmp_path / "telemetry" / "thermal_alerts_90d.parquet"
    cts.create_stub(p)
    assert p.exists()
    table = pq.read_table(str(p))
    assert "node" in table.schema.names
    assert "alert_type" in table.schema.names


def test_stub_csv(tmp_path: Path) -> None:
    p = tmp_path / "power" / "node_power_gpu_24h.csv"
    cts.create_stub(p)
    assert p.exists()
    content = p.read_text()
    assert "timestamp" in content


def test_stub_text(tmp_path: Path) -> None:
    p = tmp_path / "slurm" / "sacct_12345.txt"
    cts.create_stub(p)
    assert p.exists()
    assert p.read_text().strip() != ""


def test_stub_markdown(tmp_path: Path) -> None:
    p = tmp_path / "docs" / "aiops_thresholds.md"
    cts.create_stub(p)
    assert p.exists()
    content = p.read_text()
    assert content.startswith("#")


def test_dry_run_no_write(tmp_path: Path) -> None:
    p = tmp_path / "slurm" / "job_details.json"
    cts.create_stub(p, dry_run=True)
    assert not p.exists()


# ---------------------------------------------------------------------------
# run() integration — minimal task/env fixtures
# ---------------------------------------------------------------------------

def _write_task(task_dir: Path, task_id: str, env_id: str, refs: list[str]) -> None:
    spec = {
        "task_id": task_id,
        "title": "Stub test task",
        "query_text": "Why?",
        "role": "scientific_user",
        "qcat": "JOB",
        "difficulty": "easy",
        "environment_id": env_id,
        "expected_answer_type": "diagnosis",
        "eval_criteria": {"gold_answer": "answer"},
        "allowed_tools": ["slurm"],
        "gold_evidence_refs": refs,
    }
    (task_dir / f"{task_id}.json").write_text(json.dumps(spec))


def test_run_creates_missing_stubs(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks"
    task_dir.mkdir()
    env_dir = tmp_path / "environments"
    env_dir.mkdir()
    (env_dir / "env_t1").mkdir()

    _write_task(task_dir, "TEST_001", "env_t1", [
        "slurm/job_details.json",
        "telemetry/power.parquet",
    ])

    exit_code = cts.run(task_dir, env_dir, dry_run=False)
    assert exit_code == 0
    assert (env_dir / "env_t1" / "slurm" / "job_details.json").exists()
    assert (env_dir / "env_t1" / "telemetry" / "power.parquet").exists()


def test_run_skips_existing_files(tmp_path: Path) -> None:
    task_dir = tmp_path / "tasks"
    task_dir.mkdir()
    env_dir = tmp_path / "environments"
    (env_dir / "env_t2" / "slurm").mkdir(parents=True)
    existing = env_dir / "env_t2" / "slurm" / "job_details.json"
    existing.write_text('{"real": true}')

    _write_task(task_dir, "TEST_002", "env_t2", ["slurm/job_details.json"])

    cts.run(task_dir, env_dir, dry_run=False)
    # File should remain unchanged
    assert json.loads(existing.read_text())["real"] is True
