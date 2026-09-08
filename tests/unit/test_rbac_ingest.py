"""Unit tests for aobench.cli.rbac_cmd — RBAC policy ingestion."""

from __future__ import annotations

import tempfile
from pathlib import Path

import yaml


# ── helpers ───────────────────────────────────────────────────────────────────


def _make_mock_env(env_dir: Path, env_id: str = "env_test") -> None:
    """Create a minimal valid environment bundle for testing."""
    env_dir.mkdir(parents=True, exist_ok=True)

    # metadata.yaml
    metadata = {
        "environment_id": env_id,
        "snapshot_name": "Test snapshot",
        "scenario_type": "job_failure",
        "cluster_name": "test-cluster",
        "snapshot_timestamp": "2026-01-01T00:00:00Z",
        "bundle_root": f"environments/{env_id}",
        "supported_roles": ["scientific_user", "sysadmin"],
        "supported_categories": ["JOB"],
        "included_sources": ["policy"],
        "included_files": ["policy/rbac_policy.yaml"],
        "implementation_status": "bundled",
        "validation_status": "validated",
        "description": "Test environment",
    }
    with (env_dir / "metadata.yaml").open("w", encoding="utf-8") as f:
        yaml.dump(metadata, f)

    # policy/rbac_policy.yaml
    policy_dir = env_dir / "policy"
    policy_dir.mkdir()
    policy = {
        "version": "1.0",
        "roles": {
            "scientific_user": {
                "description": "Test user",
                "permissions": [],
                "allowed_tools": ["slurm"],
            }
        },
    }
    with (policy_dir / "rbac_policy.yaml").open("w", encoding="utf-8") as f:
        yaml.dump(policy, f)

    # manifest.txt
    (env_dir / "manifest.txt").write_text("metadata.yaml\npolicy/rbac_policy.yaml\n")


def _make_customer_policy(path: Path, *, extra_role: str | None = None) -> None:
    policy = {
        "version": "1.1",
        "roles": {
            "scientific_user": {
                "description": "Customer user",
                "permissions": [{"resource": "slurm.jobs", "actions": ["read_own"]}],
                "allowed_tools": ["slurm", "docs"],
            }
        },
    }
    if extra_role:
        policy["roles"][extra_role] = {"description": "Extra role", "permissions": [], "allowed_tools": []}
    with path.open("w", encoding="utf-8") as f:
        yaml.dump(policy, f)


# ── direct function tests ─────────────────────────────────────────────────────


def test_ingest_creates_new_env_directory():
    """rbac ingest creates a new directory cloned from the base env."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        envs_dir = tmpdir / "benchmark" / "environments"
        base_dir = envs_dir / "env_base"
        _make_mock_env(base_dir, "env_base")

        policy_file = tmpdir / "customer.yaml"
        _make_customer_policy(policy_file)

        from typer.testing import CliRunner
        from aobench.cli.rbac_cmd import rbac_app

        runner = CliRunner()
        result = runner.invoke(
            rbac_app,
            [
                "--policy", str(policy_file),
                "--base-env", "env_base",
                "--env-id", "env_rbac_test",
                "--benchmark", str(tmpdir / "benchmark"),
            ],
            catch_exceptions=False,
        )
        # The command may warn about bundle validation (missing snapshot validator)
        # but must still create the directory
        new_env_dir = envs_dir / "env_rbac_test"
        assert new_env_dir.exists(), f"Expected new env dir; got output: {result.output}"


def test_ingest_replaces_rbac_policy():
    """The customer RBAC policy replaces the base env policy."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        envs_dir = tmpdir / "benchmark" / "environments"
        base_dir = envs_dir / "env_base"
        _make_mock_env(base_dir, "env_base")

        policy_file = tmpdir / "customer.yaml"
        _make_customer_policy(policy_file, extra_role="admin")

        from typer.testing import CliRunner
        from aobench.cli.rbac_cmd import rbac_app

        runner = CliRunner()
        runner.invoke(
            rbac_app,
            ["--policy",str(policy_file), "--base-env", "env_base",
             "--env-id", "env_rbac_test2", "--benchmark", str(tmpdir / "benchmark")],
            catch_exceptions=False,
        )
        installed_policy = envs_dir / "env_rbac_test2" / "policy" / "rbac_policy.yaml"
        assert installed_policy.exists()
        loaded = yaml.safe_load(installed_policy.read_text(encoding="utf-8"))
        assert "admin" in loaded["roles"]  # extra_role was carried through


def test_ingest_updates_metadata_env_id():
    """metadata.yaml in the new bundle has the correct environment_id."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        envs_dir = tmpdir / "benchmark" / "environments"
        _make_mock_env(envs_dir / "env_base", "env_base")

        policy_file = tmpdir / "customer.yaml"
        _make_customer_policy(policy_file)

        from typer.testing import CliRunner
        from aobench.cli.rbac_cmd import rbac_app

        runner = CliRunner()
        runner.invoke(
            rbac_app,
            ["--policy",str(policy_file), "--base-env", "env_base",
             "--env-id", "env_rbac_meta_test", "--benchmark", str(tmpdir / "benchmark")],
            catch_exceptions=False,
        )
        metadata = yaml.safe_load(
            (envs_dir / "env_rbac_meta_test" / "metadata.yaml").read_text(encoding="utf-8")
        )
        assert metadata["environment_id"] == "env_rbac_meta_test"
        assert "env_rbac_meta_test" in metadata["bundle_root"]


def test_ingest_missing_policy_file_exits():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        envs_dir = tmpdir / "benchmark" / "environments"
        _make_mock_env(envs_dir / "env_base", "env_base")

        from typer.testing import CliRunner
        from aobench.cli.rbac_cmd import rbac_app

        runner = CliRunner()
        result = runner.invoke(
            rbac_app,
            ["--policy","/nonexistent/policy.yaml",
             "--base-env", "env_base", "--benchmark", str(tmpdir / "benchmark")],
        )
        assert result.exit_code != 0


def test_ingest_missing_base_env_exits():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        (tmpdir / "benchmark" / "environments").mkdir(parents=True)

        policy_file = tmpdir / "customer.yaml"
        _make_customer_policy(policy_file)

        from typer.testing import CliRunner
        from aobench.cli.rbac_cmd import rbac_app

        runner = CliRunner()
        result = runner.invoke(
            rbac_app,
            ["--policy",str(policy_file),
             "--base-env", "env_nonexistent", "--benchmark", str(tmpdir / "benchmark")],
        )
        assert result.exit_code != 0


def test_ingest_duplicate_env_id_exits():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        envs_dir = tmpdir / "benchmark" / "environments"
        _make_mock_env(envs_dir / "env_base", "env_base")
        _make_mock_env(envs_dir / "env_dup", "env_dup")

        policy_file = tmpdir / "customer.yaml"
        _make_customer_policy(policy_file)

        from typer.testing import CliRunner
        from aobench.cli.rbac_cmd import rbac_app

        runner = CliRunner()
        result = runner.invoke(
            rbac_app,
            ["--policy",str(policy_file),
             "--base-env", "env_base", "--env-id", "env_dup",
             "--benchmark", str(tmpdir / "benchmark")],
        )
        assert result.exit_code != 0


def test_ingest_invalid_yaml_exits():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        envs_dir = tmpdir / "benchmark" / "environments"
        _make_mock_env(envs_dir / "env_base", "env_base")

        bad_policy = tmpdir / "bad.yaml"
        bad_policy.write_text(": : invalid yaml {{{{", encoding="utf-8")

        from typer.testing import CliRunner
        from aobench.cli.rbac_cmd import rbac_app

        runner = CliRunner()
        result = runner.invoke(
            rbac_app,
            ["--policy",str(bad_policy),
             "--base-env", "env_base", "--benchmark", str(tmpdir / "benchmark")],
        )
        assert result.exit_code != 0
