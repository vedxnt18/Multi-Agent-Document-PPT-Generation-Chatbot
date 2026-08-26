"""
backend/services/trace_service.py

End-to-end traceability. Every orchestrated request gets a trace record:
what was requested, which agents ran and their status, retrieved chunks/
sources, generated artifacts, validation outcome, timestamps. Persisted to
SQLite so it survives restarts and is queryable via GET /trace/{id}.
"""
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from backend.config import settings, PROJECT_ROOT


def _db_path() -> Path:
    p = PROJECT_ROOT / settings.sqlite_db_path
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


@contextmanager
def _connect():
    conn = sqlite3.connect(str(_db_path()))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS traces (
                trace_id TEXT PRIMARY KEY,
                user_request TEXT NOT NULL,
                created_at TEXT NOT NULL,
                data TEXT NOT NULL
            )
            """
        )


def create_trace(user_request: str, data: dict) -> str:
    init_db()
    trace_id = f"trace_{uuid.uuid4().hex[:10]}"
    with _connect() as conn:
        conn.execute(
            "INSERT INTO traces (trace_id, user_request, created_at, data) VALUES (?, ?, ?, ?)",
            (trace_id, user_request, datetime.now(timezone.utc).isoformat(), json.dumps(data)),
        )
    return trace_id


def get_trace(trace_id: str) -> dict | None:
    init_db()
    with _connect() as conn:
        row = conn.execute("SELECT * FROM traces WHERE trace_id = ?", (trace_id,)).fetchone()
        if row is None:
            return None
        return {
            "trace_id": row["trace_id"],
            "user_request": row["user_request"],
            "created_at": row["created_at"],
            **json.loads(row["data"]),
        }


def list_traces(limit: int = 50) -> list[dict]:
    init_db()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT trace_id, user_request, created_at FROM traces ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
