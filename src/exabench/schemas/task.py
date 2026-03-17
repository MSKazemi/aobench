"""Task schema — canonical benchmark task specification."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

Role = Literal["scientific_user", "sysadmin", "facility_admin"]
QCat = Literal["JOB", "MON", "ENERGY"]
Difficulty = Literal["easy", "medium", "hard", "adversarial"]
AnswerType = Literal["diagnosis", "comparison", "lookup", "action", "explanation", "numeric", "summary", "factoid"]
ValidationStatus = Literal["not_started", "in_review", "validated", "rejected"]
ScoringReadiness = Literal["blocked", "partial", "ready"]
BenchmarkSplit = Literal["dev", "public_test", "hidden_test"]


class EvalCriteria(BaseModel):
    """Correctness check criteria embedded in a task spec."""

    evaluation_mode: Literal[
        "exact_match", "numeric_tolerance", "structured_output",
        "semantic_match", "policy_evaluation", "trace_sensitive",
    ] = "semantic_match"
    gold_answer: Optional[str] = None
    numeric_tolerance: Optional[float] = None
    required_evidence_refs: list[str] = Field(default_factory=list)


class TaskSpec(BaseModel):
    """Fully-specified benchmark task item."""

    # Identity
    task_id: str
    legacy_query_id: Optional[str] = None
    title: str

    # Task content
    query_text: str
    role: Role
    qcat: QCat
    difficulty: Difficulty

    # Environment linkage
    environment_id: str

    # Evidence and correctness
    gold_evidence_refs: list[str] = Field(default_factory=list)
    expected_answer_type: AnswerType
    eval_criteria: Optional[EvalCriteria] = None

    # Tool and access constraints
    allowed_tools: Optional[list[str]] = None
    hard_fail_conditions: list[str] = Field(default_factory=list)

    # Scoring configuration
    aggregate_weight_profile: str = "default_hpc_v01"

    # Lifecycle
    benchmark_split: Optional[BenchmarkSplit] = None
    validation_status: ValidationStatus = "not_started"
    scoring_readiness: ScoringReadiness = "blocked"
