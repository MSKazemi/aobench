"""Unit tests for the ExaBench leaderboard backend (Phase E2.1)."""

from __future__ import annotations

import sqlite3

import pytest
from pydantic import ValidationError

from exabench.leaderboard.auth import check_basic_auth
from exabench.leaderboard.database import (
    create_tables,
    get_connection,
    get_leaderboard,
    insert_model,
    insert_result_rows,
    upsert_clear_row,
)
from exabench.leaderboard.models import (
    CLEARRow,
    LeaderboardResponse,
    ModelEntry,
    ResultRow,
    SubmissionStatus,
    VerificationResult,
)
from exabench.leaderboard.renderer import render_leaderboard_html


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _in_memory_conn() -> sqlite3.Connection:
    """Return a fresh in-memory SQLite connection with schema created."""
    conn = get_connection(":memory:")
    create_tables(conn)
    return conn


def _make_model_entry(**overrides) -> ModelEntry:
    defaults = dict(
        model_id="gpt-4o-test",
        display_name="GPT-4o Test",
        organization="OpenAI",
        submitted_at="2025-01-01T00:00:00Z",
        run_id="run-001",
        is_verified=False,
    )
    defaults.update(overrides)
    return ModelEntry(**defaults)


def _make_result_row(**overrides) -> ResultRow:
    defaults = dict(
        result_id="res-001",
        model_id="gpt-4o-test",
        task_id="TASK_001",
        role="scientific_user",
        aggregate_score=0.75,
        cup_score=0.65,
        engaged=True,
        governance_eng=0.80,
    )
    defaults.update(overrides)
    return ResultRow(**defaults)


def _make_clear_row(**overrides) -> CLEARRow:
    defaults = dict(
        model_id="gpt-4o-test",
        clear_score=0.72,
        E=0.70,
        A=0.75,
        R=0.65,
        C_norm=0.80,
        L_norm=0.60,
        cup=0.65,
        governance_eng=0.80,
        engagement_rate=1.0,
        n_tasks=1,
    )
    defaults.update(overrides)
    return CLEARRow(**defaults)


# ---------------------------------------------------------------------------
# database.py — create_tables
# ---------------------------------------------------------------------------

EXPECTED_TABLES = {
    "model_entries",
    "result_rows",
    "clear_rows",
    "submissions",
    "verification_results",
    "audit_log",
}


def test_create_tables_creates_all_six_tables():
    conn = _in_memory_conn()
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )
    tables = {row[0] for row in cursor.fetchall()}
    assert tables >= EXPECTED_TABLES, f"Missing tables: {EXPECTED_TABLES - tables}"


def test_create_tables_is_idempotent():
    """Calling create_tables twice should not raise."""
    conn = _in_memory_conn()
    create_tables(conn)  # second call
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )
    tables = {row[0] for row in cursor.fetchall()}
    assert tables >= EXPECTED_TABLES


# ---------------------------------------------------------------------------
# database.py — insert_model / retrieve
# ---------------------------------------------------------------------------

def test_insert_model_and_retrieve():
    conn = _in_memory_conn()
    entry = _make_model_entry()
    insert_model(conn, entry)

    row = conn.execute(
        "SELECT * FROM model_entries WHERE model_id = ?", ("gpt-4o-test",)
    ).fetchone()

    assert row is not None
    assert row["display_name"] == "GPT-4o Test"
    assert row["organization"] == "OpenAI"
    assert row["is_verified"] == 0


def test_insert_model_replace():
    """Inserting same model_id twice should update (INSERT OR REPLACE)."""
    conn = _in_memory_conn()
    entry = _make_model_entry()
    insert_model(conn, entry)

    updated = _make_model_entry(display_name="Updated Name", is_verified=True)
    insert_model(conn, updated)

    row = conn.execute(
        "SELECT * FROM model_entries WHERE model_id = ?", ("gpt-4o-test",)
    ).fetchone()
    assert row["display_name"] == "Updated Name"
    assert row["is_verified"] == 1


# ---------------------------------------------------------------------------
# database.py — insert_result_rows / get_leaderboard
# ---------------------------------------------------------------------------

def test_insert_result_rows_single():
    conn = _in_memory_conn()
    rows = [_make_result_row()]
    insert_result_rows(conn, rows)

    cur = conn.execute("SELECT * FROM result_rows WHERE result_id = ?", ("res-001",))
    db_row = cur.fetchone()
    assert db_row is not None
    assert db_row["model_id"] == "gpt-4o-test"
    assert db_row["aggregate_score"] == pytest.approx(0.75)
    assert db_row["engaged"] == 1


def test_insert_result_rows_multiple():
    conn = _in_memory_conn()
    rows = [
        _make_result_row(result_id="res-001"),
        _make_result_row(result_id="res-002", aggregate_score=0.50),
    ]
    insert_result_rows(conn, rows)

    count = conn.execute("SELECT COUNT(*) FROM result_rows").fetchone()[0]
    assert count == 2


def test_get_leaderboard_sorted_by_clear_score():
    conn = _in_memory_conn()

    # Insert two CLEAR rows with different scores.
    upsert_clear_row(conn, _make_clear_row(model_id="model-a", clear_score=0.90, n_tasks=2))
    upsert_clear_row(conn, _make_clear_row(model_id="model-b", clear_score=0.50, n_tasks=1))

    lb = get_leaderboard(conn)
    assert len(lb) == 2
    # Highest score first.
    assert lb[0]["model_id"] == "model-a"
    assert lb[1]["model_id"] == "model-b"


def test_get_leaderboard_empty():
    conn = _in_memory_conn()
    lb = get_leaderboard(conn)
    assert lb == []


def test_get_leaderboard_null_score_last():
    """Models with NULL clear_score should sort after models with a score."""
    conn = _in_memory_conn()
    upsert_clear_row(conn, _make_clear_row(model_id="model-scored", clear_score=0.60))
    upsert_clear_row(conn, _make_clear_row(model_id="model-null", clear_score=None))

    lb = get_leaderboard(conn)
    assert lb[0]["model_id"] == "model-scored"


# ---------------------------------------------------------------------------
# auth.py — check_basic_auth
# ---------------------------------------------------------------------------

def _make_basic_header(username: str, password: str) -> str:
    import base64
    creds = base64.b64encode(f"{username}:{password}".encode()).decode()
    return f"Basic {creds}"


def test_check_basic_auth_correct(monkeypatch):
    monkeypatch.setenv("LEADERBOARD_ADMIN_PASSWORD", "secret123")
    header = _make_basic_header("admin", "secret123")
    assert check_basic_auth(header) is True


def test_check_basic_auth_wrong_password(monkeypatch):
    monkeypatch.setenv("LEADERBOARD_ADMIN_PASSWORD", "secret123")
    header = _make_basic_header("admin", "wrongpass")
    assert check_basic_auth(header) is False


def test_check_basic_auth_wrong_username(monkeypatch):
    monkeypatch.setenv("LEADERBOARD_ADMIN_PASSWORD", "secret123")
    header = _make_basic_header("root", "secret123")
    assert check_basic_auth(header) is False


def test_check_basic_auth_none():
    assert check_basic_auth(None) is False


def test_check_basic_auth_empty_string():
    assert check_basic_auth("") is False


def test_check_basic_auth_no_basic_prefix():
    assert check_basic_auth("Bearer sometoken") is False


def test_check_basic_auth_default_password():
    """Default password is 'changeme' when env var is not set."""
    import os
    os.environ.pop("LEADERBOARD_ADMIN_PASSWORD", None)
    header = _make_basic_header("admin", "changeme")
    assert check_basic_auth(header) is True


def test_check_basic_auth_malformed_base64():
    assert check_basic_auth("Basic !!!not-valid-base64!!!") is False


# ---------------------------------------------------------------------------
# models.py — Pydantic validation
# ---------------------------------------------------------------------------

class TestModelEntry:
    def test_valid(self):
        entry = _make_model_entry()
        assert entry.model_id == "gpt-4o-test"
        assert entry.is_verified is False

    def test_is_verified_default_false(self):
        entry = ModelEntry(
            model_id="m",
            display_name="M",
            organization="Org",
            submitted_at="2025-01-01T00:00:00Z",
            run_id="r1",
        )
        assert entry.is_verified is False

    def test_missing_required_field(self):
        with pytest.raises(ValidationError):
            ModelEntry(model_id="m")  # missing display_name etc.


class TestCLEARRow:
    def test_valid_all_fields(self):
        row = _make_clear_row()
        assert row.model_id == "gpt-4o-test"
        assert row.n_tasks == 1

    def test_optional_fields_default_none(self):
        row = CLEARRow(model_id="m")
        assert row.clear_score is None
        assert row.E is None
        assert row.n_tasks == 0

    def test_missing_model_id(self):
        with pytest.raises(ValidationError):
            CLEARRow()  # model_id is required


class TestVerificationResult:
    def test_valid(self):
        v = VerificationResult(
            model_id="m",
            schema_ok=True,
            aggregate_diff_ok=False,
            validity_gates={"V1": True, "V2": False},
        )
        assert v.schema_ok is True
        assert v.validity_gates["V1"] is True

    def test_default_empty_gates(self):
        v = VerificationResult(
            model_id="m",
            schema_ok=False,
            aggregate_diff_ok=False,
        )
        assert v.validity_gates == {}

    def test_missing_required_fields(self):
        with pytest.raises(ValidationError):
            VerificationResult(model_id="m")  # missing schema_ok, aggregate_diff_ok


class TestResultRow:
    def test_valid(self):
        row = _make_result_row()
        assert row.result_id == "res-001"
        assert row.engaged is True

    def test_optional_scores_default_none(self):
        row = ResultRow(
            result_id="r",
            model_id="m",
            task_id="t",
            role="scientific_user",
        )
        assert row.aggregate_score is None
        assert row.cup_score is None

    def test_engaged_default_false(self):
        row = ResultRow(
            result_id="r",
            model_id="m",
            task_id="t",
            role="scientific_user",
        )
        assert row.engaged is False


class TestSubmissionStatus:
    def test_valid(self):
        s = SubmissionStatus(
            submission_id="sub-1",
            model_id="m",
            status="pending",
        )
        assert s.message == ""

    def test_all_statuses_accepted(self):
        for status in ("pending", "verifying", "verified", "rejected"):
            s = SubmissionStatus(submission_id="s", model_id="m", status=status)
            assert s.status == status


# ---------------------------------------------------------------------------
# renderer.py — render_leaderboard_html
# ---------------------------------------------------------------------------

def _make_leaderboard_response() -> LeaderboardResponse:
    entries = [
        _make_clear_row(model_id="alpha", clear_score=0.90),
        _make_clear_row(model_id="beta", clear_score=0.80),
    ]
    return LeaderboardResponse(
        generated_at="2025-01-01T12:00:00Z",
        entries=entries,
    )


def test_render_leaderboard_html_contains_title(tmp_path):
    response = _make_leaderboard_response()
    out = tmp_path / "leaderboard.html"
    result_path = render_leaderboard_html(response, out)

    assert result_path == out
    html = out.read_text()
    assert "ExaBench Leaderboard" in html


def test_render_leaderboard_html_contains_model_ids(tmp_path):
    response = _make_leaderboard_response()
    out = tmp_path / "leaderboard.html"
    render_leaderboard_html(response, out)
    html = out.read_text()
    assert "alpha" in html
    assert "beta" in html


def test_render_leaderboard_html_contains_scores(tmp_path):
    response = _make_leaderboard_response()
    out = tmp_path / "leaderboard.html"
    render_leaderboard_html(response, out)
    html = out.read_text()
    # Scores formatted to 4 decimal places.
    assert "0.9000" in html
    assert "0.8000" in html


def test_render_leaderboard_html_creates_parent_dirs(tmp_path):
    response = _make_leaderboard_response()
    out = tmp_path / "nested" / "dir" / "lb.html"
    render_leaderboard_html(response, out)
    assert out.exists()


def test_render_leaderboard_html_valid_html_structure(tmp_path):
    response = _make_leaderboard_response()
    out = tmp_path / "lb.html"
    render_leaderboard_html(response, out)
    html = out.read_text()
    assert "<!DOCTYPE html>" in html
    assert "<table>" in html
    assert "</table>" in html
    assert "</html>" in html


def test_render_leaderboard_html_generated_at(tmp_path):
    response = _make_leaderboard_response()
    out = tmp_path / "lb.html"
    render_leaderboard_html(response, out)
    html = out.read_text()
    assert "2025-01-01T12:00:00Z" in html


def test_render_leaderboard_html_empty_entries(tmp_path):
    """Empty leaderboard should still produce valid HTML."""
    response = LeaderboardResponse(
        generated_at="2025-01-01T00:00:00Z",
        entries=[],
    )
    out = tmp_path / "lb.html"
    render_leaderboard_html(response, out)
    html = out.read_text()
    assert "ExaBench Leaderboard" in html
    assert "<table>" in html


# ---------------------------------------------------------------------------
# FastAPI /health endpoint (skipped when FastAPI not installed)
# ---------------------------------------------------------------------------

def test_fastapi_health_endpoint():
    """GET /health returns 200 with status ok (requires FastAPI)."""
    pytest.importorskip("fastapi", reason="fastapi not installed")
    from fastapi.testclient import TestClient
    from exabench.leaderboard.api import create_app

    application = create_app()
    assert application is not None, "create_app() returned None despite FastAPI being available"

    client = TestClient(application)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
