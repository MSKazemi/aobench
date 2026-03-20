"""WorkflowGraphBuilder — derives a WorkflowGraph from a completed Trace.

Algorithm:
1. Create one WorkflowNode per TraceStep with step_type in
   {tool_call, reasoning, final_answer} (terminal for final_answer/hard_fail).
2. For each step with parent_span_ids set, create WorkflowEdges
   from each parent to this step.
3. For steps with no parent_span_ids, infer sequential edges from the
   previous step (fallback for adapters that don't emit parent_span_ids).
4. Compute complexity metrics (node_count, max_depth, branching_factor,
   parallel_pairs).

Sources:
  Kim et al. (2024). WorfBench: Benchmarking Agentic Workflow Generation
  with Graph Structures. arXiv:2410.07869.
"""

from __future__ import annotations

from collections import defaultdict, deque

from exabench.schemas.trace import Trace, TraceStep
from exabench.schemas.workflow_graph import (
    WorkflowEdge,
    WorkflowGraph,
    WorkflowNode,
)


def _step_to_node(step: TraceStep) -> WorkflowNode:
    """Convert a TraceStep into a WorkflowNode."""
    node_type: str
    tool_name = None
    method = None
    reasoning_label = None

    if step.step_type in ("final_answer", "hard_fail"):
        node_type = "terminal"
    elif step.step_type == "tool_call" and step.tool_call is not None:
        node_type = "tool_call"
        tool_name = step.tool_call.tool_name
        method = step.tool_call.method or None
    else:
        node_type = "reasoning"
        # Use first 60 chars of reasoning as label when available
        if step.reasoning:
            reasoning_label = step.reasoning[:60].strip()

    accessed: list[str] = []
    if step.tool_call:
        accessed = list(step.tool_call.accessed_artifacts)

    return WorkflowNode(
        node_id=step.span_id or f"step_{step.step_id:03d}",
        node_type=node_type,  # type: ignore[arg-type]
        tool_name=tool_name,
        method=method,
        reasoning_label=reasoning_label,
        accessed_artifacts=accessed,
    )


class WorkflowGraphBuilder:
    """Derives a WorkflowGraph from a completed Trace."""

    @staticmethod
    def build(trace: Trace) -> WorkflowGraph:
        """Build and return a WorkflowGraph from a Trace."""
        nodes: list[WorkflowNode] = []
        edges: list[WorkflowEdge] = []

        span_to_index: dict[str, int] = {}

        for step in trace.steps:
            node = _step_to_node(step)
            span_to_index[node.node_id] = len(nodes)
            nodes.append(node)

        # Build edges
        for idx, (step, node) in enumerate(zip(trace.steps, nodes)):
            if step.parent_span_ids:
                for parent_id in step.parent_span_ids:
                    if parent_id in span_to_index:
                        edges.append(
                            WorkflowEdge(
                                source_node_id=parent_id,
                                target_node_id=node.node_id,
                                edge_type="sequential",
                            )
                        )
            elif idx > 0:
                # Fallback: sequential edge from previous node
                prev_node = nodes[idx - 1]
                edges.append(
                    WorkflowEdge(
                        source_node_id=prev_node.node_id,
                        target_node_id=node.node_id,
                        edge_type="sequential",
                    )
                )

        node_count = len(nodes)
        max_depth = WorkflowGraphBuilder._compute_max_depth(nodes, edges)
        branching_factor = WorkflowGraphBuilder._compute_branching_factor(nodes, edges)
        parallel_pairs = WorkflowGraphBuilder._compute_parallel_pairs(edges)

        return WorkflowGraph(
            graph_id=trace.trace_id,
            task_id=trace.task_id,
            role=trace.role,
            is_ground_truth=False,
            nodes=nodes,
            edges=edges,
            node_count=node_count,
            max_depth=max_depth,
            branching_factor=branching_factor,
            parallel_pairs=parallel_pairs,
        )

    @staticmethod
    def _compute_max_depth(
        nodes: list[WorkflowNode],
        edges: list[WorkflowEdge],
    ) -> int:
        """Longest path from any root to any leaf via topological sort."""
        if not nodes:
            return 0

        node_ids = {n.node_id for n in nodes}
        # in-degree and adjacency
        in_degree: dict[str, int] = {n.node_id: 0 for n in nodes}
        children: dict[str, list[str]] = defaultdict(list)

        for e in edges:
            if e.source_node_id in node_ids and e.target_node_id in node_ids:
                in_degree[e.target_node_id] += 1
                children[e.source_node_id].append(e.target_node_id)

        # BFS topological sort tracking max depth
        depth: dict[str, int] = {nid: 1 for nid in node_ids}
        queue: deque[str] = deque(
            nid for nid, d in in_degree.items() if d == 0
        )

        while queue:
            nid = queue.popleft()
            for child in children[nid]:
                depth[child] = max(depth[child], depth[nid] + 1)
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)

        return max(depth.values()) if depth else 0

    @staticmethod
    def _compute_branching_factor(
        nodes: list[WorkflowNode],
        edges: list[WorkflowEdge],
    ) -> float:
        """Average out-degree of non-terminal nodes."""
        if not nodes:
            return 0.0

        out_degree: dict[str, int] = {n.node_id: 0 for n in nodes}
        for e in edges:
            if e.source_node_id in out_degree:
                out_degree[e.source_node_id] += 1

        non_terminal = [
            n for n in nodes if n.node_type != "terminal"
        ]
        if not non_terminal:
            return 0.0

        total = sum(out_degree[n.node_id] for n in non_terminal)
        return round(total / len(non_terminal), 4)

    @staticmethod
    def _compute_parallel_pairs(edges: list[WorkflowEdge]) -> int:
        """Count of node pairs with parallel edges."""
        return sum(1 for e in edges if e.edge_type == "parallel")
