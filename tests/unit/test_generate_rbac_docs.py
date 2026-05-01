"""Tests for scripts/generate_rbac_docs.py."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
import generate_rbac_docs as grd


MINIMAL_POLICY = {
    "version": "1.1",
    "hard_fail_on_violation": True,
    "roles": {
        "scientific_user": {
            "description": "HPC user",
            "permissions": [
                {"resource": "slurm.jobs", "actions": ["read_own"], "constraint": "user == requester"},
                {"resource": "docs", "actions": ["read"]},
            ],
            "allowed_tools": ["slurm", "docs"],
            "partition_access": [
                {"name": "cpu", "max_walltime": "48:00:00"},
            ],
        },
        "sysadmin": {
            "description": "System admin",
            "permissions": [
                {"resource": "slurm.jobs", "actions": ["read", "modify", "cancel"]},
            ],
            "allowed_tools": ["slurm", "rbac"],
            "partition_access": [{"name": "*", "max_walltime": "168:00:00"}],
        },
    },
    "access_tiers": {
        "tier1_public": {"resources": ["slurm.partitions", "docs"], "roles": ["*"]},
        "tier2_privileged": {
            "resources": ["slurm.jobs"],
            "roles": ["sysadmin"],
            "request_required_for": ["scientific_user"],
            "approval_sla_days": 2,
            "grant_duration_days": 90,
        },
    },
}


def test_render_contains_env_id() -> None:
    md = grd.render_rbac_markdown("env_42", MINIMAL_POLICY)
    assert "env_42" in md


def test_render_contains_version() -> None:
    md = grd.render_rbac_markdown("env_01", MINIMAL_POLICY)
    assert "1.1" in md


def test_render_contains_hard_fail() -> None:
    md = grd.render_rbac_markdown("env_01", MINIMAL_POLICY)
    assert "true" in md.lower()


def test_render_contains_role_names() -> None:
    md = grd.render_rbac_markdown("env_01", MINIMAL_POLICY)
    assert "scientific_user" in md
    assert "sysadmin" in md


def test_render_contains_permission_table() -> None:
    md = grd.render_rbac_markdown("env_01", MINIMAL_POLICY)
    assert "| Resource |" in md
    assert "slurm.jobs" in md
    assert "read_own" in md


def test_render_contains_access_tier_table() -> None:
    md = grd.render_rbac_markdown("env_01", MINIMAL_POLICY)
    assert "## Access Tiers" in md
    assert "tier1_public" in md
    assert "tier2_privileged" in md
    assert "approval SLA 2d" in md


def test_generate_for_env_writes_file(tmp_path: Path) -> None:
    env_dir = tmp_path / "env_test"
    policy_dir = env_dir / "policy"
    policy_dir.mkdir(parents=True)
    (policy_dir / "rbac_policy.yaml").write_text(
        yaml.dump(MINIMAL_POLICY), encoding="utf-8"
    )

    result = grd.generate_for_env(env_dir, dry_run=False)

    assert result is True
    out = env_dir / "docs" / "rbac_policy.md"
    assert out.exists()
    content = out.read_text()
    assert "env_test" in content
    assert "scientific_user" in content


def test_generate_for_env_dry_run_no_write(tmp_path: Path) -> None:
    env_dir = tmp_path / "env_dry"
    policy_dir = env_dir / "policy"
    policy_dir.mkdir(parents=True)
    (policy_dir / "rbac_policy.yaml").write_text(
        yaml.dump(MINIMAL_POLICY), encoding="utf-8"
    )

    result = grd.generate_for_env(env_dir, dry_run=True)

    assert result is True
    assert not (env_dir / "docs" / "rbac_policy.md").exists()


def test_generate_for_env_skip_missing_yaml(tmp_path: Path) -> None:
    env_dir = tmp_path / "env_noyaml"
    env_dir.mkdir()
    result = grd.generate_for_env(env_dir, dry_run=False)
    assert result is False


def test_main_generates_all(tmp_path: Path) -> None:
    for i in range(1, 4):
        env_dir = tmp_path / f"env_{i:02d}"
        (env_dir / "policy").mkdir(parents=True)
        (env_dir / "policy" / "rbac_policy.yaml").write_text(
            yaml.dump(MINIMAL_POLICY), encoding="utf-8"
        )

    exit_code = grd.main(["--env-base", str(tmp_path)])
    assert exit_code == 0

    for i in range(1, 4):
        md = tmp_path / f"env_{i:02d}" / "docs" / "rbac_policy.md"
        assert md.exists(), f"Missing {md}"
