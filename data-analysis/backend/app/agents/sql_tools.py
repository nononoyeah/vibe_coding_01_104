from __future__ import annotations

import sqlite3
import threading
from typing import Any

from langchain.tools import tool

from app.db.database import (
    get_table_schema,
    is_safe_select_only,
    list_tables,
    run_select_query,
)


def build_sql_tools(conn: sqlite3.Connection):
    lock = threading.Lock()

    @tool
    def sql_db_list_tables() -> list[str]:
        """列出数据库中可用的业务表名列表。"""
        with lock:
            return list_tables(conn)

    @tool
    def sql_db_schema(table_name: str) -> dict[str, Any]:
        """获取指定表的 schema（列信息）与少量样例行。"""
        with lock:
            if table_name not in list_tables(conn):
                return {"error": f"unknown_table: {table_name}"}
            return get_table_schema(conn, table_name)

    @tool
    def sql_db_query(query: str) -> dict[str, Any]:
        """执行 SQL 查询并返回结果。只允许 SELECT。"""
        ok, reason = is_safe_select_only(query)
        if not ok:
            return {"error": f"unsafe_sql: {reason}", "query": query}
        try:
            with lock:
                return {"query": query, "result": run_select_query(conn, query)}
        except Exception as e:  # noqa: BLE001
            return {"error": f"sql_error: {type(e).__name__}: {e}", "query": query}

    @tool
    def sql_db_query_checker(query: str) -> dict[str, Any]:
        """在执行前检查 SQL 是否安全、语法是否可能有问题。"""
        ok, reason = is_safe_select_only(query)
        return {"ok": ok, "reason": reason, "query": query}

    return [sql_db_list_tables, sql_db_schema, sql_db_query, sql_db_query_checker]
