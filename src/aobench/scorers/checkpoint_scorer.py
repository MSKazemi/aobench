"""Checkpoint scorer — partial-completion scoring via trace-based checkpoint evaluation.

Implements the S_partial formula from TheAgentCompany (Xu et al. 2024):

    S_partial = 0.5 * (checkpoints_passed / checkpoints_total) + 0.5 * S_full

Each checkpoint is evaluated deterministically against the agent's execution trace
using one of four evaluator types: tool_call_present, response_contains_gt,
no_forbidden_calls, tool_call_with_metric.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Literal

from aobench.schemas.result import CheckpointResult
from aobench.schemas.trace import TraceStep

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CheckpointSpec dataclass
# ---------------------------------------------------------------------------


@dataclass
class CheckpointSpec:
    """Evaluator-facing checkpoint definition.

    Built from HPCCheckpointDef (task schema) by the aggregate scorer.
    """

    checkpoint_id: str
    description: str
    evaluator: Literal[
        "tool_call_present",
        "response_contains_gt",
        "no_forbidden_calls",
        "tool_call_with_metric",
    ]
    evaluator_params: dict[str, Any] = field(default_factory=dict)
    pass_condition: str = ""   # human-readable; used for logging only
    qcat: str = ""             # QCAT category; used for logging only


# ---------------------------------------------------------------------------
# Private evaluator functions
# ---------------------------------------------------------------------------


def _eval_tool_call_present(
    steps: list[TraceStep],
    params: dict[str, Any],
) -> tuple[bool, str | None]:
    """Pass if the trace contains a call to ``tool_name`` satisfying all conditions."""
    tool_name: str = params.get("tool_name", "")
    required_status: str | None = params.get("required_status")
    required_field: str | None = params.get("required_field")
    required_value: Any = params.get("required_value")
    require_nonempty_result: bool = params.get("require_nonempty_result", False)

    for step in steps:
        tc = step.tool_call
        if tc is None or tc.tool_name != tool_name:
            continue

        obs_content = step.observation.content if step.observation else None

        # Check required_status in observation content (dict key "status")
        if required_status is not None:
            if not isinstance(obs_content, dict):
                continue
            if obs_content.get("status") != required_status:
                continue

        # Check required_field + required_value in observation content
        if required_field is not None and required_value is not None:
            if not isinstance(obs_content, dict):
                continue
            if obs_content.get(required_field) != required_value:
                continue

        # Check that observation content is non-empty
        if require_nonempty_result:
            if not obs_content:
                continue

        evidence = f"tool_call {tool_name!r} at step {step.step_id}"
        return True, evidence

    return False, None


def _eval_response_contains_gt(
    agent_response: str,
    ground_truth: dict[str, Any],
    params: dict[str, Any],
    tolerance_pct: float,
) -> tuple[bool, str | None]:
    """Pass if the agent response contains a value matching ``ground_truth[gt_key]``.

    - Numeric values: pass when any number in the response is within ``tolerance_pct``
      of the ground-truth value.
    - List values: pass when any element of the list appears in the response.
    - String values: pass when the string appears (case-insensitive) in the response.
    """
    gt_key: str | None = params.get("gt_key")
    if not gt_key or ground_truth is None:
        return False, None

    gt_value = ground_truth.get(gt_key)
    if gt_value is None:
        logger.debug("response_contains_gt: key %r not in ground_truth", gt_key)
        return False, None

    if isinstance(gt_value, (int, float)):
        numbers = re.findall(r"-?\d+(?:\.\d+)?", agent_response)
        tol = tolerance_pct / 100.0
        for num_str in numbers:
            num = float(num_str)
            denom = max(abs(float(gt_value)), 1e-9)
            if abs(num - float(gt_value)) / denom <= tol:
                return True, f"numeric match: {num} ≈ {gt_value} (tol {tolerance_pct}%)"
        return False, None

    if isinstance(gt_value, list):
        for item in gt_value:
            if str(item).lower() in agent_response.lower():
                return True, f"list item {item!r} found in response"
        return False, None

    # String match
    if str(gt_value).lower() in agent_response.lower():
        return True, f"string {gt_value!r} found in response"
    return False, None


def _eval_no_forbidden_calls(
    steps: list[TraceStep],
    params: dict[str, Any],
) -> tuple[bool, str | None]:
    """Pass if no step invokes any tool in ``forbidden_tool_names``."""
    forbidden: list[str] = params.get("forbidden_tool_names", [])
    for step in steps:
        tc = step.tool_call
        if tc is not None and tc.tool_name in forbidden:
            return False, f"forbidden call to {tc.tool_name!r} at step {step.step_id}"
    return True, "no forbidden calls detected"


def _eval_tool_call_with_metric(
    steps: list[TraceStep],
    params: dict[str, Any],
) -> tuple[bool, str | None]:
    """Pass if trace contains a call to ``tool_name`` whose arguments include a
    ``metric_type`` (or ``metric``) field containing ``metric_type_contains``."""
    tool_name: str = params.get("tool_name", "")
    metric_type_contains: str = params.get("metric_type_contains", "")

    for step in steps:
        tc = step.tool_call
        if tc is None or tc.tool_name != tool_name:
            continue
        args = tc.arguments or {}
        metric_field = str(args.get("metric_type", "") or args.get("metric", ""))
        if metric_type_contains.lower() in metric_field.lower():
            evidence = (
                f"tool_call {tool_name!r} with metric_type={metric_field!r}"
                f" at step {step.step_id}"
            )
            return True, evidence

    return False, None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def evaluate_checkpoints(
    task_checkpoints: list[CheckpointSpec],
    trace: list[TraceStep],
    agent_response: str,
    ground_truth: dict[str, Any],
    tolerance_pct: float = 5.0,
) -> list[CheckpointResult]:
    """Evaluate all checkpoints for a task against the run trace.

    Returns one ``CheckpointResult`` per checkpoint (order preserved).
    If ``trace`` is empty, all checkpoints fail and are logged as ``trace_missing``.
    """
    if not trace:
        logger.warning("evaluate_checkpoints: trace is empty — all checkpoints fail (trace_missing)")
        return [
            CheckpointResult(checkpoint_id=cp.checkpoint_id, passed=False, evidence="trace_missing")
            for cp in task_checkpoints
        ]

    results: list[CheckpointResult] = []
    for cp in task_checkpoints:
        try:
            passed, evidence = _dispatch_evaluator(cp, trace, agent_response, ground_truth, tolerance_pct)
        except Exception as exc:  # noqa: BLE001
            logger.warning("checkpoint %r evaluator error: %s", cp.checkpoint_id, exc)
            passed, evidence = False, f"evaluator_error: {exc}"

        results.append(CheckpointResult(checkpoint_id=cp.checkpoint_id, passed=passed, evidence=evidence))

    return results


def _dispatch_evaluator(
    cp: CheckpointSpec,
    trace: list[TraceStep],
    agent_response: str,
    ground_truth: dict[str, Any],
    tolerance_pct: float,
) -> tuple[bool, str | None]:
    if cp.evaluator == "tool_call_present":
        return _eval_tool_call_present(trace, cp.evaluator_params)
    if cp.evaluator == "response_contains_gt":
        return _eval_response_contains_gt(agent_response, ground_truth, cp.evaluator_params, tolerance_pct)
    if cp.evaluator == "no_forbidden_calls":
        return _eval_no_forbidden_calls(trace, cp.evaluator_params)
    if cp.evaluator == "tool_call_with_metric":
        return _eval_tool_call_with_metric(trace, cp.evaluator_params)
    raise ValueError(f"unknown evaluator type: {cp.evaluator!r}")


def compute_s_partial(
    checkpoint_results: list[CheckpointResult],
    s_full: float,
) -> float:
    """Compute partial completion score.

    S_partial = 0.5 * (passed / total) + 0.5 * S_full

    If ``checkpoint_results`` is empty, returns ``s_full`` unchanged (no checkpoint data).
    """
    if not checkpoint_results:
        return s_full
    passed = sum(1 for cr in checkpoint_results if cr.passed)
    total = len(checkpoint_results)
    return round(0.5 * (passed / total) + 0.5 * s_full, 6)


def score_checkpoint_run(
    task_id: str,
    task_checkpoints: list[CheckpointSpec],
    trace: list[TraceStep],
    agent_response: str,
    ground_truth: dict[str, Any],
    outcome: float,
    pass_threshold: float = 0.5,
    tolerance_pct: float = 5.0,
) -> tuple[list[CheckpointResult], float, float]:
    """Full checkpoint evaluation for one run.

    Args:
        task_id:          Identifier used for logging.
        task_checkpoints: List of CheckpointSpec for the task.
        trace:            Execution trace steps.
        agent_response:   Agent's final answer / last response text.
        ground_truth:     Task ground-truth dict (for response_contains_gt evaluator).
        outcome:          Raw outcome score from the hybrid scorer (0–1).
        pass_threshold:   Threshold above which ``outcome`` counts as S_full = 1.
        tolerance_pct:    Numeric tolerance for ground-truth matching.

    Returns:
        (checkpoint_results, s_partial, s_full)
    """
    s_full = 1.0 if outcome >= pass_threshold else 0.0

    if not task_checkpoints:
        logger.debug("score_checkpoint_run: task %s has no checkpoints", task_id)
        return [], outcome, s_full

    checkpoint_results = evaluate_checkpoints(
        task_checkpoints,
        trace=trace,
        agent_response=agent_response,
        ground_truth=ground_truth,
        tolerance_pct=tolerance_pct,
    )
    s_partial = compute_s_partial(checkpoint_results, s_full)

    n_passed = sum(1 for cr in checkpoint_results if cr.passed)
    logger.debug(
        "score_checkpoint_run: task=%s checkpoints=%d/%d s_partial=%.4f s_full=%.1f",
        task_id, n_passed, len(checkpoint_results), s_partial, s_full,
    )
    return checkpoint_results, s_partial, s_full
