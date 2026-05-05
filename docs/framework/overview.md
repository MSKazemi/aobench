# Overview

This page is the canonical statement of **what AOBench is, the principles it
applies, and the scope of the v0.1 release**. Other framework documents
elaborate on specific aspects (architecture, evaluation, taxonomy) but never
redefine the fundamentals collected here.

For an authoritative end-to-end description of the implemented system,
including the component map and the scoring pipeline, see
[System Architecture](../reference/system-architecture.md).

---

## 1. What AOBench is

**AOBench is a benchmark framework for evaluating AI agent systems in
High-Performance Computing (HPC) environments.**

AOBench is the *benchmark*. The agents being evaluated — research baselines
(`direct_qa`), commercial LLMs (`openai`, `anthropic`), reference HPC agents
(`mcp`), or third-party operational assistants such as ODA / ExaSage — are
*external* systems. AOBench connects to them through adapters, sends each a
task and a constrained tool surface, captures the resulting trace, and scores
the trace.

Because every run is grounded in a deterministic environment snapshot, results
are reproducible and portable: AOBench never requires access to a live
cluster.

---

## 2. The five benchmark principles

AOBench is designed to evaluate behaviours that ordinary QA benchmarks miss.

| Principle | Meaning |
|-----------|---------|
| **Role-aware** | The same operational question may require different answers, evidence scope, and refusal behaviour depending on the requester role (`scientific_user`, `sysadmin`, `facility_admin`, `researcher`, `system_designer`). |
| **Tool-using** | Agents are evaluated as systems that interact with controlled HPC tools (scheduler, telemetry, docs, RBAC, facility). |
| **Permission-aware** | Success requires respecting RBAC and policy boundaries. Forbidden tool calls and permission violations hard-fail the run regardless of the final answer. |
| **Trace-based** | Evaluation considers the execution trace — tool selection, arguments, sequence, evidence pathway — not only the final answer. |
| **Reproducible** | Runs target deterministic environment snapshots packaged under `benchmark/environments/`, not live infrastructure. |

These principles are checked by twelve scorers organised into six dimensions
(see [Evaluation](evaluation.md) and
[scoring-dimensions.md](scoring-dimensions.md)).

---

## 3. Implemented scope

The following table describes the system **as currently implemented**, with paths to authoritative artifacts.

| Item | Quantity | Authoritative source |
|------|----------|----------------------|
| Original tasks (JOB / MON / ENERGY) | 30 | `benchmark/tasks/specs/*.json` |
| HPC v1 tasks (Souza 2025 schema) | 36 | `benchmark/tasks/task_set_v1.json` |
| **Current task set (v3 — all 10 QCATs)** | **80** | `benchmark/tasks/specs/` |
| Environment snapshot bundles | 26 (`env_01`…`env_26`) | `benchmark/environments/` |
| Mock tool families | 5 (slurm, docs, rbac, telemetry, facility) | `src/aobench/tools/` |
| Tool methods catalogued | 16 | `benchmark/configs/hpc_tool_catalog.yaml` |
| Adapters | 4 — `direct_qa`, `openai`, `anthropic`, `mcp` | `src/aobench/adapters/` |
| Roles with tasks | 5 — `scientific_user`, `sysadmin`, `facility_admin`, `researcher`, `system_designer` | `src/aobench/schemas/task.py` |
| QCATs with tasks | 10 — all QCATs covered | [Taxonomy](taxonomy.md) |
| Scorers | 12 across 6 dimensions | `src/aobench/scorers/` |
| Scoring profiles | `alpha0_minimal`, `alpha1_grounding`, `default_hpc_v01` | `benchmark/configs/scoring_profiles.yaml` |
| Dataset split | 62 dev / 18 test (~22% held-out), frozen 2026-05-02 (v0.3) | `benchmark/tasks/dataset_splits.py` |
| Tests passing | 1048 | `tests/` |
| CLI commands | 9 sub-trees (run, validate, lite, report, compare, robustness, clear, leaderboard) | [`COMMANDS.md`](../reference/commands.md) |

---

## 4. Long-term goal

AOBench aims to be a **citable, reproducible, and extensible benchmark
standard** for comparing HPC-focused agentic systems before they are deployed
in real supercomputing or data-centre operations.

Beyond the offline mock-tool mode shipped in v0.1, the project plans two
extensions for future releases:

- **Connect-to-agent mode (§C9)** — adapters that drive HPC agents already
  deployed on or near clusters via HTTP / MCP / FastAPI. AOBench still never
  touches the cluster directly; the agent under test does.
- **In-situ stress testing** — using AOBench as a workload driver to
  measure latency, throughput, and correctness of production HPC agents
  under realistic load.

---

## 5. Where to go next

| If you want to… | Read |
|-----------------|------|
| Understand the implemented system end-to-end | [System Architecture](../reference/system-architecture.md) |
| Run the benchmark | [COMMANDS.md](../reference/commands.md) |
| Author a new task | [Implementation](implementation.md) and [Taxonomy](taxonomy.md) |
| Understand scoring | [Evaluation](evaluation.md) and [scoring-dimensions.md](scoring-dimensions.md) |
| Inspect available environments | [environments-overview.md](../reference/environments-overview.md) |
| Contribute or extend the framework | [How to Contribute](../about/contributing.md) and [Developer Guide](implementation.md) |
