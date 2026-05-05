"""TraceWriter — persists trace and result artifacts to disk."""

from __future__ import annotations

from pathlib import Path

from aobench.schemas.result import BenchmarkResult
from aobench.schemas.trace import Trace
from aobench.schemas.trace_annotation import TraceAnnotation
from aobench.schemas.workflow_graph import WorfEvalScore, WorkflowGraph


class TraceWriter:
    def __init__(self, run_dir: str | Path) -> None:
        self._run_dir = Path(run_dir)

    def write_trace(self, trace: Trace) -> Path:
        out = self._run_dir / "traces" / f"{trace.task_id}_trace.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(trace.model_dump_json(indent=2))
        return out

    def write_result(self, result: BenchmarkResult) -> Path:
        out = self._run_dir / "results" / f"{result.task_id}_result.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(result.model_dump_json(indent=2))
        return out

    def write_workflow_graph(self, graph: WorkflowGraph) -> Path:
        """Write derived workflow graph alongside the trace."""
        out = self._run_dir / "traces" / f"{graph.graph_id}_workflow.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(graph.model_dump_json(indent=2))
        return out

    def write_worfeval_score(self, score: WorfEvalScore) -> Path:
        """Write WorfEval score for one run."""
        out = self._run_dir / "results" / f"{score.trace_id}_worfeval.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(score.model_dump_json(indent=2))
        return out

    def write_annotation(self, annotation: TraceAnnotation) -> Path:
        """Write TRAIL-style trace annotation."""
        out = self._run_dir / "annotations" / f"{annotation.run_id}_annotation.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(annotation.model_dump_json(indent=2))
        return out
