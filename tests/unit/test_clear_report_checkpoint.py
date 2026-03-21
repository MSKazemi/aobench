"""Unit tests for CLEAR report checkpoint integration (checkpoint_scorer_spec.md §7.2)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from exabench.reports.clear_report import (
    build_clear_report,
    compute_clear_scores,
    compute_cps,
)
from exabench.schemas.result import BenchmarkResult, CheckpointResult, DimensionScores


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TS = datetime.now(tz=timezone.utc)


def _result(
    task_id: str = "task_1",
    outcome: float = 1.0,
    s_partial: float | None = None,
    s_full: float | None = None,
    checkpoint_results: list[CheckpointResult] | None = None,
    cost_usd: float | None = 0.01,
    aggregate_score: float | None = None,
) -> BenchmarkResult:
    if aggregate_score is None:
        aggregate_score = s_partial if s_partial is not None else outcome
    return BenchmarkResult(
        result_id="rid",
        run_id="run1",
        task_id=task_id,
        role="sysadmin",
        environment_id="env_01",
        adapter_name="test",
        dimension_scores=DimensionScores(outcome=outcome),
        aggregate_score=aggregate_score,
        cost_estimate_usd=cost_usd,
        timestamp=_TS,
        s_partial=s_partial,
        s_full=s_full,
        checkpoint_results=checkpoint_results,
    )


def _make_checkpoint_results(passed_flags: list[bool]) -> list[CheckpointResult]:
    return [CheckpointResult(checkpoint_id=f"cp_{i}", passed=p) for i, p in enumerate(passed_flags)]


# ---------------------------------------------------------------------------
# E uses s_partial when available
# ---------------------------------------------------------------------------


class TestEfficacySource:
    def test_e_uses_s_partial_when_available(self):
        """results with s_partial=0.8 → E=0.8 (not binary outcome=1.0)"""
        r = _result(outcome=1.0, s_partial=0.8)
        scores = compute_clear_scores({"model_a": [r]})
        assert scores["model_a"]["E"] == pytest.approx(0.8)

    def test_e_falls_back_to_binary(self):
        """results with s_partial=None → E=binary outcome"""
        r = _result(outcome=0.6, s_partial=None)
        scores = compute_clear_scores({"model_a": [r]})
        assert scores["model_a"]["E"] == pytest.approx(0.6)

    def test_e_mixed_partial_and_binary(self):
        """mix of results with/without s_partial → E uses s_partial where available"""
        r1 = _result(task_id="t1", outcome=1.0, s_partial=0.75)
        r2 = _result(task_id="t2", outcome=0.5, s_partial=None)
        scores = compute_clear_scores({"model_a": [r1, r2]})
        # E = mean(0.75, 0.5) = 0.625
        assert scores["model_a"]["E"] == pytest.approx(0.625)


# ---------------------------------------------------------------------------
# CPS uses s_partial threshold
# ---------------------------------------------------------------------------


class TestCpsWithSPartial:
    def test_cps_uses_s_partial_threshold(self):
        """s_partial=0.6 (>= 0.5 threshold) → counted as successful"""
        r = _result(outcome=0.0, s_partial=0.6, cost_usd=0.02, aggregate_score=0.0)
        cps = compute_cps([r], pass_threshold=0.5)
        assert cps is not None
        assert cps == pytest.approx(0.02)

    def test_cps_s_partial_below_threshold(self):
        """s_partial=0.3 (< 0.5) → not counted as successful → CPS=None"""
        r = _result(outcome=0.0, s_partial=0.3, cost_usd=0.02, aggregate_score=0.0)
        cps = compute_cps([r], pass_threshold=0.5)
        assert cps is None

    def test_cps_falls_back_to_aggregate_when_no_s_partial(self):
        """s_partial=None, aggregate_score=0.8 → falls back to aggregate for success check"""
        r = _result(outcome=0.8, s_partial=None, cost_usd=0.05, aggregate_score=0.8)
        cps = compute_cps([r], pass_threshold=0.5)
        assert cps is not None
        assert cps == pytest.approx(0.05)

    def test_cps_none_when_no_cost_data(self):
        """no cost_estimate_usd → CPS=None"""
        r = _result(outcome=1.0, s_partial=0.9, cost_usd=None, aggregate_score=0.9)
        cps = compute_cps([r])
        assert cps is None


# ---------------------------------------------------------------------------
# build_clear_report output shape
# ---------------------------------------------------------------------------


class TestReportShape:
    def _build(self, results: list[BenchmarkResult]) -> dict:
        return build_clear_report({"model_a": results})

    def test_report_shape_e_source_field(self):
        """build_clear_report output contains E_source key for each model"""
        r = _result(s_partial=0.7)
        report = self._build([r])
        assert "E_source" in report["models"]["model_a"]

    def test_e_source_is_s_partial_when_any_have_s_partial(self):
        """E_source='s_partial' when any result has s_partial"""
        r = _result(s_partial=0.7)
        report = self._build([r])
        assert report["models"]["model_a"]["E_source"] == "s_partial"

    def test_e_source_is_binary_when_no_s_partial(self):
        """E_source='binary_outcome' when no result has s_partial"""
        r = _result(s_partial=None)
        report = self._build([r])
        assert report["models"]["model_a"]["E_source"] == "binary_outcome"

    def test_report_mean_checkpoints_passed(self):
        """mean_checkpoints_passed computed correctly"""
        cp_results = _make_checkpoint_results([True, True, False, False])  # 2 passed
        r1 = _result(task_id="t1", checkpoint_results=cp_results, s_partial=0.25)
        cp_results2 = _make_checkpoint_results([True, True, True, True])  # 4 passed
        r2 = _result(task_id="t2", checkpoint_results=cp_results2, s_partial=1.0)
        report = self._build([r1, r2])
        # mean = (2 + 4) / 2 = 3.0
        assert report["models"]["model_a"]["mean_checkpoints_passed"] == pytest.approx(3.0)

    def test_report_mean_s_partial(self):
        """mean_s_partial present and correct"""
        r1 = _result(task_id="t1", s_partial=0.25)
        r2 = _result(task_id="t2", s_partial=0.75)
        report = self._build([r1, r2])
        assert report["models"]["model_a"]["mean_s_partial"] == pytest.approx(0.5)

    def test_report_mean_s_full(self):
        """mean_s_full present and correct"""
        r1 = _result(task_id="t1", s_full=0.0, s_partial=0.25)
        r2 = _result(task_id="t2", s_full=1.0, s_partial=0.75)
        report = self._build([r1, r2])
        assert report["models"]["model_a"]["mean_s_full"] == pytest.approx(0.5)

    def test_leaderboard_has_cps_column(self):
        """leaderboard entries include CPS field"""
        r = _result(cost_usd=0.01, s_partial=0.8)
        report = self._build([r])
        for entry in report["leaderboard"]:
            assert "CPS" in entry

    def test_leaderboard_has_e_column(self):
        """leaderboard entries include E field"""
        r = _result(s_partial=0.7)
        report = self._build([r])
        for entry in report["leaderboard"]:
            assert "E" in entry
