"""Unit tests: extended SlurmJob (M100 fields) stays backward-compatible."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aobench.schemas.snapshot import SlurmJob, SlurmState

_ENVS = Path(__file__).resolve().parents[2] / "benchmark" / "environments"


def test_m100_job_fields_validate():
    job = SlurmJob.model_validate({
        "job_id": "7421033",
        "user": "5012",
        "state": "RUNNING",
        "partition": "m100_usr_prod",
        "qos": "normal",
        "job_state": "RUNNING",
        "derived_ec": "0:0",
        "run_time": 18000,
        "nodes": ["r3n7"],
        "min_memory_node": 262144,
        "state_reason": "None",
    })
    assert job.qos == "normal"
    assert job.nodes == ["r3n7"]
    assert job.run_time == 18000


def test_legacy_job_without_m100_fields_still_valid():
    # Existing bundles never set the new fields — they must default cleanly.
    job = SlurmJob.model_validate({
        "job_id": "891234", "user": "alice", "state": "FAILED", "partition": "standard",
    })
    assert job.qos is None
    assert job.job_state is None
    assert job.nodes is None


@pytest.mark.parametrize("env_dir", sorted(p for p in _ENVS.glob("env_*") if p.is_dir()))
def test_existing_slurm_states_still_validate(env_dir):
    # The schema extension must not break any existing or new bundle.
    slurm_path = env_dir / "slurm" / "slurm_state.json"
    if not slurm_path.exists():
        pytest.skip("no slurm_state.json")
    SlurmState.model_validate(json.loads(slurm_path.read_text(encoding="utf-8")))
