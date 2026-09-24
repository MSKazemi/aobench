"""Integration tests for the benchmark-engine REST API (spec-0003)."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from aobench.server.rest.app import create_app  # noqa: E402
from aobench.server.rest.auth import reset_rate_limits  # noqa: E402
from aobench.service import BenchmarkService  # noqa: E402

KEY = "testkey"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("AOBENCH_API_KEYS", f"{KEY}:admin")
    monkeypatch.delenv("AOBENCH_UNLOCK_TEST", raising=False)
    reset_rate_limits()
    svc = BenchmarkService(benchmark_root="benchmark", output_root=str(tmp_path))
    return TestClient(create_app(svc))


@pytest.fixture()
def a_task():
    svc = BenchmarkService(benchmark_root="benchmark", output_root="data/runs")
    t = svc.list_tasks()[0]
    return t.task_id, (t.environment_id or "env_01")


H = {"X-API-Key": KEY}


def test_health_open(client):
    assert client.get("/health").json() == {"status": "ok"}


# AC1 — sync run + parity
def test_create_run_sync(client, a_task):
    tid, eid = a_task
    r = client.post("/v1/runs?wait=true",
                    json={"task_id": tid, "env_id": eid, "adapter": "direct_qa"}, headers=H)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "completed"
    run_id = body["run_id"]

    rec = client.get(f"/v1/runs/{run_id}", headers=H).json()
    assert rec["n_tasks"] == 1
    assert rec["aggregate_score"] == body["aggregate_score"]

    rep = client.get(f"/v1/runs/{run_id}/report?format=json", headers=H).json()
    assert rep["payload"]["run_id"] == run_id


# AC2 — auth required
def test_missing_key_401(client, a_task):
    tid, eid = a_task
    r = client.post("/v1/runs", json={"task_id": tid, "env_id": eid, "adapter": "direct_qa"})
    assert r.status_code == 401


def test_bad_key_401(client, a_task):
    tid, eid = a_task
    r = client.post("/v1/runs", json={"task_id": tid, "env_id": eid, "adapter": "direct_qa"},
                    headers={"X-API-Key": "wrong"})
    assert r.status_code == 401


# AC3 — test split locked
def test_test_split_403(client, a_task):
    tid, eid = a_task
    r = client.post("/v1/runs",
                    json={"task_id": tid, "env_id": eid, "adapter": "direct_qa", "split": "test"},
                    headers=H)
    assert r.status_code == 403


# AC4 — unknown run
def test_unknown_run_404(client):
    assert client.get("/v1/runs/nope", headers=H).status_code == 404


def test_unknown_task_404(client):
    r = client.post("/v1/runs",
                    json={"task_id": "NO_SUCH_TASK", "env_id": "env_01", "adapter": "direct_qa"},
                    headers=H)
    assert r.status_code == 404


def test_blocked_task_is_client_conflict_not_adapter_failure(client):
    r = client.post(
        "/v1/runs?wait=true",
        json={"task_id": "PERF_FAC_001", "env_id": "env_12", "adapter": "direct_qa"},
        headers=H,
    )
    assert r.status_code == 409
    assert "scoring_readiness: blocked" in r.json()["detail"]


def test_explicit_external_trace_scoring_remains_available_for_blocked_task(client):
    trace = {
        "trace_id": "external_1", "run_id": "adhoc", "task_id": "PERF_FAC_001",
        "role": "facility_admin", "environment_id": "env_12",
        "adapter_name": "external", "final_answer": "2.3 GFLOPS/W", "steps": [],
    }
    r = client.post("/v1/score", json={"task_id": "PERF_FAC_001", "trace": trace}, headers=H)
    assert r.status_code == 200, r.text
    assert isinstance(r.json()["aggregate_score"], float)


def test_bad_adapter_502(client, a_task):
    tid, eid = a_task
    r = client.post("/v1/runs",
                    json={"task_id": tid, "env_id": eid, "adapter": "bogus"}, headers=H)
    assert r.status_code == 502


# AC5 — SSE
def test_sse_events(client, a_task):
    tid, eid = a_task
    run_id = client.post("/v1/runs?wait=true",
                         json={"task_id": tid, "env_id": eid, "adapter": "direct_qa"},
                         headers=H).json()["run_id"]
    r = client.get(f"/v1/runs/{run_id}/events", headers=H)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")
    assert "event: done" in r.text


# AC6 — OpenAPI 3.1 + security scheme
def test_openapi_31_with_apikey(client):
    spec = client.get("/openapi.json").json()
    assert spec["openapi"].startswith("3.1")
    schemes = spec.get("components", {}).get("securitySchemes", {})
    assert any(s.get("name") == "X-API-Key" for s in schemes.values())


# catalog
def test_list_tasks_and_envs(client):
    t = client.get("/v1/tasks", headers=H).json()
    assert t["count"] > 0
    e = client.get("/v1/envs", headers=H).json()
    assert e["count"] > 0


# compare + score
def test_compare(client, a_task):
    tid, eid = a_task
    a = client.post("/v1/runs?wait=true",
                    json={"task_id": tid, "env_id": eid, "adapter": "direct_qa"},
                    headers=H).json()["run_id"]
    b = client.post("/v1/runs?wait=true",
                    json={"task_id": tid, "env_id": eid, "adapter": "direct_qa"},
                    headers=H).json()["run_id"]
    cmp = client.post("/v1/compare", json={"run_a": a, "run_b": b}, headers=H).json()
    assert cmp["delta"] == pytest.approx(0.0, abs=1e-9)


# AC7 — graceful absence handled elsewhere (create_app returns None); here app exists.
def test_app_exists(client):
    assert client.app is not None


# --------------------------------------------------------------------------- #
# Error-branch coverage-hardening
# --------------------------------------------------------------------------- #
def test_http_error_500_fallback():
    from aobench.server.rest.app import _http_error
    exc = _http_error(RuntimeError("unexpected"))
    assert exc.status_code == 500


def test_rate_limit_429(client, a_task, monkeypatch):
    monkeypatch.setenv("AOBENCH_RATE_LIMIT_PER_MIN", "1")
    reset_rate_limits()
    assert client.get("/v1/tasks", headers=H).status_code == 200
    assert client.get("/v1/tasks", headers=H).status_code == 429


def test_report_bad_format_400(client, a_task):
    tid, eid = a_task
    run_id = client.post("/v1/runs?wait=true",
                         json={"task_id": tid, "env_id": eid, "adapter": "direct_qa"},
                         headers=H).json()["run_id"]
    r = client.get(f"/v1/runs/{run_id}/report?format=pdf", headers=H)
    assert r.status_code == 400


def test_report_missing_run_404(client):
    assert client.get("/v1/runs/nope/report", headers=H).status_code == 404


def test_events_missing_run_404(client):
    assert client.get("/v1/runs/nope/events", headers=H).status_code == 404


def test_score_unknown_task_404(client, a_task):
    # run a real task to get a schema-valid trace, then score it against a bogus task
    tid, eid = a_task
    run_id = client.post("/v1/runs?wait=true",
                         json={"task_id": tid, "env_id": eid, "adapter": "direct_qa"},
                         headers=H).json()["run_id"]
    trace = client.get(f"/v1/runs/{run_id}/trace", headers=H).json()
    r = client.post("/v1/score", json={"task_id": "NO_SUCH_TASK", "trace": trace}, headers=H)
    assert r.status_code == 404


def test_compare_missing_run_404(client):
    r = client.post("/v1/compare", json={"run_a": "nope1", "run_b": "nope2"}, headers=H)
    assert r.status_code == 404


def test_robustness_unknown_task_errors(client):
    r = client.post("/v1/robustness",
                    json={"task_id": "NO_SUCH_TASK", "env_id": "env_01",
                          "adapter": "direct_qa", "n": 2},
                    headers=H)
    assert r.status_code in (404, 502)


def test_trace_missing_run_404(client):
    assert client.get("/v1/runs/nope/trace", headers=H).status_code == 404


def test_datasets_endpoint(client):
    r = client.get("/v1/datasets", headers=H)
    assert r.status_code == 200
    d = r.json()["datasets"][0]
    assert d["dataset_version"]
    assert d["split_counts"]["dev"] + d["split_counts"]["test"] == d["split_counts"]["all"]


def test_async_run_and_job_poll(client, a_task):
    tid, eid = a_task
    r = client.post("/v1/runs?wait=false",
                    json={"task_id": tid, "env_id": eid, "adapter": "direct_qa"}, headers=H)
    assert r.status_code == 200, r.text
    job = r.json()
    assert job["state"] == "completed"
    job_id = job["job_id"]

    got = client.get(f"/v1/jobs/{job_id}", headers=H).json()
    assert got["job_id"] == job_id
    assert got["run_id"]

    listing = client.get("/v1/jobs", headers=H).json()
    assert listing["count"] >= 1


def test_job_missing_404(client):
    assert client.get("/v1/jobs/job_999999", headers=H).status_code == 404
