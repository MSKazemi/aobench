"""Aggregate scorer — combines dimension scores using a named weight profile."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from exabench.schemas.result import BenchmarkResult, DimensionScores
from exabench.schemas.scoring import ScoringConfig, WeightProfile
from exabench.schemas.task import TaskSpec
from exabench.schemas.trace import Trace
from exabench.scorers.efficiency_scorer import EfficiencyScorer
from exabench.scorers.governance_scorer import GovernanceScorer
from exabench.scorers.grounding_scorer import GroundingScorer
from exabench.scorers.outcome_scorer import OutcomeScorer
from exabench.scorers.tool_use_scorer import ToolUseScorer
from exabench.utils.cost import estimate_cost
from exabench.utils.ids import make_result_id
from exabench.utils.logging import get_logger

logger = get_logger(__name__)

_SCORERS = [OutcomeScorer(), GovernanceScorer(), EfficiencyScorer(), ToolUseScorer(), GroundingScorer()]


class AggregateScorer:
    def __init__(self, scoring_config_path: str | Path) -> None:
        with Path(scoring_config_path).open() as f:
            raw: dict[str, Any] = yaml.safe_load(f)
        profiles = {
            name: WeightProfile(name=name, **data)
            for name, data in raw.get("profiles", {}).items()
        }
        self._config = ScoringConfig(profiles=profiles)

    def score(self, task: TaskSpec, trace: Trace, run_id: str) -> BenchmarkResult:
        outputs = {s.dimension: s.score(task, trace) for s in _SCORERS}
        logger.debug("scorer outputs for %s: %s", task.task_id,
                     {k: round(v.score, 4) for k, v in outputs.items()})

        hard_fail = trace.hard_fail or any(o.hard_fail for o in outputs.values())
        hard_fail_reason = trace.hard_fail_reason or next(
            (o.hard_fail_reason for o in outputs.values() if o.hard_fail), None
        )

        governance_output = outputs["governance"]
        rbac_compliant = governance_output.score == 1.0 and not governance_output.hard_fail

        dim_scores = DimensionScores(
            outcome=outputs["outcome"].score,
            tool_use=outputs["tool_use"].score,
            grounding=outputs["grounding"].score,
            governance=outputs["governance"].score,
            efficiency=outputs["efficiency"].score,
        )

        profile = self._config.get(task.aggregate_weight_profile)
        aggregate = self._compute_weighted(dim_scores, profile)

        # Latency
        latency_seconds: float | None = None
        if trace.start_time and trace.end_time:
            latency_seconds = round((trace.end_time - trace.start_time).total_seconds(), 3)

        # Cost
        cost_estimate_usd: float | None = None
        if trace.model_name and trace.prompt_tokens is not None and trace.completion_tokens is not None:
            cost_estimate_usd = estimate_cost(
                trace.model_name, trace.prompt_tokens, trace.completion_tokens
            )

        return BenchmarkResult(
            result_id=make_result_id(),
            run_id=run_id,
            task_id=task.task_id,
            role=task.role,
            environment_id=task.environment_id,
            adapter_name=trace.adapter_name,
            hard_fail=hard_fail,
            hard_fail_reason=hard_fail_reason,
            rbac_compliant=rbac_compliant,
            dimension_scores=dim_scores,
            aggregate_score=0.0 if hard_fail else aggregate,
            weight_profile_name=profile.name,
            model_name=trace.model_name,
            prompt_tokens=trace.prompt_tokens,
            completion_tokens=trace.completion_tokens,
            total_tokens=trace.total_tokens,
            cost_estimate_usd=cost_estimate_usd,
            latency_seconds=latency_seconds,
            timestamp=datetime.now(tz=timezone.utc),
        )

    @staticmethod
    def _compute_weighted(scores: DimensionScores, profile: WeightProfile) -> float:
        total = 0.0
        score_map = scores.model_dump()
        for dim, weight in profile.weights.items():
            val = score_map.get(dim)
            if val is not None:
                total += val * weight
        return round(total, 4)
