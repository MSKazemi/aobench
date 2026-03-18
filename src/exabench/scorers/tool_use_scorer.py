"""Tool-use scorer — evaluates tool selection, argument quality, and call sequence."""

from __future__ import annotations

from exabench.schemas.task import TaskSpec
from exabench.schemas.trace import Trace
from exabench.scorers.base import BaseScorer, ScorerOutput


class ToolUseScorer(BaseScorer):
    """Scores the agent's tool-use behaviour across three sub-dimensions:

    1. Coverage   — did the agent call at least one tool that maps to a required evidence ref?
    2. Precision  — did the agent avoid calling disallowed tools?
    3. No-redundancy — did the agent avoid repeating the exact same call more than twice?

    Final score = mean of the three sub-scores.
    """

    dimension = "tool_use"

    def score(self, task: TaskSpec, trace: Trace) -> ScorerOutput:
        if trace.hard_fail:
            return ScorerOutput(dimension=self.dimension, score=0.0,
                                hard_fail=True, hard_fail_reason=trace.hard_fail_reason)

        tool_calls = [
            s.tool_call for s in trace.steps if s.tool_call is not None
        ]

        if not tool_calls:
            # No tools used — check if task requires tools
            if task.allowed_tools:
                return ScorerOutput(dimension=self.dimension, score=0.0,
                                    notes="No tools called but task has allowed_tools defined")
            return ScorerOutput(dimension=self.dimension, score=1.0,
                                notes="No tools required, none called")

        called_tool_names = {tc.tool_name.split("__")[0] for tc in tool_calls}
        allowed = set(task.allowed_tools) if task.allowed_tools else called_tool_names

        # 1. Coverage: at least one call to a tool relevant to gold evidence refs
        coverage = self._coverage_score(task, called_tool_names)

        # 2. Precision: no calls to tools outside the allowed set
        disallowed_calls = called_tool_names - allowed
        precision = 1.0 if not disallowed_calls else max(0.0, 1.0 - 0.3 * len(disallowed_calls))

        # 3. No redundancy: same (tool, method, args) called more than twice
        call_counts: dict[str, int] = {}
        for tc in tool_calls:
            key = f"{tc.tool_name}:{sorted(tc.arguments.items())}"
            call_counts[key] = call_counts.get(key, 0) + 1
        redundant = sum(1 for c in call_counts.values() if c > 2)
        no_redundancy = max(0.0, 1.0 - 0.2 * redundant)

        score = round((coverage + precision + no_redundancy) / 3, 4)
        notes = (
            f"coverage={coverage:.2f}  precision={precision:.2f}  "
            f"no_redundancy={no_redundancy:.2f}  tools_called={sorted(called_tool_names)}"
        )
        return ScorerOutput(dimension=self.dimension, score=score, notes=notes)

    @staticmethod
    def _coverage_score(task: TaskSpec, called_tools: set[str]) -> float:
        """Heuristic: map gold_evidence_refs prefixes to tool names."""
        _REF_TO_TOOL = {
            "slurm": "slurm",
            "telemetry": "telemetry",
            "docs": "docs",
            "policy": "rbac",
            "incidents": "slurm",  # incidents surfaced via slurm/docs
            "power": "facility",
            "rack": "facility",
            "inventory": "facility",
            "cooling": "facility",
            "thermal": "facility",
        }
        if not task.gold_evidence_refs:
            return 1.0

        required_tools: set[str] = set()
        for ref in task.gold_evidence_refs:
            prefix = ref.split("/")[0]
            if prefix in _REF_TO_TOOL:
                required_tools.add(_REF_TO_TOOL[prefix])

        if not required_tools:
            return 1.0

        covered = required_tools & called_tools
        return len(covered) / len(required_tools)
