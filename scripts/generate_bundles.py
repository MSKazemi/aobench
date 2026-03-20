#!/usr/bin/env python3
"""Generate canonical HPC snapshot bundles env_06 through env_20.

Usage:
    python scripts/generate_bundles.py [--benchmark-root benchmark/]

Each bundle follows the canonical layout:
    benchmark/environments/<env_id>/
        metadata.yaml
        slurm/slurm_state.json
        telemetry/telemetry_timeseries.parquet
        policy/rbac_policy.yaml
        incidents/incident_metadata.json
        docs/<doc>.md
"""

from __future__ import annotations

import argparse
import json
import textwrap
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import yaml

UTC = timezone.utc


def ts(s: str) -> str:
    """Return ISO8601 UTC string (no trailing Z workaround for json)."""
    return s


# ---------------------------------------------------------------------------
# Shared RBAC policies
# ---------------------------------------------------------------------------

RBAC_SYSADMIN_FULL = {
    "version": "1.0",
    "roles": {
        "sysadmin": {
            "description": "HPC system administrator — full read/modify access",
            "permissions": [
                {"resource": "*", "actions": ["*"]},
            ],
        },
        "scientific_user": {
            "description": "Regular user — own jobs only",
            "permissions": [
                {"resource": "slurm.jobs", "actions": ["read_own"], "constraint": "user == requester"},
                {"resource": "slurm.partitions", "actions": ["read"]},
                {"resource": "docs", "actions": ["read"]},
            ],
        },
    },
    "hard_fail_on_violation": True,
}

RBAC_FACILITY = {
    "version": "1.0",
    "roles": {
        "facility_admin": {
            "description": "Facility administrator — full energy and infrastructure access",
            "permissions": [
                {"resource": "*", "actions": ["*"]},
            ],
        },
        "sysadmin": {
            "description": "System administrator",
            "permissions": [
                {"resource": "slurm.*", "actions": ["read", "modify", "cancel"]},
                {"resource": "telemetry.*", "actions": ["read"]},
                {"resource": "docs", "actions": ["read"]},
                {"resource": "incidents", "actions": ["read", "update"]},
            ],
        },
    },
    "hard_fail_on_violation": True,
}

RBAC_RESEARCHER = {
    "version": "1.0",
    "roles": {
        "researcher": {
            "description": "Researcher — own jobs and read-only telemetry",
            "permissions": [
                {"resource": "slurm.jobs", "actions": ["read_own"], "constraint": "user == requester"},
                {"resource": "slurm.partitions", "actions": ["read"]},
                {"resource": "telemetry.*", "actions": ["read"]},
                {"resource": "docs", "actions": ["read"]},
            ],
        },
        "sysadmin": {
            "description": "System administrator — full access",
            "permissions": [
                {"resource": "*", "actions": ["*"]},
            ],
        },
    },
    "hard_fail_on_violation": True,
}

RBAC_SYSTEM_DESIGNER = {
    "version": "1.0",
    "roles": {
        "system_designer": {
            "description": "System designer — full read access for capacity planning",
            "permissions": [
                {"resource": "*", "actions": ["read"]},
            ],
        },
        "facility_admin": {
            "description": "Facility administrator",
            "permissions": [
                {"resource": "*", "actions": ["*"]},
            ],
        },
    },
    "hard_fail_on_violation": True,
}


# ---------------------------------------------------------------------------
# Telemetry helpers
# ---------------------------------------------------------------------------

def make_telemetry(
    nodes: list[str],
    hours: int = 2,
    snapshot_time: datetime | None = None,
    metrics: dict | None = None,
) -> pd.DataFrame:
    """Generate synthetic time-series telemetry parquet data."""
    if snapshot_time is None:
        snapshot_time = datetime(2026, 3, 19, 12, 0, 0, tzinfo=UTC)

    default_metrics = {
        "cpu_util_pct": (60.0, 5.0, "%"),
        "memory_util_pct": (55.0, 3.0, "%"),
        "memory_used_mb": (220000.0, 5000.0, "MB"),
        "power_w": (350.0, 20.0, "W"),
    }
    if metrics:
        default_metrics.update(metrics)

    rows = []
    import random
    rng = random.Random(42)
    step = timedelta(minutes=5)
    start = snapshot_time - timedelta(hours=hours)
    t = start
    while t <= snapshot_time:
        for node in nodes:
            for metric_name, (mean, std, unit) in default_metrics.items():
                value = max(0.0, mean + rng.gauss(0, std))
                rows.append({
                    "timestamp": t,
                    "node_id": node,
                    "metric_name": metric_name,
                    "value": round(value, 2),
                    "unit": unit,
                })
        t += step

    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    return df


# ---------------------------------------------------------------------------
# Bundle definitions
# ---------------------------------------------------------------------------

def build_env_06(root: Path) -> None:
    """energy_anomaly — Power spike on GPU partition."""
    env = root / "env_06"
    snap_time = "2026-03-10T16:00:00Z"
    nodes = ["gpu01", "gpu02", "gpu03", "gpu04"]

    _write_metadata(env, {
        "environment_id": "env_06",
        "snapshot_name": "GPU Power Spike",
        "scenario_type": "energy_anomaly",
        "cluster_name": "exabench-cluster-a",
        "snapshot_timestamp": snap_time,
        "bundle_root": "environments/env_06",
        "supported_roles": ["sysadmin", "facility_admin"],
        "supported_categories": ["ENERGY", "MON"],
        "included_sources": ["slurm", "telemetry", "docs", "rbac", "incidents"],
        "included_files": [
            "slurm/slurm_state.json",
            "telemetry/telemetry_timeseries.parquet",
            "policy/rbac_policy.yaml",
            "incidents/incident_metadata.json",
            "docs/gpu_power_policy.md",
        ],
        "implementation_status": "bundled",
        "validation_status": "validated",
        "description": (
            "Power draw on gpu01 spiked to 650W (baseline ~380W) during a large "
            "training job. The spike triggered a facility power alert. Sysadmin "
            "must identify the offending job and node, and facility_admin must "
            "assess PDU capacity margin."
        ),
    })

    _write_json(env / "slurm" / "slurm_state.json", {
        "cluster": "exabench-cluster-a",
        "snapshot_time": snap_time,
        "nodes": [
            {"name": n, "state": "allocated", "cpus": 64, "memory_mb": 512000,
             "partitions": ["gpu"]} for n in nodes
        ],
        "partitions": [
            {"name": "gpu", "max_time": "72:00:00", "max_mem_per_node_mb": 512000,
             "default_mem_per_cpu_mb": 4096},
        ],
        "jobs": [
            {"job_id": "920001", "job_name": "llm_train_run7", "user": "bob",
             "account": "ml-lab", "state": "RUNNING", "exit_code": None,
             "node": "gpu01", "partition": "gpu",
             "submit_time": "2026-03-10T08:00:00Z", "start_time": "2026-03-10T08:05:00Z",
             "end_time": None, "elapsed": "07:55:00", "num_cpus": 64, "num_nodes": 1,
             "requested_mem_mb": 256000, "used_mem_mb": 240000,
             "oom_kill": False, "failure_reason": None},
        ],
    })

    snap_dt = datetime(2026, 3, 10, 16, 0, 0, tzinfo=UTC)
    metrics = {
        "power_w": (380.0, 10.0, "W"),
        "gpu_util_pct": (95.0, 3.0, "%"),
        "cpu_util_pct": (80.0, 5.0, "%"),
        "memory_util_pct": (47.0, 2.0, "%"),
    }
    df = make_telemetry(nodes, hours=8, snapshot_time=snap_dt, metrics=metrics)
    # Inject spike on gpu01 in the last 2 hours
    spike_mask = (df["node_id"] == "gpu01") & (df["metric_name"] == "power_w") & \
                 (df["timestamp"] >= snap_dt - timedelta(hours=2))
    df.loc[spike_mask, "value"] = df.loc[spike_mask, "value"].apply(lambda _: 650.0)
    _write_parquet(env / "telemetry" / "telemetry_timeseries.parquet", df)

    _write_yaml(env / "policy" / "rbac_policy.yaml", RBAC_FACILITY)

    _write_json(env / "incidents" / "incident_metadata.json", {
        "incident_id": "INC-2026-0310-001",
        "severity": "high",
        "title": "GPU power spike exceeds PDU threshold on gpu01",
        "opened_at": "2026-03-10T14:10:00Z",
        "status": "open",
        "affected_resource": "gpu01",
        "affected_job": "920001",
        "summary": (
            "gpu01 power draw reached 650W (~71% above baseline of ~380W) during "
            "job 920001 (llm_train_run7, bob). Facility PDU threshold is 600W per node. "
            "Sustained spike started ~14:00 UTC."
        ),
        "timeline": [
            {"time": "2026-03-10T08:05:00Z", "event": "Job 920001 started on gpu01"},
            {"time": "2026-03-10T14:00:00Z", "event": "Power draw began climbing on gpu01"},
            {"time": "2026-03-10T14:10:00Z", "event": "Facility alert: PDU threshold breached (650W)"},
            {"time": "2026-03-10T16:00:00Z", "event": "Snapshot captured for benchmark"},
        ],
        "resolution": None,
        "notes": "Job is still running. Sysadmin must decide whether to throttle or cancel.",
    })

    _write_text(env / "docs" / "gpu_power_policy.md", textwrap.dedent("""\
        # GPU Partition Power Policy

        ## Per-node power limits
        - Baseline TDP per GPU node: ~380W (4× A100 80GB at idle/moderate load)
        - Sustained limit: 550W per node (PDU safety margin)
        - Hard limit (facility PDU threshold): 600W per node

        ## Breach response
        1. Identify offending job via `slurm query_jobs`.
        2. If sustained > 600W for >10 min: cancel job with `slurm scancel`.
        3. File incident report with affected_resource and affected_job.

        ## GPU power capping
        Run `nvidia-smi -pl <watts>` on the node to apply a software power cap.
        Typical training cap: 400W per GPU (1600W per node for 4-GPU systems).
    """))


def build_env_07(root: Path) -> None:
    """energy_anomaly — PUE degradation, cooling issue."""
    env = root / "env_07"
    snap_time = "2026-03-12T10:00:00Z"
    nodes = [f"node{i:02d}" for i in range(1, 9)]

    _write_metadata(env, {
        "environment_id": "env_07",
        "snapshot_name": "PUE Degradation Cooling Issue",
        "scenario_type": "energy_anomaly",
        "cluster_name": "exabench-cluster-a",
        "snapshot_timestamp": snap_time,
        "bundle_root": "environments/env_07",
        "supported_roles": ["facility_admin"],
        "supported_categories": ["ENERGY"],
        "included_sources": ["slurm", "telemetry", "docs", "rbac", "incidents"],
        "included_files": [
            "slurm/slurm_state.json",
            "telemetry/telemetry_timeseries.parquet",
            "policy/rbac_policy.yaml",
            "incidents/incident_metadata.json",
            "docs/pue_monitoring.md",
        ],
        "implementation_status": "bundled",
        "validation_status": "validated",
        "description": (
            "Cluster PUE has degraded from 1.35 to 1.62 over 48 hours due to a "
            "partial CRAC unit failure. Inlet temperatures rising across multiple "
            "racks. facility_admin must identify root cause and recommend remediation."
        ),
    })

    _write_json(env / "slurm" / "slurm_state.json", {
        "cluster": "exabench-cluster-a",
        "snapshot_time": snap_time,
        "nodes": [
            {"name": n, "state": "allocated", "cpus": 64, "memory_mb": 256000,
             "partitions": ["standard"]} for n in nodes
        ],
        "partitions": [
            {"name": "standard", "max_time": "48:00:00", "max_mem_per_node_mb": 256000,
             "default_mem_per_cpu_mb": 2048},
        ],
        "jobs": [
            {"job_id": f"92100{i}", "job_name": f"sim_run_{i}", "user": "carol",
             "account": "cfd-lab", "state": "RUNNING", "exit_code": None,
             "node": f"node{i:02d}", "partition": "standard",
             "submit_time": "2026-03-11T22:00:00Z", "start_time": "2026-03-11T22:05:00Z",
             "end_time": None, "elapsed": "11:55:00", "num_cpus": 64, "num_nodes": 1,
             "requested_mem_mb": 128000, "used_mem_mb": 110000,
             "oom_kill": False, "failure_reason": None}
            for i in range(1, 9)
        ],
    })

    snap_dt = datetime(2026, 3, 12, 10, 0, 0, tzinfo=UTC)
    metrics = {
        "power_w": (320.0, 8.0, "W"),
        "cpu_util_pct": (88.0, 4.0, "%"),
        "cpu_temp_c": (72.0, 3.0, "°C"),
        "inlet_temp_c": (28.0, 2.0, "°C"),
        "memory_util_pct": (43.0, 2.0, "%"),
    }
    df = make_telemetry(nodes, hours=48, snapshot_time=snap_dt, metrics=metrics)
    # Simulate inlet temp rising over last 12 hours
    rising_mask = (df["metric_name"] == "inlet_temp_c") & \
                  (df["timestamp"] >= snap_dt - timedelta(hours=12))
    idxs = df[rising_mask].index
    hours_since = (df.loc[idxs, "timestamp"] - (snap_dt - timedelta(hours=12))).dt.total_seconds() / 3600
    df.loc[idxs, "value"] = 28.0 + hours_since * 1.5
    _write_parquet(env / "telemetry" / "telemetry_timeseries.parquet", df)

    _write_yaml(env / "policy" / "rbac_policy.yaml", {
        "version": "1.0",
        "roles": {
            "facility_admin": {
                "description": "Full facility access",
                "permissions": [{"resource": "*", "actions": ["*"]}],
            },
        },
        "hard_fail_on_violation": True,
    })

    _write_json(env / "incidents" / "incident_metadata.json", {
        "incident_id": "INC-2026-0312-001",
        "severity": "high",
        "title": "PUE degradation: 1.35 → 1.62 over 48h",
        "opened_at": "2026-03-11T22:00:00Z",
        "status": "open",
        "affected_resource": "CRAC-unit-2",
        "affected_job": None,
        "summary": (
            "Cluster PUE rose from baseline 1.35 to 1.62 over 48 hours. "
            "Inlet temperatures increasing across rack rows B and C. "
            "CRAC unit 2 reported partial airflow reduction at 22:00 UTC Mar 11."
        ),
        "timeline": [
            {"time": "2026-03-11T22:00:00Z", "event": "CRAC-2 partial airflow alarm triggered"},
            {"time": "2026-03-11T22:30:00Z", "event": "Inlet temp on node05-node08 starts climbing"},
            {"time": "2026-03-12T06:00:00Z", "event": "PUE crosses 1.5 threshold"},
            {"time": "2026-03-12T10:00:00Z", "event": "Snapshot captured — PUE at 1.62"},
        ],
        "resolution": None,
        "notes": "CRAC-2 filter may need replacement. Cooling capacity marginal at current load.",
    })

    _write_text(env / "docs" / "pue_monitoring.md", textwrap.dedent("""\
        # PUE Monitoring and Alerting

        ## Baseline and thresholds
        - Target PUE: 1.35
        - Warning threshold: 1.45
        - Critical threshold: 1.55

        ## Inlet temperature limits
        - Normal operating range: 18–27°C
        - Warning: >27°C for any rack row
        - Critical: >32°C — throttle or evacuate

        ## CRAC unit roles
        - CRAC-1: rows A–B (nodes 01–16)
        - CRAC-2: rows C–D (nodes 17–32)
        - CRAC-3: backup / overflow

        ## Remediation steps
        1. Check CRAC unit status via BMS.
        2. If airflow reduced: inspect/replace filter.
        3. Enable CRAC-3 backup while servicing primary.
        4. Monitor PUE recovery over 30-min windows.
    """))


def build_env_08(root: Path) -> None:
    """node_degradation — Thermal throttling on compute node."""
    env = root / "env_08"
    snap_time = "2026-03-14T09:00:00Z"
    nodes = [f"node{i:02d}" for i in range(1, 5)]

    _write_metadata(env, {
        "environment_id": "env_08",
        "snapshot_name": "Thermal Throttling on node03",
        "scenario_type": "node_degradation",
        "cluster_name": "exabench-cluster-a",
        "snapshot_timestamp": snap_time,
        "bundle_root": "environments/env_08",
        "supported_roles": ["sysadmin"],
        "supported_categories": ["MON"],
        "included_sources": ["slurm", "telemetry", "docs", "rbac", "incidents"],
        "included_files": [
            "slurm/slurm_state.json",
            "telemetry/telemetry_timeseries.parquet",
            "policy/rbac_policy.yaml",
            "incidents/incident_metadata.json",
            "docs/thermal_runbook.md",
        ],
        "implementation_status": "bundled",
        "validation_status": "validated",
        "description": (
            "node03 is experiencing thermal throttling due to a blocked cooling duct. "
            "CPU frequency is reduced by 40%. Jobs on node03 are running ~30% slower "
            "than on peer nodes. Sysadmin must identify the degraded node and drain it."
        ),
    })

    _write_json(env / "slurm" / "slurm_state.json", {
        "cluster": "exabench-cluster-a",
        "snapshot_time": snap_time,
        "nodes": [
            {"name": "node01", "state": "allocated", "cpus": 64, "memory_mb": 512000, "partitions": ["standard"]},
            {"name": "node02", "state": "allocated", "cpus": 64, "memory_mb": 512000, "partitions": ["standard"]},
            {"name": "node03", "state": "allocated", "cpus": 64, "memory_mb": 512000, "partitions": ["standard"]},
            {"name": "node04", "state": "idle",      "cpus": 64, "memory_mb": 512000, "partitions": ["standard"]},
        ],
        "partitions": [
            {"name": "standard", "max_time": "48:00:00", "max_mem_per_node_mb": 512000,
             "default_mem_per_cpu_mb": 2048},
        ],
        "jobs": [
            {"job_id": "930001", "job_name": "md_sim_run1", "user": "alice",
             "account": "phys-lab", "state": "RUNNING", "exit_code": None,
             "node": "node03", "partition": "standard",
             "submit_time": "2026-03-14T06:00:00Z", "start_time": "2026-03-14T06:05:00Z",
             "end_time": None, "elapsed": "02:55:00", "num_cpus": 32, "num_nodes": 1,
             "requested_mem_mb": 65536, "used_mem_mb": 60000,
             "oom_kill": False, "failure_reason": None},
        ],
    })

    snap_dt = datetime(2026, 3, 14, 9, 0, 0, tzinfo=UTC)
    df = make_telemetry(nodes, hours=6, snapshot_time=snap_dt)
    # node03: elevated temperature, reduced CPU util (throttled)
    throttle_mask = (df["node_id"] == "node03") & (df["metric_name"] == "cpu_util_pct")
    df.loc[throttle_mask, "value"] = df.loc[throttle_mask, "value"] * 0.6
    temp_node03 = (df["node_id"] == "node03") & (df["metric_name"] == "cpu_temp_c")
    if not temp_node03.any():
        # Add cpu_temp_c rows for node03
        import random
        rng = random.Random(1)
        step = timedelta(minutes=5)
        t = snap_dt - timedelta(hours=6)
        new_rows = []
        while t <= snap_dt:
            new_rows.append({
                "timestamp": t, "node_id": "node03", "metric_name": "cpu_temp_c",
                "value": round(88.0 + rng.gauss(0, 2), 2), "unit": "°C",
            })
            t += step
        extra = pd.DataFrame(new_rows)
        extra["timestamp"] = pd.to_datetime(extra["timestamp"], utc=True)
        df = pd.concat([df, extra], ignore_index=True)
    _write_parquet(env / "telemetry" / "telemetry_timeseries.parquet", df)

    _write_yaml(env / "policy" / "rbac_policy.yaml", RBAC_SYSADMIN_FULL)

    _write_json(env / "incidents" / "incident_metadata.json", {
        "incident_id": "INC-2026-0314-001",
        "severity": "medium",
        "title": "Thermal throttling on node03 — cooling duct blocked",
        "opened_at": "2026-03-14T07:30:00Z",
        "status": "open",
        "affected_resource": "node03",
        "affected_job": "930001",
        "summary": (
            "node03 CPU temperature reached 88–92°C (normal: 65–72°C). "
            "Thermal throttle engaged, reducing effective CPU frequency by ~40%. "
            "Root cause: blocked rear cooling duct (dust accumulation)."
        ),
        "timeline": [
            {"time": "2026-03-14T06:05:00Z", "event": "Job 930001 started on node03"},
            {"time": "2026-03-14T07:00:00Z", "event": "CPU temperature alarm on node03 (>85°C)"},
            {"time": "2026-03-14T07:30:00Z", "event": "Thermal throttle engaged — frequency reduced"},
            {"time": "2026-03-14T09:00:00Z", "event": "Snapshot captured for benchmark"},
        ],
        "resolution": None,
        "notes": "node03 should be drained and taken offline for cooling maintenance.",
    })

    _write_text(env / "docs" / "thermal_runbook.md", textwrap.dedent("""\
        # Thermal Management Runbook

        ## Normal CPU temperature ranges
        - Idle: 40–55°C
        - Full load: 65–75°C
        - Throttle threshold: 80°C (hardware-enforced)
        - Emergency shutdown: 95°C

        ## Symptoms of thermal throttling
        - Reduced CPU utilization despite full job load
        - SLURM job runtime significantly longer than expected
        - cpu_temp_c metric consistently above 80°C

        ## Immediate response
        1. Identify affected node: query telemetry for cpu_temp_c > 80°C.
        2. Drain node: `scontrol update nodename=<node> state=drain reason="thermal_throttle"`.
        3. Migrate any queued jobs to healthy nodes.
        4. Inspect cooling duct and fans.

        ## Root causes
        - Blocked rear duct (dust, cable obstruction)
        - Failed fan
        - CRAC unit insufficient capacity in rack section
    """))


def build_env_09(root: Path) -> None:
    """node_degradation — Memory ECC errors, flapping node."""
    env = root / "env_09"
    snap_time = "2026-03-15T11:00:00Z"
    nodes = ["node05", "node06", "node07", "node08"]

    _write_metadata(env, {
        "environment_id": "env_09",
        "snapshot_name": "Memory ECC Errors Flapping Node",
        "scenario_type": "node_degradation",
        "cluster_name": "exabench-cluster-a",
        "snapshot_timestamp": snap_time,
        "bundle_root": "environments/env_09",
        "supported_roles": ["sysadmin"],
        "supported_categories": ["MON"],
        "included_sources": ["slurm", "telemetry", "docs", "rbac", "incidents"],
        "included_files": [
            "slurm/slurm_state.json",
            "telemetry/telemetry_timeseries.parquet",
            "policy/rbac_policy.yaml",
            "incidents/incident_metadata.json",
            "docs/memory_ecc_guide.md",
        ],
        "implementation_status": "bundled",
        "validation_status": "validated",
        "description": (
            "node06 has been flapping between allocated and draining state due to "
            "correctable ECC memory errors. Two jobs have been requeued in the last "
            "4 hours. Sysadmin must determine if the node requires DIMM replacement."
        ),
    })

    _write_json(env / "slurm" / "slurm_state.json", {
        "cluster": "exabench-cluster-a",
        "snapshot_time": snap_time,
        "nodes": [
            {"name": "node05", "state": "allocated", "cpus": 64, "memory_mb": 512000, "partitions": ["standard"]},
            {"name": "node06", "state": "draining",  "cpus": 64, "memory_mb": 512000, "partitions": ["standard"]},
            {"name": "node07", "state": "allocated", "cpus": 64, "memory_mb": 512000, "partitions": ["standard"]},
            {"name": "node08", "state": "idle",      "cpus": 64, "memory_mb": 512000, "partitions": ["standard"]},
        ],
        "partitions": [
            {"name": "standard", "max_time": "48:00:00", "max_mem_per_node_mb": 512000,
             "default_mem_per_cpu_mb": 2048},
        ],
        "jobs": [
            {"job_id": "940010", "job_name": "genome_assembly", "user": "dave",
             "account": "bio-lab", "state": "REQUEUED", "exit_code": "0:1",
             "node": "node06", "partition": "standard",
             "submit_time": "2026-03-15T06:00:00Z", "start_time": "2026-03-15T06:05:00Z",
             "end_time": "2026-03-15T08:30:00Z", "elapsed": "02:25:00", "num_cpus": 32, "num_nodes": 1,
             "requested_mem_mb": 131072, "used_mem_mb": 125000,
             "oom_kill": False, "failure_reason": "NodeFail"},
        ],
    })

    snap_dt = datetime(2026, 3, 15, 11, 0, 0, tzinfo=UTC)
    df = make_telemetry(nodes, hours=6, snapshot_time=snap_dt)
    _write_parquet(env / "telemetry" / "telemetry_timeseries.parquet", df)

    _write_yaml(env / "policy" / "rbac_policy.yaml", RBAC_SYSADMIN_FULL)

    _write_json(env / "incidents" / "incident_metadata.json", {
        "incident_id": "INC-2026-0315-001",
        "severity": "medium",
        "title": "node06 flapping — correctable ECC memory errors",
        "opened_at": "2026-03-15T07:00:00Z",
        "status": "open",
        "affected_resource": "node06",
        "affected_job": "940010",
        "summary": (
            "node06 has generated 847 correctable ECC errors in the last 6 hours "
            "(normal: <10/day). Node transitioned to draining state twice. "
            "Job 940010 was requeued due to NodeFail. DIMM slot 4 suspected."
        ),
        "timeline": [
            {"time": "2026-03-15T05:00:00Z", "event": "ECC error rate begins rising on node06"},
            {"time": "2026-03-15T07:00:00Z", "event": "node06 auto-drains after threshold exceeded"},
            {"time": "2026-03-15T07:05:00Z", "event": "Job 940010 requeued"},
            {"time": "2026-03-15T08:30:00Z", "event": "Job 940010 fails again, node06 flaps"},
            {"time": "2026-03-15T11:00:00Z", "event": "Snapshot captured for benchmark"},
        ],
        "resolution": None,
        "notes": "Run `edac-util -s 0` on node06. DIMM replacement likely required.",
    })

    _write_text(env / "docs" / "memory_ecc_guide.md", textwrap.dedent("""\
        # Memory ECC Error Guide

        ## ECC error types
        - **Correctable (CE):** Single-bit errors, corrected by hardware. Logged but non-fatal.
        - **Uncorrectable (UE):** Multi-bit errors, cause system crash or memory corruption.

        ## Thresholds
        - CE threshold for alerting: >50 per hour on any DIMM
        - CE threshold for drain: >200 per hour (indicates failing DIMM)
        - Any UE: immediate drain and offline

        ## Diagnosis
        1. Check SLURM node state — is the node draining or drained?
        2. Query telemetry for memory error events.
        3. Run on the node: `edac-util -s 0` to see per-DIMM error counts.
        4. Run `mcelog` to see detailed CPU/memory machine check events.

        ## Remediation
        - Replace failing DIMM with spare.
        - Test with `memtest86+` before returning to service.
        - Document DIMM slot and replacement in asset management.
    """))


def build_env_10(root: Path) -> None:
    """policy_violation — User submits to restricted partition."""
    env = root / "env_10"
    snap_time = "2026-03-16T14:00:00Z"
    nodes = ["node01", "node02", "restricted01", "restricted02"]

    _write_metadata(env, {
        "environment_id": "env_10",
        "snapshot_name": "Policy Violation Restricted Partition",
        "scenario_type": "policy_violation",
        "cluster_name": "exabench-cluster-a",
        "snapshot_timestamp": snap_time,
        "bundle_root": "environments/env_10",
        "supported_roles": ["scientific_user", "sysadmin"],
        "supported_categories": ["JOB"],
        "included_sources": ["slurm", "telemetry", "docs", "rbac", "incidents"],
        "included_files": [
            "slurm/slurm_state.json",
            "telemetry/telemetry_timeseries.parquet",
            "policy/rbac_policy.yaml",
            "incidents/incident_metadata.json",
            "docs/partition_access_policy.md",
        ],
        "implementation_status": "bundled",
        "validation_status": "validated",
        "description": (
            "User 'eve' submitted a job to the 'restricted' partition, which requires "
            "explicit approval for accounts in the 'guest' group. The job was held by "
            "SLURM. Sysadmin must identify the violation and advise the user on the "
            "correct partition to use."
        ),
    })

    _write_json(env / "slurm" / "slurm_state.json", {
        "cluster": "exabench-cluster-a",
        "snapshot_time": snap_time,
        "nodes": [
            {"name": "node01",      "state": "allocated", "cpus": 64, "memory_mb": 256000, "partitions": ["standard"]},
            {"name": "node02",      "state": "idle",      "cpus": 64, "memory_mb": 256000, "partitions": ["standard"]},
            {"name": "restricted01","state": "allocated", "cpus": 128, "memory_mb": 1024000, "partitions": ["restricted"]},
            {"name": "restricted02","state": "idle",      "cpus": 128, "memory_mb": 1024000, "partitions": ["restricted"]},
        ],
        "partitions": [
            {"name": "standard",   "max_time": "48:00:00", "max_mem_per_node_mb": 256000, "default_mem_per_cpu_mb": 2048},
            {"name": "restricted", "max_time": "168:00:00", "max_mem_per_node_mb": 1024000, "default_mem_per_cpu_mb": 8192},
        ],
        "jobs": [
            {"job_id": "950100", "job_name": "protein_fold", "user": "eve",
             "account": "guest-account", "state": "PENDING", "exit_code": None,
             "node": None, "partition": "restricted",
             "submit_time": "2026-03-16T13:45:00Z", "start_time": None,
             "end_time": None, "elapsed": None, "num_cpus": 64, "num_nodes": 1,
             "requested_mem_mb": 512000, "used_mem_mb": None,
             "oom_kill": False, "failure_reason": "PartitionNotAvailable"},
        ],
    })

    snap_dt = datetime(2026, 3, 16, 14, 0, 0, tzinfo=UTC)
    df = make_telemetry(nodes, hours=2, snapshot_time=snap_dt)
    _write_parquet(env / "telemetry" / "telemetry_timeseries.parquet", df)

    _write_yaml(env / "policy" / "rbac_policy.yaml", RBAC_SYSADMIN_FULL)

    _write_json(env / "incidents" / "incident_metadata.json", {
        "incident_id": "INC-2026-0316-001",
        "severity": "low",
        "title": "Policy violation: guest account submitted to restricted partition",
        "opened_at": "2026-03-16T13:50:00Z",
        "status": "open",
        "affected_resource": "partition:restricted",
        "affected_job": "950100",
        "summary": (
            "User 'eve' (account: guest-account) submitted job 950100 to the 'restricted' "
            "partition. guest-account does not have AllowAccounts membership for 'restricted'. "
            "Job is held in PENDING state with reason PartitionNotAvailable."
        ),
        "timeline": [
            {"time": "2026-03-16T13:45:00Z", "event": "Job 950100 submitted to restricted partition"},
            {"time": "2026-03-16T13:45:00Z", "event": "Job held: PartitionNotAvailable"},
            {"time": "2026-03-16T13:50:00Z", "event": "Sysadmin alert: unauthorized partition access attempt"},
            {"time": "2026-03-16T14:00:00Z", "event": "Snapshot captured for benchmark"},
        ],
        "resolution": None,
        "notes": "User should be directed to submit to 'standard' partition or apply for restricted access.",
    })

    _write_text(env / "docs" / "partition_access_policy.md", textwrap.dedent("""\
        # Partition Access Policy

        ## standard partition
        - Available to: all registered users and accounts
        - Max walltime: 48 hours
        - Memory per node: 256 GB

        ## restricted partition
        - Available to: approved research groups only (AllowAccounts list)
        - Requires: PI approval + sysadmin account addition
        - Max walltime: 168 hours (1 week)
        - Memory per node: 1 TB (high-memory nodes)

        ## Requesting restricted access
        1. PI submits access request to helpdesk@hpc.example.edu.
        2. Sysadmin adds account to AllowAccounts in slurm.conf.
        3. User is notified and may resubmit.

        ## If a job is held (PartitionNotAvailable)
        - The job will remain PENDING indefinitely.
        - Cancel and resubmit to the correct partition, or request access.
        - `scancel <jobid>` to remove the held job.
    """))


def build_env_11(root: Path) -> None:
    """policy_violation — Account over allocation limit."""
    env = root / "env_11"
    snap_time = "2026-03-17T16:00:00Z"
    nodes = [f"node{i:02d}" for i in range(1, 9)]

    _write_metadata(env, {
        "environment_id": "env_11",
        "snapshot_name": "Account Over Allocation Limit",
        "scenario_type": "policy_violation",
        "cluster_name": "exabench-cluster-a",
        "snapshot_timestamp": snap_time,
        "bundle_root": "environments/env_11",
        "supported_roles": ["sysadmin", "facility_admin"],
        "supported_categories": ["JOB"],
        "included_sources": ["slurm", "telemetry", "docs", "rbac", "incidents"],
        "included_files": [
            "slurm/slurm_state.json",
            "telemetry/telemetry_timeseries.parquet",
            "policy/rbac_policy.yaml",
            "incidents/incident_metadata.json",
            "docs/allocation_policy.md",
        ],
        "implementation_status": "bundled",
        "validation_status": "validated",
        "description": (
            "Account 'ml-lab' has consumed 98% of its monthly CPU-hour allocation. "
            "Three jobs are pending due to QOS limit enforcement. facility_admin must "
            "assess whether to grant an exception or enforce the limit."
        ),
    })

    _write_json(env / "slurm" / "slurm_state.json", {
        "cluster": "exabench-cluster-a",
        "snapshot_time": snap_time,
        "nodes": [
            {"name": n, "state": "allocated", "cpus": 64, "memory_mb": 256000,
             "partitions": ["standard"]} for n in nodes
        ],
        "partitions": [
            {"name": "standard", "max_time": "48:00:00", "max_mem_per_node_mb": 256000,
             "default_mem_per_cpu_mb": 2048},
        ],
        "jobs": [
            {"job_id": "960001", "job_name": "bert_finetune_1", "user": "frank",
             "account": "ml-lab", "state": "PENDING", "exit_code": None,
             "node": None, "partition": "standard",
             "submit_time": "2026-03-17T15:00:00Z", "start_time": None,
             "end_time": None, "elapsed": None, "num_cpus": 64, "num_nodes": 1,
             "requested_mem_mb": 128000, "used_mem_mb": None,
             "oom_kill": False, "failure_reason": "QOSMaxCpuMinutesPerJobLimit"},
            {"job_id": "960002", "job_name": "bert_finetune_2", "user": "frank",
             "account": "ml-lab", "state": "PENDING", "exit_code": None,
             "node": None, "partition": "standard",
             "submit_time": "2026-03-17T15:01:00Z", "start_time": None,
             "end_time": None, "elapsed": None, "num_cpus": 64, "num_nodes": 1,
             "requested_mem_mb": 128000, "used_mem_mb": None,
             "oom_kill": False, "failure_reason": "QOSMaxCpuMinutesPerJobLimit"},
        ],
    })

    snap_dt = datetime(2026, 3, 17, 16, 0, 0, tzinfo=UTC)
    df = make_telemetry(nodes, hours=2, snapshot_time=snap_dt)
    _write_parquet(env / "telemetry" / "telemetry_timeseries.parquet", df)

    _write_yaml(env / "policy" / "rbac_policy.yaml", RBAC_FACILITY)

    _write_json(env / "incidents" / "incident_metadata.json", {
        "incident_id": "INC-2026-0317-001",
        "severity": "low",
        "title": "Account ml-lab at 98% monthly CPU-hour allocation",
        "opened_at": "2026-03-17T15:00:00Z",
        "status": "open",
        "affected_resource": "account:ml-lab",
        "affected_job": "960001",
        "summary": (
            "Account ml-lab has used 490,000 of 500,000 allocated CPU-hours for March 2026. "
            "Two new jobs (960001, 960002) are blocked by QOS limit. "
            "User frank has 4 days remaining in the billing period."
        ),
        "timeline": [
            {"time": "2026-03-17T15:00:00Z", "event": "Jobs 960001 and 960002 submitted"},
            {"time": "2026-03-17T15:00:00Z", "event": "Jobs blocked: QOSMaxCpuMinutesPerJobLimit"},
            {"time": "2026-03-17T15:05:00Z", "event": "Alert: ml-lab at 98% allocation"},
            {"time": "2026-03-17T16:00:00Z", "event": "Snapshot captured for benchmark"},
        ],
        "resolution": None,
        "notes": "PI may request emergency allocation extension via helpdesk.",
    })

    _write_text(env / "docs" / "allocation_policy.md", textwrap.dedent("""\
        # CPU-Hour Allocation Policy

        ## Allocation periods
        - Billing period: calendar month (reset on the 1st)
        - Allocations are per-account (not per-user within an account)

        ## QOS limits enforcement
        - At 90%: warning email to PI
        - At 100%: all new jobs blocked (QOSMaxCpuMinutesPerJobLimit)
        - Running jobs are NOT affected — only new submissions blocked

        ## Emergency extensions
        - PI submits request to allocations@hpc.example.edu
        - facility_admin reviews and may grant up to 20% overage
        - Overage is deducted from next month's allocation

        ## Checking account usage
        - `sacct -A <account> --format=CPUTimeRAW --starttime=<first-of-month>`
        - Divide by 60 for CPU-hours
    """))


def build_env_12(root: Path) -> None:
    """queue_congestion — Fairshare starvation, priority inversion."""
    env = root / "env_12"
    snap_time = "2026-03-18T10:00:00Z"
    nodes = [f"node{i:02d}" for i in range(1, 9)]

    _write_metadata(env, {
        "environment_id": "env_12",
        "snapshot_name": "Fairshare Starvation Priority Inversion",
        "scenario_type": "queue_congestion",
        "cluster_name": "exabench-cluster-a",
        "snapshot_timestamp": snap_time,
        "bundle_root": "environments/env_12",
        "supported_roles": ["sysadmin"],
        "supported_categories": ["JOB", "MON"],
        "included_sources": ["slurm", "telemetry", "docs", "rbac", "incidents"],
        "included_files": [
            "slurm/slurm_state.json",
            "telemetry/telemetry_timeseries.parquet",
            "policy/rbac_policy.yaml",
            "incidents/incident_metadata.json",
            "docs/fairshare_policy.md",
        ],
        "implementation_status": "bundled",
        "validation_status": "validated",
        "description": (
            "Account 'ml-lab' has been monopolizing the cluster for 72 hours, "
            "consuming 85% of CPU-hours. Account 'bio-lab' has 12 jobs waiting "
            "over 48 hours each due to fairshare starvation. Sysadmin must "
            "intervene to restore scheduling fairness."
        ),
    })

    _write_json(env / "slurm" / "slurm_state.json", {
        "cluster": "exabench-cluster-a",
        "snapshot_time": snap_time,
        "nodes": [
            {"name": n, "state": "allocated", "cpus": 64, "memory_mb": 256000,
             "partitions": ["standard"]} for n in nodes
        ],
        "partitions": [
            {"name": "standard", "max_time": "48:00:00", "max_mem_per_node_mb": 256000,
             "default_mem_per_cpu_mb": 2048},
        ],
        "jobs": [
            {"job_id": f"97000{i}", "job_name": f"ml_job_{i}", "user": "frank",
             "account": "ml-lab", "state": "RUNNING", "exit_code": None,
             "node": f"node{i:02d}", "partition": "standard",
             "submit_time": "2026-03-15T10:00:00Z", "start_time": "2026-03-15T10:05:00Z",
             "end_time": None, "elapsed": "71:55:00", "num_cpus": 64, "num_nodes": 1,
             "requested_mem_mb": 128000, "used_mem_mb": 100000,
             "oom_kill": False, "failure_reason": None}
            for i in range(1, 9)
        ] + [
            {"job_id": f"98000{i}", "job_name": f"genome_analysis_{i}", "user": "dave",
             "account": "bio-lab", "state": "PENDING", "exit_code": None,
             "node": None, "partition": "standard",
             "submit_time": "2026-03-16T10:00:00Z", "start_time": None,
             "end_time": None, "elapsed": None, "num_cpus": 32, "num_nodes": 1,
             "requested_mem_mb": 65536, "used_mem_mb": None,
             "oom_kill": False, "failure_reason": "Priority"}
            for i in range(1, 5)
        ],
    })

    snap_dt = datetime(2026, 3, 18, 10, 0, 0, tzinfo=UTC)
    df = make_telemetry(nodes, hours=72, snapshot_time=snap_dt)
    _write_parquet(env / "telemetry" / "telemetry_timeseries.parquet", df)

    _write_yaml(env / "policy" / "rbac_policy.yaml", RBAC_SYSADMIN_FULL)

    _write_json(env / "incidents" / "incident_metadata.json", {
        "incident_id": "INC-2026-0318-001",
        "severity": "medium",
        "title": "Fairshare starvation: bio-lab jobs pending 48+ hours",
        "opened_at": "2026-03-18T08:00:00Z",
        "status": "open",
        "affected_resource": "account:bio-lab",
        "affected_job": "980001",
        "summary": (
            "Account bio-lab has 4 jobs pending for 48+ hours due to low fairshare weight. "
            "ml-lab has consumed 85% of cluster resources over the past 72 hours, "
            "depressing bio-lab's fairshare score to near zero."
        ),
        "timeline": [
            {"time": "2026-03-15T10:05:00Z", "event": "ml-lab jobs start, consuming all 8 nodes"},
            {"time": "2026-03-16T10:00:00Z", "event": "bio-lab jobs submitted, enter queue"},
            {"time": "2026-03-18T08:00:00Z", "event": "Alert: bio-lab jobs pending >48h"},
            {"time": "2026-03-18T10:00:00Z", "event": "Snapshot captured for benchmark"},
        ],
        "resolution": None,
        "notes": "Consider setting TopJob priority boost for bio-lab or setting ml-lab job hold.",
    })

    _write_text(env / "docs" / "fairshare_policy.md", textwrap.dedent("""\
        # Fairshare Scheduling Policy

        ## How fairshare works
        - Each account has a fairshare weight (proportional to allocation size).
        - Jobs from accounts that have used more than their share get lower priority.
        - Fairshare score decays over a half-life period (default: 14 days).

        ## Priority formula
        `Job Priority = (Fairshare × W_fs) + (Age × W_age) + (QOS × W_qos)`

        ## Starvation prevention
        - `PriorityDecayHalfLife` = 14 days
        - `PriorityMaxAge` = 7 days (age boost caps at 7 days of waiting)
        - After 7 days, a starving job still may not start if fairshare delta is extreme.

        ## Sysadmin interventions
        - Boost a starving job: `scontrol update jobid=<id> priority=<high>`
        - Hold monopolizing account: `scontrol update account=<acct> maxsubmitjobs=0`
        - Reset fairshare counters: `sacctmgr modify account <acct> set rawusage=0`
    """))


def build_env_13(root: Path) -> None:
    """capacity_planning — 6-month CPU utilisation trend."""
    env = root / "env_13"
    snap_time = "2026-03-19T12:00:00Z"
    nodes = [f"node{i:02d}" for i in range(1, 17)]

    _write_metadata(env, {
        "environment_id": "env_13",
        "snapshot_name": "Six Month CPU Utilisation Trend",
        "scenario_type": "capacity_planning",
        "cluster_name": "exabench-cluster-a",
        "snapshot_timestamp": snap_time,
        "bundle_root": "environments/env_13",
        "supported_roles": ["facility_admin", "system_designer"],
        "supported_categories": ["ENERGY", "MON"],
        "included_sources": ["slurm", "telemetry", "docs", "rbac", "incidents"],
        "included_files": [
            "slurm/slurm_state.json",
            "telemetry/telemetry_timeseries.parquet",
            "policy/rbac_policy.yaml",
            "incidents/incident_metadata.json",
            "docs/capacity_planning_guide.md",
        ],
        "implementation_status": "bundled",
        "validation_status": "validated",
        "description": (
            "Six-month CPU utilisation telemetry showing a steady growth trend from "
            "62% average in October 2025 to 89% in March 2026. system_designer must "
            "forecast when the cluster will reach saturation and recommend expansion."
        ),
    })

    _write_json(env / "slurm" / "slurm_state.json", {
        "cluster": "exabench-cluster-a",
        "snapshot_time": snap_time,
        "nodes": [
            {"name": n, "state": "allocated", "cpus": 64, "memory_mb": 256000,
             "partitions": ["standard"]} for n in nodes
        ],
        "partitions": [
            {"name": "standard", "max_time": "48:00:00", "max_mem_per_node_mb": 256000,
             "default_mem_per_cpu_mb": 2048},
        ],
        "jobs": [],
    })

    # 6-month trend: daily aggregates
    snap_dt = datetime(2026, 3, 19, 12, 0, 0, tzinfo=UTC)
    start_dt = datetime(2025, 10, 1, 0, 0, 0, tzinfo=UTC)
    rows = []
    import random
    rng = random.Random(99)
    t = start_dt
    day = 0
    while t <= snap_dt:
        progress = day / 170  # 6 months ≈ 170 days
        base_util = 62.0 + progress * 27.0  # 62% → 89%
        for node in nodes:
            for metric, (mean_offset, std, unit) in [
                ("cpu_util_pct", (0.0, 5.0, "%")),
                ("memory_util_pct", (-10.0, 4.0, "%")),
                ("power_w", (-50.0, 15.0, "W")),
            ]:
                value = max(0.0, base_util + mean_offset + rng.gauss(0, std))
                rows.append({
                    "timestamp": t, "node_id": node,
                    "metric_name": metric, "value": round(value, 2), "unit": unit,
                })
        t += timedelta(days=1)
        day += 1

    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    _write_parquet(env / "telemetry" / "telemetry_timeseries.parquet", df)

    _write_yaml(env / "policy" / "rbac_policy.yaml", RBAC_SYSTEM_DESIGNER)

    _write_json(env / "incidents" / "incident_metadata.json", {
        "incident_id": "INC-2026-0319-001",
        "severity": "low",
        "title": "Capacity planning: CPU utilisation approaching saturation",
        "opened_at": "2026-03-19T00:00:00Z",
        "status": "open",
        "affected_resource": "cluster:exabench-cluster-a",
        "affected_job": None,
        "summary": (
            "Average CPU utilisation has grown from 62% (Oct 2025) to 89% (Mar 2026), "
            "a rate of ~4.7 pp/month. At this rate, 95% saturation will be reached in "
            "approximately 6 weeks. Expansion planning lead time is 12 weeks."
        ),
        "timeline": [
            {"time": "2025-10-01T00:00:00Z", "event": "Baseline: 62% average CPU utilisation"},
            {"time": "2026-01-01T00:00:00Z", "event": "Utilisation at 74% — growth trend confirmed"},
            {"time": "2026-03-01T00:00:00Z", "event": "Utilisation at 86% — capacity planning initiated"},
            {"time": "2026-03-19T12:00:00Z", "event": "Snapshot captured — 89% utilisation"},
        ],
        "resolution": None,
        "notes": "Recommend submitting hardware order within 2 weeks to avoid saturation impact.",
    })

    _write_text(env / "docs" / "capacity_planning_guide.md", textwrap.dedent("""\
        # Capacity Planning Guide

        ## Saturation thresholds
        - 85%: Begin capacity planning process
        - 90%: Order hardware (assuming 12-week delivery)
        - 95%: Queue times become unacceptable (>4h average wait)
        - 100%: New jobs cannot start

        ## Expansion options
        1. Add compute nodes to existing cluster (fastest, 8–12 weeks)
        2. Burst to cloud (immediate, higher cost per CPU-hour)
        3. Add new rack section (16–20 weeks — facility work required)

        ## Forecasting methodology
        - Use 90-day rolling average to smooth seasonal variation
        - Linear extrapolation for 6-week horizon
        - Flag if growth rate changes >2 pp/month

        ## Data sources
        - CPU utilisation: `telemetry query_timeseries metric_name=cpu_util_pct`
        - Job queue depth: `slurm query_jobs state=PENDING`
        - Historical sacct: available via the reporting portal
    """))


def build_env_14(root: Path) -> None:
    """capacity_planning — GPU demand forecast, expansion ask."""
    env = root / "env_14"
    snap_time = "2026-03-19T12:00:00Z"
    gpu_nodes = [f"gpu{i:02d}" for i in range(1, 5)]

    _write_metadata(env, {
        "environment_id": "env_14",
        "snapshot_name": "GPU Demand Forecast Expansion",
        "scenario_type": "capacity_planning",
        "cluster_name": "exabench-cluster-a",
        "snapshot_timestamp": snap_time,
        "bundle_root": "environments/env_14",
        "supported_roles": ["system_designer"],
        "supported_categories": ["ENERGY", "MON"],
        "included_sources": ["slurm", "telemetry", "docs", "rbac", "incidents"],
        "included_files": [
            "slurm/slurm_state.json",
            "telemetry/telemetry_timeseries.parquet",
            "policy/rbac_policy.yaml",
            "incidents/incident_metadata.json",
            "docs/gpu_expansion_proposal.md",
        ],
        "implementation_status": "bundled",
        "validation_status": "validated",
        "description": (
            "GPU partition utilisation has averaged 97% for the past 30 days. "
            "Average queue wait for GPU jobs is 18 hours. system_designer must "
            "quantify the demand gap and produce an expansion recommendation."
        ),
    })

    _write_json(env / "slurm" / "slurm_state.json", {
        "cluster": "exabench-cluster-a",
        "snapshot_time": snap_time,
        "nodes": [
            {"name": n, "state": "allocated", "cpus": 64, "memory_mb": 512000,
             "partitions": ["gpu"]} for n in gpu_nodes
        ],
        "partitions": [
            {"name": "gpu", "max_time": "72:00:00", "max_mem_per_node_mb": 512000,
             "default_mem_per_cpu_mb": 4096},
        ],
        "jobs": [
            {"job_id": f"98500{i}", "job_name": f"gpu_pending_{i}", "user": "bob",
             "account": "ml-lab", "state": "PENDING", "exit_code": None,
             "node": None, "partition": "gpu",
             "submit_time": f"2026-03-1{i}T10:00:00Z", "start_time": None,
             "end_time": None, "elapsed": None, "num_cpus": 64, "num_nodes": 1,
             "requested_mem_mb": 256000, "used_mem_mb": None,
             "oom_kill": False, "failure_reason": "Priority"}
            for i in range(1, 7)
        ],
    })

    snap_dt = datetime(2026, 3, 19, 12, 0, 0, tzinfo=UTC)
    df = make_telemetry(gpu_nodes, hours=720, snapshot_time=snap_dt,
                        metrics={
                            "gpu_util_pct": (97.0, 2.0, "%"),
                            "cpu_util_pct": (85.0, 5.0, "%"),
                            "power_w": (580.0, 20.0, "W"),
                            "memory_util_pct": (88.0, 3.0, "%"),
                        })
    _write_parquet(env / "telemetry" / "telemetry_timeseries.parquet", df)

    _write_yaml(env / "policy" / "rbac_policy.yaml", {
        "version": "1.0",
        "roles": {
            "system_designer": {
                "description": "Full read access for capacity planning",
                "permissions": [{"resource": "*", "actions": ["read"]}],
            },
        },
        "hard_fail_on_violation": True,
    })

    _write_json(env / "incidents" / "incident_metadata.json", {
        "incident_id": "INC-2026-0319-002",
        "severity": "medium",
        "title": "GPU partition at 97% utilisation — expansion required",
        "opened_at": "2026-03-01T00:00:00Z",
        "status": "open",
        "affected_resource": "partition:gpu",
        "affected_job": None,
        "summary": (
            "GPU partition (4 nodes, 16 GPUs) has run at 97%+ utilisation for 30 days. "
            "Average queue wait: 18 hours. 6 jobs currently pending. "
            "ML workload growth rate: ~15% MoM. Projected: 20+ GPUs needed by Q3 2026."
        ),
        "timeline": [
            {"time": "2026-02-01T00:00:00Z", "event": "GPU utilisation crosses 90% sustained"},
            {"time": "2026-02-15T00:00:00Z", "event": "Average queue wait exceeds 12 hours"},
            {"time": "2026-03-01T00:00:00Z", "event": "Capacity planning triggered"},
            {"time": "2026-03-19T12:00:00Z", "event": "Snapshot captured — 6 jobs pending"},
        ],
        "resolution": None,
        "notes": "H100 nodes recommended. 8-week delivery from approved vendor.",
    })

    _write_text(env / "docs" / "gpu_expansion_proposal.md", textwrap.dedent("""\
        # GPU Expansion Proposal — Q3 2026

        ## Current state
        - GPU nodes: 4 (gpu01–gpu04), each with 4× A100 80GB
        - Total GPUs: 16
        - 30-day average utilisation: 97%
        - 30-day average queue wait: 18 hours

        ## Demand projection
        - ML workload growth: ~15% month-over-month
        - Projected demand at Q3 2026: equivalent of 28 A100s (175% of current)

        ## Expansion options
        | Option | GPUs added | Cost | Lead time |
        |--------|-----------|------|-----------|
        | 2× A100 nodes (8 GPUs) | 8 | $320K | 8 weeks |
        | 4× A100 nodes (16 GPUs) | 16 | $640K | 8 weeks |
        | 4× H100 nodes (32 GPUs) | 32 (equiv) | $1.1M | 12 weeks |

        ## Recommendation
        Option C (4× H100) provides 2× compute/GPU vs A100 for AI workloads,
        effectively adding 64 A100-equivalent GPU slots. Covers projected demand
        through Q1 2027.
    """))


def build_env_15(root: Path) -> None:
    """multi_job_interference — Two jobs competing for same node memory."""
    env = root / "env_15"
    snap_time = "2026-03-13T15:00:00Z"
    nodes = ["node01", "node02", "node03"]

    _write_metadata(env, {
        "environment_id": "env_15",
        "snapshot_name": "Multi-Job Memory Interference",
        "scenario_type": "multi_job_interference",
        "cluster_name": "exabench-cluster-a",
        "snapshot_timestamp": snap_time,
        "bundle_root": "environments/env_15",
        "supported_roles": ["sysadmin", "researcher"],
        "supported_categories": ["JOB", "MON"],
        "included_sources": ["slurm", "telemetry", "docs", "rbac", "incidents"],
        "included_files": [
            "slurm/slurm_state.json",
            "telemetry/telemetry_timeseries.parquet",
            "policy/rbac_policy.yaml",
            "incidents/incident_metadata.json",
            "docs/memory_oversubscription.md",
        ],
        "implementation_status": "bundled",
        "validation_status": "validated",
        "description": (
            "Two jobs share node01: job A requested 180GB and job B requested 200GB, "
            "totalling 380GB on a 256GB node. Swap activity is causing severe performance "
            "degradation. Sysadmin must identify the oversubscription and decide which "
            "job to terminate or migrate."
        ),
    })

    _write_json(env / "slurm" / "slurm_state.json", {
        "cluster": "exabench-cluster-a",
        "snapshot_time": snap_time,
        "nodes": [
            {"name": "node01", "state": "allocated", "cpus": 64, "memory_mb": 256000, "partitions": ["standard"]},
            {"name": "node02", "state": "idle",      "cpus": 64, "memory_mb": 256000, "partitions": ["standard"]},
            {"name": "node03", "state": "idle",      "cpus": 64, "memory_mb": 256000, "partitions": ["standard"]},
        ],
        "partitions": [
            {"name": "standard", "max_time": "48:00:00", "max_mem_per_node_mb": 256000,
             "default_mem_per_cpu_mb": 2048},
        ],
        "jobs": [
            {"job_id": "990001", "job_name": "climate_model_A", "user": "alice",
             "account": "phys-lab", "state": "RUNNING", "exit_code": None,
             "node": "node01", "partition": "standard",
             "submit_time": "2026-03-13T10:00:00Z", "start_time": "2026-03-13T10:05:00Z",
             "end_time": None, "elapsed": "04:55:00", "num_cpus": 32, "num_nodes": 1,
             "requested_mem_mb": 184320, "used_mem_mb": 183000,
             "oom_kill": False, "failure_reason": None},
            {"job_id": "990002", "job_name": "climate_model_B", "user": "alice",
             "account": "phys-lab", "state": "RUNNING", "exit_code": None,
             "node": "node01", "partition": "standard",
             "submit_time": "2026-03-13T10:00:00Z", "start_time": "2026-03-13T10:05:00Z",
             "end_time": None, "elapsed": "04:55:00", "num_cpus": 32, "num_nodes": 1,
             "requested_mem_mb": 204800, "used_mem_mb": 195000,
             "oom_kill": False, "failure_reason": None},
        ],
    })

    snap_dt = datetime(2026, 3, 13, 15, 0, 0, tzinfo=UTC)
    df = make_telemetry(nodes, hours=5, snapshot_time=snap_dt, metrics={
        "memory_util_pct": (75.0, 2.0, "%"),
        "memory_used_mb": (192000.0, 3000.0, "MB"),
        "cpu_util_pct": (55.0, 8.0, "%"),  # Low CPU — stalled on swap I/O
        "power_w": (280.0, 10.0, "W"),
    })
    # node01: memory at 145% (oversubscribed)
    mem_mask = (df["node_id"] == "node01") & (df["metric_name"] == "memory_util_pct")
    df.loc[mem_mask, "value"] = 145.0
    used_mask = (df["node_id"] == "node01") & (df["metric_name"] == "memory_used_mb")
    df.loc[used_mask, "value"] = 378000.0
    _write_parquet(env / "telemetry" / "telemetry_timeseries.parquet", df)

    _write_yaml(env / "policy" / "rbac_policy.yaml", RBAC_RESEARCHER)

    _write_json(env / "incidents" / "incident_metadata.json", {
        "incident_id": "INC-2026-0313-001",
        "severity": "high",
        "title": "Memory oversubscription: node01 at 145% utilisation",
        "opened_at": "2026-03-13T12:00:00Z",
        "status": "open",
        "affected_resource": "node01",
        "affected_job": "990001",
        "summary": (
            "Jobs 990001 and 990002 are both running on node01. Combined requested "
            "memory: 380GB on a 256GB node. node01 memory utilisation at 145%. "
            "Swap I/O causing both jobs to run 3–4× slower than expected."
        ),
        "timeline": [
            {"time": "2026-03-13T10:05:00Z", "event": "Jobs 990001 and 990002 start on node01"},
            {"time": "2026-03-13T11:00:00Z", "event": "Memory utilisation crosses 100%"},
            {"time": "2026-03-13T12:00:00Z", "event": "Alert: node01 swap I/O excessive"},
            {"time": "2026-03-13T15:00:00Z", "event": "Snapshot captured — 145% memory util"},
        ],
        "resolution": None,
        "notes": "SLURM memory enforcement was bypassed — investigate MaxMemPerNode setting.",
    })

    _write_text(env / "docs" / "memory_oversubscription.md", textwrap.dedent("""\
        # Memory Oversubscription and Enforcement

        ## Why oversubscription happens
        - `--mem` in job script is a request, not a hard limit by default.
        - If MaxMemPerNode is not enforced in SLURM, jobs can use more than requested.
        - Multiple jobs on the same node can collectively exceed physical RAM.

        ## Symptoms
        - node memory_util_pct > 100%
        - Excessive swap I/O (disk_write_mbps spikes)
        - Jobs run much slower than expected (CPU util drops due to I/O wait)

        ## Immediate response
        1. Identify jobs on the affected node: `slurm query_jobs`.
        2. Determine which job is using more than requested.
        3. Cancel the lower-priority job: `scancel <jobid>`.
        4. The remaining job should recover performance.

        ## Prevention
        - Set `MaxMemPerNode` in partition config.
        - Enable cgroup-based memory enforcement: `ConstrainRAMSpace=yes`.
        - Run `scontrol show config | grep Memory` to verify enforcement is active.
    """))


def build_env_16(root: Path) -> None:
    """scheduler_misconfiguration — Wrong default partition in slurm.conf."""
    env = root / "env_16"
    snap_time = "2026-03-11T09:00:00Z"
    nodes = ["node01", "node02", "gpu01"]

    _write_metadata(env, {
        "environment_id": "env_16",
        "snapshot_name": "Wrong Default Partition Misconfiguration",
        "scenario_type": "scheduler_misconfiguration",
        "cluster_name": "exabench-cluster-a",
        "snapshot_timestamp": snap_time,
        "bundle_root": "environments/env_16",
        "supported_roles": ["sysadmin"],
        "supported_categories": ["JOB"],
        "included_sources": ["slurm", "telemetry", "docs", "rbac", "incidents"],
        "included_files": [
            "slurm/slurm_state.json",
            "telemetry/telemetry_timeseries.parquet",
            "policy/rbac_policy.yaml",
            "incidents/incident_metadata.json",
            "docs/slurm_config_guide.md",
        ],
        "implementation_status": "bundled",
        "validation_status": "validated",
        "description": (
            "After a SLURM reconfiguration, the default partition was accidentally "
            "changed to 'gpu'. CPU-only jobs are now landing on GPU nodes, wasting "
            "GPUs and blocking GPU workloads. Sysadmin must identify and fix the "
            "misconfiguration."
        ),
    })

    _write_json(env / "slurm" / "slurm_state.json", {
        "cluster": "exabench-cluster-a",
        "snapshot_time": snap_time,
        "nodes": [
            {"name": "node01", "state": "idle",      "cpus": 64, "memory_mb": 256000, "partitions": ["standard"]},
            {"name": "node02", "state": "idle",      "cpus": 64, "memory_mb": 256000, "partitions": ["standard"]},
            {"name": "gpu01",  "state": "allocated", "cpus": 64, "memory_mb": 512000, "partitions": ["gpu"]},
        ],
        "partitions": [
            {"name": "standard", "max_time": "48:00:00", "max_mem_per_node_mb": 256000,
             "default_mem_per_cpu_mb": 2048},
            {"name": "gpu",      "max_time": "72:00:00", "max_mem_per_node_mb": 512000,
             "default_mem_per_cpu_mb": 4096},
        ],
        "jobs": [
            {"job_id": "910500", "job_name": "cpu_only_analysis", "user": "carol",
             "account": "cfd-lab", "state": "RUNNING", "exit_code": None,
             "node": "gpu01", "partition": "gpu",
             "submit_time": "2026-03-11T08:00:00Z", "start_time": "2026-03-11T08:05:00Z",
             "end_time": None, "elapsed": "00:55:00", "num_cpus": 16, "num_nodes": 1,
             "requested_mem_mb": 32768, "used_mem_mb": 28000,
             "oom_kill": False, "failure_reason": None},
        ],
    })

    snap_dt = datetime(2026, 3, 11, 9, 0, 0, tzinfo=UTC)
    df = make_telemetry(nodes, hours=2, snapshot_time=snap_dt, metrics={
        "cpu_util_pct": (20.0, 5.0, "%"),
        "gpu_util_pct": (0.0, 1.0, "%"),  # GPUs idle despite job on gpu01
        "memory_util_pct": (10.0, 2.0, "%"),
        "power_w": (200.0, 10.0, "W"),
    })
    _write_parquet(env / "telemetry" / "telemetry_timeseries.parquet", df)

    _write_yaml(env / "policy" / "rbac_policy.yaml", RBAC_SYSADMIN_FULL)

    _write_json(env / "incidents" / "incident_metadata.json", {
        "incident_id": "INC-2026-0311-001",
        "severity": "medium",
        "title": "Scheduler misconfiguration: default partition changed to 'gpu'",
        "opened_at": "2026-03-11T08:30:00Z",
        "status": "open",
        "affected_resource": "partition:gpu",
        "affected_job": "910500",
        "summary": (
            "After slurm.conf reconfiguration at 08:00 UTC, Default=YES was incorrectly "
            "applied to the 'gpu' partition. CPU-only job 910500 was routed to gpu01, "
            "occupying the node while wasting all 4 GPUs. standard partition nodes are idle."
        ),
        "timeline": [
            {"time": "2026-03-11T07:55:00Z", "event": "slurm.conf updated (routine maintenance)"},
            {"time": "2026-03-11T08:00:00Z", "event": "slurmctld reloaded with new config"},
            {"time": "2026-03-11T08:05:00Z", "event": "Job 910500 starts on gpu01 (wrong partition)"},
            {"time": "2026-03-11T08:30:00Z", "event": "Alert: GPU nodes allocated, GPUs idle"},
            {"time": "2026-03-11T09:00:00Z", "event": "Snapshot captured for benchmark"},
        ],
        "resolution": None,
        "notes": "Fix: set Default=YES on 'standard', remove from 'gpu' in slurm.conf.",
    })

    _write_text(env / "docs" / "slurm_config_guide.md", textwrap.dedent("""\
        # SLURM Configuration Guide

        ## Default partition
        - Set `Default=YES` on exactly one partition.
        - Jobs submitted without `-p` go to the default partition.
        - Only one partition can be default; if multiple have `Default=YES`, behaviour is undefined.

        ## GPU partition configuration
        - GPU partitions should NOT be the default.
        - Users must explicitly request GPU resources with `-p gpu --gres=gpu:N`.
        - Prevents CPU-only jobs from consuming GPU nodes.

        ## Verifying configuration after reload
        1. `sinfo -o "%P %D %C"` — check partition status and node counts.
        2. `scontrol show partition <name>` — verify Default=YES/NO.
        3. Submit a test job without `-p` and verify it lands in 'standard'.

        ## Safe config reload procedure
        1. Edit `/etc/slurm/slurm.conf`
        2. `scontrol reconfig` (live reload, no restart needed)
        3. Verify with `sinfo` immediately
    """))


def build_env_17(root: Path) -> None:
    """job_failure — MPI communication timeout (network fault)."""
    env = root / "env_17"
    snap_time = "2026-03-16T20:00:00Z"
    nodes = ["node10", "node11", "node12", "node13"]

    _write_metadata(env, {
        "environment_id": "env_17",
        "snapshot_name": "MPI Communication Timeout Network Fault",
        "scenario_type": "job_failure",
        "cluster_name": "exabench-cluster-a",
        "snapshot_timestamp": snap_time,
        "bundle_root": "environments/env_17",
        "supported_roles": ["sysadmin"],
        "supported_categories": ["JOB", "MON"],
        "included_sources": ["slurm", "telemetry", "docs", "rbac", "incidents"],
        "included_files": [
            "slurm/slurm_state.json",
            "telemetry/telemetry_timeseries.parquet",
            "policy/rbac_policy.yaml",
            "incidents/incident_metadata.json",
            "docs/mpi_troubleshooting.md",
        ],
        "implementation_status": "bundled",
        "validation_status": "validated",
        "description": (
            "A 4-node MPI job failed after 6 hours with exit code 137 (SIGKILL). "
            "Network telemetry shows node11 had zero RX traffic for 30 minutes before "
            "the failure. Sysadmin must diagnose the network fault and identify whether "
            "the switch port or NIC is at fault."
        ),
    })

    _write_json(env / "slurm" / "slurm_state.json", {
        "cluster": "exabench-cluster-a",
        "snapshot_time": snap_time,
        "nodes": [
            {"name": "node10", "state": "idle", "cpus": 64, "memory_mb": 256000, "partitions": ["standard"]},
            {"name": "node11", "state": "drain", "cpus": 64, "memory_mb": 256000, "partitions": ["standard"]},
            {"name": "node12", "state": "idle", "cpus": 64, "memory_mb": 256000, "partitions": ["standard"]},
            {"name": "node13", "state": "idle", "cpus": 64, "memory_mb": 256000, "partitions": ["standard"]},
        ],
        "partitions": [
            {"name": "standard", "max_time": "48:00:00", "max_mem_per_node_mb": 256000,
             "default_mem_per_cpu_mb": 2048},
        ],
        "jobs": [
            {"job_id": "915000", "job_name": "mpi_weather_sim", "user": "carol",
             "account": "cfd-lab", "state": "FAILED", "exit_code": "137:0",
             "node": "node10,node11,node12,node13", "partition": "standard",
             "submit_time": "2026-03-16T14:00:00Z", "start_time": "2026-03-16T14:05:00Z",
             "end_time": "2026-03-16T20:05:00Z", "elapsed": "06:00:00",
             "num_cpus": 256, "num_nodes": 4,
             "requested_mem_mb": 65536, "used_mem_mb": 55000,
             "oom_kill": False, "failure_reason": "NodeFail"},
        ],
    })

    snap_dt = datetime(2026, 3, 16, 20, 0, 0, tzinfo=UTC)
    df = make_telemetry(nodes, hours=7, snapshot_time=snap_dt, metrics={
        "cpu_util_pct": (85.0, 5.0, "%"),
        "net_rx_mbps": (450.0, 30.0, "Mbps"),
        "net_tx_mbps": (440.0, 30.0, "Mbps"),
        "memory_util_pct": (40.0, 3.0, "%"),
        "power_w": (300.0, 10.0, "W"),
    })
    # node11: zero network RX from 5h before snap to end
    silent_mask = (df["node_id"] == "node11") & \
                  (df["metric_name"] == "net_rx_mbps") & \
                  (df["timestamp"] >= snap_dt - timedelta(hours=1))
    df.loc[silent_mask, "value"] = 0.0
    _write_parquet(env / "telemetry" / "telemetry_timeseries.parquet", df)

    _write_yaml(env / "policy" / "rbac_policy.yaml", RBAC_SYSADMIN_FULL)

    _write_json(env / "incidents" / "incident_metadata.json", {
        "incident_id": "INC-2026-0316-002",
        "severity": "high",
        "title": "MPI job failure due to network timeout on node11",
        "opened_at": "2026-03-16T20:05:00Z",
        "status": "open",
        "affected_resource": "node11",
        "affected_job": "915000",
        "summary": (
            "4-node MPI job 915000 failed after 6 hours with exit 137. "
            "Network telemetry shows node11 net_rx_mbps dropped to 0 at ~19:05 UTC. "
            "MPI timeout (300s) triggered SIGKILL across all ranks. "
            "node11 auto-drained after NodeFail detection."
        ),
        "timeline": [
            {"time": "2026-03-16T14:05:00Z", "event": "Job 915000 starts on 4 nodes"},
            {"time": "2026-03-16T19:05:00Z", "event": "node11 network RX drops to 0"},
            {"time": "2026-03-16T20:05:00Z", "event": "MPI timeout — SIGKILL sent to all ranks"},
            {"time": "2026-03-16T20:06:00Z", "event": "Job 915000 failed (exit 137)"},
            {"time": "2026-03-16T20:07:00Z", "event": "node11 auto-drained (NodeFail)"},
            {"time": "2026-03-16T20:00:00Z", "event": "Snapshot captured for benchmark"},
        ],
        "resolution": None,
        "notes": "Check switch port on node11 for link-down events. Possible NIC failure.",
    })

    _write_text(env / "docs" / "mpi_troubleshooting.md", textwrap.dedent("""\
        # MPI Job Failure Troubleshooting

        ## Common failure modes
        1. **Network timeout**: One rank loses connectivity; other ranks hang waiting.
        2. **OOM kill**: A rank exceeds memory limit and is killed.
        3. **Node failure**: Hardware fault causes one node to drop out.
        4. **Rank timeout**: Slow node causes MPI barrier timeout.

        ## Diagnosis steps for network timeout (exit 137)
        1. Query telemetry: `telemetry query_timeseries metric_name=net_rx_mbps`
           — Look for zero or near-zero values on any node during the job runtime.
        2. Check SLURM node state: nodes that failed should be drained.
        3. On the suspect node: `ip link show` — check for link-down.
        4. Check switch logs for port errors: `ethtool -S <nic>`.

        ## Network hardware checklist
        - Check NIC link status: `ethtool eth0 | grep -i link`
        - Check switch port: contact network admin for switch port counters
        - Check InfiniBand (if used): `ibstat`, `ibdiagnet`
        - Replace NIC or cable if persistent link failures confirmed
    """))


def build_env_18(root: Path) -> None:
    """job_failure — Checkpoint file missing, restart fails."""
    env = root / "env_18"
    snap_time = "2026-03-17T08:00:00Z"
    nodes = ["node05", "node06"]

    _write_metadata(env, {
        "environment_id": "env_18",
        "snapshot_name": "Checkpoint File Missing Restart Fails",
        "scenario_type": "job_failure",
        "cluster_name": "exabench-cluster-a",
        "snapshot_timestamp": snap_time,
        "bundle_root": "environments/env_18",
        "supported_roles": ["scientific_user"],
        "supported_categories": ["JOB"],
        "included_sources": ["slurm", "telemetry", "docs", "rbac", "incidents"],
        "included_files": [
            "slurm/slurm_state.json",
            "telemetry/telemetry_timeseries.parquet",
            "policy/rbac_policy.yaml",
            "incidents/incident_metadata.json",
            "docs/checkpoint_restart_guide.md",
        ],
        "implementation_status": "bundled",
        "validation_status": "validated",
        "description": (
            "User 'alice' resubmitted a long-running simulation with checkpoint/restart. "
            "The job failed immediately with exit code 1 because the checkpoint file "
            "path referenced in the job script no longer exists (scratch purge). "
            "User must identify the root cause and know how to recover."
        ),
    })

    _write_json(env / "slurm" / "slurm_state.json", {
        "cluster": "exabench-cluster-a",
        "snapshot_time": snap_time,
        "nodes": [
            {"name": "node05", "state": "idle", "cpus": 64, "memory_mb": 512000, "partitions": ["standard"]},
            {"name": "node06", "state": "idle", "cpus": 64, "memory_mb": 512000, "partitions": ["standard"]},
        ],
        "partitions": [
            {"name": "standard", "max_time": "48:00:00", "max_mem_per_node_mb": 512000,
             "default_mem_per_cpu_mb": 2048},
        ],
        "jobs": [
            {"job_id": "925000", "job_name": "md_restart_run", "user": "alice",
             "account": "phys-lab", "state": "FAILED", "exit_code": "1:0",
             "node": "node05", "partition": "standard",
             "submit_time": "2026-03-17T07:50:00Z", "start_time": "2026-03-17T07:55:00Z",
             "end_time": "2026-03-17T07:56:00Z", "elapsed": "00:01:00",
             "num_cpus": 32, "num_nodes": 1,
             "requested_mem_mb": 131072, "used_mem_mb": 2048,
             "oom_kill": False, "failure_reason": "NonZeroExitCode"},
        ],
    })

    snap_dt = datetime(2026, 3, 17, 8, 0, 0, tzinfo=UTC)
    df = make_telemetry(nodes, hours=1, snapshot_time=snap_dt)
    _write_parquet(env / "telemetry" / "telemetry_timeseries.parquet", df)

    _write_yaml(env / "policy" / "rbac_policy.yaml", {
        "version": "1.0",
        "roles": {
            "scientific_user": {
                "description": "Regular user — own jobs only",
                "permissions": [
                    {"resource": "slurm.jobs", "actions": ["read_own"], "constraint": "user == requester"},
                    {"resource": "slurm.partitions", "actions": ["read"]},
                    {"resource": "docs", "actions": ["read"]},
                    {"resource": "incidents", "actions": ["read"]},
                ],
            },
        },
        "hard_fail_on_violation": True,
    })

    _write_json(env / "incidents" / "incident_metadata.json", {
        "incident_id": "INC-2026-0317-002",
        "severity": "low",
        "title": "Job restart failed: checkpoint file missing (scratch purge)",
        "opened_at": "2026-03-17T07:56:00Z",
        "status": "open",
        "affected_resource": "node05",
        "affected_job": "925000",
        "summary": (
            "Job 925000 (alice, md_restart_run) failed 1 minute after start with exit code 1. "
            "The job script referenced checkpoint file /scratch/alice/md_run/checkpoint.dat, "
            "which was deleted by the 30-day scratch auto-purge on 2026-03-15. "
            "User must restart from the last available checkpoint or restart from scratch."
        ),
        "timeline": [
            {"time": "2026-02-15T00:00:00Z", "event": "Original job ran and wrote checkpoint"},
            {"time": "2026-03-15T00:00:00Z", "event": "Scratch auto-purge deleted /scratch/alice/md_run/"},
            {"time": "2026-03-17T07:55:00Z", "event": "Job 925000 starts, opens checkpoint — FileNotFoundError"},
            {"time": "2026-03-17T07:56:00Z", "event": "Job exits with code 1"},
            {"time": "2026-03-17T08:00:00Z", "event": "Snapshot captured for benchmark"},
        ],
        "resolution": None,
        "notes": "User should check if checkpoint exists in long-term storage before restarting from scratch.",
    })

    _write_text(env / "docs" / "checkpoint_restart_guide.md", textwrap.dedent("""\
        # Checkpoint and Restart Guide

        ## Scratch filesystem purge policy
        - `/scratch` files are automatically deleted after **30 days** without access.
        - This is to prevent scratch from filling up.
        - **Do NOT store checkpoints you intend to reuse in /scratch.**

        ## Where to store checkpoints
        - Long-term: `/project/<group>/<user>/checkpoints/` (not purged, quota applies)
        - Short-term (active jobs): `/scratch/<user>/` (purged after 30 days)

        ## Recovering from missing checkpoint
        1. Check if checkpoint was saved to a non-scratch location.
        2. If not: you must restart the simulation from the beginning.
        3. Update your job script to write checkpoints to `/project/` going forward.

        ## Writing a restart-capable job script
        ```bash
        #SBATCH --job-name=md_restart
        CHECKPOINT=/project/phys-lab/alice/checkpoints/md_run.chk
        if [ -f "$CHECKPOINT" ]; then
            srun md_sim --restart "$CHECKPOINT"
        else
            srun md_sim --new-run
        fi
        ```
    """))


def build_env_19(root: Path) -> None:
    """energy_anomaly — GPU idle but not released, energy waste."""
    env = root / "env_19"
    snap_time = "2026-03-18T18:00:00Z"
    gpu_nodes = ["gpu01", "gpu02", "gpu03", "gpu04"]

    _write_metadata(env, {
        "environment_id": "env_19",
        "snapshot_name": "GPU Idle Energy Waste Not Released",
        "scenario_type": "energy_anomaly",
        "cluster_name": "exabench-cluster-a",
        "snapshot_timestamp": snap_time,
        "bundle_root": "environments/env_19",
        "supported_roles": ["facility_admin"],
        "supported_categories": ["ENERGY", "MON"],
        "included_sources": ["slurm", "telemetry", "docs", "rbac", "incidents"],
        "included_files": [
            "slurm/slurm_state.json",
            "telemetry/telemetry_timeseries.parquet",
            "policy/rbac_policy.yaml",
            "incidents/incident_metadata.json",
            "docs/gpu_idle_policy.md",
        ],
        "implementation_status": "bundled",
        "validation_status": "validated",
        "description": (
            "gpu02 and gpu03 have been allocated to a job for 9 hours but GPU "
            "utilisation has been <2% for the past 6 hours. The nodes are drawing "
            "full power (~400W each) while GPUs idle. facility_admin must quantify "
            "the energy waste and determine if the job should be terminated."
        ),
    })

    _write_json(env / "slurm" / "slurm_state.json", {
        "cluster": "exabench-cluster-a",
        "snapshot_time": snap_time,
        "nodes": [
            {"name": "gpu01", "state": "allocated", "cpus": 64, "memory_mb": 512000, "partitions": ["gpu"]},
            {"name": "gpu02", "state": "allocated", "cpus": 64, "memory_mb": 512000, "partitions": ["gpu"]},
            {"name": "gpu03", "state": "allocated", "cpus": 64, "memory_mb": 512000, "partitions": ["gpu"]},
            {"name": "gpu04", "state": "idle",      "cpus": 64, "memory_mb": 512000, "partitions": ["gpu"]},
        ],
        "partitions": [
            {"name": "gpu", "max_time": "72:00:00", "max_mem_per_node_mb": 512000,
             "default_mem_per_cpu_mb": 4096},
        ],
        "jobs": [
            {"job_id": "932000", "job_name": "inference_batch", "user": "bob",
             "account": "ml-lab", "state": "RUNNING", "exit_code": None,
             "node": "gpu02,gpu03", "partition": "gpu",
             "submit_time": "2026-03-18T09:00:00Z", "start_time": "2026-03-18T09:05:00Z",
             "end_time": None, "elapsed": "08:55:00", "num_cpus": 128, "num_nodes": 2,
             "requested_mem_mb": 512000, "used_mem_mb": 50000,
             "oom_kill": False, "failure_reason": None},
        ],
    })

    snap_dt = datetime(2026, 3, 18, 18, 0, 0, tzinfo=UTC)
    df = make_telemetry(gpu_nodes, hours=9, snapshot_time=snap_dt, metrics={
        "gpu_util_pct": (85.0, 5.0, "%"),
        "power_w": (580.0, 10.0, "W"),
        "cpu_util_pct": (70.0, 8.0, "%"),
        "memory_util_pct": (60.0, 5.0, "%"),
    })
    # gpu02, gpu03: GPU utilisation drops to near zero after 3h
    idle_mask = (df["node_id"].isin(["gpu02", "gpu03"])) & \
                (df["metric_name"] == "gpu_util_pct") & \
                (df["timestamp"] >= snap_dt - timedelta(hours=6))
    df.loc[idle_mask, "value"] = 1.0
    _write_parquet(env / "telemetry" / "telemetry_timeseries.parquet", df)

    _write_yaml(env / "policy" / "rbac_policy.yaml", {
        "version": "1.0",
        "roles": {
            "facility_admin": {
                "description": "Full facility access",
                "permissions": [{"resource": "*", "actions": ["*"]}],
            },
        },
        "hard_fail_on_violation": True,
    })

    _write_json(env / "incidents" / "incident_metadata.json", {
        "incident_id": "INC-2026-0318-001",
        "severity": "medium",
        "title": "GPU idle for 6h while allocated — energy waste on gpu02/gpu03",
        "opened_at": "2026-03-18T15:00:00Z",
        "status": "open",
        "affected_resource": "gpu02,gpu03",
        "affected_job": "932000",
        "summary": (
            "Job 932000 has allocated gpu02 and gpu03 for 9 hours. "
            "GPU utilisation has been <2% for the past 6 hours. "
            "Each node draws ~400W idle. Estimated wasted energy: ~4.8 kWh (2 nodes × 400W × 6h). "
            "6 pending GPU jobs are queued behind this job."
        ),
        "timeline": [
            {"time": "2026-03-18T09:05:00Z", "event": "Job 932000 starts on gpu02, gpu03"},
            {"time": "2026-03-18T12:00:00Z", "event": "GPU util drops to <2% — batch complete, job hung"},
            {"time": "2026-03-18T15:00:00Z", "event": "Alert: GPU idle >3h on allocated nodes"},
            {"time": "2026-03-18T18:00:00Z", "event": "Snapshot captured — 6h idle, 4.8 kWh wasted"},
        ],
        "resolution": None,
        "notes": "Job appears hung. Contact user bob before cancellation. GPU idle timeout policy applies.",
    })

    _write_text(env / "docs" / "gpu_idle_policy.md", textwrap.dedent("""\
        # GPU Idle Policy

        ## Energy context
        - GPU nodes draw ~400W at idle (A100 80GB base power)
        - At cluster scale, idle GPUs represent significant avoidable cost
        - 1 idle GPU node for 24 hours = 9.6 kWh wasted

        ## Idle timeout policy
        - Warning to user: GPU util <10% for >2 hours (automated email)
        - Sysadmin review: GPU util <5% for >4 hours
        - Cancellation eligible: GPU util <2% for >6 hours, with user notification

        ## Facility_admin actions
        1. Query telemetry: `telemetry query_timeseries metric_name=gpu_util_pct`
        2. Identify nodes with sustained near-zero GPU util
        3. Contact user via helpdesk ticket before cancellation
        4. Cancel job if no response within 1 hour: `scancel <jobid>`

        ## Prevention
        - Submit jobs with `--time` limits appropriate to actual workload
        - Use `seff <jobid>` after completion to assess GPU efficiency
        - Consider job arrays instead of holding GPUs for batch processing
    """))


def build_env_20(root: Path) -> None:
    """multi_job_interference — I/O contention on shared Lustre."""
    env = root / "env_20"
    snap_time = "2026-03-19T14:00:00Z"
    nodes = [f"node{i:02d}" for i in range(1, 9)]

    _write_metadata(env, {
        "environment_id": "env_20",
        "snapshot_name": "Lustre IO Contention Multi-Job Interference",
        "scenario_type": "multi_job_interference",
        "cluster_name": "exabench-cluster-a",
        "snapshot_timestamp": snap_time,
        "bundle_root": "environments/env_20",
        "supported_roles": ["sysadmin"],
        "supported_categories": ["JOB", "MON"],
        "included_sources": ["slurm", "telemetry", "docs", "rbac", "incidents"],
        "included_files": [
            "slurm/slurm_state.json",
            "telemetry/telemetry_timeseries.parquet",
            "policy/rbac_policy.yaml",
            "incidents/incident_metadata.json",
            "docs/lustre_io_guide.md",
        ],
        "implementation_status": "bundled",
        "validation_status": "validated",
        "description": (
            "A large I/O-intensive checkpoint job on nodes 1–4 is saturating the "
            "Lustre filesystem, causing a science job on nodes 5–8 to stall with "
            "effective throughput <5% of normal. Sysadmin must identify the I/O "
            "offender and apply throttling or scheduling separation."
        ),
    })

    _write_json(env / "slurm" / "slurm_state.json", {
        "cluster": "exabench-cluster-a",
        "snapshot_time": snap_time,
        "nodes": [
            {"name": n, "state": "allocated", "cpus": 64, "memory_mb": 256000,
             "partitions": ["standard"]} for n in nodes
        ],
        "partitions": [
            {"name": "standard", "max_time": "48:00:00", "max_mem_per_node_mb": 256000,
             "default_mem_per_cpu_mb": 2048},
        ],
        "jobs": [
            {"job_id": "999001", "job_name": "checkpoint_dump", "user": "frank",
             "account": "ml-lab", "state": "RUNNING", "exit_code": None,
             "node": "node01,node02,node03,node04", "partition": "standard",
             "submit_time": "2026-03-19T13:00:00Z", "start_time": "2026-03-19T13:05:00Z",
             "end_time": None, "elapsed": "00:55:00", "num_cpus": 256, "num_nodes": 4,
             "requested_mem_mb": 65536, "used_mem_mb": 60000,
             "oom_kill": False, "failure_reason": None},
            {"job_id": "999002", "job_name": "climate_sim", "user": "carol",
             "account": "cfd-lab", "state": "RUNNING", "exit_code": None,
             "node": "node05,node06,node07,node08", "partition": "standard",
             "submit_time": "2026-03-19T12:00:00Z", "start_time": "2026-03-19T12:05:00Z",
             "end_time": None, "elapsed": "01:55:00", "num_cpus": 256, "num_nodes": 4,
             "requested_mem_mb": 65536, "used_mem_mb": 55000,
             "oom_kill": False, "failure_reason": None},
        ],
    })

    snap_dt = datetime(2026, 3, 19, 14, 0, 0, tzinfo=UTC)
    df = make_telemetry(nodes, hours=2, snapshot_time=snap_dt, metrics={
        "cpu_util_pct": (60.0, 8.0, "%"),
        "disk_write_mbps": (100.0, 20.0, "Mbps"),
        "disk_read_mbps": (80.0, 15.0, "Mbps"),
        "net_tx_mbps": (200.0, 30.0, "Mbps"),
        "memory_util_pct": (45.0, 5.0, "%"),
    })
    # node01–node04: massive I/O write throughput
    io_mask = (df["node_id"].isin(["node01", "node02", "node03", "node04"])) & \
              (df["metric_name"] == "disk_write_mbps") & \
              (df["timestamp"] >= snap_dt - timedelta(hours=1))
    df.loc[io_mask, "value"] = 800.0
    # node05–node08: CPU stalled (waiting for I/O), disk_read near zero
    stall_mask = (df["node_id"].isin(["node05", "node06", "node07", "node08"])) & \
                 (df["metric_name"] == "cpu_util_pct") & \
                 (df["timestamp"] >= snap_dt - timedelta(hours=1))
    df.loc[stall_mask, "value"] = 5.0
    _write_parquet(env / "telemetry" / "telemetry_timeseries.parquet", df)

    _write_yaml(env / "policy" / "rbac_policy.yaml", RBAC_SYSADMIN_FULL)

    _write_json(env / "incidents" / "incident_metadata.json", {
        "incident_id": "INC-2026-0319-003",
        "severity": "high",
        "title": "Lustre I/O saturation — climate_sim stalled by checkpoint_dump",
        "opened_at": "2026-03-19T13:30:00Z",
        "status": "open",
        "affected_resource": "lustre-fs",
        "affected_job": "999002",
        "summary": (
            "Job 999001 (checkpoint_dump) is writing at 800 MB/s per node (3.2 GB/s total) "
            "to the shared Lustre filesystem, saturating the OST bandwidth. "
            "Job 999002 (climate_sim) on nodes 5–8 has stalled — CPU util <5%, "
            "read throughput near zero. climate_sim is performing at <5% normal rate."
        ),
        "timeline": [
            {"time": "2026-03-19T12:05:00Z", "event": "Job 999002 (climate_sim) starts normally"},
            {"time": "2026-03-19T13:05:00Z", "event": "Job 999001 (checkpoint_dump) starts"},
            {"time": "2026-03-19T13:10:00Z", "event": "Lustre OST bandwidth saturated"},
            {"time": "2026-03-19T13:30:00Z", "event": "Alert: climate_sim CPU util drops to <5%"},
            {"time": "2026-03-19T14:00:00Z", "event": "Snapshot captured for benchmark"},
        ],
        "resolution": None,
        "notes": "Consider cancelling checkpoint_dump or applying lctl I/O throttle.",
    })

    _write_text(env / "docs" / "lustre_io_guide.md", textwrap.dedent("""\
        # Lustre I/O Troubleshooting Guide

        ## Lustre bandwidth limits
        - Aggregate OST write bandwidth: ~3.2 GB/s (4 OSTs × 800 MB/s)
        - If one job consumes all OST bandwidth, other jobs see near-zero I/O

        ## Identifying the I/O offender
        1. Query telemetry for `disk_write_mbps` across all nodes.
        2. High writers (>500 MB/s per node) are suspects.
        3. Correlate with SLURM job list to find the account and user.

        ## Throttling I/O on Lustre
        - Apply per-job I/O limit (if MDS jobstats enabled):
          `lctl set_param llite.*.max_dirty_mb=256`
        - Or cancel the offending job after notifying user.

        ## Scheduling I/O-heavy jobs
        - Submit checkpoint jobs during off-peak hours (nights/weekends).
        - Use `--exclusive` for I/O-intensive jobs to isolate them.
        - Consider separate I/O queue for checkpoint/backup workloads.
    """))


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def _write_metadata(env: Path, data: dict) -> None:
    (env).mkdir(parents=True, exist_ok=True)
    with (env / "metadata.yaml").open("w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str))


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)


def _write_parquet(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

BUILDERS = [
    build_env_06, build_env_07, build_env_08, build_env_09, build_env_10,
    build_env_11, build_env_12, build_env_13, build_env_14, build_env_15,
    build_env_16, build_env_17, build_env_18, build_env_19, build_env_20,
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate ExaBench snapshot bundles env_06–env_20")
    parser.add_argument(
        "--benchmark-root",
        default="benchmark",
        help="Path to the benchmark/ directory (default: benchmark/)",
    )
    args = parser.parse_args()

    envs_root = Path(args.benchmark_root) / "environments"
    envs_root.mkdir(parents=True, exist_ok=True)

    for builder in BUILDERS:
        env_name = builder.__name__  # e.g. build_env_06
        print(f"Generating {env_name[6:]}...", end=" ", flush=True)
        try:
            builder(envs_root)
            print("OK")
        except Exception as e:
            print(f"FAILED: {e}")
            raise

    print(f"\nGenerated {len(BUILDERS)} bundles in {envs_root}")


if __name__ == "__main__":
    main()
