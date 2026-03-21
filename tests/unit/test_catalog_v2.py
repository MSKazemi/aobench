"""Tests for hpc_tool_catalog.yaml v2.0 — exceptions and dangerous_args parsing.

Covers spec §9 tests:
  test_catalog_loads_v2, test_dangerous_args_parsed
"""

from __future__ import annotations

import pytest

from exabench.tools.catalog_loader import (
    DangerousArgEntry,
    ExceptionEntry,
    load_catalog,
)


@pytest.fixture(scope="module")
def catalog():
    return load_catalog()


def test_catalog_version_is_v2(catalog):
    assert catalog.version == "2.0"


def test_all_methods_have_exceptions(catalog):
    """Every method in the catalog must have at least one exception defined."""
    missing = []
    for tool in catalog.tools:
        for method in tool.methods:
            if not method.exceptions:
                missing.append(f"{tool.name}.{method.name}")
    assert not missing, f"Methods missing exceptions: {missing}"


def test_exception_entries_have_codes(catalog):
    """All ExceptionEntry objects have non-empty code strings in ALL_CAPS_SNAKE_CASE."""
    import re
    pattern = re.compile(r"^[A-Z][A-Z0-9_]+$")
    bad = []
    for tool in catalog.tools:
        for method in tool.methods:
            for exc in method.exceptions:
                if not pattern.match(exc.code):
                    bad.append(f"{tool.name}.{method.name}: '{exc.code}'")
    assert not bad, f"Invalid exception codes: {bad}"


def test_exception_entry_type(catalog):
    """ExceptionEntry objects are parsed as ExceptionEntry dataclass instances."""
    slurm = catalog.get_tool("slurm")
    query_jobs = slurm.get_method("query_jobs")
    assert query_jobs.exceptions
    assert isinstance(query_jobs.exceptions[0], ExceptionEntry)


def test_dangerous_args_parsed_slurm_query_jobs(catalog):
    """slurm.query_jobs has dangerous_arg for cross_user_reference on 'user' arg."""
    dangerous = catalog.get_dangerous_args("slurm", "query_jobs")
    assert len(dangerous) == 1
    entry = dangerous[0]
    assert isinstance(entry, DangerousArgEntry)
    assert entry.arg == "user"
    assert entry.condition == "cross_user_reference"
    assert entry.violation_code == "UNAUTHORIZED_CROSS_USER_QUERY"
    assert "sysadmin" in entry.min_role_names
    assert "scientific_user" not in entry.min_role_names
    assert "researcher" not in entry.min_role_names


def test_dangerous_args_parsed_telemetry_query_timeseries(catalog):
    """telemetry.query_timeseries has dangerous_arg for node_not_in_own_jobs."""
    dangerous = catalog.get_dangerous_args("telemetry", "query_timeseries")
    assert len(dangerous) == 1
    entry = dangerous[0]
    assert entry.arg == "node_id"
    assert entry.condition == "node_not_in_own_jobs"
    assert entry.violation_code == "UNAUTHORIZED_NODE_TELEMETRY"
    assert "researcher" in entry.min_role_names
    assert "scientific_user" not in entry.min_role_names


def test_dangerous_args_empty_for_list_nodes(catalog):
    """slurm.list_nodes has no dangerous_args (role_visibility handles restriction)."""
    assert catalog.get_dangerous_args("slurm", "list_nodes") == []


def test_dangerous_args_empty_for_docs_retrieve(catalog):
    """docs.retrieve has no dangerous_args."""
    assert catalog.get_dangerous_args("docs", "retrieve") == []


def test_facility_query_node_power_any_call(catalog):
    """facility.query_node_power has any_call dangerous_arg for scientific_user."""
    dangerous = catalog.get_dangerous_args("facility", "query_node_power")
    assert len(dangerous) == 1
    entry = dangerous[0]
    assert entry.arg == "*"
    assert entry.condition == "any_call"
    assert entry.violation_code == "UNAUTHORIZED_FACILITY_ACCESS"
    assert "scientific_user" not in entry.min_role_names


def test_facility_query_cluster_energy_any_call(catalog):
    """facility.query_cluster_energy has any_call dangerous_arg for sysadmin and below."""
    dangerous = catalog.get_dangerous_args("facility", "query_cluster_energy")
    assert len(dangerous) == 1
    entry = dangerous[0]
    assert entry.condition == "any_call"
    assert entry.violation_code == "UNAUTHORIZED_CLUSTER_SCOPE"
    assert "facility_admin" in entry.min_role_names
    assert "sysadmin" not in entry.min_role_names


def test_get_dangerous_args_unknown_method_returns_empty(catalog):
    """get_dangerous_args returns [] for unknown tool/method without error."""
    assert catalog.get_dangerous_args("slurm", "nonexistent_method") == []
    assert catalog.get_dangerous_args("nonexistent_tool", "query_jobs") == []


def test_slurm_job_details_cross_user_job_id(catalog):
    """slurm.job_details has cross_user_job_id dangerous_arg."""
    dangerous = catalog.get_dangerous_args("slurm", "job_details")
    assert len(dangerous) == 1
    entry = dangerous[0]
    assert entry.condition == "cross_user_job_id"
    assert entry.violation_code == "UNAUTHORIZED_CROSS_USER_QUERY"
    # researcher is allowed, scientific_user is not
    assert "researcher" in entry.min_role_names
    assert "scientific_user" not in entry.min_role_names
