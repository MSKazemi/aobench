"""Tests for the AOBench FastMCP server (spec-0004).

Handler logic is tested without FastMCP; one integration test drives the server
in-memory via the FastMCP client when the extra is installed.
"""

from __future__ import annotations

import asyncio
import json

import pytest

from aobench.server.mcp import handlers
from aobench.service import BenchmarkService, TaskBlocked


@pytest.fixture()
def svc(tmp_path):
    return BenchmarkService(benchmark_root="benchmark", output_root=str(tmp_path))


@pytest.fixture()
def a_task(svc):
    t = svc.list_tasks()[0]
    return t.task_id, (t.environment_id or "env_01")


# --------------------------------------------------------------------------- #
# Pure handlers (no fastmcp required)
# --------------------------------------------------------------------------- #
def test_validate_benchmark(svc):
    out = handlers.validate_benchmark(svc)
    assert out["ok"] is True
    assert out["n_tasks"] > 0 and out["n_envs"] > 0


def test_run_task_and_report_and_trace(svc, a_task):
    tid, eid = a_task
    res = handlers.run_task(svc, tid, eid, "direct_qa")
    assert res["status"] == "completed"
    run_id = res["run_id"]

    report = json.loads(handlers.run_report(svc, run_id))
    assert report["payload"]["run_id"] == run_id

    trace = json.loads(handlers.run_trace(svc, run_id))
    assert "steps" in trace


def test_blocked_run_handler_keeps_typed_error(svc):
    with pytest.raises(TaskBlocked, match="scoring_readiness: blocked"):
        handlers.run_task(svc, "PERF_FAC_001", "env_12")


def test_score_trace_handler(svc, a_task):
    tid, eid = a_task
    res = handlers.run_task(svc, tid, eid, "direct_qa")
    trace = json.loads(handlers.run_trace(svc, res["run_id"]))
    scored = handlers.score_trace(svc, tid, trace)
    assert scored["task_id"] == tid


def test_catalog_resources(svc, a_task):
    tid, _ = a_task
    tasks = json.loads(handlers.catalog_tasks(svc))
    assert tasks["count"] > 0
    one = json.loads(handlers.catalog_task(svc, tid))
    assert one["task_id"] == tid
    missing = json.loads(handlers.catalog_task(svc, "NOPE_X"))
    assert missing["error"] == "task_not_found"
    envs = json.loads(handlers.catalog_envs(svc))
    assert envs["count"] > 0


def test_robustness_handler(svc, a_task):
    tid, eid = a_task
    out = handlers.robustness(svc, tid, eid, "direct_qa", n=2)
    assert out["n"] == 2
    assert out["stdev"] == pytest.approx(0.0, abs=1e-9)


# --------------------------------------------------------------------------- #
# create_server guard
# --------------------------------------------------------------------------- #
def test_create_server_guard(svc):
    from aobench.server.mcp import FASTMCP_AVAILABLE, create_server

    if not FASTMCP_AVAILABLE:
        with pytest.raises(RuntimeError):
            create_server(svc)
    else:
        server = create_server(svc)
        assert server.__class__.__name__ == "FastMCP"


# --------------------------------------------------------------------------- #
# Integration via in-memory FastMCP client
# --------------------------------------------------------------------------- #
def test_mcp_client_inmemory(svc):
    fastmcp = pytest.importorskip("fastmcp")
    from aobench.server.mcp import create_server

    server = create_server(svc)

    async def _run():
        async with fastmcp.Client(server) as client:
            tools = {t.name for t in await client.list_tools()}
            assert {"run_task", "score_trace", "validate_benchmark", "robustness"} <= tools
            result = await client.call_tool("validate_benchmark", {})
            data = getattr(result, "data", None)
            if data is None:  # fallback for older client shapes
                data = json.loads(result.content[0].text)
            assert data["ok"] is True
            return data

    data = asyncio.run(_run())
    assert data["n_tasks"] > 0


# --------------------------------------------------------------------------- #
# In-memory FastMCP client drive-through (covers the tool/resource bindings)
# --------------------------------------------------------------------------- #
def test_server_inmemory_client_drive(svc, a_task):
    from aobench.server.mcp import FASTMCP_AVAILABLE, create_server

    if not FASTMCP_AVAILABLE:
        pytest.skip("fastmcp not installed")

    from fastmcp import Client

    tid, eid = a_task
    server = create_server(svc)

    async def _drive():
        async with Client(server) as client:
            names = {t.name for t in await client.list_tools()}
            assert {"run_task", "score_trace", "validate_benchmark", "robustness"} <= names

            await client.call_tool("validate_benchmark", {})
            run = await client.call_tool(
                "run_task", {"task_id": tid, "env_id": eid, "adapter": "direct_qa"})
            run_id = run.data["run_id"]

            await client.call_tool("robustness",
                                   {"task_id": tid, "env_id": eid, "adapter": "direct_qa", "n": 2})

            trace_res = await client.read_resource(f"aobench://runs/{run_id}/trace")
            trace = json.loads(trace_res[0].text)
            await client.call_tool("score_trace", {"task_id": tid, "trace": trace})

            # resources
            await client.read_resource("aobench://catalog/tasks")
            await client.read_resource(f"aobench://catalog/tasks/{tid}")
            await client.read_resource("aobench://catalog/envs")
            await client.read_resource(f"aobench://runs/{run_id}/report")
            return run_id

    run_id = asyncio.run(_drive())
    assert run_id


def test_build_auth_none_without_jwks(svc, monkeypatch):
    monkeypatch.delenv("AOBENCH_MCP_JWKS_URI", raising=False)
    from aobench.server.mcp.server import _build_auth
    assert _build_auth() is None
