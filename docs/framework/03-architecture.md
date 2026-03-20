# 03 — Architecture & Benchmark Specification

Owner: Mohsen

## Purpose

This page defines how the **ExaBench benchmark** is structured: its design principles, layers, entities, execution workflow, and relationships between tasks, environments, traces, and results.

ExaBench is a framework for evaluating AI agents that operate in HPC environments (e.g., ODA, ExaSage). This page specifies the **benchmark design** — what is being evaluated, in what world, and how — not the software implementation (see [04 — Implementation](04-implementation.md)).

It specifies:

- the benchmark design principles
- the benchmark layers (task, interaction, execution)
- the core entities (Task, Environment, Trace, Result)
- the unit of evaluation
- the execution architecture
- the minimum viable v0.1 scope

This page answers:

> **How is the ExaBench benchmark structured?**
> 

Detailed evaluation logic, scoring dimensions, trace schema, and pass/fail rules are defined in [06 — Evaluation](06-evaluation.md).

## v0.1 Scope Reference

This page follows the canonical v0.1 scope defined in [01 — Overview](01-overview.md).

Unless explicitly marked as future work, ExaBench v0.1 is fixed as: Roles `scientific_user`, `sysadmin`, `facility_admin`; Categories `JOB`, `MON`, `ENERGY`; ~30 tasks; ~5 environment snapshots; baselines `direct_qa`, `rag_baseline`, `tool_agent_baseline`.

## Canonical Principle Reference

Principles: role-aware, tool-using, permission-aware, trace-based, reproducible via environment snapshots. See [01 — Overview](01-overview.md).

---

## 1. Benchmark Design Principles

ExaBench is designed around six core principles.

### 1.1 Reproducibility

Benchmark runs must be repeatable across agents, models, and evaluation settings. ExaBench therefore relies on deterministic environment snapshots and mock tool backends rather than live production infrastructure.

### 1.2 Realism

Tasks should reflect realistic HPC user and operational scenarios, including job monitoring, telemetry inspection, policy lookup, incident diagnosis, and energy-aware reasoning.

### 1.3 Role-awareness

HPC environments are inherently multi-role. The same scenario may require different evidence, actions, and response boundaries depending on whether the requester is a user, researcher, sysadmin, facility operator, or HPC architect.

### 1.4 Traceability

ExaBench evaluates not only final outputs but also the observable interaction process, including tool calls, retrieved evidence, and execution steps.

### 1.5 Governance-awareness

Agents must be evaluated in the presence of permissions, policy constraints, and safe-response expectations. Correct refusal, redaction, and access-boundary compliance are part of benchmark design.

### 1.6 Extensibility

The framework should support future extensions such as richer tools, live backends, multi-agent execution (benchmarking systems where the agent under test is a multi-agent orchestration; ExaBench still connects to a single entry point), human-in-the-loop workflows, and broader HPC operational coverage.

---

## 2. Three-layer Benchmark Model

ExaBench is structured as a three-layer benchmark.

### Layer A — Task Benchmark

This layer defines the benchmark item space.

It includes:

- role-aware task/query corpus
- task categories and difficulty
- expected output forms
- success conditions
- evidence expectations

This layer answers:

> **What is being asked?**
> 

### Layer B — Interaction Benchmark

This layer defines how the agent is expected to interact with the environment.

It includes:

- available tools
- tool-access constraints
- role-aware access boundaries
- expected interaction patterns
- evidence pathways

This layer answers:

> **How is the agent allowed to act?**
> 

### Layer C — Execution Benchmark

This layer defines the reproducible world in which the task is executed.

It includes:

- deterministic HPC environment snapshots
- replayable telemetry and incident state
- mock tool backends
- execution logging
- benchmark artifacts

This layer answers:

> **In what world is the task executed?**
> 

Together, these three layers allow ExaBench to evaluate not only answer quality but also **interactive operational competence in realistic HPC settings**.

---

## 3. Unit of Evaluation

The basic unit of evaluation in ExaBench is:

> **Task + Role + Environment Snapshot + Agent Run + Result**
> 

This is important because a benchmark instance is not merely a question-answer pair. It is a fully specified evaluation unit in which correct behavior depends on:

- the **task**
- the **requester role**
- the **environment snapshot**
- the **agent’s interaction behavior during the run**

A result is produced from the run and later interpreted by the evaluation protocol defined in [06-evaluation](06-evaluation.md).

### 3.1 Why this matters

The same task text may yield different valid behavior depending on:

- permission level
- available evidence
- environment state
- tool availability
- operational constraints

ExaBench therefore treats the benchmark item as a structured execution instance, not as a standalone prompt.

## 4. Taxonomic Dimensions of a Benchmark Item

Each ExaBench benchmark item is associated with a structured taxonomy. At minimum, a benchmark item should include:

- **Role / Persona** — who is asking
- **QCAT Category** — the primary HPC query category
- **Capability Group** — the main competence being exercised
- **Access / Policy Profile** — what data or actions are allowed
- **Knowledge Source Scope** — which knowledge source groups (from `docs/taxonomy/05_knowledge_sources.md`) may be used as evidence
- **Difficulty Level** — expected complexity of execution or reasoning
- **Expected Output Type** — narrative answer, diagnosis, recommendation, table, structured JSON, and so on

This taxonomy makes ExaBench more than a task list. It supports controlled slicing by role, category, capability, governance profile, and task type. See [07-taxonomy](07-taxonomy.md).

---

## 5. Core Benchmark Data Model

ExaBench is built around four primary entities: **Task**, **Environment**, **Trace**, and **Result**.

### 5.1 Task

A `Task` represents one benchmark item.

A task defines:

- what is being asked
-under which role and access conditions
-which environment is required
-what successful task completion means
-which evidence or outputs are expected

Typical task fields include:

- `task_id`
-`role`
-`qcat`
-`category`
-`difficulty`
-`query_text`
-`required_capabilities`
-`allowed_tools`
-`knowledge_source_scope` — list of `KnowledgeSourceCode` values from the knowledge source taxonomy
-`access_tier`
-`expected_outputs`
-`gold_evidence_refs`
-`permission_profile`
-`environment_id`
-`success_criteria`
-`failure_modes`
-`answer_schema`

Task-level evaluation fields are defined in [07-taxonomy](07-taxonomy.md) and linked to [06-evaluation](06-evaluation.md).

### 5.2 Environment

An `Environment` represents a deterministic HPC world-state used for execution.

An environment may include:

- scheduler state
-telemetry state
-topology state
-policy state
-incident context
-documentation scope

Each task references exactly one valid `environment_id`, ensuring that execution is reproducible and does not depend on live infrastructure.

### 5.3 Trace

A `Trace` records the observable behavior of an agent during one run.

At a structural level, the trace captures:

- interaction steps
-tool invocations
-observations returned from tools
-final output
-runtime metadata

The formal trace schema is specified in [06-evaluation](06-evaluation.md).

### 5.4 Result

A `Result` stores the benchmark outcome of one evaluated run.

At a structural level, it links:

- the task
-the environment
-the run
-the trace
-the evaluation output

The formal result schema and score interpretation are defined in [06-evaluation](06-evaluation.md).


---

## 6. Architectural Execution Workflow

A standard ExaBench run follows this architecture-level workflow:

1. **Load task**
    - Read the benchmark item and its role, environment, and execution constraints.
2. **Load environment snapshot**
    - Initialize the deterministic HPC state referenced by the task.
3. **Expose allowed tools**
    - Provide only the tools and permissions allowed for the task and role.
4. **Execute agent run**
    - Submit the task input and allow the agent to interact with the environment.
5. **Capture execution trace**
    - Record tool calls, observations, outputs, and runtime metadata.
6. **Produce result artifact**
    - Store the run output for later evaluation under the protocol defined in [06-evaluation](06-evaluation.md).

This workflow ensures a clean separation between:

- benchmark specification
- runtime execution
- evaluation logic



---

## 7. Tool Environment Model

### 7.1 v0.1 Tool Philosophy

ExaBench v0.1 should not depend on live SLURM, HPC monitoring tools (Grafana, InfluxDB, etc.), facility energy monitoring, or production documentation systems.

Instead, v0.1 should use **deterministic mock tools** backed by local files, SQLite, or structured snapshot bundles. This makes the benchmark reproducible, portable, easier to debug, and easier to publish.

### 7.2 Initial Tool Families

The initial tool layer may include mock interfaces for:

- scheduler/job inspection
- telemetry querying
- document retrieval
- RBAC or policy checks
- facility-state inspection

Illustrative examples:

- `slurm.query_jobs()`
-`slurm.job_details(job_id)`
- `telemetry.query(metric, labels, time_range)`
-`docs.retrieve(query)`
-`rbac.check(user_role, resource)`
-`facility.get_rack_state(rack_id)`

The exact interface definitions belong in the implementation design and tool architecture pages.

### 7.3 Why mock tools first

Mock tools are preferred initially because they:

- avoid site-specific infrastructure coupling
- support deterministic benchmarking
- simplify debugging
- support artifact release and reproducibility
- reduce operational overhead for external adopters


## 8. Environment Snapshot Model

Each benchmark environment should be packaged as a deterministic snapshot bundle referenced by `environment_id`.

A snapshot may include artifacts such as:

- scheduler state
- telemetry timeseries
- power or energy data
- topology metadata
- policy definitions
- document subsets — keyed by `KnowledgeSourceCode` (e.g., `USR_DOC`, `OPS_DOC`, `FAC_DOC`); see `docs/taxonomy/05_knowledge_sources.md`
- incident metadata

This design allows ExaBench to model realistic HPC conditions without depending on a live cluster.

The operational registry of environments is defined in [05-environments](05-environments.md).

---

## 9. Capability-oriented Benchmark View

In addition to task categories, ExaBench can organize tasks by capability group. This makes explicit which forms of agent competence are being exercised.

Illustrative capability groups include:

- retrieval grounding
- telemetry querying
- cross-source fusion
- diagnostic reasoning
- optimization recommendation
- role-aware response adaptation
- permission compliance
- incident triage
- energy-aware reasoning
- action planning

This capability layer supports more interpretable reporting and targeted benchmark expansion.

In addition to task categories, ExaBench can organize tasks by capability group. This makes explicit which forms of agent competence are being exercised.

Illustrative capability groups include:

- retrieval grounding
- telemetry querying
- cross-source fusion
- diagnostic reasoning
- optimization recommendation
- role-aware response adaptation
- permission compliance
- incident triage
- energy-aware reasoning
- action planning

This capability layer supports more interpretable reporting and targeted benchmark expansion.

---

## 10. Minimal ExaBench v0.1 Scope

ExaBench v0.1 is intentionally small but publishable.

### Roles

- scientific_user
- sysadmin
- facility_admin

### Categories

- JOB
- MON
- ENERGY

### Dataset size

- approximately 30 tasks

### Environment coverage

- approximately 5 snapshots

### Baseline styles

- direct QA
- RAG-style retrieval baseline
- tool-using agent baseline

This scope is designed to validate the framework architecture before broader expansion.

ExaBench v0.1 is intentionally small but publishable.

### Roles

- scientific_user
- sysadmin
- facility_admin

### Categories

- JOB
- MON
- ENERGY

### Dataset size

- approximately 30 tasks

### Environment coverage

- approximately 5 snapshots

### Baseline styles

- direct QA
- RAG-style retrieval baseline
- tool-using agent baseline

This scope is designed to validate the framework architecture before broader expansion.

---

## 11. Repository and Implementation Mapping

The ExaBench repository structure (aligned with the [README](../README.md)):

```
ExaBench/
├── src/exabench/           # Python package (pip install exabench)
│   ├── schemas/            # Pydantic data models (environment, snapshot, task, result, trace, trace_annotation)
│   ├── taxonomy/           # HPC error taxonomy YAML (hpc_error_taxonomy.yaml — 24 TRAIL-adapted leaf categories)
│   ├── environment/        # Snapshot loading + validation (snapshot_loader, snapshot_validator)
│   ├── loaders/            # Task and environment loaders
│   ├── tools/              # Mock HPC tools (SLURM, telemetry, docs, RBAC, facility)
│   ├── adapters/           # Agent backend adapters
│   ├── runners/            # Execution runner and trace writer
│   ├── scorers/            # Scoring engine (outcome, governance, efficiency, error_annotator)
│   ├── reports/            # Report generation
│   ├── utils/              # Shared utilities
│   └── cli/                # exabench run / validate commands
│
├── benchmark/              # Benchmark dataset (static source data)
│   ├── tasks/specs/        # Task specification files (JSON)
│   ├── environments/       # HPC state snapshot bundles (env_01–env_20)
│   ├── configs/            # Scoring profiles, tool registry
│   └── qa/                 # ExaBench-QA dataset (query corpus)
│
├── scripts/                # Utility scripts (generate_bundles.py, check_coverage.py)
├── data/runs/              # Runtime artifacts (traces, results — gitignored)
├── tests/                  # Unit and integration tests
└── docs/                   # Documentation
    └── framework/          # Framework design documents (01–07)
```

Detailed implementation interfaces, CLI commands, and build milestones are in [04 — Implementation](04-implementation.md).

---

## 12. Page Responsibilities in the ExaBench Design

To keep the framework consistent, page responsibilities are separated as follows:

| Page | Responsibility |
|------|----------------|
| **03 — Architecture** (this page) | Benchmark structure, entities, workflow |
| **04 — Implementation** | Software architecture, CLI, adapters, tools |
| **05 — Environments** | Environment snapshot format and registry |
| **06 — Evaluation** | Scoring, trace schema, result schema |
| **07 — Taxonomy** | Roles, categories, task schema, access control |

---

## 13. Bottom Line

ExaBench is not just a collection of HPC questions. It is a benchmark framework for evaluating **interactive, tool-using, role-aware, and governance-constrained AI agent systems** in HPC environments.

Its defining architectural elements are:

- role-aware benchmark tasks
- deterministic environment snapshots
- controlled tool exposure
- traceable agent interaction
- structured result artifacts
- reproducible execution architecture

This page provides the architectural foundation of ExaBench. The detailed evaluation protocol is defined separately in [06-evaluation](06-evaluation.md).

---