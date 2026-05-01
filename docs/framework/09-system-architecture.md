# 09 — System Architecture (Current State)

> **Authoritative reference.** This document describes the system as
> implemented. Pages 01–07 describe the same system at higher levels of
> abstraction (principles, design, developer guide, taxonomy, evaluation
> protocol) and are kept in sync with this page.
>
> Last updated: 2026-05-02

---

## 1. Three-Repo Ecosystem

ExaBench is a three-repository system. Each repo has a single responsibility.

```
┌─────────────────────────────────────────────────────────────────────┐
│                         ExaBench Ecosystem                          │
│                                                                     │
│  ┌──────────────────┐   specs /    ┌──────────────────┐            │
│  │  ExaBench-SoA    │  HANDOFF.md  │    ExaBench       │            │
│  │  (Scientific)    │ ──────────►  │  (Engineering)    │            │
│  │                  │             │                    │            │
│  │ • Literature     │             │ • Core app (pip)   │            │
│  │ • Paper draft    │             │ • Tasks + Envs     │            │
│  │ • Feature specs  │             │ • Mock HPC tools   │            │
│  │ • Gap analysis   │             │ • Scorers + CLI     │            │
│  └──────────────────┘             └──────────┬─────────┘            │
│                                              │                      │
│                                   embedded   │                      │
│                                   at bench-  │                      │
│                                   mark/qa/   │                      │
│  ┌──────────────────┐                        │                      │
│  │  ExaBench-QA     │  ◄─────────────────────┘                      │
│  │  (Dataset)       │                                               │
│  │                  │                                               │
│  │ • ~95 HPC queries│                                               │
│  │ • Role variants  │                                               │
│  │ • JSON schema    │                                               │
│  └──────────────────┘                                               │
└─────────────────────────────────────────────────────────────────────┘
```

**Data flows:**
- `ExaBench-SoA → ExaBench`: Implementation specs in `outputs/specs/*.md` are converted to engineering prompts via `HANDOFF.md`. Engineering implements them in `ExaBench/src/`.
- `ExaBench-QA → ExaBench`: Dataset embedded at `ExaBench/benchmark/qa/`. Used by `DirectQAAdapter` as ground truth and to seed task design.
- `ExaBench-SoA` scripts pipeline: `papers/extracted/*.json` → `scripts/build_outputs.py` → `inventory/feature_matrix.csv`, `outputs/{exabench_backlog, benchmark_gap_analysis, architecture_ideas}.md`.

---

## 2. ExaBench App — Component Map

```
src/exabench/
├── cli/               CLI commands (typer app)
│   ├── main.py        Entry point — registers all sub-commands
│   ├── run_cmd.py     exabench run task / run all
│   ├── validate_cmd.py exabench validate benchmark
│   ├── report_cmd.py  exabench report json / html / slices
│   ├── compare_cmd.py exabench compare
│   ├── robustness_cmd.py exabench robustness task / all
│   ├── clear_cmd.py   exabench clear run
│   └── lite_cmd.py    exabench lite select
│
├── schemas/           Pydantic data models (no logic)
│   ├── task.py        TaskSpec, HPCTaskSpec, HPCRoleVariant, EvalCriteria, HybridScoringConfig
│   ├── trace.py       Trace, TraceStep, ToolCall, Observation, BenchmarkResult
│   ├── snapshot.py    SlurmState, SlurmJob, SlurmNode, IncidentMetadata, EnvBundle
│   └── trace_annotation.py  ErrorAnnotation, TraceAnnotation, HolisticScores
│
├── loaders/           Data loading (stateless functions)
│   └── task_loader.py Load TaskSpec + HPCTaskSpec from JSON; RAG context builder
│
├── tasks/             Dataset management
│   ├── task_loader.py Load task by ID from benchmark/tasks/specs/
│   ├── context_builder.py Build RAG context string for HPC task set v1
│   └── dataset_splits.py  FROZEN split manifest (21 dev / 9 test tasks)
│
├── environment/       Environment snapshot system
│   ├── snapshot_loader.py   Build ToolRegistry from EnvBundle
│   └── snapshot_validator.py  validate_bundle() — JSON schema checks
│
├── tools/             Mock HPC tool implementations
│   ├── slurm_tool.py       MockSlurmTool (query_jobs, job_details, cancel_job, etc.)
│   ├── docs_tool.py        MockDocsTool (retrieve)
│   ├── rbac_tool.py        MockRBACTool (get_allowed_tools, check_permission)
│   ├── telemetry_tool.py   MockTelemetryTool (query_timeseries, query_node_metrics)
│   ├── facility_tool.py    MockFacilityTool (get_power_usage, set_power_cap)
│   ├── registry.py         ToolRegistry — role-filtered tool dispatch
│   └── catalog_loader.py   Load hpc_tool_catalog.yaml → tool schema dict
│
├── adapters/          Agent backend adapters
│   ├── base.py             BaseAdapter interface (run(task, context) → Trace)
│   ├── direct_qa_adapter.py DirectQA — zero-tool baseline
│   ├── openai_adapter.py   OpenAIAdapter — GPT-4o, GPT-4o-mini, o1 (plain + Azure)
│   ├── anthropic_adapter.py AnthropicAdapter — Claude (native tool_use blocks)
│   └── mcp_adapter.py      MCPClientAdapter — stdio + SSE transports
│
├── runners/           Execution orchestration
│   ├── runner.py      BenchmarkRunner.run_task() — full pipeline per task
│   ├── trace_writer.py TraceWriter — append steps, tool calls to Trace
│   └── context.py     ExecutionContext dataclass
│
├── scorers/           Scoring engine (12 scorers)
│   ├── aggregate.py   AggregateScorer — orchestrates all dimensions
│   ├── outcome_scorer.py    OutcomeScorer
│   ├── tool_use_scorer.py   ToolUseScorer (BFCL-decomposed)
│   ├── grounding_scorer.py  GroundingScorer
│   ├── governance_scorer.py GovernanceScorer (RBAC hard-fail)
│   ├── efficiency_scorer.py EfficiencyScorer
│   ├── robustness_scorer.py compute_pass_k, compute_robustness_suite
│   ├── hybrid_scorer.py     HybridScorer (routes deterministic vs rubric)
│   ├── deterministic.py     DAComp three-tier (CS / CFS / SR)
│   ├── rubric_scorer.py     LLM-judge rubric scoring
│   ├── gsb_scorer.py        Good-Same-Bad comparative scoring
│   ├── checkpoint_scorer.py Checkpoint partial-credit scoring
│   ├── workflow_scorer.py   WorfEvalScorer — workflow DAG matching
│   └── error_annotator.py   TRAIL-adapted HPC error taxonomy (14 categories)
│
├── reports/           Output generation
│   ├── clear_report.py      CLEAR five-dimension scorecard (E/A/R/C/L)
│   ├── json_report.py       Full JSON result dump
│   ├── html_report.py       Self-contained HTML report
│   └── slice_report.py      Role × QCAT stratification slices
│
├── exporters/
│   └── langfuse_exporter.py Optional Langfuse observability export
│
├── taxonomy/
│   └── hpc_error_taxonomy.yaml  24-leaf TRAIL-adapted error taxonomy
│
└── utils/
    ├── logging.py     get_logger(), configure_logging()
    ├── cost.py        estimate_cost(model, prompt_tokens, completion_tokens)
    └── ids.py         make_trace_id(), make_run_id()
```

---

## 3. Dataset & Benchmark Data

```
benchmark/
├── tasks/
│   ├── specs/          30 original task JSON files (JOB_*.json, MON_*.json, ENERGY_*.json)
│   ├── task_set_v1.json  36 HPC task set v1 tasks (HPCTaskSpec format)
│   ├── dataset_splits.py FROZEN — 21 dev / 9 test split (never modify)
│   ├── guidelines/     6 domain guideline files for task set v1
│   └── lite_manifest_v1.json  ExaBench-Lite task subset
│
├── environments/
│   └── env_01/ … env_20/   20 snapshot bundles, each with:
│       ├── slurm_state.json     SLURM jobs, nodes, partitions
│       ├── incident_metadata.json  Active incidents
│       ├── rbac_policy.yaml     Role permissions (v1.1, 5 roles)
│       └── telemetry/           Parquet files for timeseries/node metrics
│
├── configs/
│   ├── hpc_tool_catalog.yaml    16 tool methods, role visibility, dangerous_args
│   ├── scoring_profiles.yaml    Named weight profiles
│   └── error_taxonomy.yaml      Score-based error categories (14)
│
└── qa/                  Embedded ExaBench-QA dataset (~95 queries)
```

**Actual scope (v0.1):**

| Item | Original plan | Actual |
|------|--------------|--------|
| Tasks | ~30 | 30 original + 36 HPC v1 = 66 total |
| Environments | ~5 | 20 snapshot bundles |
| Roles | 3 | 3 scored (sci_user, sysadmin, fac_admin) + 2 schema-only |
| QCATs | 3 | 3 scored (JOB, MON, ENERGY) + 7 schema-only |
| Adapters | 3 baseline names | 4 implemented (direct_qa, openai, anthropic, mcp) |
| Scorers | outcome only | 12 scorers across 6 dimensions |
| CLI commands | 3 | 9+ commands |

---

## 4. End-to-End Execution Flow

`exabench run task --task JOB_USR_001 --env env_01 --adapter openai:gpt-4o`

```
CLI (run_cmd.py)
│
├─ 1. Load TaskSpec from benchmark/tasks/specs/JOB_USR_001.json
│      task_loader.load_task(task_id) → TaskSpec
│
├─ 2. Load EnvBundle from benchmark/environments/env_01/
│      snapshot_loader.load_environment(env_id) → EnvBundle
│      snapshot_validator.validate_bundle(bundle) → raises on schema error
│
├─ 3. Build ToolRegistry (role-filtered)
│      snapshot_loader.build_tool_registry(bundle, role=task.role)
│      → ToolRegistry with allowed methods per role
│
├─ 4. Select Adapter
│      _build_adapter("openai:gpt-4o") → OpenAIAdapter(model="gpt-4o")
│
├─ 5. BenchmarkRunner.run_task(task, env_bundle, adapter)
│   │
│   ├─ 5a. Build prompt: task.query_text + role + tool schemas
│   │
│   ├─ 5b. adapter.run(task, tool_registry, execution_context) [loop ≤10 rounds]
│   │        For each LLM response:
│   │        ├─ If tool_call → ToolRegistry.dispatch(tool_name, args)
│   │        │   ├─ RBAC check → permission_denied if not allowed
│   │        │   └─ Tool method returns observation (JSON)
│   │        ├─ TraceWriter.append_step(step)
│   │        └─ If stop_reason=stop → exit loop
│   │
│   ├─ 5c. TraceWriter.finalize() → Trace
│   │        Contains: steps[], final_answer, hard_fail,
│   │                  model_name, prompt_tokens, completion_tokens
│   │
│   └─ 5d. AggregateScorer.score(task, trace) → BenchmarkResult
│             [see Section 5: Scoring Pipeline]
│
├─ 6. Persist results
│      data/runs/<run_id>/
│      ├── <task_id>_result.json     BenchmarkResult
│      ├── <task_id>_trace.json      Full Trace
│      └── manifest.json             Model, date, split, commit hash
│
└─ 7. Optional: Langfuse export (--langfuse flag)
       langfuse_exporter.export(trace, result) → post to Langfuse server
```

---

## 5. Scoring Pipeline

```
Trace + TaskSpec
│
├─ OutcomeScorer          → score ∈ [0,1]
│  Mode routing:
│  • exact_match: case-insensitive string equality
│  • numeric: ±5% relative tolerance
│  • semantic_match: 60% rapidfuzz + 40% numeric blend
│  NOTE: If task.hybrid_scoring is set, HybridScorer replaces this.
│
├─ HybridScorer (optional, replaces OutcomeScorer)
│  ├─ deterministic path: DAComp CS/CFS/SR
│  │   CS = weighted component partial credit
│  │   CFS = cascading failure (upstream errors nullify downstream)
│  │   SR = strict all-or-nothing (outcome used = SR)
│  └─ rubric path: LLM judge → score_rubric
│      + optional GSB: α·score_rubric + (1−α)·score_gsb
│
├─ ToolUseScorer          → score ∈ [0,1]  +  tool_use_detail
│  Decomposed (BFCL-style) when expected_tool_sequence set:
│  • selection_score = |expected ∩ actual| / |expected|
│  • argument_score = per-arg match (±5% numeric, exact string)
│  • sequence_score = LCS(expected, actual) / |expected|
│  • forbidden_call_penalty = 1.0 − 0.3 × |disallowed calls|
│  With gold_trajectory: upgrades to 0.5×base + 0.3×NED + 0.2×F1
│
├─ GroundingScorer        → score ∈ [0,1]
│  Key token overlap: answer_tokens ∩ observation_tokens / answer_tokens
│  Key tokens: multi-digit numbers, HPC entities (node*, gpu*), status words
│
├─ GovernanceScorer       → score ∈ [0,1]  +  ViolationVector
│  Hard-fail triggers:
│  • trace.hard_fail (permission_denied propagated from tool)
│  • dangerous_args matched against hpc_tool_catalog.yaml conditions
│  Penalties: FORBIDDEN_CALL_PENALTY=0.50, PERMISSION_DENIED=0.25
│  rbac_compliant = True iff score == 1.0
│
├─ EfficiencyScorer       → score ∈ [0,1]
│  Linear: ≤5 steps → 1.0, ≥20 steps → 0.0
│
├─ [Optional] CheckpointScorer  → s_partial, s_full
│  4 evaluator types: tool_call_present, response_contains_gt,
│                     no_forbidden_calls, tool_call_with_metric
│  S_partial = 0.5×(checkpoints_passed/total) + 0.5×S_full
│
└─ AggregateScorer (orchestrator)
   ├─ effective_outcome = s_partial if checkpoints else outcome_score
   ├─ CuP gating: cup_score penalized by ViolationVector
   ├─ Weight profile (from scoring_profiles.yaml):
   │   default_hpc_v01:
   │   outcome=0.30, tool_use=0.20, grounding=0.15,
   │   governance=0.20, robustness=0.10, efficiency=0.05
   ├─ aggregate_score = Σ(weight_i × dim_i)
   └─ IF hard_fail=True → aggregate_score forced to 0.0

Output: BenchmarkResult
├─ dimension_scores: {outcome, tool_use, grounding, governance, efficiency}
├─ aggregate_score (0–1, 0.0 if hard_fail)
├─ hard_fail, hard_fail_reason
├─ rbac_compliant (bool)
├─ cup_score (CuP-gated efficacy)
├─ violation_vector (6 boolean flags)
├─ tool_use_detail (ToolUseResult with sub-scores)
├─ checkpoint_results, s_partial, s_full
└─ cost_estimate_usd, latency_seconds, model_name, token counts
```

---

## 6. CLEAR Scorecard

Computed by `reports/clear_report.py` across all results for a run.

```
Per model, from BenchmarkResult[]:

E  — Efficacy     = mean(outcome or s_partial)                  ∈ [0,1]
A  — Assurance    = fraction(rbac_compliant == True)             ∈ [0,1]
R  — Reliability  = mean(pass^k) across tasks (k=8 default)     ∈ [0,1]
    pass^k = ∏ᵢ (c−i)/(n−i) for i in 0..k−1
    where c = passing runs, n = total runs, pass_threshold=0.7

C  — Cost         = cost_estimate_usd, min-max normalised, inverted
L  — Latency      = latency_seconds, min-max normalised, inverted

CLEAR = 0.2·C_norm + 0.2·L_norm + 0.2·E + 0.2·A + 0.2·R

Additional metrics per model:
CNA = (outcome / cost_usd) × 100    [Cost-Normalised Accuracy]
CPS = total_cost / n_successful      [Cost Per Success]
cup = mean(cup_score)               [CuP-gated efficacy]
cup_gap = completion_rate − cup     [RBAC compliance gap]
risk_ratios = per-violation-flag fractions from violation_vector
```

**v0.1 results (dev split, 21 tasks):**

| Model | E | A | R | CLEAR | Notes |
|-------|---|---|---|-------|-------|
| direct_qa | 0.337 | 1.000 | 0.000 | 0.324 | Zero tool use; A=1.0 trivially |
| GPT-4o | 0.517 | 0.000 | — | — | A=0.000: RBAC failure on all tool episodes |

---

## 7. Scorer Reference Table

| Scorer | File | Dimension | LLM Required | Wired in AggregateScorer |
|--------|------|-----------|-------------|--------------------------|
| OutcomeScorer | outcome_scorer.py | outcome | No | Yes |
| HybridScorer | hybrid_scorer.py | outcome (replaces above) | Optional | Yes (if hybrid_scoring set) |
| → DeterministicScorer | deterministic.py | outcome via Hybrid | No | Via Hybrid |
| → RubricScorer | rubric_scorer.py | outcome via Hybrid | Yes | Via Hybrid |
| → GSBScorer | gsb_scorer.py | outcome via Hybrid | Yes | Via Hybrid |
| ToolUseScorer | tool_use_scorer.py | tool_use | No | Yes |
| GroundingScorer | grounding_scorer.py | grounding | No | Yes |
| GovernanceScorer | governance_scorer.py | governance | No | Yes |
| EfficiencyScorer | efficiency_scorer.py | efficiency | No | Yes |
| CheckpointScorer | checkpoint_scorer.py | outcome (s_partial) | No | Yes (if task.checkpoints) |
| RobustnessScorer | robustness_scorer.py | R in CLEAR | No | Via CLI robustness cmd |
| ErrorAnnotator | error_annotator.py | post-hoc taxonomy | Yes (semantic) | Not wired (standalone) |
| WorfEvalScorer | workflow_scorer.py | workflow DAG | No | Not yet wired |

---

## 8. Role × QCAT × Environment Coverage

**3 scored roles:**

| Role | SLURM access | Telemetry | RBAC | Facility |
|------|-------------|-----------|------|---------|
| scientific_user | Own jobs only | Own node only | Read own | No |
| sysadmin | All jobs + nodes | All nodes | Read + write | Partial |
| facility_admin | All + cluster-wide | All + energy | Full | Full |

**3 scored QCATs:**

| QCAT | Task focus | Tools primarily used |
|------|-----------|---------------------|
| JOB | Job submission, status, failure diagnosis | slurm, docs, rbac |
| MON | Node health, telemetry, incident response | telemetry, slurm, docs |
| ENERGY | Power usage, efficiency, facility controls | telemetry, facility, rbac |

**Dataset split (frozen 2026-03-21):**
- Dev: 21 tasks (70%) — stratified by QCAT × role × difficulty
- Test: 9 tasks (30%) — held-out, run exactly once at end of paper development

---

## 9. Configuration System

**Scoring profiles** (`benchmark/configs/scoring_profiles.yaml`):
- `alpha0_minimal`: outcome only (1.0)
- `alpha1_grounding`: outcome + grounding (0.5/0.5)
- `default_hpc_v01`: full six-dimension weighted profile

**Tool catalog** (`benchmark/configs/hpc_tool_catalog.yaml`):
- 16 tool methods across 5 tool families
- Each method: `description`, `parameters`, `role_visibility` (which roles can call it), `dangerous_args` (conditions that trigger hard-fail)

**RBAC policies** (`benchmark/environments/env_*/rbac_policy.yaml`):
- Per-environment, per-role: `allowed_tools`, `partition_access`, `access_tiers`
- Schema version: v1.1

---

## 10. Document hierarchy

This document is the authoritative current-state reference. The framework
documentation cleanup of 2026-05-02 rewrote pages 01–07 (and
`scoring-dimensions.md`) so they all describe the system as implemented; if
any of those pages diverges from this one in the future, the divergence is
a bug to be fixed in the older page, not in this one.

Six early-version documents were removed in the same cleanup
(`docs-integration-plan.md`, `benchmark-status-and-design.md`,
`chat-outcomes.md`, `architecture-clarification.md`, `docs/langfuse.md`,
`docs/taxonomy/README.md`); their content was either folded into the
authoritative pages or moved to
`.claude/plans/2026-05-02-future-work.md`.

---

## 11. External System Integrations

| System | Integration point | Required? |
|--------|-----------------|-----------|
| OpenAI / Azure OpenAI | openai_adapter.py — reads `OPENAI_API_KEY` / Azure env vars | No (direct_qa works without) |
| Anthropic | anthropic_adapter.py — reads `ANTHROPIC_API_KEY` | No |
| MCP server | mcp_adapter.py — stdio/SSE | No |
| Langfuse | langfuse_exporter.py — reads `LANGFUSE_*` env vars | No (`--langfuse` flag) |
| vLLM / OpenRouter | OpenAIAdapter with `OPENAI_BASE_URL` env var override | No (zero code change) |
| Zenodo | Dataset DOI archival (post-submission) | No |

**To add an open-weight baseline via vLLM or OpenRouter:**
```bash
export OPENAI_BASE_URL=http://localhost:8000/v1  # vLLM
export OPENAI_API_KEY=dummy
make run-all-openai MODEL=meta-llama/Llama-3.1-8B-Instruct
```

---

## 12. CLI Command Reference (Summary)

Full reference: `docs/reference/commands.md`

| Command | Description |
|---------|-------------|
| `exabench validate benchmark` | Validate all task specs and environment bundles |
| `exabench run task TASK_ID` | Run one task with given adapter and environment |
| `exabench run all` | Run all dev-split tasks |
| `exabench report json` | Generate JSON summary report for a run |
| `exabench report html` | Generate self-contained HTML report |
| `exabench report slices` | Role × QCAT stratification report |
| `exabench compare RUN_A RUN_B` | Diff two run directories |
| `exabench robustness task TASK_ID` | Compute pass^k for one task |
| `exabench robustness all` | Compute pass^k across all tasks |
| `exabench clear run RUN_DIR` | Compute CLEAR scorecard for a run |
| `exabench lite select` | Run ExaBench-Lite 3-stage task selection |
