# Adapters & Tools — Plain-English Overview

A quick guide to how adapters and tools work in ExaBench.

---

## Tools

**What they are:** Mock HPC services that agents call during a run. They simulate scheduler queries, docs lookups, telemetry, and RBAC checks.

| What | Description |
|------|-------------|
| **Purpose** | Answer tool calls from the agent by reading data from the environment snapshot |
| **Data source** | `benchmark/environments/<env_id>/` — JSON, CSV, YAML files |
| **Role awareness** | Behavior changes by role (e.g. `scientific_user` sees only their own jobs) |
| **Examples** | `slurm__query_jobs`, `slurm__job_details`, `docs__retrieve`, `telemetry__query_memory_events`, `rbac__check`, `facility__query_node_power`, `facility__query_rack_telemetry` |

**Flow:** Agent calls a tool → tool reads env data → returns a result (or permission denied).

---

## Adapters

**What they are:** Bridges to different agent backends (OpenAI, Azure, a stub, etc.). They orchestrate the task loop and produce a trace.

| What | Description |
|------|-------------|
| **Purpose** | Run the agent on a task; mediate between the agent and tools until an answer is produced |
| **Input** | `ExecutionContext` — task, environment, tools |
| **Output** | A `Trace` — steps, tool calls, observations, final answer |
| **Examples** | `direct_qa` — stub that returns a placeholder with no tools; `openai` — OpenAI/Azure API with function calling |

**Flow:** Receive task + context → send to agent → when agent wants tools, call tools and feed results back → repeat until agent stops with a final answer → return trace.

**Connect-to-agent mode (planned post-v0.1):** New adapters will invoke external HPC agents (ODA, ExaSage, …) deployed on or near clusters via HTTP / MCP / FastAPI. ExaBench connects to the agent's API and scores its trace; ExaBench never needs direct access to real SLURM or the cluster.

---

## How They Work Together

```
┌─────────────────────────────────────────────────────────────┐
│  Runner                                                     │
│  1. Loads task + environment (deterministic snapshot)       │
│  2. Builds ToolRegistry — methods filtered by role          │
│  3. Passes task, tools → Adapter; receives Trace back       │
│  4. Passes Trace + task → Scorers; returns BenchmarkResult  │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│  Adapter  (e.g. OpenAIAdapter)                              │
│  • Sends task.query_text + tool schemas → LLM               │
│  • When LLM calls a tool → ToolRegistry.dispatch()   ─────┐ │
│  • Appends [tool call + observation] as a TraceStep  ◄────┘ │
│  • Repeats until LLM gives a final answer  (≤ 10 rounds)    │
│  • Returns completed Trace                                  │
└──────────────────────────────┬──────────────────────────────┘
                    dispatch   │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│  Tools  (slurm · docs · telemetry · rbac · facility)        │
│  • Run in-process — no external APIs                        │
│  • Read from env bundle (deterministic snapshot)            │
│  • Wrong role → permission_denied observation               │
│  • Return JSON observation → Adapter                        │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               │  ← Adapter returns completed Trace
                               ▼
┌─────────────────────────────────────────────────────────────┐
│  Scorers  (invoked by Runner · AggregateScorer)             │
│  • OutcomeScorer     — final answer vs gold                 │
│  • ToolUseScorer     — tool selection & argument quality    │
│  • GovernanceScorer  — RBAC compliance, permission checks   │
│  • GroundingScorer   — answer grounded in observations      │
│  • EfficiencyScorer  — step count  (≤ 5 steps → 1.0)        │
│                                                             │
│  → BenchmarkResult: aggregate_score (0–1) + DimensionScores │
└─────────────────────────────────────────────────────────────┘
```

---

## Tool Reference

| Tool | Methods | Data source | Notes |
|------|---------|-------------|-------|
| `slurm` | `query_jobs`, `job_details`, `list_nodes`, `list_partitions` | `slurm/slurm_state.json`, `slurm/job_details.json` | Role-aware: `scientific_user` sees own jobs only |
| `docs` | `retrieve` | `docs/*.md` | Keyword search over documentation files |
| `telemetry` | `query_memory_events`, `list_metrics` | `telemetry/*.csv` | Memory event time series |
| `rbac` | `check` | `policy/*.yaml` | Permission checks by role + resource + action |
| `facility` | `query_node_power`, `query_cluster_energy`, `query_rack_telemetry`, `list_inventory` | `power/*.csv`, `rack/*.csv`, `inventory/*.csv` | For `facility_admin` role; ENERGY tasks |

## Scorers Reference

| Scorer | Dimension | What it measures |
|--------|-----------|-----------------|
| `OutcomeScorer` | `outcome` | Quality of final answer vs gold (exact / semantic / numeric match) |
| `ToolUseScorer` | `tool_use` | Tool selection coverage, precision, no redundancy |
| `GroundingScorer` | `grounding` | Fraction of answer's key claims supported by tool observations |
| `GovernanceScorer` | `governance` | RBAC compliance — penalises permission violations |
| `EfficiencyScorer` | `efficiency` | Step count efficiency (≤5 steps = 1.0, ≥20 = 0.0) |

## Scoring Profiles

| Profile | Use when | grounding weight |
|---------|----------|-----------------|
| `alpha0_minimal` | Tasks with no tool expectation / stubs | 0.00 |
| `alpha1_grounding` | Tasks where tool evidence is expected | 0.20 |
| `default_hpc_v01` | Full production benchmark | 0.15 |

---

## One-Line Summary

| Component | Role |
|-----------|------|
| **Tools** | Simulate HPC APIs — read env data, enforce permissions |
| **Adapters** | Connect to agent backends — drive the task loop, use tools when the agent requests them |
| **Scorers** | Evaluate the trace on 5 dimensions and aggregate into one score |
