from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException
from langchain_core.messages import HumanMessage
from sse_starlette.sse import EventSourceResponse

from app.agents.chart_agent import generate_chart_option
from app.agents.direct_chat import stream_direct_reply
from app.agents.intent import should_use_sql_agent
from app.agents.sql_agent import create_sql_agent, stream_nl2sql
from app.api.schemas import ChatRequest
from app.db import app_store
from app.db.database import open_biz_connection
from app.memory.history import load_langchain_messages, save_agent_turn, save_direct_turn

router = APIRouter(prefix="/api", tags=["chat"])


def _sse(event: str, payload: dict) -> dict:
    return {"event": event, "data": json.dumps(payload, ensure_ascii=False)}


async def _chat_event_generator(body: ChatRequest) -> AsyncIterator[dict]:
    session = app_store.get_session(body.session_id)
    if not session:
        yield _sse("error", {"type": "error", "message": "会话不存在"})
        return

    question = body.message.strip()
    lc_messages = load_langchain_messages(body.session_id)
    prior_len = len(lc_messages)
    lc_messages.append(HumanMessage(content=question))

    use_sql = should_use_sql_agent(question)
    conn = None
    try:
        if use_sql:
            conn = open_biz_connection()
            event_iter = stream_nl2sql(create_sql_agent(conn), lc_messages)
        else:
            event_iter = stream_direct_reply(lc_messages[:-1], question)

        final_answer = ""
        sql_text: str | None = None
        query_result: dict | None = None
        usage: dict | None = None
        all_messages: list = []

        for event in event_iter:
            if event.get("type") == "_done_internal":
                final_answer = event.get("final_answer") or ""
                sql_text = event.get("sql_text")
                query_result = event.get("query_result")
                usage = event.get("usage")
                all_messages = event.get("messages") or []
                continue

            yield _sse(event["type"], event)
            await asyncio.sleep(0)

        if use_sql and query_result and query_result.get("row_count", 0) > 0:
            try:
                chart_option = await asyncio.to_thread(
                    generate_chart_option,
                    question,
                    query_result.get("columns", []),
                    query_result.get("rows", []),
                )
                app_store.touch_session(body.session_id, chart_option=chart_option)
                yield _sse("chart", {"type": "chart", "option": chart_option})
            except Exception as e:  # noqa: BLE001
                yield _sse("error", {"type": "error", "message": f"图表生成失败: {e}"})

        if use_sql:
            save_agent_turn(
                body.session_id,
                question,
                prior_len,
                all_messages,
                sql_text,
            )
        else:
            save_direct_turn(body.session_id, question, final_answer)

        done_payload: dict = {"type": "done"}
        if usage:
            done_payload["usage"] = usage
        yield _sse("done", done_payload)

    except Exception as e:  # noqa: BLE001
        yield _sse("error", {"type": "error", "message": str(e)})
    finally:
        if conn is not None:
            conn.close()


@router.post("/chat")
async def chat_stream(body: ChatRequest):
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")
    return EventSourceResponse(_chat_event_generator(body))
