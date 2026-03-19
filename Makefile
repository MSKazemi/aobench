# ExaBench Makefile
# Requires: uv (https://github.com/astral-sh/uv)

.DEFAULT_GOAL := help
PYTHON        := uv run python
PYTEST        := uv run pytest
RUFF          := uv run ruff
MYPY          := uv run mypy
EXABENCH      := uv run exabench

# ── Setup ─────────────────────────────────────────────────────────────────────

.PHONY: install
install:  ## Create .venv and install all dependencies (including dev + optional extras)
	uv sync --all-extras

.PHONY: install-core
install-core:  ## Install core dependencies only (no dev/openai/anthropic)
	uv sync

# ── Langfuse (local observability backend) ────────────────────────────────────

LANGFUSE_DIR := docker/langfuse

.PHONY: langfuse-up
langfuse-up:  ## Start Langfuse locally (UI at http://localhost:3000)
	docker compose -f $(LANGFUSE_DIR)/docker-compose.yml up -d
	@echo "Langfuse starting — UI will be ready at http://localhost:3000"

.PHONY: langfuse-down
langfuse-down:  ## Stop Langfuse (keeps data volume)
	docker compose -f $(LANGFUSE_DIR)/docker-compose.yml down

.PHONY: langfuse-logs
langfuse-logs:  ## Stream Langfuse container logs
	docker compose -f $(LANGFUSE_DIR)/docker-compose.yml logs -f

.PHONY: langfuse-reset
langfuse-reset:  ## Stop Langfuse and DELETE all data (volume removed)
	docker compose -f $(LANGFUSE_DIR)/docker-compose.yml down -v

# ── Quality ───────────────────────────────────────────────────────────────────

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
test-cov:  ## Run tests with coverage report
	$(PYTEST) tests/ --cov=exabench --cov-report=term-missing --cov-report=html

.PHONY: lint
lint:  ## Check code style with ruff
	$(RUFF) check src/ tests/

.PHONY: format
format:  ## Auto-format code with ruff
	$(RUFF) format src/ tests/

.PHONY: typecheck
typecheck:  ## Run mypy type checker
	$(MYPY) src/exabench/

.PHONY: check
check: lint typecheck test  ## Run lint + typecheck + tests (full CI check)

# ── Benchmark ─────────────────────────────────────────────────────────────────

.PHONY: validate
validate:  ## Validate all benchmark data (tasks + environments)
	$(EXABENCH) validate benchmark

.PHONY: run-alpha0
run-alpha0:  ## Run Alpha-0 slice: JOB_USR_001 + env_01 + direct_qa adapter
	$(EXABENCH) run task --task JOB_USR_001 --env env_01 --adapter direct_qa

TASK   ?= JOB_USR_001
ENV    ?= env_01
ADAPTER ?= direct_qa
MODEL  ?= gpt-4o

.PHONY: run
run:  ## Run a single task and auto-generate reports (TASK=, ENV=, ADAPTER= overridable)
	$(EXABENCH) run task --task $(TASK) --env $(ENV) --adapter $(ADAPTER)

.PHONY: run-openai
run-openai:  ## Run a task with OpenAI adapter (TASK=, ENV=, MODEL= overridable)
	$(EXABENCH) run task --task $(TASK) --env $(ENV) --adapter openai:$(MODEL)

.PHONY: run-all
run-all:  ## Run all benchmark tasks and auto-generate reports (ADAPTER= overridable)
	$(EXABENCH) run all --adapter $(ADAPTER)

.PHONY: run-all-openai
run-all-openai:  ## Run all tasks with OpenAI adapter (MODEL= overridable)
	$(EXABENCH) run all --adapter openai:$(MODEL)

.PHONY: run-anthropic
run-anthropic:  ## Run a task with Anthropic adapter (TASK=, ENV=, MODEL= overridable)
	$(EXABENCH) run task --task $(TASK) --env $(ENV) --adapter anthropic:$(MODEL)

.PHONY: run-all-anthropic
run-all-anthropic:  ## Run all tasks with Anthropic adapter (MODEL= overridable, default claude-sonnet-4-6)
	$(EXABENCH) run all --adapter anthropic:$(MODEL)

MCP_SERVER ?= stdio:python mcp_server.py

.PHONY: run-mcp
run-mcp:  ## Run a task via an MCP server (TASK=, ENV=, MCP_SERVER= overridable)
	$(EXABENCH) run task --task $(TASK) --env $(ENV) --adapter "mcp:$(MCP_SERVER)"

.PHONY: run-langfuse
run-langfuse:  ## Run a task and export traces + scores to Langfuse (TASK=, ENV=, ADAPTER= overridable)
	$(EXABENCH) run task --task $(TASK) --env $(ENV) --adapter $(ADAPTER) --langfuse --no-report

.PHONY: run-all-langfuse
run-all-langfuse:  ## Run all tasks and export traces + scores to Langfuse (ADAPTER= overridable)
	$(EXABENCH) run all --adapter $(ADAPTER) --langfuse

.PHONY: report
report:  ## Generate JSON + HTML report for the latest run (RUN_DIR= overridable)
	$(eval RUN_DIR ?= $(shell ls -td data/runs/run_* 2>/dev/null | head -1))
	$(EXABENCH) report json $(RUN_DIR)
	$(EXABENCH) report html $(RUN_DIR)
	$(EXABENCH) report slices $(RUN_DIR)

RUN_A ?= $(shell ls -td data/runs/run_* 2>/dev/null | sed -n '2p')
RUN_B ?= $(shell ls -td data/runs/run_* 2>/dev/null | head -1)

.PHONY: compare
compare:  ## Compare last two runs (RUN_A= baseline, RUN_B= comparison)
	$(EXABENCH) compare runs $(RUN_A) $(RUN_B)

N ?= 5

.PHONY: robustness
robustness:  ## Run a single task N times and report score variance (TASK=, ENV=, ADAPTER=, N= overridable)
	$(EXABENCH) robustness task --task $(TASK) --env $(ENV) --adapter $(ADAPTER) --n $(N)

.PHONY: robustness-all
robustness-all:  ## Run ALL tasks N times each and report suite-level pass^k (ADAPTER=, N=, SPLIT= overridable)
	$(EXABENCH) robustness all --adapter $(ADAPTER) --n $(N) $(if $(SPLIT),--split $(SPLIT),)

.PHONY: coverage-matrix
coverage-matrix:  ## Print task coverage matrix (role × category)
	$(PYTHON) scripts/check_coverage.py

.PHONY: scoring-dims
scoring-dims:  ## Show scoring dimensions reference (open docs/framework/scoring-dimensions.md)
	@cat docs/framework/scoring-dimensions.md

# ── Housekeeping ──────────────────────────────────────────────────────────────

.PHONY: clean
clean:  ## Remove build artifacts, caches, and coverage reports
	rm -rf dist/ build/ .eggs/ *.egg-info/ src/*.egg-info/
	rm -rf .pytest_cache/ .mypy_cache/ .ruff_cache/
	rm -rf htmlcov/ .coverage
	find src tests scripts -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

.PHONY: build
build:  ## Build distributable package (uv build)
	uv build

.PHONY: clean-runs
clean-runs:  ## Remove all benchmark run artifacts from data/runs/
	rm -rf data/runs/*/
	@echo "Run artifacts cleared."

.PHONY: help
help:  ## Show this help
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
