#!/usr/bin/env python3
"""Phase 1 — build M100-grounded environment bundles (env_m100_*).

These bundles are *hybrid-grounded* in the real CINECA Marconi100 ExaData dataset:

  * **Schema/vocabulary** is M100-faithful — node names ``r{rack}n{slot}``, IPMI
    metric names (``total_power``, ``ambient``, ``gpu3_core_temp``, ``fanX_Y`` …),
    and an extra ``plugin`` column carrying the M100 plugin (``ipmi_pub`` …).
  * **Values** are sampled from *real* M100 distributions fit from a population of real
    nodes (see ``scripts/build_m100_reference.py`` →
    ``benchmark/environments/_m100_reference/metric_distributions.json``), so daily
    drift, noise, and cross-node baseline spread match real Marconi100 operation.
  * **Ground truth** stays authorable: each scenario overlays a controlled, *labeled*
    perturbation (a thermal hotspot, a power spike) whose exact location/magnitude/
    timing we know and encode in the task gold answers.

The output follows AOBench's canonical bundle layout and reuses the existing tools
unchanged — M100 telemetry lands in the canonical long-format parquet
(``timestamp, node_id, metric_name, value, unit`` + ``plugin``). Power is kept *inside
the parquet* (never a CSV ``power_w`` column) so the F4 fidelity check correctly skips.

Usage::

    uv run python scripts/build_m100_bundles.py [--benchmark-root benchmark/]
        [--dataset-path /path/to/full/m100/parquet]   # optional live-slice refinement

Determinism: a single numpy RNG seeded per environment makes the parquet byte-stable.
Provenance: CINECA Marconi100 ExaData dataset, doi:10.1038/s41597-023-02174-3.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import textwrap
import zlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

# Reuse the canonical bundle I/O helpers and RBAC policies from the existing generator.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_bundles import (
    RBAC_FACILITY,
    RBAC_SYSADMIN_FULL,
    _write_json,
    _write_metadata,
    _write_parquet,
    _write_text,
    _write_yaml,
)

UTC = timezone.utc
_REPO_ROOT = Path(__file__).resolve().parents[1]
_REFERENCE_JSON = _REPO_ROOT / "benchmark" / "environments" / "_m100_reference" / "metric_distributions.json"

# Set by main() from --real-baselines. When a directory of real per-node wide parquets
# (time_aggregated/) is given, each env node's baseline series is taken from a real M100
# node's real trace at the env's real timestamp, instead of sampled from distributions.
# Telemetry built this way is NOT reproducible offline (needs the dataset, on n1), so the
# committed/offline default remains the distribution-sampled path below.
_REAL_DIR: Path | None = None
_REAL_FILES: list[Path] | None = None
# When True, upward magnitude anomalies scale to each node's real baseline (for --real-baselines).
_RELATIVE_ANOMALIES: bool = False


# ---------------------------------------------------------------------------
# Reference distributions
# ---------------------------------------------------------------------------

def load_reference_distributions(path: Path = _REFERENCE_JSON) -> dict[str, dict]:
    """Load the committed per-metric M100 distribution parameters (offline)."""
    if not path.exists():
        raise FileNotFoundError(
            f"Missing M100 reference distributions: {path}\n"
            "Run: uv run python scripts/build_m100_reference.py"
        )
    return json.loads(path.read_text(encoding="utf-8"))["metrics"]


def maybe_load_live_slice(dataset_path: str | None) -> pd.DataFrame | None:
    """Optionally refine distributions from a real M100 parquet slice.

    Falls back silently (returns None) when the full dataset / query tool is absent,
    so the build always succeeds from repo contents alone.
    """
    if not dataset_path:
        print("  [data] using committed sample-derived distributions (no live dataset)")
        return None
    try:
        exadata_tool = _REPO_ROOT / ".." / "exadata" / "parquet_dataset" / "query_tool"
        sys.path.insert(0, str(exadata_tool.resolve()))
        from query_tool import M100DataClient  # type: ignore[import-not-found]

        client = M100DataClient(dataset_path)
        df = client.query("total_power", year_month="22-07", columns=["timestamp", "value", "node"])
        print(f"  [data] refined from live M100 slice: {len(df)} rows")
        return df
    except Exception as exc:  # noqa: BLE001 — optional path, never fatal
        print(f"  [data] live slice unavailable ({exc.__class__.__name__}); using sample distributions")
        return None


# ---------------------------------------------------------------------------
# Telemetry synthesis (long format, M100 vocabulary)
# ---------------------------------------------------------------------------

def _real_node_files() -> list[Path]:
    """Sorted list of real per-node wide parquets in --real-baselines (cached)."""
    global _REAL_FILES
    if _REAL_FILES is None:
        assert _REAL_DIR is not None
        _REAL_FILES = sorted(_REAL_DIR.glob("*.parquet"))
        if not _REAL_FILES:
            raise FileNotFoundError(f"No real node parquets in {_REAL_DIR}")
    return _REAL_FILES


def _synthesize_from_real(
    nodes: list[str],
    metrics: list[str],
    timestamps: list[datetime],
    dist: dict[str, dict],
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Build long-format telemetry from REAL per-node M100 traces.

    Each env node is mapped to a distinct real node; for each metric the real
    ``{metric}_avg`` series is sliced to the env's real time window and aligned to the
    env timestamps (nearest real sample). Metrics/nodes with no real coverage fall back
    to distribution sampling so the bundle is always complete.
    """
    ts_index = pd.to_datetime(pd.Series(timestamps), utc=True)
    lo_t, hi_t = ts_index.min(), ts_index.max()
    files = _real_node_files()
    # Deterministic distinct real node per env node.
    pick = rng.permutation(len(files))
    cols_needed = ["timestamp"] + [f"{m}_avg" for m in metrics]

    rows = []
    for i, node in enumerate(nodes):
        real_fp = files[pick[i % len(files)]]
        try:
            rdf = pd.read_parquet(real_fp, columns=[c for c in cols_needed])
        except Exception:  # noqa: BLE001 — some metric col may be absent for this node
            rdf = pd.read_parquet(real_fp)
        rdf = rdf[[c for c in rdf.columns if c in cols_needed]].copy()
        rdf["timestamp"] = pd.to_datetime(rdf["timestamp"], utc=True)
        rdf = rdf.sort_values("timestamp")
        win = rdf[(rdf["timestamp"] >= lo_t) & (rdf["timestamp"] <= hi_t)]
        for metric in metrics:
            params = dist.get(metric)
            if params is None:
                continue
            unit, plugin = params["unit"], params["plugin"]
            col = f"{metric}_avg"
            real_vals = None
            if col in win.columns:
                sub = win[["timestamp", col]].dropna()
                if len(sub) >= 2:
                    aligned = pd.merge_asof(
                        pd.DataFrame({"timestamp": ts_index}), sub,
                        on="timestamp", direction="nearest",
                    )
                    real_vals = aligned[col].to_numpy()
            if real_vals is None:
                # Fallback: distribution-sampled baseline for this (node, metric).
                base = min(max(params["mean"] + rng.normal(0.0, params.get("node_baseline_std", 0.0)),
                               params["lo"]), params["hi"])
                real_vals = [
                    min(max(base + rng.normal(0.0, max(params["within_window_std"], 1e-6)),
                            params["lo"]), params["hi"])
                    for _ in timestamps
                ]
            for ts, val in zip(timestamps, real_vals):
                rows.append({
                    "timestamp": ts, "node_id": node, "metric_name": metric,
                    "value": round(float(val), 2), "unit": unit, "plugin": plugin,
                })

    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    return df


def synthesize_node_telemetry(
    nodes: list[str],
    metrics: list[str],
    hours: float,
    snapshot_time: datetime,
    dist: dict[str, dict],
    rng: np.random.Generator,
    *,
    cadence_seconds: int = 300,
    drift_factor: float = 0.15,
) -> pd.DataFrame:
    """Generate long-format telemetry for M100-named nodes from real distributions.

    ``value(t) = clamp(mean + diurnal_drift(t) + gauss(0, within_window_std), lo, hi)``
    where the diurnal drift amplitude is a fraction of the real across-window std.
    """
    step = timedelta(seconds=cadence_seconds)
    start = snapshot_time - timedelta(hours=hours)
    timestamps: list[datetime] = []
    t = start
    while t <= snapshot_time:
        timestamps.append(t)
        t += step

    # Real-baseline mode: each env node gets a distinct real M100 node's real trace.
    if _REAL_DIR is not None:
        return _synthesize_from_real(nodes, metrics, timestamps, dist, rng)

    rows = []
    for metric in metrics:
        params = dist.get(metric)
        if params is None:
            print(f"  [warn] metric '{metric}' not in reference; skipping")
            continue
        mean = params["mean"]
        within = max(params["within_window_std"], 1e-6)
        drift_amp = drift_factor * params["across_window_std"]
        # Real cross-node baseline spread (population reference only); 0 for single-node.
        node_spread = params.get("node_baseline_std", 0.0)
        lo, hi = params["lo"], params["hi"]
        unit = params["unit"]
        plugin = params["plugin"]
        # Per-node phase offset (decorrelates nodes) and a per-node baseline offset
        # drawn from the real cross-node spread, so each env node looks like a distinct
        # real M100 node rather than a copy of the population mean.
        for node in nodes:
            phase = rng.uniform(0, 2 * math.pi)
            node_baseline = mean + rng.normal(0.0, node_spread)
            node_baseline = min(max(node_baseline, lo), hi)
            for ts in timestamps:
                hrs = (ts - start).total_seconds() / 3600.0
                drift = drift_amp * math.sin(2 * math.pi * hrs / 24.0 + phase)
                value = node_baseline + drift + rng.normal(0.0, within)
                value = min(max(value, lo), hi)
                rows.append({
                    "timestamp": ts,
                    "node_id": node,
                    "metric_name": metric,
                    "value": round(float(value), 2),
                    "unit": unit,
                    "plugin": plugin,
                })

    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    return df


def apply_ramp(
    df: pd.DataFrame, node: str, metric: str, snapshot_time: datetime,
    window_hours: float, start_value: float, end_value: float,
) -> pd.DataFrame:
    """Overlay a linear ramp on (node, metric) over the last ``window_hours``."""
    t0 = pd.Timestamp(snapshot_time) - pd.Timedelta(hours=window_hours)
    mask = (df["node_id"] == node) & (df["metric_name"] == metric) & (df["timestamp"] >= t0)
    idxs = df[mask].index
    if len(idxs) == 0:
        return df
    span = (df.loc[idxs, "timestamp"] - t0).dt.total_seconds() / (window_hours * 3600.0)
    df.loc[idxs, "value"] = (start_value + (end_value - start_value) * span).round(2)
    return df


def apply_step(
    df: pd.DataFrame, node: str, metric: str, snapshot_time: datetime,
    window_hours: float, value: float,
) -> pd.DataFrame:
    """Overlay a sustained step (constant ``value``) on (node, metric) for last window."""
    t0 = pd.Timestamp(snapshot_time) - pd.Timedelta(hours=window_hours)
    mask = (df["node_id"] == node) & (df["metric_name"] == metric) & (df["timestamp"] >= t0)
    df.loc[mask, "value"] = round(value, 2)
    return df


def apply_magnitude_anomaly(
    df: pd.DataFrame, node: str, metric: str, snapshot_time: datetime,
    window_hours: float, absolute: float, factor: float,
) -> pd.DataFrame:
    """Apply an upward magnitude anomaly, absolute or relative to the node's real baseline.

    In the default (distribution-sampled) build this is the fixed ``absolute`` value, so the
    canonical bundles are byte-identical. With ``--relative-anomalies`` (recommended alongside
    ``--real-baselines``), the target is ``factor × the node's pre-window median`` — so the
    anomaly stays clearly separated from the real, noisy peer load instead of being a fixed
    level a busy real node might approach.
    """
    if not _RELATIVE_ANOMALIES:
        return apply_step(df, node, metric, snapshot_time, window_hours, absolute)
    t0 = pd.Timestamp(snapshot_time) - pd.Timedelta(hours=window_hours)
    pre = df[(df["node_id"] == node) & (df["metric_name"] == metric) & (df["timestamp"] < t0)]
    base = float(pre["value"].median()) if not pre.empty else absolute / max(factor, 1e-6)
    return apply_step(df, node, metric, snapshot_time, window_hours, max(absolute, factor * base))


def drop_node_after(
    df: pd.DataFrame, node: str, snapshot_time: datetime, window_hours: float,
) -> pd.DataFrame:
    """Remove all telemetry for ``node`` after T0 (simulates a node going dark)."""
    t0 = pd.Timestamp(snapshot_time) - pd.Timedelta(hours=window_hours)
    mask = (df["node_id"] == node) & (df["timestamp"] >= t0)
    return df[~mask].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Shared M100 SLURM helpers
# ---------------------------------------------------------------------------

# Real M100 job pool (committed); populated by load_real_jobs() when --real-jobs is on.
_REAL_JOBS: list[dict] = []
_REAL_JOBS_JSON = (
    _REPO_ROOT / "benchmark" / "environments" / "_m100_reference" / "real_jobs.json"
)


def load_real_jobs(path: Path = _REAL_JOBS_JSON) -> list[dict]:
    """Load the committed pool of real M100 job records (empty list if absent)."""
    if not path.exists():
        print(f"  [jobs] real job pool not found at {path}; using synthetic jobs only")
        return []
    return json.loads(path.read_text(encoding="utf-8")).get("jobs", [])


def real_background_jobs(nodes: list[str], snap_time: str, n: int,
                         exclude_ids: tuple[str, ...] = ()) -> list[dict]:
    """Pick ``n`` real M100 job records as background queue context for these nodes.

    Deterministic per env (seeded from snap_time). Real records ground partition/qos/user/
    runtime/terminal-state in actual M100 data; nodes are assigned from the env topology.
    ``exclude_ids`` skips records already used as scenario anchors (avoids duplicate job_ids).
    """
    if not _REAL_JOBS or n <= 0:
        return []
    rng = np.random.default_rng(zlib.crc32(snap_time.encode()))
    excl = set(exclude_ids)
    out = []
    for ix in rng.permutation(len(_REAL_JOBS)):
        if len(out) >= n:
            break
        r = _REAL_JOBS[int(ix)]
        if r["job_id"] in excl:
            continue
        node = nodes[len(out) % len(nodes)]
        out.append({
            "job_id": r["job_id"],
            "user": r.get("user_id") or "0",
            "state": r.get("state") or r["job_state"],
            "partition": "m100_usr_prod",
            "node": node,
            "nodes": [node],
            "num_cpus": r.get("num_cpus"),
            "num_nodes": r.get("num_nodes") or 1,
            "elapsed": r.get("elapsed"),
            "qos": str(r.get("qos")) if r.get("qos") is not None else None,
            "job_state": r["job_state"],
            "time_limit": r.get("time_limit"),
            "state_reason": r.get("state_reason"),
            "derived_ec": r.get("derived_ec"),
        })
    return out


def m100_slurm_state(cluster: str, snap_time: str, nodes: list[str], jobs: list[dict],
                     n_background: int = 4) -> dict:
    """Build a SlurmState dict in M100 vocabulary (kept <8 jobs so F1–F3 skip).

    When the real job pool is loaded, ``n_background`` real M100 job records are appended as
    queue context (after the scenario jobs), grounding the queue in real job characteristics.
    """
    anchor_ids = tuple(j["job_id"] for j in jobs)
    all_jobs = list(jobs) + real_background_jobs(nodes, snap_time, n_background, anchor_ids)
    return {
        "cluster": cluster,
        "snapshot_time": snap_time,
        "nodes": [
            {"name": n, "state": "allocated", "cpus": 128, "memory_mb": 262144,
             "partitions": ["m100_usr_prod"]} for n in nodes
        ],
        "partitions": [
            {"name": "m100_usr_prod", "max_time": "24:00:00",
             "max_mem_per_node_mb": 262144, "default_mem_per_cpu_mb": 7600},
        ],
        "jobs": all_jobs,
    }


def m100_job(job_id: str, user_id: int, node: str, snap_time: str, **extra) -> dict:
    """One M100-vocabulary job record. Mirrors canonical fields for tools/fidelity."""
    job = {
        "job_id": job_id,
        "user": str(user_id),          # canonical (M100 user_id is an anonymized int)
        "state": "RUNNING",            # canonical, mirrors job_state
        "partition": "m100_usr_prod",
        "node": node,
        "num_cpus": 128,
        "num_nodes": 1,
        # M100 vocabulary fields
        "qos": "normal",
        "job_state": "RUNNING",
        "nodes": [node],
        "submit_time": snap_time,
        "start_time": snap_time,
        "time_limit": "24:00:00",
        "min_memory_node": 262144,
        "priority": 100000,
    }
    job.update(extra)
    return job


PROVENANCE_BASE = {
    "data_source": "CINECA Marconi100 ExaData (time_aggregated population, 120 real nodes)",
    "grounding": "hybrid",
    "citation": "Borghesi, A. et al. (2023) M100 ExaData: a data collection campaign on the CINECA's Marconi100 Tier-0 supercomputer. Scientific Data 10(1):288. https://doi.org/10.1038/s41597-023-02174-3",
    "data_source_url": "https://doi.org/10.1038/s41597-023-02174-3",
    "schema": "M100 ipmi_pub metric vocabulary in canonical long-format telemetry",
    "baselines": "per-node baselines drawn from real cross-node population spread (node_baseline_std)",
}


# ---------------------------------------------------------------------------
# env_m100_01 — GPU thermal hotspot / throttling
# ---------------------------------------------------------------------------

def build_env_m100_01(root: Path, dist: dict) -> None:
    env = root / "env_m100_01"
    seed = 388
    rng = np.random.default_rng(seed)
    snap_time = "2022-07-15T14:00:00Z"
    snap_dt = datetime(2022, 7, 15, 14, 0, 0, tzinfo=UTC)
    rack = 3
    nodes = [f"r{rack}n{i}" for i in range(8)]            # r3n0 .. r3n7
    hot_node = "r3n7"
    metrics = [
        "gpu0_core_temp", "gpu1_core_temp", "gpu3_core_temp", "gpu4_core_temp",
        "gpu0_mem_temp", "gpu3_mem_temp", "ambient", "total_power",
        "fan0_0", "fan1_0", "p0_power", "p1_power",
    ]

    _write_metadata(env, {
        "environment_id": "env_m100_01",
        "snapshot_name": "M100 GPU Thermal Hotspot",
        "scenario_type": "node_degradation",
        "cluster_name": "marconi100",
        "snapshot_timestamp": snap_time,
        "bundle_root": "environments/env_m100_01",
        "supported_roles": ["sysadmin", "scientific_user"],
        "supported_categories": ["MON"],
        "included_sources": ["slurm", "telemetry", "docs", "rbac", "incidents"],
        "included_files": [
            "slurm/slurm_state.json",
            "telemetry/telemetry_timeseries.parquet",
            "policy/rbac_policy.yaml",
            "incidents/incident_metadata.json",
            "docs/gpu_thermal_runbook.md",
            "provenance.json",
        ],
        "implementation_status": "bundled",
        "validation_status": "validated",
        "description": (
            "Real-M100-grounded snapshot (ipmi_pub telemetry). GPU3 on node r3n7 is "
            "overheating: gpu3_core_temp ramps from ~45°C to ~88°C over the final 90 "
            "minutes, crossing the 84°C throttle threshold, while peer nodes stay "
            "34–41°C. Sysadmin must identify the degraded node and GPU."
        ),
    })

    jobs = [
        m100_job("7421033", 5012, hot_node, snap_time, job_name="dl_train",
                 start_time="2022-07-15T09:00:00Z", elapsed="05:00:00", run_time=18000),
        m100_job("7421034", 5012, "r3n2", snap_time, job_name="dl_train",
                 start_time="2022-07-15T09:00:00Z", elapsed="05:00:00", run_time=18000),
    ]
    _write_json(env / "slurm" / "slurm_state.json",
                m100_slurm_state("marconi100", snap_time, nodes, jobs))

    df = synthesize_node_telemetry(nodes, metrics, hours=6, snapshot_time=snap_dt,
                                   dist=dist, rng=rng)
    # Labeled perturbation: GPU3 thermal ramp on r3n7 over the final 1.5h.
    df = apply_ramp(df, hot_node, "gpu3_core_temp", snap_dt, 1.5, 45.0, 88.0)
    # Fans on the hot node spin up in response over the same window.
    df = apply_ramp(df, hot_node, "fan0_0", snap_dt, 1.5, 4400.0, 6500.0)
    df = apply_ramp(df, hot_node, "fan1_0", snap_dt, 1.5, 4400.0, 6500.0)
    _write_parquet(env / "telemetry" / "telemetry_timeseries.parquet", df)

    _write_yaml(env / "policy" / "rbac_policy.yaml", RBAC_SYSADMIN_FULL)

    _write_json(env / "incidents" / "incident_metadata.json", {
        "incident_id": "INC-M100-0715-001",
        "severity": "high",
        "title": "GPU3 thermal hotspot on r3n7 (ipmi gpu3_core_temp → 88°C)",
        "opened_at": "2022-07-15T13:30:00Z",
        "status": "open",
        "affected_resource": "r3n7",
        "affected_job": "7421033",
        "summary": (
            "IPMI gpu3_core_temp on node r3n7 rose from ~45°C to ~88°C over 90 minutes, "
            "crossing the 84°C throttle threshold at ~13:30 UTC. Peer GPUs on r3n0–r3n6 "
            "remain 34–41°C. Node fans (fan0_0, fan1_0) ramped to ~6500 RPM."
        ),
        "timeline": [
            {"time": "2022-07-15T12:30:00Z", "event": "gpu3_core_temp begins rising on r3n7"},
            {"time": "2022-07-15T13:30:00Z", "event": "84°C throttle threshold crossed"},
            {"time": "2022-07-15T14:00:00Z", "event": "Snapshot captured — gpu3_core_temp ~88°C"},
        ],
        "resolution": None,
        "notes": "Drain r3n7 and inspect GPU3 cooling path / thermal paste.",
    })

    _write_text(env / "docs" / "gpu_thermal_runbook.md", textwrap.dedent("""\
        # Marconi100 GPU Thermal Runbook

        ## IPMI thermal metrics (ipmi_pub plugin)
        - `gpuN_core_temp` — GPU N core temperature (°C); N ∈ {0, 1, 3, 4}
        - `gpuN_mem_temp`  — GPU N HBM2 memory temperature (°C)
        - `ambient`        — node inlet temperature (°C)
        - `fanX_Y`         — chassis fan speed (RPM)

        ## Normal ranges (per real M100 telemetry)
        - GPU core temp: 30–70°C under load
        - Throttle threshold: 84°C (Volta GV100 thermal slowdown)
        - Critical: 90°C

        ## Response
        1. Query telemetry for `gpuN_core_temp` across the rack.
        2. The node whose GPU exceeds 84°C while peers stay <70°C is the hotspot.
        3. Drain the node: `scontrol update nodename=<node> state=drain reason=thermal`.
        4. Inspect the GPU cooling path; check `fanX_Y` saturation as a corroborating signal.
    """))

    _write_json(env / "provenance.json", {**PROVENANCE_BASE, "m100_seed": seed,
                "scenario": "gpu_thermal_hotspot", "perturbation":
                "ramp gpu3_core_temp on r3n7 45→88°C over final 1.5h"})


# ---------------------------------------------------------------------------
# env_m100_02 — node power anomaly
# ---------------------------------------------------------------------------

def build_env_m100_02(root: Path, dist: dict) -> None:
    env = root / "env_m100_02"
    seed = 1004
    rng = np.random.default_rng(seed)
    snap_time = "2022-07-20T11:00:00Z"
    snap_dt = datetime(2022, 7, 20, 11, 0, 0, tzinfo=UTC)
    rack = 10
    nodes = [f"r{rack}n{i}" for i in range(8)]            # r10n0 .. r10n7
    spike_node = "r10n4"
    metrics = [
        "total_power", "ps0_input_power", "ps1_input_power",
        "p0_power", "p1_power", "ambient",
    ]

    _write_metadata(env, {
        "environment_id": "env_m100_02",
        "snapshot_name": "M100 Node Power Anomaly",
        "scenario_type": "energy_anomaly",
        "cluster_name": "marconi100",
        "snapshot_timestamp": snap_time,
        "bundle_root": "environments/env_m100_02",
        "supported_roles": ["sysadmin", "facility_admin"],
        "supported_categories": ["ENERGY", "MON"],
        "included_sources": ["slurm", "telemetry", "docs", "rbac", "incidents"],
        "included_files": [
            "slurm/slurm_state.json",
            "telemetry/telemetry_timeseries.parquet",
            "policy/rbac_policy.yaml",
            "incidents/incident_metadata.json",
            "docs/node_power_policy.md",
            "provenance.json",
        ],
        "implementation_status": "bundled",
        "validation_status": "validated",
        "description": (
            "Real-M100-grounded snapshot (ipmi_pub telemetry). Node r10n4 total_power "
            "spikes to ~1400W (sustained 30 min) versus the ~644W rack baseline, with a "
            "corresponding rise in ps0/ps1 input power. Sysadmin/facility_admin must "
            "identify the offending node and quantify the overshoot."
        ),
    })

    jobs = [
        m100_job("7558120", 6221, spike_node, snap_time, job_name="cfd_solver",
                 start_time="2022-07-20T08:00:00Z", elapsed="03:00:00", run_time=10800),
        m100_job("7558121", 6221, "r10n1", snap_time, job_name="cfd_solver",
                 start_time="2022-07-20T08:00:00Z", elapsed="03:00:00", run_time=10800),
    ]
    _write_json(env / "slurm" / "slurm_state.json",
                m100_slurm_state("marconi100", snap_time, nodes, jobs))

    df = synthesize_node_telemetry(nodes, metrics, hours=4, snapshot_time=snap_dt,
                                   dist=dist, rng=rng)
    # Labeled perturbation: total_power spike on r10n4 (sustained, last 0.5h). Relative in
    # real-baseline mode (2.4× the node's real draw) so it stands out above noisy real peers.
    df = apply_magnitude_anomaly(df, spike_node, "total_power", snap_dt, 0.5, 1400.0, 2.4)
    # Power supplies carry the extra draw (~700W each input).
    df = apply_magnitude_anomaly(df, spike_node, "ps0_input_power", snap_dt, 0.5, 740.0, 2.0)
    df = apply_magnitude_anomaly(df, spike_node, "ps1_input_power", snap_dt, 0.5, 735.0, 2.0)
    _write_parquet(env / "telemetry" / "telemetry_timeseries.parquet", df)

    _write_yaml(env / "policy" / "rbac_policy.yaml", RBAC_FACILITY)

    _write_json(env / "incidents" / "incident_metadata.json", {
        "incident_id": "INC-M100-0720-001",
        "severity": "high",
        "title": "Node power anomaly on r10n4 (total_power ~1400W)",
        "opened_at": "2022-07-20T10:30:00Z",
        "status": "open",
        "affected_resource": "r10n4",
        "affected_job": "7558120",
        "summary": (
            "IPMI total_power on r10n4 spiked to ~1400W, sustained for ~30 minutes, "
            "versus a ~644W rack-10 baseline (~117% over baseline). Power-supply input "
            "(ps0_input_power, ps1_input_power) rose to ~740W each."
        ),
        "timeline": [
            {"time": "2022-07-20T10:30:00Z", "event": "total_power on r10n4 jumps to ~1400W"},
            {"time": "2022-07-20T11:00:00Z", "event": "Snapshot captured — spike sustained"},
        ],
        "resolution": None,
        "notes": "Correlate with job 7558120 (cfd_solver). Consider per-node power cap.",
    })

    _write_text(env / "docs" / "node_power_policy.md", textwrap.dedent("""\
        # Marconi100 Node Power Policy

        ## IPMI power metrics (ipmi_pub plugin)
        - `total_power`       — whole-node power draw (W)
        - `psN_input_power`   — power-supply N input power (W)
        - `pN_power`          — CPU socket N package power (W)

        ## Reference levels (per real M100 telemetry)
        - Typical node draw: ~640W (idle/moderate), up to ~1820W at full GPU load
        - Sustained per-node alert threshold: 1300W
        - A single node >> rack median for >15 min indicates a power anomaly

        ## Response
        1. Query telemetry for `total_power` across the rack; rank nodes by recent mean.
        2. Flag any node whose sustained draw exceeds the rack baseline by >100%.
        3. Cross-check `psN_input_power` to confirm it is real draw, not a sensor fault.
        4. Correlate with the running job; apply a power cap or reschedule.
    """))

    _write_json(env / "provenance.json", {**PROVENANCE_BASE, "m100_seed": seed,
                "scenario": "node_power_anomaly", "perturbation":
                "step total_power on r10n4 to 1400W for final 0.5h"})


# ---------------------------------------------------------------------------
# env_m100_03 — rack cooling fault (rack-wide ambient rise)
# ---------------------------------------------------------------------------

def build_env_m100_03(root: Path, dist: dict) -> None:
    env = root / "env_m100_03"
    seed = 404
    rng = np.random.default_rng(seed)
    snap_time = "2022-08-02T15:00:00Z"
    snap_dt = datetime(2022, 8, 2, 15, 0, 0, tzinfo=UTC)
    rack = 4
    nodes = [f"r{rack}n{i}" for i in range(8)]
    metrics = ["ambient", "Supply_Air_Temperature", "Return_Air_Temperature",
               "total_power", "gpu0_core_temp", "gpu3_core_temp", "fan0_0", "fan1_0"]

    _write_metadata(env, {
        "environment_id": "env_m100_03",
        "snapshot_name": "M100 Rack Cooling Fault",
        "scenario_type": "energy_anomaly",
        "cluster_name": "marconi100",
        "snapshot_timestamp": snap_time,
        "bundle_root": "environments/env_m100_03",
        "supported_roles": ["facility_admin", "sysadmin"],
        "supported_categories": ["ENERGY", "MON"],
        "included_sources": ["slurm", "telemetry", "docs", "rbac", "incidents"],
        "included_files": [
            "slurm/slurm_state.json",
            "telemetry/telemetry_timeseries.parquet",
            "policy/rbac_policy.yaml",
            "incidents/incident_metadata.json",
            "docs/cooling_runbook.md",
            "provenance.json",
        ],
        "implementation_status": "bundled",
        "validation_status": "validated",
        "description": (
            "Real-M100-grounded snapshot (ipmi_pub + vertiv_pub telemetry). A cooling fault "
            "affects ALL of rack 4: the CRAC Supply_Air_Temperature climbs ~18→30°C, driving "
            "inlet temperature (ambient) on every node from ~22°C to ~33°C over the final 2 "
            "hours (vs a single-node hotspot). facility_admin must recognise the rack-wide "
            "signature and attribute it to the cooling unit, not a node."
        ),
    })

    jobs = [
        m100_job("7689210", 7001, "r4n0", snap_time, job_name="weather_sim",
                 start_time="2022-08-02T09:00:00Z", elapsed="06:00:00", run_time=21600),
        m100_job("7689211", 7001, "r4n3", snap_time, job_name="weather_sim",
                 start_time="2022-08-02T09:00:00Z", elapsed="06:00:00", run_time=21600),
    ]
    _write_json(env / "slurm" / "slurm_state.json",
                m100_slurm_state("marconi100", snap_time, nodes, jobs))

    df = synthesize_node_telemetry(nodes, metrics, hours=5, snapshot_time=snap_dt,
                                   dist=dist, rng=rng)
    # Labeled perturbation: the CRAC supply air (vertiv Supply_Air_Temperature) climbs from
    # ~18°C to ~30°C over the final 2h, driving a rack-wide inlet (ambient) rise on every node.
    for i, node in enumerate(nodes):
        df = apply_ramp(df, node, "Supply_Air_Temperature", snap_dt, 2.0, 18.0, 30.0)
        df = apply_ramp(df, node, "ambient", snap_dt, 2.0, 22.0, 31.5 + 0.4 * (i % 4))
    _write_parquet(env / "telemetry" / "telemetry_timeseries.parquet", df)

    _write_yaml(env / "policy" / "rbac_policy.yaml", RBAC_FACILITY)

    _write_json(env / "incidents" / "incident_metadata.json", {
        "incident_id": "INC-M100-0802-001",
        "severity": "high",
        "title": "Rack-4 cooling fault — ambient rising across all nodes",
        "opened_at": "2022-08-02T14:20:00Z",
        "status": "open",
        "affected_resource": "rack-4",
        "affected_job": None,
        "summary": (
            "The vertiv CRAC Supply_Air_Temperature feeding rack 4 climbed from ~18°C to "
            "~30°C, and IPMI ambient (inlet) on every rack-4 node (r4n0–r4n7) rose from ~22°C "
            "to ~32°C over 2 hours — a rack-wide signature of a cooling (CRAC) fault rather "
            "than a single-node issue. Fans ramped up."
        ),
        "timeline": [
            {"time": "2022-08-02T13:00:00Z", "event": "ambient starts rising across rack 4"},
            {"time": "2022-08-02T14:20:00Z", "event": "rack-4 inlet temps exceed 28°C warning"},
            {"time": "2022-08-02T15:00:00Z", "event": "Snapshot captured — ambient ~32°C rack-wide"},
        ],
        "resolution": None,
        "notes": "Check the cooling unit serving rack 4; ambient rising on ALL nodes rules out per-node fault.",
    })

    _write_text(env / "docs" / "cooling_runbook.md", textwrap.dedent("""\
        # Marconi100 Cooling Runbook

        ## Metrics
        - `ambient` (ipmi) — node inlet (intake) air temperature (°C)
        - `Supply_Air_Temperature` (vertiv) — CRAC supply (cold) air temperature (°C)
        - `Return_Air_Temperature` (vertiv) — CRAC return (warm) air temperature (°C)

        ## Normal ranges (per real M100 telemetry)
        - Inlet (ambient): 18–26°C
        - Warning: >28°C
        - Critical: >32°C

        ## Single-node vs rack-wide
        - ONE node's ambient rising → node-local airflow blockage; drain that node.
        - ALL nodes in a rack rising together → cooling-unit fault feeding that rack.
          Escalate to facilities; do not drain individual nodes.

        ## Response (rack-wide)
        1. Confirm `ambient` is elevated across the whole rack, not one node.
        2. Check the cooling unit / liquid loop serving that rack.
        3. Reduce rack load if inlet approaches 32°C while cooling is restored.
    """))

    _write_json(env / "provenance.json", {**PROVENANCE_BASE, "m100_seed": seed,
                "scenario": "rack_cooling_fault",
                "perturbation": "ramp ambient on all r4 nodes 22→~32°C over final 2h"})


# ---------------------------------------------------------------------------
# env_m100_04 — node-down detection (telemetry goes dark)
# ---------------------------------------------------------------------------

def build_env_m100_04(root: Path, dist: dict) -> None:
    env = root / "env_m100_04"
    seed = 702
    rng = np.random.default_rng(seed)
    snap_time = "2022-08-10T12:00:00Z"
    snap_dt = datetime(2022, 8, 10, 12, 0, 0, tzinfo=UTC)
    rack = 7
    nodes = [f"r{rack}n{i}" for i in range(8)]
    down_node = "r7n2"
    metrics = ["total_power", "ambient", "p0_power", "gpu0_core_temp"]

    _write_metadata(env, {
        "environment_id": "env_m100_04",
        "snapshot_name": "M100 Node Down",
        "scenario_type": "incident_response",
        "cluster_name": "marconi100",
        "snapshot_timestamp": snap_time,
        "bundle_root": "environments/env_m100_04",
        "supported_roles": ["sysadmin", "scientific_user"],
        "supported_categories": ["MON"],
        "included_sources": ["slurm", "telemetry", "docs", "rbac", "incidents"],
        "included_files": [
            "slurm/slurm_state.json",
            "telemetry/telemetry_timeseries.parquet",
            "policy/rbac_policy.yaml",
            "incidents/incident_metadata.json",
            "docs/node_down_runbook.md",
            "provenance.json",
        ],
        "implementation_status": "bundled",
        "validation_status": "validated",
        "description": (
            "Real-M100-grounded snapshot (ipmi_pub telemetry). Node r7n2 went dark at "
            "~10:45 UTC: all of its IPMI telemetry stops after that point while peers keep "
            "reporting, and SLURM marks r7n2 'down'. Sysadmin must identify the unreachable "
            "node and the time it stopped reporting."
        ),
    })

    nodes_state = [
        {"name": n, "state": ("down" if n == down_node else "allocated"),
         "cpus": 128, "memory_mb": 262144, "partitions": ["m100_usr_prod"]}
        for n in nodes
    ]
    jobs = [
        m100_job("7731050", 8110, "r7n0", snap_time, job_name="md_run",
                 start_time="2022-08-10T08:00:00Z", elapsed="04:00:00", run_time=14400),
    ]
    _write_json(env / "slurm" / "slurm_state.json", {
        "cluster": "marconi100",
        "snapshot_time": snap_time,
        "nodes": nodes_state,
        "partitions": [
            {"name": "m100_usr_prod", "max_time": "24:00:00",
             "max_mem_per_node_mb": 262144, "default_mem_per_cpu_mb": 7600},
        ],
        "jobs": jobs + real_background_jobs(nodes, snap_time, 4,
                                            tuple(j["job_id"] for j in jobs)),
    })

    df = synthesize_node_telemetry(nodes, metrics, hours=4, snapshot_time=snap_dt,
                                   dist=dist, rng=rng)
    # Labeled perturbation: r7n2 telemetry stops 1h15m before the snapshot.
    df = drop_node_after(df, down_node, snap_dt, 1.25)
    _write_parquet(env / "telemetry" / "telemetry_timeseries.parquet", df)

    _write_yaml(env / "policy" / "rbac_policy.yaml", RBAC_SYSADMIN_FULL)

    _write_json(env / "incidents" / "incident_metadata.json", {
        "incident_id": "INC-M100-0810-001",
        "severity": "high",
        "title": "Node r7n2 unreachable — telemetry stopped, SLURM down",
        "opened_at": "2022-08-10T10:50:00Z",
        "status": "open",
        "affected_resource": "r7n2",
        "affected_job": None,
        "summary": (
            "Node r7n2 stopped reporting all IPMI telemetry at ~10:45 UTC and SLURM marks "
            "it 'down'. Peer nodes r7n0–r7n7 continue reporting normally. The node is "
            "unreachable and any jobs on it require rescheduling."
        ),
        "timeline": [
            {"time": "2022-08-10T10:45:00Z", "event": "r7n2 telemetry stops"},
            {"time": "2022-08-10T10:50:00Z", "event": "SLURM marks r7n2 down"},
            {"time": "2022-08-10T12:00:00Z", "event": "Snapshot captured — r7n2 still dark"},
        ],
        "resolution": None,
        "notes": "Power-cycle r7n2 via BMC; check IB link and BMC reachability.",
    })

    _write_text(env / "docs" / "node_down_runbook.md", textwrap.dedent("""\
        # Marconi100 Node-Down Runbook

        ## Detecting an unreachable node
        - A live node emits IPMI telemetry continuously (cadence ~minutes).
        - A node with NO recent telemetry while peers keep reporting is likely down.
        - Cross-check the SLURM node state: 'down' / 'drain' confirms it.

        ## Response
        1. Query telemetry per node; find the node with no samples after some T0.
        2. Confirm with `sinfo -N` / SLURM node state.
        3. Reschedule affected jobs off the node.
        4. Power-cycle via BMC (`ipmitool -H <bmc> power cycle`); check the IB link.
    """))

    _write_json(env / "provenance.json", {**PROVENANCE_BASE, "m100_seed": seed,
                "scenario": "node_down",
                "perturbation": "drop all r7n2 telemetry after T0 (last 1.25h); SLURM state=down"})


# ---------------------------------------------------------------------------
# env_m100_05 — job failure ↔ telemetry correlation
# ---------------------------------------------------------------------------

def build_env_m100_05(root: Path, dist: dict) -> None:
    env = root / "env_m100_05"
    seed = 255
    rng = np.random.default_rng(seed)
    snap_time = "2022-08-18T16:00:00Z"
    snap_dt = datetime(2022, 8, 18, 16, 0, 0, tzinfo=UTC)
    rack = 2
    nodes = [f"r{rack}n{i}" for i in range(8)]
    fail_node = "r2n5"
    metrics = ["total_power", "p0_power", "p1_power", "ambient", "gpu0_core_temp"]

    _write_metadata(env, {
        "environment_id": "env_m100_05",
        "snapshot_name": "M100 Job Failure Correlation",
        "scenario_type": "job_failure",
        "cluster_name": "marconi100",
        "snapshot_timestamp": snap_time,
        "bundle_root": "environments/env_m100_05",
        "supported_roles": ["scientific_user", "sysadmin"],
        "supported_categories": ["JOB", "MON"],
        "included_sources": ["slurm", "telemetry", "docs", "rbac", "incidents"],
        "included_files": [
            "slurm/slurm_state.json",
            "telemetry/telemetry_timeseries.parquet",
            "policy/rbac_policy.yaml",
            "incidents/incident_metadata.json",
            "docs/job_failure_runbook.md",
            "provenance.json",
        ],
        "implementation_status": "bundled",
        "validation_status": "validated",
        "description": (
            "Real-M100-grounded snapshot (ipmi_pub telemetry). Job 7798450 on node r2n5 "
            "FAILED at ~15:30 UTC; the node's total_power and CPU package power (p0_power, "
            "p1_power) collapse to near-idle at that moment as the process dies. The agent "
            "must correlate the failed SLURM job with the telemetry drop."
        ),
    })

    fail_job = m100_job(
        "7798450", 9120, fail_node, snap_time, job_name="qmc_solver",
        start_time="2022-08-18T11:00:00Z", end_time="2022-08-18T15:30:00Z",
        elapsed="04:30:00", run_time=16200, state="FAILED", job_state="FAILED",
        exit_code="1:0", derived_ec="1:0", state_reason="JobLaunchFailure",
    )
    other_job = m100_job("7798451", 9120, "r2n1", snap_time, job_name="qmc_solver",
                         start_time="2022-08-18T11:00:00Z", elapsed="05:00:00", run_time=18000)
    _write_json(env / "slurm" / "slurm_state.json",
                m100_slurm_state("marconi100", snap_time, nodes, [fail_job, other_job]))

    df = synthesize_node_telemetry(nodes, metrics, hours=4, snapshot_time=snap_dt,
                                   dist=dist, rng=rng)
    # Labeled perturbation: power collapse on r2n5 after the failure (last 0.5h).
    df = apply_step(df, fail_node, "total_power", snap_dt, 0.5, 260.0)
    df = apply_step(df, fail_node, "p0_power", snap_dt, 0.5, 22.0)
    df = apply_step(df, fail_node, "p1_power", snap_dt, 0.5, 22.0)
    _write_parquet(env / "telemetry" / "telemetry_timeseries.parquet", df)

    _write_yaml(env / "policy" / "rbac_policy.yaml", RBAC_SYSADMIN_FULL)

    _write_json(env / "incidents" / "incident_metadata.json", {
        "incident_id": "INC-M100-0818-001",
        "severity": "medium",
        "title": "Job 7798450 FAILED on r2n5 — power collapse at failure time",
        "opened_at": "2022-08-18T15:35:00Z",
        "status": "open",
        "affected_resource": "r2n5",
        "affected_job": "7798450",
        "summary": (
            "Job 7798450 (qmc_solver) on r2n5 entered FAILED state at ~15:30 UTC "
            "(exit_code 1:0, reason JobLaunchFailure). IPMI total_power on r2n5 dropped "
            "from ~730W to ~260W and CPU package power (p0_power/p1_power) fell to idle at "
            "the same time, consistent with the workload terminating."
        ),
        "timeline": [
            {"time": "2022-08-18T11:00:00Z", "event": "Job 7798450 starts on r2n5"},
            {"time": "2022-08-18T15:30:00Z", "event": "Job 7798450 FAILED; node power collapses"},
            {"time": "2022-08-18T16:00:00Z", "event": "Snapshot captured — r2n5 at idle power"},
        ],
        "resolution": None,
        "notes": "Check the job's stderr for the launch failure; node hardware looks healthy (idle power normal).",
    })

    _write_text(env / "docs" / "job_failure_runbook.md", textwrap.dedent("""\
        # Marconi100 Job Failure Correlation Runbook

        ## Signals
        - SLURM `job_state` = FAILED with an `exit_code` / `state_reason`.
        - IPMI `total_power` and CPU package power (`p0_power`, `p1_power`) drop to
          near-idle on the job's node at the failure time as the process terminates.

        ## Correlating a failure
        1. Find the failed job and its node + end_time via SLURM.
        2. Query telemetry for that node around end_time.
        3. A power collapse aligned with end_time confirms the workload died there
           (vs a node hardware fault, where idle power would be abnormal).
    """))

    _write_json(env / "provenance.json", {**PROVENANCE_BASE, "m100_seed": seed,
                "scenario": "job_failure_correlation",
                "perturbation": "FAILED job on r2n5 + total_power/pN_power collapse for final 0.5h"})


# ---------------------------------------------------------------------------
# env_m100_06 — REAL OOM job diagnosis (real job_table record + real mem telemetry)
# ---------------------------------------------------------------------------

def _real_oom_anchor(node: str, snap_time: str) -> dict | None:
    """The longest-running real OUT_OF_MEMORY job from the committed pool, on ``node``."""
    pool = _REAL_JOBS or load_real_jobs()
    ooms = [j for j in pool if j["job_state"] == "OUT_OF_MEMORY" and j.get("elapsed")]
    if not ooms:
        return None

    def _secs(e: str) -> int:
        p = [int(x) for x in e.split(":")]
        return p[0] * 3600 + p[1] * 60 + p[2] if len(p) == 3 else 0

    r = max(ooms, key=lambda x: _secs(x["elapsed"]))
    return {
        "job_id": r["job_id"], "user": r.get("user_id") or "0",
        "state": "FAILED", "job_state": "OUT_OF_MEMORY", "partition": "m100_usr_prod",
        "node": node, "nodes": [node], "num_cpus": r.get("num_cpus"),
        "num_nodes": r.get("num_nodes") or 1, "elapsed": r.get("elapsed"),
        "qos": str(r.get("qos")) if r.get("qos") is not None else None,
        "time_limit": r.get("time_limit"), "state_reason": "OutOfMemory",
    }


def build_env_m100_06(root: Path, dist: dict) -> None:
    env = root / "env_m100_06"
    seed = 606
    rng = np.random.default_rng(seed)
    snap_time = "2022-07-25T18:00:00Z"
    snap_dt = datetime(2022, 7, 25, 18, 0, 0, tzinfo=UTC)
    rack = 5
    nodes = [f"r{rack}n{i}" for i in range(8)]
    oom_node = "r5n3"
    metrics = ["mem_free", "mem_total", "total_power", "p0_power", "ambient"]

    anchor = _real_oom_anchor(oom_node, snap_time)
    job_id = anchor["job_id"] if anchor else "0"

    _write_metadata(env, {
        "environment_id": "env_m100_06",
        "snapshot_name": "M100 Real OOM Job",
        "scenario_type": "job_failure",
        "cluster_name": "marconi100",
        "snapshot_timestamp": snap_time,
        "bundle_root": "environments/env_m100_06",
        "supported_roles": ["scientific_user", "sysadmin"],
        "supported_categories": ["JOB", "MON"],
        "included_sources": ["slurm", "telemetry", "docs", "rbac", "incidents"],
        "included_files": [
            "slurm/slurm_state.json",
            "telemetry/telemetry_timeseries.parquet",
            "policy/rbac_policy.yaml",
            "incidents/incident_metadata.json",
            "docs/oom_runbook.md",
            "provenance.json",
        ],
        "implementation_status": "bundled",
        "validation_status": "validated",
        "description": (
            f"Real-M100-grounded snapshot. The failed job is an ACTUAL Marconi100 "
            f"OUT_OF_MEMORY record (job {job_id}) from the ExaData job_table. On node r5n3 the "
            "real ganglia mem_free falls from ~260 GB toward near-zero before the OOM kill, "
            "then total_power collapses to idle. The user must diagnose the OOM and act."
        ),
    })

    scenario_jobs = [anchor] if anchor else []
    _write_json(env / "slurm" / "slurm_state.json",
                m100_slurm_state("marconi100", snap_time, nodes, scenario_jobs))

    df = synthesize_node_telemetry(nodes, metrics, hours=4, snapshot_time=snap_dt,
                                   dist=dist, rng=rng)
    # Labeled perturbation: mem_free on r5n3 collapses toward ~8 GB before the OOM kill,
    # then total_power drops to idle as the process dies.
    df = apply_ramp(df, oom_node, "mem_free", snap_dt, 0.75, 2.6e8, 8.0e6)
    df = apply_step(df, oom_node, "total_power", snap_dt, 0.25, 260.0)
    df = apply_step(df, oom_node, "p0_power", snap_dt, 0.25, 22.0)
    _write_parquet(env / "telemetry" / "telemetry_timeseries.parquet", df)

    _write_yaml(env / "policy" / "rbac_policy.yaml", RBAC_SYSADMIN_FULL)

    _write_json(env / "incidents" / "incident_metadata.json", {
        "incident_id": "INC-M100-0725-001",
        "severity": "medium",
        "title": f"Job {job_id} killed OUT_OF_MEMORY on r5n3",
        "opened_at": "2022-07-25T17:45:00Z",
        "status": "open",
        "affected_resource": "r5n3",
        "affected_job": job_id,
        "summary": (
            f"Real M100 job {job_id} on r5n3 was terminated by the kernel OOM killer; SLURM "
            "classified it OUT_OF_MEMORY. ganglia mem_free on r5n3 fell from ~260 GB to under "
            "~10 GB (mem_total ~314 GB) before the kill, and total_power then dropped to idle."
        ),
        "timeline": [
            {"time": "2022-07-25T17:15:00Z", "event": "mem_free on r5n3 begins steep decline"},
            {"time": "2022-07-25T17:45:00Z", "event": f"job {job_id} OOM-killed; power collapses"},
            {"time": "2022-07-25T18:00:00Z", "event": "Snapshot captured — r5n3 at idle power"},
        ],
        "resolution": None,
        "notes": "Advise the user to reduce per-task memory or request a high-memory node.",
    })

    _write_text(env / "docs" / "oom_runbook.md", textwrap.dedent("""\
        # Marconi100 Out-Of-Memory (OOM) Runbook

        ## Signals
        - SLURM `job_state` = OUT_OF_MEMORY (the scheduler's own classification).
        - ganglia `mem_free` on the node approaches 0 (against `mem_total`) just before the kill.
        - `total_power` / CPU package power drop to idle when the process dies.

        ## Diagnosis
        1. Confirm the job's `job_state` is OUT_OF_MEMORY via SLURM.
        2. Query telemetry `mem_free` for the node around the failure time — a fall toward 0
           confirms memory exhaustion (vs a node hardware fault).
        3. Distinguish from a hardware fault: after an OOM kill idle power is normal.

        ## Remediation (user)
        - Reduce per-task memory footprint or batch size.
        - Request more memory (`--mem`) or a high-memory node.
        - Use fewer tasks per node so each gets more RAM.
    """))

    _write_json(env / "provenance.json", {**PROVENANCE_BASE, "m100_seed": seed,
                "scenario": "real_oom_job", "anchor_job_id": job_id,
                "anchor_source": "real ExaData job_table OUT_OF_MEMORY record",
                "perturbation": "real OOM job anchor + ganglia mem_free collapse + power drop"})


# ---------------------------------------------------------------------------
# Gold-consistency guard
# ---------------------------------------------------------------------------
#
# Each M100 gold_answer (benchmark/tasks/specs/M100_*.json) asserts qualitative,
# mode-invariant facts: a named node crosses a named hardware/policy threshold,
# its peers stay below it, or its trace collapses/drops out. These checks verify
# those exact facts hold in the GENERATED telemetry — in BOTH distribution-sampled
# and --real-baselines mode — so a build that silently de-syncs from the scored
# gold is caught at build time rather than surfacing as a quietly wrong score.

GOLD_CHECKS: dict[str, list[dict]] = {
    "env_m100_01": [
        {"kind": "exceeds", "node": "r3n7", "metric": "gpu3_core_temp", "threshold": 84.0},
        {"kind": "peers_below", "nodes": [f"r3n{i}" for i in range(7)],
         "metric": "gpu3_core_temp", "threshold": 84.0},
    ],
    "env_m100_02": [
        {"kind": "exceeds", "node": "r10n4", "metric": "total_power", "threshold": 1300.0},
        {"kind": "peers_below", "nodes": [f"r10n{i}" for i in range(8) if i != 4],
         "metric": "total_power", "threshold": 1300.0},
    ],
    "env_m100_03": [
        {"kind": "exceeds_all", "nodes": [f"r4n{i}" for i in range(8)],
         "metric": "ambient", "threshold": 28.0},
    ],
    "env_m100_04": [
        {"kind": "drops_out", "node": "r7n2"},
    ],
    "env_m100_05": [
        {"kind": "collapses", "node": "r2n5", "metric": "total_power", "ratio": 0.6},
    ],
    "env_m100_06": [
        {"kind": "collapses", "node": "r5n3", "metric": "mem_free", "ratio": 0.5},
    ],
}


def _series(df: pd.DataFrame, node: str, metric: str) -> pd.Series:
    return df[(df["node_id"] == node) & (df["metric_name"] == metric)]["value"]


def verify_gold_consistency(df: pd.DataFrame, checks: list[dict]) -> list[str]:
    """Return a list of failure messages (empty == all gold facts hold)."""
    failures: list[str] = []
    for c in checks:
        kind = c["kind"]
        if kind == "exceeds":
            vals = _series(df, c["node"], c["metric"])
            if vals.empty or vals.max() <= c["threshold"]:
                failures.append(
                    f"{c['node']}.{c['metric']} max={vals.max() if not vals.empty else 'n/a'} "
                    f"does not exceed threshold {c['threshold']}")
        elif kind == "peers_below":
            peak = max((_series(df, n, c["metric"]).max() for n in c["nodes"]
                        if not _series(df, n, c["metric"]).empty), default=float("-inf"))
            if peak >= c["threshold"]:
                failures.append(
                    f"a peer {c['metric']} max={peak:.2f} reaches threshold {c['threshold']} "
                    f"(anomaly not isolated)")
        elif kind == "exceeds_all":
            for n in c["nodes"]:
                vals = _series(df, n, c["metric"])
                if vals.empty or vals.max() <= c["threshold"]:
                    failures.append(
                        f"{n}.{c['metric']} max={vals.max() if not vals.empty else 'n/a'} "
                        f"does not exceed rack-wide threshold {c['threshold']}")
        elif kind == "drops_out":
            node_last = df[df["node_id"] == c["node"]]["timestamp"].max()
            overall_last = df["timestamp"].max()
            if not (node_last < overall_last):
                failures.append(
                    f"{c['node']} last sample {node_last} not before snapshot {overall_last} "
                    f"(node did not drop out)")
        elif kind == "collapses":
            vals = _series(df, c["node"], c["metric"]).reset_index(drop=True)
            if vals.empty:
                failures.append(f"{c['node']}.{c['metric']} has no data")
                continue
            head = vals.iloc[: max(1, len(vals) // 3)]
            baseline = float(head.median())
            trough = float(vals.min())
            if not (trough < c["ratio"] * baseline):
                failures.append(
                    f"{c['node']}.{c['metric']} trough={trough:.2f} not below "
                    f"{c['ratio']}×baseline ({c['ratio'] * baseline:.2f}) — no collapse")
        else:  # pragma: no cover - guards against typos in the table
            failures.append(f"unknown check kind '{kind}'")
    return failures


def check_all_envs(envs_root: Path) -> dict[str, list[str]]:
    """Run gold-consistency checks against every built env's telemetry parquet."""
    results: dict[str, list[str]] = {}
    for env_id, checks in GOLD_CHECKS.items():
        pq = envs_root / env_id / "telemetry" / "telemetry_timeseries.parquet"
        if not pq.exists():
            results[env_id] = [f"telemetry parquet missing at {pq}"]
            continue
        df = pd.read_parquet(pq)
        results[env_id] = verify_gold_consistency(df, checks)
    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

BUILDERS = [
    build_env_m100_01, build_env_m100_02, build_env_m100_03,
    build_env_m100_04, build_env_m100_05, build_env_m100_06,
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate M100-grounded bundles env_m100_*")
    parser.add_argument("--benchmark-root", default="benchmark")
    parser.add_argument("--dataset-path", default=None,
                        help="Optional path to a full M100 parquet dataset for live-slice refinement")
    parser.add_argument("--real-baselines", type=Path, default=None,
                        help="Directory of real per-node wide parquets (time_aggregated/). When "
                             "set, env-node baselines come from real M100 traces at the env's real "
                             "timestamp instead of distribution sampling (run where the data lives).")
    parser.add_argument("--real-jobs", dest="real_jobs", action="store_true", default=True,
                        help="Append real M100 job records (from the committed pool) as queue "
                             "context (default: on; builds offline).")
    parser.add_argument("--no-real-jobs", dest="real_jobs", action="store_false",
                        help="Use only synthetic scenario jobs (no real background jobs).")
    parser.add_argument("--relative-anomalies", action="store_true", default=False,
                        help="Scale upward magnitude anomalies to each node's real baseline "
                             "(recommended with --real-baselines so the anomaly stays clearly "
                             "separated from noisy real peer load).")
    args = parser.parse_args()

    global _REAL_DIR, _REAL_JOBS, _RELATIVE_ANOMALIES
    _RELATIVE_ANOMALIES = args.relative_anomalies
    _REAL_DIR = args.real_baselines
    if _REAL_DIR is not None:
        print(f"  [data] real-baseline mode: env nodes use real traces from {_REAL_DIR}")
    if args.real_jobs:
        _REAL_JOBS = load_real_jobs()
        if _REAL_JOBS:
            print(f"  [jobs] grounding queues in {len(_REAL_JOBS)} real M100 job records")

    dist = load_reference_distributions()
    maybe_load_live_slice(args.dataset_path)

    envs_root = Path(args.benchmark_root) / "environments"
    envs_root.mkdir(parents=True, exist_ok=True)

    for builder in BUILDERS:
        name = builder.__name__.replace("build_", "")
        print(f"Generating {name}...", end=" ", flush=True)
        builder(envs_root, dist)
        print("OK")

    print(f"\nGenerated {len(BUILDERS)} M100-grounded bundles in {envs_root}")

    # Gold-consistency gate: the scored gold_answers depend on these facts holding.
    print("Verifying gold consistency...", end=" ", flush=True)
    results = check_all_envs(envs_root)
    failures = {env: msgs for env, msgs in results.items() if msgs}
    if failures:
        print("FAILED")
        for env, msgs in failures.items():
            for m in msgs:
                print(f"  [{env}] {m}")
        if _REAL_DIR is not None and not _RELATIVE_ANOMALIES:
            print("  hint: real-baseline mode rides on noisy real peer load — re-run with "
                  "--relative-anomalies so anomalies stay clearly separated from peers.")
        raise SystemExit(1)
    print("OK")


if __name__ == "__main__":
    main()
