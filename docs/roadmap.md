# ExaBench Roadmap

Single source of truth for project status, next steps, and backlog.

---

## Current State (2026-03-19)

**Alpha-1 complete + HPC task set v1 implemented.** Full pipeline runs end-to-end with 30 tasks, 20 environments, 5 tools, 4 adapters, 5 scorers, structured logging, progress bars, Langfuse tracing, and a complete CLI. Dataset splits frozen; cost + latency tracking in place. HPC snapshot schema (validator, loader factory, parquet telemetry queries) fully implemented. HPC task set v1 (36 role-aware tasks, 6 data types, schema-driven RAG context builder) implemented from Souza et al. 2025.

| Area | Details |
|------|---------|
| Tasks | 30 original (JOB×10, MON×10, ENERGY×10) — all have `scoring_readiness: ready`; + **36 HPC task set v1** (job_ops×8, node_ops×6, telemetry×8, energy×7, dataflow×4, rbac×3) |
| Environments | 20 (env_01–env_20) — full snapshot bundles across all 8 scenario types; all pass `validate_bundle()` |
| Mock tools | `slurm`, `docs`, `rbac`, `telemetry` (+ `query_timeseries`, `query_node_metrics`), `facility` — all 16 methods catalogued in `benchmark/configs/hpc_tool_catalog.yaml` |
| Adapters | `direct_qa`, `openai` (plain + Azure), `anthropic` (Claude), `mcp` (stdio + SSE transports) |
| Scorers | `outcome` (fuzzy+numeric), `tool_use` (decomposed BFCL-style + `tool_discovery_rate`/`method_discovery_rate` coverage metrics), `grounding`, `governance`, `efficiency` |
| Robustness | `compute_robustness` + `compute_robustness_suite`; `exabench robustness task/all` CLI |
| Reports | JSON summary, HTML report, role×category slices, HPC error taxonomy (14 categories), compare diff |
| Tracing | Optional Langfuse backend — `--langfuse` flag on run commands; posts scores as Langfuse score objects |
| Logging | `utils/logging.py` — `get_logger()` + `configure_logging()`; `--verbose` on run commands |
| CI | `.github/workflows/ci.yml` — lint + typecheck + tests + validate on every push/PR |
| Tests | 251 passing (unit + integration) |
| Scoring profiles | `alpha0_minimal`, `alpha1_grounding`, `default_hpc_v01` |
| Dataset splits | 12 dev / 10 public_test / 8 hidden_test — balanced by category and role |
| Difficulty levels | 10 easy / 13 medium / 7 hard across all 30 tasks |

---

## Immediate Next Steps

Ordered by impact. Work from top to bottom.

### 1. Run 3-way baseline comparison

```bash
make run-all-openai MODEL=gpt-4o      # already done — 0.702 mean score
make run-all-anthropic MODEL=claude-sonnet-4-6
make report
make compare RUN_A=data/runs/<openai_run> RUN_B=data/runs/<anthropic_run>
```

Requires: `ANTHROPIC_API_KEY` in `.env`. First 3-way comparison (direct_qa=0.338 vs gpt-4o=0.702 vs Claude=pending).

### 2. ~~Fix `06-evaluation.md` schema divergence~~ ✓

`docs/framework/06-evaluation.md` fully updated: phantom fields removed, hard-fail definition added, HPC error taxonomy table, pass^k formula, trace and result schema tables accurate.

### 3. ~~Expand to 30 tasks~~ ✓

30/30 tasks complete (JOB×10, MON×10, ENERGY×10). All have `scoring_readiness: ready`.

---

## Short-term Backlog (next 2–4 weeks)

### Bug fixes

- [x] ~~Fix `slurm_tool.py` `list_nodes` dispatch bug~~ ✓ Fixed
- [x] ~~Fix duplicate help text in `run_cmd.py` error message~~ ✓ Fixed
- [x] ~~`06-evaluation.md` schema divergence~~ ✓ §3 and §6 rewritten to match actual `TaskSpec` fields

### Infrastructure

- [x] ~~GitHub Actions CI~~ ✓ `.github/workflows/ci.yml` (lint + typecheck + tests + validate)
- [x] ~~`CONTRIBUTING.md`~~ ✓ exists
- [x] ~~`utils/logging.py`~~ ✓ implemented; module-level loggers in runner, aggregate scorer, OpenAI adapter; `--verbose/-v` on `run task` and `run all`
- [ ] **Dockerfile** — reproducible environment for contributors and paper reviewers

### Dataset quality

- [x] ~~Populate `gold_answer` for all tasks~~ ✓ all 30 tasks have `scoring_readiness: ready`
- [x] ~~`--verbose` / `--quiet` flags to CLI~~ ✓ `--verbose/-v` implemented on run commands
- [x] ~~**Token cost estimation**~~ ✓ `prompt_tokens`, `completion_tokens`, `cost_estimate_usd`, `latency_seconds`, `model_name` in `BenchmarkResult` and `Trace`; pricing table in `utils/cost.py`; surfaced in JSON report
- [x] ~~**Freeze dataset splits**~~ ✓ 12 dev / 10 public_test / 8 hidden_test assigned across all 30 tasks

### Refactoring

- [ ] Fix `FacilityTool` and `TelemetryTool` repeated `try: import pandas` in every method — replace with a single class-level `_require_pandas()` guard
- [x] ~~`_build_adapter()` hand-rolled if/elif factory~~ ✓ replaced with registry dict in `run_cmd.py`

---

## Medium-term Backlog (1–2 months)

### Features — Done

- [x] ~~**HPC error taxonomy (score-based)**~~ ✓ 14 HPC-specific categories in `reports/error_taxonomy.py`; definitions in `benchmark/configs/error_taxonomy.yaml`; 17 unit tests
- [x] ~~**TRAIL-adapted HPC trace annotation taxonomy**~~ ✓ 24-leaf TRAIL-adapted taxonomy in `src/exabench/taxonomy/hpc_error_taxonomy.yaml`; `ErrorAnnotation` + `TraceAnnotation` Pydantic schemas in `schemas/trace_annotation.py`; rule-based `auto_detect_errors()` (7 auto-detectable categories) + LLM-judge `annotate_trace()` + TRAIL metrics (`category_f1`, `location_accuracy`, `joint_accuracy`) in `scorers/error_annotator.py`; 23 unit tests in `tests/unit/test_error_annotator.py`
- [x] ~~**pass^k metric**~~ ✓ `compute_pass_k` + `compute_robustness` + `compute_robustness_suite` in `scorers/robustness_scorer.py`; `exabench robustness task` + `exabench robustness all` CLI; `make robustness` + `make robustness-all` Makefile targets
- [x] ~~**Decomposed tool-call scorer**~~ ✓ BFCL-inspired: `selection_score`, `argument_score`, `sequence_score`, `forbidden_call_penalty`; activated when `eval_criteria.expected_tool_sequence` is set; 20 unit tests
- [x] ~~**`AnthropicAdapter`**~~ ✓ `anthropic_adapter.py`; Claude native `tool_use` blocks; token tracking; `make run-anthropic` + `make run-all-anthropic`
- [x] ~~**`MCPClientAdapter`**~~ ✓ stdio + SSE transports; `pip install exabench[mcp]`
- [x] ~~**Progress bars**~~ ✓ `rich.progress` on `exabench run all`: spinner, task ID, %, elapsed time, rolling score/fail status
- [x] ~~**Langfuse integration**~~ ✓ `src/exabench/exporters/langfuse_exporter.py`; optional `--langfuse` flag; posts traces and scores; `LANGFUSE_PUBLIC_KEY` + `LANGFUSE_SECRET_KEY` env vars
- [x] ~~**BFCL-style difficulty splits**~~ ✓ `difficulty: easy/medium/hard` on all 30 tasks (10/13/7 distribution)

### Features — To Do

- [x] ~~**Hybrid scorer (deterministic + rubric)**~~ ✓ `scorers/hybrid_scorer.py` routes on `task.hybrid_scoring.scoring_mode`; deterministic path: CS/CFS/SR (DAComp three-tier); rubric path: LLM-judge with hierarchical YAML rubric + optional GSB comparative scoring; three HPC rubric templates (`hpc_job_failure_diagnosis_v1`, `hpc_energy_anomaly_v1`, `hpc_rbac_response_v1`); `ComponentSpec` + `HybridScoringConfig` embedded in `TaskSpec`; `make_openai_judge` + `make_anthropic_judge` factory helpers
- [ ] **Structured output evaluation mode** — `eval_criteria.evaluation_mode: structured_output` declared in schema but no scorer validates JSON schema; add `jsonschema` validation path to `OutcomeScorer`
- [ ] **Parallel task execution** — `exabench run all` runs tasks serially; add `asyncio` or `concurrent.futures` mode; required before dataset expands beyond 30 tasks
- [ ] **`exabench task create`** — interactive task authoring helper (currently requires manual JSON editing of ~20 fields)
- [x] ~~**RBAC policy spec (τ-bench + CLEAR + BFCL)**~~ ✓ `GovernanceScorer` upgraded: forbidden-call detection (`FORBIDDEN_CALL_PENALTY=0.50`) + severity-tiered penalties; `rbac_compliant: bool` field in `BenchmarkResult`; CLEAR Assurance (A) now uses binary compliance rate via `compute_assurance_rate()`; `MockRBACTool.get_allowed_tools()`; all 20 `rbac_policy.yaml` upgraded to v1.1 (5 roles, `allowed_tools`, `partition_access`, `access_tiers`); `docs/rbac_policy.md` created for all 20 environments
- [ ] **Cross-role evaluation** — run same task under different roles, verify scoped answers differ correctly; CLI command + test suite; validates RBAC as a scoring dimension beyond governance penalty
- [ ] **Adversarial task variants** — `difficulty: adversarial` in schema but no adversarial tasks; design for jailbreak resistance, misleading evidence, social engineering; most scientifically differentiating feature vs generic QA benchmarks
- [ ] **Success-per-dollar leaderboard** — cost data exists in reports; add ranking by `success_rate / cost_per_task` across models in `exabench report json`
- [ ] **Win-rate evaluation** — run both evaluated model and reference model (GPT-4o) on each task; compare outputs via judge; extend `compare_cmd.py`

### SoA Backlog — Not Planned Yet (post-paper)

- [x] ~~**HPC snapshot schema + replay** *(cloud-opsbench)*~~ ✓ `schemas/snapshot.py` (SlurmState, SlurmJob, SlurmNode, IncidentMetadata Pydantic models); `environment/snapshot_validator.py` (`validate_bundle()`); `environment/snapshot_loader.py` (`build_tool_registry()`); `MockTelemetryTool.query_timeseries()` + `query_node_metrics()` backed by parquet; `load_environment()` now calls `validate_bundle()` and raises on schema errors; 20 canonical bundles covering all 8 scenario types; `scripts/generate_bundles.py`
- [ ] **Multi-turn HPC episode + simulated user** *(τ-bench)* — all adapters are single-turn; add episode runner where LLM-simulated HPC user asks follow-ups; directly tests agent conversational reasoning
- [x] ~~**HPC task set v1 (Souza 2025)**~~ ✓ `benchmark/tasks/task_set_v1.json` (36 tasks); `HPCTaskSpec` + `HPCRoleVariant` + `HPCGroundTruth` Pydantic models in `schemas/task.py`; `src/exabench/tasks/task_loader.py` + `context_builder.py`; 6 domain guideline files in `benchmark/tasks/guidelines/`; `make validate-hpc-tasks`
- [ ] **Flowcept provenance backend** *(flowcept)* — optional `pip install exabench[flowcept]`; emit events on tool call and step completion; cross-run provenance comparison
- [ ] **Gymnasium-compatible environment interface** *(τ²-bench)* — `ExaBenchEnv(gym.Env)` with `step()`, `reset()`, `render()`; drop-in compatibility with RL frameworks
- [ ] **HPC workflow graph scorer** *(worfbench)* — evaluate multi-step operational tasks as DAG matching; partial-credit via subgraph matching; workflow complexity metric (depth, branching)
- [ ] **Multi-agent execution mode** — benchmark orchestration systems (coordinator + specialist agents); architecture comparison in paper (ReAct vs function-calling vs plan-then-act)
- [ ] **Evolving HPC scenario** *(dacomp)* — mid-task state changes (new job submitted, node fails) to test agent adaptability
- [ ] **HPC telemetry analysis tasks** *(infiagent-dabench)* — 20+ HPC monitoring/facility energy snapshot CSV/parquet files; format-prompted answer schema (numeric + unit + confidence)

### Taxonomy & Query Categories

- [ ] **Improve query categories** — currently 3 QCATs (JOB, MON, ENERGY) vs 10 defined in `docs/taxonomy/02_query_categories.md`; extend schema, task specs, scoring profiles, and reports to support PERF, DATA, SEC, FAC, ARCH, AIOPS, DOCS

### Dataset expansion

- [ ] **Complete role coverage** — taxonomy defines 5 personas; benchmark uses 3 (`scientific_user`, `sysadmin`, `facility_admin`); add `normal_user` and `system_designer` to schema, RBAC, tool registry, environments, and task specs
- [x] ~~Expand to 30 task records~~ ✓ 30/30 complete (JOB×10, MON×10, ENERGY×10)
  - Next phase: expand to PERF, DATA, SEC, FAC, ARCH, AIOPS, DOCS as taxonomy improvement progresses
  - All 5 roles covered once complete
  - Mix of easy/medium/hard/adversarial difficulty
- [x] ~~Freeze dataset splits~~ ✓ 12 dev / 10 public_test / 8 hidden_test
- [ ] Assign annotation ownership per task

### Refactoring

- [ ] **Generate adapter tool schemas from tool classes** — `BaseTool.schema()` method; `OpenAIAdapter` and `AnthropicAdapter` auto-collect schemas instead of maintaining hardcoded lists (biggest drift risk as tool count grows)
- [ ] **Unified config loader** — `BenchmarkConfig` that loads `scoring_profiles.yaml`, `tool_registry.yaml`, and any future configs in one place with validation (currently loaded ad-hoc)
- [x] ~~**Result schema enrichment**~~ ✓ `model_name`, `cost_estimate_usd`, `latency_seconds`, `prompt_tokens`, `completion_tokens` added to `BenchmarkResult`
- [ ] **HTML template extraction** — `html_report.py` has a 160-line f-string mixing Python and HTML/CSS; extract to `templates/report.html`, use `string.Template` or Jinja2

### Documentation

- [ ] **Complete roles taxonomy** — fix broken links in `docs/taxonomy/01_roles_overview.md`
- [ ] `docs/guides/adding-tasks.md` — how to author a new task spec end-to-end
- [ ] `docs/guides/adding-adapters.md` — how to add a new LLM backend
- [ ] Archive or merge redundant docs: `adapters-and-tools.md`, `architecture-clarification.md` overlap with `docs/framework/`
- [ ] `CHANGELOG.md` — create and maintain going forward

---

## Long-term / Paper Prep (Phase 8+)

- [ ] Baseline comparison analysis — figures and tables for paper (direct_qa vs openai vs anthropic)
- [ ] Reproducibility statement + benchmark README (third-party setup)
- [ ] Define release package structure and PyPI publication (`exabench` on PyPI)
- [ ] Public leaderboard spec — JSON format for result submission
- [ ] Production agent integration — connect to agents with real cluster access; ExaBench never needs direct cluster access
- [ ] Dataset split validation CLI — ensure dev/test splits are disjoint
- [ ] API service — expose benchmark execution over HTTP
- [ ] Documentation site (mkdocs or Sphinx with auto-generated API reference)
- [ ] `SECURITY.md`, `CODE_OF_CONDUCT.md` for community infrastructure

---

## Completed Phases (history)

### Phase 0–1 — Framing, Schema, Specification ✓
- Task, trace, result, environment, scoring schemas frozen (Pydantic v2)
- Roles: `scientific_user`, `sysadmin`, `facility_admin`
- QCATs: `JOB`, `MON`, `ENERGY`
- Environment snapshot format defined

### Phase 2–3 — Evaluation Protocol & Dataset ✓
- Multi-dimensional scoring defined: outcome, tool_use, grounding, governance, efficiency, robustness
- 12 task specs created across all roles and QCATs; all have `scoring_readiness: ready`
- Dataset split strategy defined (dev / public_test / hidden_test)
- Weighted profiles: `alpha0_minimal`, `alpha1_grounding`, `default_hpc_v01`

### Phase 4 — Environments ✓ (expanded to 20)
- env_01: OOM failure (job_failure, scientific_user)
- env_02: Queue congestion (queue_congestion, sysadmin)
- env_03: Thermal and power monitoring (thermal_power, facility_admin)
- env_04: Rack energy comparison (rack_energy, facility_admin)
- env_05: CRAC unit failure (cooling_failure, facility_admin + sysadmin)
- env_06: GPU power spike (energy_anomaly, sysadmin + facility_admin)
- env_07: PUE degradation / cooling issue (energy_anomaly, facility_admin)
- env_08: Thermal throttling on node (node_degradation, sysadmin)
- env_09: Memory ECC errors / flapping node (node_degradation, sysadmin)
- env_10: User submits to restricted partition (policy_violation, scientific_user + sysadmin)
- env_11: Account over allocation limit (policy_violation, sysadmin + facility_admin)
- env_12: Fairshare starvation / priority inversion (queue_congestion, sysadmin)
- env_13: Six-month CPU utilisation trend (capacity_planning, facility_admin + system_designer)
- env_14: GPU demand forecast (capacity_planning, system_designer)
- env_15: Two jobs competing for node memory (multi_job_interference, sysadmin + researcher)
- env_16: Wrong default partition in slurm.conf (scheduler_misconfiguration, sysadmin)
- env_17: MPI communication timeout / network fault (job_failure, sysadmin)
- env_18: Checkpoint file missing / restart fails (job_failure, scientific_user)
- env_19: GPU idle but not released / energy waste (energy_anomaly, facility_admin)
- env_20: I/O contention on shared Lustre (multi_job_interference, sysadmin)

### Phase 5 — Runner, Tools, Adapters ✓
- `MockSlurmTool`, `MockDocsTool`, `MockRBACTool`, `MockTelemetryTool` (`query_timeseries` + `query_node_metrics` + role filtering), `MockFacilityTool`
- `ToolRegistry` with role-based access enforcement and `allowed_tools` filtering
- `benchmark/configs/hpc_tool_catalog.yaml` — canonical BFCL-style catalog: 5 tools, 16 methods, full parameter schemas, role-visibility matrix, difficulty tiers, OpenAI-compatible export
- `src/exabench/tools/catalog_loader.py` — `ToolCatalog` / `load_catalog()` / `generate_docs_page()` — validates catalog YAML, filters by role, exports to OpenAI tool format
- `ToolUseScorer` augmented with `tool_discovery_rate` + `method_discovery_rate` diagnostic metrics in `ScorerOutput.notes`
- `build_tool_registry(bundle, role)` factory in `environment/snapshot_loader.py` — replaces inline tool construction in runner
- `validate_bundle(bundle_root)` in `environment/snapshot_validator.py` — validates slurm_state.json, incident_metadata.json, rbac_policy.yaml, parquet columns
- `schemas/snapshot.py` — `SlurmState`, `SlurmJob`, `SlurmNode`, `SlurmPartition`, `IncidentMetadata` Pydantic models
- `BenchmarkRunner` full pipeline (load → validate → build tools → run adapter → score → write)
- `DirectQAAdapter`, `OpenAIAdapter` (plain + Azure, function calling), `AnthropicAdapter` (Claude native tool_use blocks), `MCPClientAdapter` (stdio + SSE transports)

### Phase 6 — Scoring Engine ✓
- `OutcomeScorer`: exact match, semantic match (rapidfuzz), numeric tolerance (±5%)
- `ToolUseScorer`: decomposed BFCL-style (selection, argument, sequence, forbidden_call_penalty) + legacy heuristic mode
- `GroundingScorer`: answer-to-evidence token overlap
- `GovernanceScorer`: forbidden-call detection (`FORBIDDEN_CALL_PENALTY=0.50`) + permission-denied penalty (`PERMISSION_DENIED_PENALTY=0.25`) + hard-fail; `rbac_compliant` boolean in `BenchmarkResult`
- `EfficiencyScorer`: token and step count
- `compute_robustness(results)` + `compute_robustness_suite()`: pass^k (k=1,2,4,8) + score variance
- `HybridScorer`: routes `"deterministic"` tasks to CS/CFS/SR; routes `"rubric"` tasks to LLM-judge + optional GSB; backward-compatible (falls back to partial credit when `hybrid_scoring` is `None`)
- `AggregateScorer`: weighted profile composition

### Phase 7 — Reporting, CLI, Infrastructure ✓
- `exabench validate benchmark`
- `exabench run task` / `exabench run all` (progress bars, `--verbose/-v`)
- `exabench report json` / `exabench report html` / `exabench report slices`
- `exabench compare runs`
- `exabench robustness task` / `exabench robustness all`
- JSON report with HPC error taxonomy — 14 categories: `ok`, `rbac_hard_fail`, `hard_fail`, `no_tools_used`, `wrong_tool_sequence`, `rbac_violation`, `role_scope_error`, `ungrounded_answer`, `energy_unit_or_value_error`, `job_misdiagnosis`, `telemetry_interpretation_error`, `wrong_answer`, `partial`
- HTML report (self-contained, colour-coded)
- Role × category score table
- Langfuse optional trace backend (`--langfuse` flag, `exporters/langfuse_exporter.py`)
- `utils/logging.py` — `get_logger()` + `configure_logging()`; module-level loggers in runner, scorer, adapters
- `utils/cost.py` — token cost estimation for 10 models; pricing surfaced in JSON report
- GitHub Actions CI (`.github/workflows/ci.yml`) — lint + typecheck + tests + validate
- `CONTRIBUTING.md`
- 118 tests passing (unit + integration)

---

## Coverage Matrix (current)

```
Role / QCAT        JOB    MON    ENERGY    TOTAL
scientific_user      5      2         2        9
sysadmin             3      6         2       11
facility_admin       2      2         6       10
TOTAL               10     10        10       30
```

v0.1 target: 30/30 tasks complete. Dataset splits frozen (12 dev / 10 public_test / 8 hidden_test). Next: add `normal_user` and `system_designer` roles per taxonomy.
