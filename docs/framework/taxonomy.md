# Taxonomy

This page consolidates the four taxonomic dimensions used to organise
ExaBench tasks: **roles**, **query categories (QCAT)**, **knowledge source
scopes**, and **access control / RBAC tiers**. It also documents the
canonical task metadata schema.

The authoritative Pydantic types live in `src/exabench/schemas/task.py`.

---

## 1. Roles & personas

A task's `role` field says **who is asking**. ExaBench defines five role
values; v0.1 scores three.

| Role | Schema value | Scored in v0.1? | Primary mission | Priority QCATs |
|------|-------------|-----------------|-----------------|----------------|
| **Normal user / scientific user** | `scientific_user` | ✅ | Run workloads, manage own data | JOB, MON, ENERGY (scored); DATA, PERF, DOCS (taxonomy) |
| **System administrator** | `sysadmin` | ✅ | Cluster reliability, scheduling, security | JOB, MON, ENERGY (scored); DATA, SEC, AIOPS (taxonomy) |
| **Facility admin** | `facility_admin` | ✅ | Power and cooling operations | MON, ENERGY (scored); FAC, AIOPS, DOCS (taxonomy) |
| Researcher | `researcher` | schema only | Telemetry analysis, performance, efficiency | AIOPS, PERF, ENERGY (taxonomy) |
| System designer / architect | `system_designer` | schema only | Capacity planning, topology, benchmarking | ARCH, PERF, ENERGY (taxonomy) |

The two unscored roles are present in `task.py` and in
`benchmark/configs/hpc_tool_catalog.yaml` so that tasks can be authored for
them, but no task currently uses them. Promotion to scored status is tracked
in `.claude/plans/2026-05-02-future-work.md` §B8.

---

## 2. Query categories (QCAT)

The `qcat` field labels the functional domain of the task. Ten QCATs are
defined in the taxonomy; v0.1 scores three.

| Code | Name | Scored in v0.1? | Description |
|------|------|-----------------|-------------|
| **JOB** | Job & Workflow Management | ✅ | Submitting, monitoring, debugging jobs; queues; batch scripts |
| **MON** | Monitoring & Observability | ✅ | Metrics, logs, alerts, dashboards, telemetry correlation |
| **ENERGY** | Power, Energy & Sustainability | ✅ | Power monitoring, PUE, energy-aware scheduling |
| PERF | Performance & Optimisation | taxonomy only | Profiling, bottlenecks, scaling studies |
| DATA | Data & Storage Management | taxonomy only | Filesystems, quotas, I/O, transfers |
| SEC | Security & Policy | taxonomy only | IAM, access control, compliance |
| FAC | Facility & Environmental | taxonomy only | Cooling, BMS/DCIM, rack health, alarms |
| ARCH | Architecture & Capacity | taxonomy only | Topology design, performance modelling |
| AIOPS | AI & Intelligent Operations | taxonomy only | Anomaly detection, predictive maintenance |
| DOCS | Documentation & Support | taxonomy only | FAQs, tutorials, troubleshooting |

The seven taxonomy-only QCATs are accepted by the schema and the validator,
but no scored tasks exist for them. Expansion to PERF, AIOPS, and SEC is part
of the v0.2 evaluation matrix (`.claude/plans/2026-05-02-future-work.md` §B2).

---

## 3. Knowledge source scope

`knowledge_source_scope: list[KnowledgeSourceCode]` constrains which document
groups the environment exposes and which the agent may cite as evidence.

| Code | Group | Description | Primary roles |
|------|-------|-------------|---------------|
| `ARCH_DOC` | System architecture & hardware | Cluster topology, hardware specs, rack layouts, BoM, firmware | `system_designer`, `sysadmin` |
| `OPS_DOC` | Sysadmin & operations manuals | Queue config, LDAP/RBAC policy, backup procedures, change mgmt | `sysadmin` |
| `FAC_DOC` | Facility & infrastructure | Cooling diagrams, BMS/DCIM config, P&ID, power distribution, setpoints | `facility_admin`, `system_designer` |
| `USR_DOC` | User documentation & help | Onboarding guides, SLURM/PBS reference, batch templates, FAQs | `scientific_user`, `researcher` |
| `DATA_GOV` | Data management & governance | Backup/archival, retention, GDPR, data transfer rules | `sysadmin`, `researcher` |
| `POLICY` | Organisational & policy | AUP, SLA, security policy, incident response, energy mgmt | `sysadmin`, `facility_admin` |
| `ADMIN_DATA` | Administrative & org data | Project allocations, billing, vendor contracts, maintenance calendar | `system_designer`, `sysadmin` |
| `WIKI` | Knowledge base / wiki / portal | How-to, troubleshooting pages, internal wiki, helpdesk KB | all |
| `REF_STD` | Reference standards & config tables | ASHRAE setpoints, partition definitions, compliance standards | `facility_admin`, `system_designer` |
| `ENG_DOC` | Engineering & upgrade documents | RFPs, system acceptance tests, expansion plans, integration diagrams | `system_designer` |

Example task usage:

```json
{
  "knowledge_source_scope": ["USR_DOC", "WIKI"]
}
```

The canonical type definition is in `src/exabench/schemas/task.py`.

---

## 4. Access control & RBAC

ExaBench enforces two-layered access control: **access tiers** govern data
exposure, **role permissions** govern tool calls.

### 4.1 Access levels (data exposure)

| Level | Holders | Scope |
|-------|---------|-------|
| **User-level** | scientific_user, researcher | Own jobs, public docs, safe how-to |
| **Elevated / privileged** | sysadmin, project managers | Software install, config, user management |
| **Restricted read-only** | researcher | Aggregated, anonymised telemetry |
| **Sensitive / admin-only** | sysadmin, security | Auth logs, security config, network |
| **Highly sensitive** | architect, facility_admin | Procurement, physical access design |

### 4.2 Access tiers (per-task)

| Tier | Description | Controls |
|------|-------------|----------|
| Tier-1 — Public / user-level | Safe docs, non-sensitive RAG | No approval |
| Tier-2 — Privileged | Real telemetry | Role-based validation |
| Tier-3 — Restricted read-only | Energy dashboards, KPIs | Read-only |
| Tier-4 — Highly sensitive | Procurement, cyber-security | Approval + isolation |

### 4.3 RBAC policy v1.1

Per-environment, per-role permissions live in
`benchmark/environments/env_NN/rbac_policy.yaml`. Each entry declares:

- `allowed_tools` — list of tool methods this role may call.
- `partition_access` — which SLURM partitions are visible / submittable.
- `access_tiers` — Tier-1 to Tier-4 as above.

The policies follow least-privilege: each role gets the minimum required
access. Privileged actions are logged in the trace (whether or not the
agent uses them) and contribute to the governance dimension.

The catalog of every tool method, its `role_visibility`, and its
`dangerous_args` conditions is in `benchmark/configs/hpc_tool_catalog.yaml`
(16 methods across the 5 tool families). Forbidden tool calls and
permission-denied propagation are absorbing hard-fails — see
[Evaluation §6](evaluation.md).

---

## 5. Task metadata schema

Authoritative Pydantic definition: `src/exabench/schemas/task.py`. The
following fields are required on every task spec; the validator
(`exabench validate benchmark`) enforces them.

| Field | Type | Purpose | Example |
|-------|------|---------|---------|
| `task_id` | `str` | Unique identifier | `"JOB-USR-003"` |
| `role` | `Role` | Persona context | `"scientific_user"` |
| `qcat` | `QCat` | Functional domain | `"JOB"` |
| `query_text` | `str` | User-facing prompt | `"Why did my job fail?"` |
| `difficulty` | `Difficulty` | `"easy"` / `"medium"` / `"hard"` / `"adversarial"` | `"medium"` |
| `difficulty_tier` | `int` | Numeric tier (1, 2, 3) | `2` |
| `knowledge_source_scope` | `list[KnowledgeSourceCode]` | Allowed evidence groups | `["USR_DOC", "WIKI"]` |
| `allowed_tools` | `list[str]` | Tool whitelist | `["slurm", "docs"]` |
| `gold_evidence_refs` | `list[str]` | Expected evidence anchors | `["job_891234_oom"]` |
| `expected_answer_type` | `AnswerType` | Output form | `"diagnosis"` |
| `environment_id` | `str` | Snapshot linkage | `"env_01"` |
| `hard_fail_conditions` | `list[str]` | Absorbing-failure triggers | `["fabricated_evidence"]` |
| `eval_criteria` | `EvalCriteria` | Scoring config | `{"evaluation_mode": "semantic_match"}` |
| `aggregate_weight_profile` | `str` | Profile name | `"default_hpc_v01"` |
| `scoring_readiness` | `Literal["draft","ready","locked"]` | Validation state | `"ready"` |
| `task_creation_date` | `date` | Authoring date (contamination tracking) | `"2026-02-10"` |
| `contamination_risk` | `Literal["clean","elevated","unknown"]` | Pre-training-leakage risk | `"clean"` |

`HPCTaskSpec` (used for the 36 v1 tasks in `task_set_v1.json`) extends
`TaskSpec` with `HPCRoleVariant` blocks for multi-role variants and
`HPCGroundTruth` for component-wise gold answers.

---

## 6. Authoritative schemas & related documents

- Task & role schema: `src/exabench/schemas/task.py`
- Trace & result schema: `src/exabench/schemas/trace.py`
- Tool catalog: `benchmark/configs/hpc_tool_catalog.yaml`
- RBAC policies: `benchmark/environments/env_NN/rbac_policy.yaml`
- Evaluation protocol: [Evaluation](evaluation.md)
- Architecture: [Architecture §4](architecture.md)
- Implemented system: [System Architecture](system-architecture.md)
