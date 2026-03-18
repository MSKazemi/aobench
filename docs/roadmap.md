# Roadmap & Steps

## Purpose

This roadmap defines the execution plan for turning ExaBench from a conceptual HPC agent benchmark into a reproducible Python evaluation framework, a structured benchmark dataset, and a publishable scientific artifact.

## Current Status

## What I would build first

### Phase 1 — Minimal executable benchmark

The first goal is to produce a **small but fully runnable end-to-end benchmark pipeline**.

This phase should focus on the minimum components required to execute, trace, and score benchmark tasks under deterministic conditions.

### Build first

1. **Task schema and task loader**
    - canonical task model
    - task validation
    - task filtering by role, category, difficulty, and split
2. **Environment schema and environment loader**
    - canonical environment snapshot model
    - snapshot metadata validation
    - deterministic environment loading
3. **Two initial environment bundles**
    - `env_01`
    - `env_02`
4. **Three core mock tools**
    - `slurm` for scheduler and job inspection
    - `docs` for retrieval and evidence grounding
    - `rbac` for permission and access checks
5. **One initial agent adapter**
    - a single working adapter is enough for v0.1 seed execution
6. **One benchmark runner**
    - load task
    - load environment
    - expose allowed tools
    - invoke agent
    - capture outputs
7. **One trace writer**
    - persist canonical run traces as artifacts
8. **Three initial scorers**
    - `outcome`
    - `governance`
    - `efficiency`

### Goal of Phase 1

By the end of this phase, ExaBench should be able to run at least one benchmark task end to end and produce:

- a trace artifact
- a result artifact
- a basic scored outcome

---

### Phase 2 — Stronger benchmark

Once the first executable pipeline works, the next step is to improve benchmark quality and evaluation depth.

### Add next

- **Telemetry tool**
    - support monitoring and metric-based scenarios
- **Grounding scorer**
    - evaluate whether answers are supported by valid evidence
- **Tool-use scorer**
    - evaluate tool selection, sequence, and correctness of usage
- **HTML report generation**
    - produce human-readable benchmark summaries
- **Role × category slicing**
    - compare benchmark performance across user roles and QCAT categories
- **Repeated-run evaluation**
    - assess consistency across multiple runs of the same task

### Goal of Phase 2

By the end of this phase, ExaBench should move from a minimally runnable prototype to a **credible benchmark system** suitable for structured experiments and early paper results.

---

### Phase 3 — Advanced extensions

After the core benchmark is stable, the framework can be extended with broader capabilities and more advanced execution models.

### Add later

- **Robustness variants**
    - degraded inputs
    - ambiguous scenarios
    - repeated-run stability checks
- **Facility and energy tools**
    - support energy-aware and facility-admin tasks
- **MCP compatibility**
    - optional protocol-based tool integration
- **API service**
    - expose benchmark execution through a service interface if needed
- **Multi-agent execution mode**
    - support future orchestration or agent-to-agent workflows
- **Production agent integration**
    - connect ExaBench to agents deployed on HPC clusters with access to the real cluster (SLURM, telemetry, etc.)
    - enables stress testing of production agents under realistic load
    - agent uses its own HPC access; ExaBench drives tasks and evaluates responses

### Goal of Phase 3

This phase extends ExaBench beyond the minimal publishable benchmark toward a broader research and integration platform, including stress testing of production HPC agents.

---

## Milestones

### Milestone 1 — Schemas and loaders

Deliver:

- task schema models
- environment schema models
- task loader
- environment loader
- validation pipeline

### Milestone 2 — Tool layer

Deliver:

- tool base classes
- tool registry
- mock SLURM tool
- mock telemetry tool
- mock docs tool
- mock RBAC tool

### Milestone 3 — Runner and traces

Deliver:

- execution context
- adapter interface
- runner implementation
- canonical trace emission
- trace persistence

### Milestone 4 — Scoring

Deliver:

- scorer base class
- canonical scorer modules
- aggregate scorer
- hard-fail enforcement

### Milestone 5 — CLI and reporting

Deliver:

- CLI commands
- JSON result writer
- HTML benchmark report
- role/category slice tables
- failure taxonomy summary
- optional radar chart
- comparison output

### Milestone 6 — Seed benchmark execution

Deliver:

- at least one full end-to-end benchmark run
- one working agent adapter
- one deterministically loaded environment
- one fully scored task
- one generated HTML benchmark report

### Completed

- [x] Spec/design pages drafted (architecture, task schema, evaluation schema)
- [x] `05 — Task Database` converted into a live tracker structure
- [x] Task operational lifecycle fields defined (collection/validation/evidence/env-link/scoring/split/owners)
- [x] Controlled vocabulary for task readiness states defined

### In progress

- [~] Coverage matrix and readiness dashboard (moving from seed numbers to 30 real tasks)

### Next milestone

- [ ] First runnable Alpha-0: 1 task + 1 environment + 1 adapter + trace + result

## Phase 0 — Project Framing & v0.1 Scope Freeze

## ExaBench v0.1 Alpha-0

- [ ]  **Build the first executable ExaBench alpha using 10 tasks, 2 environments, and 1 end-to-end runner path**
    - Seed distribution (recommended): **10 tasks total**
    - 4 × JOB
    - 3 × MON
    - 3 × ENERGY
    - across the 3 roles
    - Seed environments (recommended): **2 environments first**
        - `env_01` — user OOM failure
        - `env_02` or `env_03` — queue congestion or node anomaly
        - For each of the first 2 environments, define:
            - actual folder path
            - `metadata.yaml`
            - required files
            - included sources
            - supported roles
            - supported categories
            - validation checklist
            - implementation status
    - Seed tasks examples: `JOB_USR_001`, `JOB_USR_002`, `JOB_SYS_001`, `MON_SYS_001`, `MON_SYS_002`, `ENERGY_FAC_001`, …
    - Each seed task must include at least: `task_id`, `title`, `role`, `qcat`, `difficulty`, `query_text`, `environment_id`, `allowed_tools`, `gold_evidence_refs`, `success_criteria`, `failure_modes`, `required_scorers`, `split_assignment`, `validation_status`, `scoring_readiness`
    - Minimum runnable slice (recommended)
        - 1 adapter
        - 1 task
        - 1 environment
        - 4 scorers: `outcome`, `tool_use`, `governance`, `efficiency`
        - (leave `grounding` and `robustness` for the second pass)

**Definition:** A minimal but real benchmark slice exists.

### Scope

- [ ]  10 real tasks
- [ ]  2 real environments
- [ ]  1 adapter
- [ ]  4 scorers
- [ ]  1 runner command
- [ ]  `trace.json`
- [ ]  `result.json`

### Exit criteria

- [ ]  10 tasks exist as actual records
- [ ]  2 environments exist as actual bundles
- [ ]  each seed task references a valid environment
- [ ]  one adapter runs at least one task end-to-end
- [ ]  one canonical trace is saved
- [ ]  one canonical result is saved

## Phase 1 — Benchmark Specification Freeze

**Goal:** Freeze the conceptual benchmark specification before implementation.

### Tasks

- [ ]  Review taxonomy subpages for operational completeness
- [ ]  Ensure each taxonomy page defines
    - scope
    - controlled vocabulary
    - relation to task schema
    - relation to scoring
- [ ]  Simplify any taxonomy page that is too descriptive
- [ ]  Identify whether each taxonomy page is
    - normative (used directly by benchmark design, annotation, scoring)
    - explanatory (background only)
- [ ]  Add explicit mapping from taxonomy dimensions to task fields and evaluation dimensions
- [ ]  Finalize roles/personas
- [ ]  Finalize QCAT categories
- [ ]  Finalize capability groups
- [ ]  Finalize policy/access model
- [ ]  Finalize knowledge-source taxonomy
- [ ]  Finalize benchmark item schema
- [ ]  Finalize task schema
- [ ]  Finalize environment snapshot schema

### Deliverables

- [ ]  `03 — Architecture & Benchmark Specification`
- [ ]  `04 — Taxonomy & Benchmark Dimensions`
- [ ]  `05 — Task Database` schema section
- [ ]  `06 — Environment Snapshots` schema section

### Exit criteria

- taxonomy pages are compact, operational, and benchmark-usable
- controlled vocabulary is stable
- task fields are frozen
- snapshot fields are frozen

## Phase 2 — Evaluation Protocol, Metrics & Trace Freeze

**Goal:** Define exactly how a run is judged.

### Tasks

- [ ]  Define benchmark run unit
    - Task
    - Role
    - Environment
    - Run
    - Score
- [ ]  Define outcome metrics
- [ ]  Define tool-use metrics
- [ ]  Define grounding metrics
- [ ]  Define governance / RBAC metrics
- [ ]  Define robustness metrics
- [ ]  Define efficiency metrics
- [ ]  Define trace schema
- [ ]  Define result schema
- [ ]  Define aggregate scoring method
- [ ]  Define pass/fail logic and reporting dimensions

### Deliverables

- [ ]  `08 — Evaluation Protocol, Metrics & Trace Schema`

### Exit criteria

- every task can reference explicit evaluation logic
- every run can produce a standard trace
- every result can be scored dimension-by-dimension

## Phase 3 — Dataset Operationalization

**Goal:** Turn the task database from design into an operational benchmark dataset.

### Tasks

- [x]  Convert `05 — Task Database` from a schema page into a live benchmark tracker
- [x]  Define task-level operational fields
    - `collection_status`
    - `validation_status`
    - `gold_evidence_status`
    - `environment_link_status`
    - `scoring_readiness`
    - `split_assignment`
    - `annotation_owner`
    - `review_status`
- [~] Define the 30-task v0.1 coverage matrix
- [~] Allocate target counts by role × category
- [ ]  Create the first 30 v0.1 task records
- [ ]  Attach to each task
    - success criteria
    - failure modes
    - gold evidence references
    - linked `environment_id`
    - scorer mapping
- [ ]  Define dataset split strategy
    - dev
    - public_test
    - hidden_test
- [x]  Define operational task states
    - blocked
    - in_progress
    - ready
- [ ]  Assign annotation ownership per task
- [ ]  Assign review ownership per task
- [ ]  Create a v0.1 dataset readiness dashboard

### Deliverables

- [ ]  Operational `05 — Task Database`
- [ ]  First 30 v0.1 task records
- [ ]  Coverage tracker
- [ ]  Validation tracker
- [ ]  Evidence completion tracker
- [ ]  Dataset split tracker
- [ ]  Dataset readiness dashboard

### Exit criteria

- all 30 v0.1 tasks exist
- every task has role, category, environment, evidence, and scorer mapping
- every task has validation, evidence, environment link, scoring readiness, split assignment
- no task marked `ready` is missing a verified environment link

## Phase 4 — Environment Operationalization

**Goal:** Define and materialize the first reproducible benchmark worlds.

### Tasks

- [ ]  Define the 5 canonical v0.1 snapshots
- [ ]  Assign scenario type to each
- [ ]  Define supported roles per snapshot
- [ ]  Define supported categories per snapshot
- [ ]  Define included sources and files
- [ ]  Define validation rules
- [ ]  Prepare snapshot metadata and layout
- [ ]  Initialize the canonical snapshot tracker in `06 — Environment Snapshots` with the first 5 v0.1 entries

### Deliverables

- [ ]  Operational `06 — Environment Snapshots`
- [ ]  Snapshot tracker table
- [ ]  First 5 environment bundles

### Exit criteria

- five snapshots are explicitly defined
- each snapshot has metadata
- task-to-environment mapping is complete
- snapshot tracker contains the v0.1 environments with valid `environment_id`

## Phase 5 — Runner, Tools, and Trace Implementation (Software Architecture)

**Goal:** Build the first executable benchmark pipeline.

### Tasks

- [ ]  Create repository scaffold
    - Minimum repo scaffold
        - `exabench/schemas/`
        - `exabench/tasks/`
        - `exabench/environments/`
        - `exabench/tools/`
        - `exabench/agents/`
        - `exabench/runners/`
        - `exabench/scorers/`
        - `exabench/reports/`
        - `exabench/cli/`
        - `data/tasks/`
        - `data/environments/`
        - `data/runs/`
        - `tests/`
- [ ]  Implement package structure
- [ ]  Implement task loader
- [ ]  Implement snapshot loader
- [ ]  Implement mock tool layer
- [ ]  Implement role-aware access checks
- [ ]  Implement agent adapter interface
- [ ]  Implement runner
- [ ]  Implement trace capture
- [ ]  Implement result serialization

### Deliverables

- [ ]  Finalized `07 — Software Architecture & Build Plan`
- [ ]  Runnable CLI prototype
- [ ]  End-to-end single-task execution
- [ ]  Saved trace artifact
- [ ]  Saved result artifact

### Exit criteria

- one task can be executed end-to-end
- one snapshot can be loaded deterministically
- trace output is valid against schema
- end-to-end path exists
    - load one task
    - load one environment
    - expose only allowed tools
    - run one adapter
    - capture trace
    - score result
    - write JSON artifacts

## Phase 6 — Scoring Engine & Baselines

**Goal:** Make ExaBench a real benchmark, not only a runner.

### Tasks

- [ ]  Implement outcome scorer
- [ ]  Implement tool-use scorer
- [ ]  Implement grounding scorer
- [ ]  Implement governance / RBAC scorer
- [ ]  Implement robustness scorer
- [ ]  Implement efficiency scorer
- [ ]  Implement aggregate score computation
- [ ]  Implement slicing by role/category/capability
- [ ]  Define three baseline styles
- [ ]  Run baselines on the v0.1 set
- [ ]  Analyze failures and refine weak tasks

### Deliverables

- [ ]  Scoring pipeline
- [ ]  Per-dimension score output
- [ ]  Aggregated benchmark result format
- [ ]  First baseline comparison

### Exit criteria

- at least one complete benchmark run over the 30-task set
- baseline comparison available
- failures categorized and interpretable

## Phase 7 — Reporting, Release, and Paper Preparation

**Goal:** Package ExaBench as a shareable benchmark artifact and paper-ready system.

### Tasks

- [ ]  Implement JSON report output
- [ ]  Implement HTML summary report
- [ ]  Add role/category breakdown tables
- [ ]  Add error taxonomy summary
- [ ]  Write benchmark README
- [ ]  Define release package structure
- [ ]  Prepare figures/tables for paper
- [ ]  Align benchmark terminology with paper sections

### Deliverables

- [ ]  Benchmark release package
- [ ]  Public repo documentation
- [ ]  Paper-ready evaluation summary
- [ ]  Reproducibility statement

### Exit criteria

- a third party could run the released benchmark
- benchmark results can be cited in the paper
- artifact structure is stable enough for public release

## Prompts (keep for action-item execution)

### Notion project review prompt

```python
Use the attached file as the system prompt.

Also use my attached/shared Notion page as project context:
https://www.notion.so/323924e5e1718190b905e5d0f271ee13?v=323924e5e171807f997d000cffe76f08&t=324924e5e1718052909e00a90a4dcb9e

Instructions:

1. Review the relevant pages and subpages carefully.
2. Use the Notion content as the source of project context.
3. Apply the attached system prompt fully when reasoning and responding.
4. If some pages are redundant, inconsistent, incomplete, or misplaced, point that out clearly.
5. Give a structured, expert-level answer.

Now answer this question:

[YOUR QUESTION]
```

### Roadmap execution prompt

```python
Use the attached file as the system prompt.
Also use my attached/shared Notion page as project context:
https://www.notion.so/323924e5e1718190b905e5d0f271ee13?v=323924e5e171807f997d000cffe76f08&t=324924e5e1718052909e00a90a4dcb9e

Instructions:

1. Review the relevant pages and subpages carefully.
2. Use the Notion content as the source of project context.
3. Apply the attached system prompt fully when reasoning and responding.
4. If some pages are redundant, inconsistent, incomplete, or misplaced, point that out clearly.
5. Give a structured, expert-level answer.

Now answer this question:
This my roadmap - but I did not update in view of the whcih task already done.
https://www.notion.so/Roadmap-Steps-323924e5e17181a9b9eafcc5d7dc0d01?t=325924e5e1718079874b00a990730246
So can you give which steps and tasks already done based on the checking all the pages of the 
https://www.notion.so/323924e5e1718190b905e5d0f271ee13?v=323924e5e171807f997d000cffe76f08&t=324924e5e1718052909e00a90a4dcb9e
give me what I did in fromat which I can find from the easyly in roadmap  

```

```
Use the attached file as the system prompt.
Also use my attached/shared Notion page as project context:
https://www.notion.so/323924e5e1718190b905e5d0f271ee13?v=323924e5e171807f997d000cffe76f08&t=324924e5e1718052909e00a90a4dcb9e

Instructions:

1. Review the relevant pages and subpages carefully.
2. Use the Notion content as the source of project context.
3. Apply the attached system prompt fully when reasoning and responding.
4. If some pages are redundant, inconsistent, incomplete, or misplaced, point that out clearly.
5. Give a structured, expert-level answer.

Now answer this question:
Check the page https://www.notion.so/Roadmap-Steps-323924e5e17181a9b9eafcc5d7dc0d01
and let me know that the text and materials are in correct places.
be clear and let me know which part should move from where to where. 
```