# 07 — Taxonomy

**Owner:** Mohsen

This page consolidates the taxonomy dimensions used to organize ExaBench tasks: roles, query categories (QCAT), access control, and query metadata schema.

---

## 1. Roles & Personas

Who is asking in an ExaBench task. Schema values: `scientific_user`, `sysadmin`, `facility_admin`, `researcher`, `system_designer`.

| Role | Schema Value | Primary Mission | High-Priority QCATs | Example Query |
|------|-------------|-----------------|---------------------|---------------|
| **Normal User** | `scientific_user` | Run workloads, manage data | JOB, DATA, PERF, MON, DOCS | "Why did my job fail and how can I fix it?" |
| **Researcher** | `researcher` | Analyze telemetry, performance, efficiency | AIOPS, PERF, ENERGY, DATA, MON | "Detect power anomalies across 3 years and rank top outlier jobs." |
| **System Administrator** | `sysadmin` | Cluster reliability, security, scheduling | JOB, MON, DATA, SEC, AIOPS | "Drain node n101 and requeue pending jobs." |
| **Facility Admin** | `facility_admin` | Power and cooling operations | MON, ENERGY, FAC, AIOPS, DOCS | "List all active critical alarms and show affected racks." |
| **System Designer/Architect** | `system_designer` | Capacity planning, topology, benchmarking | ARCH, PERF, ENERGY, MON, DOCS | "Estimate LINPACK scaling for 512 nodes and identify bottlenecks." |

See `docs/taxonomy/roles/` for per-role query categories, example queries, and priority tags.

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

v0.1 focuses on: **JOB**, **MON**, **ENERGY**. All 10 QCATs are active in the full taxonomy; role files under `docs/taxonomy/roles/` document per-role sub-categories and priorities.

---

## 3. Knowledge Source Scope

Every ExaBench task declares which knowledge source groups may be used as evidence. This constrains what the agent may retrieve and which environment documents are in scope.

Source codes map to the 10 groups defined in `docs/taxonomy/05_knowledge_sources.md`.

| Code | Group | Description | Primary Roles |
|------|-------|-------------|---------------|
| `ARCH_DOC` | System Architecture & Hardware Docs | Cluster topology, hardware specs, rack layouts, BoM, firmware | `system_designer`, `sysadmin` |
| `OPS_DOC` | Sysadmin & Operations Manuals | Queue config, LDAP/RBAC policy, backup procedures, change management | `sysadmin` |
| `FAC_DOC` | Facility & Infrastructure Docs | Cooling diagrams, BMS/DCIM config, P&ID, power distribution, setpoints | `facility_admin`, `system_designer` |
| `USR_DOC` | User Documentation & Help Resources | Onboarding guides, SLURM/PBS references, batch script templates, FAQs | `scientific_user`, `researcher` |
| `DATA_GOV` | Data Management & Governance | Backup/archival policy, data retention, GDPR, data transfer rules | `sysadmin`, `researcher` |
| `POLICY` | Organizational & Policy Documents | AUP, SLA, security policy, incident response plan, energy management | `sysadmin`, `facility_admin` |
| `ADMIN_DATA` | Administrative & Org Data | Project allocations, billing rules, vendor contracts, maintenance calendar | `system_designer`, `sysadmin` |
| `WIKI` | Knowledge Base / Wiki / Portal | How-to guides, troubleshooting pages, internal wiki, helpdesk KB | all roles |
| `REF_STD` | Reference Standards & Config Tables | ASHRAE setpoints, SLURM partition definitions, compliance standards | `facility_admin`, `system_designer` |
| `ENG_DOC` | Engineering & Upgrade Documents | RFPs, System Acceptance Tests, expansion plans, integration diagrams | `system_designer` |

### Usage in task specs

```json
{
  "knowledge_source_scope": ["USR_DOC", "WIKI"]
}
```

This field controls which document groups the environment exposes and which the agent is permitted to cite as evidence. See `src/exabench/schemas/task.py` for the canonical type definition.

---

## 4. Access Control & RBAC

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

## 5. Task Metadata Schema

Canonical fields for benchmark task records. The authoritative Pydantic definition is `src/exabench/schemas/task.py`.

| Key | Type | Purpose | Example |
|-----|------|---------|---------|
| `task_id` | `str` | Unique identifier | `"JOB-USR-003"` |
| `role` | `Role` | Persona context | `"scientific_user"` |
| `qcat` | `QCat` | Functional domain | `"JOB"` |
| `query_text` | `str` | User-facing prompt | `"Why did my job fail?"` |
| `difficulty` | `Difficulty` | Complexity tier | `"medium"` |
| `knowledge_source_scope` | `list[KnowledgeSourceCode]` | Permitted evidence groups | `["USR_DOC", "WIKI"]` |
| `allowed_tools` | `list[str]` | Tool whitelist | `["slurm", "docs"]` |
| `gold_evidence_refs` | `list[str]` | Expected evidence anchors | `["job_891234_oom"]` |
| `expected_answer_type` | `AnswerType` | Output form | `"diagnosis"` |
| `environment_id` | `str` | Snapshot linkage | `"env_01"` |
| `hard_fail_conditions` | `list[str]` | Automatic-fail triggers | `["fabricated_evidence"]` |
| `eval_criteria` | `EvalCriteria` | Scoring config | `{evaluation_mode: "semantic_match"}` |

---

## 6. Related Documents

- Role detail pages: `docs/taxonomy/roles/` (per-role query categories, priorities, example queries)
- Knowledge source taxonomy: `docs/taxonomy/05_knowledge_sources.md`
- Task schema: `src/exabench/schemas/task.py`
- Evaluation protocol: [06-evaluation](06-evaluation.md)
- Architecture: [03-architecture](03-architecture.md) § 4–5
