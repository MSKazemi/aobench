"""Deterministic scorer — three-tier execution metrics (CS / CFS / SR).

Implements the Component Score (CS), Cascading Failure Score (CFS), and
Success Rate (SR) metrics from DAComp (Lei et al. 2025, arXiv:2512.04324).

- CS   : partial-credit isolated evaluation of each component.
- CFS  : cascading — a component's score is nullified if any upstream is wrong.
- SR   : strict all-or-nothing; 1 only when every component matches.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from exabench.schemas.task import ComponentSpec


@dataclass
class ComponentResult:
    component_id: str
    match: bool
    expected: Any
    actual: Any
    tolerance_pct: float
    deviation_pct: float | None = None  # None for non-numeric / exact comparisons


@dataclass
class DeterministicResult:
    cs: float               # 0–100 — Component Score (partial credit, isolated)
    cfs: float              # 0–100 — Cascading Failure Score (dependency-propagated)
    sr: int                 # 0 or 1 — Success Rate (strict all-or-nothing)
    outcome: float          # SR normalised to [0, 1] (for CLEAR Efficacy)
    component_results: list[ComponentResult] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Internal matching helpers
# ---------------------------------------------------------------------------

def _numeric_match(actual: Any, expected: Any, tolerance_pct: float) -> tuple[bool, float | None]:
    """Try to compare actual vs expected as floats with a relative tolerance band.

    Returns (matched, deviation_pct).  deviation_pct is None for non-numeric comparisons.
    """
    try:
        a = float(actual)
        e = float(expected)
    except (TypeError, ValueError):
        return False, None

    if e == 0:
        matched = math.isclose(a, e, abs_tol=tolerance_pct / 100.0)
        dev = abs(a - e) * 100.0
    else:
        dev = abs(a - e) / abs(e) * 100.0
        matched = dev <= tolerance_pct
    return matched, round(dev, 4)


def _set_match(actual: Any, expected: Any) -> bool:
    """Check set equality (order-independent)."""
    try:
        return set(actual) == set(expected)
    except TypeError:
        return actual == expected


def _match_component(
    actual_output: dict[str, Any],
    spec: ComponentSpec,
) -> ComponentResult:
    """Evaluate one component against its ground truth.

    Iterates over every key in ``ground_truth`` and applies the matching
    rule determined by ``spec.match_type``.  All keys must match for the
    component to be considered correct.
    """
    gt = spec.ground_truth
    matched_all = True
    worst_dev: float | None = None

    for key, expected_val in gt.items():
        actual_val = actual_output.get(key)
        if actual_val is None:
            matched_all = False
            break

        if spec.match_type == "exact":
            # Try numeric first, fall back to string comparison
            num_match, dev = _numeric_match(actual_val, expected_val, spec.tolerance_pct)
            if dev is not None:
                key_ok = num_match
                if dev is not None:
                    worst_dev = max(worst_dev or 0.0, dev)
            else:
                key_ok = str(actual_val).strip().lower() == str(expected_val).strip().lower()
        elif spec.match_type == "numeric":
            key_ok, dev = _numeric_match(actual_val, expected_val, spec.tolerance_pct)
            if dev is not None:
                worst_dev = max(worst_dev or 0.0, dev)
        elif spec.match_type == "set":
            key_ok = _set_match(actual_val, expected_val)
        else:
            key_ok = actual_val == expected_val

        if not key_ok:
            matched_all = False
            break

    return ComponentResult(
        component_id=spec.component_id,
        match=matched_all,
        expected=gt,
        actual={k: actual_output.get(k) for k in gt},
        tolerance_pct=spec.tolerance_pct,
        deviation_pct=worst_dev,
    )


# ---------------------------------------------------------------------------
# Public scoring function
# ---------------------------------------------------------------------------

def deterministic_score(
    agent_output: dict[str, Any],
    components: list[ComponentSpec],
) -> DeterministicResult:
    """Compute CS, CFS, and SR for a multi-component task.

    Args:
        agent_output: Mapping of component_id → component output dict.
        components:   List of ComponentSpec definitions for the task.

    Returns:
        DeterministicResult with cs, cfs, sr, outcome, and per-component details.
    """
    if not components:
        return DeterministicResult(cs=0.0, cfs=0.0, sr=0, outcome=0.0)

    # Build a lookup for quick spec access
    spec_by_id: dict[str, ComponentSpec] = {s.component_id: s for s in components}

    # --- Step 1: Evaluate each component in isolation (for CS) ---
    component_results: dict[str, ComponentResult] = {}
    match_flags: dict[str, bool] = {}

    for spec in components:
        comp_output = agent_output.get(spec.component_id, {})
        result = _match_component(comp_output, spec)
        component_results[spec.component_id] = result
        match_flags[spec.component_id] = result.match

    # --- Step 2: Compute CS (isolated, partial credit) ---
    total_weight = sum(s.weight for s in components)
    if total_weight == 0:
        total_weight = 1.0

    cs_numerator = sum(
        s.weight * (1.0 if match_flags[s.component_id] else 0.0)
        for s in components
    )
    cs = round(100.0 * cs_numerator / total_weight, 4)

    # --- Step 3: Compute CFS (cascading) ---
    # cfs_scores[cid] = m_cid * product(cfs_scores[anc] for anc in ancestors)
    cfs_scores: dict[str, float] = {}

    def _cfs(cid: str) -> float:
        if cid in cfs_scores:
            return cfs_scores[cid]
        own_match = 1.0 if match_flags.get(cid, False) else 0.0
        spec = spec_by_id[cid]
        ancestor_product = 1.0
        for dep in spec.upstream_deps:
            ancestor_product *= _cfs(dep)
        cfs_scores[cid] = own_match * ancestor_product
        return cfs_scores[cid]

    for spec in components:
        _cfs(spec.component_id)

    cfs_numerator = sum(s.weight * cfs_scores[s.component_id] for s in components)
    cfs = round(100.0 * cfs_numerator / total_weight, 4)

    # --- Step 4: SR (strict all-or-nothing) ---
    sr = 1 if all(match_flags.values()) else 0

    return DeterministicResult(
        cs=cs,
        cfs=cfs,
        sr=sr,
        outcome=float(sr),
        component_results=list(component_results.values()),
    )
