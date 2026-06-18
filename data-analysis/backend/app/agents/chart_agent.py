from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.llm.client import get_llm

CHART_SYSTEM_PROMPT = """你是数据可视化专家。根据用户问题和 SQL 查询结果，生成 ECharts option JSON。
要求：
- 只输出合法 JSON，不要 markdown 代码块，不要额外解释。
- 包含 title、tooltip、legend（如适用）、xAxis/yAxis 或 series。
- 根据数据特征选择 bar、line 或 pie；类别少且为占比用 pie，时间序列用 line，对比用 bar。
- 金额展示为元（若输入为分请先除以 100）。
- 中文标题与轴标签。"""


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if fence:
        text = fence.group(1).strip()
    return json.loads(text)


def generate_chart_option(
    question: str,
    columns: list[str],
    rows: list[list[Any]],
) -> dict[str, Any]:
    if not columns or not rows:
        return {
            "title": {"text": "暂无数据", "left": "center"},
            "series": [],
        }

    llm = get_llm()
    preview_rows = rows[:20]
    human = (
        f"用户问题：{question}\n"
        f"列名：{json.dumps(columns, ensure_ascii=False)}\n"
        f"数据行：{json.dumps(preview_rows, ensure_ascii=False)}\n"
        "请生成 ECharts option JSON。"
    )
    msg = llm.invoke(
        [
            SystemMessage(content=CHART_SYSTEM_PROMPT),
            HumanMessage(content=human),
        ]
    )
    content = msg.content if isinstance(msg.content, str) else str(msg.content)
    try:
        return _extract_json(content)
    except (json.JSONDecodeError, TypeError):
        return _fallback_chart(columns, rows)


def _fallback_chart(columns: list[str], rows: list[list[Any]]) -> dict[str, Any]:
    x_idx = 0
    y_idx = 1 if len(columns) > 1 else 0
    categories = [str(r[x_idx]) for r in rows]
    values = [r[y_idx] for r in rows]
    return {
        "title": {"text": columns[y_idx] if len(columns) > 1 else "统计结果", "left": "center"},
        "tooltip": {"trigger": "axis"},
        "xAxis": {"type": "category", "data": categories},
        "yAxis": {"type": "value"},
        "series": [{"type": "bar", "data": values, "itemStyle": {"color": "#4f46e5"}}],
    }
