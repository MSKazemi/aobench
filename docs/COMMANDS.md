# ExaBench Command Reference

Reference for all ExaBench CLI commands and Makefile targets.

## Quick Reference

| Command | Description |
|---------|-------------|
| `exabench validate benchmark` | Validate all task specs and environment bundles |
| `exabench run task` | Run a single benchmark task against an environment |

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
| `--help` | Show help and exit |

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
| `--help` | — | Show help and exit |

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
| `--help` | — | — | Show help and exit |

**Adapters:**

| Adapter | Description |
|---------|-------------|
| `direct_qa` | Direct question-answering adapter (no LLM) |
| `openai` | OpenAI API (default model: `gpt-4o-mini`) |
| `openai:MODEL` | OpenAI with specific model, e.g. `openai:gpt-4o` |

**Examples:**

```bash
# Run with direct_qa adapter (default)
exabench run task --task JOB_USR_001 --env env_01

# Run with OpenAI
exabench run task -t JOB_USR_001 -e env_01 -a openai:gpt-4o-mini
# Custom benchmark path and output
exabench run task -t JOB_USR_001 -e env_01 -o results/
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
| `make coverage-matrix` | Print task coverage matrix (role × category) |

**Example with overrides:**

```bash
make run TASK=JOB_USR_002 ENV=env_02
make run-openai MODEL=gpt-4o
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
