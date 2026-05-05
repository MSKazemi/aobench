"""Unit tests for MockFacilityTool."""

from __future__ import annotations

from pathlib import Path

from aobench.tools.facility_tool import MockFacilityTool

ENV_ROOT = str(Path(__file__).parent.parent.parent / "benchmark" / "environments" / "env_03")


def test_query_node_power_returns_records():
    tool = MockFacilityTool(ENV_ROOT, role="facility_admin")
    result = tool.call("query_node_power")
    assert result.success
    assert isinstance(result.data, list)
    assert len(result.data) > 0
    # Each record should have a 'node' and 'power_kw' column
    assert "node" in result.data[0]


def test_query_node_power_filter():
    tool = MockFacilityTool(ENV_ROOT, role="facility_admin")
    # Get all nodes first
    all_result = tool.call("query_node_power")
    if not all_result.data:
        return
    first_node = all_result.data[0]["node"]
    filtered = tool.call("query_node_power", node=first_node)
    assert filtered.success
    for rec in filtered.data:
        assert rec["node"] == first_node


def test_query_rack_telemetry_returns_records():
    tool = MockFacilityTool(ENV_ROOT, role="facility_admin")
    result = tool.call("query_rack_telemetry")
    assert result.success
    assert isinstance(result.data, list)
    assert len(result.data) > 0


def test_list_inventory_nodes():
    tool = MockFacilityTool(ENV_ROOT, role="facility_admin")
    result = tool.call("list_inventory", kind="nodes")
    assert result.success
    assert isinstance(result.data, list)


def test_list_inventory_racks():
    tool = MockFacilityTool(ENV_ROOT, role="facility_admin")
    result = tool.call("list_inventory", kind="racks")
    assert result.success
    assert isinstance(result.data, list)


def test_query_cluster_energy_returns_records():
    tool = MockFacilityTool(ENV_ROOT, role="facility_admin")
    result = tool.call("query_cluster_energy")
    assert result.success
    assert isinstance(result.data, list)
    assert len(result.data) > 0


def test_unknown_method_returns_error():
    tool = MockFacilityTool(ENV_ROOT, role="facility_admin")
    result = tool.call("nonexistent")
    assert not result.success
    assert result.error is not None


def test_no_power_dir_returns_error(tmp_path):
    tool = MockFacilityTool(str(tmp_path), role="facility_admin")
    result = tool.call("query_node_power")
    assert not result.success
