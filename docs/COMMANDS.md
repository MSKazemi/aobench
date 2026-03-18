# ExaBench Command Reference

Reference for all ExaBench CLI commands and Makefile targets.

## Quick Reference

| Command | Description |
|---------|-------------|
| `exabench validate benchmark` | Validate all task specs and environment bundles |
| `exabench run task` | Run a single benchmark task against an environment |
| `exabench run all` | Run all benchmark tasks (one run dir, one trace per task) |
| `exabench report json` | Write a JSON summary of all results in a run directory |
| `exabench report html` | Write a self-contained HTML benchmark report |
| `exabench report slices` | Print a role × category score table for a run |
| `exabench compare runs` | Diff two run directories — show score deltas and regressions |
| `exabench robustness task` | Run a task N times and report score variance (robustness score) |

---

## CLI Commands

### Main

```bash
exabench [OPTIONS] COMMAND [ARGS]...
```

**Options:**

| Option | Description |
|--------|-------------|
| `--install-completion` | Install shell completion (bash, zsh, etc.) |
| `--show-completion` | Show completion script for manual setup |
| `-h`, `--help` | Show help and exit |

---

### validate

Validate benchmark data.

```bash
exabench validate [OPTIONS] COMMAND [ARGS]...
```

#### validate benchmark

Validate all task specs and environment bundles under a benchmark root.

```bash
exabench validate benchmark [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--benchmark` | `benchmark` | Path to benchmark root directory |
| `-h`, `--help` | — | Show help and exit |

**Example:**

```bash
exabench validate benchmark
exabench validate benchmark --benchmark /path/to/my-benchmark
```

---

### run

Run benchmark tasks.

```bash
exabench run [OPTIONS] COMMAND [ARGS]...
```

#### run task

Run a single benchmark task against an environment.

```bash
exabench run task [OPTIONS]
```

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--task` | `-t` | (required) | Task ID, e.g. `JOB_USR_001` |
| `--env` | `-e` | (required) | Environment ID, e.g. `env_01` |
| `--adapter` | `-a` | `direct_qa` | Adapter name |
| `--benchmark` | — | `benchmark` | Path to benchmark root |
| `--output` | `-o` | `data/runs` | Output directory for runs |
| `--report/--no-report` | — | `--report` | Auto-generate JSON + HTML reports after run |
| `-h`, `--help` | — | — | Show help and exit |

**Adapters:**

| Adapter | Description |
|---------|-------------|
| `direct_qa` | Direct question-answering adapter (no LLM) |
| `openai` | OpenAI API (default model: `gpt-4o`) |
| `openai:MODEL` | OpenAI with specific model, e.g. `openai:gpt-4o` |
| `mcp:stdio:COMMAND` | MCP client — launch a local subprocess via stdio transport |
| `mcp:sse:URL` | MCP client — connect to a remote MCP server via HTTP SSE |

**Examples:**

```bash
# Run with direct_qa adapter (default)
exabench run task --task JOB_USR_001 --env env_01

# Run with OpenAI
exabench run task -t JOB_USR_001 -e env_01 -a openai:gpt-4o

# Run via a local MCP server subprocess
exabench run task -t JOB_USR_001 -e env_01 -a "mcp:stdio:python my_agent.py"

# Run via a remote MCP server (SSE)
exabench run task -t JOB_USR_001 -e env_01 -a "mcp:sse:http://localhost:8000/sse"

# Custom benchmark path and output
exabench run task -t JOB_USR_001 -e env_01 -o results/

# Skip report generation
exabench run task -t JOB_USR_001 -e env_01 --no-report
```

#### run all

Run all benchmark tasks. Uses each task's `environment_id` from its spec. Creates one run directory with a trace and result file for every task.

```bash
exabench run all [OPTIONS]
```

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--adapter` | `-a` | `direct_qa` | Adapter name |
| `--benchmark` | — | `benchmark` | Path to benchmark root |
| `--output` | `-o` | `data/runs` | Output directory for runs |
| `--report/--no-report` | — | `--report` | Auto-generate JSON + HTML reports after run |
| `-h`, `--help` | — | — | Show help and exit |

**Output structure:** One run directory (e.g. `data/runs/run_20260318_123456_abc123/`) containing:

- `traces/<task_id>_trace.json` — one trace per task
- `results/<task_id>_result.json` — one result per task

**Examples:**

```bash
exabench run all
exabench run all --adapter openai:gpt-4o
exabench run all -o my_runs/
exabench run all --no-report   # skip report generation
```

---

### report

Generate reports from a completed benchmark run directory.

```bash
exabench report [OPTIONS] COMMAND [ARGS]...
```

#### report json

Write a JSON summary of all results in a run directory.

```bash
exabench report json [OPTIONS] RUN_DIR
```

| Argument / Option | Short | Default | Description |
|-------------------|-------|---------|-------------|
| `RUN_DIR` | | (required) | Path to run directory, e.g. `data/runs/run_…` |
| `--output` | `-o` | `<run_dir>/run_summary.json` | Output file path |
| `-h`, `--help` | | | Show help and exit |

**Output file:** `run_summary.json` with `run_id`, `task_count`, `mean_aggregate_score`, `hard_fail_count`, `error_taxonomy` (category counts), and a per-task score table including `error_category` for each task.

**Example:**

```bash
exabench report json data/runs/run_20260318_135249_14013e8c
exabench report json data/runs/run_20260318_135249_14013e8c -o reports/summary.json
```

#### report slices

Print a role × category score table to stdout.

```bash
exabench report slices [OPTIONS] RUN_DIR
```

| Argument  | Description                                      |
|-----------|--------------------------------------------------|
| `RUN_DIR` | Path to run directory, e.g. `data/runs/run_DATE` |

**Example:**

```bash
exabench report slices data/runs/run_20260318_135249_14013e8c
```

**Output:**

```text
Role × Category scores  (run: run_20260318_135249_14013e8c)

Role                        ENERGY           JOB           MON
--------------------------------------------------------------
facility_admin         0.618 (n=3)             -             -
scientific_user                  -   0.670 (n=3)             -
sysadmin                         -   0.610 (n=1)   0.620 (n=3)
```

#### report html

Write a self-contained HTML report for a run directory.

```bash
exabench report html RUN_DIR
```

**Example:**

```bash
exabench report html data/runs/run_20260318_143040_6a47e0f0
# Output: data/runs/run_20260318_143040_6a47e0f0/report.html
```

---

### compare

Compare two benchmark run directories.

```bash
exabench compare [OPTIONS] COMMAND [ARGS]...
```

#### compare runs

Show score deltas between two runs (run_b minus run_a). Positive delta = improvement.

```bash
exabench compare runs [OPTIONS] RUN_A RUN_B
```

| Argument | Description |
|----------|-------------|
| `RUN_A`  | Baseline run directory |
| `RUN_B`  | Comparison run directory |
| `--output` / `-o` | Optional path to write diff JSON |

**Example:**

```bash
exabench compare runs data/runs/run_20260318_130835_abc data/runs/run_20260318_143040_def
```

**Output:**

```text
Baseline : run_20260318_130835_abc
Compare  : run_20260318_143040_def
Mean score: 0.6119 → 0.6334  (+0.0215)

Task                 Status        Score A  Score B    Delta
------------------------------------------------------------
ENERGY_FAC_001       ▲ improved     0.6119   0.6334  +0.0215
JOB_USR_001          = unchanged    0.7500   0.7500  +0.0000
...
Improved: 1  Regressed: 0  Unchanged: 9
```

---

### robustness

Measure score consistency across repeated runs.

```bash
exabench robustness [OPTIONS] COMMAND [ARGS]...
```

#### robustness task

Run a task N times with the same adapter and report score variance.

```bash
exabench robustness task [OPTIONS]
```

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--task` | `-t` | (required) | Task ID, e.g. `JOB_USR_001` |
| `--env` | `-e` | (required) | Environment ID, e.g. `env_01` |
| `--adapter` | `-a` | `direct_qa` | Adapter name |
| `--n` | | `5` | Number of repeated runs |
| `--output` | `-o` | | Optional path to write robustness JSON |
| `--benchmark-root` | | `benchmark` | Benchmark root directory |
| `--output-root` | | `data/runs` | Run output root directory |

**Output:** `robustness_score = 1.0 − std_dev`. A score of 1.0 means perfectly consistent results. Scores below 1.0 indicate the adapter produces variable answers for identical queries.

**Example:**

```bash
exabench robustness task --task JOB_USR_001 --env env_01 --adapter openai:gpt-4o --n 5
```

**Output:**

```text
Robustness run: JOB_USR_001 @ env_01  adapter=openai:gpt-4o  n=5

  Run 1/5  score=0.8124
  Run 2/5  score=0.7891
  ...

──────────────────────────────────────────────────
Task         : JOB_USR_001
Runs         : 5
Mean score   : 0.7983
Std dev      : 0.0124
Range        : 0.7891 – 0.8124
Robustness   : 0.9876
──────────────────────────────────────────────────
```

---

## Makefile Targets

Convenience targets that wrap CLI commands. Use `make help` to list all.

### Setup

| Target | Description |
|--------|-------------|
| `make install` | Create `.venv` and install all dependencies (including dev + optional extras) |
| `make install-core` | Install core dependencies only (no dev/openai/anthropic) |

### Benchmark

| Target | Description |
|--------|-------------|
| `make validate` | Validate all benchmark data (equivalent to `exabench validate benchmark`) |
| `make run` | Run a single task (overridable: `TASK=`, `ENV=`, `ADAPTER=`) |
| `make run-alpha0` | Run Alpha-0 slice: JOB_USR_001 + env_01 + direct_qa |
| `make run-openai` | Run a task with OpenAI adapter (overridable: `TASK=`, `ENV=`, `MODEL=`) |
| `make run-all` | Run all tasks (one run dir, one trace per task; ADAPTER= overridable) |
| `make run-all-openai` | Run all tasks with OpenAI (MODEL= overridable) |
| `make run-mcp` | Run a task via MCP server (TASK=, ENV=, MCP_SERVER= overridable) |
| `make report` | Generate JSON + HTML report for the latest run (RUN_DIR= overridable) |
| `make compare` | Diff last two runs (RUN_A= baseline, RUN_B= comparison) |
| `make robustness` | Run a task N times and report variance (TASK=, ENV=, ADAPTER=, N= overridable) |
| `make coverage-matrix` | Print task coverage matrix (role × category) |

**Example with overrides:**

```bash
make run TASK=JOB_USR_002 ENV=env_02
make run-openai MODEL=gpt-4o
make run-all
make run-all-openai MODEL=gpt-4o
```

### Quality

| Target | Description |
|--------|-------------|
| `make test` | Run all tests |
| `make test-unit` | Run unit tests only |
| `make test-integration` | Run integration tests only |
| `make test-cov` | Run tests with coverage report |
| `make lint` | Check code style with ruff |
| `make format` | Auto-format code with ruff |
| `make typecheck` | Run mypy type checker |
| `make check` | Run lint + typecheck + tests (full CI check) |

### Housekeeping

| Target | Description |
|--------|-------------|
| `make clean` | Remove build artifacts, caches, and coverage reports |
| `make clean-runs` | Remove all benchmark run artifacts from `data/runs/` |
| `make build` | Build distributable package |
| `make help` | Show all Makefile targets and descriptions |
