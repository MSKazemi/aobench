"""Outcome scorer — evaluates the quality of the agent's final answer."""

from __future__ import annotations

import re

from aobench.schemas.task import TaskSpec
from aobench.schemas.trace import Trace
from aobench.scorers.base import BaseScorer, ScorerOutput

# Fuzzy match threshold: partial_ratio score (0–100) required to count as a match
_FUZZY_THRESHOLD = 70
# Numeric tolerance: answers within this relative fraction are treated as correct
_NUMERIC_TOLERANCE = 0.05


def _extract_numbers(text: str) -> list[float]:
    """Extract all numeric values from a string."""
    return [float(m) for m in re.findall(r"-?\d+(?:\.\d+)?", text)]


def _numeric_match(pred: str, gold: str) -> float | None:
    """If both strings contain numbers, return 1.0 if all gold numbers are
    approximately reproduced in pred (within tolerance), else 0.0.
    Returns None if no numbers found in gold."""
    gold_nums = _extract_numbers(gold)
    if not gold_nums:
        return None
    pred_nums = _extract_numbers(pred)
    if not pred_nums:
        return 0.0
    matched = 0
    for gn in gold_nums:
        denom = abs(gn) if gn != 0 else 1.0
        if any(abs(pn - gn) / denom <= _NUMERIC_TOLERANCE for pn in pred_nums):
            matched += 1
    return matched / len(gold_nums)


def _fuzzy_score(pred: str, gold: str) -> float:
    """Return a 0–1 score using rapidfuzz partial_ratio."""
    try:
        from rapidfuzz import fuzz
    except ImportError:
        # Fallback: crude token overlap
        pred_tokens = set(pred.lower().split())
        gold_tokens = set(gold.lower().split())
        if not gold_tokens:
            return 1.0
        return len(pred_tokens & gold_tokens) / len(gold_tokens)
    return fuzz.partial_ratio(pred.lower(), gold.lower()) / 100.0


class OutcomeScorer(BaseScorer):
    """Scores the agent's final answer against the task's gold answer.

    Scoring logic by evaluation_mode:

    - ``exact_match``   : 1.0 only if strings match exactly (case-insensitive).
    - ``semantic_match``: fuzzy string similarity (rapidfuzz partial_ratio ≥ threshold),
                          blended with numeric accuracy when the answer contains numbers.
    - ``numeric``       : numeric tolerance check only (±5% relative error).
    - unset / other     : partial credit (0.5) for any non-empty answer.
    """

    dimension = "outcome"

    def score(self, task: TaskSpec, trace: Trace) -> ScorerOutput:
        if trace.hard_fail:
            return ScorerOutput(
                dimension=self.dimension,
                score=0.0,
                hard_fail=True,
                hard_fail_reason=trace.hard_fail_reason,
            )

        if not trace.final_answer or not trace.final_answer.strip():
            return ScorerOutput(dimension=self.dimension, score=0.0,
                                notes="No final answer produced")

        if not (task.eval_criteria and task.eval_criteria.gold_answer):
            return ScorerOutput(dimension=self.dimension, score=0.5,
                                notes="Gold answer not set; partial credit for non-empty answer")

        gold = task.eval_criteria.gold_answer.strip()
        pred = trace.final_answer.strip()
        mode = (task.eval_criteria.evaluation_mode or "").lower()

        if mode == "exact_match":
            match = pred.lower() == gold.lower()
            return ScorerOutput(dimension=self.dimension, score=1.0 if match else 0.0,
                                notes=f"exact_match={'yes' if match else 'no'}")

        if mode == "numeric":
            num_score = _numeric_match(pred, gold)
            if num_score is None:
                # No numbers in gold — fall back to fuzzy
                score = _fuzzy_score(pred, gold)
                return ScorerOutput(dimension=self.dimension, score=round(score, 4),
                                    notes=f"numeric mode fallback to fuzzy: {score:.2f}")
            return ScorerOutput(dimension=self.dimension, score=round(num_score, 4),
                                notes=f"numeric match: {num_score:.2f}")

        if mode == "semantic_match":
            fuzzy = _fuzzy_score(pred, gold)
            num_score = _numeric_match(pred, gold)
            if num_score is not None:
                # Blend: 60% fuzzy text, 40% numeric accuracy
                score = round(0.6 * fuzzy + 0.4 * num_score, 4)
                notes = (
                    f"semantic_match: fuzzy={fuzzy:.2f}  numeric={num_score:.2f}  "
                    f"blended={score:.4f}"
                )
            else:
                score = round(fuzzy, 4)
                notes = f"semantic_match: fuzzy={fuzzy:.2f}"
            return ScorerOutput(dimension=self.dimension, score=score, notes=notes)

        # Unknown / unset mode — partial credit
        return ScorerOutput(dimension=self.dimension, score=0.5,
                            notes=f"Unknown evaluation_mode '{mode}'; partial credit")
