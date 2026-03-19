"""Anthropic adapter — uses Claude's native tool_use blocks to drive ExaBench mock tools.

Reads credentials from environment / .env:
    ANTHROPIC_API_KEY   — required for Anthropic API

Model selection:
    Pass model name directly, e.g. ``AnthropicAdapter(model="claude-sonnet-4-6")``.
    Default: ``claude-sonnet-4-6``.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from exabench.adapters.base import BaseAdapter
from exabench.runners.context import ExecutionContext
from exabench.schemas.trace import Observation, ToolCall, Trace, TraceStep
from exabench.utils.ids import make_trace_id
from exabench.utils.logging import get_logger

logger = get_logger(__name__)

_MAX_ROUNDS = 10
_MAX_TOKENS = 4096

# Anthropic tool schema format (input_schema instead of parameters)
_TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "slurm__query_jobs",
        "description": "Query SLURM scheduler for jobs. Respects role-based access (scientific_user sees own jobs only).",
        "input_schema": {
            "type": "object",
            "properties": {
                "user":  {"type": "string", "description": "Filter by username (optional)"},
                "state": {"type": "string", "description": "Filter by job state: RUNNING, PENDING, FAILED, etc. (optional)"},
            },
        },
    },
    {
        "name": "slurm__job_details",
        "description": "Get full details for a specific job ID including OOM evidence, stderr, and sacct record.",
        "input_schema": {
            "type": "object",
            "properties": {
                "job_id": {"type": "string", "description": "The SLURM job ID"},
            },
            "required": ["job_id"],
        },
    },
    {
        "name": "slurm__list_partitions",
        "description": "List available SLURM partitions and their current utilisation.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "docs__retrieve",
        "description": "Retrieve relevant documentation snippets by keyword query.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query":       {"type": "string", "description": "Search keywords"},
                "max_results": {"type": "integer", "description": "Max docs to return (default 3)"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "rbac__check",
        "description": "Check whether the current role has permission for a resource/action.",
        "input_schema": {
            "type": "object",
            "properties": {
                "resource": {"type": "string", "description": "Resource name, e.g. 'slurm.jobs'"},
                "action":   {"type": "string", "description": "Action, e.g. 'read', 'cancel'"},
            },
            "required": ["resource", "action"],
        },
    },
    {
        "name": "telemetry__query_memory_events",
        "description": "Query memory event timeseries data from the environment snapshot.",
        "input_schema": {
            "type": "object",
            "properties": {
                "job_id": {"type": "string", "description": "Filter events for a specific job ID (optional)"},
            },
        },
    },
    {
        "name": "facility__query_node_power",
        "description": "Query per-node power consumption readings (kW) from the environment snapshot.",
        "input_schema": {
            "type": "object",
            "properties": {
                "node": {"type": "string", "description": "Filter by node name, e.g. 'node03' (optional)"},
            },
        },
    },
    {
        "name": "facility__query_cluster_energy",
        "description": "Query cluster-level and rack-level energy time series (kWh) from the environment snapshot.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "facility__query_rack_telemetry",
        "description": "Query rack telemetry: ambient temperature, hotspot temperature, humidity, and cooling status.",
        "input_schema": {
            "type": "object",
            "properties": {
                "rack_id": {"type": "string", "description": "Filter by rack ID, e.g. 'rack-b' (optional)"},
            },
        },
    },
    {
        "name": "facility__list_inventory",
        "description": "List facility inventory: nodes with their rack assignments (kind='nodes') or rack layout (kind='racks').",
        "input_schema": {
            "type": "object",
            "properties": {
                "kind": {
                    "type": "string",
                    "enum": ["nodes", "racks"],
                    "description": "Type of inventory to list: 'nodes' (default) or 'racks'",
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
    return [s for s in _TOOL_SCHEMAS if s["name"].split("__")[0] in allowed]


def _build_client() -> Any:
    """Return an Anthropic client. Reads ANTHROPIC_API_KEY from env / .env."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    try:
        import anthropic
    except ImportError:
        raise ImportError("anthropic package required: pip install exabench[anthropic]")

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise EnvironmentError(
            "Anthropic API requires ANTHROPIC_API_KEY in environment or .env file."
        )
    return anthropic.Anthropic(api_key=api_key)


class AnthropicAdapter(BaseAdapter):
    """Agent adapter using Anthropic Claude with native tool_use blocks."""

    name = "anthropic"

    def __init__(
        self,
        model: str = "claude-sonnet-4-6",
        system_prompt: str | None = None,
    ) -> None:
        self._model = model
        self._system_prompt = system_prompt or (
            "You are an HPC operations assistant. Use the available tools to investigate "
            "the user's question by querying the scheduler, telemetry, and documentation. "
            "Be precise, cite specific evidence, and respect your role's access limits."
        )

    def run(self, context: ExecutionContext) -> Trace:
        client = _build_client()
        task = context.task
        tools_registry = context.tools
        allowed = tools_registry.available_tool_names
        tool_schemas = _filter_schemas(allowed)

        # Anthropic: system is a top-level param, not a message
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": task.query_text},
        ]

        steps: list[TraceStep] = []
        start = datetime.now(tz=timezone.utc)
        prompt_tokens = 0
        completion_tokens = 0
        hard_fail = False
        hard_fail_reason: str | None = None

        logger.info("anthropic run start task=%s model=%s", task.task_id, self._model)

        for round_idx in range(_MAX_ROUNDS):
            logger.debug("round %d: sending %d messages", round_idx + 1, len(messages))

            response = client.messages.create(
                model=self._model,
                max_tokens=_MAX_TOKENS,
                system=self._system_prompt,
                messages=messages,
                tools=tool_schemas if tool_schemas else [],
            )

            if response.usage:
                prompt_tokens += response.usage.input_tokens
                completion_tokens += response.usage.output_tokens

            # Separate text blocks from tool_use blocks
            text_blocks = [b for b in response.content if b.type == "text"]
            tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

            if not tool_use_blocks:
                # Final answer — collect all text content
                final_text = " ".join(b.text for b in text_blocks if b.text)
                logger.debug("round %d: final answer (no tool_use blocks)", round_idx + 1)
                steps.append(TraceStep(
                    step_id=len(steps) + 1,
                    reasoning=final_text or None,
                    timestamp=datetime.now(tz=timezone.utc),
                ))
                break

            # Append assistant message with all content blocks
            messages.append({"role": "assistant", "content": response.content})

            # Execute each tool call and collect tool_result blocks
            tool_results: list[dict[str, Any]] = []
            for block in tool_use_blocks:
                tool_name, method = _parse_tool_name(block.name)
                kwargs = block.input or {}
                logger.debug("tool call: %s.%s(%s)", tool_name, method, kwargs)

                result = tools_registry.call(tool_name, method, **kwargs)

                obs = Observation(
                    content=result.data,
                    error=result.error,
                    permission_denied=result.permission_denied,
                )
                if result.permission_denied:
                    hard_fail = True
                    hard_fail_reason = f"Permission denied calling {block.name}"
                    logger.warning("permission denied: %s", block.name)

                steps.append(TraceStep(
                    step_id=len(steps) + 1,
                    reasoning=None,
                    tool_call=ToolCall(tool_name=block.name, arguments=kwargs),
                    observation=obs,
                    timestamp=datetime.now(tz=timezone.utc),
                ))

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result.data) if result.success else (result.error or "error"),
                })

            # Append all tool results as a single user message
            messages.append({"role": "user", "content": tool_results})

        final_answer = next(
            (s.reasoning for s in reversed(steps) if s.reasoning and not s.tool_call),
            None,
        )
        total_tokens = prompt_tokens + completion_tokens

        return Trace(
            trace_id=make_trace_id(),
            run_id=context.run_id,
            task_id=task.task_id,
            role=task.role,
            environment_id=task.environment_id,
            adapter_name=self.name,
            model_name=self._model,
            steps=steps,
            final_answer=final_answer,
            start_time=start,
            end_time=datetime.now(tz=timezone.utc),
            total_tokens=total_tokens or None,
            prompt_tokens=prompt_tokens or None,
            completion_tokens=completion_tokens or None,
            hard_fail=hard_fail,
            hard_fail_reason=hard_fail_reason,
        )
