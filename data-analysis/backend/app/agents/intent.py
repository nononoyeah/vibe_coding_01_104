from __future__ import annotations

import re

# 与数据库分析无关、应直接对话回复的意图
_CHITCHAT_RE = re.compile(
    r"(你是谁|你是什么|你叫什么|介绍一下你|你能做什么|你会什么|你可以做什么|"
    r"你是干什么的|你是干嘛的|怎么用你|如何使用|"
    r"^你好[吗呀]?[！!？?。.]*$|"
    r"^谢谢[你您]?[！!？?。.]*$|^感谢[你您]?[！!？?。.]*$)",
    re.IGNORECASE,
)

_DATA_HINT_RE = re.compile(
    r"(统计|查询|查一下|多少|几个|数量|排名|趋势|分析|对比|占比|平均|总计|分组|"
    r"订单|用户|客户|商品|产品|销售|金额|收入|城市|地区|库存|"
    r"select|count|sum|avg|group\s+by)",
    re.IGNORECASE,
)


def should_use_sql_agent(question: str) -> bool:
    """非数据分析类问题走直连 LLM，避免误调 SQL 工具。"""
    text = question.strip()
    if not text:
        return False
    if _CHITCHAT_RE.search(text):
        return False
    if _DATA_HINT_RE.search(text):
        return True
    # 短句且无数据关键词，视为闲聊
    if len(text) <= 16:
        return False
    return True
