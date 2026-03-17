# 00 — Project Framing & v0.1 Scope

Owner: Mohsen

## Purpose

This page defines the foundational framing of **ExaBench** and freezes the scope of the first implementable version of the benchmark. It serves as the single reference point for what ExaBench is, why it exists, what is included in **v0.1**, and what is intentionally deferred to later versions.

This page should be treated as the canonical framing page for:

- the README
- the paper introduction
- the roadmap
- the benchmark specification

---

## 1 — What ExaBench Is

**ExaBench** is a benchmark framework for evaluating **AI agent systems in High-Performance Computing (HPC) environments**.

Unlike ordinary QA datasets, ExaBench evaluates whether an agent can operate correctly in realistic HPC scenarios that require:

- multi-step reasoning
- tool use
- evidence grounding
- role-aware responses
- permission and policy compliance
- reproducible execution against deterministic environment snapshots

In other words, ExaBench is not only about whether an answer is correct, but whether an agent behaves correctly as an **interactive operational system**.

---

## 2 — Problem Statement

AI agents are increasingly being proposed for HPC support, operations, monitoring, telemetry analysis, and user assistance. However, there is currently no benchmark that evaluates such agents under the actual constraints of HPC environments.

Existing benchmarks cover:

- general assistants
- web agents
- software engineering agents
- enterprise workflow agents
- tool-using agents
- cloud-operations agents

But they do not jointly evaluate the combination required in HPC:

- scheduler-aware reasoning
- telemetry and monitoring interpretation
- document and policy grounding
- role-conditioned answers
- permission-sensitive behavior
- reproducible operational-state evaluation

ExaBench is motivated by this gap.

---

## 3 — Positioning Statement

> **ExaBench is a benchmark framework for evaluating HPC agent systems using role-aware tasks, deterministic HPC state snapshots, and trace-based scoring.**
> 

This is the core one-sentence description of the project and should remain stable across the workspace.

---

## 4 — Benchmark Framing

ExaBench frames HPC agent evaluation as a benchmark of **interactive, tool-using, role-aware, permission-constrained operational behavior**, rather than a simple question-answering task.

The benchmark is evaluated not only by final answer quality, but also by:

- whether the agent used the right tools
- whether the agent respected role and access constraints
- whether the response was grounded in valid evidence
- whether the execution trace was valid and reproducible

The canonical principle set for ExaBench v0.1 is frozen in **4.1** and must remain consistent across the roadmap, architecture, README, and paper draft.

## 4.1 — Canonical Benchmark Principles (v0.1 Freeze)

For ExaBench v0.1, the benchmark is explicitly defined by the following canonical principles:

- **role-aware**
    
    The same operational question may require different answers, evidence scope, and response boundaries depending on the requester role.
    
- **tool-using**
    
    Agents are evaluated as systems that interact with controlled tools such as scheduler queries, telemetry access, documentation retrieval, and policy checks.
    
- **permission-aware**
    
    Benchmark success includes respecting RBAC and policy boundaries, refusing unsafe or unauthorized requests, and avoiding inappropriate disclosure.
    
- **trace-based**
    
    Evaluation considers not only the final answer, but also the execution trace, including tool selection, tool arguments, evidence path, and process validity.
    
- **reproducible via environment snapshots**
    
    Benchmark runs are grounded in deterministic environment snapshots rather than live infrastructure, so results are repeatable, comparable, and publishable.
    

This five-part principle set is the canonical ExaBench v0.1 framing and should remain consistent across the roadmap, README, paper draft, architecture pages, and implementation notes.

## 4.2 — Normative v0.1 Freeze

The following decisions are considered **frozen for ExaBench v0.1** and should be treated as canonical across the workspace:

### Canonical benchmark principles

- role-aware
- tool-using
- permission-aware
- trace-based
- reproducible via environment snapshots

### Canonical v0.1 scope

- Roles:
    - `scientific_user`
    - `sysadmin`
    - `facility_admin`
- Task categories:
    - `JOB`
    - `MON`
    - `ENERGY`
- Benchmark size:
    - approximately `30 tasks`
- Environment coverage:
    - approximately `5 environment snapshots`
- Baseline styles:
    - `direct_qa`
    - `rag_baseline`
    - `tool_agent_baseline`

### Normative rule for downstream pages

All downstream pages must **inherit** this framing and scope.

They may refine implementation details, schemas, mappings, and evaluation logic, but they should **not redefine** the canonical benchmark principles or the v0.1 scope unless this page is explicitly updated first.

---

## 5 — Core Research Gap

No existing benchmark, to our knowledge, simultaneously provides:

- an **HPC-native tool environment**
- **role-aware task variants**
- **deterministic operational-state snapshots**
- **permission and governance scoring**
- **trace-based evaluation of agent behavior**
- **energy- and facility-aware benchmark tasks**

This is the central gap that ExaBench addresses.

---

## 6 — ExaBench v0.1 Scope

This section defines the first concrete and publishable version of ExaBench.

### v0.1 objective

ExaBench v0.1 aims to establish a **minimal but coherent benchmark prototype** that is sufficient to:

- demonstrate the benchmark concept
- support early implementation
- evaluate baseline agent configurations
- provide a foundation for a scientific paper

### Included in v0.1

ExaBench v0.1 includes:

### Roles

- `scientific_user`
- `sysadmin`
- `facility_admin`

### Task categories

- `JOB`
- `MON`
- `ENERGY`

### Benchmark size

- approximately **30 tasks**
- approximately **5 environment snapshots**

### Benchmark properties

- deterministic offline evaluation
- mock tools instead of live production systems
- trace capture for each run
- multi-dimensional scoring
- baseline comparisons across simple QA / RAG / tool-agent styles

### Baseline styles in v0.1

- `direct_qa`
- `rag_baseline`
- `tool_agent_baseline`

---

## 7 — What v0.1 Includes Conceptually

The first version of ExaBench should already support the following benchmark logic:

### 7.1 Task layer

A structured task dataset where each item includes:

- task text
- role
- category
- allowed tools
- expected evidence
- success criteria
- failure modes
- linked environment snapshot

### 7.2 Environment layer

A deterministic HPC state bundle containing selected combinations of:

- scheduler state
- telemetry data
- energy / power signals
- policy and RBAC information
- documentation context
- incident metadata

### 7.3 Interaction layer

A controlled tool interface using mock tools such as:

- scheduler queries
- telemetry queries
- documentation retrieval
- permission checks

### 7.4 Evaluation layer

A run should be scored using:

- task success
- tool correctness
- evidence grounding
- policy compliance
- robustness
- efficiency

---

## 8 — What v0.1 Does Not Include

To keep the project focused, ExaBench v0.1 does **not** aim to include:

- live cluster integrations
- full production telemetry backends
- large-scale public leaderboard infrastructure
- multimodal evaluation
- long-horizon autonomous workflow benchmarks
- complex multi-agent orchestration
- site-specific deployment packages
- full benchmark industrialization

These belong to later stages such as **v0.2** or **v1.0**.

---

## 9 — Minimal Deliverables for v0.1

The minimum outputs expected for ExaBench v0.1 are:

1. a stable benchmark framing
2. a frozen taxonomy for roles, categories, capabilities, and access constraints
3. a seed task database of about 30 benchmark tasks
4. a small environment-snapshot set of about 5 scenarios
5. a trace schema for benchmark runs
6. a first scoring protocol
7. at least a small number of baseline evaluation runs
8. benchmark documentation suitable for paper writing and repo README use

---

## 10 — Success Criteria for Phase 0

**Phase 0 — Project Framing** is complete when:

- the one-sentence positioning statement is finalized
- the canonical benchmark-principle set is frozen
- the canonical v0.1 scope is frozen
- explicit non-scope items for v0.1 are documented
- downstream pages reference this page as the canonical framing source
- README and paper-introduction text can be derived directly from this page without reinterpretation

---

## 11 — Relationship to the Rest of the Workspace

This page is the top-level framing page for the rest of the ExaBench structure.

### Related pages

- **01 — Motivation / Vision**
    
    explains why the benchmark is needed
    
- **02 — Related Work / Positioning**
    
    shows how ExaBench differs from prior work
    
- **03 — Architecture & Benchmark Specification**
    
    defines the benchmark structure and execution model
    
- **04 — Taxonomy & Benchmark Dimensions**
    
    defines the dimensions used to organize tasks and evaluation
    
- **05 — Task Database**
    
    operationalizes the benchmark into benchmark items
    
- **06 — Environment Snapshots**
    
    defines the deterministic operational states used during evaluation
    
- **07 — Software Architecture & Build Plan**
    
    describes how the benchmark framework will be implemented in Python
    
- **08 — Evaluation Protocol, Metrics & Trace Schema**
    
    defines the scoring and run-evaluation model
    

---

## 12 — Concise Novelty Claim

> **ExaBench is, to our knowledge, the first benchmark framework that unifies HPC-native tools, role-aware tasks, deterministic operational snapshots, and trace-based evaluation for AI agent systems in HPC environments.**
> 

---

## 13 — Bottom Line

ExaBench shifts the evaluation question from:

> “Can an LLM answer HPC questions?”
> 

to the much stronger question:

> **“Can an AI agent operate reliably, safely, and efficiently in HPC environments under realistic tool, role, and policy constraints?”**
> 

That is the central framing of the project.

---