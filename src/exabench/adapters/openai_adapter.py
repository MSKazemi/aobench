"""OpenAI / Azure OpenAI adapter — uses function calling to drive ExaBench mock tools.

Client selection (checked in order):
  1. Explicit ``provider`` argument passed to ``__init__``.
  2. ``LLM_PROVIDER`` env var (``"azure"`` or ``"openai"``).
  3. Falls back to Azure if ``AZURE_OPENAI_ENDPOINT`` is set, else plain OpenAI.
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
    {
        "type": "function",
        "function": {
            "name": "facility__query_node_power",
            "description": "Query per-node power consumption readings (kW) from the environment snapshot.",
            "parameters": {
                "type": "object",
                "properties": {
                    "node": {"type": "string", "description": "Filter by node name, e.g. 'node03' (optional)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "facility__query_cluster_energy",
            "description": "Query cluster-level and rack-level energy time series (kWh) from the environment snapshot.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "facility__query_rack_telemetry",
            "description": "Query rack telemetry: ambient temperature, hotspot temperature, humidity, and cooling status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "rack_id": {"type": "string", "description": "Filter by rack ID, e.g. 'rack-b' (optional)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "facility__list_inventory",
            "description": "List facility inventory: nodes with their rack assignments (kind='nodes') or rack layout (kind='racks').",
            "parameters": {
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
    },
]


def _parse_tool_name(name: str) -> tuple[str, str]:
    """Split 'slurm__query_jobs' → ('slurm', 'query_jobs')."""
    tool, _, method = name.partition("__")
    return tool, method


def _filter_schemas(allowed: list[str]) -> list[dict[str, Any]]:
    return [s for s in _TOOL_SCHEMAS if s["function"]["name"].split("__")[0] in allowed]


def _build_client(provider: str | None, model: str) -> tuple[Any, str]:
    """Return (client, deployment_name).

    For Azure the 'model' arg is treated as the deployment name.
    Reads .env automatically if python-dotenv is available.
    """
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass  # dotenv optional; env vars may already be set

    try:
        from openai import AzureOpenAI, OpenAI
    except ImportError:
        raise ImportError("openai package required: pip install exabench[openai]")

    resolved = provider or os.environ.get("LLM_PROVIDER", "").lower()
    if not resolved:
        resolved = "azure" if os.environ.get("AZURE_OPENAI_ENDPOINT") else "openai"

    if resolved == "azure":
        endpoint   = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
        api_key    = os.environ.get("AZURE_OPENAI_API_KEY", "")
        api_ver    = os.environ.get("AZURE_OPENAI_API_VERSION", os.environ.get("AZURE_API_VERSION", "2024-08-01-preview"))
        deployment = model or os.environ.get("AZURE_OPENAI_DEPLOYMENT", "").strip()
        if not endpoint or not api_key:
            raise EnvironmentError(
                "Azure OpenAI requires AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY "
                "in environment or .env file."
            )
        if not deployment:
            raise EnvironmentError(
                "Azure OpenAI requires a deployment name. "
                "Set AZURE_OPENAI_DEPLOYMENT=<your-deployment-name> in .env\n"
                "Find it in Azure AI Studio → Deployments."
            )
        client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=api_ver,
        )
        return client, deployment  # Azure uses deployment name, not model name

    # Plain OpenAI
    return OpenAI(), model


class OpenAIAdapter(BaseAdapter):
    """Agent adapter using OpenAI / Azure OpenAI chat completions with function calling."""

    name = "openai"

    def __init__(
        self,
        model: str = "gpt-4o",
        provider: str | None = None,
        system_prompt: str | None = None,
    ) -> None:
        self._model = model
        self._provider = provider  # "azure" | "openai" | None (auto-detect)
        self._system_prompt = system_prompt or (
            "You are an HPC operations assistant. Use the available tools to investigate "
            "the user's question by querying the scheduler, telemetry, and documentation. "
            "Be precise, cite specific evidence, and respect your role's access limits."
        )

    def run(self, context: ExecutionContext) -> Trace:
        client, deployment = _build_client(self._provider, self._model)
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
        prompt_tokens = 0
        completion_tokens = 0
        hard_fail = False
        hard_fail_reason: str | None = None

        logger.info("openai run start task=%s model=%s", task.task_id, deployment)
        for round_idx in range(_MAX_ROUNDS):
            logger.debug("round %d: sending %d messages", round_idx + 1, len(messages))
            response = client.chat.completions.create(
                model=deployment,
                messages=messages,
                tools=tool_schemas if tool_schemas else None,
                tool_choice="auto" if tool_schemas else None,
            )
            msg = response.choices[0].message
            if response.usage:
                total_tokens += response.usage.total_tokens
                prompt_tokens += response.usage.prompt_tokens
                completion_tokens += response.usage.completion_tokens

            if not msg.tool_calls:
                # Final answer
                logger.debug("round %d: final answer (no tool calls)", round_idx + 1)
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
                logger.debug("tool call: %s.%s(%s)", tool_name, method, kwargs)

                result = tools_registry.call(tool_name, method, **kwargs)

                obs = Observation(
                    content=result.data,
                    error=result.error,
                    permission_denied=result.permission_denied,
                )
                if result.permission_denied:
                    hard_fail = True
                    hard_fail_reason = f"Permission denied calling {tc.function.name}"
                    logger.warning("permission denied: %s", tc.function.name)

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
            model_name=deployment,
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
