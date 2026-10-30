"""Unit tests for OpenAIAdapter tool-call handling."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from aobench.adapters import openai_adapter
from aobench.adapters.openai_adapter import OpenAIAdapter
from aobench.runners.context import ExecutionContext
from aobench.schemas.environment import EnvironmentBundle, EnvironmentMetadata
from aobench.schemas.task import EvalCriteria, TaskSpec
from aobench.tools.base import ToolResult
from aobench.tools.registry import ToolRegistry


def _make_context(tool: MagicMock) -> ExecutionContext:
    task = TaskSpec(
        task_id="TST_001",
        title="Test task",
        query_text="Check a job",
        role="scientific_user",
        qcat="JOB",
        difficulty="easy",
        environment_id="env_01",
        expected_answer_type="diagnosis",
        eval_criteria=EvalCriteria(evaluation_mode="semantic_match", gold_answer="OOM"),
    )
    metadata = EnvironmentMetadata(
        environment_id="env_01",
        snapshot_name="test",
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
    env = EnvironmentBundle(metadata=metadata, root_path="/tmp/env_01")
    return ExecutionContext(
        task=task,
        env=env,
        tools=ToolRegistry([tool], allowed_tool_names=["slurm"]),
        run_id="run_test",
    )


def _tool_call(arguments: str) -> MagicMock:
    tool_call = MagicMock()
    tool_call.id = "call_1"
    tool_call.function.name = "slurm__query_jobs"
    tool_call.function.arguments = arguments
    return tool_call


def _response(message: MagicMock) -> SimpleNamespace:
    usage = SimpleNamespace(total_tokens=10, prompt_tokens=7, completion_tokens=3)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=usage)


def _message(content: str | None = None, tool_calls: list | None = None) -> MagicMock:
    message = MagicMock()
    message.content = content
    message.tool_calls = tool_calls or []
    message.model_dump.return_value = {
        "role": "assistant",
        "content": content,
        "tool_calls": [
            {
                "id": tool_call.id,
                "type": "function",
                "function": {
                    "name": tool_call.function.name,
                    "arguments": tool_call.function.arguments,
                },
            }
            for tool_call in message.tool_calls
        ],
    }
    return message


@pytest.mark.parametrize("arguments", ["{bad json", "[]", "null"])
def test_malformed_tool_arguments_are_returned_as_tool_errors(
    monkeypatch: pytest.MonkeyPatch,
    arguments: str,
) -> None:
    tool = MagicMock()
    tool.name = "slurm"
    tool.call.return_value = ToolResult(tool_name="slurm", success=True, data={"jobs": []})
    context = _make_context(tool)

    client = MagicMock()
    client.chat.completions.create.side_effect = [
        _response(_message(tool_calls=[_tool_call(arguments)])),
        _response(_message(content="I will retry with valid arguments.")),
    ]
    monkeypatch.setattr(
        openai_adapter, "_build_client", lambda provider, model: (client, "test-model")
    )

    trace = OpenAIAdapter(model="test-model", provider="openai").run(context)

    assert len(trace.steps) == 2
    failed_call = trace.steps[0]
    assert failed_call.tool_call is not None
    assert failed_call.tool_call.arguments == {}
    assert failed_call.observation is not None
    assert failed_call.observation.error is not None
    assert "Invalid arguments" in failed_call.observation.error
    assert failed_call.observation.permission_denied is False
    assert trace.hard_fail is False
    assert trace.final_answer == "I will retry with valid arguments."
    tool.call.assert_not_called()

    followup_messages = client.chat.completions.create.call_args_list[1].kwargs["messages"]
    assert followup_messages[-1]["role"] == "tool"
    assert "Invalid arguments" in followup_messages[-1]["content"]
