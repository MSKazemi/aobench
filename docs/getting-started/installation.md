# Installation & Running AOBench

This page is the single, canonical guide to **installing AOBench and running it**.

!!! tip "In a hurry?"
    ```bash
    git clone https://github.com/MSKazemi/aobench.git && cd aobench && make install
    aobench quickstart
    ```
    That is the whole happy path — see the **[Quickstart](quickstart.md)** for what the
    output means. This page is the reference for everything else: the other install
    paths, the optional extras, and the container images.

There are three supported paths — pick the one that matches how you want to use the
benchmark:

| Path | Best for | What you get |
|------|----------|--------------|
| **A · Python package** | Running the benchmark, the CLI, and the REST/MCP servers on your own machine | The `aobench` CLI + the Python API (`BenchmarkService`) |
| **B · Docker CLI image** | A reproducible, dependency-free run of the CLI | A container whose entrypoint *is* `aobench` |
| **C · Docker Compose stack** | The observability + leaderboard services (Langfuse + leaderboard API) | A running Langfuse UI and leaderboard HTTP API |

Paths B and C are complementary to A, not replacements: the Compose stack runs the
**services** around the benchmark, while you still drive runs with the CLI or REST/MCP
surfaces.

---

## Requirements

- **Python ≥ 3.10** (3.12 is used in the Docker image and CI, and is recommended).
- **[uv](https://docs.astral.sh/uv/)** — the project's package manager/runner (recommended).
  Plain `pip` also works.
- **Docker** with **Compose v2.20+** — only for paths B and C.
  Check with `docker compose version`.

AOBench evaluates agents against **deterministic environment snapshots** with mock HPC
tools, so no live cluster, SLURM install, or GPU is required.

---

## Path A — Python package (recommended)

AOBench is a standard Python package that installs an `aobench` console script.

### With uv (recommended)

```bash
git clone https://github.com/MSKazemi/aobench.git
cd aobench

# Install the package with the dev group + all optional extras
uv sync --all-extras
```

### With pip

```bash
git clone https://github.com/MSKazemi/aobench.git
cd aobench

# Editable install with the dev extras
pip install -e ".[dev]"
```

!!! note "Not yet on PyPI"
    AOBench is installed **from source** (editable / `uv sync`). There is no
    `pip install aobench` from PyPI yet — clone the repository first.

### Optional extras

Install only the surfaces/adapters you need. Extras compose (list several together):

| Extra | Enables | Install |
|-------|---------|---------|
| `openai` | OpenAI adapter | `uv sync --extra openai` |
| `anthropic` | Anthropic adapter | `uv sync --extra anthropic` |
| `mcp` | MCP client adapter **and** the `aobench serve mcp` server | `uv sync --extra mcp` |
| `rest` | The `aobench serve rest` FastAPI server | `uv sync --extra rest` |
| `langfuse` | Langfuse trace export (`--langfuse`) | `uv sync --extra langfuse` |
| `leaderboard` | The leaderboard FastAPI service | `uv sync --extra leaderboard` |
| `otel` | OpenTelemetry span export | `uv sync --extra otel` |

!!! warning "`uv sync --extra` is exclusive"
    Each `uv sync --extra X` call resolves to *exactly* that set and will **remove**
    previously-installed extras. To keep several, list them in one call:
    `uv sync --extra rest --extra mcp --extra langfuse`. Or just use
    `uv sync --all-extras`.

### Choosing an install target

| Makefile target | Installs | Use when |
|---|---|---|
| `make install` | dev group **and** every optional extra | You are contributing, or you want every adapter available |
| `make install-dev` | dev group only (pytest, ruff, mypy) | You are contributing but do not need the provider SDKs |
| `make install-core` | just enough to run the benchmark | You only want to *use* AOBench |

### Verify the install

```bash
aobench --version                  # CLI is on PATH
aobench doctor                     # Python, corpus, extras, credentials — with fixes
```

`aobench doctor` exits non-zero only when a **required** check fails. Missing optional
extras and absent API keys are reported as warnings, because the `direct_qa` baseline
genuinely needs neither. `aobench info --json` prints the same picture as a JSON blob —
paste that into a bug report.

If the `aobench` console script is not on your `PATH`, `python -m aobench` is equivalent.

### First run

```bash
# The whole thing in one command — no arguments, no API key, no network
aobench quickstart

# The same run, spelled out
aobench run task --task JOB_USR_001 --env env_01 --adapter direct_qa

# A real adapter (needs a key)
export OPENAI_API_KEY=sk-…
aobench run all --adapter openai:gpt-4o --split dev
aobench report json data/runs/<run_id>
aobench clear run data/runs/<run_id>
```

See the **[Quickstart](quickstart.md)** for a narrated walkthrough of that first run
and how to read the seven-dimension scorecard.

### Where the benchmark corpus comes from

Every command needs the corpus (task specs, environment snapshots, scoring configs).
AOBench finds it automatically, in this order:

1. `$AOBENCH_BENCHMARK_ROOT`, if set — an explicit override.
2. A `benchmark/` directory found by walking **up** from the current directory, so a
   source checkout works from any subdirectory.
3. The copy bundled inside the installed package — so a wheel install works from any
   directory at all, with no checkout present.

Every command also accepts `--benchmark /path/to/benchmark` to override it for a single
invocation. If none of the three resolve, the error names all the locations tried.

See the [CLI command reference](../reference/commands.md) for every subcommand, and
[Serve the Benchmark](../tutorials/serving-the-benchmark.md) to drive it over REST/MCP.

---

## Path B — Docker CLI image

The repository ships a `Dockerfile` that builds a slim image whose **entrypoint is the
`aobench` CLI**. Use it for a reproducible, host-independent run.

```bash
# Build the image
docker build -t aobench:latest .

# Run any aobench subcommand — arguments after the image name are passed to aobench
docker run --rm aobench:latest --help
docker run --rm aobench:latest validate benchmark
docker run --rm aobench:latest run task \
  --task JOB_USR_001 --env env_01 --adapter direct_qa
```

To persist run artifacts to the host and pass API keys:

```bash
docker run --rm \
  -e OPENAI_API_KEY \
  -v "$PWD/data:/app/data" \
  aobench:latest run all --adapter openai:gpt-4o --split dev
```

A one-shot build + entrypoint smoke test is wired into the Makefile:

```bash
make repro-docker
```

---

## Path C — Docker Compose stack (Langfuse + leaderboard)

The root `compose.yml` brings up the **service stack** around the benchmark —
[Langfuse](../guides/langfuse-integration.md) for observability and the leaderboard
HTTP API — via Compose's `include:` (requires Compose **v2.20+**).

```bash
# Start the full stack (Langfuse UI + leaderboard API)
make stack-up

# Stream logs / stop (volumes are preserved on stop)
make stack-logs
make stack-down
```

| What | URL |
|------|-----|
| Langfuse UI | <http://localhost:3000> |
| Leaderboard API | <http://localhost:8000> (health: `/health`) |

`make stack-up` runs `langfuse-setup` first, which writes Langfuse keys into `.env`
idempotently. To run only one service:

```bash
make langfuse-up          # Langfuse only  → http://localhost:3000
make leaderboard-serve    # leaderboard API only (needs the `leaderboard` extra)
```

Once Langfuse is up, export traces from any run with the `--langfuse` flag (e.g.
`make run-langfuse`). See the [Langfuse integration guide](../guides/langfuse-integration.md)
for the full stack layout and troubleshooting.

---

## Environment variables

Copy the example file and fill in what you need:

```bash
cp .env.example .env
```

Key variables (see `.env.example` for the full list):

| Variable | Purpose |
|----------|---------|
| `LLM_PROVIDER` | `azure` or `openai` |
| `OPENAI_API_KEY` | OpenAI adapter |
| `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT` | Azure path |
| `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL` | Langfuse export |

---

## Where to go next

- **[Serve the Benchmark](../tutorials/serving-the-benchmark.md)** — run the engine over REST & MCP.
- **[Programmatic access](../guides/programmatic-access.md)** — call the `BenchmarkService` façade directly.
- **[CLI command reference](../reference/commands.md)** — every subcommand and flag.
- **[Adapters & tools](../guides/adapters-and-tools.md)** — how adapters and mock tools fit together.
