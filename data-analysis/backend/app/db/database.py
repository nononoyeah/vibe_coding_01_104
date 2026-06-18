from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any

from app.config import settings
from app.paths import resolve_data_path


@dataclass(frozen=True)
class SQLResult:
    columns: list[str]
    rows: list[list[Any]]

    def to_dict(self) -> dict[str, Any]:
        return {"columns": self.columns, "rows": self.rows, "row_count": len(self.rows)}


def get_biz_db_path() -> str:
    return str(resolve_data_path(settings.biz_db_path))


def open_biz_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(get_biz_db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def fetchall(cur: sqlite3.Cursor) -> SQLResult:
    rows = cur.fetchall()
    columns = [d[0] for d in (cur.description or [])]
    return SQLResult(columns=columns, rows=[list(r) for r in rows])


def list_tables(conn: sqlite3.Connection) -> list[str]:
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;"
    )
    return [r[0] for r in cur.fetchall()]


def get_table_schema(conn: sqlite3.Connection, table_name: str) -> dict[str, Any]:
    cur = conn.execute(f"PRAGMA table_info({table_name});")
    cols = [
        {
            "cid": r[0],
            "name": r[1],
            "type": r[2],
            "notnull": bool(r[3]),
            "default": r[4],
            "pk": bool(r[5]),
        }
        for r in cur.fetchall()
    ]
    sample = fetchall(conn.execute(f"SELECT * FROM {table_name} LIMIT 3;")).to_dict()
    return {"table": table_name, "columns": cols, "sample_rows": sample}


def run_select_query(conn: sqlite3.Connection, query: str) -> dict[str, Any]:
    cur = conn.execute(query)
    return fetchall(cur).to_dict()


def is_safe_select_only(sql: str) -> tuple[bool, str]:
    s = " ".join(sql.strip().split()).lower()
    if not s:
        return False, "SQL 为空"
    forbidden = [
        "insert ",
        "update ",
        "delete ",
        "drop ",
        "alter ",
        "create ",
        "replace ",
        "truncate ",
        "attach ",
        "detach ",
        "pragma ",
    ]
    if any(k in s for k in forbidden):
        return False, "只允许 SELECT，禁止写操作关键字"
    if not s.startswith("select "):
        return False, "只允许 SELECT 开头的查询"
    return True, "ok"
