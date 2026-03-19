# ExaBench Architecture Ideas

> Generated: 2026-03-19 from 17 extracted resource cards

---

## Reuse Directly

**clear:** All five CLEAR dimensions are directly applicable to ExaBench. Reliability (pass^k) and Assurance (RBAC compliance) are especially critical for HPC operational contexts.

**dacomp:** Hybrid dual-scoring methodology: deterministic for closed-form HPC tasks + rubric/LLM-judge for diagnostic reasoning tasks

**flowcept:** Provenance schema design, runtime event capture patterns, structured metadata format for HPC task context. Can be used directly as the trace storage backend for ExaBench runs.

**langfuse:** Langfuse as the local trace collection backend for ExaBench runs. Use its SDK to capture every agent tool call, reasoning step, cost, and latency. Use its dataset management to build annotated evaluation sets.

**tau-bench:** pass^k reliability metric implementation, policy-following evaluation methodology, multi-turn episode structure, pluggable agent interface, LLM-simulated user pattern

---

## Adapt for HPC

**agentops:** Same adaptation as Langfuse: add ExaBench-specific metadata (task_id, role, tier, score) to AgentOps session events. Use AgentOps as optional trace backend.

**bfcl:** Replace generic APIs with HPC-native tool signatures: squeue, sbatch, scancel, prometheus_query, kepler_query, rbac_check, docs_lookup. Evaluate whether agents call the right HPC tool with the right arguments.

**cloud-opsbench:** Replace cloud-native environment (Kubernetes, cloud APIs) with HPC-native state: SLURM job queue snapshot, Prometheus telemetry snapshot, Kepler energy snapshot, RBAC profile, incident context. Extend snapshots to capture multi-role views of the same state.

**infiagent-dabench:** Replace CSV data analysis with HPC telemetry analysis: Prometheus metrics, Kepler energy data, SLURM accounting logs as parquet/CSV files. Agent must query, aggregate, and reason over time-series telemetry to answer operational questions.

**llm-agents-workflow-provenance:** Extend from workflow provenance queries to full HPC operational queries: add SLURM job state queries, Prometheus telemetry queries, energy budget queries, and RBAC-filtered information access. Add role-aware task variants.

**tau2-bench:** Replace retail/airline/telecom with HPC domain. ExaBench could implement the user-agent as an HPC user persona (sysadmin, researcher, etc.) and the service agent as the HPC AI assistant being evaluated.

**trail:** Define an HPC-specific error taxonomy derived from TRAIL's general categories: wrong Slurm command, wrong partition, wrong node filter, wrong time window in telemetry query, incorrect unit conversion, privilege escalation attempt, wrong role-specific explanation, unsupported remediation recommendation

**worfbench:** Apply graph workflow evaluation to HPC operational tasks: a job submission + monitoring + diagnosis + remediation workflow is naturally graph-structured. Score whether the agent's operational plan matches the expected dependency graph.

---

## Implementation Tasks (all resources)

### clear (must adopt)

- [ ] Add cost tracking to ExaBench runner: count tokens in/out per task and compute cost using model pricing table
- [ ] Add latency tracking: measure wall-clock time from task start to final answer per run
- [ ] Define RBAC assurance scoring rubric: binary per query (did the agent respect the role's permission boundary?)

### cloud-opsbench (must adopt)

- [ ] Define ExaBench snapshot schema covering all HPC state dimensions (jobs, nodes, energy, incidents, policy docs)
- [ ] Build snapshot loader that initializes the HPC mock environment from a JSON/parquet snapshot bundle
- [ ] Create a set of 20+ canonical HPC snapshots representing common operational scenarios (job failure, energy anomaly, node degradation, policy violation)

### dacomp (must adopt)

- [ ] Implement ExaBench scorer with two paths: deterministic (exact match / range check) and rubric (LLM judge with structured scoring criteria)
- [ ] Define rubric templates for common HPC explanation types: job failure diagnosis, energy anomaly explanation, RBAC-aware response
- [ ] Build rubric validation set: human-annotated reference answers with scoring rationale for calibration

### llm-agents-workflow-provenance (must adopt)

- [ ] Create ExaBench HPC observability task set: 30+ OLAP-style questions over synthetic Prometheus/SLURM/Kepler snapshots
- [ ] Implement schema-driven RAG tool for ExaBench agents: structured query interface over HPC data files
- [ ] Build LLM-as-judge scorer for HPC observability answers with role-aware rubric

### tau-bench (must adopt)

- [ ] Port pass^k metric computation into ExaBench scorer module (statistics over k independent runs per task)
- [ ] Define ExaBench policy document format analogous to tau-bench's retail/airline policy files, covering SLURM policies, partition rules, and RBAC constraints
- [ ] Implement LLM-simulated HPC user that asks questions appropriate to each role persona

### trail (must adopt)

- [ ] Define ExaBench HPC error taxonomy YAML with categories, subcategories, and detection heuristics
- [ ] Build trace annotation schema that captures tool calls, reasoning steps, and error labels in structured JSON
- [ ] Implement automatic error classifier that checks traces against known HPC error patterns (wrong partition, bad time range, unit mismatch)

### agentarch (should consider)

- [ ] Implement at least 3 agent architecture adapters in ExaBench: ReAct, function-calling, plan-then-act
- [ ] Run ExaBench Tier 1 tasks across all 3 architectures and report per-category results
- [ ] Add architecture field to ExaBench result schema for architecture-controlled comparison

### agentbench (should consider)

- [ ] Map ExaBench's task categories (job ops, telemetry, energy, RBAC) to an AgentBench-compatible episode interface
- [ ] Implement AgentBench-style success rate reporting per task category
- [ ] Add AgentBench OS environment results as a comparison baseline in the paper

### bfcl (should consider)

- [ ] Define ExaBench HPC tool signature library: all mock tool function signatures with parameter types and valid value ranges
- [ ] Implement decomposed tool call scorer: selection_score, argument_score, sequence_score, forbidden_call_penalty
- [ ] Create BFCL-style evaluation split for ExaBench: easy (single tool, exact args), medium (multi-tool sequence), hard (parallel + role-aware)

### flowcept (should consider)

- [ ] Integrate Flowcept as optional trace backend in ExaBench runner: pip install flowcept, emit events on tool call and step completion
- [ ] Define ExaBench provenance event schema extending Flowcept's base schema with benchmark-specific fields
- [ ] Build provenance query examples for common ExaBench audit questions: 'which tasks did model X fail on?', 'what evidence did the agent use for task Y?'

### infiagent-dabench (should consider)

- [ ] Create HPC telemetry dataset: 20+ Prometheus/Kepler snapshot CSV/parquet files representing real operational scenarios
- [ ] Define format-prompted answer schema for HPC telemetry questions (numeric, categorical, time-range answers)
- [ ] Build code execution sandbox for HPC telemetry queries: expose pandas/polars + HPC-specific query functions

### langfuse (should consider)

- [ ] Add optional Langfuse integration to ExaBench runner: LANGFUSE_PUBLIC_KEY + LANGFUSE_SECRET_KEY env vars enable auto-tracing
- [ ] Define ExaBench trace metadata schema as Langfuse custom attributes
- [ ] Build ExaBench score posting step: after each task evaluation, post structured score object to Langfuse trace

### tau2-bench (should consider)

- [ ] Implement ExaBench environment as a Gymnasium Env subclass with step(), reset(), and render() methods
- [ ] Define action space as structured HPC tool calls and observation space as HPC state snapshot + conversation history
- [ ] Build leaderboard output format: per-model CSV with all CLEAR dimensions and pass^k per task category

### toolbench (should consider)

- [ ] Define ExaBench HPC tool catalog YAML: all mock tool signatures, descriptions, parameter schemas, and role-visibility flags
- [ ] Implement win-rate evaluation: run both the evaluated model and a reference model on each task; compare outputs via judge
- [ ] Build tool coverage metric: track which HPC tools each agent uses and which it never discovers

### worfbench (should consider)

- [ ] Implement WorfEval-style subgraph matching scorer for ExaBench workflow tasks
- [ ] Define ExaBench workflow graph schema: nodes are tool calls or reasoning steps, edges are dependencies
- [ ] Create 10+ canonical HPC operational workflow graphs as ground truth templates (job failure diagnosis, energy anomaly investigation, RBAC policy check)

### agentops (optional inspiration)

- [ ] Add AgentOps as optional backend: AGENTOPS_API_KEY env var enables session tracking
- [ ] Emit ExaBench-specific events to AgentOps: task_start, tool_call, scoring_complete, task_end
- [ ] Compare Langfuse vs AgentOps for ExaBench needs and document recommendation in Claude.md

### scienceagentbench (optional inspiration)

- [ ] Define ExaBench task validation checklist based on ScienceAgentBench's expert review process
- [ ] Recruit 2-3 HPC domain experts (sysadmins or facility ops) for task validation
- [ ] Add validation_status field to ExaBench task schema: unvalidated / expert_validated / community_validated
