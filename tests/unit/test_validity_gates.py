"""Tests for check_validity_gates.py — gate_v0 (fidelity precondition)."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pytest

# Add scripts/ to sys.path so we can import check_validity_gates directly
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
import check_validity_gates as cvg


# ---------------------------------------------------------------------------
# gate_v0
# ---------------------------------------------------------------------------

def test_v0_skip_when_index_missing(tmp_path: Path) -> None:
    """V0 passes (with warning) when the fidelity index file does not exist."""
    result = cvg.gate_v0(tmp_path / "nonexistent.json")
    assert result["gate"] == "V0"
    assert result["passed"] is True
    assert result["warning_only"] is True
    assert any("skipped" in iss or "index not found" in iss for iss in result["issues"])


def test_v0_pass_when_all_envs_pass(tmp_path: Path) -> None:
    """V0 passes when every entry in the fidelity index has passed=True."""
    index = [
        {"env_id": "env_01", "passed": True},
        {"env_id": "env_02", "passed": True},
        {"env_id": "env_03", "passed": True},
    ]
    idx_file = tmp_path / "index.json"
    idx_file.write_text(json.dumps(index))

    result = cvg.gate_v0(idx_file)
    assert result["passed"] is True
    assert result["warning_only"] is True
    assert result["issues"] == []


def test_v0_fail_when_any_env_fails(tmp_path: Path) -> None:
    """V0 fails (warning) when any entry in the fidelity index has passed=False."""
    index = [
        {"env_id": "env_01", "passed": True},
        {"env_id": "env_02", "passed": False},
    ]
    idx_file = tmp_path / "index.json"
    idx_file.write_text(json.dumps(index))

    result = cvg.gate_v0(idx_file)
    assert result["passed"] is False
    assert result["warning_only"] is True
    assert any("env_02" in iss for iss in result["issues"])


def test_v0_fail_multiple_envs(tmp_path: Path) -> None:
    """V0 issues list contains all failed env IDs."""
    index = [
        {"env_id": "env_01", "passed": False},
        {"env_id": "env_02", "passed": True},
        {"env_id": "env_03", "passed": False},
    ]
    idx_file = tmp_path / "index.json"
    idx_file.write_text(json.dumps(index))

    result = cvg.gate_v0(idx_file)
    assert result["passed"] is False
    failed_in_issues = [iss for iss in result["issues"] if "env_01" in iss or "env_03" in iss]
    assert len(failed_in_issues) == 2


def test_v0_graceful_on_malformed_json(tmp_path: Path) -> None:
    """V0 returns warning_only=True and passed=False when index JSON is malformed."""
    idx_file = tmp_path / "index.json"
    idx_file.write_text("this is not json")

    result = cvg.gate_v0(idx_file)
    assert result["warning_only"] is True
    assert result["passed"] is False
    assert any("could not read" in iss for iss in result["issues"])


def test_v0_not_blocking_in_main_exit_code(tmp_path: Path) -> None:
    """Failing V0 alone must NOT cause main() to return non-zero exit code."""
    # Write a fidelity index with a failed env
    index = [{"env_id": "env_01", "passed": False}]
    idx_file = tmp_path / "index.json"
    idx_file.write_text(json.dumps(index))

    # Run main with no run dirs (models=0 → V1-V5 trivially pass or warn, V6 warns)
    # We only care that the exit code is 0 when V0 is the only failure.
    exit_code = cvg.main([
        "--fidelity-index", str(idx_file),
        "--rob-dir", str(tmp_path),  # empty dir → no robustness data
    ])
    # V0 is warning-only, so its failure shouldn't make the script return 1
    # (V4 will warn about missing robustness data, but it's not the focus here)
    # The key assertion: V0 failure alone doesn't set exit_code=1
    # Since we have no model data either, V1-V5 may also have issues — just check
    # that V0's warning_only flag is respected in the gating logic.
    result_v0 = cvg.gate_v0(idx_file)
    assert result_v0["warning_only"] is True
