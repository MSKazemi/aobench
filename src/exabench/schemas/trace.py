"""Trace schema — execution trace of an agent run on a benchmark task."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


StepType = Literal["reasoning", "tool_call", "final_answer", "hard_fail"]


class ToolCall(BaseModel):
    tool_name: str
    method: str = ""                              # e.g. "query_jobs", "query_timeseries"
    arguments: dict[str, Any] = Field(default_factory=dict)
    accessed_artifacts: list[str] = Field(default_factory=list)
    # Flowcept 'used': env-relative file paths this call accessed


class Observation(BaseModel):
    content: Any
    error: Optional[str] = None
    permission_denied: bool = False
    generated_artifacts: list[str] = Field(default_factory=list)
    # Flowcept 'generated': logical artifact names produced


class TraceStep(BaseModel):
    step_id: int
    span_id: str = ""
    # Globally unique ID: "{trace_id}_step_{step_id:03d}"
    step_type: StepType = "reasoning"
    reasoning: Optional[str] = None
    tool_call: Optional[ToolCall] = None
    observation: Optional[Observation] = None
    timestamp: Optional[datetime] = None
    duration_ms: Optional[float] = None
    parent_span_ids: list[str] = Field(default_factory=list)
    # Steps this step explicitly depends on (for parallel/chained patterns)


class Trace(BaseModel):
    """Full execution trace for one task run."""

    # ---- Identity ----
    trace_id: str        # = workflow_id in Flowcept vocabulary
    run_id: str
    task_id: str
    role: str
    environment_id: str
    adapter_name: str

    # ---- Execution steps ----
    steps: list[TraceStep] = Field(default_factory=list)
    final_answer: Optional[str] = None

    # ---- Timing ----
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    # ---- Cost + model ----
    total_tokens: Optional[int] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    model_name: Optional[str] = None
    cost_estimate_usd: Optional[float] = None

    # ---- Hard fail ----
    hard_fail: bool = False
    hard_fail_reason: Optional[str] = None

    # ---- Provenance (Flowcept §2.2) ----
    campaign_id: Optional[str] = None
    # Groups all k traces from k runs of the same task.
    # Format: "{task_id}__{role}__{model_name}"

    # ---- WorfBench graph metrics (computed at write time) ----
    workflow_node_count: Optional[int] = None
    workflow_max_depth: Optional[int] = None
    workflow_parallel_steps: Optional[int] = None
