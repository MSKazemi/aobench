"""Unit tests for WorfEvalScorer wired into AggregateScorer.

RED phase: these tests define the desired behavior before implementation.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from exabench.schemas.result import DimensionScores
from exabench.schemas.workflow_graph import WorkflowEdge, WorkflowGraph, WorkflowNode
from exabench.scorers.workflow_scorer import WorfEvalScorer

SCORING_PROFILES = Path(__file__).parent.parent.parent / "benchmark/configs/scoring_profiles.yaml"


# ---------------------------------------------------------------------------
# Schema: DimensionScores must have a workflow field
# ---------------------------------------------------------------------------

def test_dimension_scores_has_workflow_field():
    """DimensionScores must have an optional workflow field defaulting to None."""
    d = DimensionScores()
    assert hasattr(d, "workflow")
    assert d.workflow is None


def test_dimension_scores_accepts_workflow_value():
    """DimensionScores must accept a float for the workflow dimension."""
    d = DimensionScores(workflow=0.75)
    assert d.workflow == 0.75


# ---------------------------------------------------------------------------
# Scoring profile: default_hpc_v01 must include workflow weight
# ---------------------------------------------------------------------------

def _load_profiles() -> dict:
    with SCORING_PROFILES.open() as f:
        return yaml.safe_load(f)


def test_default_hpc_v01_has_workflow_weight():
    """default_hpc_v01 must declare a workflow dimension weight."""
    raw = _load_profiles()
    weights = raw["profiles"]["default_hpc_v01"]["weights"]
    assert "workflow" in weights, "default_hpc_v01 is missing 'workflow' weight"


def test_default_hpc_v01_workflow_weight_positive():
    """default_hpc_v01 workflow weight must be > 0 (it's the primary HPC profile)."""
    raw = _load_profiles()
    weights = raw["profiles"]["default_hpc_v01"]["weights"]
    assert weights.get("workflow", 0.0) > 0.0


def test_all_profiles_sum_to_one():
    """All weight profiles must still sum to 1.0 after adding workflow."""
    raw = _load_profiles()
    for name, data in raw["profiles"].items():
        total = sum(data["weights"].values())
        assert abs(total - 1.0) < 1e-6, f"Profile '{name}' weights sum to {total:.6f}, not 1.0"


# ---------------------------------------------------------------------------
# AggregateScorer wiring: workflow populated iff task has ground_truth_workflow
# ---------------------------------------------------------------------------

def _minimal_task(ground_truth_workflow=None):
    from exabench.schemas.task import TaskSpec
    return TaskSpec(
        task_id="WF_TEST_001",
        title="Workflow test",
        query_text="Check job workflow",
        role="scientific_user",
        qcat="JOB",
        difficulty="easy",
        environment_id="env_01",
        expected_answer_type="diagnosis",
        ground_truth_workflow=ground_truth_workflow,
    )


def _minimal_trace():
    from exabench.schemas.trace import Observation, ToolCall, Trace, TraceStep
    return Trace(
        trace_id="wf_trace_01",
        run_id="run_01",
        task_id="WF_TEST_001",
        role="scientific_user",
        environment_id="env_01",
        adapter_name="direct_qa",
        final_answer="OOM kill on node03",
        steps=[
            TraceStep(
                step_id=1,
                tool_call=ToolCall(tool_name="slurm", arguments={"method": "job_details"}),
                observation=Observation(content="job 891234 OOM"),
            ),
        ],
    )


def _gt_workflow() -> WorkflowGraph:
    """Minimal ground-truth workflow: slurm call → terminal."""
    nodes = [
        WorkflowNode(node_id="gt_n0", node_type="tool_call", tool_name="slurm", method="job_details"),
        WorkflowNode(node_id="gt_n1", node_type="terminal"),
    ]
    edges = [WorkflowEdge(source_node_id="gt_n0", target_node_id="gt_n1")]
    return WorkflowGraph(
        graph_id="WF_TEST_001_gt",
        task_id="WF_TEST_001",
        role="scientific_user",
        is_ground_truth=True,
        nodes=nodes,
        edges=edges,
        node_count=2,
    )


def test_aggregate_scorer_workflow_none_without_gt():
    """When TaskSpec has no ground_truth_workflow, dim_scores.workflow must be None."""
    from exabench.scorers.aggregate import AggregateScorer
    scorer = AggregateScorer(SCORING_PROFILES)
    result = scorer.score(_minimal_task(ground_truth_workflow=None), _minimal_trace(), run_id="r1")
    assert result.dimension_scores.workflow is None


def test_aggregate_scorer_workflow_set_with_gt():
    """When TaskSpec has ground_truth_workflow, dim_scores.workflow must be a float in [0,1]."""
    from exabench.scorers.aggregate import AggregateScorer
    scorer = AggregateScorer(SCORING_PROFILES)
    task = _minimal_task(ground_truth_workflow=_gt_workflow())
    result = scorer.score(task, _minimal_trace(), run_id="r1")
    assert result.dimension_scores.workflow is not None
    assert 0.0 <= result.dimension_scores.workflow <= 1.0


def test_aggregate_scorer_workflow_perfect_match():
    """When actual trace matches the GT workflow exactly, workflow score should be 1.0."""
    from exabench.schemas.trace import Observation, ToolCall, Trace, TraceStep
    from exabench.scorers.aggregate import AggregateScorer

    # GT: single slurm tool_call node
    gt = WorkflowGraph(
        graph_id="WF_TEST_001_gt",
        task_id="WF_TEST_001",
        role="scientific_user",
        is_ground_truth=True,
        nodes=[WorkflowNode(node_id="gt_n0", node_type="tool_call", tool_name="slurm", method="job_details")],
        edges=[],
        node_count=1,
    )
    task = _minimal_task(ground_truth_workflow=gt)

    # Trace with exactly that tool call (no edges needed — GT has no edges either)
    trace = Trace(
        trace_id="wf_perfect_01",
        run_id="run_01",
        task_id="WF_TEST_001",
        role="scientific_user",
        environment_id="env_01",
        adapter_name="direct_qa",
        final_answer="done",
        steps=[
            TraceStep(
                step_id=1,
                span_id="actual_n0",
                step_type="tool_call",
                tool_call=ToolCall(tool_name="slurm", method="job_details"),
                observation=Observation(content="ok"),
            ),
        ],
    )

    scorer = AggregateScorer(SCORING_PROFILES)
    result = scorer.score(task, trace, run_id="r1")
    assert result.dimension_scores.workflow == 1.0
