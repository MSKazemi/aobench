"""SQLite database layer for the ExaBench leaderboard.

Uses only the Python stdlib ``sqlite3`` module — no SQLAlchemy required.
"""

import json
import sqlite3
from pathlib import Path
from typing import Union

DB_PATH = Path("data/leaderboard/leaderboard.db")


def get_connection(db_path: Union[Path, str] = DB_PATH) -> sqlite3.Connection:
    """Return a sqlite3 connection.

    Pass ``":memory:"`` (the string) to create an in-memory database suitable
    for unit tests.
    """
    if isinstance(db_path, str) and db_path == ":memory:":
        path_str = ":memory:"
    else:
        p = Path(db_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        path_str = str(p)

    conn = sqlite3.connect(path_str)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables(conn: sqlite3.Connection) -> None:
    """Create all 6 tables if they don't exist."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS model_entries (
            model_id TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            organization TEXT NOT NULL,
            submitted_at TEXT NOT NULL,
            run_id TEXT NOT NULL,
            is_verified INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS result_rows (
            result_id TEXT PRIMARY KEY,
            model_id TEXT NOT NULL,
            task_id TEXT NOT NULL,
            role TEXT NOT NULL,
            aggregate_score REAL,
            cup_score REAL,
            engaged INTEGER DEFAULT 0,
            governance_eng REAL
        );
        CREATE TABLE IF NOT EXISTS clear_rows (
            model_id TEXT PRIMARY KEY,
            clear_score REAL,
            E REAL,
            A REAL,
            R REAL,
            C_norm REAL,
            L_norm REAL,
            cup REAL,
            governance_eng REAL,
            engagement_rate REAL,
            n_tasks INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS submissions (
            submission_id TEXT PRIMARY KEY,
            model_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            message TEXT DEFAULT '',
            superseded_by TEXT DEFAULT NULL
        );
        CREATE TABLE IF NOT EXISTS verification_results (
            model_id TEXT PRIMARY KEY,
            schema_ok INTEGER DEFAULT 0,
            aggregate_diff_ok INTEGER DEFAULT 0,
            validity_gates TEXT DEFAULT '{}'
        );
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            model_id TEXT,
            timestamp TEXT NOT NULL,
            details TEXT DEFAULT ''
        );
    """)
    conn.commit()


def insert_model(conn: sqlite3.Connection, entry) -> None:
    """Insert or replace a ModelEntry into model_entries."""
    conn.execute(
        """
        INSERT OR REPLACE INTO model_entries
            (model_id, display_name, organization, submitted_at, run_id, is_verified)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            entry.model_id,
            entry.display_name,
            entry.organization,
            entry.submitted_at,
            entry.run_id,
            int(entry.is_verified),
        ),
    )
    conn.commit()


def insert_result_rows(conn: sqlite3.Connection, rows: list) -> None:
    """Insert a list of ResultRow objects into result_rows."""
    conn.executemany(
        """
        INSERT OR REPLACE INTO result_rows
            (result_id, model_id, task_id, role, aggregate_score, cup_score,
             engaged, governance_eng)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row.result_id,
                row.model_id,
                row.task_id,
                row.role,
                row.aggregate_score,
                row.cup_score,
                int(row.engaged),
                row.governance_eng,
            )
            for row in rows
        ],
    )
    conn.commit()


def upsert_clear_row(conn: sqlite3.Connection, row) -> None:
    """Insert or replace a CLEARRow into clear_rows."""
    conn.execute(
        """
        INSERT OR REPLACE INTO clear_rows
            (model_id, clear_score, E, A, R, C_norm, L_norm, cup,
             governance_eng, engagement_rate, n_tasks)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            row.model_id,
            row.clear_score,
            row.E,
            row.A,
            row.R,
            row.C_norm,
            row.L_norm,
            row.cup,
            row.governance_eng,
            row.engagement_rate,
            row.n_tasks,
        ),
    )
    conn.commit()


def get_leaderboard(conn: sqlite3.Connection) -> list:
    """Return all CLEARRow records sorted by clear_score descending."""
    cursor = conn.execute(
        """
        SELECT model_id, clear_score, E, A, R, C_norm, L_norm, cup,
               governance_eng, engagement_rate, n_tasks
        FROM clear_rows
        ORDER BY clear_score DESC NULLS LAST
        """
    )
    rows = cursor.fetchall()
    return [dict(row) for row in rows]


def log_audit_event(
    conn: sqlite3.Connection,
    event_type: str,
    model_id: str | None,
    timestamp: str,
    details: str = "",
) -> None:
    """Append a row to the audit_log table."""
    conn.execute(
        """
        INSERT INTO audit_log (event_type, model_id, timestamp, details)
        VALUES (?, ?, ?, ?)
        """,
        (event_type, model_id, timestamp, details),
    )
    conn.commit()


def rebuild_clear_from_results(conn: sqlite3.Connection) -> int:
    """Recompute CLEAR scores from result_rows and update clear_rows.

    Returns the number of model rows updated.
    """
    cursor = conn.execute(
        """
        SELECT
            model_id,
            COUNT(*) AS n_tasks,
            AVG(aggregate_score) AS A,
            AVG(cup_score) AS cup,
            AVG(governance_eng) AS governance_eng,
            SUM(engaged) * 1.0 / COUNT(*) AS engagement_rate
        FROM result_rows
        GROUP BY model_id
        """
    )
    rows = cursor.fetchall()

    from .models import CLEARRow

    count = 0
    for r in rows:
        # Minimal CLEAR computation: use aggregate as E, R and cup placeholders.
        A = r["A"]
        cup = r["cup"]
        gov = r["governance_eng"]
        eng_rate = r["engagement_rate"]

        # Simple proxy for composite CLEAR score.
        components = [x for x in [A, cup, gov] if x is not None]
        clear_score = sum(components) / len(components) if components else None

        clear_row = CLEARRow(
            model_id=r["model_id"],
            clear_score=clear_score,
            E=A,           # proxy
            A=A,
            R=cup,         # proxy
            cup=cup,
            governance_eng=gov,
            engagement_rate=eng_rate,
            n_tasks=r["n_tasks"],
        )
        upsert_clear_row(conn, clear_row)
        count += 1

    return count
