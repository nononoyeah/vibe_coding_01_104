from __future__ import annotations

import json
import sqlite3
import time
import uuid
from typing import Any

from app.config import settings
from app.paths import resolve_data_path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  chart_option TEXT,
  created_at REAL NOT NULL,
  updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  sql_text TEXT,
  metadata_json TEXT,
  tool_call_id TEXT,
  tool_name TEXT,
  created_at REAL NOT NULL,
  FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, created_at);
"""


def _connect() -> sqlite3.Connection:
    path = resolve_data_path(settings.app_db_path)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_app_db() -> None:
    conn = _connect()
    try:
        conn.executescript(_SCHEMA)
        conn.commit()
    finally:
        conn.close()


def create_session(title: str | None = None) -> dict[str, Any]:
    now = time.time()
    session_id = str(uuid.uuid4())
    session_title = title or "新会话"
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO sessions(id, title, chart_option, created_at, updated_at) VALUES(?, ?, NULL, ?, ?)",
            (session_id, session_title, now, now),
        )
        conn.commit()
    finally:
        conn.close()
    return {
        "id": session_id,
        "title": session_title,
        "messages": [],
        "chartOption": None,
        "updatedAt": int(now * 1000),
    }


def list_sessions() -> list[dict[str, Any]]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT id, title, chart_option, updated_at FROM sessions ORDER BY updated_at DESC"
        ).fetchall()
        return [
            {
                "id": r["id"],
                "title": r["title"],
                "messages": [],
                "chartOption": json.loads(r["chart_option"]) if r["chart_option"] else None,
                "updatedAt": int(r["updated_at"] * 1000),
            }
            for r in rows
        ]
    finally:
        conn.close()


def delete_session(session_id: str) -> bool:
    conn = _connect()
    try:
        cur = conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def get_session(session_id: str) -> dict[str, Any] | None:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT id, title, chart_option, updated_at FROM sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "title": row["title"],
            "messages": list_messages(session_id, conn=conn),
            "chartOption": json.loads(row["chart_option"]) if row["chart_option"] else None,
            "updatedAt": int(row["updated_at"] * 1000),
        }
    finally:
        conn.close()


def touch_session(session_id: str, chart_option: dict[str, Any] | None = None) -> None:
    now = time.time()
    conn = _connect()
    try:
        if chart_option is not None:
            conn.execute(
                "UPDATE sessions SET updated_at = ?, chart_option = ? WHERE id = ?",
                (now, json.dumps(chart_option, ensure_ascii=False), session_id),
            )
        else:
            conn.execute(
                "UPDATE sessions SET updated_at = ? WHERE id = ?",
                (now, session_id),
            )
        conn.commit()
    finally:
        conn.close()


def list_raw_messages(session_id: str) -> list[dict[str, Any]]:
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT role, content, metadata_json, tool_call_id, tool_name
            FROM messages WHERE session_id = ?
            ORDER BY created_at ASC
            """,
            (session_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def list_messages(
    session_id: str,
    *,
    conn: sqlite3.Connection | None = None,
) -> list[dict[str, Any]]:
    own_conn = conn is None
    db = conn or _connect()
    try:
        rows = db.execute(
            """
            SELECT id, role, content, sql_text, created_at
            FROM messages WHERE session_id = ?
            ORDER BY created_at ASC
            """,
            (session_id,),
        ).fetchall()
        return [
            {
                "id": r["id"],
                "role": "user" if r["role"] == "human" else "assistant",
                "content": r["content"],
                **({"sql": r["sql_text"]} if r["sql_text"] else {}),
                "createdAt": int(r["created_at"] * 1000),
            }
            for r in rows
            if r["role"] in ("human", "ai") and (r["content"] or r["sql_text"])
        ]
    finally:
        if own_conn:
            db.close()


def add_message(
    session_id: str,
    *,
    role: str,
    content: str,
    sql_text: str | None = None,
    metadata: dict[str, Any] | None = None,
    tool_call_id: str | None = None,
    tool_name: str | None = None,
) -> str:
    msg_id = str(uuid.uuid4())
    now = time.time()
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO messages(
              id, session_id, role, content, sql_text, metadata_json,
              tool_call_id, tool_name, created_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                msg_id,
                session_id,
                role,
                content,
                sql_text,
                json.dumps(metadata, ensure_ascii=False) if metadata else None,
                tool_call_id,
                tool_name,
                now,
            ),
        )
        conn.commit()
    finally:
        conn.close()
    touch_session(session_id)
    return msg_id
