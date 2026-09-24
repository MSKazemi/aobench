"""FastAPI application exposing the AOBench benchmark engine (spec-0003).

All endpoints are thin wrappers over ``aobench.service.BenchmarkService`` — no
scoring logic lives here. FastAPI is an optional dependency; ``create_app()``
returns ``None`` when it is absent (mirrors ``leaderboard/api.py``).
"""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING, Any, Iterator, Optional

from pydantic import BaseModel

from aobench.schemas.trace import Trace
from aobench.server.rest.auth import Identity, check_rate_limit, resolve_identity
from aobench.service import (
    AdapterError,
    BenchmarkService,
    EnvNotFound,
    RoleForbidden,
    RunNotFound,
    SplitLockedError,
    TaskBlocked,
    TaskNotFound,
)

try:
    from fastapi import Depends, FastAPI, HTTPException, Query
    from fastapi.responses import StreamingResponse
    from fastapi.security import APIKeyHeader

    _FASTAPI_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only when extra absent
    _FASTAPI_AVAILABLE = False

if TYPE_CHECKING:
    from fastapi import FastAPI as _FastAPIType
    from fastapi import HTTPException as _HTTPExceptionType


# --------------------------------------------------------------------------- #
# Request models (defined at module level; pydantic is a core dep)
# --------------------------------------------------------------------------- #
class RunRequest(BaseModel):
    task_id: str
    env_id: str
    adapter: str = "direct_qa"
    role: Optional[str] = None
    split: str = "dev"
    seed: Optional[int] = None
    replay: str = "live"


class ScoreRequest(BaseModel):
    task_id: str
    trace: Trace


class CompareRequest(BaseModel):
    run_a: str
    run_b: str


class RobustnessRequest(BaseModel):
    task_id: str
    env_id: str
    adapter: str = "direct_qa"
    n: int = 5


# --------------------------------------------------------------------------- #
# Error mapping (spec-0003 R5)
# --------------------------------------------------------------------------- #
def _http_error(exc: Exception) -> "_HTTPExceptionType":
    from fastapi import HTTPException as _HE

    if isinstance(exc, (TaskNotFound, EnvNotFound, RunNotFound)):
        return _HE(status_code=404, detail=str(exc) or exc.__class__.__name__)
    if isinstance(exc, (SplitLockedError, RoleForbidden)):
        return _HE(status_code=403, detail=str(exc) or exc.__class__.__name__)
    if isinstance(exc, TaskBlocked):
        return _HE(status_code=409, detail=str(exc))
    if isinstance(exc, AdapterError):
        return _HE(status_code=502, detail=str(exc))
    return _HE(status_code=500, detail=str(exc))


def create_app(service: Optional[BenchmarkService] = None) -> "Optional[_FastAPIType]":
    """Return a FastAPI app, or None if FastAPI is not installed."""
    if not _FASTAPI_AVAILABLE:
        return None

    svc = service or BenchmarkService(
        benchmark_root=os.environ.get("AOBENCH_BENCHMARK_ROOT", "benchmark"),
        output_root=os.environ.get("AOBENCH_OUTPUT_ROOT", "data/runs"),
    )

    app = FastAPI(
        title="AOBench Engine API",
        description="REST access to the AOBench benchmark engine (run/score/report/trace).",
        version="1.0.0",
    )

    # ---------------- auth dependency ---------------- #
    _api_key_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)

    def require_identity(x_api_key: Optional[str] = Depends(_api_key_scheme)) -> Identity:
        identity = resolve_identity(x_api_key or None)
        if identity is None:
            raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key")
        if not check_rate_limit(identity.tenant):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        return identity

    # ---------------- meta ---------------- #
    @app.get("/health")
    def health() -> dict[str, Any]:
        return {"status": "ok"}

    # ---------------- runs ---------------- #
    @app.post("/v1/runs")
    def create_run(
        body: RunRequest,
        wait: bool = Query(default=True, description="Run synchronously and return the result"),
        identity: Identity = Depends(require_identity),
    ) -> dict[str, Any]:
        role = body.role or (identity.role if identity else None)
        try:
            if wait:
                handle = svc.submit_run(
                    body.task_id, body.env_id, body.adapter,
                    role=role, split=body.split, seed=body.seed, replay=body.replay,
                )
                return handle.model_dump()
            # async: enqueue as a tracked job (poll via /v1/jobs/{id})
            job = svc.enqueue_run(
                body.task_id, body.env_id, body.adapter,
                role=role, split=body.split, seed=body.seed, replay=body.replay,
            )
            return job.model_dump()
        except Exception as exc:  # noqa: BLE001 - mapped to HTTP
            raise _http_error(exc) from exc

    @app.get("/v1/jobs")
    def list_jobs(identity: Identity = Depends(require_identity)) -> dict[str, Any]:
        jobs = svc.list_jobs()
        return {"count": len(jobs), "jobs": [j.model_dump() for j in jobs]}

    @app.get("/v1/jobs/{job_id}")
    def get_job(job_id: str, identity: Identity = Depends(require_identity)) -> dict[str, Any]:
        try:
            return svc.get_job(job_id).model_dump()
        except Exception as exc:  # noqa: BLE001
            raise _http_error(exc) from exc

    @app.get("/v1/runs/{run_id}")
    def get_run(run_id: str, identity: Identity = Depends(require_identity)) -> dict[str, Any]:
        try:
            return svc.get_run(run_id).model_dump()
        except Exception as exc:  # noqa: BLE001
            raise _http_error(exc) from exc

    @app.get("/v1/runs/{run_id}/trace")
    def get_trace(run_id: str, task_id: Optional[str] = None,
                  identity: Identity = Depends(require_identity)) -> dict[str, Any]:
        try:
            return svc.get_trace(run_id, task_id=task_id).model_dump()
        except Exception as exc:  # noqa: BLE001
            raise _http_error(exc) from exc

    @app.get("/v1/runs/{run_id}/report")
    def get_report(run_id: str, format: str = "json",
                   identity: Identity = Depends(require_identity)) -> dict[str, Any]:
        try:
            return svc.get_report(run_id, fmt=format).model_dump()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            raise _http_error(exc) from exc

    @app.get("/v1/runs/{run_id}/events")
    def stream_events(
        run_id: str, identity: Identity = Depends(require_identity)
    ) -> "StreamingResponse":
        """SSE: replay the persisted trace steps then a terminal ``done`` event."""
        try:
            trace = svc.get_trace(run_id)
        except Exception as exc:  # noqa: BLE001
            raise _http_error(exc) from exc

        def _gen() -> Iterator[str]:
            for i, step in enumerate(trace.steps):
                payload = json.dumps({"index": i, "step": step.model_dump(mode="json")})
                yield f"event: step\ndata: {payload}\n\n"
            yield f"event: done\ndata: {json.dumps({'run_id': run_id, 'steps': len(trace.steps)})}\n\n"

        return StreamingResponse(_gen(), media_type="text/event-stream")

    # ---------------- score / compare / robustness ---------------- #
    @app.post("/v1/score")
    def score(body: ScoreRequest, identity: Identity = Depends(require_identity)) -> dict[str, Any]:
        try:
            return svc.score_trace(body.task_id, body.trace).model_dump(mode="json")
        except Exception as exc:  # noqa: BLE001
            raise _http_error(exc) from exc

    @app.post("/v1/compare")
    def compare(body: CompareRequest, identity: Identity = Depends(require_identity)) -> dict[str, Any]:
        try:
            return svc.compare(body.run_a, body.run_b).model_dump()
        except Exception as exc:  # noqa: BLE001
            raise _http_error(exc) from exc

    @app.post("/v1/robustness")
    def robustness(body: RobustnessRequest, identity: Identity = Depends(require_identity)) -> dict[str, Any]:
        try:
            return svc.robustness(body.task_id, body.env_id, body.adapter, body.n).model_dump()
        except Exception as exc:  # noqa: BLE001
            raise _http_error(exc) from exc

    # ---------------- catalog ---------------- #
    @app.get("/v1/tasks")
    def list_tasks(split: Optional[str] = None, qcat: Optional[str] = None,
                   role: Optional[str] = None, identity: Identity = Depends(require_identity)) -> dict[str, Any]:
        tasks = svc.list_tasks(split=split, qcat=qcat, role=role)
        return {"count": len(tasks), "tasks": [t.model_dump() for t in tasks]}

    @app.get("/v1/envs")
    def list_envs(identity: Identity = Depends(require_identity)) -> dict[str, Any]:
        envs = svc.list_envs()
        return {"count": len(envs), "envs": [e.model_dump() for e in envs]}

    @app.get("/v1/datasets")
    def datasets(identity: Identity = Depends(require_identity)) -> dict[str, Any]:
        ds = svc.list_datasets()
        return {"datasets": [d.model_dump() for d in ds]}

    return app


app = create_app()
