"""Unit tests for compute_tier_accuracy() and tier columns in build_clear_report()."""

from datetime import datetime, timezone

import pytest

from exabench.reports.clear_report import build_clear_report, compute_tier_accuracy
from exabench.schemas.result import BenchmarkResult, DimensionScores


def _make_result(
    task_id: str,
    tier: int | None,
    aggregate_score: float,
    model_name: str = "test_model",
) -> BenchmarkResult:
    return BenchmarkResult(
        result_id=f"r_{task_id}",
        run_id="run_01",
        task_id=task_id,
        role="scientific_user",
        environment_id="env_01",
        adapter_name="test_adapter",
        dimension_scores=DimensionScores(outcome=aggregate_score),
        aggregate_score=aggregate_score,
        model_name=model_name,
        timestamp=datetime.now(tz=timezone.utc),
        task_difficulty_tier=tier,
    )


# ---------------------------------------------------------------------------
# compute_tier_accuracy tests
# ---------------------------------------------------------------------------


def test_compute_tier_accuracy_all_tiers():
    """10 results (4 tier1, 4 tier2, 2 tier3); 3 of 4 tier1 pass → tier1_acc=0.75."""
    results = [
        # tier1: 3 pass, 1 fail
        _make_result("t1_1", 1, 1.0),
        _make_result("t1_2", 1, 1.0),
        _make_result("t1_3", 1, 1.0),
        _make_result("t1_4", 1, 0.0),
        # tier2: 2 pass, 2 fail
        _make_result("t2_1", 2, 1.0),
        _make_result("t2_2", 2, 1.0),
        _make_result("t2_3", 2, 0.0),
        _make_result("t2_4", 2, 0.0),
        # tier3: 1 pass, 1 fail
        _make_result("t3_1", 3, 1.0),
        _make_result("t3_2", 3, 0.0),
    ]
    acc = compute_tier_accuracy(results, pass_threshold=0.5)
    assert acc["tier1_acc"] == pytest.approx(0.75)
    assert acc["tier2_acc"] == pytest.approx(0.5)
    assert acc["tier3_acc"] == pytest.approx(0.5)


def test_compute_tier_accuracy_missing_tier():
    """No tier3 results → tier3_acc is None."""
    results = [
        _make_result("t1_1", 1, 1.0),
        _make_result("t2_1", 2, 0.5),
    ]
    acc = compute_tier_accuracy(results)
    assert acc["tier3_acc"] is None
    assert acc["tier1_acc"] is not None
    assert acc["tier2_acc"] is not None


def test_compute_tier_accuracy_empty():
    """Empty results → all None."""
    acc = compute_tier_accuracy([])
    assert acc == {"tier1_acc": None, "tier2_acc": None, "tier3_acc": None}


def test_compute_tier_accuracy_none_tier_ignored():
    """Results with tier=None are ignored."""
    results = [
        _make_result("t1_1", 1, 1.0),
        _make_result("t_none", None, 0.0),  # should be ignored
    ]
    acc = compute_tier_accuracy(results)
    assert acc["tier1_acc"] == pytest.approx(1.0)
    assert acc["tier2_acc"] is None
    assert acc["tier3_acc"] is None


# ---------------------------------------------------------------------------
# build_clear_report tier column tests
# ---------------------------------------------------------------------------


def test_build_clear_report_includes_tier_columns():
    """Verify tier1_acc, tier2_acc, tier3_acc are present in the report output."""
    results = [
        _make_result("t1", 1, 1.0),
        _make_result("t2", 2, 0.8),
        _make_result("t3", 3, 0.3),
    ]
    report = build_clear_report({"model_a": results}, pass_threshold=0.5)

    model_data = report["models"]["model_a"]
    assert "tier1_acc" in model_data
    assert "tier2_acc" in model_data
    assert "tier3_acc" in model_data

    assert model_data["tier1_acc"] == pytest.approx(1.0)
    assert model_data["tier2_acc"] == pytest.approx(1.0)
    assert model_data["tier3_acc"] == pytest.approx(0.0)

    # Also check leaderboard entry
    lb_entry = report["leaderboard"][0]
    assert "tier1_acc" in lb_entry
    assert "tier2_acc" in lb_entry
    assert "tier3_acc" in lb_entry
