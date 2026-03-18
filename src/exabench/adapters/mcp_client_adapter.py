"""MCP Client Adapter — benchmark agents that expose an MCP server.

ExaBench connects as an MCP *client* to an external agent (the MCP server),
discovers its tools, and drives an OpenAI agentic loop using those tools.
The full tool-call trace is captured and returned for scoring — no mock tools
or cluster access required on the ExaBench side.

Connection string formats (passed after ``mcp:`` in the adapter name):

  ``stdio:python mcp_server.py [ARGS...]``
      Spawn a local subprocess via stdio transport.

  ``sse:http://HOST:PORT/sse``
      Connect to a remote server via HTTP SSE transport.

  ``http://HOST:PORT/sse``
      Shorthand SSE — any string starting with ``http://`` or ``https://``.

CLI examples::

    exabench run task -t JOB_USR_001 -e env_01 --adapter "mcp:stdio:python my_agent.py"
    exabench run task -t JOB_USR_001 -e env_01 --adapter "mcp:sse:http://localhost:8000/sse"

Install requirements::

    pip install "exabench[mcp]"
    # installs: mcp>=1.0, openai>=1.0
"""

from __future__ import annotations

import asyncio
import json
import shlex
from datetime import datetime, timezone
from typing import Any

from exabench.adapters.base import BaseAdapter
from exabench.runners.context import ExecutionContext
from exabench.schemas.trace import Observation, ToolCall, Trace, TraceStep
from exabench.utils.ids import make_trace_id

# Optional dependencies — imported at module level so tests can patch them.
# If not installed the ImportError is raised lazily inside _run_async.
try:
    from mcp import ClientSession  # type: ignore[import]
    from mcp.client.stdio import StdioServerParameters, stdio_client  # type: ignore[import]
    from mcp.client.sse import sse_client  # type: ignore[import]
except ImportError:
    ClientSession = None  # type: ignore[assignment,misc]
    StdioServerParameters = None  # type: ignore[assignment,misc]
    stdio_client = None  # type: ignore[assignment]
    sse_client = None  # type: ignore[assignment]

try:
    from openai import AsyncOpenAI  # type: ignore[import]
except ImportError:
    AsyncOpenAI = None  # type: ignore[assignment,misc]

_MAX_ROUNDS = 10

_DEFAULT_SYSTEM_PROMPT = (
    "You are an HPC operations assistant. Use the available tools to investigate "
    "the user's question by querying the scheduler, telemetry, and documentation. "
    "Be precise, cite specific evidence, and respect your role's access limits."
)


def _mcp_tool_to_openai_schema(tool: Any) -> dict[str, Any]:
    """Convert an MCP Tool object to an OpenAI function-calling schema dict."""
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": tool.inputSchema or {"type": "object", "properties": {}},
        },
    }


def _extract_text(content_items: list[Any]) -> str:
    """Flatten MCP content items (TextContent / ImageContent / etc.) to a string."""
    parts: list[str] = []
    for item in content_items:
        if hasattr(item, "text"):
            parts.append(item.text)
        else:
            parts.append(str(item))
    return "\n".join(parts)


async def _run_async(
    server: str,
    context: ExecutionContext,
    model: str,
    system_prompt: str,
) -> Trace:
    """Async implementation of the MCP agentic loop."""
    if ClientSession is None:
        raise ImportError(
            "mcp package required: pip install 'exabench[mcp]'  "
            "(or: pip install 'mcp>=1.0')"
        )
    if AsyncOpenAI is None:
        raise ImportError(
            "openai package required: pip install 'exabench[mcp]'  "
            "(or: pip install openai)"
        )

    # ── Resolve transport ────────────────────────────────────────────────────
    if server.startswith("stdio:"):
        cmd_str = server[len("stdio:"):]
        parts = shlex.split(cmd_str)
        transport_cm = stdio_client(StdioServerParameters(command=parts[0], args=parts[1:]))
    elif server.startswith("sse:"):
        transport_cm = sse_client(url=server[len("sse:"):])
    elif server.startswith("http://") or server.startswith("https://"):
        transport_cm = sse_client(url=server)
    else:
        raise ValueError(
            f"Cannot parse MCP server spec {server!r}. "
            "Use 'stdio:COMMAND [ARGS]' or 'sse:http://HOST/sse'."
        )

    task = context.task
    start = datetime.now(tz=timezone.utc)
    steps: list[TraceStep] = []
    total_tokens = 0
    hard_fail = False
    hard_fail_reason: str | None = None

    async with transport_cm as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            # ── Discover tools from the MCP server ──────────────────────────
            tools_result = await session.list_tools()
            tool_schemas = [_mcp_tool_to_openai_schema(t) for t in tools_result.tools]

            # ── Agentic loop via OpenAI function-calling ─────────────────────
            oai = AsyncOpenAI()
            messages: list[dict[str, Any]] = [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": task.query_text},
            ]

            for _ in range(_MAX_ROUNDS):
                response = await oai.chat.completions.create(
                    model=model,
                    messages=messages,
                    tools=tool_schemas if tool_schemas else None,
                    tool_choice="auto" if tool_schemas else None,
                )
                msg = response.choices[0].message
                total_tokens += response.usage.total_tokens if response.usage else 0

                if not msg.tool_calls:
                    steps.append(TraceStep(
                        step_id=len(steps) + 1,
                        reasoning=msg.content,
                        timestamp=datetime.now(tz=timezone.utc),
                    ))
                    break

                messages.append(msg.model_dump(exclude_unset=True))

                for tc in msg.tool_calls:
                    kwargs = json.loads(tc.function.arguments or "{}")

                    mcp_result = await session.call_tool(tc.function.name, kwargs)

                    content_text = _extract_text(mcp_result.content) if mcp_result.content else ""
                    is_error = bool(getattr(mcp_result, "isError", False))

                    obs = Observation(
                        content=content_text,
                        error=content_text if is_error else None,
                        permission_denied=is_error and "permission" in content_text.lower(),
                    )

                    if obs.permission_denied:
                        hard_fail = True
                        hard_fail_reason = f"Permission denied calling {tc.function.name}"

                    steps.append(TraceStep(
                        step_id=len(steps) + 1,
                        reasoning=None,
                        tool_call=ToolCall(tool_name=tc.function.name, arguments=kwargs),
                        observation=obs,
                        timestamp=datetime.now(tz=timezone.utc),
                    ))

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": content_text if not is_error else f"Error: {content_text}",
                    })

    final_answer = next(
        (s.reasoning for s in reversed(steps) if s.reasoning and not s.tool_call),
        None,
    )

    return Trace(
        trace_id=make_trace_id(),
        run_id=context.run_id,
        task_id=task.task_id,
        role=task.role,
        environment_id=task.environment_id,
        adapter_name=MCPClientAdapter.name,
        steps=steps,
        final_answer=final_answer,
        start_time=start,
        end_time=datetime.now(tz=timezone.utc),
        total_tokens=total_tokens,
        hard_fail=hard_fail,
        hard_fail_reason=hard_fail_reason,
    )


class MCPClientAdapter(BaseAdapter):
    """Adapter that connects to an external MCP server to run benchmark tasks.

    The server represents an HPC agent with real or mock tools.  ExaBench
    drives an OpenAI agentic loop using the server's tools, capturing the
    full tool-call trace for multi-dimensional scoring.

    Args:
        server: Connection string — ``"stdio:python agent.py"`` or
                ``"sse:http://localhost:8000/sse"``.
        model:  OpenAI model used as the LLM brain (default ``"gpt-4o"``).
        system_prompt: Override the default HPC assistant system prompt.
    """

    name = "mcp"

    def __init__(
        self,
        server: str,
        model: str = "gpt-4o",
        system_prompt: str | None = None,
    ) -> None:
        if not server:
            raise ValueError(
                "MCPClientAdapter requires a server connection string. "
                "Use 'stdio:COMMAND' or 'sse:http://HOST/sse'."
            )
        self._server = server
        self._model = model
        self._system_prompt = system_prompt or _DEFAULT_SYSTEM_PROMPT

    def run(self, context: ExecutionContext) -> Trace:  # noqa: D102
        return asyncio.run(
            _run_async(self._server, context, self._model, self._system_prompt)
        )
