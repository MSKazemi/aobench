"""Grounding scorer — checks whether the agent's answer is supported by tool observations."""

from __future__ import annotations

import json
import re
from typing import Any

from exabench.schemas.task import TaskSpec
from exabench.schemas.trace import Trace
from exabench.scorers.base import BaseScorer, ScorerOutput

# Regex patterns for HPC-domain key tokens
_RE_NUMBER = re.compile(r"\b\d+\.?\d*\b")
_RE_HPC_ENTITY = re.compile(
    r"\b(?:node|gpu|rack|job|partition|queue|user)[\w\-]+\b", re.IGNORECASE
)
_RE_STATUS = re.compile(
    r"\b(?:running|pending|failed|completed|cancelled|timeout|"
    r"warning|critical|ok|error|oom|preempted)\b",
    re.IGNORECASE,
)


def _flatten(obj: Any) -> str:
    """Recursively flatten any Python object to a single lowercase string."""
    if obj is None:
        return ""
    if isinstance(obj, str):
        return obj.lower()
    if isinstance(obj, (int, float)):
        return str(obj)
    if isinstance(obj, (list, tuple)):
        return " ".join(_flatten(item) for item in obj)
    if isinstance(obj, dict):
        return " ".join(_flatten(v) for v in obj.values())
    try:
        return json.dumps(obj).lower()
    except (TypeError, ValueError):
        return str(obj).lower()


def _key_tokens(text: str) -> set[str]:
    """Extract numbers, HPC entity names, and status words from *text*."""
    tokens: set[str] = set()
    lower = text.lower()

    for m in _RE_NUMBER.finditer(lower):
        val = m.group()
        # Skip single-digit trivial values (0-9) to reduce noise
        if len(val) > 1 or "." in val:
            tokens.add(val)

    for m in _RE_HPC_ENTITY.finditer(lower):
        tokens.add(m.group().lower())

    for m in _RE_STATUS.finditer(lower):
        tokens.add(m.group().lower())

    return tokens


class GroundingScorer(BaseScorer):
    """Scores how well the agent's final answer is grounded in tool observations.

    Sub-scores:
    1. **Observation presence** — did any tool return usable (non-error) data?
       No observations → 0.0 immediately (ungrounded by definition).
    2. **Answer-to-evidence overlap** — what fraction of the answer's key tokens
       (numbers, entity names, status words) appear in the collected observations?

    The final score is the overlap fraction. If observations exist but the answer
    contains no extractable tokens, a partial credit of 0.3 is given (the agent
    called tools but produced a vague answer).

    This scorer does NOT penalise for calling the wrong tools — that is
    ``ToolUseScorer``'s job. It only asks: *is the answer supported by what
    the tools actually returned?*
    """

    dimension = "grounding"

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
                                notes="No final answer to assess")

        # Collect all successful (non-error) observations from the trace
        obs_texts: list[str] = []
        for step in trace.steps:
            if step.observation and not step.observation.error and not step.observation.permission_denied:
                obs_texts.append(_flatten(step.observation.content))

        if not obs_texts:
            return ScorerOutput(dimension=self.dimension, score=0.0,
                                notes="No successful tool observations in trace")

        obs_blob = " ".join(obs_texts)
        obs_tokens = _key_tokens(obs_blob)
        answer_tokens = _key_tokens(trace.final_answer)

        if not answer_tokens:
            # Agent answered but made no specific claims — vague, partial credit
            return ScorerOutput(
                dimension=self.dimension,
                score=0.3,
                notes="Answer contains no extractable key tokens; partial credit",
            )

        if not obs_tokens:
            # Observations returned no extractable evidence
            return ScorerOutput(
                dimension=self.dimension,
                score=0.1,
                notes="Observations contain no extractable key tokens",
            )

        supported = answer_tokens & obs_tokens
        score = round(len(supported) / len(answer_tokens), 4)

        notes = (
            f"answer_tokens={len(answer_tokens)}  "
            f"obs_tokens={len(obs_tokens)}  "
            f"supported={len(supported)}  "
            f"overlap={score:.2f}  "
            f"supported_by={sorted(supported)}"
        )
        return ScorerOutput(dimension=self.dimension, score=score, notes=notes)
