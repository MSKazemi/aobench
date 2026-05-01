"""Tests for snapshot replay determinism (hpc_snapshot_schema_spec §11)."""

from __future__ import annotations

import csv
import json
import tempfile
from pathlib import Path

from exabench.environment.replay_determinism import (
    ReplayDeterminismReport,
    validate_telemetry_cadence,
    verify_replay_determinism,
)


def _write_csv(path: Path, timestamps: list[float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "value"])
        for ts in timestamps:
            writer.writerow([ts, 1.0])


# ---- verify_replay_determinism tests ----

def test_first_run_mode_always_passes():
    """First-run (no fixture_hashes): always passes, records hashes."""
    with tempfile.TemporaryDirectory() as tmp:
        env_dir = Path(tmp)
        # Write one canonical file
        slurm_dir = env_dir / "slurm"
        slurm_dir.mkdir()
        (slurm_dir / "slurm_state.json").write_text('{"cluster":"test","snapshot_time":"2026-01-01T00:00:00","nodes":[],"partitions":[],"jobs":[]}')

        report = verify_replay_determinism(env_dir, fixture_hashes=None)
        assert report.passed is True
        slurm_entry = next(r for r in report.hash_results if r["file"] == "slurm/slurm_state.json")
        assert slurm_entry["status"] == "recorded"
        assert slurm_entry["actual"] is not None


def test_matching_hashes_pass():
    """When fixture hashes match actual files, report passes."""
    with tempfile.TemporaryDirectory() as tmp:
        env_dir = Path(tmp)
        slurm_dir = env_dir / "slurm"
        slurm_dir.mkdir()
        content = b'{"cluster":"test","snapshot_time":"2026-01-01T00:00:00","nodes":[],"partitions":[],"jobs":[]}'
        (slurm_dir / "slurm_state.json").write_bytes(content)

        import hashlib
        expected_hash = hashlib.sha256(content).hexdigest()
        fixture_hashes = {"slurm/slurm_state.json": expected_hash}

        report = verify_replay_determinism(env_dir, fixture_hashes=fixture_hashes)
        assert report.passed is True
        slurm_entry = next(r for r in report.hash_results if r["file"] == "slurm/slurm_state.json")
        assert slurm_entry["status"] == "ok"


def test_mismatched_hash_fails():
    """When fixture hash differs from actual, report fails."""
    with tempfile.TemporaryDirectory() as tmp:
        env_dir = Path(tmp)
        slurm_dir = env_dir / "slurm"
        slurm_dir.mkdir()
        (slurm_dir / "slurm_state.json").write_text('{"cluster":"modified"}')

        fixture_hashes = {"slurm/slurm_state.json": "deadbeef" * 8}

        report = verify_replay_determinism(env_dir, fixture_hashes=fixture_hashes)
        assert report.passed is False
        slurm_entry = next(r for r in report.hash_results if r["file"] == "slurm/slurm_state.json")
        assert slurm_entry["status"] == "mismatch"


def test_missing_canonical_file_is_skipped():
    """A missing canonical file is recorded as 'missing' but does not fail."""
    with tempfile.TemporaryDirectory() as tmp:
        env_dir = Path(tmp)
        report = verify_replay_determinism(env_dir, fixture_hashes={})
        assert report.passed is True
        missing_entries = [r for r in report.hash_results if r["status"] == "missing"]
        assert len(missing_entries) > 0


def test_report_to_dict():
    """to_dict() returns a serialisable dict."""
    with tempfile.TemporaryDirectory() as tmp:
        env_dir = Path(tmp)
        report = verify_replay_determinism(env_dir)
        d = report.to_dict()
        assert "env_id" in d
        assert "passed" in d
        assert "hash_results" in d
        assert "cadence_results" in d


# ---- validate_telemetry_cadence tests ----

def test_no_telemetry_dir_returns_empty():
    with tempfile.TemporaryDirectory() as tmp:
        env_dir = Path(tmp)
        results = validate_telemetry_cadence(env_dir)
        assert results == []


def test_power_cadence_within_tolerance_passes():
    """Power CSV with ~60s gaps should pass F5."""
    with tempfile.TemporaryDirectory() as tmp:
        env_dir = Path(tmp)
        timestamps = [float(i * 60) for i in range(20)]  # exactly 60s gaps
        _write_csv(env_dir / "telemetry" / "power_timeseries.csv", timestamps)

        results = validate_telemetry_cadence(env_dir)
        assert len(results) == 1
        assert results[0].passed is True
        assert results[0].stream == "power"


def test_power_cadence_too_fast_fails():
    """Power CSV with 10s gaps (far below 60s ±20%) should fail."""
    with tempfile.TemporaryDirectory() as tmp:
        env_dir = Path(tmp)
        timestamps = [float(i * 10) for i in range(20)]  # 10s gaps
        _write_csv(env_dir / "telemetry" / "power_timeseries.csv", timestamps)

        results = validate_telemetry_cadence(env_dir)
        assert len(results) == 1
        assert results[0].passed is False


def test_energy_cadence_within_300s_passes():
    """Energy CSV with ~300s gaps passes."""
    with tempfile.TemporaryDirectory() as tmp:
        env_dir = Path(tmp)
        timestamps = [float(i * 300) for i in range(15)]
        _write_csv(env_dir / "telemetry" / "energy_timeseries.csv", timestamps)

        results = validate_telemetry_cadence(env_dir)
        assert len(results) == 1
        assert results[0].passed is True
        assert results[0].stream == "energy"


def test_too_few_rows_skips():
    """CSV with < 10 rows is skipped (passes)."""
    with tempfile.TemporaryDirectory() as tmp:
        env_dir = Path(tmp)
        timestamps = [float(i * 60) for i in range(5)]  # only 5 rows
        _write_csv(env_dir / "telemetry" / "power_timeseries.csv", timestamps)

        results = validate_telemetry_cadence(env_dir)
        assert len(results) == 1
        assert results[0].passed is True
        assert "skipped" in results[0].message
