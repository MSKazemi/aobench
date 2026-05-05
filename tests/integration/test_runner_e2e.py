"""Integration test: full Alpha-0 pipeline — 1 task + 1 env + direct_qa adapter."""

from __future__ import annotations

from pathlib import Path

import pytest

BENCHMARK_ROOT = Path(__file__).parent.parent.parent / "benchmark"


def test_alpha0_run(tmp_path):
    """Run JOB_USR_001 on env_01 with direct_qa adapter and validate outputs."""
    from aobench.adapters.direct_qa_adapter import DirectQAAdapter
    from aobench.runners.runner import BenchmarkRunner
    from aobench.schemas.result import BenchmarkResult

    runner = BenchmarkRunner(
        adapter=DirectQAAdapter(answer="Job 891234 failed due to out-of-memory (OOM kill)."),
        benchmark_root=BENCHMARK_ROOT,
        output_root=tmp_path,
    )

    result = runner.run("JOB_USR_001", "env_01")

    # Result is a valid BenchmarkResult
    assert isinstance(result, BenchmarkResult)
    assert result.task_id == "JOB_USR_001"
    assert result.role == "scientific_user"
    assert result.environment_id == "env_01"
    assert result.adapter_name == "direct_qa"

    # Scores are populated and in range
    assert result.dimension_scores.outcome is not None
    assert 0.0 <= result.dimension_scores.outcome <= 1.0
    assert result.dimension_scores.governance is not None
    assert result.aggregate_score is not None
    assert 0.0 <= result.aggregate_score <= 1.0

    # Trace file was written
    run_dir = tmp_path / result.run_id
    trace_file = run_dir / "traces" / "JOB_USR_001_trace.json"
    result_file = run_dir / "results" / "JOB_USR_001_result.json"
    assert trace_file.exists(), f"Trace file missing: {trace_file}"
    assert result_file.exists(), f"Result file missing: {result_file}"

    # Trace file is valid JSON
    import json
    trace_data = json.loads(trace_file.read_text())
    assert trace_data["task_id"] == "JOB_USR_001"
    assert "steps" in trace_data

    result_data = json.loads(result_file.read_text())
    assert result_data["task_id"] == "JOB_USR_001"
    assert "dimension_scores" in result_data
