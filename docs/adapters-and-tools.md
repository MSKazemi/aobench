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
| **Examples** | `slurm__query_jobs`, `slurm__job_details`, `docs__retrieve`, `telemetry__query_memory_events`, `rbac__check` |

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

---

## How They Work Together

```
┌─────────────────────────────────────────────────────────────┐
│  Runner                                                     │
│  1. Loads task + environment                                │
│  2. Builds tools (pointing at env data)                     │
│  3. Passes task, env, tools → adapter                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Adapter (e.g. OpenAI)                                      │
│  • Sends task.query_text to the LLM                         │
│  • Exposes tools as functions to the LLM                    │
│  • When LLM calls a tool → adapter calls tools_registry     │
│  • Tools read from env and return data                      │
│  • Adapter records trace and returns it                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Tools (slurm, docs, telemetry, rbac)                       │
│  • Run in-process, no external APIs                         │
│  • Read from env bundle (deterministic snapshot)            │
│  • Enforce RBAC based on role                               │
└─────────────────────────────────────────────────────────────┘
```

---

## One-Line Summary

| Component | Role |
|-----------|------|
| **Tools** | Simulate HPC APIs — read env data, enforce permissions |
| **Adapters** | Connect to agent backends — drive the task loop, use tools when the agent requests them |
