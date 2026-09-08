"""Unit tests for aobench.reports.governance_report."""

from __future__ import annotations

import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from aobench.reports.governance_report import (
    _wilson_ci,
    build_governance_report,
    write_governance_report,
)
from aobench.schemas.result import BenchmarkResult, DimensionScores


# ── helpers ───────────────────────────────────────────────────────────────────


def _make_result(
    *,
    task_id: str = "TASK_USR_001",
    model_name: str = "test-model",
    governance: float | None = 1.0,
    outcome: float | None = 0.8,
    hard_fail: bool = False,
    hard_fail_reason: str | None = None,
    role: str = "usr",
) -> BenchmarkResult:
    return BenchmarkResult(
        result_id=f"r-{task_id}",
        run_id="run-test",
        task_id=task_id,
        role=role,
        environment_id="env_01",
        adapter_name="test",
        model_name=model_name,
        dimension_scores=DimensionScores(
            outcome=outcome,
            governance=governance,
        ),
        aggregate_score=(governance or 0.0) * 0.2 + (outcome or 0.0) * 0.3,
        hard_fail=hard_fail,
        hard_fail_reason=hard_fail_reason,
        timestamp=datetime.now(tz=timezone.utc),
    )


def _write_results(run_dir: Path, results: list[BenchmarkResult]) -> None:
    results_dir = run_dir / "results"
    results_dir.mkdir(parents=True)
    for r in results:
        out = results_dir / f"{r.task_id}_result.json"
        out.write_text(r.model_dump_json(), encoding="utf-8")


# ── _wilson_ci ────────────────────────────────────────────────────────────────


def test_wilson_ci_all_pass():
    lo, hi = _wilson_ci(10, 10)
    assert lo > 0.7
    assert hi <= 1.0


def test_wilson_ci_no_pass():
    lo, hi = _wilson_ci(0, 10)
    assert lo == pytest.approx(0.0)
    assert hi < 0.3


def test_wilson_ci_zero_n():
    lo, hi = _wilson_ci(0, 0)
    assert lo == 0.0
    assert hi == 0.0


def test_wilson_ci_half():
    lo, hi = _wilson_ci(5, 10)
    assert lo < 0.5 < hi


# ── build_governance_report ───────────────────────────────────────────────────


def test_report_has_three_sections():
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)
        results = [
            _make_result(task_id="TASK_USR_001", governance=1.0, outcome=0.8),
            _make_result(task_id="TASK_USR_002", governance=0.0, outcome=0.5, hard_fail=True, hard_fail_reason="permission denied"),
            _make_result(task_id="TASK_USR_003", governance=1.0, outcome=0.9),
        ]
        _write_results(run_dir, results)
        report = build_governance_report(run_dir)

    assert "## 1. Governance Score" in report
    assert "## 2. Governance vs. Task Completion" in report
    assert "## 3. Interpretation and Next Steps" in report


def test_report_contains_wilson_ci():
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)
        results = [_make_result(task_id=f"T_{i:03d}", governance=1.0) for i in range(10)]
        _write_results(run_dir, results)
        report = build_governance_report(run_dir)

    assert "95% CI (Wilson)" in report


def test_report_shows_hard_fail():
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)
        results = [
            _make_result(task_id="TASK_001", hard_fail=True, hard_fail_reason="rbac violation"),
            _make_result(task_id="TASK_002"),
        ]
        _write_results(run_dir, results)
        report = build_governance_report(run_dir)

    assert "**YES**" in report
    assert "rbac violation" in report


def test_report_includes_paper_baselines_by_default():
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)
        _write_results(run_dir, [_make_result()])
        report = build_governance_report(run_dir)

    assert "GPT-4o (paper, E1)" in report


def test_report_no_baselines_flag():
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)
        _write_results(run_dir, [_make_result()])
        report = build_governance_report(run_dir, include_baselines=False)

    assert "GPT-4o (paper, E1)" not in report


def test_report_strong_governance_interpretation():
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)
        results = [_make_result(task_id=f"T_{i:03d}", governance=1.0, outcome=0.9) for i in range(5)]
        _write_results(run_dir, results)
        report = build_governance_report(run_dir)

    assert "Strong governance compliance" in report


def test_report_critical_governance_interpretation():
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)
        results = [
            _make_result(task_id=f"T_{i:03d}", governance=0.0, outcome=0.4, hard_fail=True, hard_fail_reason="rbac")
            for i in range(5)
        ]
        _write_results(run_dir, results)
        report = build_governance_report(run_dir)

    assert "Critical governance gaps" in report


def test_report_custom_title():
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)
        _write_results(run_dir, [_make_result()])
        report = build_governance_report(run_dir, title="My Custom Report")

    assert "# My Custom Report" in report


def test_write_governance_report_creates_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)
        _write_results(run_dir, [_make_result()])
        out_path = write_governance_report(run_dir)

        assert out_path.exists()
        assert out_path.suffix == ".md"
        assert out_path.stat().st_size > 0


def test_report_empty_run_raises():
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)
        (run_dir / "results").mkdir()
        with pytest.raises(FileNotFoundError):
            build_governance_report(run_dir)
