"""OpenAI adapter — uses function calling to drive ExaBench mock tools."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from exabench.adapters.base import BaseAdapter
from exabench.runners.context import ExecutionContext
from exabench.schemas.trace import Observation, ToolCall, Trace, TraceStep
from exabench.utils.ids import make_trace_id

# Max tool-call rounds before stopping
_MAX_ROUNDS = 10

# Mapping from ExaBench tool.method → OpenAI function definition
_TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "slurm__query_jobs",
            "description": "Query SLURM scheduler for jobs. Respects role-based access (scientific_user sees own jobs only).",
            "parameters": {
                "type": "object",
                "properties": {
                    "user":  {"type": "string", "description": "Filter by username (optional)"},
                    "state": {"type": "string", "description": "Filter by job state: RUNNING, PENDING, FAILED, etc. (optional)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "slurm__job_details",
            "description": "Get full details for a specific job ID including OOM evidence, stderr, and sacct record.",
            "parameters": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "The SLURM job ID"},
                },
                "required": ["job_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "slurm__list_partitions",
            "description": "List available SLURM partitions and their current utilisation.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "docs__retrieve",
            "description": "Retrieve relevant documentation snippets by keyword query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query":       {"type": "string", "description": "Search keywords"},
                    "max_results": {"type": "integer", "description": "Max docs to return (default 3)"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "rbac__check",
            "description": "Check whether the current role has permission for a resource/action.",
            "parameters": {
                "type": "object",
                "properties": {
                    "resource": {"type": "string", "description": "Resource name, e.g. 'slurm.jobs'"},
                    "action":   {"type": "string", "description": "Action, e.g. 'read', 'cancel'"},
                },
                "required": ["resource", "action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "telemetry__query_memory_events",
            "description": "Query memory event timeseries data from the environment snapshot.",
            "parameters": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "Filter events for a specific job ID (optional)"},
                },
            },
        },
    },
]


def _parse_tool_name(name: str) -> tuple[str, str]:
    """Split 'slurm__query_jobs' → ('slurm', 'query_jobs')."""
    tool, _, method = name.partition("__")
    return tool, method


def _filter_schemas(allowed: list[str]) -> list[dict[str, Any]]:
    return [s for s in _TOOL_SCHEMAS if s["function"]["name"].split("__")[0] in allowed]


class OpenAIAdapter(BaseAdapter):
    """Agent adapter using OpenAI chat completions with function calling."""

    name = "openai"

    def __init__(self, model: str = "gpt-4o-mini", system_prompt: str | None = None) -> None:
        self._model = model
        self._system_prompt = system_prompt or (
            "You are an HPC operations assistant. Use the available tools to investigate "
            "the user's question by querying the scheduler, telemetry, and documentation. "
            "Be precise, cite specific evidence, and respect your role's access limits."
        )

    def run(self, context: ExecutionContext) -> Trace:
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai package required: pip install exabench[openai]")

        client = OpenAI()
        task = context.task
        tools_registry = context.tools
        allowed = tools_registry.available_tool_names

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self._system_prompt},
            {"role": "user",   "content": task.query_text},
        ]
        tool_schemas = _filter_schemas(allowed)

        steps: list[TraceStep] = []
        start = datetime.now(tz=timezone.utc)
        total_tokens = 0
        hard_fail = False
        hard_fail_reason: str | None = None

        for round_idx in range(_MAX_ROUNDS):
            response = client.chat.completions.create(
                model=self._model,
                messages=messages,
                tools=tool_schemas if tool_schemas else None,
                tool_choice="auto" if tool_schemas else None,
            )
            msg = response.choices[0].message
            total_tokens += response.usage.total_tokens if response.usage else 0

            if not msg.tool_calls:
                # Final answer
                steps.append(TraceStep(
                    step_id=len(steps) + 1,
                    reasoning=msg.content,
                    timestamp=datetime.now(tz=timezone.utc),
                ))
                break

            # Process each tool call
            messages.append(msg.model_dump(exclude_unset=True))
            for tc in msg.tool_calls:
                tool_name, method = _parse_tool_name(tc.function.name)
                kwargs = json.loads(tc.function.arguments or "{}")

                result = tools_registry.call(tool_name, method, **kwargs)

                obs = Observation(
                    content=result.data,
                    error=result.error,
                    permission_denied=result.permission_denied,
                )
                if result.permission_denied:
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
                    "content": json.dumps(result.data) if result.success else (result.error or "error"),
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
            adapter_name=self.name,
            steps=steps,
            final_answer=final_answer,
            start_time=start,
            end_time=datetime.now(tz=timezone.utc),
            total_tokens=total_tokens,
            hard_fail=hard_fail,
            hard_fail_reason=hard_fail_reason,
        )
