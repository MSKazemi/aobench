"""Unit tests for ToolUseScorer — legacy mode, decomposed mode, and gold-trajectory metrics."""

from __future__ import annotations

from exabench.schemas.task import (
    EvalCriteria, ExpectedToolCall, GoldStep, GoldTrajectory, OrderedPair, TaskSpec,
)
from exabench.schemas.trace import Observation, ToolCall, Trace, TraceStep
from exabench.scorers.tool_use_scorer import (
    ToolUseScorer, _args_match, _lcs_length,
    score_node_f1, score_ned, score_step_accuracy, score_sequence_violations,
    _compute_clear_T,
)


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


# ---------------------------------------------------------------------------
# Gold-trajectory metric helpers
# ---------------------------------------------------------------------------

def _make_gold_trajectory(tools: list[str], pairs: list[dict] | None = None) -> GoldTrajectory:
    steps = [
        GoldStep(step=i + 1, tool=t, method="query", required_args={})
        for i, t in enumerate(tools)
    ]
    ordered_pairs = [
        OrderedPair(
            before=p["before"], after=p["after"],
            operation=p.get("operation", "op"),
            severity=p.get("severity", "hard_fail"),
        )
        for p in (pairs or [])
    ]
    return GoldTrajectory(steps=steps, ordered_required_pairs=ordered_pairs)


def _make_tool_calls(names: list[str]) -> list[ToolCall]:
    return [ToolCall(tool_name=n, arguments={}) for n in names]


def _task_with_trajectory(gold_tools: list[str], pairs: list[dict] | None = None) -> TaskSpec:
    gt = _make_gold_trajectory(gold_tools, pairs)
    return TaskSpec(
        task_id="TST_GT_001", title="GT", query_text="Q",
        role="scientific_user", qcat="JOB", difficulty="easy",
        environment_id="env_01", expected_answer_type="diagnosis",
        gold_trajectory=gt,
    )


# ---------------------------------------------------------------------------
# Gold-trajectory metric tests (spec §7.4)
# ---------------------------------------------------------------------------

def test_node_f1_exact_match():
    """Returns 1.0 for identical gold/pred tool sets."""
    gt = _make_gold_trajectory(["slurm", "telemetry"])
    calls = _make_tool_calls(["slurm", "telemetry"])
    assert score_node_f1(gt, calls) == 1.0


def test_node_f1_partial():
    """Returns < 1.0 for partial overlap."""
    gt = _make_gold_trajectory(["slurm", "telemetry"])
    calls = _make_tool_calls(["slurm"])
    f1 = score_node_f1(gt, calls)
    assert f1 is not None
    assert 0.0 < f1 < 1.0
    # precision=1.0 (slurm∈gold), recall=0.5 → F1 = 2/3 ≈ 0.667
    assert abs(f1 - 2 / 3) < 0.01


def test_ned_correct_order():
    """Returns 1.0 for matching sequence."""
    gt = _make_gold_trajectory(["slurm", "telemetry", "docs"])
    calls = _make_tool_calls(["slurm", "telemetry", "docs"])
    assert score_ned(gt, calls) == 1.0


def test_ned_reversed():
    """Penalizes reversed sequence (NED < 1.0)."""
    gt = _make_gold_trajectory(["slurm", "telemetry", "docs"])
    calls = _make_tool_calls(["docs", "telemetry", "slurm"])
    ned = score_ned(gt, calls)
    assert ned is not None
    assert ned < 1.0


def test_step_accuracy_partial():
    """Returns hit rate for partially correct positional sequence."""
    gt = _make_gold_trajectory(["slurm", "telemetry", "docs"])
    # slurm correct at pos 0, wrong at pos 1 (rbac≠telemetry), docs correct at pos 2
    calls = _make_tool_calls(["slurm", "rbac", "docs"])
    acc = score_step_accuracy(gt, calls)
    assert acc is not None
    assert abs(acc - 2 / 3) < 0.01


def test_sequence_violation_hard_fail():
    """hard_fail_triggered=True when 'after' tool called before 'before' tool."""
    pairs = [{"before": "rbac_tool", "after": "slurm_tool",
               "operation": "job_cancel_privileged", "severity": "hard_fail"}]
    gt = _make_gold_trajectory(["rbac_tool", "slurm_tool"], pairs)
    # slurm_tool (index 0) called before rbac_tool (index 1) → violation
    calls = _make_tool_calls(["slurm_tool", "rbac_tool"])
    violations = score_sequence_violations(gt, calls)
    assert len(violations) == 1
    assert violations[0]["severity"] == "hard_fail"
    _, _, hard_fail = _compute_clear_T(0.8, 0.7, 0.6, violations)
    assert hard_fail is True


def test_sequence_penalty_applied():
    """CLEAR T reduced by 0.20 for a severity='penalty' violation."""
    pairs = [{"before": "docs_tool", "after": "slurm_tool",
               "operation": "policy_lookup", "severity": "penalty"}]
    gt = _make_gold_trajectory(["docs_tool", "slurm_tool"], pairs)
    # slurm_tool called first → violation
    calls = _make_tool_calls(["slurm_tool", "docs_tool"])
    violations = score_sequence_violations(gt, calls)
    assert len(violations) == 1
    assert violations[0]["severity"] == "penalty"
    base = 0.8
    ned_val = 0.5
    nf1_val = 0.9
    T, penalty, hf = _compute_clear_T(base, nf1_val, ned_val, violations)
    expected_base = 0.5 * base + 0.3 * ned_val + 0.2 * nf1_val
    assert abs(T - max(0.0, expected_base - 0.20)) < 0.001
    assert abs(penalty - 0.20) < 0.001
    assert hf is False


def test_no_gold_trajectory_returns_none():
    """All new fields are None when task has no gold_trajectory."""
    task = _task(allowed_tools=["slurm"])
    trace = _trace_with_calls(["slurm"])
    result = scorer.score(task, trace)
    detail = result.tool_use_detail
    assert detail is not None
    assert detail.node_f1 is None
    assert detail.ned is None
    assert detail.step_accuracy is None
    assert detail.sequence_violations is None
    assert detail.sequence_penalty_applied is None
    assert detail.hard_fail_triggered is None


def test_composite_clear_T_formula():
    """Weighted composite matches spec §4.3: T = 0.5*tus + 0.3*ned + 0.2*nf1."""
    tus = 0.8
    ned_val = 0.6
    nf1_val = 0.9
    expected_T = 0.5 * tus + 0.3 * ned_val + 0.2 * nf1_val
    T, penalty, hf = _compute_clear_T(tus, nf1_val, ned_val, [])
    assert abs(T - expected_T) < 0.001
    assert penalty == 0.0
    assert hf is False
