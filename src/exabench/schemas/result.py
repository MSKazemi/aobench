"""Result schema — scored output of a benchmark task run."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DimensionScores(BaseModel):
    outcome: Optional[float] = None       # 0–1
    tool_use: Optional[float] = None      # 0–1
    grounding: Optional[float] = None     # 0–1
    governance: Optional[float] = None    # 0–1
    robustness: Optional[float] = None    # 0–1
    efficiency: Optional[float] = None    # 0–1


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
