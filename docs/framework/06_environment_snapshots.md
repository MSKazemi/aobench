# 06 — Environment Snapshots

Owner: Mohsen

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

## 5 — Recommended Directory Layout

```
data/environments/
  env_01/
    metadata.yaml
    slurm_state.json
    telemetry_timeseries.parquet
    power_metrics.csv
    topology.json
    rbac_policy.yaml
    docs_index/
    incident_metadata.json

  env_02/
    metadata.yaml
    slurm_state.json
    telemetry_timeseries.parquet
    rbac_policy.yaml
    docs_index/
```

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
- `prom.query(metric, labels, time_range)`
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

## 12 — v0.1 Environment Scope

This page implements the canonical v0.1 principle that ExaBench is reproducible via deterministic environment snapshots.

For ExaBench v0.1, the environment layer should stay intentionally small.

### Recommended v0.1 target

- 5 environment snapshots
- 3 core categories: `JOB`, `MON`, `ENERGY`
- 3 main roles: `scientific_user`, `sysadmin`, `facility_admin`

### Suggested first 5 snapshots

1. user job OOM failure
2. queue congestion and long pending jobs
3. node utilization anomaly
4. power spike on selected nodes
5. documentation + policy lookup scenario

This matches the current minimal benchmark scope where ExaBench v0.1 targets about 5 environment snapshots.

### v0.1 Naming Freeze

For ExaBench v0.1, the canonical environment IDs are:

- `env_01`
- `env_02`
- `env_03`
- `env_04`
- `env_05`

Long-form example identifiers such as `env_cluster_snapshot_01` should not be used in v0.1 task records, metadata examples, or tracker tables.

---

## `12.1 — Canonical v0.1 Snapshot Tracker`

| environment_id | snapshot_name | scenario_type | supported_roles | supported_categories | status |
| --- | --- | --- | --- | --- | --- |
| `env_01` | User OOM Failure | `job_failure` | `scientific_user`, `sysadmin` | `JOB`, `MON` | `defined` |
| `env_02` | Queue Congestion / Long Pending Jobs | `queue_congestion` | `scientific_user`, `sysadmin` | `JOB`, `MON` | `defined` |
| `env_03` | Node Utilization / Health Anomaly | `node_health_alert` | `sysadmin`, `facility_admin` | `MON`, `ENERGY` | `defined` |
| `env_04` | Power Spike on Selected Nodes | `energy_anomaly` | `sysadmin`, `facility_admin` | `ENERGY`, `MON` | `defined` |
| `env_05` | Documentation + Policy Lookup | `policy_lookup` | `scientific_user`, `sysadmin`, `facility_admin` | `JOB`, `MON`, `ENERGY` | `defined` |

> This tracker converts the environment design into an operational registry.
> 
> 
> Every task in `05 — Task Database` must reference exactly one valid `environment_id` from this table.
> 
> For v0.1, all five snapshots should exist at least in `defined` state before full runner integration.
> 

---

## `12.2 — Operational Bundle Tracker (Alpha-0)`

### Paste this explanatory text

> This section operationalizes the canonical environment snapshots into real benchmark bundles.
> 
> 
> The table below is not only a conceptual tracker; it is the implementation tracker for the first concrete environment packages used by ExaBench Alpha-0.
> 
> A snapshot is not considered implemented until it has:
> 
> - a canonical `environment_id`
> - a real bundle root path in the repository
> - a concrete `metadata.yaml`
> - a declared source inventory
> - a concrete file inventory
> - implementation status
> - validation status
> 
> For Alpha-0, the initial target is to implement at least 2 real snapshot bundles: `env_01` and `env_02`.
> 

### Status definitions (Alpha-0)

**Implementation status**

- `defined`: exists only as a row in a table
- `scaffolded`: repo folder exists, metadata exists, inventory exists (files may be placeholders)
- `bundled`: required files are present in the bundle structure
- `validated`: passes structural checks
- `runner_ready`: snapshot can be loaded by the snapshot loader / mock tools

**Validation status**

- `not_checked`
- `structure_valid`
- `metadata_valid`
- `file_inventory_valid`
- `fully_validated`

| Column | Purpose |
| --- | --- |
| `environment_id` | canonical ID |
| `snapshot_name` | short scenario name |
| `scenario_type` | job_failure / queue_congestion / ... |
| `bundle_root` | repo path |
| `included_sources` | source groups included |
| `included_files` | concrete file list |
| `supported_roles` | roles supported |
| `supported_categories` | categories supported |
| `metadata_status` | missing / draft / complete |
| `implementation_status` | defined / scaffolded / bundled / validated / runner_ready |
| `validation_status` | not_checked / partial / passed / failed |
| `owner` | responsible person |
| `notes` | implementation notes |
| `blockers` | missing files / unclear source / etc. |

### Operational tracker (seed for Alpha-0)

| environment_id | snapshot_name | scenario_type | bundle_root | included_sources | included_files | supported_roles | supported_categories | metadata_status | implementation_status | validation_status | owner | notes | blockers |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `env_01` | User OOM Failure | `job_failure` | `data/environments/env_01/` | `slurm`, `telemetry`, `docs`, `rbac`, `incidents` | `metadata.yaml`
`slurm/slurm_state.json`
`slurm/job_details.json`
`telemetry/telemetry_timeseries.parquet`
`telemetry/memory_events.csv`
`policy/rbac_policy.yaml`
`docs/memory_request_guide.md`
`docs/troubleshooting_oom.md`
`incidents/incident_metadata.json` | `scientific_user`, `sysadmin` | `JOB`, `MON` | `draft` | `scaffolded` | `not_checked` | slurm/job_details.json | telemetry/telemetry_timeseries.parquet | telemetry/memory_events.csv |
| `env_02` | Queue Congestion / Long Pending Jobs | `queue_congestion` | `data/environments/env_02/` | `slurm`, `telemetry`, `docs`, `rbac`, `incidents` | `metadata.yaml`
`slurm/slurm_state.json`
`slurm/pending_jobs.json`
`slurm/qos_limits.json`
`telemetry/queue_pressure_metrics.csv`
`policy/rbac_policy.yaml`
`docs/queue_policy.md`
`docs/scheduling_faq.md`
`incidents/incident_metadata.json` | `scientific_user`, `sysadmin` | `JOB`, `MON` | `draft` | `scaffolded` | `not_checked` | slurm/pending_jobs.json | slurm/qos_limits.json | telemetry/queue_pressure_metrics.csv |

### Recommended repo structure (Alpha-0)

```
data/
  environments/
    env_01/
      metadata.yaml
      manifest.txt
      slurm/
        slurm_state.json
        job_details.json
      telemetry/
        telemetry_timeseries.parquet
        memory_events.csv
      policy/
        rbac_policy.yaml
      docs/
        memory_request_guide.md
        troubleshooting_oom.md
      incidents/
        incident_metadata.json

    env_02/
      metadata.yaml
      manifest.txt
      slurm/
        slurm_state.json
        pending_jobs.json
        qos_limits.json
      telemetry/
        queue_pressure_metrics.csv
      policy/
        rbac_policy.yaml
      docs/
        queue_policy.md
        scheduling_faq.md
      incidents/
        incident_metadata.json
```

### Concrete `metadata.yaml` examples

#### `env_01/metadata.yaml`

```yaml
environment_id: env_01
snapshot_name: User OOM Failure
scenario_type: job_failure
cluster_name: exabench-cluster-a
snapshot_timestamp: 2026-02-10T14:00:00Z
bundle_root: data/environments/env_01
supported_roles:
  - scientific_user
  - sysadmin
supported_categories:
  - JOB
  - MON
included_sources:
  - slurm
  - telemetry
  - docs
  - rbac
  - incidents
included_files:
  - slurm/slurm_state.json
  - slurm/job_details.json
  - telemetry/telemetry_timeseries.parquet
  - telemetry/memory_events.csv
  - policy/rbac_policy.yaml
  - docs/memory_request_guide.md
  - docs/troubleshooting_oom.md
  - incidents/incident_metadata.json
implementation_status: scaffolded
validation_status: not_checked
description: >
  Deterministic snapshot representing a user job failure caused by
  out-of-memory pressure, with scheduler state, memory telemetry,
  role-aware visibility, and user-facing troubleshooting documents.
```

#### `env_02/metadata.yaml`

```yaml
environment_id: env_02
snapshot_name: Queue Congestion / Long Pending Jobs
scenario_type: queue_congestion
cluster_name: exabench-cluster-a
snapshot_timestamp: 2026-02-11T09:00:00Z
bundle_root: data/environments/env_02
supported_roles:
  - scientific_user
  - sysadmin
supported_categories:
  - JOB
  - MON
included_sources:
  - slurm
  - telemetry
  - docs
  - rbac
  - incidents
included_files:
  - slurm/slurm_state.json
  - slurm/pending_jobs.json
  - slurm/qos_limits.json
  - telemetry/queue_pressure_metrics.csv
  - policy/rbac_policy.yaml
  - docs/queue_policy.md
  - docs/scheduling_faq.md
  - incidents/incident_metadata.json
implementation_status: scaffolded
validation_status: not_checked
description: >
  Deterministic snapshot representing queue congestion and long pending
  jobs, including queue state, scheduler policy context, role-aware
  access, and supporting documentation for interpretation.
```

---

## 13 — Validation Rules

Each environment snapshot should satisfy basic validation checks.

### Required

- valid `environment_id`
- metadata file exists
- referenced files exist
- supported roles declared
- supported QCATs declared

### Recommended

- deterministic mock tool outputs
- timestamp included
- clear scenario description
- known source inventory
- no dependence on live external systems

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