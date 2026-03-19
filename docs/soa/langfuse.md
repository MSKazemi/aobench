# Langfuse — LLM Observability Platform

Reference document covering what Langfuse is, how it works, and why it is relevant to ExaBench.

---

## What Is Langfuse?

Langfuse is an **open-source LLM engineering platform** that provides:

- **Tracing** — capture every LLM call, tool invocation, and agent step as a structured tree of spans
- **Evaluation** — attach numeric scores to traces for regression analysis and quality tracking
- **Prompt management** — version and A/B-test system prompts without code changes
- **Dataset management** — build curated test sets from production traces
- **Cost & latency monitoring** — per-model token usage, USD cost, and p50/p95 latency dashboards

Website: <https://langfuse.com>
GitHub: <https://github.com/langfuse/langfuse> (MIT License)
Docs: <https://langfuse.com/docs>

---

## Licensing & Pricing

| Tier | Cost | Notes |
|------|------|-------|
| **Self-hosted (OSS)** | Free | MIT license, full features, Docker Compose |
| **Cloud — Hobby** | Free | 50 k observations/month, 30-day retention |
| **Cloud — Pro** | $59/month | Unlimited observations, team features |
| **Cloud — Enterprise** | Custom | SSO, SLA, on-prem support |

> **Recommended for ExaBench**: self-host with Docker Compose.
> All benchmark data stays on your own machine; no usage limits; no subscription required.

---

## Core Concepts

### Observation hierarchy

```
Trace  (one per agent run)
 └─ Span           (a logical unit of work — e.g., "tool call", "planning step")
     └─ Generation (an LLM call — captures prompt, completion, model, tokens, cost)
```

Every trace has a unique `trace_id`. ExaBench's existing `trace_id` maps directly to this.

### Scores

Scores are numeric values (or categorical labels) attached to a trace or span after the fact.
They are used to track quality metrics across runs and model versions.

ExaBench's six scoring dimensions (outcome, tool_use, grounding, governance, robustness, efficiency)
map cleanly to Langfuse scores attached to the root trace.

### Sessions & Users

- **Session**: groups multiple traces from one user session or one benchmark run.
- **User**: identifies who ran the query. For ExaBench, `run_id` = session, `role` = user.

---

## Langfuse Data Model vs. ExaBench Data Model

| ExaBench | Langfuse | Notes |
|----------|----------|-------|
| `Trace.trace_id` | `trace.id` | 1:1 mapping |
| `Trace.run_id` | `trace.session_id` | Groups all traces in one benchmark run |
| `Trace.role` | `trace.user_id` | Identifies role (scientific_user, sysadmin, …) |
| `Trace.task_id` | `trace.name` | Human-readable trace name |
| `Trace.adapter_name` + `model_name` | `trace.metadata` | Stored as key-value metadata |
| `TraceStep` (tool call + observation) | `span` | One span per step |
| LLM call inside adapter | `generation` | With model, tokens, cost |
| `BenchmarkResult.dimension_scores.*` | `score` objects | Attached to root trace post-scoring |
| `BenchmarkResult.aggregate_score` | `score` (name="aggregate") | Summary score |

---

## Python SDK

Install:

```bash
pip install langfuse
```

Minimal usage:

```python
from langfuse import Langfuse

lf = Langfuse(
    public_key="pk-lf-...",
    secret_key="sk-lf-...",
    host="http://localhost:3000",   # or https://cloud.langfuse.com
)

trace = lf.trace(id="my-trace-id", name="JOB_USR_001", session_id="run-abc")

span = trace.span(name="step-1-slurm_tool", metadata={"tool": "slurm"})
span.end()

gen = trace.generation(
    name="llm-call",
    model="gpt-4o",
    usage={"input": 120, "output": 45},
    input=[{"role": "user", "content": "..."}],
    output="...",
)

trace.score(name="outcome", value=0.9)
trace.score(name="tool_use", value=0.75)

lf.flush()
```

---

## Architecture (v3)

Langfuse v3 is a multi-service stack. Every service is required:

| Service | Image | Purpose |
|---------|-------|---------|
| `langfuse-web` | `langfuse/langfuse` | UI + REST API (port 3000) |
| `langfuse-worker` | `langfuse/langfuse-worker` | Background job processor |
| `postgres` | `postgres:16-alpine` | Project metadata, users, API keys |
| `clickhouse` | `clickhouse/clickhouse-server:24.12` | Trace + observation analytics store |
| `redis` | `redis:7-alpine` | Task queue between web and worker |
| `minio` | `minio/minio` | S3-compatible blob storage (media uploads) |
> **Why so many?** Langfuse v3 separated trace storage (ClickHouse, columnar DB optimized
> for analytics) from metadata (Postgres). This allows querying millions of traces fast.
> Prior to v3, only Postgres was needed.

> **ClickHouse Keeper**: ClickHouse requires ZooKeeper (or its built-in replacement,
> ClickHouse Keeper) to manage `ReplicatedMergeTree` tables used by Langfuse migrations.
> The ExaBench compose file ships `docker/langfuse/clickhouse-config.xml` which enables
> the built-in Keeper — no external ZooKeeper container is needed.

## Self-Hosting with Docker Compose

A ready-to-use `docker-compose.yml` is included in the ExaBench repo at
`docker/langfuse/docker-compose.yml`. No external cloning needed.

```bash
# From the ExaBench repo root:
make langfuse-up          # start all 6 services
make langfuse-down        # stop (data volumes preserved)
make langfuse-logs        # stream logs from all containers
make langfuse-reset       # stop + wipe all data volumes

# Or call Docker Compose directly:
docker compose -f docker/langfuse/docker-compose.yml up -d
```

**First startup takes 1–2 minutes** — wait for the health check:

```bash
docker compose -f docker/langfuse/docker-compose.yml ps
# langfuse-web should show (healthy) before opening the browser
```

- UI available at `http://localhost:3000`
- First user to register becomes the admin
- Create a project → copy `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY`
- All data persists in named Docker volumes across restarts

**Troubleshooting — pull timeouts (WireGuard/VPN users):** If `make langfuse-up` fails
with `TLS handshake timeout` even though `curl https://registry-1.docker.io/v2/` works,
the Docker daemon's MTU (1500) is larger than your VPN tunnel's MTU (e.g. WireGuard uses
1420). Fix it once:

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

If the pull simply times out mid-download (no VPN), run `make langfuse-up` again —
already-downloaded layers are cached and only missing layers are retried.

Environment variables needed by ExaBench:

```bash
export LANGFUSE_PUBLIC_KEY="pk-lf-..."
export LANGFUSE_SECRET_KEY="sk-lf-..."
export LANGFUSE_HOST="http://localhost:3000"   # omit for Langfuse Cloud
```

Or put them in a `.env` file at the project root (already loaded via `python-dotenv`).

---

## Relevant Links

- Python SDK reference: <https://langfuse.com/docs/sdk/python>
- Tracing concepts: <https://langfuse.com/docs/tracing>
- Self-hosting guide: <https://langfuse.com/docs/deployment/self-host>
- Docker Compose file: `docker/langfuse/docker-compose.yml` (included in ExaBench repo)
- ClickHouse Keeper config: `docker/langfuse/clickhouse-config.xml` (required for single-node)
