"""Expense parser using MiniMax API with regex fallback."""

import json
import logging
import re
from typing import Optional

import httpx

from app.config import CATEGORIES, MINIMAX_API_KEY, MINIMAX_GROUP_ID, MINIMAX_MODEL
from app.models.expense import ParsedExpense

logger = logging.getLogger(__name__)

MINIMAX_API_URL = (
    f"https://api.minimax.chat/v1/text/chatcompletion_v2"
)

SYSTEM_PROMPT = """你是一个家庭记账助手。用户会发送两种消息：
1. 记账消息，例如"午饭 35"、"打车 18"、"奶茶 20"
2. 查询消息，例如"本月花了多少"、"餐饮花了多少"、"本月汇总"

请分析用户消息的意图，返回严格的 JSON 格式（不要包含其他文字）。

--- 记账消息 ---
如果是记账，返回：
{"intent": "expense", "category": "分类", "amount": 金额, "note": "备注"}

可选分类：餐饮、交通、购物、娱乐、生活、医疗、其他
如果用户消息包含多笔消费，返回数组：
[{"intent": "expense", "category": "餐饮", "amount": 35, "note": "午饭"}, {"intent": "expense", "category": "餐饮", "amount": 20, "note": "奶茶"}]

--- 查询消息 ---
如果是查询本月总花费，返回：
{"intent": "query", "query_type": "monthly_total"}

如果是查询某个分类的花费，返回：
{"intent": "query", "query_type": "category_total", "category": "分类名"}

如果是查询本月汇总（按分类），返回：
{"intent": "query", "query_type": "summary"}

--- 无法识别 ---
如果无法识别，返回：
{"intent": "unknown"}

示例：
用户: 午饭 35
返回: {"intent": "expense", "category": "餐饮", "amount": 35, "note": "午饭"}

用户: 打车去公司 18
返回: {"intent": "expense", "category": "交通", "amount": 18, "note": "打车去公司"}

用户: 本月花了多少
返回: {"intent": "query", "query_type": "monthly_total"}

用户: 餐饮花了多少
返回: {"intent": "query", "query_type": "category_total", "category": "餐饮"}

用户: 本月汇总
返回: {"intent": "query", "query_type": "summary"}
"""


async def parse_expense(text: str) -> list[ParsedExpense]:
    """Parse user text via MiniMax API. Returns a list of ParsedExpense.

    Falls back to regex-based parsing if API call fails.
    """
    try:
        result = await _call_minimax(text)
        if result is not None:
            return _build_parsed_list(result, text)
    except Exception:
        logger.exception("MiniMax API call failed, falling back to regex parser")

    # Fallback: simple regex parser
    fallback = _regex_parse(text)
    if fallback:
        return fallback

    return [ParsedExpense(intent="unknown", raw_text=text)]


async def _call_minimax(text: str) -> Optional[dict | list]:
    """Call MiniMax chat completion API and return parsed JSON."""
    headers = {
        "Authorization": f"Bearer {MINIMAX_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MINIMAX_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        "temperature": 0.1,
        "max_tokens": 512,
    }

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(MINIMAX_API_URL, headers=headers, json=payload)
        resp.raise_for_status()

    data = resp.json()
    content: str = data["choices"][0]["message"]["content"]
    logger.debug("MiniMax raw response: %s", content)

    # Strip markdown code fence if present
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)

    return json.loads(content)


def _build_parsed_list(result: dict | list, raw_text: str) -> list[ParsedExpense]:
    """Convert raw JSON result into a list of ParsedExpense."""
    items = result if isinstance(result, list) else [result]
    parsed: list[ParsedExpense] = []
    for item in items:
        intent = item.get("intent", "unknown")
        parsed.append(
            ParsedExpense(
                intent=intent,
                category=item.get("category"),
                amount=item.get("amount"),
                note=item.get("note"),
                query_type=item.get("query_type"),
                raw_text=raw_text,
            )
        )
    return parsed


# --------------- Regex Fallback ---------------

# Matches patterns like "午饭 35", "奶茶20元", "打车 18.5"
_EXPENSE_RE = re.compile(r"^(.+?)\s*(\d+(?:\.\d+)?)\s*元?$")

# Category keyword mapping
_CATEGORY_KEYWORDS: dict[str, str] = {
    "饭": "餐饮", "餐": "餐饮", "吃": "餐饮", "食": "餐饮",
    "奶茶": "餐饮", "咖啡": "餐饮", "外卖": "餐饮", "零食": "餐饮",
    "车": "交通", "地铁": "交通", "公交": "交通", "油": "交通", "打车": "交通",
    "买": "购物", "购": "购物", "超市": "购物", "商场": "购物",
    "电影": "娱乐", "游戏": "娱乐", "唱": "娱乐",
    "水电": "生活", "房租": "生活", "话费": "生活", "网费": "生活",
    "药": "医疗", "医": "医疗", "挂号": "医疗",
}

_QUERY_PATTERNS: list[tuple[re.Pattern, str, Optional[str]]] = [
    (re.compile(r"本月汇总"), "summary", None),
    (re.compile(r"本月花了多少"), "monthly_total", None),
]
# Build per-category query patterns
for _cat in CATEGORIES:
    _QUERY_PATTERNS.append(
        (re.compile(rf"{_cat}花了多少"), "category_total", _cat)
    )


def _guess_category(note: str) -> str:
    """Guess expense category from note text using keyword matching."""
    for keyword, cat in _CATEGORY_KEYWORDS.items():
        if keyword in note:
            return cat
    return "其他"


def _regex_parse(text: str) -> list[ParsedExpense]:
    """Attempt to parse the text using simple regex rules."""
    # Check query patterns first
    for pattern, qtype, cat in _QUERY_PATTERNS:
        if pattern.search(text):
            return [
                ParsedExpense(
                    intent="query",
                    query_type=qtype,
                    category=cat,
                    raw_text=text,
                )
            ]

    # Try expense pattern
    m = _EXPENSE_RE.match(text.strip())
    if m:
        note = m.group(1).strip()
        amount = float(m.group(2))
        category = _guess_category(note)
        return [
            ParsedExpense(
                intent="expense",
                category=category,
                amount=amount,
                note=note,
                raw_text=text,
            )
        ]

    return []
