"""Hybrid scorer — routes tasks to deterministic or rubric evaluation path.

Implements the hybrid scoring framework from DAComp (Lei et al. 2025,
arXiv:2512.04324) adapted for AOBench HPC tasks.

Routing:
  ``scoring_mode = "deterministic"`` → three-tier execution metrics (CS/CFS/SR)
  ``scoring_mode = "rubric"``        → LLM-judge with hierarchical rubric (+ optional GSB)

The final ``outcome`` (0–1) flows into CLEAR Efficacy (E) and pass^k reliability.

Usage::

    from aobench.scorers.hybrid_scorer import HybridScorer
    from aobench.scorers.rubric_scorer import make_anthropic_judge

    scorer = HybridScorer(llm_client=make_anthropic_judge())
    result = scorer.score(task, trace)
"""

from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any

from aobench.schemas.task import HybridScoringConfig, TaskSpec
from aobench.schemas.trace import Trace
from aobench.scorers.base import BaseScorer, ScorerOutput
from aobench.scorers.deterministic import DeterministicResult, deterministic_score
from aobench.scorers.gsb_scorer import LLMJudgeClient, gsb_score
from aobench.scorers.rubric_scorer import rubric_score

logger = logging.getLogger(__name__)


class HybridScorer(BaseScorer):
    """Scores task outcomes via the hybrid deterministic/rubric routing.

    Replaces ``OutcomeScorer`` for tasks that declare ``hybrid_scoring`` in
    their ``TaskSpec``.  Falls back to a ``score=0.5`` no-op when no
    ``hybrid_scoring`` config is present (backward-compatible).

    Args:
        llm_client: Optional callable ``(prompt: str) -> str`` for rubric/GSB
                    judging.  Required for ``scoring_mode="rubric"`` tasks;
                    ignored for deterministic tasks.  When ``None`` and a rubric
                    task is encountered, outcome is recorded as ``None``
                    (unscored) rather than raising.
        max_retries: Number of LLM judge retry attempts (default 3).
    """

    dimension = "outcome"

    def __init__(
        self,
        llm_client: LLMJudgeClient | None = None,
        max_retries: int = 3,
    ) -> None:
        self._llm_client = llm_client
        self._max_retries = max_retries

    # ------------------------------------------------------------------
    # BaseScorer interface
    # ------------------------------------------------------------------

    def score(self, task: TaskSpec, trace: Trace) -> ScorerOutput:
        """Route to the appropriate evaluation path.

        Returns a ``ScorerOutput`` with:
        - ``score``: the normalised outcome (0–1), or 0.0 on hard-fail / unscored.
        - ``notes``: JSON-serialisable metadata dict serialised to string.
        """
        if trace.hard_fail:
            return ScorerOutput(
                dimension=self.dimension,
                score=0.0,
                hard_fail=True,
                hard_fail_reason=trace.hard_fail_reason,
            )

        cfg = task.hybrid_scoring
        if cfg is None:
            # No hybrid config — this scorer is a no-op; return 0.5 partial credit
            return ScorerOutput(
                dimension=self.dimension,
                score=0.5,
                notes="hybrid_scoring not configured; partial credit",
            )

        if cfg.scoring_mode == "deterministic":
            return self._score_deterministic(task, trace, cfg)
        if cfg.scoring_mode == "rubric":
            return self._score_rubric(task, trace, cfg)

        raise ValueError(
            f"Unknown scoring_mode '{cfg.scoring_mode}' for task '{task.task_id}'. "
            "Expected 'deterministic' or 'rubric'."
        )

    # ------------------------------------------------------------------
    # Deterministic path
    # ------------------------------------------------------------------

    def _score_deterministic(
        self,
        task: TaskSpec,
        trace: Trace,
        cfg: HybridScoringConfig,
    ) -> ScorerOutput:
        if not cfg.components:
            return ScorerOutput(
                dimension=self.dimension,
                score=0.0,
                notes="deterministic task has no components defined",
            )

        agent_output = self._extract_agent_output(trace)
        result: DeterministicResult = deterministic_score(agent_output, cfg.components)

        notes = _serialize({
            "path": "deterministic",
            "cs": result.cs,
            "cfs": result.cfs,
            "sr": result.sr,
            "component_results": [asdict(r) for r in result.component_results],
        })

        logger.debug(
            "hybrid_scorer deterministic task=%s sr=%d cs=%.1f cfs=%.1f",
            task.task_id, result.sr, result.cs, result.cfs,
        )
        return ScorerOutput(
            dimension=self.dimension,
            score=result.outcome,
            notes=notes,
        )

    # ------------------------------------------------------------------
    # Rubric path
    # ------------------------------------------------------------------

    def _score_rubric(
        self,
        task: TaskSpec,
        trace: Trace,
        cfg: HybridScoringConfig,
    ) -> ScorerOutput:
        if not cfg.rubric_id:
            return ScorerOutput(
                dimension=self.dimension,
                score=0.0,
                notes="rubric task missing rubric_id",
            )

        agent_text = trace.final_answer or ""
        if not agent_text.strip():
            return ScorerOutput(
                dimension=self.dimension,
                score=0.0,
                notes="empty agent output",
            )

        if self._llm_client is None:
            logger.warning(
                "hybrid_scorer: rubric task '%s' requires an LLM judge but none configured — unscored",
                task.task_id,
            )
            return ScorerOutput(
                dimension=self.dimension,
                score=0.0,
                notes="rubric_unscored: no llm_client configured",
            )

        # --- Rubric score ---
        rubric_result = rubric_score(
            agent_output=agent_text,
            rubric_id=cfg.rubric_id,
            task_context=cfg.task_context or "",
            llm_client=self._llm_client,
            max_retries=self._max_retries,
        )

        # --- GSB score (optional) ---
        alpha = cfg.alpha if cfg.baseline_answers else 1.0
        gsb_result_score = 0.0

        if cfg.baseline_answers:
            gsb_result = gsb_score(
                agent_output=agent_text,
                baseline_answers=cfg.baseline_answers,
                llm_client=self._llm_client,
                task_context=cfg.task_context or "",
                max_retries=self._max_retries,
            )
            gsb_result_score = gsb_result.score_gsb
            gsb_meta: dict[str, Any] = {
                "score_gsb": gsb_result.score_gsb,
                "good_count": gsb_result.good_count,
                "same_count": gsb_result.same_count,
                "bad_count": gsb_result.bad_count,
            }
        else:
            gsb_meta = {"score_gsb": None, "alpha_override": 1.0}

        outcome = round(alpha * rubric_result.score_rubric + (1.0 - alpha) * gsb_result_score, 4)

        notes = _serialize({
            "path": "rubric",
            "score_rubric": rubric_result.score_rubric,
            "alpha": alpha,
            "breakdown": rubric_result.breakdown,
            "rationale": rubric_result.rationale,
            **gsb_meta,
        })

        logger.debug(
            "hybrid_scorer rubric task=%s outcome=%.4f score_rubric=%.4f alpha=%.2f",
            task.task_id, outcome, rubric_result.score_rubric, alpha,
        )
        return ScorerOutput(
            dimension=self.dimension,
            score=outcome,
            notes=notes,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_agent_output(trace: Trace) -> dict[str, Any]:
        """Build a component_id → value mapping from the trace.

        For deterministic tasks the agent output must be structured as JSON
        in ``trace.final_answer`` (a dict keyed by component_id).
        Falls back to an empty dict if parsing fails.
        """
        if not trace.final_answer:
            return {}
        import json as _json
        try:
            parsed = _json.loads(trace.final_answer)
            if isinstance(parsed, dict):
                return parsed
        except (_json.JSONDecodeError, TypeError):
            pass
        return {}


def _serialize(data: dict[str, Any]) -> str:
    import json as _json
    return _json.dumps(data, default=str)
