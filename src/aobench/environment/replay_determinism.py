"""HPC snapshot replay determinism helpers (hpc_snapshot_schema_spec §11).

Provides verify_replay_determinism() which hashes 5 canonical dispatch
responses from a snapshot bundle against stored fixtures, and
TelemetryCadenceValidator which checks sampling-cadence contracts.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml


# ---------------------------------------------------------------------------
# Telemetry cadence validator
# ---------------------------------------------------------------------------

# Expected cadences in seconds (§11)
_CADENCE_RULES: dict[str, dict[str, float]] = {
    "power":      {"expected_s": 60.0,  "tolerance": 0.20},
    "job_state":  {"expected_s": 300.0, "tolerance": 0.20},
    "energy":     {"expected_s": 300.0, "tolerance": 0.20},
    "node_event": {"expected_s": 0.0,   "tolerance": 0.0},   # event-driven, not checked
}


@dataclass
class CadenceCheckResult:
    stream: str          # e.g. "power", "job_state"
    passed: bool
    median_gap_s: Optional[float]
    expected_s: float
    message: str


def _parse_timestamps(csv_path: Path) -> list[float]:
    """Extract sorted Unix timestamps (float) from a CSV file's timestamp column."""
    import csv as csv_mod
    from datetime import datetime

    timestamps: list[float] = []
    with csv_path.open(newline="") as f:
        reader = csv_mod.DictReader(f)
        if reader.fieldnames is None or "timestamp" not in reader.fieldnames:
            return []
        for row in reader:
            ts_str = row.get("timestamp", "").strip()
            if not ts_str:
                continue
            try:
                # Try Unix float first
                timestamps.append(float(ts_str))
            except ValueError:
                try:
                    dt = datetime.fromisoformat(ts_str.rstrip("Z"))
                    timestamps.append(dt.timestamp())
                except ValueError:
                    pass
    return sorted(timestamps)


def validate_telemetry_cadence(env_dir: Path) -> list[CadenceCheckResult]:
    """Check telemetry CSV cadence contracts for an environment snapshot.

    Returns one CadenceCheckResult per relevant CSV found.
    """
    telemetry_dir = env_dir / "telemetry"
    if not telemetry_dir.exists():
        return []

    results: list[CadenceCheckResult] = []
    for csv_file in sorted(telemetry_dir.glob("*.csv")):
        name = csv_file.stem.lower()
        # Determine which cadence rule applies
        if "power" in name or "watt" in name:
            stream = "power"
        elif "energy" in name or "kwh" in name:
            stream = "energy"
        elif any(k in name for k in ("state", "job", "queue", "sched", "slurm")):
            stream = "job_state"
        else:
            # Unknown cadence — skip rather than misclassify
            continue

        rule = _CADENCE_RULES.get(stream, _CADENCE_RULES["power"])
        if rule["expected_s"] == 0.0:
            continue  # event-driven, skip

        timestamps = _parse_timestamps(csv_file)
        if len(timestamps) < 10:
            results.append(CadenceCheckResult(
                stream=stream,
                passed=True,
                median_gap_s=None,
                expected_s=rule["expected_s"],
                message=f"skipped: only {len(timestamps)} rows in {csv_file.name}",
            ))
            continue

        gaps = [timestamps[i + 1] - timestamps[i] for i in range(len(timestamps) - 1)]
        gaps = [g for g in gaps if g > 0]
        if not gaps:
            results.append(CadenceCheckResult(
                stream=stream,
                passed=True,
                median_gap_s=None,
                expected_s=rule["expected_s"],
                message=f"skipped: all gaps are zero in {csv_file.name}",
            ))
            continue

        gaps_sorted = sorted(gaps)
        mid = len(gaps_sorted) // 2
        median_gap = gaps_sorted[mid] if len(gaps_sorted) % 2 else (
            (gaps_sorted[mid - 1] + gaps_sorted[mid]) / 2
        )

        expected = rule["expected_s"]
        tol = rule["tolerance"]
        lo = expected * (1 - tol)
        hi = expected * (1 + tol)
        passed = lo <= median_gap <= hi

        results.append(CadenceCheckResult(
            stream=stream,
            passed=passed,
            median_gap_s=round(median_gap, 2),
            expected_s=expected,
            message=(
                f"{csv_file.name}: median gap {median_gap:.1f}s, "
                f"expected {expected:.0f}s ±{tol*100:.0f}% [{lo:.0f}–{hi:.0f}]"
            ),
        ))

    return results


# ---------------------------------------------------------------------------
# Replay determinism
# ---------------------------------------------------------------------------

@dataclass
class ReplayDeterminismReport:
    env_id: str
    passed: bool
    hash_results: list[dict[str, Any]] = field(default_factory=list)
    cadence_results: list[CadenceCheckResult] = field(default_factory=list)
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "env_id": self.env_id,
            "passed": self.passed,
            "message": self.message,
            "hash_results": self.hash_results,
            "cadence_results": [
                {
                    "stream": r.stream,
                    "passed": r.passed,
                    "median_gap_s": r.median_gap_s,
                    "expected_s": r.expected_s,
                    "message": r.message,
                }
                for r in self.cadence_results
            ],
        }


def _hash_file(path: Path) -> str:
    """SHA-256 of file bytes (hex)."""
    h = hashlib.sha256(path.read_bytes())
    return h.hexdigest()


def _hash_json_canonical(obj: Any) -> str:
    """SHA-256 of canonically serialised JSON (sorted keys, compact)."""
    blob = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()


# Default canonical fixture files — 5 dispatch responses §11
_CANONICAL_FILES = [
    "slurm/slurm_state.json",
    "telemetry/power_timeseries.csv",
    "policy/rbac_policy.yaml",
    "incidents/incident_metadata.json",
    "docs/tool_catalog.yaml",
]


def verify_replay_determinism(
    env_dir: Path,
    fixture_hashes: Optional[dict[str, str]] = None,
) -> ReplayDeterminismReport:
    """Verify that snapshot files match canonical fixture hashes.

    Args:
        env_dir:        Path to the environment snapshot directory.
        fixture_hashes: Mapping of relative path → expected SHA-256 hex.
                        If None, hashes are computed fresh (first-run mode: always passes).

    Returns:
        ReplayDeterminismReport with per-file hash comparison results.
    """
    env_id = env_dir.name
    hash_results: list[dict[str, Any]] = []
    all_passed = True

    for rel in _CANONICAL_FILES:
        file_path = env_dir / rel
        if not file_path.exists():
            hash_results.append({
                "file": rel,
                "status": "missing",
                "actual": None,
                "expected": (fixture_hashes or {}).get(rel),
                "passed": True,  # missing files are skipped, not failed
            })
            continue

        actual_hash = _hash_file(file_path)

        if fixture_hashes is None:
            # First-run mode: record hashes without comparing
            hash_results.append({
                "file": rel,
                "status": "recorded",
                "actual": actual_hash,
                "expected": None,
                "passed": True,
            })
        else:
            expected = fixture_hashes.get(rel)
            if expected is None:
                status = "no_fixture"
                passed = True
            else:
                passed = actual_hash == expected
                status = "ok" if passed else "mismatch"
                if not passed:
                    all_passed = False

            hash_results.append({
                "file": rel,
                "status": status,
                "actual": actual_hash,
                "expected": expected,
                "passed": passed,
            })

    # Telemetry cadence checks
    # In first-run mode (fixture_hashes=None), cadence issues are warnings only.
    cadence_results = validate_telemetry_cadence(env_dir)
    if fixture_hashes is not None and any(not r.passed for r in cadence_results):
        all_passed = False

    return ReplayDeterminismReport(
        env_id=env_id,
        passed=all_passed,
        hash_results=hash_results,
        cadence_results=cadence_results,
        message="ok" if all_passed else "one or more checks failed",
    )
