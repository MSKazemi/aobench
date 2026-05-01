# 03 — Benchmark Architecture (Design)

This page defines the **conceptual architecture** of ExaBench: the design
principles, the layers a benchmark item traverses, the entities that compose
the benchmark data model, and the execution workflow the system follows.

It answers the question:

> **How is the ExaBench benchmark structured as a *benchmark*, independent of
> any particular software implementation?**

For the **current implementation** of these concepts — the file layout under
`src/exabench/`, the executable scoring pipeline, and the actual dataset scope
— see [08 — System Architecture](08-system-architecture.md).

For the canonical evaluation protocol, trace schema, and result schema, see
[06 — Evaluation](06-evaluation.md).

---

## 1. Design principles

ExaBench's architecture is shaped by six principles. They are deliberately
stronger than those of generic agent benchmarks because HPC operational
contexts demand it.

| # | Principle | What it requires |
|---|-----------|------------------|
| 1 | **Reproducibility** | Every run targets a deterministic snapshot bundle and mock tool backend. No live cluster, no time-of-day drift. |
| 2 | **Realism** | Tasks reflect actual HPC user and operator scenarios — job failures, telemetry anomalies, energy reasoning, policy lookup, incident triage. |
| 3 | **Role-awareness** | The same scenario can require different evidence, actions, or refusals depending on the requester role. RBAC is part of the *task*, not a deployment concern. |
| 4 | **Traceability** | Evaluation considers the full observable interaction process — tool calls, observations, reasoning steps — not only the final answer. |
| 5 | **Governance-awareness** | Permission compliance, refusal correctness, and access-boundary enforcement are first-class scoring dimensions. |
| 6 | **Extensibility** | The architecture supports future additions (live agent connectors, multi-turn episodes, multi-agent orchestration) without breaking existing artifacts. |

---

## 2. Three benchmark layers

Every ExaBench item lives in three layers simultaneously.

### Layer A — Task

Defines the benchmark *item space*: the role-aware question, the success
criteria, and the expected output form.

> What is being asked?

### Layer B — Interaction

Defines how an agent is allowed to act: the tool surface exposed for the role,
the tool-access constraints, and the expected evidence pathway.

> How is the agent allowed to act?

### Layer C — Execution

Defines the deterministic world the task is executed in: the snapshot bundle,
the replayable telemetry, the mock tool backends, the run manifest.

> In what world is the task executed?

The combination of all three layers makes ExaBench an **interactive
operational competence** benchmark, not a question-answering benchmark.

---

## 3. Unit of evaluation

The smallest evaluable instance in ExaBench is:

> **Task + Role + Environment Snapshot + Agent Run + Result**

The same task text can produce different valid behaviours depending on role,
permission profile, environment state, and tool availability. ExaBench
therefore treats every benchmark item as a structured execution instance, not
a standalone prompt.

---

## 4. Core data model

ExaBench is organised around four primary entities. Their authoritative
schemas live in `src/exabench/schemas/`.

### 4.1 Task — `schemas/task.py`

A task captures *what is being asked* together with the constraints under
which it must be answered.

Required fields include `task_id`, `role`, `qcat`, `query_text`, `difficulty`,
`environment_id`, `allowed_tools`, `eval_criteria`, `hard_fail_conditions`,
`knowledge_source_scope`, and `aggregate_weight_profile`.

Two task spec types are used in practice:

| Type | Used for | File |
|------|----------|------|
| `TaskSpec` | 30 original JOB/MON/ENERGY tasks | `benchmark/tasks/specs/*.json` |
| `HPCTaskSpec` | 36 HPC v1 tasks (multi-role variants) | `benchmark/tasks/task_set_v1.json` |

Both flow through the same loader and scorer pipeline.

### 4.2 Environment — `schemas/snapshot.py`

A deterministic HPC world-state composed of scheduler state (`SlurmState`),
telemetry (`telemetry/*.parquet`, `*.csv`), policy (`rbac_policy.yaml`),
documentation (`docs/*.md`), and incident metadata (`incident_metadata.json`).
Every task references exactly one `environment_id`. See
[05 — Environments](05-environments.md) and
[environments-overview.md](../reference/environments-overview.md) for the format and the
inventory of all 20 bundles.

### 4.3 Trace — `schemas/trace.py`

The full record of one agent run. Includes the ordered list of `TraceStep`s
(messages, `ToolCall`s, `Observation`s), the final answer, hard-fail flag,
model name, prompt and completion token counts, and runtime metadata. The
trace schema is normative and unchanged across adapters.

### 4.4 Result — `schemas/trace.py` (`BenchmarkResult`)

The scored artifact for one trace. Includes per-dimension scores, the
aggregate score, the violation vector, the CuP-gated efficacy, the cost and
latency estimate, and pointers to the trace and run manifest.

---

## 5. Architectural execution workflow

A standard ExaBench run, abstracted from the implementation, follows seven
steps. The implemented version of this workflow with method names is in
[08 — System Architecture §4](08-system-architecture.md).

1. **Load task** — read the benchmark item with all role and execution
   constraints.
2. **Load environment snapshot** — initialise the deterministic world state
   referenced by `environment_id` and validate the bundle.
3. **Build the role-filtered tool surface** — only the tools and methods
   permitted for the task's role are exposed.
4. **Execute the agent run** — submit the task to the adapter, allow it to
   call tools, and capture the resulting trace.
5. **Score the run** — apply the scorer set defined by the task and the
   active scoring profile, compute the aggregate score, and detect hard-fail
   conditions.
6. **Persist the result** — write the trace, the result, and the run
   manifest under `data/runs/<run_id>/`.
7. **Optional: export to observability** — if a `BaseExporter` (e.g.
   `LangfuseExporter`) is configured, emit trace + scores.

This separates benchmark specification (Task + Environment), runtime
execution (Adapter + Tools), and evaluation logic (Scorers + Profile).

---

## 6. Tool environment model

ExaBench v0.1 uses **deterministic mock tools** rather than live SLURM,
Grafana, InfluxDB, BMS/DCIM, or production documentation systems. This is a
benchmarking choice, not a limitation of ambition: mock tools make
benchmarking reproducible, debuggable, publishable, and independent of
site-specific infrastructure. The connect-to-agent mode tracked in
`.claude/plans/2026-05-02-future-work.md` §C9 will additionally allow scoring
production agents that have their own cluster access.

The tool families implemented today are:

| Family | Methods (count) | Source |
|--------|-----------------|--------|
| `slurm` | `query_jobs`, `job_details`, `list_nodes`, `list_partitions`, … | `tools/slurm_tool.py` |
| `docs` | `retrieve` | `tools/docs_tool.py` |
| `rbac` | `check`, `get_allowed_tools`, `check_permission` | `tools/rbac_tool.py` |
| `telemetry` | `query_timeseries`, `query_node_metrics`, `query_memory_events` | `tools/telemetry_tool.py` |
| `facility` | `get_power_usage`, `query_node_power`, `query_rack_telemetry`, … | `tools/facility_tool.py` |

The full method-by-method catalog with role visibility and dangerous-arg
conditions is in `benchmark/configs/hpc_tool_catalog.yaml`.

---

## 7. Capability view (for reporting)

In addition to QCAT, every task is annotated with a capability group so that
benchmark reports can stratify by *what skill is being exercised*. The
capability dimensions used today are:

retrieval grounding, telemetry querying, cross-source fusion, diagnostic
reasoning, optimisation recommendation, role-aware response adaptation,
permission compliance, incident triage, energy-aware reasoning, action
planning.

Reports surface these as columns alongside Role × QCAT × Difficulty.

---

## 8. Page responsibilities

| Page | Responsibility |
|------|----------------|
| **03 — Architecture** (this page) | Conceptual structure of the benchmark |
| **04 — Implementation** | How the architecture is realised in `src/exabench/` |
| **05 — Environments** | Snapshot bundle format |
| **06 — Evaluation** | Scoring protocol, trace schema, result schema |
| **07 — Taxonomy** | Roles, QCATs, knowledge sources, RBAC tiers |
| **08 — System Architecture** | Authoritative current-state reference |

---

## 9. Bottom line

ExaBench is not a collection of HPC questions. It is a benchmark framework
for evaluating **interactive, tool-using, role-aware, governance-constrained
AI agent systems** in HPC environments. Its defining architectural elements
are:

- role-aware benchmark tasks
- deterministic environment snapshots
- a controlled tool surface with explicit RBAC
- a normative trace schema and structured result artifact
- a six-dimension multi-scorer pipeline with hard-fail semantics
- a reproducible execution architecture

The detailed evaluation protocol is defined in [06 — Evaluation](06-evaluation.md).
