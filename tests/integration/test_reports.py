"""Integration tests: JSON and HTML report generation."""

from __future__ import annotations

import json
from pathlib import Path

BENCHMARK_ROOT = Path(__file__).parent.parent.parent / "benchmark"


def _run_all_tasks(output_root: Path) -> str:
    """Run all 10 tasks with direct_qa and return the run_id."""
    from exabench.adapters.direct_qa_adapter import DirectQAAdapter
    from exabench.loaders.registry import BenchmarkRegistry
    from exabench.runners.runner import BenchmarkRunner
    from exabench.utils.ids import make_run_id

    run_id = make_run_id()
    adapter = DirectQAAdapter(answer="OOM kill detected on node03")
    runner = BenchmarkRunner(
        adapter=adapter,
        benchmark_root=BENCHMARK_ROOT,
        output_root=output_root,
    )

    registry = BenchmarkRegistry(BENCHMARK_ROOT)
    registry.load_all()
    for task_id in registry.task_ids:
        task = registry.get_task(task_id)
        runner.run(task.task_id, task.environment_id, run_id=run_id)

    return run_id


def test_json_report_summary(tmp_path):
    from exabench.reports.json_report import build_run_summary

    run_id = _run_all_tasks(tmp_path)
    run_dir = tmp_path / run_id

    summary = build_run_summary(run_dir)

    assert summary["run_id"] == run_id
    assert summary["task_count"] >= 10
    assert summary["hard_fail_count"] == 0
    assert summary["mean_aggregate_score"] is not None
    assert 0.0 <= summary["mean_aggregate_score"] <= 1.0
    assert len(summary["tasks"]) == summary["task_count"]

    for t in summary["tasks"]:
        assert "task_id" in t
        assert "aggregate_score" in t
        assert "outcome" in t


def test_json_report_written_to_disk(tmp_path):
    from exabench.reports.json_report import write_run_summary

    run_id = _run_all_tasks(tmp_path)
    run_dir = tmp_path / run_id

    out_path = write_run_summary(run_dir)
    assert out_path.exists()

    data = json.loads(out_path.read_text())
    assert data["task_count"] >= 10


def test_html_report_written_to_disk(tmp_path):
    from exabench.reports.html_report import write_html_report

    run_id = _run_all_tasks(tmp_path)
    run_dir = tmp_path / run_id

    html_path = write_html_report(run_dir)
    assert html_path.exists()

    content = html_path.read_text()
    assert "ExaBench" in content
    assert run_id in content
    assert "<table" in content
