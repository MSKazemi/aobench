"""Unit tests for pass^k and robustness scoring (τ-bench metric).

Reference: Yao et al., "τ-bench: A Benchmark for Tool-Agent-User Interaction
in Real-World Domains", NeurIPS 2024. arXiv:2406.12045.

Formula: pass^k(task) = C(c, k) / C(n, k)
  where n = total runs, c = passing runs, k = required successes.
Aggregate: mean over tasks of C(c_t, k) / C(n, k).
"""

from __future__ import annotations

from datetime import datetime

import pytest

from exabench.schemas.result import BenchmarkResult, DimensionScores
from exabench.scorers.robustness_scorer import (
    compute_pass_k,
    compute_robustness,
    compute_robustness_suite,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_result(
    task_id: str,
    score: float | None,
    **kwargs,
) -> BenchmarkResult:
    """Minimal BenchmarkResult factory."""
    return BenchmarkResult(
        result_id="r-test",
        run_id="run-test",
        task_id=task_id,
        role="user",
        environment_id="env_test",
        adapter_name="direct_qa",
        dimension_scores=DimensionScores(),
        aggregate_score=score,
        timestamp=datetime(2026, 1, 1),
        **kwargs,
    )


def _n_results(task_id: str, n_pass: int, n_total: int) -> list[BenchmarkResult]:
    """Make n_total results for task_id with n_pass passing (score=1.0) and rest failing (score=0.0)."""
    return (
        [_make_result(task_id, 1.0) for _ in range(n_pass)]
        + [_make_result(task_id, 0.0) for _ in range(n_total - n_pass)]
    )


# ---------------------------------------------------------------------------
# compute_pass_k
# ---------------------------------------------------------------------------

class TestComputePassK:
    def test_all_pass_k1(self):
        results = _n_results("T1", 8, 8)
        assert compute_pass_k(results, k=1) == 1.0

    def test_all_pass_k8(self):
        results = _n_results("T1", 8, 8)
        assert compute_pass_k(results, k=8) == 1.0

    def test_all_fail_k1(self):
        results = _n_results("T1", 0, 8)
        assert compute_pass_k(results, k=1) == 0.0

    def test_all_fail_k4(self):
        results = _n_results("T1", 0, 8)
        assert compute_pass_k(results, k=4) == 0.0

    def test_c_less_than_k_returns_zero(self):
        # c=2, k=4 → C(2,4)=0 → 0.0
        results = _n_results("T1", 2, 8)
        assert compute_pass_k(results, k=4) == 0.0

    def test_k_exceeds_n_raises(self):
        results = _n_results("T1", 4, 4)
        with pytest.raises(ValueError, match="k=8"):
            compute_pass_k(results, k=8)

    def test_pass1_equals_success_rate(self):
        # pass^1 = C(c,1)/C(n,1) = c/n
        results = _n_results("T1", 5, 8)
        assert compute_pass_k(results, k=1) == pytest.approx(5 / 8, abs=1e-4)

    def test_unbiased_estimator_k2(self):
        # c=5, n=8, k=2: C(5,2)/C(8,2) = 10/28 ≈ 0.3571
        results = _n_results("T1", 5, 8)
        assert compute_pass_k(results, k=2) == pytest.approx(10 / 28, abs=1e-4)

    def test_unbiased_estimator_k4(self):
        # c=5, n=8, k=4: C(5,4)/C(8,4) = 5/70 ≈ 0.0714
        results = _n_results("T1", 5, 8)
        assert compute_pass_k(results, k=4) == pytest.approx(5 / 70, abs=1e-4)

    def test_unbiased_estimator_k8_with_c5_is_zero(self):
        # c=5, n=8, k=8: C(5,8)=0 → 0.0
        results = _n_results("T1", 5, 8)
        assert compute_pass_k(results, k=8) == 0.0

    def test_custom_pass_threshold(self):
        # With threshold=0.8, score=0.7 is a fail
        results = [_make_result("T1", 0.7) for _ in range(8)]
        assert compute_pass_k(results, k=1, pass_threshold=0.8) == 0.0

    def test_custom_pass_threshold_scores_above(self):
        results = [_make_result("T1", 0.9) for _ in range(8)]
        assert compute_pass_k(results, k=1, pass_threshold=0.8) == 1.0

    def test_none_aggregate_score_counts_as_fail(self):
        # 4 None + 4 passing → c=4 out of n=8 → pass^1 = 0.5
        results = (
            [_make_result("T1", None) for _ in range(4)]
            + [_make_result("T1", 1.0) for _ in range(4)]
        )
        assert compute_pass_k(results, k=1) == pytest.approx(0.5, abs=1e-4)

    def test_result_is_float_not_int(self):
        results = _n_results("T1", 4, 8)
        result = compute_pass_k(results, k=1)
        assert isinstance(result, float)

    def test_n_equals_k_all_pass(self):
        # n=k=4, c=4 → C(4,4)/C(4,4) = 1.0
        results = _n_results("T1", 4, 4)
        assert compute_pass_k(results, k=4) == 1.0

    def test_n_equals_k_some_fail(self):
        # n=k=4, c=3 → C(3,4)=0 → 0.0
        results = _n_results("T1", 3, 4)
        assert compute_pass_k(results, k=4) == 0.0


# ---------------------------------------------------------------------------
# compute_robustness
# ---------------------------------------------------------------------------

class TestComputeRobustness:
    def test_requires_at_least_two_results(self):
        with pytest.raises(ValueError, match="at least 2"):
            compute_robustness([_make_result("T1", 1.0)])

    def test_mixed_task_ids_raises(self):
        results = [_make_result("T1", 1.0), _make_result("T2", 0.5)]
        with pytest.raises(ValueError, match="task_id"):
            compute_robustness(results)

    def test_returns_expected_keys(self):
        results = _n_results("T1", 4, 8)
        stats = compute_robustness(results)
        expected_keys = {
            "task_id", "n_runs", "pass_threshold", "n_passing",
            "pass_k", "mean_score", "std_dev", "min_score", "max_score",
            "range", "robustness_score", "scores",
        }
        assert expected_keys.issubset(stats.keys())

    def test_task_id_propagated(self):
        results = _n_results("JOB_USR_001", 4, 8)
        stats = compute_robustness(results)
        assert stats["task_id"] == "JOB_USR_001"

    def test_basic_stats_values(self):
        # scores: 1.0, 0.8, 0.6, 0.4 → mean=0.7, min=0.4, max=1.0, range=0.6
        results = [_make_result("T1", s) for s in [1.0, 0.8, 0.6, 0.4]]
        stats = compute_robustness(results)
        assert stats["n_runs"] == 4
        assert stats["mean_score"] == pytest.approx(0.7, abs=1e-4)
        assert stats["min_score"] == pytest.approx(0.4, abs=1e-4)
        assert stats["max_score"] == pytest.approx(1.0, abs=1e-4)
        assert stats["range"] == pytest.approx(0.6, abs=1e-4)

    def test_perfect_consistency_std_zero(self):
        results = [_make_result("T1", 1.0) for _ in range(4)]
        stats = compute_robustness(results)
        assert stats["std_dev"] == 0.0
        assert stats["robustness_score"] == 1.0

    def test_all_pass_n_passing(self):
        results = [_make_result("T1", 1.0) for _ in range(8)]
        stats = compute_robustness(results)
        assert stats["n_passing"] == 8

    def test_none_pass_n_passing(self):
        results = [_make_result("T1", 0.0) for _ in range(8)]
        stats = compute_robustness(results)
        assert stats["n_passing"] == 0
        assert stats["pass_k"][1] == 0.0

    def test_pass_k_all_four_values_with_n8(self):
        results = [_make_result("T1", 1.0) for _ in range(8)]
        stats = compute_robustness(results)
        assert set(stats["pass_k"].keys()) == {1, 2, 4, 8}

    def test_pass_k_skipped_when_n_too_small(self):
        # n=3: k=4 and k=8 cannot be computed
        results = [_make_result("T1", 1.0) for _ in range(3)]
        stats = compute_robustness(results)
        assert 1 in stats["pass_k"]
        assert 2 in stats["pass_k"]
        assert 4 not in stats["pass_k"]
        assert 8 not in stats["pass_k"]

    def test_robustness_score_is_one_minus_std(self):
        # Binary outcomes: 1,1,0,0 → mean=0.5, std_dev=0.5 → robustness_score=0.5
        results = [_make_result("T1", 1.0), _make_result("T1", 1.0),
                   _make_result("T1", 0.0), _make_result("T1", 0.0)]
        stats = compute_robustness(results)
        assert stats["robustness_score"] == pytest.approx(1.0 - stats["std_dev"], abs=1e-4)

    def test_robustness_score_clamped_non_negative(self):
        # Max possible std_dev for 0/1 outcomes is 0.5 → robustness_score ≥ 0.5
        # but the clamp ensures it never goes negative
        results = [_make_result("T1", 0.0), _make_result("T1", 1.0)]
        stats = compute_robustness(results)
        assert stats["robustness_score"] >= 0.0

    def test_cost_aggregated(self):
        results = [
            _make_result("T1", 1.0, cost_estimate_usd=0.01),
            _make_result("T1", 0.5, cost_estimate_usd=0.02),
        ]
        stats = compute_robustness(results)
        assert stats["total_cost_usd"] == pytest.approx(0.03, abs=1e-6)

    def test_latency_averaged(self):
        results = [
            _make_result("T1", 1.0, latency_seconds=2.0),
            _make_result("T1", 0.5, latency_seconds=4.0),
        ]
        stats = compute_robustness(results)
        assert stats["mean_latency_seconds"] == pytest.approx(3.0, abs=1e-3)

    def test_missing_cost_returns_none(self):
        results = [_make_result("T1", 1.0), _make_result("T1", 0.5)]
        stats = compute_robustness(results)
        assert stats["total_cost_usd"] is None

    def test_pass_k_consistent_with_standalone_compute_pass_k(self):
        results = _n_results("T1", 5, 8)
        stats = compute_robustness(results)
        for k, v in stats["pass_k"].items():
            assert v == pytest.approx(compute_pass_k(results, k=k), abs=1e-6)


# ---------------------------------------------------------------------------
# compute_robustness_suite
# ---------------------------------------------------------------------------

class TestComputeRobustnessSuite:
    def test_empty_input(self):
        suite = compute_robustness_suite({})
        assert suite["tasks"] == {}
        assert suite["mean_robustness_score"] is None
        assert suite["mean_pass_k"] == {}

    def test_skips_tasks_with_single_run(self):
        suite = compute_robustness_suite({"T1": [_make_result("T1", 1.0)]})
        assert suite["tasks"] == {}

    def test_includes_tasks_with_sufficient_runs(self):
        results_by_task = {
            "T1": [_make_result("T1", 1.0) for _ in range(4)],
        }
        suite = compute_robustness_suite(results_by_task)
        assert "T1" in suite["tasks"]

    def test_multi_task_mean_pass_k1(self):
        # T1: all pass → pass^1=1.0; T2: all fail → pass^1=0.0 → mean=0.5
        results_by_task = {
            "T1": _n_results("T1", 4, 4),
            "T2": _n_results("T2", 0, 4),
        }
        suite = compute_robustness_suite(results_by_task)
        assert suite["mean_pass_k"][1] == pytest.approx(0.5, abs=1e-4)

    def test_perfect_suite_robustness(self):
        results_by_task = {
            "T1": [_make_result("T1", 1.0) for _ in range(4)],
            "T2": [_make_result("T2", 1.0) for _ in range(4)],
        }
        suite = compute_robustness_suite(results_by_task)
        assert suite["mean_robustness_score"] == pytest.approx(1.0, abs=1e-4)
        assert suite["mean_pass_k"][1] == 1.0

    def test_task_count_in_suite(self):
        results_by_task = {
            f"T{i}": _n_results(f"T{i}", 4, 8) for i in range(5)
        }
        suite = compute_robustness_suite(results_by_task)
        assert len(suite["tasks"]) == 5

    def test_mixed_valid_and_single_run_tasks(self):
        results_by_task = {
            "T1": _n_results("T1", 4, 8),   # valid
            "T2": [_make_result("T2", 1.0)], # only 1 run → skipped
        }
        suite = compute_robustness_suite(results_by_task)
        assert "T1" in suite["tasks"]
        assert "T2" not in suite["tasks"]

    def test_suite_cost_aggregation(self):
        results_by_task = {
            "T1": [
                _make_result("T1", 1.0, cost_estimate_usd=0.01),
                _make_result("T1", 0.5, cost_estimate_usd=0.01),
            ],
            "T2": [
                _make_result("T2", 1.0, cost_estimate_usd=0.02),
                _make_result("T2", 0.5, cost_estimate_usd=0.02),
            ],
        }
        suite = compute_robustness_suite(results_by_task)
        assert suite["total_cost_usd"] == pytest.approx(0.06, abs=1e-6)
