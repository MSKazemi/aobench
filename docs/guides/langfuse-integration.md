# Langfuse Integration Guide

Step-by-step plan for adding Langfuse observability to ExaBench.
Follow the phases in order; each phase is independently testable.

This page is the single Langfuse reference for ExaBench. It covers what Langfuse is, the local docker-compose stack under `docker/langfuse/`, and the runtime exporter wired through the `--langfuse` flag.

---

## Status

| Phase | Title | Status |
|-------|-------|--------|
| 1 | Stand up Langfuse locally | ✅ Done — running at http://localhost:3000 |
| 2 | Add SDK as optional dependency | ✅ Done |
| 3 | Create `BaseExporter` ABC | ✅ Done |
| 4 | Implement `LangfuseExporter` | ✅ Done |
| 5 | Wire exporter into `BenchmarkRunner` | ✅ Done |
| 6 | Add `--langfuse` CLI flag | ✅ Done |
| 7 | Update Makefile & COMMANDS.md | ✅ Done |
| 8 | Smoke-test end-to-end | ☐ Todo — add `.env` keys then run `make run-langfuse` |

---

## Phase 1 — Stand up Langfuse locally

**Goal**: all 6 Langfuse v3 services running, UI reachable at `http://localhost:3000`, API keys in hand.

### What gets started

Langfuse v3 is a multi-service stack (see `docker/langfuse/docker-compose.yml`):

| Container | Role |
|-----------|------|
| `langfuse-web` | UI + REST API on port 3000 |
| `langfuse-worker` | Background job processor |
| `postgres` | Project metadata, users, API keys |
| `clickhouse` | Trace + observation analytics store |
| `redis` | Task queue |
| `minio` | S3-compatible blob storage |

### Step 1.1 — Start the stack

```bash
make langfuse-up
# equivalent to: docker compose -f docker/langfuse/docker-compose.yml up -d
```

> **If a pull times out** (Docker Hub is flaky on large images), just run `make langfuse-up`
> again — already-downloaded layers are cached, only missing ones are retried.

### Step 1.2 — Wait for healthy status

First startup takes 1–2 minutes while services initialize and ClickHouse runs migrations.

```bash
# Watch until langfuse-web shows (healthy)
docker compose -f docker/langfuse/docker-compose.yml ps
```

Expected output when ready:
```
NAME                     STATUS
langfuse-web             Up X minutes (healthy)
langfuse-worker          Up X minutes
langfuse-clickhouse      Up X minutes (healthy)
langfuse-postgres        Up X minutes (healthy)
langfuse-redis           Up X minutes (healthy)
langfuse-minio           Up X minutes (healthy)
```

If `langfuse-web` keeps restarting, check its logs:
```bash
make langfuse-logs
# or: docker logs langfuse-web --tail 30
```

### Step 1.3 — Create account and project

1. Open **http://localhost:3000** in a browser
2. Click **Sign up** — the first user becomes admin
3. Create a new project — name it `exabench`
4. Go to **Settings → API Keys → Create new key**
5. Copy the **Public Key** (`pk-lf-...`) and **Secret Key** (`sk-lf-...`)

### Step 1.4 — Add credentials to `.env`

In the ExaBench repo root, copy `.env.example` to `.env` (if you haven't already) and fill in:

```bash
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=http://localhost:3000
```

**Verify**: open http://localhost:3000 — you should see your `exabench` project dashboard.

### Useful commands

```bash
make langfuse-down        # stop all containers (data preserved)
make langfuse-logs        # stream logs from all containers
make langfuse-reset       # stop + wipe ALL data (fresh start)
```

### Troubleshooting

#### TLS handshake timeout during image pull

**Symptom:** `docker compose up` fails with `TLS handshake timeout` on some images,
even though `curl https://registry-1.docker.io/v2/` works from the shell.

**Cause:** A **WireGuard VPN** (`wg0`, MTU 1420) is active. Docker's bridge defaults to
MTU 1500. Packets larger than the VPN MTU get fragmented, breaking TLS inside the daemon.

**Fix:** Lower Docker's MTU to 1400 and set reliable DNS:

```bash
sudo tee /etc/docker/daemon.json <<'EOF'
{
  "mtu": 1400,
  "dns": ["8.8.8.8", "1.1.1.1"]
}
EOF
sudo systemctl restart docker
make langfuse-up
```

**Verify:** `docker pull redis:7-alpine` should complete without timeout.

---

#### `langfuse-web` / `langfuse-worker` keep restarting — ClickHouse error

**Symptom:**
```
error: failed to open database: code: 139, message: There is no Zookeeper configuration
CREATE TABLE schema_migrations ON CLUSTER default ... Engine=ReplicatedMergeTree
```

**Cause:** Langfuse v3 creates tables using `ReplicatedMergeTree ON CLUSTER default`,
which requires ZooKeeper or ClickHouse Keeper. A plain ClickHouse image has neither by default.

**Fix:** The ExaBench compose mounts `docker/langfuse/clickhouse-config.xml` into ClickHouse,
which enables the **built-in ClickHouse Keeper** (no ZooKeeper container needed) and defines
the `default` single-node cluster. This file is already in the repo and mounted automatically.

If you see this error despite the config, wipe volumes and restart:
```bash
make langfuse-reset   # stops containers and deletes volumes
make langfuse-up
```

---

#### `ENCRYPTION_KEY` validation error

**Symptom:**
```
ENCRYPTION_KEY must be 256 bits, 64 string characters in hex format
```

**Cause:** Langfuse v3 validates the encryption key strictly. All-zero or placeholder keys
are rejected.

**Fix:** The key in `docker/langfuse/docker-compose.yml` is already a valid random 256-bit
hex key generated with `openssl rand -hex 32`. If you customise the compose file, generate
a new key with:

```bash
openssl rand -hex 32
```

Replace the `ENCRYPTION_KEY` value in both `langfuse-web` and `langfuse-worker` environment
sections with the same generated value.

---

## Phase 2 — Add SDK as optional dependency

**Files to change**: `pyproject.toml`

Add `langfuse` to `[project.optional-dependencies]`:

```toml
[project.optional-dependencies]
langfuse = ["langfuse>=2.0"]
```

Install locally:

```bash
pip install -e ".[langfuse]"
```

**Verify**:

```bash
python -c "import langfuse; print(langfuse.__version__)"
```

---

## Phase 3 — Create `BaseExporter` ABC

**New file**: `src/exabench/exporters/base_exporter.py`

The base class defines the contract all exporters must implement:

```python
from abc import ABC, abstractmethod
from exabench.schemas.result import BenchmarkResult
from exabench.schemas.task import TaskSpec
from exabench.schemas.trace import Trace

class BaseExporter(ABC):
    @abstractmethod
    def export(self, trace: Trace, result: BenchmarkResult, task: TaskSpec) -> None:
        """Export one completed task run."""

    def flush(self) -> None:
        """Flush any buffered data (optional)."""
```

Also create `src/exabench/exporters/__init__.py` (empty or re-export `BaseExporter`).

**Verify**: `python -c "from exabench.exporters.base_exporter import BaseExporter"` succeeds.

---

## Phase 4 — Implement `LangfuseExporter`

**New file**: `src/exabench/exporters/langfuse_exporter.py`

### Data mapping

| ExaBench field | Langfuse call | Notes |
|----------------|---------------|-------|
| `trace.trace_id` | `lf.trace(id=...)` | Reuses ExaBench ID |
| `trace.task_id` | `trace.name` | Human-readable name in UI |
| `trace.run_id` | `trace.session_id` | Groups all tasks in one run |
| `trace.role` | `trace.user_id` | Role as user identifier |
| `trace.adapter_name`, `model_name` | `trace.metadata` | Key-value dict |
| Each `TraceStep` | `trace.span(...)` | One span per step |
| `step.tool_call` | span `metadata` | Tool name + arguments |
| `step.observation` | span `output` | Tool result or error |
| LLM tokens (from Trace) | `trace.generation(...)` | One generation per run |
| `result.dimension_scores.*` | `trace.score(name, value)` | 6 scores |
| `result.aggregate_score` | `trace.score("aggregate", value)` | Summary score |

### Implementation outline

```python
class LangfuseExporter(BaseExporter):
    def __init__(self, public_key, secret_key, host=None):
        from langfuse import Langfuse
        self._lf = Langfuse(public_key=public_key, secret_key=secret_key, host=host)

    def export(self, trace, result, task):
        lf_trace = self._lf.trace(
            id=trace.trace_id,
            name=trace.task_id,
            session_id=trace.run_id,
            user_id=trace.role,
            metadata={...},
            tags=[trace.role, task.qcat, task.difficulty],
        )

        # One span per agent step
        for step in trace.steps:
            span = lf_trace.span(name=f"step-{step.step_id}", ...)
            span.end(output=..., metadata=...)

        # One generation for the overall LLM call
        if trace.total_tokens:
            lf_trace.generation(
                name="llm",
                model=trace.model_name,
                usage={"input": trace.prompt_tokens, "output": trace.completion_tokens},
            )

        # Attach scores
        for dim, value in result.dimension_scores.model_dump().items():
            if value is not None:
                lf_trace.score(name=dim, value=value)
        if result.aggregate_score is not None:
            lf_trace.score(name="aggregate", value=result.aggregate_score)

    def flush(self):
        self._lf.flush()
```

**Verify**: unit test with a mock `Langfuse` object.

---

## Phase 5 — Wire exporter into `BenchmarkRunner`

**File to change**: `src/exabench/runners/runner.py`

Add optional `exporter` parameter to `BenchmarkRunner.__init__`:

```python
def __init__(self, adapter, benchmark_root, output_root, exporter=None):
    ...
    self._exporter = exporter
```

After step 7 (write result to disk), add:

```python
# 8. Export to observability backend (optional)
if self._exporter is not None:
    self._exporter.export(trace, result, task)
```

Call `exporter.flush()` after all tasks in `run_all`.

**Verify**: run with `DirectQAAdapter` + `LangfuseExporter` and check trace appears in UI.

---

## Phase 6 — Add `--langfuse` CLI flag

**File to change**: `src/exabench/cli/run_cmd.py`

Add to both `run_task` and `run_all` command signatures:

```python
langfuse: Annotated[bool, typer.Option("--langfuse/--no-langfuse",
    help="Export traces and scores to Langfuse")] = False,
```

In the command body, before constructing `BenchmarkRunner`:

```python
exporter = None
if langfuse:
    from exabench.exporters.langfuse_exporter import LangfuseExporter
    import os
    exporter = LangfuseExporter(
        public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
        secret_key=os.environ["LANGFUSE_SECRET_KEY"],
        host=os.environ.get("LANGFUSE_HOST"),
    )

runner = BenchmarkRunner(..., exporter=exporter)
```

After `run_all` loop, flush:

```python
if exporter:
    exporter.flush()
```

**Verify**:

```bash
exabench run task --task JOB_USR_001 --env env_01 --adapter direct_qa --langfuse
# Trace should appear in Langfuse UI
```

---

## Phase 7 — Update Makefile & COMMANDS.md

**Makefile** — add a convenience target:

```makefile
run-langfuse: ## Run a task and export to Langfuse
	exabench run task \
		--task $(TASK) \
		--env $(ENV) \
		--adapter $(ADAPTER) \
		--langfuse \
		--no-report
```

**docs/COMMANDS.md** — document the new `--langfuse` option under `run task` and `run all`.

---

## Phase 8 — Smoke-test end-to-end

Checklist:

- [ ] `docker compose ps` — all Langfuse services healthy
- [ ] `.env` contains the three Langfuse variables
- [ ] `pip install -e ".[langfuse]"` succeeds
- [ ] `exabench run task --task JOB_USR_001 --env env_01 --adapter direct_qa --langfuse`
- [ ] Trace appears in Langfuse UI (`http://localhost:3000`)
- [ ] Trace has correct `session_id` = run_id, `name` = task_id
- [ ] Spans visible for each agent step
- [ ] Six dimension scores attached to trace
- [ ] `exabench run all --adapter openai --langfuse` — all tasks appear under one session
- [ ] Unit tests pass: `make test`

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LANGFUSE_PUBLIC_KEY` | Yes (if --langfuse) | — | Project public key from Langfuse UI |
| `LANGFUSE_SECRET_KEY` | Yes (if --langfuse) | — | Project secret key from Langfuse UI |
| `LANGFUSE_HOST` | No | `https://cloud.langfuse.com` | Override for self-hosted instance |

---

## File Manifest

Files created or modified by this integration:

| File | Action | Notes |
|------|--------|-------|
| `docker/langfuse/docker-compose.yml` | Create | Full v3 stack: postgres, clickhouse, redis, minio, web, worker |
| `docker/langfuse/clickhouse-config.xml` | Create | Enables ClickHouse Keeper + single-node cluster for Langfuse migrations |
| `src/exabench/exporters/__init__.py` | Create | Package init |
| `src/exabench/exporters/base_exporter.py` | Create | `BaseExporter` ABC |
| `src/exabench/exporters/langfuse_exporter.py` | Create | Langfuse implementation |
| `src/exabench/runners/runner.py` | Modify | Added `exporter=` param, step 8 calls `exporter.export()` |
| `src/exabench/cli/run_cmd.py` | Modify | `--langfuse/--no-langfuse` flag on `run task` and `run all` |
| `pyproject.toml` | Modify | `langfuse = ["langfuse>=2.0"]` optional dep |
| `Makefile` | Modify | `langfuse-up/down/logs/reset` + `run-langfuse` + `run-all-langfuse` targets |
| `.env.example` | Modify | Added Langfuse env var template |
| `docs/reference/commands.md` | Modify | `--langfuse` flag + Langfuse Makefile targets documented |
| `docs/guides/langfuse-integration.md` | Create | This guide (also serves as the Langfuse reference) |
| `tests/unit/test_langfuse_exporter.py` | Create | 10 unit tests (all passing) |
