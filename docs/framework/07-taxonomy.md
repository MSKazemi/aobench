# 07 — Taxonomy

**Owner:** Mohsen

This page consolidates the taxonomy dimensions used to organize ExaBench tasks: roles, query categories (QCAT), access control, and query metadata schema.

---

## 1. Roles & Personas

Who is asking in an ExaBench task. v0.1 uses: `scientific_user`, `sysadmin`, `facility_admin`.

| Role | Primary Mission | Key Data Sources | Example Query |
|------|-----------------|------------------|---------------|
| **Normal User** | Run workloads, manage data | Scheduler logs, job outputs | "Why did my job fail and how can I fix it?" |
| **Researcher** | Analyze telemetry, performance, efficiency | Prometheus, parquet, SLURM logs | "Correlate node power with CPU load." |
| **System Administrator** | Cluster reliability, security | Node metrics, scheduler, syslogs | "List nodes with GPU ECC errors." |
| **Facility Admin** | Power and cooling operations | BMS/DCIM, IPMI, energy meters | "Which racks exceeded 28 °C today?" |
| **System Designer/Architect** | Capacity planning, topology | Benchmark results, fleet telemetry | "Estimate LINPACK scaling for 512 nodes." |

---

## 2. Query Categories (QCAT)

| Code | Name | Description |
|------|------|--------------|
| **JOB** | Job & Workflow Management | Submitting, monitoring, debugging jobs; queues; batch scripts |
| **MON** | Monitoring & Observability | Metrics, logs, alerts, dashboards, telemetry correlation |
| **ENERGY** | Power, Energy & Sustainability | Power monitoring, PUE, energy-aware scheduling |
| **PERF** | Performance & Optimization | Profiling, bottlenecks, scaling studies |
| **DATA** | Data & Storage Management | Filesystems, quotas, I/O, data transfer |
| **SEC** | Security & Policy | IAM, access control, compliance |
| **FAC** | Facility & Environmental | Cooling, BMS/DCIM, rack health, alarms |
| **ARCH** | Architecture & Capacity | Topology design, performance modeling |
| **AIOPS** | AI & Intelligent Operations | Anomaly detection, predictive maintenance |
| **DOCS** | Documentation & Support | FAQs, tutorials, troubleshooting |

v0.1 focuses on: **JOB**, **MON**, **ENERGY**.

---

## 3. Access Control & RBAC

Data exposure and permission tiers for ExaBench tasks.

### Access Levels

| Level | Users | Scope |
|-------|-------|-------|
| **User-Level** | Normal users, Researchers | Own jobs, public docs, safe how-to |
| **Elevated/Privileged** | Sysadmins, Project managers | Software install, config, user management |
| **Restricted Read-Only** | Researchers | Aggregated, anonymized telemetry |
| **Sensitive/Admin-Only** | Sysadmins, Security | Auth logs, security config, network |
| **Highly Sensitive** | Architects, Facility operators | Procurement, physical access design |

### Access Tier Definitions

| Tier | Description | Controls |
|------|-------------|----------|
| Tier-1: Public/User-Level | Safe docs, non-sensitive RAG | No approval |
| Tier-2: Privileged | Real telemetry | Role-based validation |
| Tier-3: Restricted Read-Only | Energy dashboards, KPIs | Read-only |
| Tier-4: Highly Sensitive | Procurement, cybersecurity | Approval + isolation |

### Policy Notes

- **Least-privilege:** Each role gets minimum required access.
- **Data anonymization:** Facility/energy data for researchers must be aggregated and anonymized.
- **Audit logging:** Privileged actions are logged and reviewable.

---

## 4. Query Metadata Schema

Canonical keys for benchmark query/task records.

| Key | Purpose | Example |
|-----|---------|---------|
| `query_id` | Unique identifier | `"Q-ENERGY-042"` |
| `user_type` | Persona/role context | `"System Administrator"` |
| `category` | Functional domain (QCAT) | `"Energy"` |
| `intent` | Underlying goal | `"Cluster energy trend over time"` |
| `query_text` | User-facing text | `"Show total energy per rack..."` |
| `data_sources` | Telemetry/datasets needed | `["IPMI","Prometheus"]` |
| `difficulty` | Complexity | `easy` \| `medium` \| `hard` \| `edge` |
| `priority` | Evaluation weight | `"high"` |
| `expected_answer` | Output format | `table` \| `chart` \| `fact` |
| `evaluation_signal` | Correctness check | `"range_check(sum_kWh)"` |
| `dependencies` | Preconditions | `["rack_node_mapping"]` |

---

## 5. Related Documents

- Role detail pages: `docs/taxonomy/roles/` (system_administrators, facility_admin, etc.)
- Task schema: see [03-architecture](03-architecture.md) § 5.1
- Evaluation: see [06-evaluation](06-evaluation.md)
