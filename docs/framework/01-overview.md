# 01 — Overview

**Owner:** Mohsen

This page is the **single source of truth** for what ExaBench is, its principles, and v0.1 scope. All other docs reference this page; they do not redefine these fundamentals.

---

## What ExaBench Is

**ExaBench** is a benchmark framework for evaluating **AI agent systems in High-Performance Computing (HPC) environments**.

Unlike ordinary QA datasets, ExaBench evaluates whether an agent can operate correctly in realistic HPC scenarios that require:

- multi-step reasoning
- tool use
- evidence grounding
- role-aware responses
- permission and policy compliance
- reproducible execution against deterministic environment snapshots

ExaBench does **not** implement HPC agents; it benchmarks external agents (e.g., ODA, ExaSage). See [architecture-clarification.md](../architecture-clarification.md) for details.

### Positioning

> **ExaBench is a benchmark framework for evaluating AI agents in HPC environments using role-aware tasks, deterministic HPC state snapshots, and trace-based scoring.**

### Long-term goal

To provide a **citable, reproducible, and extensible benchmark standard** for comparing HPC-focused agentic systems before they are deployed in real supercomputing and data-center operations.

---

## Five Benchmark Principles (v0.1 Freeze)

| Principle | Description |
|-----------|-------------|
| **Role-aware** | The same operational question may require different answers, evidence scope, and response boundaries depending on the requester role. |
| **Tool-using** | Agents are evaluated as systems that interact with controlled tools (scheduler, telemetry, docs, policy checks). |
| **Permission-aware** | Success includes respecting RBAC and policy boundaries, refusing unsafe requests, and avoiding inappropriate disclosure. |
| **Trace-based** | Evaluation considers the execution trace—tool selection, arguments, evidence path, and process validity—not only the final answer. |
| **Reproducible via environment snapshots** | Runs are grounded in deterministic environment snapshots rather than live infrastructure. |

---

## v0.1 Scope (Frozen)

### Roles
- `scientific_user`
- `sysadmin`
- `facility_admin`

### Task categories
- `JOB`
- `MON`
- `ENERGY`

### Size
- ~30 tasks
- ~5 environment snapshots

### Baseline styles
- `direct_qa`
- `rag_baseline`
- `tool_agent_baseline`

---

## Beyond v0.1 — Future Extensions

v0.1 uses mock tools and environment snapshots so agents do not need cluster access. Future versions will support:

- **Production agent integration:** Connect ExaBench to agents already deployed on HPC clusters (via HTTP, MCP, or other protocols). The agent under test uses its own access to the real HPC cluster.
- **Stress testing in production:** Use ExaBench as a workload driver to stress-test production HPC agents under realistic conditions, measuring latency, throughput, and correctness under load.

This extends the benchmark from offline evaluation (deterministic, reproducible) to in-situ evaluation (real cluster, production agents).

---

## Documentation Map

| Document | Purpose |
|----------|---------|
| [02-background](02-background.md) | Motivation, related work |
| [03-architecture](03-architecture.md) | Benchmark design: layers, entities, workflow |
| [04-implementation](04-implementation.md) | Software architecture, CLI, adapters, tools |
| [05-environments](05-environments.md) | Environment snapshot format and loading |
| [06-evaluation](06-evaluation.md) | Evaluation protocol, metrics, trace schema |
| [07-taxonomy](07-taxonomy.md) | Roles, categories, access control, query schema |
| [roadmap](../roadmap.md) | Implementation phases and milestones |
