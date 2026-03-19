# ExaBench Roadmap

Single source of truth for project status, next steps, and backlog.

---

## Current State (2026-03-18)

**Alpha-1 complete.** Full pipeline runs end-to-end with 12 tasks, 5 environments, 5 tools, 3 adapters, 5 scorers, structured logging, and a complete CLI.

| Area | Details |
|------|---------|
| Tasks | 12 (JOB×4, MON×4, ENERGY×4) — 12/30 target; all have `scoring_readiness: ready` |
| Environments | 5 (env_01–env_05) |
| Mock tools | `slurm`, `docs`, `rbac`, `telemetry`, `facility` |
| Adapters | `direct_qa`, `openai` (plain + Azure), `mcp` (stdio + SSE transports) |
| Scorers | `outcome` (fuzzy+numeric), `tool_use`, `grounding`, `governance`, `efficiency` |
| Robustness | `compute_robustness(results)` + `exabench robustness task` CLI |
| Reports | JSON summary, HTML report, role×category slices, error taxonomy, compare diff |
| Logging | `utils/logging.py` — `get_logger()` + `configure_logging()`; `--verbose` on run commands |
| CI | `.github/workflows/ci.yml` — lint + typecheck + tests + validate on every push/PR |
| Tests | 81 passing (unit + integration) |
| Scoring profiles | `alpha0_minimal`, `alpha1_grounding`, `default_hpc_v01` |

---

## Immediate Next Steps

Ordered by impact. Work from top to bottom.

### 1. Run baseline comparison

```bash
make run-all-openai MODEL=gpt-4o
make report
make compare RUN_A=data/runs/<direct_qa_run> RUN_B=data/runs/<openai_run>
```

Requires: `OPENAI_API_KEY` or `AZURE_OPENAI_ENDPOINT` + `AZURE_OPENAI_API_KEY` in `.env`.
This produces the first scientifically valid numbers for the benchmark.

### 2. Fix `06-evaluation.md` schema divergence

`docs/framework/06-evaluation.md` §8 (trace) and §9 (result) specify ~16 fields that don't exist in the actual Pydantic models. Rewrite to match `schemas/trace.py` and `schemas/result.py`. Also remove §6 task fields (`success_criteria`, `preferred_tool_sequence`, `policy_sensitivity`, `required_scorers`) that don't exist in `TaskSpec`.

### 3. Expand to 30 tasks

Currently 12/30 (40%). Add 18 more task specs:
- Target: 10×JOB, 10×MON, 10×ENERGY across all roles and difficulty levels
- Each new task needs: gold_answer, gold_evidence_refs, environment link, allowed_tools

---

## Short-term Backlog (next 2–4 weeks)

### Bug fixes

- [x] ~~Fix `slurm_tool.py` `list_nodes` dispatch bug~~ ✓ Fixed
- [x] ~~Fix duplicate help text in `run_cmd.py` error message~~ ✓ Fixed
- [ ] `06-evaluation.md` schema divergence — see Immediate Next Steps §2

### Infrastructure

- [x] ~~GitHub Actions CI~~ ✓ `.github/workflows/ci.yml` (lint + typecheck + tests + validate)
- [x] ~~`CONTRIBUTING.md`~~ ✓ exists
- [x] ~~`utils/logging.py`~~ ✓ implemented; module-level loggers in runner, aggregate scorer, OpenAI adapter; `--verbose/-v` on `run task` and `run all`
- [ ] Dockerfile — reproducible environment for contributors and paper reviewers

### Dataset quality

- [x] ~~Populate `gold_answer` for 10 tasks~~ ✓ all 12 tasks have `scoring_readiness: ready`
- [x] ~~`--verbose` / `--quiet` flags to CLI~~ ✓ `--verbose/-v` implemented on run commands
- [ ] Add token cost estimation — `total_tokens` is captured but no cost is computed or reported

### Refactoring

- [ ] Fix `FacilityTool` and `TelemetryTool` repeated `try: import pandas` in every method — replace with a single class-level `_require_pandas()` guard
- [ ] `_build_adapter()` in `run_cmd.py` is a hand-rolled if/elif factory — replace with a registry dict as adapter count grows

---

## Medium-term Backlog (1–2 months)

### Features

- [ ] **`AnthropicAdapter`** — Claude with native `tool_use` blocks; declared in `pyproject.toml[anthropic]` extra but not implemented
- [x] **`MCPClientAdapter`** ✓ — MCP client; supports stdio and SSE transports; `pip install exabench[mcp]`
- [ ] **Parallel task execution** — `exabench run all` runs tasks serially; add `asyncio` or `concurrent.futures` mode for OpenAI runs (slow with 30+ tasks)
- [ ] **`exabench task create`** — interactive task authoring helper (currently requires manual JSON editing of ~20 fields)
- [ ] **Structured output evaluation mode** — `eval_criteria.evaluation_mode: structured_output` is declared but no scorer handles JSON schema validation
- [ ] **Progress bars** — `exabench run all` with an LLM has no visual progress; add `rich.progress` (already a transitive dependency)
- [ ] **Cross-role evaluation** — run same query under different roles, verify scoped answers; operationalize as a test suite
- [ ] **Adversarial task variants** — `difficulty: adversarial` is in the schema but no adversarial tasks exist; design tasks for jailbreak resistance, misleading evidence, social engineering

### Taxonomy & Query Categories

- [ ] **Improve query categories** — Align project and benchmark with full taxonomy (`docs/taxonomy/02_query_categories.md`): currently 3 QCATs (JOB, MON, ENERGY) used vs 10 defined; extend schema (`QCat` in `schemas/task.py`), task specs, scoring profiles, and reports to support PERF, DATA, SEC, FAC, ARCH, AIOPS, DOCS; add task coverage for new categories and update role×QCAT coverage matrix

### Dataset expansion

- [ ] **Complete role coverage** — taxonomy defines 5 personas (`docs/taxonomy/roles/`); benchmark currently uses 3 (`scientific_user`, `sysadmin`, `facility_admin`). Add `normal_user` and `system_designer` to schema, RBAC, tool registry, and environments; create tasks for both roles per `01_roles_overview.md` and persona docs
- [ ] Expand to 30 task records (currently 12/30 = 40%)
  - Target distribution: 10 × JOB, 10 × MON, 10 × ENERGY (phase 1); expand to PERF, DATA, SEC, FAC, ARCH, AIOPS, DOCS as taxonomy improvement progresses
  - All 5 roles covered once complete: `scientific_user`, `normal_user`, `sysadmin`, `facility_admin`, `system_designer`
  - Mix of easy/medium/hard/adversarial difficulty
- [ ] Freeze dataset splits: `dev` (current 12), `public_test` (new 10), `hidden_test` (new 8)
- [ ] Assign annotation ownership per task

### Refactoring

- [ ] **Generate OpenAI tool schemas from tool classes** — `BaseTool.schema()` method; `OpenAIAdapter` auto-collects schemas instead of maintaining `_TOOL_SCHEMAS` hardcoded list (biggest drift risk)
- [ ] **Unified config loader** — `BenchmarkConfig` that loads `scoring_profiles.yaml`, `tool_registry.yaml`, and any future configs in one place with validation (currently loaded ad-hoc)
- [ ] **Result schema enrichment** — add `model_name`, `benchmark_version`, `cost_estimate` to `BenchmarkResult` for reproducibility; align with `06-evaluation.md` once that doc is updated
- [ ] **HTML template extraction** — `html_report.py` has a 160-line f-string mixing Python and HTML/CSS; extract to `templates/report.html`, use `string.Template` or Jinja2

### Documentation

- [ ] **Complete roles taxonomy** — fix broken links in `docs/taxonomy/01_roles_overview.md` (point to `roles/system_administrators.md`, `roles/facility_admin.md`, etc.); align benchmark schema with taxonomy
- [ ] Update `docs/framework/06-evaluation.md` §8 (trace schema) and §9 (result schema) to match actual Pydantic models — see Immediate Next Steps §2
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
- [ ] MCP compatibility — benchmark agents that expose tools via MCP/FastAPI/HTTP
- [ ] Multi-agent execution mode — benchmark orchestration systems (coordinator + worker agents)
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

### Phase 4 — Environments ✓
- env_01: OOM failure (JOB, scientific_user)
- env_02: Queue congestion (JOB + MON, sysadmin)
- env_03: Thermal and power monitoring (ENERGY, facility_admin)
- env_04: Rack energy comparison (ENERGY, facility_admin)
- env_05: CRAC unit failure / cooling anomaly (ENERGY + MON, facility_admin + sysadmin)

### Phase 5 — Runner, Tools, Adapters ✓
- `MockSlurmTool`, `MockDocsTool`, `MockRBACTool`, `MockTelemetryTool`, `MockFacilityTool`
- `ToolRegistry` with role-based access enforcement and `allowed_tools` filtering
- `BenchmarkRunner` full pipeline (load → build tools → run adapter → score → write)
- `DirectQAAdapter`, `OpenAIAdapter` (plain + Azure, function calling, all 10 tool schemas)
- `MCPClientAdapter` (stdio + SSE transports, OpenAI agentic loop over MCP tools)

### Phase 6 — Scoring Engine ✓
- `OutcomeScorer`: exact match, semantic match (rapidfuzz), numeric tolerance (±5%)
- `ToolUseScorer`: coverage, precision, no-redundancy
- `GroundingScorer`: answer-to-evidence token overlap
- `GovernanceScorer`: permission violation penalty
- `EfficiencyScorer`: token and step count
- `compute_robustness(results)`: score variance across N repeated runs
- `AggregateScorer`: weighted profile composition

### Phase 7 — Reporting, CLI, Infrastructure ✓
- `exabench validate benchmark`
- `exabench run task` / `exabench run all` (with `--verbose/-v` flag)
- `exabench report json` / `exabench report html` / `exabench report slices`
- `exabench compare runs`
- `exabench robustness task`
- JSON report with error taxonomy (`ok`, `ungrounded`, `wrong_answer`, `permission_violation`, etc.)
- HTML report (self-contained, colour-coded)
- Role × category score table
- `utils/logging.py` — `get_logger()` + `configure_logging()`; module-level loggers in runner, scorer, adapters
- GitHub Actions CI (`.github/workflows/ci.yml`) — lint + typecheck + tests + validate
- `CONTRIBUTING.md`
- 81 tests passing (unit + integration)

---

## Coverage Matrix (current)

```
Role / QCAT        JOB    MON    ENERGY    TOTAL
scientific_user      3      0         0        3
sysadmin             1      4         0        5
facility_admin       0      0         4        4
TOTAL                4      4         4       12
```

v0.1 target: 30 tasks — currently 12/30 (40%). Target 5 roles once role coverage complete: `normal_user`, `system_designer` added per taxonomy.
