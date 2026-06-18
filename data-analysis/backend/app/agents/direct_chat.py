from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from langchain_core.messages import AIMessageChunk, BaseMessage, HumanMessage, SystemMessage

from app.llm.client import get_llm

DIRECT_SYSTEM_PROMPT = """你是「智能数据分析助手」，帮助用户分析电商 SQLite 业务库（订单、客户、商品等）。

当用户询问你的身份、能力，或与数据查询无关的闲聊时：
- 用简短、友好的中文直接回答；
- 说明你是数据分析助手，可回答自然语言数据问题；
- **不要**调用数据库，不要编造 SQL 或查询结果。

当用户提出具体数据分析需求时，请提示对方直接描述想查的数据（例如「统计每个城市的客户数量」）。"""


def stream_direct_reply(
    messages: list[BaseMessage],
    question: str,
) -> Iterator[dict[str, Any]]:
    """非 NL2SQL 场景：直连 LLM 流式回复。"""
    llm = get_llm()
    stream_messages: list[BaseMessage] = [
        SystemMessage(content=DIRECT_SYSTEM_PROMPT),
        *messages,
        HumanMessage(content=question),
    ]

    answer_parts: list[str] = []
    usage: dict[str, Any] | None = None

    for chunk in llm.stream(stream_messages):
        if not isinstance(chunk, AIMessageChunk):
            continue
        piece = chunk.content if isinstance(chunk.content, str) else ""
        if piece:
            answer_parts.append(piece)
            yield {"type": "token", "content": piece}
        if chunk.usage_metadata:
            usage = dict(chunk.usage_metadata)

    yield {
        "type": "_done_internal",
        "final_answer": "".join(answer_parts),
        "sql_text": None,
        "query_result": None,
        "usage": usage,
        "messages": [],
    }
