"""Trace annotation schema — per-run error annotation for ExaBench traces.

Adapted from TRAIL (arXiv:2505.08638, Patronus AI, 2025).
Each run's execution trace is annotated with HPC-specific error categories
and holistic scores (0-5 scale) by the error_annotator module.

Annotation is additive: it enriches result records for post-hoc analysis
without changing the outcome score produced by the hybrid scorer.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class ErrorAnnotation(BaseModel):
    """One annotated error in an execution trace."""

    category: str
    """HPC leaf category ID, e.g. ``"hpc.info.wrong_time_range"``."""

    location: str
    """Span ID in the trace, e.g. ``"step_012_tool_call"``."""

    evidence: str
    """Verbatim excerpt from the trace supporting this annotation."""

    description: str
    """Explanation of what went wrong at this location."""

    impact: Literal["HIGH", "MEDIUM", "LOW"]

    source: Literal["auto", "llm_judge"]
    """Whether this annotation was produced by rule-based detection or an LLM judge."""

    first_or_last: Literal["first", "last"] = "first"
    """For ``hpc.system.tool_abuse``, annotate the last occurrence; all others use first."""


class HolisticScores(BaseModel):
    """Holistic trace-level scores on a 0–5 scale (TRAIL §5.2)."""

    reliability_score: float = Field(ge=0.0, le=5.0)
    """Did the agent behave consistently and correctly throughout?"""

    security_score: float = Field(ge=0.0, le=5.0)
    """Did the agent respect access boundaries and avoid unsafe actions?
    Maps to RBAC assurance (CLEAR dimension A)."""

    instruction_adherence_score: float = Field(ge=0.0, le=5.0)
    """Did the agent follow the task instructions?"""

    plan_opt_score: float = Field(ge=0.0, le=5.0)
    """Was the agent's plan efficient and well-structured?"""

    overall: float = Field(ge=0.0, le=5.0)
    """Mean of the four scores above."""

    @classmethod
    def from_components(
        cls,
        reliability: float,
        security: float,
        instruction_adherence: float,
        plan_opt: float,
    ) -> "HolisticScores":
        overall = (reliability + security + instruction_adherence + plan_opt) / 4.0
        return cls(
            reliability_score=reliability,
            security_score=security,
            instruction_adherence_score=instruction_adherence,
            plan_opt_score=plan_opt,
            overall=round(overall, 4),
        )


class TraceAnnotation(BaseModel):
    """Full annotation record for one task run.

    Combines TRAIL's annotation schema with ExaBench-specific fields.
    Stored alongside the BenchmarkResult; does not alter the outcome score.
    """

    task_id: str
    run_id: str
    model: Optional[str] = None
    role: str
    snapshot_id: str
    trace_token_length: Optional[int] = None

    errors: list[ErrorAnnotation] = Field(default_factory=list)
    scores: Optional[HolisticScores] = None

    # Mirror of the hybrid scorer outcome for correlation analysis
    outcome: Optional[float] = None
    path: Optional[str] = None  # "deterministic" | "rubric"
