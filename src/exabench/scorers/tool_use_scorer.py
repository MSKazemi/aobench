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

**Gold-trajectory augmentation** (when ``task.gold_trajectory`` is set):
    Computes four additional metrics on top of the existing score:
    - node_f1: set-level tool precision/recall F1 (He et al. 2024 / WorfBench)
    - ned: normalized edit distance over tool sequences (WorfBench / T-Eval)
    - step_accuracy: positional hit rate per gold step (T-Eval)
    - sequence_violations: pairwise ordering constraint violations (AgentHarm)
    The CLEAR T composite is upgraded to weight ned and node_f1 alongside
    the existing tool_use_score.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from exabench.schemas.task import ExpectedToolCall, GoldTrajectory, TaskSpec
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
# ToolUseResult — full scoring output including gold-trajectory metrics
# ---------------------------------------------------------------------------

@dataclass
class ToolUseResult:
    """Complete tool-use scoring result, including gold-trajectory metrics.

    Fields with None values indicate that the corresponding metric could not be
    computed (typically because the task has no gold_trajectory).
    """

    # Existing decomposed/legacy sub-scores
    tool_selection_score: float
    argument_correctness_score: float
    forbidden_call_penalty: float
    tool_use_score: float          # baseline composite (existing formula)

    # Gold-trajectory metrics (None when task has no gold_trajectory)
    node_f1: float | None = None
    ned: float | None = None
    step_accuracy: float | None = None
    sequence_violations: list[dict] | None = None
    sequence_penalty_applied: float | None = None
    hard_fail_triggered: bool | None = None

    # Final CLEAR T dimension score (may differ from tool_use_score when trajectory available)
    clear_T: float = 0.0


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


def _levenshtein(a: list[str], b: list[str]) -> int:
    """Levenshtein edit distance (insertions, deletions, substitutions each cost 1)."""
    m, n = len(a), len(b)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev = dp[0]
        dp[0] = i
        for j in range(1, n + 1):
            temp = dp[j]
            if a[i - 1] == b[j - 1]:
                dp[j] = prev
            else:
                dp[j] = 1 + min(prev, dp[j], dp[j - 1])
            prev = temp
    return dp[n]


# ---------------------------------------------------------------------------
# Gold-trajectory metric functions (spec §3)
# ---------------------------------------------------------------------------

def score_node_f1(gold_trajectory: GoldTrajectory, tool_calls: list[ToolCall]) -> float | None:
    """Node F1 — set-level tool selection accuracy (spec §3.1).

    Returns None if gold_trajectory is None.
    gold_set and pred_set use tool-level names only; duplicates are collapsed.
    """
    if gold_trajectory is None:
        return None
    gold_set = {step.tool for step in gold_trajectory.steps}
    if not gold_set:
        return None
    pred_set = {tc.tool_name.split("__")[0] for tc in tool_calls}
    if not pred_set:
        return 0.0
    intersection = pred_set & gold_set
    precision = len(intersection) / len(pred_set)
    recall = len(intersection) / len(gold_set)
    if precision + recall == 0:
        return 0.0
    return round(2 * precision * recall / (precision + recall), 4)


def score_ned(gold_trajectory: GoldTrajectory, tool_calls: list[ToolCall]) -> float | None:
    """Normalized Edit Distance over tool-name sequences (spec §3.2).

    Higher = better. 1.0 means exact sequence match (tool names only, not methods).
    Returns None if gold_trajectory is None.
    """
    if gold_trajectory is None:
        return None
    gold_seq = [step.tool for step in gold_trajectory.steps]
    pred_seq = [tc.tool_name.split("__")[0] for tc in tool_calls]
    max_len = max(len(gold_seq), len(pred_seq))
    if max_len == 0:
        return 1.0
    raw_ed = _levenshtein(pred_seq, gold_seq)
    return round(max(0.0, 1.0 - raw_ed / max_len), 4)


def score_step_accuracy(gold_trajectory: GoldTrajectory, tool_calls: list[ToolCall]) -> float | None:
    """T-Eval per-step planning accuracy (spec §3.3).

    Positional alignment: at step t, did the agent call gold_trajectory.steps[t].tool?
    Returns None if gold_trajectory is None or has no steps.
    """
    if gold_trajectory is None:
        return None
    T = len(gold_trajectory.steps)
    if T == 0:
        return None
    hits = 0
    for t, gold_step in enumerate(gold_trajectory.steps):
        if t < len(tool_calls):
            pred_tool = tool_calls[t].tool_name.split("__")[0]
            if pred_tool == gold_step.tool:
                hits += 1
    return round(hits / T, 4)


def score_sequence_violations(
    gold_trajectory: GoldTrajectory,
    tool_calls: list[ToolCall],
) -> list[dict]:
    """Ordered call-sequence violation detection (spec §3.4 / AgentHarm).

    Returns a list of violation dicts. Empty list if no violations.
    """
    violations: list[dict] = []
    if gold_trajectory is None or not gold_trajectory.ordered_required_pairs:
        return violations

    tool_names = [tc.tool_name.split("__")[0] for tc in tool_calls]
    for pair in gold_trajectory.ordered_required_pairs:
        before_indices = [i for i, t in enumerate(tool_names) if t == pair.before]
        after_indices = [i for i, t in enumerate(tool_names) if t == pair.after]

        # Violation: 'after' tool was called without any 'before' tool call
        if after_indices and not before_indices:
            violations.append({
                "constraint_id": f"{pair.before}_before_{pair.after}_{pair.operation}",
                "operation": pair.operation,
                "before_tool": pair.before,
                "after_tool": pair.after,
                "severity": pair.severity,
                "type": "before_tool_missing",
                "before_call_indices": [],
                "after_call_indices": after_indices,
            })
            continue

        # No ordering issue when neither (or only 'before') tool was called
        if not after_indices:
            continue

        # Violation: first 'after' call happens before last 'before' call
        if min(after_indices) < max(before_indices):
            violations.append({
                "constraint_id": f"{pair.before}_before_{pair.after}_{pair.operation}",
                "operation": pair.operation,
                "before_tool": pair.before,
                "after_tool": pair.after,
                "severity": pair.severity,
                "type": "wrong_order",
                "before_call_indices": before_indices,
                "after_call_indices": after_indices,
            })

    return violations


def _compute_clear_T(
    tool_use_score: float,
    node_f1: float | None,
    ned: float | None,
    sequence_violations: list[dict],
) -> tuple[float, float, bool]:
    """Compute upgraded CLEAR T composite (spec §4.3).

    Returns (clear_T, sequence_penalty_applied, hard_fail_triggered).
    """
    # Upgrade composite when ned/node_f1 are available
    if ned is not None and node_f1 is not None:
        T = 0.5 * tool_use_score + 0.3 * ned + 0.2 * node_f1
    else:
        T = tool_use_score

    # Accumulate sequence penalties
    sequence_penalty = 0.0
    hard_fail = False
    for v in sequence_violations:
        if v["severity"] == "hard_fail":
            hard_fail = True
        elif v["severity"] == "penalty":
            sequence_penalty += 0.20

    T = max(0.0, T - sequence_penalty)
    if hard_fail:
        T = 0.0

    return round(T, 4), round(sequence_penalty, 4), hard_fail


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
                result = ToolUseResult(
                    tool_selection_score=0.0, argument_correctness_score=0.0,
                    forbidden_call_penalty=0.0, tool_use_score=0.0, clear_T=0.0,
                )
                return ScorerOutput(
                    dimension=self.dimension, score=0.0,
                    notes="No tools called but task has allowed_tools defined",
                    tool_use_detail=result,
                )
            result = ToolUseResult(
                tool_selection_score=1.0, argument_correctness_score=1.0,
                forbidden_call_penalty=1.0, tool_use_score=1.0, clear_T=1.0,
            )
            return ScorerOutput(
                dimension=self.dimension, score=1.0,
                notes="No tools required, none called",
                tool_use_detail=result,
            )

        expected_seq = (
            task.eval_criteria.expected_tool_sequence
            if task.eval_criteria else []
        )

        if expected_seq:
            base_output = self._decomposed_score(task, tool_calls, expected_seq)
        else:
            base_output = self._legacy_score(task, tool_calls)

        # Gold-trajectory augmentation
        gold_traj = getattr(task, "gold_trajectory", None)
        if gold_traj is not None:
            return self._augment_with_gold_trajectory(
                base_output, gold_traj, tool_calls, task, expected_seq
            )

        # No gold trajectory — wrap in ToolUseResult and return
        result = ToolUseResult(
            tool_selection_score=base_output.score,
            argument_correctness_score=base_output.score,
            forbidden_call_penalty=1.0,
            tool_use_score=base_output.score,
            clear_T=base_output.score,
        )
        base_output.tool_use_detail = result
        return base_output

    def _augment_with_gold_trajectory(
        self,
        base_output: ScorerOutput,
        gold_traj: GoldTrajectory,
        tool_calls: list[ToolCall],
        task: TaskSpec,
        expected_seq: list[ExpectedToolCall],
    ) -> ScorerOutput:
        """Compute gold-trajectory metrics and upgraded CLEAR T."""
        tool_use_score = base_output.score

        nf1 = score_node_f1(gold_traj, tool_calls)
        ned = score_ned(gold_traj, tool_calls)
        step_acc = score_step_accuracy(gold_traj, tool_calls)
        violations = score_sequence_violations(gold_traj, tool_calls)

        clear_T, penalty_applied, hard_fail_triggered = _compute_clear_T(
            tool_use_score, nf1, ned, violations
        )

        # Derive sub-scores for ToolUseResult from decomposed mode if available
        if expected_seq:
            called_names = [tc.tool_name.split("__")[0] for tc in tool_calls]
            expected_names = [e.tool_name for e in expected_seq]
            expected_tool_set = set(expected_names)
            called_tool_set = set(called_names)
            selection = (
                len(expected_tool_set & called_tool_set) / len(expected_tool_set)
                if expected_tool_set else 0.0
            )
            allowed = set(task.allowed_tools) if task.allowed_tools else None
            if allowed is not None:
                forbidden = [n for n in called_names if n not in allowed]
                forbidden_penalty = max(0.0, 1.0 - 0.3 * len(forbidden))
            else:
                forbidden_penalty = 1.0
        else:
            selection = tool_use_score
            forbidden_penalty = 1.0

        result = ToolUseResult(
            tool_selection_score=selection,
            argument_correctness_score=tool_use_score,
            forbidden_call_penalty=forbidden_penalty,
            tool_use_score=tool_use_score,
            node_f1=nf1,
            ned=ned,
            step_accuracy=step_acc,
            sequence_violations=violations,
            sequence_penalty_applied=penalty_applied,
            hard_fail_triggered=hard_fail_triggered,
            clear_T=clear_T,
        )

        notes = (
            f"{base_output.notes or ''}  "
            f"node_f1={nf1:.4f}  ned={ned:.4f}  step_accuracy={step_acc:.4f}  "
            f"sequence_violations={len(violations)}  "
            f"sequence_penalty={penalty_applied:.2f}  hard_fail={hard_fail_triggered}  "
            f"clear_T={clear_T:.4f}"
        )

        return ScorerOutput(
            dimension=self.dimension,
            score=clear_T,
            hard_fail=hard_fail_triggered,
            hard_fail_reason="sequence_violation_hard_fail" if hard_fail_triggered else None,
            notes=notes,
            tool_use_detail=result,
        )

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
