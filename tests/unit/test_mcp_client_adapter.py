"""Unit tests for MCPClientAdapter.

All tests mock the MCP session and OpenAI client — no real MCP server or API
key is needed.  The tests verify:
  - Connection string parsing (stdio / sse / http shorthand)
  - Tool schema conversion from MCP format to OpenAI function-calling format
  - Agentic loop: tool call → MCP result → next LLM round → final answer
  - Permission-denied detection and hard_fail propagation
  - Trace fields populated correctly (steps, tokens, adapter_name, etc.)
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from exabench.adapters.mcp_client_adapter import (
    MCPClientAdapter,
    _extract_text,
    _mcp_tool_to_openai_schema,
    _run_async,
)
from exabench.schemas.environment import EnvironmentBundle, EnvironmentMetadata
from exabench.schemas.task import EvalCriteria, TaskSpec
from exabench.schemas.trace import Trace


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_task(task_id: str = "TST_001") -> TaskSpec:
    return TaskSpec(
        task_id=task_id,
        title="Test task",
        query_text="Why did my job fail?",
        role="scientific_user",
        qcat="JOB",
        difficulty="easy",
        environment_id="env_01",
        expected_answer_type="diagnosis",
        eval_criteria=EvalCriteria(evaluation_mode="semantic_match", gold_answer="OOM"),
    )


def _make_env() -> EnvironmentBundle:
    meta = EnvironmentMetadata(
        environment_id="env_01",
        snapshot_name="oom_failure_v1",
        scenario_type="job_failure",
        cluster_name="test_cluster",
        snapshot_timestamp="2026-01-01T00:00:00Z",
        bundle_root="/tmp/env_01",
        supported_roles=["scientific_user"],
        supported_categories=["JOB"],
        included_sources=["slurm"],
        included_files=["slurm/slurm_state.json"],
        implementation_status="validated",
        validation_status="validated",
        description="Test environment",
    )
    return EnvironmentBundle(metadata=meta, root_path="/tmp/env_01")


def _make_context():
    from exabench.runners.context import ExecutionContext
    from exabench.tools.registry import ToolRegistry

    tools = ToolRegistry(tools={}, allowed_tool_names=["slurm"])
    return ExecutionContext(task=_make_task(), env=_make_env(), tools=tools, run_id="run_test")


def _mcp_tool(name: str, description: str = "A tool", schema: dict | None = None) -> Any:
    t = SimpleNamespace()
    t.name = name
    t.description = description
    t.inputSchema = schema or {"type": "object", "properties": {}}
    return t


def _text_content(text: str) -> Any:
    c = SimpleNamespace()
    c.text = text
    return c


def _mcp_call_result(text: str, is_error: bool = False) -> Any:
    r = SimpleNamespace()
    r.content = [_text_content(text)]
    r.isError = is_error
    return r


def _openai_message(content: str | None = None, tool_calls: list | None = None) -> Any:
    msg = MagicMock()
    msg.content = content
    msg.tool_calls = tool_calls or []
    msg.model_dump.return_value = {"role": "assistant", "content": content, "tool_calls": []}
    return msg


def _openai_tool_call(call_id: str, fn_name: str, arguments: dict) -> Any:
    tc = MagicMock()
    tc.id = call_id
    tc.function.name = fn_name
    tc.function.arguments = json.dumps(arguments)
    return tc


def _openai_response(msg: Any, total_tokens: int = 100) -> Any:
    usage = SimpleNamespace(total_tokens=total_tokens)
    choice = SimpleNamespace(message=msg)
    return SimpleNamespace(choices=[choice], usage=usage)


# ── Schema conversion ──────────────────────────────────────────────────────────

def test_mcp_tool_to_openai_schema_basic():
    tool = _mcp_tool("slurm__query_jobs", "Query jobs", {"type": "object", "properties": {"state": {"type": "string"}}})
    schema = _mcp_tool_to_openai_schema(tool)
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "slurm__query_jobs"
    assert schema["function"]["description"] == "Query jobs"
    assert "state" in schema["function"]["parameters"]["properties"]


def test_mcp_tool_to_openai_schema_no_description():
    tool = _mcp_tool("my_tool", "")
    schema = _mcp_tool_to_openai_schema(tool)
    assert schema["function"]["description"] == ""


def test_mcp_tool_to_openai_schema_none_input_schema():
    tool = _mcp_tool("my_tool")
    tool.inputSchema = None
    schema = _mcp_tool_to_openai_schema(tool)
    assert schema["function"]["parameters"] == {"type": "object", "properties": {}}


# ── Text extraction ────────────────────────────────────────────────────────────

def test_extract_text_single():
    assert _extract_text([_text_content("hello")]) == "hello"


def test_extract_text_multiple():
    items = [_text_content("line1"), _text_content("line2")]
    assert _extract_text(items) == "line1\nline2"


def test_extract_text_empty():
    assert _extract_text([]) == ""


def test_extract_text_no_text_attr():
    item = SimpleNamespace(data=42)  # no .text
    result = _extract_text([item])
    assert "data=42" in result  # str(item) fallback


# ── Adapter constructor ────────────────────────────────────────────────────────

def test_adapter_rejects_empty_server():
    with pytest.raises(ValueError, match="server connection string"):
        MCPClientAdapter(server="")


def test_adapter_stores_server():
    a = MCPClientAdapter(server="stdio:python server.py", model="gpt-4o-mini")
    assert a._server == "stdio:python server.py"
    assert a._model == "gpt-4o-mini"


def test_adapter_name():
    assert MCPClientAdapter.name == "mcp"


# ── _run_async: full agentic loop ──────────────────────────────────────────────

def _make_transport_mock(tools: list, call_results: list[Any]):
    """Build layered async context manager mocks for MCP transport + session."""

    session = AsyncMock()
    session.initialize = AsyncMock()

    tools_result = SimpleNamespace(tools=tools)
    session.list_tools = AsyncMock(return_value=tools_result)

    session.call_tool = AsyncMock(side_effect=call_results)

    # ClientSession(read, write) async context manager
    session_cm = AsyncMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=False)

    # stdio_client / sse_client context manager → (read_stream, write_stream)
    read_stream = MagicMock()
    write_stream = MagicMock()
    transport_cm = AsyncMock()
    transport_cm.__aenter__ = AsyncMock(return_value=(read_stream, write_stream))
    transport_cm.__aexit__ = AsyncMock(return_value=False)

    return transport_cm, session_cm, session


def _run(coro):
    return asyncio.run(coro)


@patch("exabench.adapters.mcp_client_adapter.AsyncOpenAI")
@patch("exabench.adapters.mcp_client_adapter.ClientSession")
@patch("exabench.adapters.mcp_client_adapter.StdioServerParameters", MagicMock())
@patch("exabench.adapters.mcp_client_adapter.stdio_client")
def test_run_async_single_tool_call_then_final(mock_stdio, mock_cs_cls, mock_oai_cls):
    context = _make_context()
    tools = [_mcp_tool("slurm__query_jobs", "Query jobs")]
    mcp_result = _mcp_call_result('{"jobs": [{"id": 891234, "state": "FAILED"}]}')

    transport_cm, session_cm, session = _make_transport_mock([tools[0]], [mcp_result])
    mock_stdio.return_value = transport_cm
    mock_cs_cls.return_value = session_cm

    # LLM round 1 → tool call;  round 2 → final answer
    tc = _openai_tool_call("tc1", "slurm__query_jobs", {"state": "FAILED"})
    msg1 = _openai_message(tool_calls=[tc])
    msg2 = _openai_message(content="Job 891234 failed due to OOM.")

    oai_instance = AsyncMock()
    oai_instance.chat.completions.create = AsyncMock(
        side_effect=[_openai_response(msg1, 80), _openai_response(msg2, 60)]
    )
    mock_oai_cls.return_value = oai_instance

    trace: Trace = _run(_run_async("stdio:python agent.py", context, "gpt-4o", "You are helpful."))

    assert trace.task_id == "TST_001"
    assert trace.adapter_name == "mcp"
    assert trace.final_answer == "Job 891234 failed due to OOM."
    assert trace.total_tokens == 140
    assert trace.hard_fail is False

    # Step 1 = tool call, Step 2 = final answer
    assert len(trace.steps) == 2
    assert trace.steps[0].tool_call is not None
    assert trace.steps[0].tool_call.tool_name == "slurm__query_jobs"
    assert trace.steps[0].tool_call.arguments == {"state": "FAILED"}
    assert trace.steps[1].reasoning == "Job 891234 failed due to OOM."


@patch("exabench.adapters.mcp_client_adapter.AsyncOpenAI")
@patch("exabench.adapters.mcp_client_adapter.ClientSession")
@patch("exabench.adapters.mcp_client_adapter.sse_client")
def test_run_async_sse_transport(mock_sse, mock_cs_cls, mock_oai_cls):
    context = _make_context()
    transport_cm, session_cm, _ = _make_transport_mock([], [])
    mock_sse.return_value = transport_cm
    mock_cs_cls.return_value = session_cm

    msg = _openai_message(content="No tools available, here is my answer.")
    oai_instance = AsyncMock()
    oai_instance.chat.completions.create = AsyncMock(return_value=_openai_response(msg, 50))
    mock_oai_cls.return_value = oai_instance

    trace = _run(_run_async("sse:http://localhost:8000/sse", context, "gpt-4o", "Be helpful."))

    mock_sse.assert_called_once_with(url="http://localhost:8000/sse")
    assert trace.final_answer == "No tools available, here is my answer."


@patch("exabench.adapters.mcp_client_adapter.AsyncOpenAI")
@patch("exabench.adapters.mcp_client_adapter.ClientSession")
@patch("exabench.adapters.mcp_client_adapter.sse_client")
def test_run_async_http_shorthand(mock_sse, mock_cs_cls, mock_oai_cls):
    """http:// prefix should also route to sse_client."""
    context = _make_context()
    transport_cm, session_cm, _ = _make_transport_mock([], [])
    mock_sse.return_value = transport_cm
    mock_cs_cls.return_value = session_cm

    msg = _openai_message(content="Done.")
    oai_instance = AsyncMock()
    oai_instance.chat.completions.create = AsyncMock(return_value=_openai_response(msg))
    mock_oai_cls.return_value = oai_instance

    _run(_run_async("http://localhost:9000/sse", context, "gpt-4o", ""))
    mock_sse.assert_called_once_with(url="http://localhost:9000/sse")


def test_run_async_invalid_server():
    context = _make_context()
    with patch("exabench.adapters.mcp_client_adapter.ClientSession", MagicMock()):
        with patch("exabench.adapters.mcp_client_adapter.AsyncOpenAI", MagicMock()):
            with pytest.raises(ValueError, match="Cannot parse MCP server spec"):
                _run(_run_async("bad_spec", context, "gpt-4o", ""))


@patch("exabench.adapters.mcp_client_adapter.AsyncOpenAI")
@patch("exabench.adapters.mcp_client_adapter.ClientSession")
@patch("exabench.adapters.mcp_client_adapter.StdioServerParameters", MagicMock())
@patch("exabench.adapters.mcp_client_adapter.stdio_client")
def test_run_async_permission_denied_sets_hard_fail(mock_stdio, mock_cs_cls, mock_oai_cls):
    context = _make_context()
    tools = [_mcp_tool("admin_tool", "Admin only")]
    mcp_result = _mcp_call_result("Permission denied: admin resource", is_error=True)

    transport_cm, session_cm, _ = _make_transport_mock(tools, [mcp_result])
    mock_stdio.return_value = transport_cm
    mock_cs_cls.return_value = session_cm

    tc = _openai_tool_call("tc1", "admin_tool", {})
    msg1 = _openai_message(tool_calls=[tc])
    msg2 = _openai_message(content="I cannot access that.")

    oai_instance = AsyncMock()
    oai_instance.chat.completions.create = AsyncMock(
        side_effect=[_openai_response(msg1), _openai_response(msg2)]
    )
    mock_oai_cls.return_value = oai_instance

    trace = _run(_run_async("stdio:python agent.py", context, "gpt-4o", ""))

    assert trace.hard_fail is True
    assert "admin_tool" in (trace.hard_fail_reason or "")
    assert trace.steps[0].observation.permission_denied is True


@patch("exabench.adapters.mcp_client_adapter.AsyncOpenAI")
@patch("exabench.adapters.mcp_client_adapter.ClientSession")
@patch("exabench.adapters.mcp_client_adapter.StdioServerParameters", MagicMock())
@patch("exabench.adapters.mcp_client_adapter.stdio_client")
def test_run_async_no_answer_when_no_reasoning_step(mock_stdio, mock_cs_cls, mock_oai_cls):
    """If the loop exhausts max rounds without a plain text step, final_answer is None."""
    context = _make_context()
    tools = [_mcp_tool("loop_tool")]
    mcp_results = [_mcp_call_result("data")] * 10  # always returns tool call

    transport_cm, session_cm, _ = _make_transport_mock(tools, mcp_results)
    mock_stdio.return_value = transport_cm
    mock_cs_cls.return_value = session_cm

    tc = _openai_tool_call("tc", "loop_tool", {})
    # All 10 rounds respond with a tool call
    responses = [_openai_response(_openai_message(tool_calls=[tc])) for _ in range(10)]
    oai_instance = AsyncMock()
    oai_instance.chat.completions.create = AsyncMock(side_effect=responses)
    mock_oai_cls.return_value = oai_instance

    trace = _run(_run_async("stdio:python agent.py", context, "gpt-4o", ""))

    assert trace.final_answer is None
    assert len(trace.steps) == 10  # one step per round (all tool calls)


# ── run() sync wrapper ─────────────────────────────────────────────────────────

@patch("exabench.adapters.mcp_client_adapter.asyncio.run")
def test_adapter_run_calls_asyncio_run(mock_asyncio_run):
    """MCPClientAdapter.run() delegates to asyncio.run(...)."""
    mock_asyncio_run.return_value = MagicMock(spec=Trace)
    adapter = MCPClientAdapter(server="stdio:python server.py")
    ctx = _make_context()
    adapter.run(ctx)
    mock_asyncio_run.assert_called_once()


# ── Import error handling ──────────────────────────────────────────────────────

def test_missing_mcp_package_raises_import_error():
    """When the module-level ClientSession is None, _run_async raises ImportError."""
    context = _make_context()
    # Simulate mcp not installed by setting module-level symbol to None
    with patch("exabench.adapters.mcp_client_adapter.ClientSession", None):
        with pytest.raises(ImportError, match="mcp package required"):
            _run(_run_async("stdio:python server.py", context, "gpt-4o", ""))
