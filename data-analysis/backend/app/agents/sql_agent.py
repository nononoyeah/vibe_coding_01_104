from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, ToolMessage

from app.agents.sql_tools import build_sql_tools
from app.llm.client import get_llm

SYSTEM_PROMPT = """你是一个 SQL Agent，帮助用户分析电商业务数据库。
目标：把用户问题转为可执行 SQL，并用工具获取答案后给出简短中文结论。

约束：
- 若用户问题与数据库分析无关（身份介绍、闲聊、常识等），直接用中文回答，**不要调用任何工具**。
- 仅当用户提出明确的数据分析需求时，才使用工具；此时必须先调用 sql_db_list_tables，再按需调用 sql_db_schema。
- 执行查询必须使用 sql_db_query；只能写 SELECT。
- 若用户请求写操作（INSERT/UPDATE/DELETE 等）必须拒绝。
- 金额字段 orders.total_amount 单位为分，展示给用户时除以 100 并说明单位为元。
- 优先使用聚合统计，结论简洁清晰。"""


@dataclass
class NL2SQLRunResult:
    messages: list[BaseMessage] = field(default_factory=list)
    final_answer: str = ""
    sql_text: str | None = None
    query_result: dict[str, Any] | None = None
    usage: dict[str, Any] | None = None


def create_sql_agent(conn: sqlite3.Connection):
    return create_agent(
        get_llm(),
        tools=build_sql_tools(conn),
        system_prompt=SYSTEM_PROMPT,
    )


def _parse_tool_content(content: Any) -> Any:
    if isinstance(content, str):
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return content
    return content


def _process_new_messages(
    new_msgs: list[BaseMessage],
    *,
    emitted_sql: set[str],
) -> Iterator[dict[str, Any]]:
    for msg in new_msgs:
        if isinstance(msg, AIMessage):
            for tc in msg.tool_calls or []:
                name = tc.get("name")
                if name != "sql_db_query":
                    continue
                sql = tc.get("args", {}).get("query", "")
                if sql and sql not in emitted_sql:
                    emitted_sql.add(sql)
                    yield {"type": "sql", "sql": sql}
        elif isinstance(msg, ToolMessage) and msg.name == "sql_db_query":
            payload = _parse_tool_content(msg.content)
            if isinstance(payload, dict) and "result" in payload:
                yield {"type": "result", **payload["result"]}
            elif isinstance(payload, dict) and "error" in payload:
                yield {"type": "error", "message": payload["error"]}


def stream_nl2sql(
    agent,
    messages: list[BaseMessage],
) -> Iterator[dict[str, Any]]:
    """Agent 流式：sql/result 随工具执行推送，token 为 AIMessageChunk 增量。"""
    emitted_sql: set[str] = set()
    seen = 0
    answer_parts: list[str] = []
    usage: dict[str, Any] | None = None
    sql_text: str | None = None
    query_result: dict[str, Any] | None = None
    all_messages: list[BaseMessage] = []

    for mode, chunk in agent.stream(
        {"messages": messages},
        stream_mode=["messages", "values"],
    ):
        if mode == "values":
            state = chunk
            msgs = state.get("messages") or []
            all_messages = msgs
            new_msgs = msgs[seen:]
            seen = len(msgs)
            for event in _process_new_messages(new_msgs, emitted_sql=emitted_sql):
                if event["type"] == "sql":
                    sql_text = event["sql"]
                elif event["type"] == "result":
                    query_result = {
                        "columns": event.get("columns", []),
                        "rows": event.get("rows", []),
                        "row_count": event.get("row_count", 0),
                    }
                yield event
            continue

        msg, _metadata = chunk
        if not isinstance(msg, AIMessageChunk):
            continue

        piece = msg.content if isinstance(msg.content, str) else ""
        if piece:
            answer_parts.append(piece)
            yield {"type": "token", "content": piece}

        if msg.usage_metadata:
            usage = dict(msg.usage_metadata)

    final_answer = "".join(answer_parts)
    if not final_answer:
        for msg in reversed(all_messages):
            if isinstance(msg, AIMessage) and msg.content:
                final_answer = msg.content if isinstance(msg.content, str) else str(msg.content)
                if msg.usage_metadata:
                    usage = dict(msg.usage_metadata)
                break

    yield {
        "type": "_done_internal",
        "final_answer": final_answer,
        "sql_text": sql_text,
        "query_result": query_result,
        "usage": usage,
        "messages": all_messages,
    }
