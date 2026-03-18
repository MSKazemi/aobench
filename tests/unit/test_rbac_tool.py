"""Unit tests for MockRBACTool."""

from __future__ import annotations

from pathlib import Path

from exabench.tools.rbac_tool import MockRBACTool

ENV_ROOT = str(Path(__file__).parent.parent / "data" / "environments" / "test_env_01")


def test_sysadmin_has_wildcard_permission():
    tool = MockRBACTool(ENV_ROOT, role="sysadmin")
    result = tool.call("check", resource="slurm.jobs", action="cancel")
    assert result.success
    assert result.data["allowed"] is True


def test_scientific_user_allowed_read_own():
    tool = MockRBACTool(ENV_ROOT, role="scientific_user")
    result = tool.call("check", resource="slurm.jobs", action="read_own")
    assert result.success
    assert result.data["allowed"] is True


def test_scientific_user_not_allowed_cancel():
    tool = MockRBACTool(ENV_ROOT, role="scientific_user")
    result = tool.call("check", resource="slurm.jobs", action="cancel")
    assert result.success
    assert result.data["allowed"] is False


def test_list_permissions_returns_data():
    tool = MockRBACTool(ENV_ROOT, role="sysadmin")
    result = tool.call("list_permissions")
    assert result.success


def test_unknown_method_returns_error():
    tool = MockRBACTool(ENV_ROOT, role="sysadmin")
    result = tool.call("invalid_method")
    assert not result.success
