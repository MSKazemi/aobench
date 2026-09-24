# Programmatic Access: REST API & MCP Server

Beyond the CLI, AOBench exposes its benchmark engine over two machine surfaces so
other tools and agents can run tasks, score traces, and read results
programmatically:

- a **REST API** (FastAPI) — HTTP access for any language or client;
- a **FastMCP server** — the same engine exposed as [Model Context
  Protocol](https://modelcontextprotocol.io) tools and resources, so an MCP
  client (an agent) can drive the benchmark directly.

Both are thin transports over one shared `BenchmarkService` façade, so a run
started over REST, over MCP, or from the CLI produces identical scores.

Each surface is an optional extra — install only what you need:

```bash
uv sync --extra rest      # REST API (fastapi + uvicorn)
uv sync --extra mcp       # FastMCP server
uv sync --extra rest --extra mcp --extra otel   # everything (list all together)
```

!!! note "Install extras together"
    Per-extra `uv sync` is exclusive — `uv sync --extra mcp` will *remove*
    `fastapi`. To keep multiple surfaces installed, list every extra in one
    command as shown above.

---

## REST API

### Start the server

The simplest way is the CLI:

```bash
uv run aobench serve rest --host 0.0.0.0 --port 8000
# OpenAPI docs at http://localhost:8000/docs  (schema at /openapi.json, OpenAPI 3.1)
```

Or embed it — `create_app()` returns a standard FastAPI application:

```python
# serve.py
import uvicorn
from aobench.server.rest.app import create_app

app = create_app()          # uses AOBENCH_BENCHMARK_ROOT / AOBENCH_OUTPUT_ROOT env
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Authentication

An API key maps to an HPC role. Configure keys via `AOBENCH_API_KEYS` as a
comma-separated `key:role` list; pass the key in the `X-API-Key` header:

```bash
export AOBENCH_API_KEYS="prod-key-1:hpc_user,admin-key:admin"
export AOBENCH_RATE_LIMIT_PER_MIN=1000        # optional; default 10000
```

When `AOBENCH_API_KEYS` is **unset**, the API runs in open (dev) mode and every
request resolves to the `admin` role — convenient locally, but always set keys in
production. A request over the per-minute budget receives `429 Too Many Requests`.

### Endpoints

| Method & path | Purpose |
|---|---|
| `GET /health` | Liveness probe (no auth) |
| `POST /v1/runs?wait=true` | Run a task against an env synchronously; returns `run_id` + score |
| `POST /v1/runs?wait=false` | Enqueue as a tracked job; returns a job record to poll |
| `GET /v1/jobs/{job_id}` | Poll a job's state (`queued`/`running`/`completed`/`failed`) |
| `GET /v1/jobs` | List submitted jobs |
| `GET /v1/runs/{run_id}` | Run record (task count, aggregate score, hard-fails) |
| `GET /v1/runs/{run_id}/trace?task_id=` | Full execution trace |
| `GET /v1/runs/{run_id}/report?format=json` | Scorecard summary (`json`/`summary`/`clear`) |
| `GET /v1/runs/{run_id}/events` | **SSE** stream: replays trace steps, then a `done` event |
| `POST /v1/score` | Score a supplied trace against a task (no re-run) |
| `POST /v1/compare` | Compare two runs (score delta) |
| `POST /v1/robustness` | Run a task `n` times; mean/stdev + pass^k |
| `GET /v1/tasks?split=&qcat=&role=` | List task specs |
| `GET /v1/envs` | List environment bundles |
| `GET /v1/datasets` | Versioned splits as datasets |

### Example

```bash
# run one task
curl -s -X POST "http://localhost:8000/v1/runs?wait=true" \
  -H "X-API-Key: admin-key" -H "Content-Type: application/json" \
  -d '{"task_id": "JOB_USR_001", "env_id": "env_01", "adapter": "direct_qa"}'
# → {"run_id": "...", "status": "completed", "aggregate_score": 0.83, ...}

# read its scorecard
curl -s "http://localhost:8000/v1/runs/<run_id>/report?format=clear" \
  -H "X-API-Key: admin-key"
```

For long sweeps, submit with `wait=false` to get a job record immediately and poll
`GET /v1/jobs/{job_id}` until its `state` is terminal. (Single-process job tracking
works out of the box; a durable arq/Redis worker is a drop-in backend upgrade.)

Synchronous errors map to HTTP status codes: unknown task/env/run/job → `404`, locked
split or forbidden role → `403`, blocked task on a new run → `409`, adapter failure →
`502`, bad report format → `400`. With `wait=false`, run failures instead appear in the
returned job record; a blocked task has `state: failed` and an error beginning with
`TaskBlocked:`. `POST /v1/score` still scores a supplied trace, including an external
trace for a blocked task; it does not start a run.

---

## MCP Server (FastMCP)

The FastMCP server exposes the same engine as MCP **tools** (actions) and
**resources** (read-only catalog/results), targeting MCP spec `2025-11-25`.

### Start the server

Via the CLI:

```bash
uv run aobench serve mcp     # stdio transport
```

Or embed it:

```python
from aobench.server.mcp import create_server

server = create_server()     # raises RuntimeError if the `mcp` extra is absent
server.run()                 # stdio transport by default
```

### Tools

| Tool | Purpose |
|---|---|
| `run_task(task_id, env_id, adapter="direct_qa", role=None, seed=None)` | Run a task; returns `run_id` + score |
| `score_trace(task_id, trace)` | Score a captured trace without re-running |
| `validate_benchmark()` | Loadable task/env counts (health check) |
| `robustness(task_id, env_id, adapter="direct_qa", n=5)` | Repeat a run; score mean/stdev |

### Resources

| Resource URI | Contents |
|---|---|
| `aobench://catalog/tasks` | All task specs with QCAT/role/split |
| `aobench://catalog/tasks/{task_id}` | One task's metadata |
| `aobench://catalog/envs` | All env bundles with manifest fingerprints |
| `aobench://runs/{run_id}/report` | Scorecard summary for a run |
| `aobench://runs/{run_id}/trace` | Full execution trace for a run |

### Authentication (HTTP transport)

For the HTTP transport, enable OAuth 2.1 resource-server auth by setting the JWKS
environment variables; the server maps JWT claims to HPC roles:

```bash
export AOBENCH_MCP_JWKS_URI="https://issuer.example.com/.well-known/jwks.json"
export AOBENCH_MCP_ISSUER="https://issuer.example.com/"
export AOBENCH_MCP_AUDIENCE="aobench-mcp"
```

Over the local stdio transport (the default), no auth is required.

### Drive it from a client

```python
import asyncio, json
from fastmcp import Client
from aobench.server.mcp import create_server

async def main():
    async with Client(create_server()) as client:
        run = await client.call_tool(
            "run_task",
            {"task_id": "JOB_USR_001", "env_id": "env_01", "adapter": "direct_qa"},
        )
        run_id = run.data["run_id"]
        report = await client.read_resource(f"aobench://runs/{run_id}/report")
        print(json.loads(report[0].text))

asyncio.run(main())
```

---

## Which surface should I use?

- **REST** — integrate AOBench into a web app, dashboard, or any HTTP client; run
  large sweeps behind a stable API.
- **MCP** — let an agent (Claude, or any MCP client) call the benchmark as native
  tools, or dogfood MCP tool-use itself.
- **CLI** — interactive/local use and scripting (see the [CLI reference](../reference/commands.md)).

All three route through the same façade, so results are directly comparable.
