# Architecture Clarification: ExaBench vs. HPC Agents

**Purpose:** Align documentation with the core vision: ExaBench is a **benchmarking framework** for evaluating *external* HPC agents (e.g., ODA). ExaBench does **not** develop or implement HPC agents.

---

## 1. Your Vision (Correct)


| ExaBench                                | HPC Agents (e.g., ODA)             |
| --------------------------------------- | ---------------------------------- |
| Benchmarking framework                  | Systems being benchmarked          |
| You develop this                        | Others develop these               |
| Connects to agents                      | Expose interfaces (API, MCP, etc.) |
| Sends tasks, receives responses, scores | Execute tasks, return answers      |


---

## 2. The Confusion: "ExaBench Drives the Agent"

The phrase **"ExaBench drives the agent"** refers to the **OpenAIAdapter** and similar in-process adapters. This has led to confusion.

### What it actually means

- **OpenAIAdapter** is not "the agent you're benchmarking."
- It is a **baseline / reference implementation** used to:
  - Develop and test the benchmark pipeline
  - Validate that tasks, environments, tools, and scorers work
  - Provide a runnable example when no external agent is available
- **ODA, ExaSage, or any real HPC agent** would be evaluated via a **connect-to-agent** adapter (e.g., HTTP/FastAPI, MCP), which is the primary use case.

### Recommended framing


| Adapter type                              | Role                                  | When used                                  |
| ----------------------------------------- | ------------------------------------- | ------------------------------------------ |
| **Connect adapters** (HTTP, MCP, A2A)     | Benchmark external agents (ODA, etc.) | Primary: evaluating real HPC agent systems |
| **Baseline adapters** (OpenAI, direct_qa) | Test the benchmark, provide reference | Development, CI, baseline comparisons      |


---

## 2.1 Future: Production Agent Stress Testing

Beyond v0.1, ExaBench will connect to agents **already deployed on HPC clusters** with access to the real cluster. In this mode:

- The agent under test uses its own access to live SLURM, telemetry, docs, etc.
- ExaBench sends benchmark tasks (via HTTP, MCP, or another protocol) and evaluates responses.
- This enables **stress testing production agents** under realistic conditions: latency, throughput, and correctness under load.

This complements the current mock-tool mode (reproducible, offline) with in-situ evaluation of production HPC agents.

---

## 3. Gaps in Current Documentation

### 3.1 Primary vs. secondary adapter roles

**Issue:** Docs treat "OpenAI-based agent" and "ODA/ExaSage style agents" equally in the adapter list. The primary use case (connect to external agents) is not clearly distinguished from baselines.

**Recommendation:** Explicitly state:

- **Primary:** ExaBench connects to deployed HPC agents (ODA and similar) via HTTP, MCP, or other protocols.
- **Secondary:** Baseline adapters (OpenAI, direct_qa) exist to develop and validate the benchmark when no external agent is available.

### 3.2 Who provides the tools?

**Issue:** The architecture says the agent "interacts with" ExaBench's mock tools. For an external agent, this implies one of:

1. **ExaBench exposes tools** (e.g., via MCP) and the agent connects to them
2. **Agent returns a trace** of its own tool use, and ExaBench scores that
3. **Agent uses its own tools** and we only score the final answer (black-box)

The docs do not clearly distinguish these modes or their trade-offs.

**Recommendation:** Add a section describing evaluation modes:

- **Sandboxed:** Agent uses ExaBench's mock tools (reproducible, full trace-based scoring)
- **Trace-reporting:** Agent uses its own tools but returns a trace (partial scoring)
- **Black-box:** Agent returns only the answer (outcome scoring only)

### 3.3 ODA as the target

**Issue:** ODA (Operational Data Analysis agent) is mentioned only in passing. The docs don't position it as the primary evaluation target.

**Recommendation:** Make ODA (and similar HPC agents) the explicit targets. For example: *"ExaBench is designed to evaluate HPC agent systems such as ODA, ExaSage, and similar operational assistants."*

---

## 4. Recommended Documentation Edits

### 4.1 In 07 — Software Architecture

**Current (D. Agent Adapter Layer):**

> You need a standard interface to plug in different agents:
>
> - OpenAI-based agent
> - LangGraph agent
> - local Python agent
> - your future ODA / ExaSage style agents

**Suggested:**

> The adapter layer connects ExaBench to the agent under evaluation. ExaBench does not implement HPC agents; it benchmarks them.
>
> **Primary use case:** Connect to deployed HPC agents (e.g., ODA, ExaSage) via HTTP, MCP, or other protocols. ExaBench sends tasks and receives responses (and optionally traces).
>
> **Baseline adapters:** OpenAIAdapter, direct_qa, and similar adapters are reference implementations for developing and validating the benchmark when no external agent is available. They are not the systems being benchmarked.

### 4.2 In chat-outcomes.md / README

Clarify that:

- ExaBench = benchmarking framework (you build this)
- HPC agents = external systems to evaluate (others build those)
- "Driving" adapters = baselines for pipeline validation
- "Connect" adapters = primary path for evaluating real agents

### 4.3 Add evaluation modes to 08 — Evaluation Protocol

Clarify what can be scored in each mode:

- Sandboxed (agent uses ExaBench tools): full 6-dimension scoring
- Trace-reporting: partial scoring if trace format is compatible
- Black-box: outcome correctness mainly

---

## 5. Summary


| Your idea                           | Doc status                 | Action                                                 |
| ----------------------------------- | -------------------------- | ------------------------------------------------------ |
| ExaBench benchmarks external agents | Partially implied          | Make explicit: ODA, ExaSage as targets                 |
| ExaBench does NOT develop agents    | Unclear                    | State clearly in architecture                          |
| "Connect to agent" is primary       | Buried among adapter types | Elevate as primary use case                            |
| "Drive agent" is confusing          | Not explained              | Reframe as "baseline adapters for pipeline validation" |


