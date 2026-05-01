"""Pydantic data models for the ExaBench leaderboard.

These models are always available regardless of whether FastAPI or
SQLAlchemy is installed.
"""

from typing import Optional

from pydantic import BaseModel


class ModelEntry(BaseModel):
    """One model submission on the leaderboard."""

    model_id: str                 # unique slug, e.g. "gpt-4o-2024-11-20"
    display_name: str
    organization: str
    submitted_at: str             # ISO-8601
    run_id: str
    is_verified: bool = False


class ResultRow(BaseModel):
    """One benchmark result row stored in the database."""

    result_id: str
    model_id: str
    task_id: str
    role: str
    aggregate_score: Optional[float] = None
    cup_score: Optional[float] = None
    engaged: bool = False
    governance_eng: Optional[float] = None


class CLEARRow(BaseModel):
    """CLEAR scores for one model."""

    model_id: str
    clear_score: Optional[float] = None
    E: Optional[float] = None
    A: Optional[float] = None
    R: Optional[float] = None
    C_norm: Optional[float] = None
    L_norm: Optional[float] = None
    cup: Optional[float] = None
    governance_eng: Optional[float] = None
    engagement_rate: Optional[float] = None
    n_tasks: int = 0


class SubmissionStatus(BaseModel):
    submission_id: str
    model_id: str
    status: str  # "pending" | "verifying" | "verified" | "rejected"
    message: str = ""


class VerificationResult(BaseModel):
    model_id: str
    schema_ok: bool
    aggregate_diff_ok: bool       # ±0.01 aggregate diff vs recomputed
    validity_gates: dict[str, bool] = {}   # V1-V6 gate outcomes


class LeaderboardResponse(BaseModel):
    generated_at: str
    entries: list[CLEARRow]
