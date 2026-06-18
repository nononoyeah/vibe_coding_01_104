from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage

from app.db import app_store

MAX_HISTORY_MESSAGES = 40


def load_langchain_messages(session_id: str) -> list[BaseMessage]:
    rows = app_store.list_raw_messages(session_id)[-MAX_HISTORY_MESSAGES:]
    lc_messages: list[BaseMessage] = []
    for row in rows:
        role = row["role"]
        if role == "human":
            lc_messages.append(HumanMessage(content=row["content"]))
        elif role == "ai":
            metadata = json.loads(row["metadata_json"]) if row["metadata_json"] else {}
            tool_calls = metadata.get("tool_calls")
            if tool_calls:
                lc_messages.append(
                    AIMessage(
                        content=row["content"] or "",
                        tool_calls=tool_calls,
                        additional_kwargs=metadata.get("additional_kwargs", {}),
                    )
                )
            else:
                lc_messages.append(AIMessage(content=row["content"]))
        elif role == "tool":
            lc_messages.append(
                ToolMessage(
                    content=row["content"],
                    tool_call_id=row["tool_call_id"] or "",
                    name=row["tool_name"] or "",
                )
            )
    return lc_messages


def save_direct_turn(session_id: str, user_text: str, answer: str) -> None:
    app_store.add_message(session_id, role="human", content=user_text)
    app_store.add_message(session_id, role="ai", content=answer)


def save_agent_turn(
    session_id: str,
    user_text: str,
    prior_len: int,
    all_messages: list[BaseMessage],
    sql_text: str | None,
) -> None:
    app_store.add_message(session_id, role="human", content=user_text)
    new_msgs = all_messages[prior_len:]
    for msg in new_msgs:
        if isinstance(msg, HumanMessage):
            continue
        if isinstance(msg, AIMessage):
            metadata: dict[str, Any] = {}
            if msg.tool_calls:
                metadata["tool_calls"] = msg.tool_calls
            reasoning = msg.additional_kwargs.get("reasoning_content")
            if reasoning:
                metadata["additional_kwargs"] = {"reasoning_content": reasoning}
            is_final = (msg.response_metadata or {}).get("finish_reason") == "stop" and bool(
                msg.content
            )
            app_store.add_message(
                session_id,
                role="ai",
                content=msg.content if isinstance(msg.content, str) else "",
                sql_text=sql_text if is_final else None,
                metadata=metadata or None,
            )
        elif isinstance(msg, ToolMessage):
            content = msg.content if isinstance(msg.content, str) else json.dumps(msg.content)
            app_store.add_message(
                session_id,
                role="tool",
                content=content,
                tool_call_id=msg.tool_call_id,
                tool_name=msg.name,
            )
