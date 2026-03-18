"""Unit tests for ToolUseScorer."""

from __future__ import annotations

from exabench.schemas.task import TaskSpec
from exabench.schemas.trace import Observation, ToolCall, Trace, TraceStep
from exabench.scorers.tool_use_scorer import ToolUseScorer


def _task(allowed_tools: list[str] | None = None,
          gold_refs: list[str] | None = None) -> TaskSpec:
    return TaskSpec(
        task_id="TST_001", title="T", query_text="Q",
        role="scientific_user", qcat="JOB", difficulty="easy",
        environment_id="env_01", expected_answer_type="diagnosis",
        allowed_tools=allowed_tools,
        gold_evidence_refs=gold_refs or [],
    )


def _trace_with_calls(tool_names: list[str]) -> Trace:
    steps = [
        TraceStep(
            step_id=i + 1,
            tool_call=ToolCall(tool_name=name, arguments={}),
            observation=Observation(content="ok"),
        )
        for i, name in enumerate(tool_names)
    ]
    return Trace(
        trace_id="t1", run_id="r1", task_id="TST_001",
        role="scientific_user", environment_id="env_01",
        adapter_name="openai", steps=steps,
    )


def _empty_trace() -> Trace:
    return Trace(
        trace_id="t1", run_id="r1", task_id="TST_001",
        role="scientific_user", environment_id="env_01",
        adapter_name="direct_qa",
    )


scorer = ToolUseScorer()


def test_no_tools_no_required_scores_one():
    result = scorer.score(_task(allowed_tools=None), _empty_trace())
    assert result.score == 1.0


def test_no_tools_but_task_requires_them_scores_zero():
    result = scorer.score(_task(allowed_tools=["slurm"]), _empty_trace())
    assert result.score == 0.0


def test_correct_tool_for_gold_ref():
    # slurm/ refs map to slurm tool
    task = _task(allowed_tools=["slurm"], gold_refs=["slurm/job_details.json"])
    result = scorer.score(task, _trace_with_calls(["slurm__query_jobs"]))
    assert result.score > 0.8  # good coverage + precision + no-redundancy


def test_disallowed_tool_penalised():
    task = _task(allowed_tools=["slurm"], gold_refs=["slurm/job_details.json"])
    result = scorer.score(task, _trace_with_calls(["slurm__query_jobs", "facility__query_node_power"]))
    # facility is not in allowed_tools → precision penalty
    assert result.score < 1.0


def test_facility_ref_maps_to_facility_tool():
    task = _task(allowed_tools=["facility"], gold_refs=["power/node_power_001.csv"])
    result = scorer.score(task, _trace_with_calls(["facility__query_node_power"]))
    assert result.score > 0.8


def test_redundant_calls_penalised():
    # Same exact call (tool, method, args) more than 2 times
    task = _task(allowed_tools=["slurm"], gold_refs=["slurm/slurm_state.json"])
    trace = _trace_with_calls(["slurm__query_jobs"] * 4)
    result = scorer.score(task, trace)
    # no_redundancy sub-score should be < 1.0
    assert result.score < 1.0


def test_hard_fail_scores_zero():
    task = _task(allowed_tools=["slurm"])
    trace = Trace(
        trace_id="t1", run_id="r1", task_id="TST_001",
        role="scientific_user", environment_id="env_01",
        adapter_name="openai", hard_fail=True,
    )
    result = scorer.score(task, trace)
    assert result.score == 0.0
    assert result.hard_fail is True
