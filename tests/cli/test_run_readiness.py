"""Regression coverage for scored batch-run readiness gating."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from aobench.cli.main import app
from aobench.cli.run_cmd import _is_run_ready, _load_split_ids
from aobench.runners.runner import BenchmarkRunner
from aobench.schemas.task import TaskSpec

BENCHMARK_ROOT = Path(__file__).parent.parent.parent / "benchmark"


def _task(*, task_id: str, scoring_readiness: str) -> TaskSpec:
    return TaskSpec(
        task_id=task_id,
        title="T",
        query_text="Q",
        role="scientific_user",
        qcat="DOCS",
        difficulty="easy",
        environment_id="env_01",
        expected_answer_type="diagnosis",
        scoring_readiness=scoring_readiness,
    )


def _output(result) -> str:
    return (result.output or "") + (result.stderr or "")


@pytest.fixture
def run_calls(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Record every task ID that reaches BenchmarkRunner.run, then run it for real."""
    calls: list[str] = []
    original = BenchmarkRunner.run

    def spy(self, task_id, env_id, run_id=None):
        calls.append(task_id)
        return original(self, task_id, env_id, run_id=run_id)

    monkeypatch.setattr(BenchmarkRunner, "run", spy)
    return calls


def _mini_corpus(tmp_path: Path) -> Path:
    """A ready, a partial and a blocked shipped task, with env_01 and the scoring configs."""
    root = tmp_path / "benchmark"
    specs = root / "tasks" / "specs"
    specs.mkdir(parents=True)
    for task_id in ("JOB_USR_001", "JOB_RES_001", "PERF_FAC_001"):
        shutil.copy(BENCHMARK_ROOT / "tasks" / "specs" / f"{task_id}.json", specs)
    shutil.copytree(BENCHMARK_ROOT / "environments" / "env_01", root / "environments" / "env_01")
    shutil.copytree(BENCHMARK_ROOT / "configs", root / "configs")
    return root


def test_is_run_ready_only_accepts_ready_tasks():
    assert _is_run_ready(_task(task_id="DOCS_USR_001", scoring_readiness="ready")) is True
    assert _is_run_ready(_task(task_id="DOCS_USR_002", scoring_readiness="partial")) is True
    assert _is_run_ready(_task(task_id="DOCS_USR_003", scoring_readiness="blocked")) is False


def test_dev_split_excludes_non_ready_scaffolds(tmp_path: Path):
    specs_dir = tmp_path / "benchmark" / "tasks" / "specs"
    specs_dir.mkdir(parents=True)
    for task in (
        _task(task_id="DOCS_USR_001", scoring_readiness="ready"),
        _task(task_id="JOB_RES_001", scoring_readiness="partial"),
        _task(task_id="DOCS_DES_002", scoring_readiness="blocked"),
    ):
        (specs_dir / f"{task.task_id}.json").write_text(task.model_dump_json(), encoding="utf-8")

    split_ids = _load_split_ids("dev", str(tmp_path / "benchmark"))

    assert split_ids is not None
    assert "DOCS_DES_002" not in split_ids
    assert "JOB_RES_001" in split_ids
    assert "DOCS_USR_001" in split_ids


@pytest.mark.parametrize("split", ["all", "dev", "lite"])
def test_run_all_skips_blocked_tasks_with_a_reason(tmp_path, monkeypatch, run_calls, split):
    from aobench.benchmark.tasks import dataset_splits

    monkeypatch.setattr(
        dataset_splits, "LITE_TASK_IDS", ["JOB_USR_001", "JOB_RES_001", "PERF_FAC_001"]
    )
    root = _mini_corpus(tmp_path)

    result = CliRunner().invoke(
        app,
        [
            "run",
            "all",
            "--adapter",
            "direct_qa",
            "--split",
            split,
            "--no-report",
            "--benchmark",
            str(root),
            "--output",
            str(tmp_path / "runs"),
        ],
    )

    assert result.exit_code == 0, _output(result)
    assert "Skipping PERF_FAC_001: scoring_readiness is blocked" in _output(result)
    assert sorted(run_calls) == ["JOB_RES_001", "JOB_USR_001"]
    assert "Completed: 2/2 tasks" in _output(result)


def test_run_task_refuses_a_blocked_task_before_running(tmp_path, run_calls):
    result = CliRunner().invoke(
        app,
        [
            "run",
            "task",
            "--task",
            "PERF_FAC_001",
            "--env",
            "env_12",
            "--adapter",
            "direct_qa",
            "--no-report",
            "--output",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 2
    assert "PERF_FAC_001" in _output(result)
    assert "scoring_readiness: blocked" in _output(result)
    assert "Traceback" not in _output(result)
    assert run_calls == []
    assert list(tmp_path.iterdir()) == []


def test_run_task_still_runs_a_partial_task(tmp_path, run_calls):
    result = CliRunner().invoke(
        app,
        [
            "run",
            "task",
            "--task",
            "JOB_RES_001",
            "--env",
            "env_01",
            "--adapter",
            "direct_qa",
            "--no-report",
            "--output",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0, _output(result)
    assert run_calls == ["JOB_RES_001"]


def test_robustness_task_refuses_blocked_task_before_runs(tmp_path, run_calls):
    result = CliRunner().invoke(
        app,
        [
            "robustness",
            "task",
            "--task",
            "PERF_FAC_001",
            "--env",
            "env_12",
            "--n",
            "2",
            "--output-root",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 2
    assert "scoring_readiness: blocked" in _output(result)
    assert run_calls == []
    assert list(tmp_path.iterdir()) == []


def test_robustness_all_skips_blocked_before_repeated_runs(tmp_path, run_calls):
    root = _mini_corpus(tmp_path)
    result = CliRunner().invoke(
        app,
        ["robustness", "all", "--n", "2", "--benchmark-root", str(root),
         "--output-root", str(tmp_path / "runs")],
    )
    assert result.exit_code == 0, _output(result)
    assert "Skipping PERF_FAC_001: scoring_readiness is blocked" in _output(result)
    assert sorted(run_calls) == ["JOB_RES_001", "JOB_RES_001", "JOB_USR_001", "JOB_USR_001"]
    assert "2 tasks × 2 runs" in _output(result)


def test_quickstart_autopick_skips_blocked_task(tmp_path, run_calls):
    root = _mini_corpus(tmp_path)
    (root / "tasks" / "specs" / "JOB_USR_001.json").unlink()
    result = CliRunner().invoke(
        app,
        ["quickstart", "--benchmark-root", str(root), "--output", str(tmp_path / "runs")],
    )
    assert result.exit_code == 0, _output(result)
    assert run_calls == ["JOB_RES_001"]
