from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException
from langchain_core.messages import HumanMessage
from sse_starlette.sse import EventSourceResponse

from app.agents.chart_agent import generate_chart_option
from app.agents.sql_agent import create_sql_agent, stream_nl2sql
from app.api.schemas import ChatRequest
from app.db import app_store
from app.db.database import open_biz_connection
from app.memory.history import load_langchain_messages, save_agent_turn

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

    conn = open_biz_connection()
    try:
        agent = create_sql_agent(conn)
        final_answer = ""
        sql_text: str | None = None
        query_result: dict | None = None
        usage: dict | None = None
        all_messages = []

        for event in stream_nl2sql(agent, lc_messages):
            if event.get("type") == "_done_internal":
                final_answer = event.get("final_answer") or ""
                sql_text = event.get("sql_text")
                query_result = event.get("query_result")
                usage = event.get("usage")
                all_messages = event.get("messages") or []
                continue

            yield _sse(event["type"], event)
            await asyncio.sleep(0)

        if query_result and query_result.get("row_count", 0) > 0:
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

        save_agent_turn(
            body.session_id,
            question,
            prior_len,
            all_messages,
            sql_text,
        )

        done_payload: dict = {"type": "done"}
        if usage:
            done_payload["usage"] = usage
        yield _sse("done", done_payload)

    except Exception as e:  # noqa: BLE001
        yield _sse("error", {"type": "error", "message": str(e)})
    finally:
        conn.close()


@router.post("/chat")
async def chat_stream(body: ChatRequest):
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")
    return EventSourceResponse(_chat_event_generator(body))
