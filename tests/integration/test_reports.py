"""Integration tests: JSON and HTML report generation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

BENCHMARK_ROOT = Path(__file__).parent.parent.parent / "benchmark"


def _run_all_tasks(output_root: Path) -> str:
    """Run all 10 tasks with direct_qa and return the run_id."""
    from aobench.adapters.direct_qa_adapter import DirectQAAdapter
    from aobench.loaders.registry import BenchmarkRegistry
    from aobench.runners.runner import BenchmarkRunner
    from aobench.utils.ids import make_run_id

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
    from aobench.reports.json_report import build_run_summary

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
    from aobench.reports.json_report import write_run_summary

    run_id = _run_all_tasks(tmp_path)
    run_dir = tmp_path / run_id

    out_path = write_run_summary(run_dir)
    assert out_path.exists()

    data = json.loads(out_path.read_text())
    assert data["task_count"] >= 10


def test_html_report_written_to_disk(tmp_path):
    from aobench.reports.html_report import write_html_report

    run_id = _run_all_tasks(tmp_path)
    run_dir = tmp_path / run_id

    html_path = write_html_report(run_dir)
    assert html_path.exists()

    content = html_path.read_text()
    assert "AOBench" in content
    assert run_id in content
    assert "<table" in content


def test_report_json_flag_emits_clean_json_on_stdout(tmp_path):
    from typer.testing import CliRunner

    from aobench.cli.main import app

    run_id = _run_all_tasks(tmp_path)
    run_dir = tmp_path / run_id

    runner = CliRunner()
    result = runner.invoke(app, ["report", "json", str(run_dir), "--json"])
    assert result.exit_code == 0, result.output

    # No "Report written:" banner, no human summary lines, no trailing blank line.
    assert result.output.count("\n") == 1
    data = json.loads(result.output)
    assert data["run_id"] == run_id
    assert data["task_count"] >= 10


def test_report_json_default_output_unchanged(tmp_path):
    from typer.testing import CliRunner

    from aobench.cli.main import app

    run_id = _run_all_tasks(tmp_path)
    run_dir = tmp_path / run_id

    runner = CliRunner()
    result = runner.invoke(app, ["report", "json", str(run_dir)])
    assert result.exit_code == 0, result.output
    assert "Report written:" in result.output
    assert f"Run ID  : {run_id}" in result.output


def test_missing_run_dir_has_an_actionable_error(tmp_path):
    from typer.testing import CliRunner

    from aobench.cli.main import app

    available_run = tmp_path / "existing-run"
    available_run.mkdir()
    missing_run = tmp_path / "missing-run"

    result = CliRunner().invoke(app, ["report", "json", str(missing_run)])

    assert result.exit_code == 2
    assert "Traceback" not in result.output
    assert f"run directory '{missing_run}' does not exist" in result.output
    assert "Available runs:" in result.output
    assert str(available_run) in result.output


def test_missing_run_dir_caps_the_available_runs_list(tmp_path):
    from typer.testing import CliRunner

    from aobench.cli.main import app

    for index in range(11):
        (tmp_path / f"run-{index}").mkdir()

    result = CliRunner().invoke(app, ["report", "json", str(tmp_path / "missing-run")])

    assert result.exit_code == 2
    assert "… and 1 more" in result.output


def test_empty_run_has_an_actionable_error(tmp_path):
    from typer.testing import CliRunner

    from aobench.cli.main import app

    empty_run = tmp_path / "empty-run"
    empty_run.mkdir()

    result = CliRunner().invoke(app, ["report", "json", str(empty_run)])

    assert result.exit_code == 2
    assert "Traceback" not in result.output
    assert f"run '{empty_run}' contains no results" in result.output
    assert "aobench run all --adapter direct_qa --split dev" in result.output


def test_run_dir_that_is_a_file_says_so(tmp_path):
    from typer.testing import CliRunner

    from aobench.cli.main import app

    not_a_dir = tmp_path / "run.json"
    not_a_dir.write_text("{}")

    result = CliRunner().invoke(app, ["report", "json", str(not_a_dir)])

    assert result.exit_code == 2
    assert "Traceback" not in result.output
    assert f"run directory '{not_a_dir}' is not a directory" in result.output


@pytest.mark.parametrize("subcommand", ["json", "html", "slices", "governance"])
def test_every_report_subcommand_explains_a_missing_run(tmp_path, subcommand):
    from typer.testing import CliRunner

    from aobench.cli.main import app

    (tmp_path / "existing-run").mkdir()

    result = CliRunner().invoke(app, ["report", subcommand, str(tmp_path / "missing-run")])

    assert result.exit_code == 2, result.output
    assert "Traceback" not in result.output
    assert "does not exist" in result.output
    assert "Available runs:" in result.output


@pytest.mark.parametrize("subcommand", ["json", "html", "slices", "governance"])
def test_every_report_subcommand_explains_an_empty_run(tmp_path, subcommand):
    from typer.testing import CliRunner

    from aobench.cli.main import app

    empty_run = tmp_path / "empty-run"
    (empty_run / "results").mkdir(parents=True)

    result = CliRunner().invoke(app, ["report", subcommand, str(empty_run)])

    assert result.exit_code == 2, result.output
    assert "Traceback" not in result.output
    assert f"run '{empty_run}' contains no results" in result.output
