"""Tests for the BenchmarkService façade (spec-0001 acceptance criteria)."""

from __future__ import annotations

import pytest

from aobench.service import (
    AdapterError,
    BenchmarkService,
    RunNotFound,
    SplitLockedError,
    TaskNotFound,
    resolve_adapter,
)

BENCH = "benchmark"


@pytest.fixture()
def svc(tmp_path):
    return BenchmarkService(benchmark_root=BENCH, output_root=str(tmp_path))


@pytest.fixture()
def a_task(svc):
    """A real deterministic task+env pair (direct_qa is deterministic)."""
    tasks = svc.list_tasks()
    assert tasks, "benchmark must contain tasks"
    t = tasks[0]
    return t.task_id, (t.environment_id or "env_01")


# --------------------------------------------------------------------------- #
# Catalog
# --------------------------------------------------------------------------- #
def test_list_tasks_nonempty_and_shaped(svc):
    tasks = svc.list_tasks()
    assert len(tasks) > 0
    t0 = tasks[0]
    assert t0.task_id
    assert t0.qcat is not None


def test_list_tasks_filters(svc):
    all_tasks = svc.list_tasks()
    role = next((t.role for t in all_tasks if t.role), None)
    if role:
        filtered = svc.list_tasks(role=role)
        assert filtered
        assert all(t.role == role for t in filtered)


def test_list_envs(svc):
    envs = svc.list_envs()
    assert envs
    assert all(not e.env_id.startswith("_") for e in envs)


# --------------------------------------------------------------------------- #
# AC1 — sync run + read-back parity
# --------------------------------------------------------------------------- #
def test_submit_run_sync_and_readback(svc, a_task):
    tid, eid = a_task
    handle = svc.submit_run(tid, eid, "direct_qa", split="dev")
    assert handle.status == "completed"
    assert handle.run_id.startswith("run_")
    assert handle.fingerprint is not None
    assert handle.fingerprint.adapter == "direct_qa"

    rec = svc.get_run(handle.run_id)
    assert rec.n_tasks == 1
    assert rec.aggregate_score == handle.aggregate_score

    trace = svc.get_trace(handle.run_id)
    assert len(trace.steps) >= 1

    report = svc.get_report(handle.run_id, "json")
    assert report.format == "json"
    assert report.payload["run_id"] == handle.run_id


def test_submit_run_is_deterministic_for_direct_qa(svc, a_task):
    tid, eid = a_task
    h1 = svc.submit_run(tid, eid, "direct_qa", split="dev")
    h2 = svc.submit_run(tid, eid, "direct_qa", split="dev")
    assert h1.aggregate_score == h2.aggregate_score


# --------------------------------------------------------------------------- #
# AC2 — test split is locked
# --------------------------------------------------------------------------- #
def test_test_split_locked(svc, a_task, monkeypatch):
    monkeypatch.delenv("AOBENCH_UNLOCK_TEST", raising=False)
    tid, eid = a_task
    with pytest.raises(SplitLockedError):
        svc.submit_run(tid, eid, "direct_qa", split="test")


# --------------------------------------------------------------------------- #
# AC3 — typed errors
# --------------------------------------------------------------------------- #
def test_task_not_found(svc):
    with pytest.raises(TaskNotFound):
        svc.submit_run("DOES_NOT_EXIST_999", "env_01", "direct_qa")


def test_env_not_found(svc, a_task):
    from aobench.service import EnvNotFound

    tid, _ = a_task
    with pytest.raises(EnvNotFound):
        svc.submit_run(tid, "env_nonexistent", "direct_qa")


def test_unknown_adapter_raises(svc, a_task):
    tid, eid = a_task
    with pytest.raises(AdapterError):
        svc.submit_run(tid, eid, "totally_bogus")


def test_resolve_adapter_direct_qa():
    a = resolve_adapter("direct_qa")
    assert a.__class__.__name__ == "DirectQAAdapter"


def test_resolve_adapter_unknown():
    with pytest.raises(AdapterError):
        resolve_adapter("nope")


def test_get_run_missing(svc):
    with pytest.raises(RunNotFound):
        svc.get_run("run_does_not_exist")


# --------------------------------------------------------------------------- #
# score_trace parity
# --------------------------------------------------------------------------- #
def test_score_trace_matches_run(svc, a_task):
    tid, eid = a_task
    handle = svc.submit_run(tid, eid, "direct_qa", split="dev")
    trace = svc.get_trace(handle.run_id)
    result = svc.score_trace(tid, trace)
    assert result.task_id == tid
    assert result.aggregate_score == pytest.approx(handle.aggregate_score, abs=1e-9)


# --------------------------------------------------------------------------- #
# AC4 — compare
# --------------------------------------------------------------------------- #
def test_compare(svc, a_task):
    tid, eid = a_task
    a = svc.submit_run(tid, eid, "direct_qa", split="dev")
    b = svc.submit_run(tid, eid, "direct_qa", split="dev")
    cmp = svc.compare(a.run_id, b.run_id)
    assert cmp.run_a == a.run_id and cmp.run_b == b.run_id
    # identical deterministic runs → zero delta
    assert cmp.delta == pytest.approx(0.0, abs=1e-9)


# --------------------------------------------------------------------------- #
# robustness
# --------------------------------------------------------------------------- #
def test_robustness(svc, a_task):
    tid, eid = a_task
    res = svc.robustness(tid, eid, "direct_qa", n=3)
    assert res.n == 3
    assert len(res.run_ids) == 3
    assert res.mean is not None
    # deterministic adapter → zero variance
    assert res.stdev == pytest.approx(0.0, abs=1e-9)


# --------------------------------------------------------------------------- #
# Read-back edge cases (coverage-hardening)
# --------------------------------------------------------------------------- #
def test_get_report_unsupported_format(svc, a_task):
    tid, eid = a_task
    h = svc.submit_run(tid, eid, "direct_qa", split="dev")
    with pytest.raises(ValueError):
        svc.get_report(h.run_id, fmt="pdf")


def test_get_report_json_ok(svc, a_task):
    tid, eid = a_task
    h = svc.submit_run(tid, eid, "direct_qa", split="dev")
    rep = svc.get_report(h.run_id, fmt="clear")
    assert rep.run_id == h.run_id
    assert rep.format == "clear"


def test_get_trace_task_filter_and_missing(svc, a_task):
    tid, eid = a_task
    h = svc.submit_run(tid, eid, "direct_qa", split="dev")
    tr = svc.get_trace(h.run_id, task_id=tid)          # filter hit
    assert tr is not None
    with pytest.raises(RunNotFound):
        svc.get_trace(h.run_id, task_id="NO_SUCH_TASK_123")  # filter miss → no trace


def test_get_run_skips_malformed_result_json(svc, a_task):
    tid, eid = a_task
    h = svc.submit_run(tid, eid, "direct_qa", split="dev")
    # drop a garbage file into the results dir — must be skipped, not crash
    results_dir = svc._output_root / h.run_id / "results"
    (results_dir / "junk_result.json").write_text("{ not valid json", encoding="utf-8")
    rec = svc.get_run(h.run_id)
    assert rec.n_tasks >= 1


def test_list_tasks_qcat_filter(svc):
    all_tasks = svc.list_tasks()
    qcat = next((t.qcat for t in all_tasks if t.qcat), None)
    if qcat:
        filtered = svc.list_tasks(qcat=qcat)
        assert filtered
        assert all(t.qcat == qcat for t in filtered)


def test_list_envs_missing_dir_returns_empty(tmp_path):
    # benchmark_root with no environments/ subdir → []
    empty = BenchmarkService(benchmark_root=str(tmp_path), output_root=str(tmp_path / "out"))
    assert empty.list_envs() == []


# --------------------------------------------------------------------------- #
# Async submission (job registry, F2)
# --------------------------------------------------------------------------- #
def test_enqueue_run_tracked_job(svc, a_task):
    tid, eid = a_task
    job = svc.enqueue_run(tid, eid, "direct_qa", split="dev")
    assert job.state == "completed"
    assert job.run_id is not None
    fetched = svc.get_job(job.job_id)
    assert fetched.job_id == job.job_id
    assert fetched.state == "completed"


def test_enqueue_run_failure_recorded_as_job_state(svc):
    # unknown task → job fails, but enqueue does not raise
    job = svc.enqueue_run("NO_SUCH_TASK_999", "env_01", "direct_qa")
    assert job.state == "failed"
    assert job.error


def test_list_jobs(svc, a_task):
    tid, eid = a_task
    svc.enqueue_run(tid, eid, "direct_qa", split="dev")
    svc.enqueue_run(tid, eid, "direct_qa", split="dev")
    jobs = svc.list_jobs()
    assert len(jobs) == 2
    assert [j.seq for j in jobs] == [1, 2]


def test_get_job_missing_raises(svc):
    with pytest.raises(RunNotFound):
        svc.get_job("job_999999")


# --------------------------------------------------------------------------- #
# Datasets (F5 read side)
# --------------------------------------------------------------------------- #
def test_list_datasets_real_split_counts(svc):
    ds = svc.list_datasets()
    assert len(ds) == 1
    d = ds[0]
    assert d.dataset_version
    assert d.n_tasks > 0
    sc = d.split_counts
    # dev + test partition the corpus; all == total; test is a real subset
    assert sc["all"] == d.n_tasks
    assert sc["dev"] + sc["test"] == sc["all"]
    assert 0 < sc["test"] < sc["all"]
