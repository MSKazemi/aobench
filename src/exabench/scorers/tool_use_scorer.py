"""Tool-use scorer — evaluates tool selection, argument quality, and call sequence.

Two scoring modes
-----------------
**Decomposed mode** (when ``eval_criteria.expected_tool_sequence`` is set):
    Scores the agent's tool use against a ground-truth call sequence.

    Sub-scores (each 0–1):

    selection_score
        Fraction of expected tool names that the agent actually called.
        Measures whether the agent discovered and used the right tools.
        Example: expected [slurm, docs], called [slurm] → 0.5

    argument_score
        For each expected call, checks whether the agent's matching call
        contained the required argument key-value pairs (string: exact match,
        number: ±5% relative tolerance).  Averaged across all expected calls.
        Example: expected slurm(method="job_details", job_id="891234"),
                 agent called slurm(method="job_details", job_id="891234") → 1.0
                 agent called slurm(method="job_details", job_id="999999") → 0.5

    sequence_score
        How well the agent's call order matches the expected order, using
        the longest common subsequence (LCS) of tool names divided by the
        length of the expected sequence.  A perfect match scores 1.0; a
        completely reversed or missing sequence scores 0.0.
        Example: expected [slurm, docs, rbac], called [docs, slurm, rbac] → 0.67

    forbidden_call_penalty
        Starts at 1.0 and is reduced by 0.3 for each call to a tool that is
        not in ``task.allowed_tools`` (when that list is set).  Equivalent to
        what the legacy scorer calls "precision".
        Example: allowed [slurm, docs], agent also called facility → 0.7

    Final score = mean(selection, argument, sequence, forbidden_call_penalty)

**Legacy mode** (when ``expected_tool_sequence`` is empty or not set):
    Heuristic scoring that does not require ground-truth sequences.

    coverage
        Did the agent call at least one tool that maps to a required evidence
        reference? (heuristic mapping from evidence-ref prefix to tool name)

    precision
        Did the agent avoid calling tools outside the allowed set?

    no_redundancy
        Did the agent avoid repeating the exact same (tool, arguments) call
        more than twice?

    Final score = mean(coverage, precision, no_redundancy)
"""

from __future__ import annotations

from exabench.schemas.task import ExpectedToolCall, TaskSpec
from exabench.schemas.trace import ToolCall, Trace
from exabench.scorers.base import BaseScorer, ScorerOutput

# Lazy import to avoid hard dependency on catalog at import time
def _try_load_catalog():
    try:
        from exabench.tools.catalog_loader import load_catalog
        return load_catalog()
    except Exception:
        return None

# Numeric tolerance for argument matching (relative, ±5%)
_ARG_NUMERIC_TOLERANCE = 0.05


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _args_match(actual: dict, required: dict) -> float:
    """Return fraction of required key-value pairs satisfied by actual args.

    String values: exact match (case-insensitive).
    Numeric values: within ±5% relative tolerance.
    Missing key in actual: counts as mismatch.
    Empty required dict: always 1.0 (no constraints specified).
    """
    if not required:
        return 1.0
    matched = 0
    for key, expected_val in required.items():
        actual_val = actual.get(key)
        if actual_val is None:
            continue
        if isinstance(expected_val, (int, float)) and isinstance(actual_val, (int, float)):
            denom = abs(float(expected_val)) if expected_val != 0 else 1.0
            if abs(float(actual_val) - float(expected_val)) / denom <= _ARG_NUMERIC_TOLERANCE:
                matched += 1
        else:
            if str(actual_val).lower() == str(expected_val).lower():
                matched += 1
    return matched / len(required)


def _lcs_length(a: list[str], b: list[str]) -> int:
    """Longest common subsequence length between two lists of strings."""
    m, n = len(a), len(b)
    # Use two-row DP to save memory
    prev = [0] * (n + 1)
    for i in range(1, m + 1):
        curr = [0] * (n + 1)
        for j in range(1, n + 1):
            if a[i - 1] == b[j - 1]:
                curr[j] = prev[j - 1] + 1
            else:
                curr[j] = max(prev[j], curr[j - 1])
        prev = curr
    return prev[n]


# ---------------------------------------------------------------------------
# Main scorer
# ---------------------------------------------------------------------------

class ToolUseScorer(BaseScorer):
    """Multi-mode tool-use scorer.

    See module docstring for full description of decomposed vs legacy modes.
    """

    dimension = "tool_use"

    def score(self, task: TaskSpec, trace: Trace) -> ScorerOutput:
        if trace.hard_fail:
            return ScorerOutput(
                dimension=self.dimension, score=0.0,
                hard_fail=True, hard_fail_reason=trace.hard_fail_reason,
            )

        tool_calls = [s.tool_call for s in trace.steps if s.tool_call is not None]

        if not tool_calls:
            if task.allowed_tools:
                return ScorerOutput(
                    dimension=self.dimension, score=0.0,
                    notes="No tools called but task has allowed_tools defined",
                )
            return ScorerOutput(
                dimension=self.dimension, score=1.0,
                notes="No tools required, none called",
            )

        expected_seq = (
            task.eval_criteria.expected_tool_sequence
            if task.eval_criteria else []
        )

        if expected_seq:
            return self._decomposed_score(task, tool_calls, expected_seq)
        return self._legacy_score(task, tool_calls)

    # ------------------------------------------------------------------
    # Decomposed mode
    # ------------------------------------------------------------------

    def _decomposed_score(
        self,
        task: TaskSpec,
        tool_calls: list[ToolCall],
        expected_seq: list[ExpectedToolCall],
    ) -> ScorerOutput:
        """Score using ground-truth expected_tool_sequence."""

        called_names = [tc.tool_name.split("__")[0] for tc in tool_calls]
        expected_names = [e.tool_name for e in expected_seq]

        # 1. selection_score — did the agent call the right tools?
        expected_tool_set = set(expected_names)
        called_tool_set = set(called_names)
        selection = len(expected_tool_set & called_tool_set) / len(expected_tool_set)

        # 2. argument_score — were the arguments correct?
        argument_scores: list[float] = []
        for exp in expected_seq:
            # Find the first actual call matching this tool name
            matching = next(
                (tc for tc in tool_calls if tc.tool_name.split("__")[0] == exp.tool_name),
                None,
            )
            if matching is None:
                argument_scores.append(0.0)
            else:
                argument_scores.append(_args_match(matching.arguments, exp.required_args))
        argument = sum(argument_scores) / len(argument_scores)

        # 3. sequence_score — was the order correct?
        lcs = _lcs_length(expected_names, called_names)
        sequence = lcs / len(expected_names)

        # 4. forbidden_call_penalty — were disallowed tools avoided?
        allowed = set(task.allowed_tools) if task.allowed_tools else None
        if allowed is not None:
            forbidden = [n for n in called_names if n not in allowed]
            forbidden_penalty = max(0.0, 1.0 - 0.3 * len(forbidden))
        else:
            forbidden_penalty = 1.0

        score = round((selection + argument + sequence + forbidden_penalty) / 4, 4)

        # Coverage metrics (diagnostic, appended to notes)
        coverage_notes = self._coverage_metric_notes(task, called_names, called_tool_set)

        notes = (
            f"decomposed: selection={selection:.2f}  argument={argument:.2f}  "
            f"sequence={sequence:.2f}  forbidden_penalty={forbidden_penalty:.2f}"
            f"{coverage_notes}"
        )
        return ScorerOutput(dimension=self.dimension, score=score, notes=notes)

    # ------------------------------------------------------------------
    # Legacy mode
    # ------------------------------------------------------------------

    def _legacy_score(
        self,
        task: TaskSpec,
        tool_calls: list[ToolCall],
    ) -> ScorerOutput:
        """Heuristic scoring when no expected_tool_sequence is provided."""

        called_tool_names = {tc.tool_name.split("__")[0] for tc in tool_calls}
        allowed = set(task.allowed_tools) if task.allowed_tools else called_tool_names

        # 1. Coverage: at least one call to a tool relevant to gold evidence refs
        coverage = self._coverage_score(task, called_tool_names)

        # 2. Precision: no calls to tools outside the allowed set
        disallowed_calls = called_tool_names - allowed
        precision = 1.0 if not disallowed_calls else max(0.0, 1.0 - 0.3 * len(disallowed_calls))

        # 3. No redundancy: same (tool, args) called more than twice
        call_counts: dict[str, int] = {}
        for tc in tool_calls:
            key = f"{tc.tool_name}:{sorted(tc.arguments.items())}"
            call_counts[key] = call_counts.get(key, 0) + 1
        redundant = sum(1 for c in call_counts.values() if c > 2)
        no_redundancy = max(0.0, 1.0 - 0.2 * redundant)

        score = round((coverage + precision + no_redundancy) / 3, 4)

        # Coverage metrics (diagnostic, appended to notes)
        called_names = [tc.tool_name.split("__")[0] for tc in tool_calls]
        coverage_notes = self._coverage_metric_notes(task, called_names, called_tool_names)

        notes = (
            f"legacy: coverage={coverage:.2f}  precision={precision:.2f}  "
            f"no_redundancy={no_redundancy:.2f}  tools_called={sorted(called_tool_names)}"
            f"{coverage_notes}"
        )
        return ScorerOutput(dimension=self.dimension, score=score, notes=notes)

    @staticmethod
    def _coverage_metric_notes(
        task: TaskSpec,
        called_names: list[str],
        called_tool_set: set[str],
    ) -> str:
        """Compute tool_discovery_rate and method_discovery_rate for the notes field.

        Uses the catalog when available; falls back to allowed_tools heuristic.
        Returns a formatted string to append to notes (empty string if metrics
        cannot be computed).
        """
        role = getattr(task, "role", None)
        if not role:
            return ""

        catalog = _try_load_catalog()

        if catalog is not None:
            available_tools = {t for t, _ in catalog.get_available_methods(role)}
            available_method_pairs = set(catalog.get_available_methods(role))
            called_method_pairs = set(
                tuple(tc.split("__", 1)) for tc in
                # Reconstruct (tool, method) pairs from raw tool_name strings
                # tool_name may already be "<tool>__<method>" format
                []  # populated below
            )
            # Build (tool, method) pairs from called names — tool_name may be
            # "slurm__job_details" or just "slurm"; we use available catalog methods
            # to match correctly.
            for name in called_names:
                parts = name.split("__", 1)
                if len(parts) == 2:
                    called_method_pairs.add((parts[0], parts[1]))
                else:
                    # bare tool name — count all methods from that tool as called
                    for t, m in available_method_pairs:
                        if t == parts[0]:
                            called_method_pairs.add((t, m))

            n_avail_tools = max(1, len(available_tools))
            n_avail_methods = max(1, len(available_method_pairs))

            tool_discovery = len(called_tool_set & available_tools) / n_avail_tools
            method_discovery = len(called_method_pairs & available_method_pairs) / n_avail_methods
        else:
            # Fallback: use allowed_tools if set
            if not task.allowed_tools:
                return ""
            available_tools = set(task.allowed_tools)
            n_avail_tools = max(1, len(available_tools))
            tool_discovery = len(called_tool_set & available_tools) / n_avail_tools
            return (
                f"  tool_discovery_rate={tool_discovery:.2f}"
            )

        return (
            f"  tool_discovery_rate={tool_discovery:.2f}"
            f"  method_discovery_rate={method_discovery:.2f}"
        )

    @staticmethod
    def _coverage_score(task: TaskSpec, called_tools: set[str]) -> float:
        """Heuristic: map gold_evidence_refs prefixes to tool names."""
        _REF_TO_TOOL = {
            "slurm": "slurm",
            "telemetry": "telemetry",
            "docs": "docs",
            "policy": "rbac",
            "incidents": "slurm",
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
