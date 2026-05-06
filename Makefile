# AOBench Makefile
# Requires: uv (https://github.com/astral-sh/uv)

.DEFAULT_GOAL := help
PYTHON        := uv run python
PYTEST        := uv run pytest
RUFF          := uv run ruff
MYPY          := uv run mypy
AOBENCH       := uv run aobench

# ── Overridable defaults ───────────────────────────────────────────────────────

TASK              ?= JOB_USR_001
ENV               ?= env_01
ADAPTER           ?= direct_qa
MODEL             ?= gpt-4o
N                 ?= 5
MCP_SERVER        ?= stdio:python mcp_server.py
CLEAR_OUTPUT      ?= clear_report.json
ROBUSTNESS_JSON   ?=
LEADERBOARD_RESULTS ?= data/runs
TOOL_DOCS_ROLE    ?=
PILOT_SCORES      ?=

RUN_A ?= $(shell ls -td data/runs/run_* 2>/dev/null | sed -n '2p')
RUN_B ?= $(shell ls -td data/runs/run_* 2>/dev/null | head -1)

RUBRIC_ANNOTATIONS     ?= data/rubric_validation/annotations.csv
RUBRIC_DIM_ANNOTATIONS ?= data/rubric_validation/dim_annotations.csv
RUBRIC_SAMPLE          ?= rv_job_015,rv_job_007,rv_job_001,rv_energy_012,rv_energy_006,rv_energy_001,rv_rbac_011,rv_rbac_005,rv_rbac_001,rv_job_016
RUBRIC_JUDGE_MODEL     ?= gemini-2.5-flash
RUBRIC_RUNS            ?= 8
RUBRIC_PRIMARY_JUDGE   ?= gemini-2.5-flash
RUBRIC_SECONDARY_JUDGE ?= gpt-4.1

PAPER_TABLE1_OUTPUT  ?= -
PAPER_TABLE4_OUTPUT  ?= -
VALIDITY_GATE_OUTPUT ?= data/reports/validity_gates.json

LANGFUSE_DIR := docker/langfuse

##@ Setup

.PHONY: install
install:  ## Create .venv and install all dependencies (including dev + optional extras)
	uv sync --all-extras

.PHONY: install-core
install-core:  ## Install core dependencies only (no dev/openai/anthropic)
	uv sync

##@ Quality

.PHONY: lint
lint:  ## Check code style with ruff
	$(RUFF) check src/ tests/

.PHONY: format
format:  ## Auto-format code with ruff
	$(RUFF) format src/ tests/

.PHONY: typecheck
typecheck:  ## Run mypy type checker
	$(MYPY) src/aobench/

.PHONY: check
check: lint typecheck test  ## Run lint + typecheck + tests (full CI suite)

.PHONY: test
test:  ## Run all tests
	$(PYTEST) tests/

.PHONY: test-unit
test-unit:  ## Run unit tests only
	$(PYTEST) tests/unit/

.PHONY: test-integration
test-integration:  ## Run integration tests only
	$(PYTEST) tests/integration/

.PHONY: test-cov
test-cov:  ## Run tests with HTML + terminal coverage report
	$(PYTEST) tests/ --cov=aobench --cov-report=term-missing --cov-report=html

##@ Observability

.PHONY: stack-up
stack-up: langfuse-setup  ## Start the full AOBench stack (Langfuse + leaderboard API)
	docker compose up -d --build

.PHONY: stack-down
stack-down:  ## Stop the full stack (keeps volumes)
	docker compose down

.PHONY: stack-logs
stack-logs:  ## Stream logs from the full stack
	docker compose logs -f

.PHONY: langfuse-setup
langfuse-setup:  ## Write Langfuse keys to .env if not already set (idempotent)
	@[ -f .env ] || cp .env.example .env
	@grep -q '^LANGFUSE_PUBLIC_KEY=' .env 2>/dev/null || { \
	  printf '\n# Langfuse — auto-provisioned by make langfuse-setup\n' >> .env; \
	  printf 'LANGFUSE_PUBLIC_KEY=pk-lf-aobench-local-dev-pub01\n' >> .env; \
	  printf 'LANGFUSE_SECRET_KEY=sk-lf-aobench-local-dev-sec01\n' >> .env; \
	  printf 'LANGFUSE_BASE_URL=http://localhost:3000\n' >> .env; \
	  echo "  → Langfuse keys written to .env"; \
	}

.PHONY: langfuse-up
langfuse-up: langfuse-setup  ## Start Langfuse only  →  http://localhost:3000
	docker compose -f $(LANGFUSE_DIR)/compose.yml up -d
	@echo "Langfuse starting — UI will be ready at http://localhost:3000"
	@echo "  admin login: admin@aobench.local / aobench-admin"

.PHONY: langfuse-down
langfuse-down:  ## Stop Langfuse (data volume preserved)
	docker compose -f $(LANGFUSE_DIR)/compose.yml down

.PHONY: langfuse-logs
langfuse-logs:  ## Stream Langfuse container logs
	docker compose -f $(LANGFUSE_DIR)/compose.yml logs -f

.PHONY: langfuse-reset
langfuse-reset:  ## Stop Langfuse and DELETE all data (volume removed)
	docker compose -f $(LANGFUSE_DIR)/compose.yml down -v

##@ Benchmark — Running

.PHONY: validate
validate:  ## Validate all benchmark data (tasks + environments)
	$(AOBENCH) validate benchmark

.PHONY: run-alpha0
run-alpha0:  ## Run Alpha-0 slice: JOB_USR_001 + env_01 + direct_qa
	$(AOBENCH) run task --task JOB_USR_001 --env env_01 --adapter direct_qa

.PHONY: run
run:  ## Run one task  (TASK=, ENV=, ADAPTER= overridable)
	$(AOBENCH) run task --task $(TASK) --env $(ENV) --adapter $(ADAPTER)

.PHONY: run-openai
run-openai:  ## Run one task with OpenAI adapter  (TASK=, ENV=, MODEL= overridable)
	$(AOBENCH) run task --task $(TASK) --env $(ENV) --adapter openai:$(MODEL)

.PHONY: run-anthropic
run-anthropic:  ## Run one task with Anthropic adapter  (TASK=, ENV=, MODEL= overridable)
	$(AOBENCH) run task --task $(TASK) --env $(ENV) --adapter anthropic:$(MODEL)

.PHONY: run-mcp
run-mcp:  ## Run one task via an MCP server  (TASK=, ENV=, MCP_SERVER= overridable)
	$(AOBENCH) run task --task $(TASK) --env $(ENV) --adapter "mcp:$(MCP_SERVER)"

.PHONY: run-langfuse
run-langfuse:  ## Run one task and export traces + scores to Langfuse  (TASK=, ENV=, ADAPTER= overridable)
	$(AOBENCH) run task --task $(TASK) --env $(ENV) --adapter $(ADAPTER) --langfuse --no-report

.PHONY: run-all
run-all:  ## Run all benchmark tasks  (ADAPTER= overridable)
	$(AOBENCH) run all --adapter $(ADAPTER)

.PHONY: run-all-openai
run-all-openai:  ## Run all tasks with OpenAI adapter  (MODEL= overridable)
	$(AOBENCH) run all --adapter openai:$(MODEL)

.PHONY: run-all-anthropic
run-all-anthropic:  ## Run all tasks with Anthropic adapter  (MODEL= overridable)
	$(AOBENCH) run all --adapter anthropic:$(MODEL)

.PHONY: run-all-langfuse
run-all-langfuse:  ## Run all tasks and export to Langfuse  (ADAPTER= overridable)
	$(AOBENCH) run all --adapter $(ADAPTER) --langfuse

.PHONY: tunnel-mc
tunnel-mc:  ## Open SSH tunnel to university Ollama server (localhost:11434 → mc:11434)
	python scripts/ollama_tunnel.py

.PHONY: tunnel-mc-check
tunnel-mc-check:  ## Verify SSH tunnel + probe Ollama model list
	python scripts/ollama_tunnel.py --check

##@ Benchmark — Reports & Analysis

.PHONY: report
report:  ## Generate JSON + HTML + slice report for the latest run  (RUN_DIR= overridable)
	$(eval RUN_DIR ?= $(shell ls -td data/runs/run_* 2>/dev/null | head -1))
	$(AOBENCH) report json $(RUN_DIR)
	$(AOBENCH) report html $(RUN_DIR)
	$(AOBENCH) report slices $(RUN_DIR)

.PHONY: compare
compare:  ## Diff two runs  (RUN_A= baseline, RUN_B= comparison — defaults to last two runs)
	$(AOBENCH) compare runs $(RUN_A) $(RUN_B)

.PHONY: robustness
robustness:  ## Run one task N times and report score variance  (TASK=, ENV=, ADAPTER=, N= overridable)
	$(AOBENCH) robustness task --task $(TASK) --env $(ENV) --adapter $(ADAPTER) --n $(N)

.PHONY: robustness-all
robustness-all:  ## Run all tasks N times each and report pass^k  (ADAPTER=, N=, SPLIT= overridable)
	$(AOBENCH) robustness all --adapter $(ADAPTER) --n $(N) $(if $(SPLIT),--split $(SPLIT),)

.PHONY: clear
clear:  ## Compute CLEAR scorecard for a run  (RUN_DIR=, CLEAR_OUTPUT=, ROBUSTNESS_JSON= overridable)
	$(eval RUN_DIR ?= $(shell ls -td data/runs/run_* 2>/dev/null | head -1))
	$(AOBENCH) clear run --run-dir $(RUN_DIR) --output $(CLEAR_OUTPUT) \
		$(if $(ROBUSTNESS_JSON),--robustness-json $(ROBUSTNESS_JSON),)

.PHONY: coverage-matrix
coverage-matrix:  ## Print task coverage matrix (role × category)
	$(PYTHON) scripts/check_coverage.py

.PHONY: scoring-dims
scoring-dims:  ## Show scoring dimensions reference (docs/framework/scoring-dimensions.md)
	@cat docs/framework/scoring-dimensions.md

##@ Benchmark — Validation & Data

.PHONY: validate-snapshots
validate-snapshots:  ## Run F1–F7 fidelity validators on all env_*/ bundles → data/fidelity/
	$(AOBENCH) validate snapshots

.PHONY: validate-bundles
validate-bundles:  ## Validate all snapshot bundles against canonical schemas
	$(PYTHON) -c "from aobench.environment.snapshot_validator import validate_bundle; \
from pathlib import Path; \
errs = {e.name: validate_bundle(e) for e in sorted(Path('benchmark/environments').iterdir()) if e.is_dir()}; \
[print(k, 'OK' if not v else v) for k, v in errs.items()]; \
exit(0 if all(not v for v in errs.values()) else 1)"

.PHONY: validate-hpc-tasks
validate-hpc-tasks:  ## Validate HPC task set v1 (benchmark/tasks/task_set_v1.json)
	$(PYTHON) -c "from aobench.tasks.task_loader import load_hpc_task_set; \
tasks = load_hpc_task_set('benchmark/tasks/task_set_v1.json'); \
print(f'HPC task set v1: {len(tasks)} tasks loaded OK'); \
from collections import Counter; \
[print(f'  {k}: {v}') for k, v in sorted(Counter(t.data_type for t in tasks).items())]"

.PHONY: validate-tasks
validate-tasks:  ## Run T1–T10 task validity checks on the task corpus
	$(PYTHON) -m aobench.cli.validate_tasks --task-file benchmark/tasks/task_set_v1.json

.PHONY: validity-report
validity-report:  ## Run T1–T10 checks and write benchmark/validity_report_v1.json
	$(PYTHON) -m aobench.cli.validate_tasks \
	  --output benchmark/validity_report_v1.json \
	  --format json

.PHONY: lite-select
lite-select:  ## Run 3-stage AOBench-Lite selection → benchmark/tasks/lite_manifest_v1.json
	$(AOBENCH) lite select \
	  --task-dir benchmark/tasks/specs \
	  --output benchmark/tasks/lite_manifest_v1.json

.PHONY: lite-select-with-scores
lite-select-with-scores:  ## Run Lite selection with pilot scores  (PILOT_SCORES= path to JSON required)
	$(AOBENCH) lite select \
	  --task-dir benchmark/tasks/specs \
	  --pilot-scores $(PILOT_SCORES) \
	  --output benchmark/tasks/lite_manifest_v1.json

.PHONY: audit-scorers
audit-scorers:  ## Run O.a–O.c scorer validity audit → benchmark/scorer_audit_v1.json
	$(PYTHON) -m aobench.cli.audit_scorers \
	  --output benchmark/scorer_audit_v1.json \
	  --format json

.PHONY: oracle-check
oracle-check:  ## Check each task's gold answer is derivable from snapshot data
	$(PYTHON) scripts/oracle_check.py

.PHONY: independence-check
independence-check:  ## Detect near-duplicate tasks by cosine similarity of feature vectors
	$(PYTHON) scripts/independence_check.py

.PHONY: generate-tool-docs
generate-tool-docs:  ## Write hpc_tools_guide.md into each environment's docs/ dir
	$(PYTHON) scripts/generate_tool_docs.py

.PHONY: generate-tool-docs-role
generate-tool-docs-role:  ## Write hpc_tools_guide.md for one role  (TOOL_DOCS_ROLE=sysadmin)
	$(PYTHON) scripts/generate_tool_docs.py --role $(TOOL_DOCS_ROLE)

.PHONY: generate-bundles
generate-bundles:  ## Generate canonical snapshot bundles env_06–env_20
	$(PYTHON) scripts/generate_bundles.py

.PHONY: upgrade-rbac-yaml
upgrade-rbac-yaml:  ## Upgrade all rbac_policy.yaml files v1.0 → v1.1
	$(PYTHON) scripts/upgrade_rbac_yaml.py

.PHONY: create-rbac-policy-docs
create-rbac-policy-docs:  ## Create docs/rbac_policy.md in all environment bundles
	$(PYTHON) scripts/create_rbac_policy_docs.py

.PHONY: generate-rbac-docs
generate-rbac-docs:  ## Generate docs/rbac_policy.md for all environment bundles
	$(PYTHON) scripts/generate_rbac_docs.py

.PHONY: create-task-stubs
create-task-stubs:  ## Create minimal stub evidence files for oracle-check failures
	$(PYTHON) scripts/create_task_stubs.py

##@ Pre-flight

.PHONY: preflight
preflight: smoke-keys verify-snapshots  ## Run all pre-flight checks (P1–P10)
	$(AOBENCH) validate benchmark
	$(AOBENCH) validate snapshots
	@test -f data/judge_config.json || (echo "ERROR: data/judge_config.json missing — run: python3 scripts/freeze_judge_config.py" && exit 1)
	@echo "preflight: all checks passed ✓"

.PHONY: smoke-keys
smoke-keys:  ## Verify OpenAI (and optionally Together.ai) API keys are valid
	python3 scripts/smoke_keys.py

.PHONY: verify-snapshots
verify-snapshots:  ## Verify snapshot file hashes match data/snapshots/MANIFEST.json
	python3 scripts/verify_snapshots.py

.PHONY: cost-check
cost-check:  ## Print v0.2 experiment budget spend vs. remaining
	python3 scripts/cost_check.py

##@ Leaderboard

.PHONY: leaderboard
leaderboard:  ## Build leaderboard from benchmark results  (LEADERBOARD_RESULTS= overridable)
	$(AOBENCH) leaderboard build $(LEADERBOARD_RESULTS)

.PHONY: leaderboard-serve
leaderboard-serve:  ## Start the leaderboard HTTP API  (requires fastapi + uvicorn)
	PYTHONPATH=src $(PYTHON) -m uvicorn aobench.leaderboard.api:app --reload

##@ Rubric Validation

.PHONY: rubric-generate-responses
rubric-generate-responses:  ## Generate 50 synthetic validation responses → data/rubric_validation/responses/
	$(PYTHON) scripts/generate_rubric_validation_responses.py

.PHONY: rubric-compute-icc
rubric-compute-icc:  ## Compute ICC(A,1) from annotation CSV  (RUBRIC_ANNOTATIONS= overridable)
	$(PYTHON) scripts/compute_icc.py --annotations $(RUBRIC_ANNOTATIONS)

.PHONY: rubric-compute-krippendorff
rubric-compute-krippendorff:  ## Compute Krippendorff alpha per dimension  (RUBRIC_DIM_ANNOTATIONS= overridable)
	$(PYTHON) scripts/compute_krippendorff.py --annotations $(RUBRIC_DIM_ANNOTATIONS)

.PHONY: rubric-stochastic-stability
rubric-stochastic-stability:  ## Run judge 8× on 10 responses and report stochastic std  (RUBRIC_JUDGE_MODEL=, RUBRIC_SAMPLE= overridable)
	$(PYTHON) scripts/stochastic_stability.py \
		--responses data/rubric_validation/responses/ \
		--sample $(RUBRIC_SAMPLE) \
		--judge-model $(RUBRIC_JUDGE_MODEL) \
		--runs $(RUBRIC_RUNS)

.PHONY: rubric-cross-judge
rubric-cross-judge:  ## Score all 50 responses with two judges and report Kendall τ_b  (RUBRIC_PRIMARY_JUDGE=, RUBRIC_SECONDARY_JUDGE= overridable)
	$(PYTHON) scripts/cross_judge_ranking.py \
		--responses data/rubric_validation/responses/ \
		--primary-judge $(RUBRIC_PRIMARY_JUDGE) \
		--secondary-judge $(RUBRIC_SECONDARY_JUDGE)

.PHONY: rubric-validate-all
rubric-validate-all: rubric-compute-icc rubric-compute-krippendorff rubric-stochastic-stability rubric-cross-judge  ## Run all 4 rubric validation gates (R1–R4)

##@ Paper Artifacts

.PHONY: paper-table1
paper-table1:  ## Generate Table 1 (main results) from v01_dev_* run summaries
	$(PYTHON) scripts/make_paper_table1.py \
	  data/runs/v01_dev_claude_sonnet \
	  data/runs/v01_dev_gpt4o \
	  data/runs/v01_dev_gpt4o_mini \
	  $(if $(filter-out -,$(PAPER_TABLE1_OUTPUT)),--output $(PAPER_TABLE1_OUTPUT),)

.PHONY: paper-table4
paper-table4:  ## Generate Table 4 (pass^k reliability) from data/robustness/v01_*.json
	$(PYTHON) scripts/make_paper_table4.py \
	  $(if $(filter-out -,$(PAPER_TABLE4_OUTPUT)),--output $(PAPER_TABLE4_OUTPUT),)

.PHONY: check-validity-gates
check-validity-gates:  ## Run V1–V6 validity gates and write JSON report  (VALIDITY_GATE_OUTPUT= overridable)
	$(PYTHON) scripts/check_validity_gates.py \
	  data/runs/v01_dev_claude_sonnet \
	  data/runs/v01_dev_gpt4o \
	  data/runs/v01_dev_gpt4o_mini \
	  --rob-dir data/robustness \
	  --output $(VALIDITY_GATE_OUTPUT)

##@ Reproducibility

.PHONY: repro-table-1
repro-table-1:  ## Reproduce Table 1 from locked run artifacts
	PYTHONPATH=src $(PYTHON) -m aobench.reproducibility.targets table-1

.PHONY: repro-table-2
repro-table-2:  ## Reproduce Table 2 from locked run artifacts
	PYTHONPATH=src $(PYTHON) -m aobench.reproducibility.targets table-2

.PHONY: repro-determinism
repro-determinism:  ## Verify deterministic score reproducibility across two independent runs
	PYTHONPATH=src $(PYTHON) -m aobench.reproducibility.targets determinism

.PHONY: fetch-snapshots
fetch-snapshots:  ## Download canonical snapshot bundles from the remote artifact store
	PYTHONPATH=src $(PYTHON) -m aobench.reproducibility.targets fetch-snapshots

.PHONY: repro-docker
repro-docker:  ## Build CLI Docker image and smoke-test the entrypoint
	docker build -t aobench:repro .
	docker run --rm aobench:repro --help

##@ Housekeeping

.PHONY: build
build:  ## Build distributable package (uv build)
	uv build

.PHONY: clean
clean:  ## Remove build artifacts, caches, and coverage reports
	rm -rf dist/ build/ .eggs/ *.egg-info/ src/*.egg-info/
	rm -rf .pytest_cache/ .mypy_cache/ .ruff_cache/
	rm -rf htmlcov/ .coverage
	find src tests scripts -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

.PHONY: clean-runs
clean-runs:  ## Delete all benchmark run artifacts from data/runs/
	rm -rf data/runs/*/
	@echo "Run artifacts cleared."

##@ Help

.PHONY: help
help:  ## Show this help
	@printf '\nAOBench — benchmark runner and evaluation toolkit\n'
	@printf 'Usage: make \033[36m<target>\033[0m  [VAR=value ...]\n'
	@awk 'BEGIN {FS = ":.*##"} \
	  /^##@/ { printf "\n\033[1;33m%s\033[0m\n", substr($$0, 5) } \
	  /^[a-zA-Z0-9_-]+:.*?##/ { printf "  \033[36m%-32s\033[0m %s\n", $$1, $$2 }' \
	  $(MAKEFILE_LIST)
	@printf '\n\033[1mDefaults\033[0m\n'
	@printf '  TASK=%-18s ENV=%-10s ADAPTER=%-14s MODEL=%s\n' \
	  "$(TASK)" "$(ENV)" "$(ADAPTER)" "$(MODEL)"
	@printf '  N=%-21s LEADERBOARD_RESULTS=%s\n\n' "$(N)" "$(LEADERBOARD_RESULTS)"
