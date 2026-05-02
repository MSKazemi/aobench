# Changelog

## v0.3 dataset integrity (2026-05-03)

### Dataset

- 80 task specs across 10 QCATs × 5 roles (up from 71 in MASTER.md snapshot)
- Dataset split frozen at **62 dev / 18 test** (~22% held-out) in `benchmark/tasks/dataset_splits.py`
- Fixed 16 `benchmark_split` mismatches between JSON spec files and `dataset_splits.py`
- Added missing `validation_status` field to 15 AIOPS / PERF / SEC specs (`"not_started"`)

### Environment fidelity

- env_07 and env_12 now pass all F1–F7 fidelity checks (were failing F1/F2/F3 due to
  synthetic slurm data with uniform runtimes and no completed jobs)
- Added historical COMPLETED jobs with realistic lognormal runtime distributions to both envs
- All 23 environment snapshot bundles now pass `exabench validate snapshots` (23/23)

### Validation

- `exabench validate benchmark` → 80/80 tasks, 26/26 environments, passes without `EXABENCH_SKIP_FIDELITY`
- Added three new stub environments (env_24 CUDA/OpenMPI conflict, env_25 privilege escalation, env_26 IB link flapping) with complete bundles

---

## v0.1.0 (2026-05-01)

First public release.

### Dataset

- 30 original HPC operational tasks across a 3×3 role–QCAT grid (JOB × 10, MON × 10, ENERGY × 10)
- 36 HPC task set v1 tasks (job_ops, node_ops, telemetry, energy, dataflow, RBAC)
- 20 deterministic HPC environment snapshot bundles (env_01–env_20) covering 8 scenario types (v0.1 baseline; expanded to env_01–env_26 in v0.3)
- Difficulty tiers: 10 easy / 13 medium / 7 hard across original 30 tasks
- Dataset splits frozen (70% dev, 30% test, stratified by QCAT × role)
- ExaBench-Lite 3-stage selection pipeline (SWE-bench Lite methodology)

### Mock HPC Environment

- 5 tool families: SLURM, docs, RBAC, telemetry, facility
- 16 tool methods catalogued in `benchmark/configs/hpc_tool_catalog.yaml`
- RBAC policy v1.1: 5 roles, forbidden-call hard-fail, per-environment `rbac_policy.yaml`

### Scoring

- 6 evaluation dimensions: Outcome, Tool-Use (BFCL-decomposed), Grounding, Governance, Efficiency, Robustness
- CLEAR five-dimension scorecard (E/A/R/CNA/CPS)
- Completion-under-Policy (CuP) metric for RBAC compliance
- pass^k reliability metric with 5 trials per task
- HPC error taxonomy: 14 categories with auto-detect and LLM-judge annotation
- Hybrid scorer: deterministic (DAComp three-tier) + rubric (LLM-judge) paths
- Scoring profiles: `alpha0_minimal`, `alpha1_grounding`, `default_hpc_v01`

### Adapters

- `direct_qa`: zero-tool baseline
- `openai`: GPT-4o, GPT-4o-mini, o1-mini via OpenAI or Azure OpenAI
- `anthropic`: Claude Sonnet, Claude Opus
- `mcp`: stdio and SSE transports

### CLI

- `exabench validate benchmark` — validate all task and environment data
- `exabench run task / run all` — run evaluations with configurable adapter, split, verbosity
- `exabench report json / html / slices` — generate result reports
- `exabench compare` — diff two run directories
- `exabench robustness task / robustness all` — compute pass^k reliability
- `exabench clear run` — CLEAR scorecard for a run
- `exabench lite select` — ExaBench-Lite subset selection

### Infrastructure

- Langfuse observability integration (`--langfuse` flag)
- GitHub Actions CI: lint + typecheck + tests + benchmark validation on every push
- 534 unit and integration tests
- Apache 2.0 license
