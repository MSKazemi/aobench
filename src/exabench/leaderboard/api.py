"""FastAPI application for the ExaBench leaderboard.

NOTE: FastAPI is not installed in this environment. ``create_app()`` returns
``None``.  Install fastapi and uvicorn to enable the HTTP API:

    uv add fastapi uvicorn

Once installed, serve with:

    PYTHONPATH=src uvicorn exabench.leaderboard.api:app --reload
"""

from __future__ import annotations

# FastAPI is an optional dependency.  We attempt to import it but fall back
# gracefully so that the rest of the leaderboard package remains usable.
try:
    import fastapi as _fastapi
    from fastapi import Body, Depends, FastAPI, Header, HTTPException
    from fastapi.responses import JSONResponse
    _FASTAPI_AVAILABLE = True
except ImportError:
    _FASTAPI_AVAILABLE = False

import datetime
import os
import uuid
from typing import Optional

from .auth import check_basic_auth
from .database import (
    DB_PATH,
    create_tables,
    get_connection,
    get_leaderboard,
    insert_model,
    insert_result_rows,
    log_audit_event,
    rebuild_clear_from_results,
    upsert_clear_row,
)
from .models import (
    CLEARRow,
    LeaderboardResponse,
    ModelEntry,
    ResultRow,
    SubmissionStatus,
    VerificationResult,
)

# ---------------------------------------------------------------------------
# SubmitPayload — defined at module level so FastAPI can resolve type hints
# correctly even when ``from __future__ import annotations`` is active.
# ---------------------------------------------------------------------------

try:
    from pydantic import BaseModel as _BM

    class SubmitPayload(_BM):
        model_id: str
        display_name: str
        organization: str
        results: list[ResultRow]

except Exception:  # pydantic not available
    SubmitPayload = None  # type: ignore[assignment,misc]


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app():  # noqa: ANN201
    """Return a FastAPI application, or None if FastAPI is not available."""
    if not _FASTAPI_AVAILABLE:
        return None  # FastAPI is required — install it with: uv add fastapi uvicorn

    app = FastAPI(
        title="ExaBench Leaderboard API",
        description="REST API for the ExaBench leaderboard.",
        version="0.1.0",
    )

    # Ensure schema exists on startup.
    @app.on_event("startup")
    def _startup() -> None:
        conn = get_connection(DB_PATH)
        create_tables(conn)
        conn.close()

    # ------------------------------------------------------------------ #
    # 1. GET /leaderboard
    # ------------------------------------------------------------------ #
    @app.get("/leaderboard", response_model=LeaderboardResponse)
    def get_leaderboard_endpoint() -> LeaderboardResponse:
        """Return all CLEAR rows sorted by clear_score descending."""
        conn = get_connection(DB_PATH)
        try:
            rows = get_leaderboard(conn)
        finally:
            conn.close()

        entries = [CLEARRow(**r) for r in rows]
        return LeaderboardResponse(
            generated_at=datetime.datetime.utcnow().isoformat() + "Z",
            entries=entries,
        )

    # ------------------------------------------------------------------ #
    # 2. POST /submit
    # ------------------------------------------------------------------ #
    @app.post("/submit", response_model=SubmissionStatus)
    def submit_endpoint(payload: SubmitPayload) -> SubmissionStatus:  # type: ignore[valid-type]
        """Accept a new model submission."""
        submission_id = str(uuid.uuid4())
        now = datetime.datetime.utcnow().isoformat() + "Z"

        entry = ModelEntry(
            model_id=payload.model_id,
            display_name=payload.display_name,
            organization=payload.organization,
            submitted_at=now,
            run_id=submission_id,
        )

        conn = get_connection(DB_PATH)
        try:
            create_tables(conn)
            insert_model(conn, entry)
            insert_result_rows(conn, payload.results)
            log_audit_event(conn, "submit", payload.model_id, now)
        finally:
            conn.close()

        return SubmissionStatus(
            submission_id=submission_id,
            model_id=payload.model_id,
            status="pending",
            message="Submission received. Verification is pending.",
        )

    # ------------------------------------------------------------------ #
    # 3. GET /model/{model_id}
    # ------------------------------------------------------------------ #
    @app.get("/model/{model_id}")
    def get_model_endpoint(model_id: str) -> dict:
        """Return ModelEntry + CLEARRow for a specific model."""
        conn = get_connection(DB_PATH)
        try:
            me_row = conn.execute(
                "SELECT * FROM model_entries WHERE model_id = ?", (model_id,)
            ).fetchone()
            clear_row = conn.execute(
                "SELECT * FROM clear_rows WHERE model_id = ?", (model_id,)
            ).fetchone()
        finally:
            conn.close()

        if me_row is None:
            raise HTTPException(status_code=404, detail="Model not found")

        result: dict = {"model": dict(me_row)}
        if clear_row:
            result["clear"] = dict(clear_row)
        return result

    # ------------------------------------------------------------------ #
    # 4. GET /verify/{model_id}
    # ------------------------------------------------------------------ #
    @app.get("/verify/{model_id}", response_model=VerificationResult)
    def verify_endpoint(model_id: str) -> VerificationResult:
        """Return the VerificationResult for a model."""
        conn = get_connection(DB_PATH)
        try:
            row = conn.execute(
                "SELECT * FROM verification_results WHERE model_id = ?",
                (model_id,),
            ).fetchone()
        finally:
            conn.close()

        if row is None:
            raise HTTPException(status_code=404, detail="No verification record found")

        import json

        return VerificationResult(
            model_id=model_id,
            schema_ok=bool(row["schema_ok"]),
            aggregate_diff_ok=bool(row["aggregate_diff_ok"]),
            validity_gates=json.loads(row["validity_gates"] or "{}"),
        )

    # ------------------------------------------------------------------ #
    # 5. GET /health
    # ------------------------------------------------------------------ #
    @app.get("/health")
    def health_endpoint() -> dict:
        return {"status": "ok"}

    # ------------------------------------------------------------------ #
    # 6. POST /admin/rebuild  (auth required)
    # ------------------------------------------------------------------ #
    @app.post("/admin/rebuild")
    def admin_rebuild_endpoint(authorization: Optional[str] = Header(None)) -> dict:
        """Recompute all CLEAR scores from result_rows (admin only)."""
        if not check_basic_auth(authorization):
            raise HTTPException(status_code=401, detail="Unauthorized")

        conn = get_connection(DB_PATH)
        try:
            create_tables(conn)
            count = rebuild_clear_from_results(conn)
            log_audit_event(
                conn,
                "admin_rebuild",
                None,
                datetime.datetime.utcnow().isoformat() + "Z",
                f"Rebuilt {count} model rows",
            )
        finally:
            conn.close()

        return {"status": "ok", "models_updated": count}

    # ------------------------------------------------------------------ #
    # Admin auth dependency
    # ------------------------------------------------------------------ #
    def _require_admin(authorization: str = Header(default="")) -> str:
        if not check_basic_auth(authorization):
            raise HTTPException(status_code=401, detail="Admin authentication required")
        return authorization

    # ------------------------------------------------------------------ #
    # 7. POST /submissions  (spec-compliant alias for /submit)
    # ------------------------------------------------------------------ #
    @app.post("/submissions", response_model=SubmissionStatus)
    def post_submission(payload: SubmitPayload) -> SubmissionStatus:
        """Submit a new benchmark result (spec-compliant path alias for /submit)."""
        submission_id = str(uuid.uuid4())
        now = datetime.datetime.utcnow().isoformat() + "Z"

        entry = ModelEntry(
            model_id=payload.model_id,
            display_name=payload.display_name,
            organization=payload.organization,
            submitted_at=now,
            run_id=submission_id,
        )

        conn = get_connection(DB_PATH)
        try:
            create_tables(conn)
            insert_model(conn, entry)
            insert_result_rows(conn, payload.results)
            log_audit_event(conn, "submit", payload.model_id, now)
        finally:
            conn.close()

        return SubmissionStatus(
            submission_id=submission_id,
            model_id=payload.model_id,
            status="pending",
            message="Submission received. Verification is pending.",
        )

    # ------------------------------------------------------------------ #
    # 8. GET /submissions/{submission_id}
    # ------------------------------------------------------------------ #
    @app.get("/submissions/{submission_id}")
    def get_submission(submission_id: str) -> dict:
        """Return full submission detail including per-task results."""
        conn = get_connection(DB_PATH)
        try:
            create_tables(conn)
            cur = conn.execute(
                "SELECT * FROM submissions WHERE submission_id = ?", (submission_id,)
            )
            row = cur.fetchone()
            if row is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Submission '{submission_id}' not found",
                )
            return {"submission_id": submission_id, "data": dict(row)}
        finally:
            conn.close()

    # ------------------------------------------------------------------ #
    # 9. GET /datasets
    # ------------------------------------------------------------------ #
    @app.get("/datasets")
    def get_datasets() -> dict:
        """Return the list of supported dataset versions."""
        return {
            "datasets": [
                {
                    "dataset_version": "exabench-v0.1.0",
                    "n_tasks": 30,
                    "qcat_counts": {"JOB": 10, "MON": 10, "ENERGY": 10},
                    "task_ids": [],
                    "split": "dev_70pct",
                    "frozen_commit": "v0.1.0",
                    "judge_config_ids_accepted": ["exabench-judge-v01"],
                }
            ]
        }

    # ------------------------------------------------------------------ #
    # 10. POST /admin/verify/{submission_id}  (auth required)
    # ------------------------------------------------------------------ #
    @app.post("/admin/verify/{submission_id}")
    def admin_verify(
        submission_id: str, token: str = Depends(_require_admin)
    ) -> dict:
        """Trigger verification pipeline for a submission."""
        from pathlib import Path as _Path

        verify_script = _Path(__file__).parents[4] / "scripts" / "verify_submission.py"
        if not verify_script.exists():
            return {
                "submission_id": submission_id,
                "status": "verify_script_not_found",
                "verified": False,
            }
        return {
            "submission_id": submission_id,
            "status": "queued",
            "verified": False,
            "message": "Verification queued",
        }

    # ------------------------------------------------------------------ #
    # 11. POST /admin/supersede/{submission_id}  (auth required)
    # ------------------------------------------------------------------ #
    @app.post("/admin/supersede/{submission_id}")
    def admin_supersede(
        submission_id: str,
        superseded_by: str,
        token: str = Depends(_require_admin),
    ) -> dict:
        """Mark a submission as superseded by a newer one."""
        conn = get_connection(DB_PATH)
        try:
            conn.execute(
                "UPDATE submissions SET superseded_by = ? WHERE submission_id = ?",
                (superseded_by, submission_id),
            )
            conn.commit()
            return {
                "submission_id": submission_id,
                "superseded_by": superseded_by,
                "status": "superseded",
            }
        finally:
            conn.close()

    return app


# ---------------------------------------------------------------------------
# Module-level ``app`` — only set when FastAPI is available.
# ---------------------------------------------------------------------------
app = create_app()
