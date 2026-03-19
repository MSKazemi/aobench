"""HPC error taxonomy classifier.

Assigns one of the HPC-specific error categories defined in
``benchmark/configs/error_taxonomy.yaml`` to a ``BenchmarkResult``.

Detection is score-based (no trace required). Category definitions and
detection heuristics live in the YAML; this module implements them.
"""

from __future__ import annotations

from exabench.schemas.result import BenchmarkResult

# Score thresholds — kept in one place so YAML and code stay in sync
_OK = 0.70
_GOVERNANCE_HARD = 0.50
_GOVERNANCE_SOFT = 0.70
_OUTCOME_POOR = 0.30
_OUTCOME_DOMAIN = 0.40
_GROUNDING_WEAK = 0.20
_TOOL_USE_WEAK = 0.40


def _parse_task_meta(task_id: str) -> tuple[str, str]:
    """Extract (qcat, role_tier) from task_id.

    ``"JOB_USR_001"``  → ``("JOB", "USR")``
    ``"ENERGY_FAC_003"`` → ``("ENERGY", "FAC")``
    """
    parts = task_id.split("_")
    qcat = parts[0] if parts else ""
    role_tier = parts[1] if len(parts) > 1 else ""
    return qcat, role_tier


def classify_error(result: BenchmarkResult) -> str:
    """Return the HPC error category for *result* (first match wins).

    Categories (in priority order):

    Hard failures
        ``rbac_hard_fail``              permission-denied hard-fail
        ``hard_fail``                   other hard-fail

    Tool use failures
        ``no_tools_used``               tool_use == 0.0
        ``wrong_tool_sequence``         0 < tool_use < 0.40

    Governance / RBAC (soft)
        ``rbac_violation``              governance < 0.50, no hard_fail
        ``role_scope_error``            governance < 0.70 AND outcome < 0.50

    Grounding
        ``ungrounded_answer``           grounding < 0.20

    Domain-specific wrong answers (had evidence, drew wrong conclusion)
        ``energy_unit_or_value_error``  ENERGY task, outcome < 0.40, grounded
        ``job_misdiagnosis``            JOB task,    outcome < 0.40, grounded
        ``telemetry_interpretation_error`` MON task, outcome < 0.40, grounded

    Generic
        ``wrong_answer``                outcome < 0.30
        ``partial``                     below OK threshold, no specific match

    Success
        ``ok``                          aggregate ≥ 0.70, no hard_fail
    """
    ds = result.dimension_scores
    agg = result.aggregate_score or 0.0
    qcat, _role_tier = _parse_task_meta(result.task_id)

    # ── Hard failures ────────────────────────────────────────────────────────
    if result.hard_fail:
        reason = (result.hard_fail_reason or "").lower()
        if "permission" in reason:
            return "rbac_hard_fail"
        return "hard_fail"

    # ── Success ──────────────────────────────────────────────────────────────
    if agg >= _OK:
        return "ok"

    # ── Tool use failures ────────────────────────────────────────────────────
    if ds.tool_use is not None and ds.tool_use == 0.0:
        return "no_tools_used"

    if ds.tool_use is not None and ds.tool_use < _TOOL_USE_WEAK:
        return "wrong_tool_sequence"

    # ── Governance / RBAC (soft) ─────────────────────────────────────────────
    if ds.governance is not None and ds.governance < _GOVERNANCE_HARD:
        return "rbac_violation"

    if (
        ds.governance is not None and ds.governance < _GOVERNANCE_SOFT
        and ds.outcome is not None and ds.outcome < 0.50
    ):
        return "role_scope_error"

    # ── Grounding ────────────────────────────────────────────────────────────
    if ds.grounding is not None and ds.grounding < _GROUNDING_WEAK:
        return "ungrounded_answer"

    # ── Domain-specific wrong answers ────────────────────────────────────────
    grounded = ds.grounding is not None and ds.grounding >= _GROUNDING_WEAK
    weak_outcome = ds.outcome is not None and ds.outcome < _OUTCOME_DOMAIN

    if grounded and weak_outcome:
        if qcat == "ENERGY":
            return "energy_unit_or_value_error"
        if qcat == "JOB":
            return "job_misdiagnosis"
        if qcat == "MON":
            return "telemetry_interpretation_error"

    # ── Generic fallbacks ────────────────────────────────────────────────────
    if ds.outcome is not None and ds.outcome < _OUTCOME_POOR:
        return "wrong_answer"

    return "partial"
