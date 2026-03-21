"""Result schema — scored output of a benchmark task run."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class DimensionScores(BaseModel):
    outcome: Optional[float] = None       # 0–1
    tool_use: Optional[float] = None      # 0–1
    grounding: Optional[float] = None     # 0–1
    governance: Optional[float] = None    # 0–1
    robustness: Optional[float] = None    # 0–1
    efficiency: Optional[float] = None    # 0–1


class CheckpointResult(BaseModel):
    """Pass/fail outcome for a single checkpoint in a task run."""

    checkpoint_id: str
    passed: bool
    evidence: Optional[str] = None   # which tool call / text span triggered the pass


class BenchmarkResult(BaseModel):
    """Scored result for one task run."""

    result_id: str
    run_id: str
    task_id: str
    role: str
    environment_id: str
    adapter_name: str
    hard_fail: bool = False
    hard_fail_reason: Optional[str] = None
    rbac_compliant: bool = True
    dimension_scores: DimensionScores
    aggregate_score: Optional[float] = None
    weight_profile_name: str = "default_hpc_v01"
    model_name: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    cost_estimate_usd: Optional[float] = None
    latency_seconds: Optional[float] = None
    timestamp: datetime

    # Checkpoint scoring (populated by CheckpointScorer when task has checkpoints)
    checkpoint_results: Optional[list[CheckpointResult]] = None
    # Per-checkpoint pass/fail list. None if task has no checkpoints defined.

    s_partial: Optional[float] = None
    # Partial completion score [0, 1]: 0.5*(passed/total) + 0.5*s_full.
    # None if checkpoint_results is None or empty.

    s_full: Optional[float] = None
    # Binary full completion outcome [0 or 1], mirroring outcome via pass_threshold.
    # Stored separately so clear_report.py can use both S_partial and S_full.

    task_difficulty_tier: Optional[int] = None
    # Difficulty tier (1, 2, or 3) copied from TaskSpec at run time.
    # Required by compute_tier_accuracy() to group results without re-loading the task set.

    task_category: Optional[str] = None
    # QCAT category string (e.g. "PERF", "DATA", "SEC") copied from TaskSpec at scoring time.

    cup_score: Optional[float] = None
    # CuP-gated efficacy score: equals outcome when no violations, 0.0 otherwise.
    # None if CuP scoring has not been applied (e.g. pre-CuP runs).

    violation_vector: Optional[Any] = None
    # ViolationVector from GovernanceScorer. Untyped (Any) to avoid circular imports.
    # None if governance scoring did not produce a ViolationVector.

    tool_use_detail: Optional[Any] = None
    # ToolUseResult from ToolUseScorer. Untyped (Any) to avoid circular imports.
    # None if task has no gold_trajectory or tool_use scoring was not applied.
