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
    from fastapi import Depends, FastAPI, Header, HTTPException
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
    class SubmitPayload(_fastapi.BaseModel if _FASTAPI_AVAILABLE else object):
        model_id: str
        display_name: str
        organization: str
        results: list[ResultRow]

    if _FASTAPI_AVAILABLE:
        from pydantic import BaseModel as _BM

        class SubmitPayload(_BM):  # type: ignore[no-redef]
            model_id: str
            display_name: str
            organization: str
            results: list[ResultRow]

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

    return app


# ---------------------------------------------------------------------------
# Module-level ``app`` — only set when FastAPI is available.
# ---------------------------------------------------------------------------
app = create_app()
