"""NL2SQL（SQL Agent）集成测试：Qwen3(ChatQwQ) + LangChain create_agent + SQLite 工具。

目的：
1) 端到端跑通「自然语言 → tool_calls → SQL 执行 → 最终回答」
2) 打印并固化 *实际* tool_calls 的 name/args 形状，便于你确定后续接口参数

运行方式（在 backend 目录下）:
    1. 复制 .env.example 为 .env 并填写 DASHSCOPE_API_KEY、LLM_MODEL、LLM_BASE_URL
    2. python test_nl2sql_agent_qwq.py
"""

from __future__ import annotations

import json
import sqlite3
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_qwq import ChatQwQ

from app.config import settings

# Windows 终端 UTF-8 输出
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

_BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(_BACKEND_DIR / ".env")


def _require_api_key() -> str:
    key = settings.dashscope_api_key.strip()
    if not key:
        print(
            f"错误: 请在 {_BACKEND_DIR / '.env'} 中设置 DASHSCOPE_API_KEY（可参考 .env.example）",
            file=sys.stderr,
        )
        sys.exit(1)
    return key


def _json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, default=str)


def _pp(label: str, data: Any) -> None:
    print(f"\n--- {label} ---")
    if hasattr(data, "model_dump"):
        print(_json(data.model_dump()))
    elif isinstance(data, (dict, list)):
        print(_json(data))
    else:
        print(repr(data))


@dataclass(frozen=True)
class SQLResult:
    columns: list[str]
    rows: list[list[Any]]

    def to_dict(self) -> dict[str, Any]:
        return {"columns": self.columns, "rows": self.rows, "row_count": len(self.rows)}


def _init_demo_db(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.executescript(
        """
        DROP TABLE IF EXISTS users;
        DROP TABLE IF EXISTS orders;

        CREATE TABLE users (
          id INTEGER PRIMARY KEY,
          name TEXT NOT NULL,
          city TEXT NOT NULL
        );

        CREATE TABLE orders (
          id INTEGER PRIMARY KEY,
          user_id INTEGER NOT NULL,
          amount REAL NOT NULL,
          created_at TEXT NOT NULL,
          FOREIGN KEY(user_id) REFERENCES users(id)
        );
        """
    )
    cur.executemany(
        "INSERT INTO users(id, name, city) VALUES(?, ?, ?);",
        [
            (1, "张三", "上海"),
            (2, "李四", "北京"),
            (3, "王五", "上海"),
        ],
    )
    cur.executemany(
        "INSERT INTO orders(id, user_id, amount, created_at) VALUES(?, ?, ?, ?);",
        [
            (101, 1, 120.5, "2026-06-01"),
            (102, 1, 39.9, "2026-06-02"),
            (103, 2, 88.0, "2026-06-02"),
            (104, 3, 15.0, "2026-06-03"),
            (105, 3, 260.0, "2026-06-10"),
        ],
    )
    conn.commit()


def _fetchall(cur: sqlite3.Cursor) -> SQLResult:
    rows = cur.fetchall()
    columns = [d[0] for d in (cur.description or [])]
    return SQLResult(columns=columns, rows=[list(r) for r in rows])


def _list_tables(conn: sqlite3.Connection) -> list[str]:
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;"
    )
    return [r[0] for r in cur.fetchall()]


def _get_schema(conn: sqlite3.Connection, table_name: str) -> dict[str, Any]:
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
    sample = _fetchall(
        conn.execute(f"SELECT * FROM {table_name} LIMIT 3;"),
    ).to_dict()
    return {"table": table_name, "columns": cols, "sample_rows": sample}


def _run_query(conn: sqlite3.Connection, query: str) -> dict[str, Any]:
    cur = conn.execute(query)
    return _fetchall(cur).to_dict()


def _is_safe_select_only(sql: str) -> tuple[bool, str]:
    s = " ".join(sql.strip().split()).lower()
    if not s:
        return False, "SQL 为空"
    forbidden = ["insert ", "update ", "delete ", "drop ", "alter ", "create ", "replace ", "truncate "]
    if any(k in s for k in forbidden):
        return False, "只允许 SELECT，禁止写操作关键字"
    if not s.startswith("select "):
        return False, "只允许 SELECT 开头的查询"
    return True, "ok"


def build_sql_tools(conn: sqlite3.Connection):
    lock = threading.Lock()

    @tool
    def sql_db_list_tables() -> list[str]:
        """列出数据库中可用的业务表名列表。"""
        with lock:
            return _list_tables(conn)

    @tool
    def sql_db_schema(table_name: str) -> dict[str, Any]:
        """获取指定表的 schema（列信息）与少量样例行。"""
        with lock:
            if table_name not in _list_tables(conn):
                return {"error": f"unknown_table: {table_name}"}
            return _get_schema(conn, table_name)

    @tool
    def sql_db_query(query: str) -> dict[str, Any]:
        """执行 SQL 查询并返回结果。只允许 SELECT。"""
        ok, reason = _is_safe_select_only(query)
        if not ok:
            return {"error": f"unsafe_sql: {reason}", "query": query}
        try:
            with lock:
                return {"query": query, "result": _run_query(conn, query)}
        except Exception as e:  # noqa: BLE001
            return {"error": f"sql_error: {type(e).__name__}: {e}", "query": query}

    @tool
    def sql_db_query_checker(query: str) -> dict[str, Any]:
        """在执行前检查 SQL 是否安全、语法是否可能有问题。"""
        ok, reason = _is_safe_select_only(query)
        return {"ok": ok, "reason": reason, "query": query}

    return [sql_db_list_tables, sql_db_schema, sql_db_query, sql_db_query_checker]


def _print_messages(messages: Iterable[BaseMessage]) -> None:
    for i, m in enumerate(messages, start=1):
        print(f"\n[message #{i}] type={m.__class__.__name__}")
        if isinstance(m, AIMessage):
            print(f"  content: {m.content!r}")
            print(f"  reasoning_content: {m.additional_kwargs.get('reasoning_content', '')!r}")
            _pp("tool_calls", m.tool_calls)
            _pp("invalid_tool_calls", getattr(m, "invalid_tool_calls", []))
            _pp("response_metadata", m.response_metadata)
            _pp("usage_metadata", m.usage_metadata)
        elif isinstance(m, ToolMessage):
            print(f"  name: {m.name!r}")
            print(f"  tool_call_id: {m.tool_call_id!r}")
            # content 可能是 str，也可能是 list[dict]，统一打印
            print("  content:")
            if isinstance(m.content, str):
                try:
                    print(_json(json.loads(m.content)))
                except Exception:  # noqa: BLE001
                    print(m.content)
            else:
                _pp("content", m.content)
        else:
            print(f"  content: {m.content!r}")


def main() -> None:
    api_key = _require_api_key()

    print(f"langchain: 1.x (当前 requirements: langchain>=0.3.0)")
    print(f"组件: ChatQwQ (langchain-qwq)")
    print(f"模型: {settings.llm_model}")
    print(f"端点: {settings.llm_base_url}")

    llm = ChatQwQ(
        model=settings.llm_model,
        api_key=api_key,
        base_url=settings.llm_base_url,
        max_retries=2,
        streaming=False,
    )

    # LangGraph 的 ToolNode 默认会用线程池并发执行工具调用
    # 因此这里显式允许跨线程使用同一个 connection，并加锁确保串行访问
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    _init_demo_db(conn)
    tools = build_sql_tools(conn)

    system_prompt = (
        "你是一个 SQL Agent。目标：把用户问题转为可执行 SQL，并用工具获取答案。\n"
        "约束：\n"
        "- 必须先调用 sql_db_list_tables 再决定查询哪些表。\n"
        "- 查询前必要时调用 sql_db_schema 获取列信息。\n"
        "- 最终执行 SQL 必须使用 sql_db_query。\n"
        "- 只能写 SELECT；若用户请求写操作必须拒绝。\n"
        "- 优先输出聚合统计，并给出简短结论。\n"
    )

    agent = create_agent(llm, tools=tools, system_prompt=system_prompt, debug=True)

    test_questions = [
        "统计每个城市的用户数量，并按数量从高到低排序。",
        "列出上海用户的总订单金额（按用户汇总），金额保留两位小数。",
    ]

    for q in test_questions:
        print("\n" + "=" * 80)
        print(f"用户问题: {q}")
        print("=" * 80)

        out = agent.invoke({"messages": [HumanMessage(content=q)]})
        messages = out.get("messages") or []
        _print_messages(messages)

        # 重点：汇总本次 run 的 tool_calls args 形状
        tool_calls: list[dict[str, Any]] = []
        for m in messages:
            if isinstance(m, AIMessage) and m.tool_calls:
                tool_calls.extend(m.tool_calls)
        print("\n[本轮 tool_calls 形状汇总（用于确定接口参数）]")
        for tc in tool_calls:
            print(_json({"name": tc.get("name"), "args": tc.get("args"), "id": tc.get("id"), "type": tc.get("type")}))

    print("\n" + "=" * 60)
    print("全部 NL2SQL 测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()

