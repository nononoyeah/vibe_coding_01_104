"""ChatQwQ 集成测试：流式输出 + 函数调用字段探查。

运行方式（在 backend 目录下）:
    1. 复制 .env.example 为 .env 并填写 DASHSCOPE_API_KEY、LLM_MODEL 等
    2. python test_chat_qwq.py

配置项（.env）:
    DASHSCOPE_API_KEY  — 百炼 API Key
    LLM_MODEL          — 模型名，如 qwen3.7-max
    LLM_BASE_URL       — 国内默认 https://dashscope.aliyuncs.com/compatible-mode/v1
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# Windows 终端 UTF-8 输出
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# 确保从 backend 目录加载 .env（与 app/config.py 一致）
_BACKEND_DIR = Path(__file__).resolve().parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from dotenv import load_dotenv

load_dotenv(_BACKEND_DIR / ".env")

from langchain.tools import tool
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_qwq import ChatQwQ

from app.config import settings


def _require_api_key() -> str:
    key = settings.dashscope_api_key.strip()
    if not key:
        env_path = _BACKEND_DIR / ".env"
        print(
            f"错误: 请在 {_BACKEND_DIR / '.env'} 中设置 DASHSCOPE_API_KEY"
            f"（可参考 .env.example）",
            file=sys.stderr,
        )
        sys.exit(1)
    return key


def _pp(label: str, data: Any) -> None:
    print(f"\n--- {label} ---")
    if hasattr(data, "model_dump"):
        print(json.dumps(data.model_dump(), ensure_ascii=False, indent=2, default=str))
    elif isinstance(data, (dict, list)):
        print(json.dumps(data, ensure_ascii=False, indent=2, default=str))
    else:
        print(repr(data))


def test_stream(llm: ChatQwQ) -> None:
    print("\n" + "=" * 60)
    print("【测试 1】流式输出 — 关注 chunk 各字段")
    print("=" * 60)

    messages = [
        HumanMessage(content="用一句话介绍你自己，不要超过30字。"),
    ]

    accumulated_content = ""
    accumulated_reasoning = ""
    chunk_index = 0

    for chunk in llm.stream(messages):
        chunk_index += 1
        content_piece = chunk.content if isinstance(chunk.content, str) else ""
        reasoning_piece = chunk.additional_kwargs.get("reasoning_content", "")

        if content_piece:
            accumulated_content += content_piece
        if reasoning_piece:
            accumulated_reasoning += reasoning_piece

        print(f"\n[chunk #{chunk_index}]")
        print(f"  .content              = {content_piece!r}")
        print(f"  .additional_kwargs.reasoning_content = {reasoning_piece!r}")
        print(f"  .tool_call_chunks     = {getattr(chunk, 'tool_call_chunks', None)}")
        print(f"  .usage_metadata       = {getattr(chunk, 'usage_metadata', None)}")
        print(f"  .response_metadata    = {getattr(chunk, 'response_metadata', None)}")

    print("\n[流式汇总]")
    print(f"  完整 content          = {accumulated_content!r}")
    print(f"  完整 reasoning_content = {accumulated_reasoning!r}")


@tool
def multiply(first_int: int, second_int: int) -> int:
    """将两个整数相乘并返回乘积。"""
    return first_int * second_int


@tool
def get_sales_summary(region: str) -> dict:
    """查询指定区域的销售摘要（模拟数据库返回）。"""
    mock_data = {
        "华东": {"region": "华东", "total_sales": 128_500, "order_count": 342},
        "华北": {"region": "华北", "total_sales": 95_200, "order_count": 218},
    }
    return mock_data.get(region, {"region": region, "total_sales": 0, "order_count": 0})


def test_tool_calling(llm: ChatQwQ) -> None:
    print("\n" + "=" * 60)
    print("【测试 2】函数调用 — 关注 tool_calls 与 ToolMessage 返回值字段")
    print("=" * 60)

    tools = [multiply, get_sales_summary]
    tools_by_name = {t.name: t for t in tools}
    llm_with_tools = llm.bind_tools(tools)

    # --- 2a: 乘法工具 ---
    messages: list = [
        HumanMessage(content="请计算 7 乘以 53 等于多少，必须使用 multiply 工具。"),
    ]

    ai_msg = llm_with_tools.invoke(messages)
    messages.append(ai_msg)

    print("\n[AIMessage 字段]")
    print(f"  .content           = {ai_msg.content!r}")
    print(f"  .reasoning_content = {ai_msg.additional_kwargs.get('reasoning_content', '')!r}")
    _pp("tool_calls", ai_msg.tool_calls)
    _pp("invalid_tool_calls", getattr(ai_msg, "invalid_tool_calls", []))
    _pp("usage_metadata", ai_msg.usage_metadata)
    _pp("response_metadata", ai_msg.response_metadata)

    for tc in ai_msg.tool_calls:
        print(f"\n[执行工具] name={tc['name']!r}, args={tc['args']!r}, id={tc['id']!r}")
        tool_fn = tools_by_name[tc["name"]]
        result = tool_fn.invoke(tc["args"])
        print(f"  工具实际返回值 (Python) = {result!r} (type={type(result).__name__})")

        tool_msg = ToolMessage(
            content=json.dumps(result, ensure_ascii=False)
            if isinstance(result, dict)
            else str(result),
            tool_call_id=tc["id"],
            name=tc["name"],
        )
        messages.append(tool_msg)

        print("[ToolMessage 字段]")
        print(f"  .content       = {tool_msg.content!r}")
        print(f"  .tool_call_id   = {tool_msg.tool_call_id!r}")
        print(f"  .name           = {tool_msg.name!r}")

    final_msg = llm_with_tools.invoke(messages)
    print("\n[模型基于工具结果的最终回复]")
    print(f"  .content           = {final_msg.content!r}")
    print(f"  .reasoning_content = {final_msg.additional_kwargs.get('reasoning_content', '')!r}")
    _pp("usage_metadata", final_msg.usage_metadata)

    # --- 2b: 模拟数据库查询工具 ---
    print("\n" + "-" * 40)
    print("【测试 2b】get_sales_summary 工具（dict 返回值）")
    print("-" * 40)

    messages2: list = [
        HumanMessage(content="查询华东区域的销售摘要，必须使用 get_sales_summary 工具。"),
    ]
    ai_msg2 = llm_with_tools.invoke(messages2)
    messages2.append(ai_msg2)

    _pp("tool_calls", ai_msg2.tool_calls)

    for tc in ai_msg2.tool_calls:
        result = tools_by_name[tc["name"]].invoke(tc["args"])
        tool_msg = ToolMessage(
            content=json.dumps(result, ensure_ascii=False),
            tool_call_id=tc["id"],
            name=tc["name"],
        )
        messages2.append(tool_msg)
        print(f"\n  工具返回 dict → ToolMessage.content = {tool_msg.content}")

    final_msg2 = llm_with_tools.invoke(messages2)
    print(f"\n  最终回复 content = {final_msg2.content!r}")


def main() -> None:
    api_key = _require_api_key()
    model = settings.llm_model
    api_base = settings.llm_base_url

    print(f"模型: {model}")
    print(f"端点: {api_base}")
    print(f"组件: ChatQwQ (langchain-qwq)")

    llm = ChatQwQ(
        model=model,
        api_key=api_key,
        base_url=api_base,
        max_retries=2,
        streaming=True,
    )

    test_stream(llm)
    test_tool_calling(llm)

    print("\n" + "=" * 60)
    print("全部测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
