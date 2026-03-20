"""Unit tests for CLEAR metrics in exabench.reports.clear_report."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from exabench.reports.clear_report import (
    build_clear_report,
    compute_assurance_rate,
    compute_cna,
    compute_cps,
    compute_clear_scores,
    normalise_min_max,
)
from exabench.schemas.result import BenchmarkResult, DimensionScores


# ── helpers ───────────────────────────────────────────────────────────────────


def _make_result(
    *,
    task_id: str = "TASK_001",
    model_name: str = "test-model",
    aggregate_score: float | None = 0.8,
    outcome: float | None = 0.8,
    governance: float | None = 0.9,
    cost_usd: float | None = 0.01,
    latency_s: float | None = 5.0,
    rbac_compliant: bool = True,
) -> BenchmarkResult:
    return BenchmarkResult(
        result_id="r1",
        run_id="run1",
        task_id=task_id,
        role="sysadmin",
        environment_id="env_01",
        adapter_name="test",
        model_name=model_name,
        rbac_compliant=rbac_compliant,
        dimension_scores=DimensionScores(
            outcome=outcome,
            governance=governance,
        ),
        aggregate_score=aggregate_score,
        cost_estimate_usd=cost_usd,
        latency_seconds=latency_s,
        timestamp=datetime.now(tz=timezone.utc),
    )


# ── compute_cna ───────────────────────────────────────────────────────────────


def test_compute_cna_normal():
    result = _make_result(outcome=0.8, cost_usd=0.01)
    cna = compute_cna(result)
    assert cna == pytest.approx(8000.0, rel=1e-6)


def test_compute_cna_zero_cost():
    result = _make_result(outcome=0.8, cost_usd=0.0)
    assert compute_cna(result) is None


def test_compute_cna_missing_cost():
    result = _make_result(outcome=0.8, cost_usd=None)
    assert compute_cna(result) is None


def test_compute_cna_missing_outcome():
    result = _make_result(outcome=None, cost_usd=0.01)
    assert compute_cna(result) is None


# ── compute_cps ───────────────────────────────────────────────────────────────


def test_compute_cps_normal():
    # 10 results, 7 passing, total_cost=$0.08 → CPS = 0.08/7 ≈ 0.01143
    results = [
        _make_result(aggregate_score=0.8 if i < 7 else 0.3, cost_usd=0.008)
        for i in range(10)
    ]
    cps = compute_cps(results, pass_threshold=0.5)
    assert cps == pytest.approx(0.08 / 7, rel=1e-5)


def test_compute_cps_all_passing():
    results = [_make_result(aggregate_score=0.9, cost_usd=0.01) for _ in range(5)]
    cps = compute_cps(results, pass_threshold=0.5)
    assert cps == pytest.approx(0.05 / 5, rel=1e-6)


def test_compute_cps_no_successes():
    results = [_make_result(aggregate_score=0.1, cost_usd=0.01) for _ in range(5)]
    assert compute_cps(results, pass_threshold=0.5) is None


def test_compute_cps_missing_cost():
    # cost=None results still count towards n_successful; total_cost=0
    results = [_make_result(aggregate_score=0.9, cost_usd=None) for _ in range(3)]
    cps = compute_cps(results, pass_threshold=0.5)
    assert cps == pytest.approx(0.0, abs=1e-9)


# ── normalise_min_max ─────────────────────────────────────────────────────────


def test_normalise_min_max_no_invert():
    values = [0.0, 0.5, 1.0]
    result = normalise_min_max(values, invert=False)
    assert result == [0.0, 0.5, 1.0]


def test_normalise_min_max_invert():
    # [0.01, 0.05, 0.10] inverted → [1.0, ~0.5556, 0.0]
    values = [0.01, 0.05, 0.10]
    result = normalise_min_max(values, invert=True)
    assert result[0] == pytest.approx(1.0, abs=1e-4)
    assert result[1] == pytest.approx(1.0 - (0.05 - 0.01) / (0.10 - 0.01), abs=1e-3)
    assert result[2] == pytest.approx(0.0, abs=1e-4)


def test_normalise_all_equal():
    # All equal → all 1.0 (no spread, treated as perfect)
    result = normalise_min_max([0.05, 0.05, 0.05], invert=True)
    assert result == [1.0, 1.0, 1.0]


def test_normalise_min_max_with_none():
    values = [0.0, None, 1.0]
    result = normalise_min_max(values, invert=False)
    assert result[0] == pytest.approx(0.0)
    assert result[1] is None
    assert result[2] == pytest.approx(1.0)


def test_normalise_all_none():
    result = normalise_min_max([None, None])
    assert result == [None, None]


# ── compute_clear_scores ──────────────────────────────────────────────────────


def _make_model_results(n: int = 5, **kwargs) -> list[BenchmarkResult]:
    return [
        _make_result(task_id=f"TASK_{i:03d}", **kwargs)
        for i in range(n)
    ]


def test_compute_clear_scores_single_model():
    # All results rbac_compliant=True (default) → A = 1.0
    model_results = {
        "model-a": _make_model_results(
            5, outcome=0.7, governance=0.8, cost_usd=0.01, latency_s=5.0,
            aggregate_score=0.75
        )
    }
    scores = compute_clear_scores(model_results, pass_threshold=0.5)
    assert "model-a" in scores
    s = scores["model-a"]
    assert s["E"] == pytest.approx(0.7, abs=1e-4)
    # A = binary compliance rate: all results have rbac_compliant=True → A = 1.0
    assert s["A"] == pytest.approx(1.0, abs=1e-4)
    # Single model → cost_max == cost_min → C_norm = L_norm = 1.0
    assert s["C_norm"] == pytest.approx(1.0)
    assert s["L_norm"] == pytest.approx(1.0)
    assert s["clear_score"] is not None
    assert 0.0 <= s["clear_score"] <= 1.0


def test_compute_clear_scores_partial_assurance():
    """A = 0.6 when 3 of 5 results are RBAC-compliant."""
    results = [
        _make_result(task_id=f"T{i}", rbac_compliant=(i < 3), aggregate_score=0.8)
        for i in range(5)
    ]
    scores = compute_clear_scores({"model-x": results}, pass_threshold=0.5)
    assert scores["model-x"]["A"] == pytest.approx(0.6, abs=1e-4)


# ── compute_assurance_rate ────────────────────────────────────────────────────


def test_compute_assurance_rate_empty():
    assert compute_assurance_rate([]) == 0.0


def test_compute_assurance_rate_all_compliant():
    results = [_make_result(rbac_compliant=True) for _ in range(4)]
    assert compute_assurance_rate(results) == pytest.approx(1.0)


def test_compute_assurance_rate_half_compliant():
    results = [_make_result(rbac_compliant=(i % 2 == 0)) for i in range(4)]
    assert compute_assurance_rate(results) == pytest.approx(0.5)


def test_compute_clear_scores_two_models():
    """Two models; verify CLEAR_score in [0,1] and normalisation."""
    model_results = {
        "cheap-model": _make_model_results(
            5, outcome=0.6, governance=0.7, cost_usd=0.005, latency_s=3.0,
            aggregate_score=0.65
        ),
        "expensive-model": _make_model_results(
            5, outcome=0.8, governance=0.9, cost_usd=0.02, latency_s=12.0,
            aggregate_score=0.85
        ),
    }
    scores = compute_clear_scores(model_results, pass_threshold=0.5)

    for model_name, s in scores.items():
        assert s["clear_score"] is not None, f"{model_name} missing clear_score"
        assert 0.0 <= s["clear_score"] <= 1.0

    # cheap-model should have higher C_norm (lower cost)
    assert scores["cheap-model"]["C_norm"] > scores["expensive-model"]["C_norm"]
    # cheap-model should have higher L_norm (lower latency)
    assert scores["cheap-model"]["L_norm"] > scores["expensive-model"]["L_norm"]


def test_compute_clear_scores_missing_cost():
    """Missing cost → C_norm is None (no cost data; clear_score is also None)."""
    model_results = {
        "model-x": _make_model_results(
            3, outcome=0.7, governance=0.8, cost_usd=None, latency_s=5.0,
            aggregate_score=0.75
        )
    }
    scores = compute_clear_scores(model_results)
    # No cost data → cannot normalise → C_norm stays None → CLEAR composite is None
    assert scores["model-x"]["C_norm"] is None
    assert scores["model-x"]["clear_score"] is None


def test_compute_clear_scores_reliability_from_results():
    """R computed from grouped task results when no robustness data provided."""
    # 3 runs per task, all pass → R should be 1.0 at k=1
    tasks = ["TASK_A", "TASK_B", "TASK_C"]
    results = [
        _make_result(task_id=t, aggregate_score=0.9, outcome=0.8, governance=0.8)
        for t in tasks
        for _ in range(3)
    ]
    scores = compute_clear_scores({"model": results}, reliability_k=1, pass_threshold=0.5)
    assert scores["model"]["R"] == pytest.approx(1.0, abs=1e-4)


def test_compute_clear_scores_uses_robustness_data():
    """When robustness_by_model is provided, R is taken from mean_pass_k."""
    model_results = {
        "model-a": _make_model_results(5, aggregate_score=0.8, outcome=0.7, governance=0.8)
    }
    rob_data = {"mean_pass_k": {1: 0.65, 8: 0.30}}
    scores = compute_clear_scores(
        model_results,
        reliability_k=1,
        robustness_by_model={"model-a": rob_data},
    )
    assert scores["model-a"]["R"] == pytest.approx(0.65, abs=1e-4)


# ── build_clear_report ────────────────────────────────────────────────────────


def test_build_clear_report_shape():
    model_results = {
        "gpt-4o": _make_model_results(
            5, outcome=0.7, governance=0.85, cost_usd=0.008, latency_s=8.0,
            aggregate_score=0.75
        )
    }
    report = build_clear_report(model_results)

    assert "generated_at" in report
    assert "task_count" in report
    assert report["task_count"] == 5
    assert "pass_threshold" in report
    assert "reliability_k" in report
    assert "models" in report
    assert "leaderboard" in report
    assert "gpt-4o" in report["models"]

    model_keys = {
        "clear_score", "C_norm", "L_norm", "E", "A", "R",
        "mean_cost_usd", "mean_latency_s", "CNA", "CPS",
        "n_tasks", "n_successful",
    }
    assert model_keys.issubset(report["models"]["gpt-4o"].keys())


def test_build_clear_report_leaderboard_sorted():
    """Leaderboard is sorted by clear_score descending."""
    model_results = {
        "model-low": _make_model_results(
            5, outcome=0.3, governance=0.3, cost_usd=0.05, latency_s=20.0,
            aggregate_score=0.3
        ),
        "model-high": _make_model_results(
            5, outcome=0.9, governance=0.9, cost_usd=0.005, latency_s=3.0,
            aggregate_score=0.9
        ),
    }
    report = build_clear_report(model_results)
    lb = report["leaderboard"]

    assert lb[0]["rank"] == 1
    assert lb[0]["model"] == "model-high"
    assert lb[1]["model"] == "model-low"

    # Scores must be in descending order
    scores = [e["clear_score"] for e in lb if e["clear_score"] is not None]
    assert scores == sorted(scores, reverse=True)
