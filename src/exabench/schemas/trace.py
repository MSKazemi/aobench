"""Trace schema — execution trace of an agent run on a benchmark task."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class Observation(BaseModel):
    content: Any
    error: Optional[str] = None
    permission_denied: bool = False


class TraceStep(BaseModel):
    step_id: int
    reasoning: Optional[str] = None
    tool_call: Optional[ToolCall] = None
    observation: Optional[Observation] = None
    timestamp: Optional[datetime] = None


class Trace(BaseModel):
    """Full execution trace for one task run."""

    trace_id: str
    run_id: str
    task_id: str
    role: str
    environment_id: str
    adapter_name: str
    steps: list[TraceStep] = Field(default_factory=list)
    final_answer: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    total_tokens: Optional[int] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    model_name: Optional[str] = None
    hard_fail: bool = False
    hard_fail_reason: Optional[str] = None
