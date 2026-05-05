"""Task schema — canonical benchmark task specification."""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, model_validator

from aobench.schemas.workflow_graph import WorkflowGraph


# ---------------------------------------------------------------------------
# Gold Trajectory schema (tool_use_scorer_spec.md §2)
# ---------------------------------------------------------------------------


class GoldStep(BaseModel):
    """One expected tool call in a canonical solution trajectory."""

    step: int
    tool: str
    method: str
    required_args: dict[str, Any] = Field(default_factory=dict)
    optional_args: dict[str, Any] = Field(default_factory=dict)
    rationale: str = ""


class OrderedPair(BaseModel):
    """A pairwise safety-critical ordering constraint for sequence_penalty scoring."""

    before: str
    after: str
    operation: str
    severity: Literal["hard_fail", "penalty"]
    rationale: str = ""


class GoldTrajectory(BaseModel):
    """Canonical expected tool-call sequence for a task (used by ToolUseScorer)."""

    description: str = ""
    steps: list[GoldStep]
    ordered_required_pairs: list[OrderedPair] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Hybrid-scorer data models (ComponentSpec + HybridScoringConfig)
# These are embedded in TaskSpec when tasks use the hybrid scoring path.
# ---------------------------------------------------------------------------


class ComponentSpec(BaseModel):
    """One scorable component of a deterministic task.

    A deterministic task is decomposed into components (e.g. individual tool
    outputs) each evaluated in isolation.  ``upstream_deps`` lists the
    ``component_id`` values that must be correct before this component's
    Cascading-Failure Score (CFS) propagates.
    """

    component_id: str
    ground_truth: dict[str, Any]
    weight: float = 1.0
    tolerance_pct: float = 5.0
    match_type: Literal["exact", "numeric", "set"] = "numeric"
    upstream_deps: list[str] = Field(default_factory=list)


class HybridScoringConfig(BaseModel):
    """Hybrid scoring configuration embedded in a TaskSpec.

    ``scoring_mode`` selects the evaluation path:
    - ``"deterministic"`` — three-tier execution metrics (CS / CFS / SR).
    - ``"rubric"``        — LLM-judge with hierarchical rubric (+ optional GSB).
    """

    scoring_mode: Literal["deterministic", "rubric"]

    # --- Deterministic path ---
    components: list[ComponentSpec] = Field(default_factory=list)

    # --- Rubric path ---
    rubric_id: Optional[str] = None
    task_context: Optional[str] = None          # HPC snapshot summary injected into judge prompt
    baseline_answers: list[str] = Field(default_factory=list)  # for GSB; empty → α=1.0
    alpha: float = 0.6                           # rubric weight; 1-α goes to GSB

Role = Literal["scientific_user", "sysadmin", "facility_admin", "researcher", "system_designer"]
QCat = Literal["JOB", "PERF", "DATA", "MON", "ENERGY", "SEC", "FAC", "ARCH", "AIOPS", "DOCS"]
Difficulty = Literal["easy", "medium", "hard", "adversarial"]
DifficultyTier = Literal[1, 2, 3]

# Mapping from Difficulty label to expected DifficultyTier integer
_DIFFICULTY_TO_TIER: dict[str, int] = {
    "easy": 1,
    "medium": 2,
    "hard": 3,
    "adversarial": 3,
}

# Knowledge source codes — aligned with docs/taxonomy/05_knowledge_sources.md
KnowledgeSourceCode = Literal[
    "ARCH_DOC",   # System architecture & hardware docs (specs, rack layouts, BoM)
    "OPS_DOC",    # Sysadmin & operations manuals (queue config, RBAC, maintenance)
    "FAC_DOC",    # Facility & infrastructure docs (cooling diagrams, BMS config)
    "USR_DOC",    # User documentation & help resources (guides, batch templates)
    "DATA_GOV",   # Data management & governance policies (retention, GDPR)
    "POLICY",     # Organizational & policy documents (AUP, SLA, security policy)
    "ADMIN_DATA", # Administrative & org data (allocations, billing, contracts)
    "WIKI",       # Knowledge base / wiki / portal content (FAQs, how-tos)
    "REF_STD",    # Reference standards, setpoints & config tables (ASHRAE, SLURM cfg)
    "ENG_DOC",    # Design, engineering & upgrade documents (RFPs, SATs, RFCs)
]
# Capability codes — aligned with docs/taxonomy/03_capabilities.md
Capability = Literal[
    "retrieval_grounding",        # cite and ground answers in knowledge sources
    "telemetry_querying",         # formulate metric, log, and event queries
    "cross_source_fusion",        # combine docs with telemetry; correlate multi-modal signals
    "diagnostic_reasoning",       # generate hypotheses; rank likely causes
    "optimization_recommendation",# propose performance/energy improvements; quantify trade-offs
    "role_aware_response",        # adapt scope, tone, detail to persona
    "permission_compliance",      # enforce RBAC and tier constraints; refuse/redact as needed
    "incident_handling",          # triage alerts; propose escalation and containment
    "energy_awareness",           # reason about power, thermals, PUE; sustainability actions
    "action_planning",            # propose step-by-step plans; decide tool order
]

# Access tier — aligned with docs/taxonomy/04_access_control.md
AccessTier = Literal[
    "tier1_public",      # Safe, non-sensitive; no approval needed (normal users, docs)
    "tier2_privileged",  # Elevated credentials required (real telemetry, admin ops)
    "tier3_restricted",  # Read-only observational access (energy dashboards, facility KPIs)
    "tier4_sensitive",   # Confidential; approval + isolation (procurement, cybersecurity)
]

AnswerType = Literal[
    "diagnosis", "comparison", "lookup", "action", "explanation",
    "numeric", "summary", "factoid",
    "job_id",    # N1: integer job ID (strip leading zeros)
    "node_list", # N2: SLURM bracket notation or comma-separated node names
    "value",         # v0.2: single numeric or categorical value answer
    "list",          # v0.2: enumerated list of items
    "recommendation", # v0.2: actionable recommendation
]
ValidationStatus = Literal["not_started", "in_review", "validated", "rejected"]
ScoringReadiness = Literal["blocked", "partial", "ready"]
BenchmarkSplit = Literal["dev", "test", "public_test", "hidden_test"]


class ExpectedToolCall(BaseModel):
    """One entry in a task's ground-truth tool-call sequence.

    Used by the decomposed ToolUseScorer to check:

    - ``tool_name``     — which tool the agent should call at this step
    - ``required_args`` — argument key-value pairs that must be present **and**
                          match in the actual call (string: exact match,
                          number: ±5% tolerance).  An empty dict means any
                          call to the right tool name scores full argument credit.

    Example::

        {"tool_name": "slurm",   "required_args": {"method": "job_details", "job_id": "891234"}}
        {"tool_name": "docs",    "required_args": {"method": "search"}}
        {"tool_name": "telemetry", "required_args": {}}
    """

    tool_name: str
    required_args: dict[str, Any] = Field(default_factory=dict)


class EvalCriteria(BaseModel):
    """Correctness check criteria embedded in a task spec."""

    evaluation_mode: Literal[
        "exact_match", "numeric_tolerance", "structured_output",
        "semantic_match", "policy_evaluation", "trace_sensitive",
        "numeric_match",  # v0.2: numeric answer with tolerance field in gold_answer text
    ] = "semantic_match"
    gold_answer: Optional[str] = None
    numeric_tolerance: Optional[float] = None
    required_evidence_refs: list[str] = Field(default_factory=list)

    # Ordered ground-truth tool-call sequence for decomposed tool-use scoring.
    # When non-empty, ToolUseScorer switches to decomposed mode:
    # selection_score + argument_score + sequence_score + forbidden_call_penalty.
    # When empty (default), the legacy heuristic mode is used instead.
    expected_tool_sequence: list[ExpectedToolCall] = Field(default_factory=list)


class TaskSpec(BaseModel):
    """Fully-specified benchmark task item."""

    model_config = {"extra": "ignore"}

    # Identity
    task_id: str
    legacy_query_id: Optional[str] = None
    title: str

    # Task content
    query_text: str
    role: Role
    qcat: QCat
    difficulty: Difficulty
    difficulty_tier: Optional[DifficultyTier] = None   # 1=single-lookup, 2=multi-step, 3=complex

    # Environment linkage
    environment_id: str

    # Evidence and correctness
    gold_evidence_refs: list[str] = Field(default_factory=list)
    expected_answer_type: AnswerType
    eval_criteria: Optional[EvalCriteria] = None

    # Knowledge sources permitted as evidence for this task
    knowledge_source_scope: list[KnowledgeSourceCode] = Field(default_factory=list)

    # Capabilities required to answer this task correctly
    required_capabilities: list[Capability] = Field(default_factory=list)

    # Minimum access tier the agent must hold to answer this task
    access_tier: AccessTier = "tier1_public"

    # Agent persona username (e.g. "alice") — used by GovernanceScorer for
    # cross_user_reference dangerous_arg checks.
    agent_user: Optional[str] = None

    # Tool and access constraints
    allowed_tools: Optional[list[str]] = None
    expected_tool_calls: Optional[set[str]] = None
    # Tool names the agent must invoke for engagement-aware CuP (§15).
    # Absent or empty → v0.1 CuP behaviour (no engagement gate).
    hard_fail_conditions: list[str] = Field(default_factory=list)

    # Scoring configuration
    aggregate_weight_profile: str = "default_hpc_v01"

    # Hybrid scoring (optional — when set, OutcomeScorer delegates to HybridScorer)
    hybrid_scoring: Optional[HybridScoringConfig] = None

    # Ground-truth workflow graph for WorfEval scoring (WorfBench §6).
    # When present, WorkflowScorer produces a WorfEvalScore for each run.
    # When absent, WorkflowScorer is skipped.
    ground_truth_workflow: Optional[WorkflowGraph] = None

    # Gold trajectory for tool-use sequence scoring (tool_use_scorer_spec.md §2).
    # When present, ToolUseScorer computes node_f1, ned, step_accuracy, sequence_penalty.
    # When absent, all four new metrics are None.
    gold_trajectory: Optional[GoldTrajectory] = None

    # Lifecycle
    benchmark_split: Optional[BenchmarkSplit] = None
    validation_status: ValidationStatus = "not_started"
    scoring_readiness: ScoringReadiness = "blocked"

    # Contamination tracking (task_lite_spec.md §5.2)
    task_creation_date: Optional[str] = None          # ISO 8601
    contamination_risk: Optional[Literal["clean", "elevated", "unknown"]] = None

    # T1–T10 validity gate (task_lite_spec.md §3.1)
    t1_t10_pass: Optional[bool] = None
    t1_t10_audit_date: Optional[str] = None           # ISO 8601

    # Authoring pipeline fields
    oracle_program: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Ordered list of tool calls that reproduce the gold answer (required for deterministic tasks).",
    )
    difficulty_justification: Optional[str] = Field(
        default=None,
        description="One-sentence defence of the difficulty tier (e.g. number of tool calls, branching factor).",
    )
    independence_attestation: Optional[dict[str, Any]] = Field(
        default=None,
        description="Stage E independence audit result: static_dup_check, nearest_existing_task, rationale.",
    )

    @model_validator(mode="after")
    def _check_difficulty_tier_consistency(self) -> "TaskSpec":
        if self.difficulty_tier is None:
            return self
        expected = _DIFFICULTY_TO_TIER.get(self.difficulty)
        if expected is not None and self.difficulty_tier != expected:
            raise ValueError(
                f"difficulty_tier={self.difficulty_tier} is inconsistent with "
                f"difficulty={self.difficulty!r} (expected {expected})"
            )
        return self


# ---------------------------------------------------------------------------
# HPC Task Set v1 schema (§8 of hpc_task_set_spec.md)
# ---------------------------------------------------------------------------

HPCDataType = Literal["job_ops", "node_ops", "telemetry", "energy", "dataflow", "rbac"]
HPCWorkloadType = Literal["OLAP", "OLTP"]
HPCTemporalType = Literal["retrospective", "prospective"]
HPCScoringMode = Literal["deterministic", "rubric"]
HPCRole = Literal["scientific_user", "researcher", "sysadmin", "facility_admin", "system_designer"]


class HPCRoleVariant(BaseModel):
    """Expected answer and visible data scope for a specific role."""

    expected_answer: str
    visible_data: list[str] = Field(default_factory=list)


class HPCGroundTruth(BaseModel):
    """Ground-truth values for deterministic HPC tasks.

    Uses ``extra = "allow"`` so that per-task fields (e.g. ``job_state``,
    ``peak_mem_pct``, ``node_count``) can be declared freely without a rigid
    schema — the data type dictates what fields appear.
    """

    model_config = {"extra": "allow"}

    # T8: comparison mode for ambiguity check
    comparison_mode: Optional[Literal["exact", "set_equal", "numeric_tolerance", "regex"]] = None
    # T3: machine-executable derivation query against snapshot
    derivation_query: Optional[str] = None


class HPCCheckpointDef(BaseModel):
    """Checkpoint definition embedded in an HPC task spec.

    Each checkpoint has a unique ID, a natural-language description, one of
    four deterministic evaluator types, and evaluator-specific parameters.
    """

    checkpoint_id: str
    description: str
    evaluator: Literal[
        "tool_call_present",       # trace contains named tool call + optional conditions
        "response_contains_gt",    # agent response references a ground-truth value
        "no_forbidden_calls",      # no forbidden tool names appear in trace
        "tool_call_with_metric",   # tool call includes a specific metric_type keyword
    ]
    evaluator_params: dict[str, Any] = Field(default_factory=dict)


class HPCTaskSpec(BaseModel):
    """HPC task set v1 task definition (hpc_task_set_spec.md §8)."""

    task_id: str
    question: str
    data_type: HPCDataType
    workload_type: HPCWorkloadType
    temporal: HPCTemporalType
    scoring_mode: HPCScoringMode
    rubric_id: Optional[str] = None
    difficulty: Difficulty
    difficulty_tier: Optional[DifficultyTier] = None   # 1=single-lookup, 2=multi-step, 3=complex
    role_variants: dict[str, HPCRoleVariant] = Field(default_factory=dict)
    snapshot_id: str
    required_tools: list[str] = Field(default_factory=list)
    ground_truth: Optional[HPCGroundTruth] = None
    tolerance_pct: float = 5.0
    # Taxonomy labels from spec §3.2
    visible_to_roles: list[str] = Field(default_factory=list)
    # Checkpoint definitions for partial-completion scoring (checkpoint_scorer_spec.md)
    checkpoints: Optional[list[HPCCheckpointDef]] = None
    # T5: ground-truth files excluded from agent context (diagnostic tasks)
    ground_truth_files_excluded: list[str] = Field(default_factory=list)
    # T8: temporal anchor — must be "snapshot_timestamp" for relative-time tasks
    temporal_anchor: Optional[str] = None
    # Gold trajectory for tool-use sequence scoring (tool_use_scorer_spec.md §2).
    gold_trajectory: Optional[GoldTrajectory] = None

    # Contamination tracking (task_lite_spec.md §5.2)
    task_creation_date: Optional[str] = None          # ISO 8601
    contamination_risk: Optional[Literal["clean", "elevated", "unknown"]] = None

    # T1–T10 validity gate (task_lite_spec.md §3.1)
    t1_t10_pass: Optional[bool] = None
    t1_t10_audit_date: Optional[str] = None           # ISO 8601

    @model_validator(mode="after")
    def _check_hpc_difficulty_tier_consistency(self) -> "HPCTaskSpec":
        if self.difficulty_tier is None:
            return self
        expected = _DIFFICULTY_TO_TIER.get(self.difficulty)
        if expected is not None and self.difficulty_tier != expected:
            raise ValueError(
                f"difficulty_tier={self.difficulty_tier} is inconsistent with "
                f"difficulty={self.difficulty!r} (expected {expected})"
            )
        return self
