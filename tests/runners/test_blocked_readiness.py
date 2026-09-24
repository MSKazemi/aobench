"""BenchmarkRunner refuses blocked tasks before the adapter or scorer runs."""

from __future__ import annotations

from pathlib import Path

import pytest

from aobench.adapters.direct_qa_adapter import DirectQAAdapter
from aobench.runners import runner as runner_module
from aobench.runners.runner import BenchmarkRunner, BlockedTaskError

BENCHMARK_ROOT = Path(__file__).parent.parent.parent / "benchmark"


class _SpyAdapter(DirectQAAdapter):
    def __init__(self) -> None:
        super().__init__(answer="spy answer")
        self.calls: list[str] = []

    def run(self, context):
        self.calls.append(context.task.task_id)
        return super().run(context)


@pytest.fixture
def score_calls(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    calls: list[str] = []
    original = runner_module.AggregateScorer.score

    def spy(self, task, trace, *args, **kwargs):
        calls.append(task.task_id)
        return original(self, task, trace, *args, **kwargs)

    monkeypatch.setattr(runner_module.AggregateScorer, "score", spy)
    return calls


@pytest.mark.parametrize(
    ("task_id", "env_id"), [("PERF_FAC_001", "env_12"), ("PERF_DES_001", "env_17")]
)
def test_blocked_task_never_reaches_adapter_or_scorer(tmp_path, score_calls, task_id, env_id):
    adapter = _SpyAdapter()
    runner = BenchmarkRunner(adapter=adapter, benchmark_root=BENCHMARK_ROOT, output_root=tmp_path)

    with pytest.raises(BlockedTaskError, match=f"{task_id} has scoring_readiness: blocked"):
        runner.run(task_id, env_id, run_id="run_blocked")

    assert adapter.calls == []
    assert score_calls == []
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("task_id", ["JOB_USR_001", "JOB_RES_001"])
def test_ready_and_partial_tasks_still_run_and_score(tmp_path, score_calls, task_id):
    adapter = _SpyAdapter()
    runner = BenchmarkRunner(adapter=adapter, benchmark_root=BENCHMARK_ROOT, output_root=tmp_path)

    result = runner.run(task_id, "env_01", run_id="run_ok")

    assert result.task_id == task_id
    assert adapter.calls == [task_id]
    assert score_calls == [task_id]
    assert (tmp_path / "run_ok" / "results" / f"{task_id}_result.json").exists()
