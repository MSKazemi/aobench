"""Workflow graph schema — derived from a Trace for WorfEval scoring.

A WorkflowGraph is a directed acyclic graph (DAG) where:
  - Nodes are tool calls or reasoning steps from the trace
  - Edges represent data-flow dependencies between steps

WorfEval scores how well the agent's actual WorkflowGraph matches
the TaskSpec's ground-truth WorkflowGraph via subgraph matching.

Sources:
  Kim et al. (2024). WorfBench: Benchmarking Agentic Workflow Generation
  with Graph Structures. arXiv:2410.07869.
"""

from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field


NodeType = Literal["tool_call", "reasoning", "terminal"]


class WorkflowNode(BaseModel):
    """One node in the workflow graph."""

    node_id: str
    # TraceStep.span_id for actual graphs; "<task_id>_gt_node_<N>" for GT.

    node_type: NodeType

    # For tool_call nodes:
    tool_name: Optional[str] = None    # e.g. "slurm", "telemetry", "rbac"
    method: Optional[str] = None       # e.g. "query_jobs", "check_permission"

    # For reasoning nodes:
    reasoning_label: Optional[str] = None
    # Optional short label, e.g. "diagnose_oom" or "cross_check_policy"

    # Provenance: which environment artifacts this node accessed
    accessed_artifacts: list[str] = Field(default_factory=list)


class WorkflowEdge(BaseModel):
    """A directed dependency edge: source → target."""

    source_node_id: str   # node that must complete first (provides data)
    target_node_id: str   # node that depends on source output
    edge_type: Literal["sequential", "data_flow", "parallel"] = "sequential"
    # sequential: target runs after source; order matters
    # data_flow:  target uses output of source as input argument
    # parallel:   source and target are independent and may run concurrently


class WorkflowGraph(BaseModel):
    """Directed acyclic graph of an agent's execution workflow.

    For actual traces: built by WorkflowGraphBuilder from a Trace.
    For ground truth: declared in TaskSpec.ground_truth_workflow.
    """

    graph_id: str           # trace_id for actual graphs; task_id + "_gt" for GT
    task_id: str
    role: str
    is_ground_truth: bool = False

    nodes: list[WorkflowNode] = Field(default_factory=list)
    edges: list[WorkflowEdge] = Field(default_factory=list)

    # Complexity metrics (computed at build time)
    node_count: int = 0
    max_depth: int = 0             # longest path from any root to any leaf
    branching_factor: float = 0.0  # avg out-degree of non-terminal nodes
    parallel_pairs: int = 0        # count of node pairs with parallel edges


class WorfEvalScore(BaseModel):
    """WorfEval partial-credit score for one actual vs ground-truth graph pair."""

    task_id: str
    trace_id: str
    ground_truth_graph_id: str

    subsequence_score: float   # [0, 1]: fraction of GT nodes in correct order
    subgraph_score: float      # [0, 1]: fraction of GT edges reproduced
    worfeval_score: float      # [0, 1]: harmonic mean of above two

    matched_nodes: list[str]              # GT node_ids matched in actual graph
    missed_nodes: list[str]               # GT node_ids absent from actual graph
    extra_nodes: list[str]                # actual node_ids not in GT (hallucinated)
    matched_edges: list[tuple[str, str]]  # (source, target) pairs matched
