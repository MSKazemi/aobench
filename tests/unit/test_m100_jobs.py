"""Unit tests for the real M100 job-pool extractor and its integration."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(_SCRIPTS))

from build_m100_jobs import build_pool, parse_slurm_duration, seconds_to_elapsed  # noqa: E402
from build_m100_bundles import load_real_jobs, real_background_jobs  # noqa: E402
from aobench.schemas.snapshot import SlurmJob  # noqa: E402

_POOL_JSON = (
    Path(__file__).resolve().parents[2]
    / "benchmark" / "environments" / "_m100_reference" / "real_jobs.json"
)


@pytest.mark.parametrize("s,secs", [
    ("1:00:00", 3600), ("1-00:00:00", 86400), ("5:00", 300), ("30:00", 1800),
    ("01:30:05", 5405), ("Unknown", None), (None, None),
])
def test_parse_slurm_duration(s, secs):
    assert parse_slurm_duration(s) == secs


def test_seconds_to_elapsed():
    assert seconds_to_elapsed(5405) == "01:30:05"
    assert seconds_to_elapsed(None) is None


def test_build_pool_dedups_and_maps():
    df = pd.DataFrame([
        # job 1 appears twice: a RUNNING poll then a terminal OUT_OF_MEMORY poll.
        {"job_id": "1", "job_state": "RUNNING", "user_id": 5, "partition": "1", "qos": "1",
         "num_cpus": 4, "num_nodes": 1, "start_time": pd.Timestamp("2022-07-01T10:00:00Z"),
         "end_time": pd.NaT, "last_sched_eval": pd.Timestamp("2022-07-01T10:00:00Z")},
        {"job_id": "1", "job_state": "OUT_OF_MEMORY", "user_id": 5, "partition": "1", "qos": "1",
         "num_cpus": 4, "num_nodes": 1, "start_time": pd.Timestamp("2022-07-01T10:00:00Z"),
         "end_time": pd.Timestamp("2022-07-01T10:30:00Z"),
         "last_sched_eval": pd.Timestamp("2022-07-01T10:30:00Z")},
        {"job_id": "2", "job_state": "COMPLETED", "user_id": 7, "partition": "2", "qos": "3",
         "num_cpus": 32, "num_nodes": 1, "start_time": pd.Timestamp("2022-07-01T09:00:00Z"),
         "end_time": pd.Timestamp("2022-07-01T11:00:00Z"),
         "last_sched_eval": pd.Timestamp("2022-07-01T11:00:00Z")},
    ])
    pool = build_pool(df, seed=1)
    by_id = {j["job_id"]: j for j in pool}
    assert len(pool) == 2                                  # deduped to one record per job
    assert by_id["1"]["job_state"] == "OUT_OF_MEMORY"      # kept the terminal record
    assert by_id["1"]["state"] == "FAILED"                 # canonical mapping
    assert by_id["1"]["elapsed"] == "00:30:00"             # derived from start/end
    assert by_id["2"]["state"] == "COMPLETED"


def test_committed_pool_records_are_valid_slurmjobs():
    """Every real background job must validate against the SlurmJob schema."""
    assert _POOL_JSON.exists(), "run scripts/build_m100_jobs.py on n1 and commit the pool"
    import build_m100_bundles as bb
    bb._REAL_JOBS = load_real_jobs(_POOL_JSON)
    assert len(bb._REAL_JOBS) >= 20
    bg = real_background_jobs(["r0n0", "r0n1", "r0n2", "r0n3"], "2022-07-15T14:00:00Z", 4)
    assert len(bg) == 4
    for j in bg:
        SlurmJob.model_validate(j)                         # real records map to valid jobs
    # Deterministic for a given snap_time.
    bg2 = real_background_jobs(["r0n0", "r0n1", "r0n2", "r0n3"], "2022-07-15T14:00:00Z", 4)
    assert [j["job_id"] for j in bg] == [j["job_id"] for j in bg2]


def test_pool_has_real_failure_states():
    """The real job table carries genuine failure states (incl. OUT_OF_MEMORY)."""
    pool = json.loads(_POOL_JSON.read_text(encoding="utf-8"))
    assert "OUT_OF_MEMORY" in pool["state_counts"]
