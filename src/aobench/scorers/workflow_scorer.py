"""WorfEval scorer — graph-based workflow evaluation.

Measures how well an agent's actual execution graph matches the ground-truth
workflow graph using LCS subsequence matching + directed subgraph edge matching.

Algorithm adapted from:
  Kim et al. (2024). WorfBench: Benchmarking Agentic Workflow Generation
  with Graph Structures. arXiv:2410.07869.
"""

from __future__ import annotations

from typing import Optional

from aobench.schemas.workflow_graph import (
    WorkflowGraph,
    WorkflowNode,
    WorfEvalScore,
)


def _nodes_match(gt_node: WorkflowNode, actual_node: WorkflowNode) -> bool:
    """Return True if actual_node satisfies the ground-truth node spec."""
    if gt_node.node_type != actual_node.node_type:
        return False
    if gt_node.node_type == "tool_call":
        if gt_node.tool_name != actual_node.tool_name:
            return False
        if gt_node.method != actual_node.method:
            return False
    if gt_node.node_type == "reasoning":
        # None label in GT means any reasoning node at that position qualifies
        if gt_node.reasoning_label is not None:
            if gt_node.reasoning_label != actual_node.reasoning_label:
                return False
    # terminal always matches
    return True


def _lcs_indices(
    gt_nodes: list[WorkflowNode],
    actual_nodes: list[WorkflowNode],
) -> list[tuple[int, int]]:
    """Return LCS as list of (gt_index, actual_index) pairs."""
    n, m = len(gt_nodes), len(actual_nodes)
    # DP table
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if _nodes_match(gt_nodes[i - 1], actual_nodes[j - 1]):
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

    # Backtrack to find matched pairs
    pairs: list[tuple[int, int]] = []
    i, j = n, m
    while i > 0 and j > 0:
        if _nodes_match(gt_nodes[i - 1], actual_nodes[j - 1]) and dp[i][j] == dp[i - 1][j - 1] + 1:
            pairs.append((i - 1, j - 1))
            i -= 1
            j -= 1
        elif dp[i - 1][j] > dp[i][j - 1]:
            i -= 1
        else:
            j -= 1
    pairs.reverse()
    return pairs


class WorfEvalScorer:
    """Computes WorfEval score for one actual vs ground-truth graph pair.

    Usage::

        score = WorfEvalScorer.score(actual_graph, ground_truth_graph)
    """

    @staticmethod
    def score(
        actual: WorkflowGraph,
        ground_truth: Optional[WorkflowGraph],
    ) -> WorfEvalScore:
        """Compute WorfEval score.

        Args:
            actual: WorkflowGraph derived from the agent's trace.
            ground_truth: Ground-truth WorkflowGraph from TaskSpec.
                          If None, all scores are 0.0 and matched lists are empty.

        Returns:
            WorfEvalScore with subsequence_score, subgraph_score, worfeval_score.
        """
        if ground_truth is None:
            return WorfEvalScore(
                task_id=actual.task_id,
                trace_id=actual.graph_id,
                ground_truth_graph_id="",
                subsequence_score=0.0,
                subgraph_score=0.0,
                worfeval_score=0.0,
                matched_nodes=[],
                missed_nodes=[],
                extra_nodes=[n.node_id for n in actual.nodes],
                matched_edges=[],
            )

        gt_nodes = ground_truth.nodes
        actual_nodes = actual.nodes

        # --- Subsequence score (LCS) ---
        if not gt_nodes:
            subseq_score = 1.0
            matched_gt_indices: list[int] = []
            matched_actual_indices: list[int] = []
        else:
            lcs_pairs = _lcs_indices(gt_nodes, actual_nodes)
            matched_gt_indices = [p[0] for p in lcs_pairs]
            matched_actual_indices = [p[1] for p in lcs_pairs]
            subseq_score = len(lcs_pairs) / len(gt_nodes)

        matched_gt_ids = {gt_nodes[i].node_id for i in matched_gt_indices}
        matched_actual_ids = {actual_nodes[i].node_id for i in matched_actual_indices}

        # Map GT node_id → matched actual node_id
        gt_to_actual: dict[str, str] = {}
        for gi, ai in zip(matched_gt_indices, matched_actual_indices):
            gt_to_actual[gt_nodes[gi].node_id] = actual_nodes[ai].node_id

        missed_nodes = [n.node_id for n in gt_nodes if n.node_id not in matched_gt_ids]
        extra_nodes = [n.node_id for n in actual_nodes if n.node_id not in matched_actual_ids]

        # --- Subgraph score ---
        gt_edges = {(e.source_node_id, e.target_node_id) for e in ground_truth.edges}
        actual_edge_set = {(e.source_node_id, e.target_node_id) for e in actual.edges}

        matched_edges: list[tuple[str, str]] = []
        for src_gt, tgt_gt in gt_edges:
            if src_gt in gt_to_actual and tgt_gt in gt_to_actual:
                src_actual = gt_to_actual[src_gt]
                tgt_actual = gt_to_actual[tgt_gt]
                if (src_actual, tgt_actual) in actual_edge_set:
                    matched_edges.append((src_gt, tgt_gt))

        if not gt_edges:
            subgraph_score = 1.0
        else:
            subgraph_score = len(matched_edges) / len(gt_edges)

        # --- WorfEval (harmonic mean) ---
        denom = subseq_score + subgraph_score
        if denom == 0.0:
            worfeval = 0.0
        else:
            worfeval = 2.0 * subseq_score * subgraph_score / denom

        return WorfEvalScore(
            task_id=actual.task_id,
            trace_id=actual.graph_id,
            ground_truth_graph_id=ground_truth.graph_id,
            subsequence_score=round(subseq_score, 6),
            subgraph_score=round(subgraph_score, 6),
            worfeval_score=round(worfeval, 6),
            matched_nodes=list(matched_gt_ids),
            missed_nodes=missed_nodes,
            extra_nodes=extra_nodes,
            matched_edges=matched_edges,
        )
