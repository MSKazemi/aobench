"""Integration tests: trace + result JSON artifacts written by BenchmarkRunner."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

BENCHMARK_ROOT = Path(__file__).parent.parent.parent / "benchmark"


def test_trace_and_result_files_written(tmp_path):
    """Both trace and result JSON must be written for a completed run."""
    from exabench.adapters.direct_qa_adapter import DirectQAAdapter
    from exabench.runners.runner import BenchmarkRunner

    runner = BenchmarkRunner(
        adapter=DirectQAAdapter(answer="OOM kill on node03"),
        benchmark_root=BENCHMARK_ROOT,
        output_root=tmp_path,
    )
    result = runner.run("JOB_USR_001", "env_01")

    run_dir = tmp_path / result.run_id
    trace_file = run_dir / "traces" / "JOB_USR_001_trace.json"
    result_file = run_dir / "results" / "JOB_USR_001_result.json"

    assert trace_file.exists()
    assert result_file.exists()

    trace_data = json.loads(trace_file.read_text())
    assert trace_data["task_id"] == "JOB_USR_001"
    assert "steps" in trace_data
    assert "final_answer" in trace_data

    result_data = json.loads(result_file.read_text())
    assert result_data["task_id"] == "JOB_USR_001"
    assert "dimension_scores" in result_data
    assert result_data["dimension_scores"]["governance"] is not None


def test_all_dimension_scores_populated(tmp_path):
    """All 5 scorer dimensions must be non-None in a direct_qa result."""
    from exabench.adapters.direct_qa_adapter import DirectQAAdapter
    from exabench.runners.runner import BenchmarkRunner

    runner = BenchmarkRunner(
        adapter=DirectQAAdapter(answer="Job 891234 failed: OOM kill"),
        benchmark_root=BENCHMARK_ROOT,
        output_root=tmp_path,
    )
    result = runner.run("JOB_USR_001", "env_01")

    dims = result.dimension_scores
    assert dims.outcome is not None
    assert dims.tool_use is not None
    assert dims.grounding is not None
    assert dims.governance is not None
    assert dims.efficiency is not None
    assert 0.0 <= result.aggregate_score <= 1.0
