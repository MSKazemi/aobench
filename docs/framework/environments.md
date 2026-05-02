# Environment Snapshots

## Purpose

Environment Snapshots define the **deterministic HPC operational states** used by ExaBench during evaluation.

An environment snapshot is a packaged, reproducible bundle of scheduler state, telemetry, policies, documentation, and incident context that simulates a realistic HPC situation without requiring access to a live system.

Each benchmark task references one environment snapshot through `environment_id`. This allows the same task to be executed repeatedly under the same conditions, ensuring reproducibility, fair comparison, and offline benchmarking. ExaBench relies on these deterministic snapshots rather than live infrastructure as part of its benchmark design.

---

## 1 — What an Environment Snapshot Represents

An Environment Snapshot is the **world-state** in which an agent must operate.

It may capture:

- scheduler and queue state
- node and job telemetry
- power and energy measurements
- cluster topology
- role-based access policies
- documentation and operational procedures
- incident or fault context

In simple terms:

```
Task = what the agent is asked
Environment Snapshot = the frozen HPC reality used to answer it
```

---

## 2 — Why Environment Snapshots Are Needed

Environment Snapshots are required because live HPC systems are constantly changing.

Without snapshots:

- job queues change
- metrics drift
- incidents resolve
- documents get updated
- permissions change over time

Using snapshots makes ExaBench:

- reproducible
- publishable
- easier to debug
- independent of site-specific live infrastructure
- suitable for offline evaluation and artifact release

---

## 3 — Core Design Principles

### 3.1 Deterministic

The same snapshot must always produce the same tool outputs for the same inputs.

### 3.2 Realistic

Snapshots should reflect real HPC operational situations such as job failures, thermal anomalies, queue congestion, or documentation lookup.

### 3.3 Role-aware

The same snapshot may expose different views depending on the requester role and policy profile.

### 3.4 Modular

A snapshot should be composed of clearly separated files for scheduler state, telemetry, policies, docs, and incidents.

### 3.5 Extensible

The format should support future additions such as live replay, multi-agent interaction, or time-evolving scenarios.

---

## 4 — Typical Snapshot Contents

A snapshot bundle may include the following components:

- `slurm_state.json`
- `telemetry_timeseries.parquet`
- `power_metrics.csv`
- `topology.json`
- `rbac_policy.yaml`
- `docs_index/`
- `incident_metadata.json`
- `metadata.yaml`

These file types are consistent with the ExaBench architecture page, which already describes the HPC state snapshot model and typical files.

---

## 5 — Canonical Directory Layout

```
benchmark/environments/
  <env_id>/
    metadata.yaml                        ← EnvironmentMetadata (Pydantic-validated)
    slurm/
      slurm_state.json                   ← nodes, partitions, jobs (validated by SlurmState)
      job_details.json                   ← sacct-level details (optional)
    telemetry/
      telemetry_timeseries.parquet       ← columns: timestamp, node_id, metric_name, value, unit
      memory_events.csv                  ← OOM/memory events (optional)
    policy/
      rbac_policy.yaml                   ← per-role permission definitions
    docs/
      *.md                               ← user-facing knowledge docs
    incidents/
      incident_metadata.json             ← incident timeline + affected resources
```

Bundles are validated by `exabench.environment.snapshot_validator.validate_bundle()`.

---

## 6 — Snapshot Metadata Schema

Each environment snapshot should have a small metadata file.

### Example `metadata.yaml`

```yaml
environment_id: env_01
snapshot_name: OOM Failure Scenario
cluster_name: cluster-a
snapshot_timestamp: 2026-02-10T14:00:00Z
supported_roles:
  - scientific_user
  - sysadmin
supported_qcats:
  - JOB
  - MON
included_sources:
  - slurm
  - telemetry metrics snapshot
  - docs
  - rbac
scenario_type: job_failure
description: >
  Snapshot representing a user job failure caused by out-of-memory pressure,
  with associated scheduler state, metrics, and policy context.
```

---

## 7 — Logical Components of a Snapshot

### 7.1 Scheduler State

Represents batch system information such as:

- jobs
- queues
- partitions
- node assignments
- exit codes
- scheduling state

Typical source file:

- `slurm_state.json`

### 7.2 Telemetry State

Represents operational measurements such as:

- CPU utilization
- memory usage
- node health
- power draw
- temperature
- cooling indicators

Typical source files:

- `telemetry_timeseries.parquet`
- `power_metrics.csv`

### 7.3 Policy and Access State

Represents what a role can view or do.

Examples:

- read-only user policy
- sysadmin visibility
- restricted facility billing data
- redaction rules

Typical source file:

- `rbac_policy.yaml`

### 7.4 Documentation Bundle

Represents the knowledge artifacts accessible to the agent.

Examples:

- user guides
- quota policies
- troubleshooting docs
- facility procedures

Typical source:

- `docs_index/`

### 7.5 Incident Context

Represents scenario-specific operational conditions.

Examples:

- rack overheat
- queue backlog
- partial metrics outage
- node failure
- maintenance window

Typical source file:

- `incident_metadata.json`

---

## 8 — Example Snapshot Use Case

### Example task

```
Why did my job 482910 fail and what should I change?
```

### Referenced environment

```
environment_id = env_01
```

### Snapshot contents

- `slurm_state.json` shows job 482910 failed with OOM
- `telemetry_timeseries.parquet` shows memory spike before termination
- `rbac_policy.yaml` allows the user to see only their own job details
- `docs_index/` includes memory request documentation
- `incident_metadata.json` confirms no broader cluster outage

This lets the agent answer the question using a realistic but fully reproducible scenario.

---

## 9 — Relationship to Tasks

A task should never depend on live infrastructure.

Instead, each task references one snapshot via:

```json
{
  "task_id": "JOB_USR_003",
  "environment_id": "env_01"
}
```

This means:

- the task defines the question and evaluation logic
- the environment snapshot defines the underlying HPC state

So the mapping is:

```
Task → references → Environment Snapshot
Agent → interacts with → Mock tools over snapshot data
Scorers → evaluate → output + trace against task + snapshot
```

---

## 10 — Relationship to Mock Tools

Snapshots are not accessed directly by the agent.

Instead, mock tools expose the snapshot data through controlled interfaces.

Examples:

- `slurm.query_jobs()`
- `slurm.job_details(job_id)`
- `telemetry.query(metric, labels, time_range)`
- `docs.retrieve(query)`
- `rbac.check(role, resource)`

So the snapshot is the **backend state**, and the mock tools are the **evaluation interface**.

---

## 11 — Environment Scenario Types

To keep dataset design organized, snapshots can be categorized by scenario type.

Suggested types:

- `job_failure`
- `queue_congestion`
- `node_health_alert`
- `energy_anomaly`
- `thermal_issue`
- `policy_lookup`
- `permission_violation`
- `incident_response`
- `performance_bottleneck`

This helps align snapshots with QCAT categories and capabilities.

---

## 12 — Current Environment Coverage

ExaBench currently ships 23 canonical snapshot bundles across 11 scenario types.

| Scenario type | Count | Env IDs |
|---------------|-------|---------|
| `job_failure` | 3 | env_01, env_17, env_18 |
| `energy_anomaly` | 3 | env_06, env_07, env_19 |
| `node_degradation` | 2 | env_08, env_09 |
| `policy_violation` | 2 | env_10, env_11 |
| `queue_congestion` | 2 | env_02, env_12 |
| `capacity_planning` | 2 | env_13, env_14 |
| `multi_job_interference` | 2 | env_15, env_20 |
| `scheduler_misconfiguration` | 1 | env_16 |
| `storage_management` | 1 | env_21 |
| `facility_incident` | 1 | env_22 |
| `architecture_review` | 1 | env_23 |

### Naming convention

Canonical environment IDs use the `env_NN` scheme (zero-padded). New bundles should continue from `env_24`.

---

## `12.1 — Canonical Snapshot Tracker`

| environment_id | snapshot_name | scenario_type | supported_roles | supported_categories | status |
| --- | --- | --- | --- | --- | --- |
| `env_01` | User OOM Failure | `job_failure` | `scientific_user`, `sysadmin` | `JOB`, `MON` | `validated` |
| `env_02` | Queue Congestion / Long Pending Jobs | `queue_congestion` | `scientific_user`, `sysadmin` | `JOB`, `MON` | `validated` |
| `env_03` | Thermal and Power Monitoring | `thermal_power` | `sysadmin`, `facility_admin` | `MON`, `ENERGY` | `validated` |
| `env_04` | Rack Energy Comparison | `rack_energy` | `facility_admin` | `ENERGY` | `validated` |
| `env_05` | Cooling Unit Failure | `cooling_failure` | `facility_admin`, `sysadmin` | `ENERGY`, `MON` | `validated` |
| `env_06` | GPU Power Spike | `energy_anomaly` | `sysadmin`, `facility_admin` | `ENERGY`, `MON` | `validated` |
| `env_07` | PUE Degradation Cooling Issue | `energy_anomaly` | `facility_admin` | `ENERGY` | `validated` |
| `env_08` | Thermal Throttling on node03 | `node_degradation` | `sysadmin` | `MON` | `validated` |
| `env_09` | Memory ECC Errors Flapping Node | `node_degradation` | `sysadmin` | `MON` | `validated` |
| `env_10` | Policy Violation Restricted Partition | `policy_violation` | `scientific_user`, `sysadmin` | `JOB` | `validated` |
| `env_11` | Account Over Allocation Limit | `policy_violation` | `sysadmin`, `facility_admin` | `JOB` | `validated` |
| `env_12` | Fairshare Starvation Priority Inversion | `queue_congestion` | `sysadmin` | `JOB`, `MON` | `validated` |
| `env_13` | Six Month CPU Utilisation Trend | `capacity_planning` | `facility_admin`, `system_designer` | `ENERGY`, `MON` | `validated` |
| `env_14` | GPU Demand Forecast Expansion | `capacity_planning` | `system_designer` | `ENERGY`, `MON` | `validated` |
| `env_15` | Multi-Job Memory Interference | `multi_job_interference` | `sysadmin`, `researcher` | `JOB`, `MON` | `validated` |
| `env_16` | Wrong Default Partition Misconfiguration | `scheduler_misconfiguration` | `sysadmin` | `JOB` | `validated` |
| `env_17` | MPI Communication Timeout Network Fault | `job_failure` | `sysadmin` | `JOB`, `MON` | `validated` |
| `env_18` | Checkpoint File Missing Restart Fails | `job_failure` | `scientific_user` | `JOB` | `validated` |
| `env_19` | GPU Idle Energy Waste Not Released | `energy_anomaly` | `facility_admin` | `ENERGY`, `MON` | `validated` |
| `env_20` | Lustre IO Contention Multi-Job Interference | `multi_job_interference` | `sysadmin` | `JOB`, `MON` | `validated` |
| `env_21` | Storage Quota Pressure | `storage_management` | all 5 roles | `DATA` | `not_checked` |
| `env_22` | Cooling Alarm Response | `facility_incident` | all 5 roles | `FAC`, `ENERGY`, `DOCS` | `not_checked` |
| `env_23` | Capacity Expansion Planning | `architecture_review` | sysadmin, researcher, facility_admin, system_designer | `ARCH`, `PERF`, `DOCS` | `not_checked` |

Every task must reference exactly one valid `environment_id` from this table.

---

## `12.2 — Snapshot Schema Implementation`

All 20 bundles are validated by `validate_bundle()` on every `load_environment()` call.

### Key implementation files

| File | Purpose |
|------|---------|
| `src/exabench/schemas/snapshot.py` | Pydantic models: `SlurmState`, `SlurmJob`, `SlurmNode`, `SlurmPartition`, `IncidentMetadata` |
| `src/exabench/environment/snapshot_validator.py` | `validate_bundle(bundle_root)` — validates JSON schemas, RBAC YAML, parquet columns |
| `src/exabench/environment/snapshot_loader.py` | `build_tool_registry(bundle, role)` — instantiates all mock tools bound to a role |
| `src/exabench/loaders/env_loader.py` | `load_environment()` — calls `validate_bundle()` before returning bundle |
| `scripts/generate_bundles.py` | Generates env_06–env_20 bundles programmatically (`make generate-bundles`) |

### Telemetry parquet schema (canonical)

| Column | dtype | Description |
|--------|-------|-------------|
| `timestamp` | `datetime64[ns, UTC]` | Sample time (UTC) |
| `node_id` | `string` | Node name (e.g. `node01`) |
| `metric_name` | `string` | e.g. `cpu_util_pct`, `power_w`, `gpu_util_pct` |
| `value` | `float64` | Metric value |
| `unit` | `string` | `%`, `MB`, `W`, `Mbps` |

### Mock tool telemetry methods

| Method | Description |
|--------|-------------|
| `telemetry.query_timeseries(node_id, metric_name, start, end)` | Parquet time-range query with role-based node filtering |
| `telemetry.query_node_metrics(node_id)` | Per-node latest-value summary across all metrics |
| `telemetry.query_memory_events(job_id)` | Memory events CSV lookup |
| `telemetry.list_metrics()` | List available telemetry files |

### Implementation status values

| Status | Meaning |
|--------|---------|
| `planned` | Exists only as a row in a table |
| `scaffolded` | Directory + metadata exist; files may be placeholders |
| `bundled` | All required files present |
| `validated` | Passes `validate_bundle()` — no schema errors |

All 20 current bundles are at `validated` status.

---

## 13 — Validation Rules

`validate_bundle(bundle_root)` (in `src/exabench/environment/snapshot_validator.py`) checks:

- `slurm/slurm_state.json` — validates against `SlurmState` Pydantic model
- `incidents/incident_metadata.json` — validates against `IncidentMetadata` Pydantic model
- `policy/rbac_policy.yaml` — must be valid YAML with a top-level `roles` key
- `telemetry/telemetry_timeseries.parquet` — must contain columns: `timestamp`, `node_id`, `metric_name`, `value`, `unit`

`load_environment()` calls `validate_bundle()` automatically and raises `ValueError` on any error.

To validate all bundles manually:

```bash
make validate-bundles
```

---

## 14 — Future Extensions

Later versions of ExaBench may support:

- time-series replay environments
- partially degraded environments
- multi-step incident simulations
- hidden environment variants for leaderboard robustness
- site-specific snapshot packs
- multi-agent environment interaction

---

## 15 — Bottom Line

Environment Snapshots are a core part of ExaBench. They make the benchmark more than a question set by providing a reproducible HPC world-state for agent evaluation.

Their role is to:

- freeze operational reality
- support mock tool interaction
- enable fair scoring
- make benchmark runs reproducible
- bridge task definitions and executable evaluation