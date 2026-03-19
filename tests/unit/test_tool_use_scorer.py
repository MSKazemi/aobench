"""Unit tests for ToolUseScorer — legacy mode and decomposed mode."""

from __future__ import annotations

from exabench.schemas.task import EvalCriteria, ExpectedToolCall, TaskSpec
from exabench.schemas.trace import Observation, ToolCall, Trace, TraceStep
from exabench.scorers.tool_use_scorer import ToolUseScorer, _args_match, _lcs_length


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _task(
    allowed_tools: list[str] | None = None,
    gold_refs: list[str] | None = None,
    expected_seq: list[ExpectedToolCall] | None = None,
) -> TaskSpec:
    eval_criteria = None
    if expected_seq is not None:
        eval_criteria = EvalCriteria(expected_tool_sequence=expected_seq)
    return TaskSpec(
        task_id="TST_001", title="T", query_text="Q",
        role="scientific_user", qcat="JOB", difficulty="easy",
        environment_id="env_01", expected_answer_type="diagnosis",
        allowed_tools=allowed_tools,
        gold_evidence_refs=gold_refs or [],
        eval_criteria=eval_criteria,
    )


def _trace_with_calls(calls: list[str | tuple]) -> Trace:
    """Build a trace from a list of tool names (str) or (name, args_dict) tuples."""
    steps = []
    for i, item in enumerate(calls):
        if isinstance(item, tuple):
            name, args = item
        else:
            name, args = item, {}
        steps.append(TraceStep(
            step_id=i + 1,
            tool_call=ToolCall(tool_name=name, arguments=args),
            observation=Observation(content="ok"),
        ))
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


# ---------------------------------------------------------------------------
# Unit helpers
# ---------------------------------------------------------------------------

def test_args_match_empty_required():
    assert _args_match({"method": "job_details"}, {}) == 1.0


def test_args_match_exact_string():
    assert _args_match({"method": "job_details"}, {"method": "job_details"}) == 1.0


def test_args_match_string_case_insensitive():
    assert _args_match({"method": "Job_Details"}, {"method": "job_details"}) == 1.0


def test_args_match_string_mismatch():
    assert _args_match({"method": "list_nodes"}, {"method": "job_details"}) == 0.0


def test_args_match_numeric_within_tolerance():
    assert _args_match({"threshold": 95.0}, {"threshold": 95.0}) == 1.0
    assert _args_match({"threshold": 96.0}, {"threshold": 95.0}) > 0.0  # within 5%


def test_args_match_numeric_outside_tolerance():
    # 200 vs 95 → way outside 5% tolerance
    assert _args_match({"threshold": 200.0}, {"threshold": 95.0}) == 0.0


def test_args_match_missing_key():
    assert _args_match({}, {"method": "job_details"}) == 0.0


def test_args_match_partial():
    result = _args_match(
        {"method": "job_details", "job_id": "999"},
        {"method": "job_details", "job_id": "891234"},
    )
    assert result == 0.5  # method matches, job_id doesn't


def test_lcs_identical():
    assert _lcs_length(["a", "b", "c"], ["a", "b", "c"]) == 3


def test_lcs_empty():
    assert _lcs_length([], ["a"]) == 0
    assert _lcs_length(["a"], []) == 0


def test_lcs_partial():
    # LCS of [a, b, c] and [b, a, c] = [b, c] or [a, c] → length 2
    assert _lcs_length(["a", "b", "c"], ["b", "a", "c"]) == 2


def test_lcs_no_overlap():
    assert _lcs_length(["x", "y"], ["a", "b"]) == 0


# ---------------------------------------------------------------------------
# Legacy mode (no expected_tool_sequence)
# ---------------------------------------------------------------------------

def test_no_tools_no_required_scores_one():
    result = scorer.score(_task(allowed_tools=None), _empty_trace())
    assert result.score == 1.0


def test_no_tools_but_task_requires_them_scores_zero():
    result = scorer.score(_task(allowed_tools=["slurm"]), _empty_trace())
    assert result.score == 0.0


def test_correct_tool_for_gold_ref():
    task = _task(allowed_tools=["slurm"], gold_refs=["slurm/job_details.json"])
    result = scorer.score(task, _trace_with_calls(["slurm__query_jobs"]))
    assert result.score > 0.8
    assert "legacy" in result.notes


def test_disallowed_tool_penalised():
    task = _task(allowed_tools=["slurm"], gold_refs=["slurm/job_details.json"])
    result = scorer.score(task, _trace_with_calls(["slurm__query_jobs", "facility__query_node_power"]))
    assert result.score < 1.0


def test_facility_ref_maps_to_facility_tool():
    task = _task(allowed_tools=["facility"], gold_refs=["power/node_power_001.csv"])
    result = scorer.score(task, _trace_with_calls(["facility__query_node_power"]))
    assert result.score > 0.8


def test_redundant_calls_penalised():
    task = _task(allowed_tools=["slurm"], gold_refs=["slurm/slurm_state.json"])
    trace = _trace_with_calls(["slurm__query_jobs"] * 4)
    result = scorer.score(task, trace)
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


# ---------------------------------------------------------------------------
# Decomposed mode (expected_tool_sequence set)
# ---------------------------------------------------------------------------

def test_decomposed_perfect_match():
    """Agent calls exactly the expected tools in the expected order with correct args."""
    seq = [
        ExpectedToolCall(tool_name="slurm", required_args={"method": "job_details", "job_id": "891234"}),
        ExpectedToolCall(tool_name="docs",  required_args={"method": "search"}),
    ]
    task = _task(allowed_tools=["slurm", "docs"], expected_seq=seq)
    trace = _trace_with_calls([
        ("slurm", {"method": "job_details", "job_id": "891234"}),
        ("docs",  {"method": "search", "query": "OOM"}),
    ])
    result = scorer.score(task, trace)
    assert result.score == 1.0
    assert "decomposed" in result.notes


def test_decomposed_mode_notes_label():
    """Decomposed mode should label its notes 'decomposed:'."""
    seq = [ExpectedToolCall(tool_name="slurm", required_args={})]
    task = _task(allowed_tools=["slurm"], expected_seq=seq)
    trace = _trace_with_calls([("slurm", {"method": "list_jobs"})])
    result = scorer.score(task, trace)
    assert "decomposed" in result.notes


def test_decomposed_selection_partial():
    """Agent misses one expected tool — selection_score should be 0.5."""
    seq = [
        ExpectedToolCall(tool_name="slurm", required_args={}),
        ExpectedToolCall(tool_name="docs",  required_args={}),
    ]
    task = _task(allowed_tools=["slurm", "docs"], expected_seq=seq)
    # Only calls slurm, not docs
    trace = _trace_with_calls([("slurm", {})])
    result = scorer.score(task, trace)
    # selection=0.5, argument=0.5 (slurm ok, docs missing→0), sequence=0.5, forbidden=1.0
    assert result.score < 1.0
    assert result.score > 0.0


def test_decomposed_argument_mismatch():
    """Agent calls right tool but wrong job_id — argument_score should be < 1."""
    seq = [ExpectedToolCall(tool_name="slurm",
                            required_args={"method": "job_details", "job_id": "891234"})]
    task = _task(allowed_tools=["slurm"], expected_seq=seq)
    trace = _trace_with_calls([("slurm", {"method": "job_details", "job_id": "999999"})])
    result = scorer.score(task, trace)
    # argument_score = 0.5 (method ok, job_id wrong)
    assert result.score < 1.0


def test_decomposed_sequence_wrong_order():
    """Agent calls right tools but in wrong order — sequence_score should be < 1."""
    seq = [
        ExpectedToolCall(tool_name="slurm",    required_args={}),
        ExpectedToolCall(tool_name="telemetry", required_args={}),
        ExpectedToolCall(tool_name="docs",      required_args={}),
    ]
    task = _task(allowed_tools=["slurm", "telemetry", "docs"], expected_seq=seq)
    # Reversed order
    trace = _trace_with_calls([("docs", {}), ("telemetry", {}), ("slurm", {})])
    result = scorer.score(task, trace)
    assert result.score < 1.0


def test_decomposed_forbidden_call_penalty():
    """Agent calls a tool outside allowed_tools — forbidden_penalty should fire."""
    seq = [ExpectedToolCall(tool_name="slurm", required_args={})]
    task = _task(allowed_tools=["slurm"], expected_seq=seq)
    # Also calls facility which is forbidden
    trace = _trace_with_calls([("slurm", {}), ("facility", {})])
    result = scorer.score(task, trace)
    # forbidden_penalty = 1.0 - 0.3 = 0.7
    assert result.score < 1.0


def test_decomposed_no_required_args_any_call_scores_full_argument():
    """When required_args is empty, any call to the right tool scores 1.0 on arguments."""
    seq = [ExpectedToolCall(tool_name="telemetry", required_args={})]
    task = _task(allowed_tools=["telemetry"], expected_seq=seq)
    trace = _trace_with_calls([("telemetry", {"method": "query_range", "metric": "cpu_util"})])
    result = scorer.score(task, trace)
    assert result.score == 1.0


def test_decomposed_missing_expected_tool_argument_zero():
    """If expected tool was never called, argument_score for that step is 0."""
    seq = [
        ExpectedToolCall(tool_name="slurm", required_args={"method": "job_details"}),
        ExpectedToolCall(tool_name="docs",  required_args={"method": "search"}),
    ]
    task = _task(allowed_tools=["slurm", "docs"], expected_seq=seq)
    # Only calls slurm — docs never called
    trace = _trace_with_calls([("slurm", {"method": "job_details"})])
    result = scorer.score(task, trace)
    # argument_score = mean(1.0, 0.0) = 0.5
    assert result.score < 1.0
