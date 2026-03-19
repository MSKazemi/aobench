# ExaBench Backlog

> Generated: 2026-03-19 from 17 extracted resource cards

---

## Core v0.1 Features

_From resources marked 'Adopt directly' or 'must adopt':_

### From clear — Adopt directly

- [ ] **Feature:** Report all five CLEAR dimensions per ExaBench task: cost, latency, efficacy, RBAC compliance rate, pass^k
- [ ] **Feature:** Success-per-dollar leaderboard: normalize task success rate by API cost to surface cost-efficient models
- [ ] **Feature:** Reliability heatmap across tasks and models: show which task categories have highest variance across runs
- [ ] **Task:** Add cost tracking to ExaBench runner: count tokens in/out per task and compute cost using model pricing table
- [ ] **Task:** Add latency tracking: measure wall-clock time from task start to final answer per run
- [ ] **Task:** Define RBAC assurance scoring rubric: binary per query (did the agent respect the role's permission boundary?)

### From cloud-opsbench — Adapt conceptually

- [ ] **Feature:** HPC environment snapshot schema: environment_snapshot.json (job queue, node topology), telemetry_snapshot.parquet (HPC monitoring metrics), scheduler_state.json (SLURM), rbac_profile.yaml (role permissions)
- [ ] **Feature:** Snapshot replay system: load identical HPC state for every benchmark run to guarantee reproducibility across models
- [ ] **Feature:** Role-differentiated snapshot views: same underlying state presented with different tool access and information visibility per user role
- [ ] **Task:** Define ExaBench snapshot schema covering all HPC state dimensions (jobs, nodes, energy, incidents, policy docs)
- [ ] **Task:** Build snapshot loader that initializes the HPC mock environment from a JSON/parquet snapshot bundle
- [ ] **Task:** Create a set of 20+ canonical HPC snapshots representing common operational scenarios (job failure, energy anomaly, node degradation, policy violation)

### From dacomp — Adopt directly

- [ ] **Feature:** Hybrid ExaBench scorer: deterministic path for numeric/exact tool tasks (correct node count, correct energy value), rubric path for explanations and recommendations
- [ ] **Feature:** LLM-judge rubric for HPC diagnostic explanations: evaluate whether the agent's diagnosis is technically correct, role-appropriate, and actionable
- [ ] **Feature:** Evolving HPC scenario: mid-task state changes (new job submitted, node fails) to test agent adaptability
- [ ] **Task:** Implement ExaBench scorer with two paths: deterministic (exact match / range check) and rubric (LLM judge with structured scoring criteria)
- [ ] **Task:** Define rubric templates for common HPC explanation types: job failure diagnosis, energy anomaly explanation, RBAC-aware response
- [ ] **Task:** Build rubric validation set: human-annotated reference answers with scoring rationale for calibration

### From llm-agents-workflow-provenance — Adapt conceptually

- [ ] **Feature:** HPC observability task category in ExaBench: OLAP-style queries over HPC monitoring, SLURM accounting, and facility energy data
- [ ] **Feature:** Role-differentiated query evaluation: same provenance query answered with different detail levels and scope per user role
- [ ] **Feature:** Adaptive routing baseline: show that no single model dominates across all ExaBench HPC task categories
- [ ] **Task:** Create ExaBench HPC observability task set: 30+ OLAP-style questions over synthetic HPC monitoring/SLURM/facility energy snapshots
- [ ] **Task:** Implement schema-driven RAG tool for ExaBench agents: structured query interface over HPC data files
- [ ] **Task:** Build LLM-as-judge scorer for HPC observability answers with role-aware rubric

### From tau-bench — Adopt directly

- [ ] **Feature:** Implement pass^k scoring across k=8 runs for every ExaBench task, reporting per-task reliability distributions
- [ ] **Feature:** Role-aware policy compliance scoring: evaluate whether agents respect RBAC boundaries per user role
- [ ] **Feature:** Multi-turn HPC episode structure: agent interacts with simulated HPC user to diagnose job failures or energy anomalies
- [ ] **Task:** Port pass^k metric computation into ExaBench scorer module (statistics over k independent runs per task)
- [ ] **Task:** Define ExaBench policy document format analogous to tau-bench's retail/airline policy files, covering SLURM policies, partition rules, and RBAC constraints
- [ ] **Task:** Implement LLM-simulated HPC user that asks questions appropriate to each role persona

### From trail — Adapt conceptually

- [ ] **Feature:** HPC error taxonomy as a first-class ExaBench scoring dimension, with 15+ HPC-specific error categories
- [ ] **Feature:** Trace-based failure labeling: annotate each ExaBench run trace with error type and step, enabling post-hoc analysis
- [ ] **Feature:** Error distribution reporting per model per task category (job ops, telemetry, energy, RBAC)
- [ ] **Task:** Define ExaBench HPC error taxonomy YAML with categories, subcategories, and detection heuristics
- [ ] **Task:** Build trace annotation schema that captures tool calls, reasoning steps, and error labels in structured JSON
- [ ] **Task:** Implement automatic error classifier that checks traces against known HPC error patterns (wrong partition, bad time range, unit mismatch)

### From agentarch — Use only for comparison in paper

- [ ] **Feature:** Architecture comparison table in ExaBench paper: ReAct vs. function-calling vs. CodeAct on HPC task categories
- [ ] **Feature:** Multi-agent configuration testing: single HPC agent vs. orchestrator + specialist agents (scheduler agent, telemetry agent, RBAC agent)
- [ ] **Feature:** Task-architecture affinity analysis: show which HPC task types favor which architectures
- [ ] **Task:** Implement at least 3 agent architecture adapters in ExaBench: ReAct, function-calling, plan-then-act
- [ ] **Task:** Run ExaBench Tier 1 tasks across all 3 architectures and report per-category results
- [ ] **Task:** Add architecture field to ExaBench result schema for architecture-controlled comparison

### From agentbench — Use only for comparison in paper

- [ ] **Feature:** Adopt AgentBench's episode harness interface as ExaBench's base runner architecture
- [ ] **Feature:** Use AgentBench as baseline comparison in paper: ExaBench agents evaluated on AgentBench OS/DB environments for cross-benchmark context
- [ ] **Feature:** Multi-environment result aggregation pattern for ExaBench's task category reporting
- [ ] **Task:** Map ExaBench's task categories (job ops, telemetry, energy, RBAC) to an AgentBench-compatible episode interface
- [ ] **Task:** Implement AgentBench-style success rate reporting per task category
- [ ] **Task:** Add AgentBench OS environment results as a comparison baseline in the paper

### From bfcl — Adapt conceptually

- [ ] **Feature:** HPC function-calling scorer: decomposed evaluation of tool selection, argument correctness, and sequence validity for SLURM/HPC monitoring/RBAC tools
- [ ] **Feature:** Parallel tool call evaluation: some HPC tasks require simultaneous tool calls (query telemetry + check RBAC at the same time)
- [ ] **Feature:** Forbidden call detection: score agents for not calling tools outside their role's permission profile
- [ ] **Task:** Define ExaBench HPC tool signature library: all mock tool function signatures with parameter types and valid value ranges
- [ ] **Task:** Implement decomposed tool call scorer: selection_score, argument_score, sequence_score, forbidden_call_penalty
- [ ] **Task:** Create BFCL-style evaluation split for ExaBench: easy (single tool, exact args), medium (multi-tool sequence), hard (parallel + role-aware)

### From flowcept — Adopt directly

- [ ] **Feature:** Flowcept-backed trace storage: every ExaBench run produces a structured provenance record queryable via Flowcept's RAG interface
- [ ] **Feature:** Reasoning-to-evidence linkage: store which HPC data artifacts (telemetry snapshots, scheduler logs) the agent accessed and cited in its answer
- [ ] **Feature:** Cross-run provenance comparison: use Flowcept to compare agent behavior across models on the same task
- [ ] **Task:** Integrate Flowcept as optional trace backend in ExaBench runner: pip install flowcept, emit events on tool call and step completion
- [ ] **Task:** Define ExaBench provenance event schema extending Flowcept's base schema with benchmark-specific fields
- [ ] **Task:** Build provenance query examples for common ExaBench audit questions: 'which tasks did model X fail on?', 'what evidence did the agent use for task Y?'

### From infiagent-dabench — Adapt conceptually

- [ ] **Feature:** HPC telemetry analysis tasks: agent must query time-series HPC monitoring snapshots to answer questions like 'which nodes had >90% CPU utilization during job 12345?'
- [ ] **Feature:** Format-prompted HPC answers: structured output format (JSON with numeric answer + unit + confidence) enables deterministic scoring
- [ ] **Feature:** Multi-source analysis tasks: agent must correlate telemetry, scheduler logs, and energy data to diagnose operational issues
- [ ] **Task:** Create HPC telemetry dataset: 20+ HPC monitoring/facility energy snapshot CSV/parquet files representing real operational scenarios
- [ ] **Task:** Define format-prompted answer schema for HPC telemetry questions (numeric, categorical, time-range answers)
- [ ] **Task:** Build code execution sandbox for HPC telemetry queries: expose pandas/polars + HPC-specific query functions

### From langfuse — Adopt directly

- [ ] **Feature:** Langfuse as ExaBench's default trace backend: every run automatically produces a structured Langfuse session with full tool call history
- [ ] **Feature:** ExaBench score attachment: post-evaluation scores (pass/fail, RBAC compliance, error type) attached as Langfuse score objects for visual inspection
- [ ] **Feature:** Cross-model comparison view: use Langfuse's dataset/experiment features to compare multiple models on the same ExaBench task set
- [ ] **Task:** Add optional Langfuse integration to ExaBench runner: LANGFUSE_PUBLIC_KEY + LANGFUSE_SECRET_KEY env vars enable auto-tracing
- [ ] **Task:** Define ExaBench trace metadata schema as Langfuse custom attributes
- [ ] **Task:** Build ExaBench score posting step: after each task evaluation, post structured score object to Langfuse trace

### From tau2-bench — Adapt conceptually

- [ ] **Feature:** Gymnasium-compatible ExaBench environment interface for drop-in compatibility with RL frameworks and standard agent evaluation libraries
- [ ] **Feature:** Dual-role evaluation: simultaneously score the HPC AI agent and the simulated user (did the user provide realistic HPC-context queries?)
- [ ] **Feature:** ExaBench leaderboard tracking pass^k per model across HPC task categories
- [ ] **Task:** Implement ExaBench environment as a Gymnasium Env subclass with step(), reset(), and render() methods
- [ ] **Task:** Define action space as structured HPC tool calls and observation space as HPC state snapshot + conversation history
- [ ] **Task:** Build leaderboard output format: per-model CSV with all CLEAR dimensions and pass^k per task category

### From toolbench — Use only for comparison in paper

- [ ] **Feature:** Adopt win-rate evaluation for ExaBench: compare agent answers to a reference baseline (GPT-4o) across HPC tasks
- [ ] **Feature:** DFSDT-inspired exploration: allow agents to systematically explore HPC tool space during complex multi-step tasks
- [ ] **Feature:** ExaBench HPC API catalog: define ~30 canonical HPC tool signatures as ExaBench's equivalent of ToolBench's API catalog
- [ ] **Task:** Define ExaBench HPC tool catalog YAML: all mock tool signatures, descriptions, parameter schemas, and role-visibility flags
- [ ] **Task:** Implement win-rate evaluation: run both the evaluated model and a reference model on each task; compare outputs via judge
- [ ] **Task:** Build tool coverage metric: track which HPC tools each agent uses and which it never discovers

### From worfbench — Adapt conceptually

- [ ] **Feature:** HPC workflow graph scorer: evaluate multi-step operational tasks (inspect queue → inspect telemetry → inspect logs → cross-check policy → synthesize answer) as graph matching
- [ ] **Feature:** Partial-credit scoring for incomplete but structurally correct HPC workflows using subgraph matching
- [ ] **Feature:** Workflow complexity metric: report graph depth, branching factor, and total nodes per task to characterize difficulty
- [ ] **Task:** Implement WorfEval-style subgraph matching scorer for ExaBench workflow tasks
- [ ] **Task:** Define ExaBench workflow graph schema: nodes are tool calls or reasoning steps, edges are dependencies
- [ ] **Task:** Create 10+ canonical HPC operational workflow graphs as ground truth templates (job failure diagnosis, energy anomaly investigation, RBAC policy check)

---

## Paper-Positioning References

_Resources used only for comparison, not implementation:_

- **agentarch:** AgentArch benchmarks 18 different agent architectural configurations on enterprise tasks, covering single vs. multi-agen...
- **agentbench:** AgentBench is a comprehensive benchmark testing LLM agents across 8 heterogeneous environments: OS (shell), DB (SQL), kn...
- **scienceagentbench:** ScienceAgentBench evaluates LLM agents on data-driven scientific workflow tasks validated by domain experts. Tasks span ...
- **toolbench:** ToolBench/ToolLLM is a large-scale framework for training and evaluating LLMs on real-world API tool use, covering 16,46...
