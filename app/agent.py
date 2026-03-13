"""LLM Agent: uses function calling to dispatch skills.

Flow:
1. User message (text or image) → LLM (with tool definitions)
2. LLM returns tool_calls → execute skills → get results
3. Feed results back to LLM → LLM generates final human-readable reply

Supports any OpenAI-compatible provider via llm_provider.py.
"""

import json
import logging
import re
from typing import Optional

from app.api_tracker import is_within_limit, record_usage
from app.config import CURRENCY, LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_PROVIDER, LLM_VISION_MODEL
from app.llm_provider import create_provider
from app.skills import TOOL_DEFINITIONS, execute_skill

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = f"""你是一个家庭记账助手机器人。这个家庭有两个人（夫妻）。
默认货币是 {CURRENCY}。

你可以帮助用户：
1. 记录日常支出（调用 record_expense），支持多币种
2. 查询支出情况（调用 query_monthly_total / query_category_total / query_summary）
3. 设置和查看预算（调用 set_budget / query_budget）
4. 分析消费习惯并给出财务建议（调用 get_spending_analysis）
5. 删除误记的支出（调用 delete_last_expense）
6. 管理事件/旅行标签（调用 start_event / stop_event / query_event_summary）
7. 导出数据为 CSV（调用 export_csv）

回复规则：
- 用简洁友好的中文回复
- 金额后面带货币单位
- 如果用户用非 {CURRENCY} 货币记账，回复中提示已自动折算
- 如果 skill 返回了 budget_alert，一定要在回复中提醒用户
- 如果用户的消息包含多笔消费，每笔都分别调用 record_expense
- 对于事件汇总，展示每人花费和 AA 结算建议
"""

VISION_PROMPT = f"""你是一个 OCR 助手。请识别这张图片中的消费信息。

提取以下信息并返回严格的 JSON（不要包含其他文字）：
- 如果是收据/小票，提取每一项消费
- 如果是截图（打车、外卖等），提取总金额

返回格式（数组）：
[{{"category": "分类", "amount": 金额, "note": "备注", "currency": "货币代码"}}]

可选分类：餐饮、交通、购物、娱乐、生活、医疗、其他
默认货币：{CURRENCY}
如果图片中有其他货币（如 ¥ 为 CNY，$ 可能是 USD 或 SGD，请根据上下文判断），请正确填写 currency 字段。

如果无法识别消费信息，返回：
[{{"error": "无法识别"}}]
"""

# Lazy-init provider
_provider = None
_vision_provider = None


def _get_provider():
    global _provider
    if _provider is None and LLM_API_KEY:
        _provider = create_provider(LLM_PROVIDER, LLM_API_KEY, LLM_MODEL, LLM_BASE_URL)
    return _provider


def _get_vision_provider():
    global _vision_provider
    if _vision_provider is None and LLM_API_KEY:
        vision_model = LLM_VISION_MODEL or LLM_MODEL
        _vision_provider = create_provider(LLM_PROVIDER, LLM_API_KEY, vision_model, LLM_BASE_URL)
    return _vision_provider


# ═══════════════════════════════════════════
#  Text message handling
# ═══════════════════════════════════════════

async def agent_handle(text: str, user_id: int, user_name: str) -> str:
    """Main agent entry for text messages."""
    if not LLM_API_KEY or not is_within_limit():
        if not LLM_API_KEY:
            logger.info("No API key, using fallback")
        else:
            logger.warning("API token limit reached, using fallback")
        return _fallback_handle(text, user_id, user_name)

    try:
        return await _llm_agent_loop(text, user_id, user_name)
    except Exception:
        logger.exception("Agent LLM loop failed, falling back")
        return _fallback_handle(text, user_id, user_name)


async def _llm_agent_loop(text: str, user_id: int, user_name: str) -> str:
    provider = _get_provider()
    if provider is None:
        return _fallback_handle(text, user_id, user_name)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": text},
    ]

    resp_msg, usage = await provider.chat_completion(messages, tools=TOOL_DEFINITIONS)
    if usage:
        record_usage(user_id, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0), usage.get("total_tokens", 0), LLM_MODEL)

    tool_calls = resp_msg.get("tool_calls")
    if not tool_calls:
        return resp_msg.get("content", "🤔 我没有理解你的意思，请输入 /help 查看帮助。")

    messages.append(resp_msg)

    for tc in tool_calls:
        func = tc.get("function", {})
        skill_name = func.get("name", "")
        try:
            params = json.loads(func.get("arguments", "{}"))
        except json.JSONDecodeError:
            params = {}

        result = execute_skill(skill_name, user_id, user_name, params)
        logger.info("Skill %s → %s", skill_name, json.dumps(result, ensure_ascii=False)[:200])

        messages.append({
            "role": "tool",
            "tool_call_id": tc.get("id", ""),
            "content": json.dumps(result, ensure_ascii=False),
        })

    final_msg, usage2 = await provider.chat_completion(messages, tools=TOOL_DEFINITIONS)
    if usage2:
        record_usage(user_id, usage2.get("prompt_tokens", 0), usage2.get("completion_tokens", 0), usage2.get("total_tokens", 0), LLM_MODEL)

    return final_msg.get("content", "操作完成。")


# ═══════════════════════════════════════════
#  Image (Receipt OCR) handling
# ═══════════════════════════════════════════

async def agent_handle_image(
    image_url: str, caption: str, user_id: int, user_name: str
) -> str:
    """Handle an image message: OCR → record expenses."""
    if not LLM_API_KEY or not is_within_limit():
        return "📷 收据识别需要 LLM API，当前不可用。请手动输入记账信息。"

    vision = _get_vision_provider()
    if vision is None:
        return "📷 Vision 模型未配置，无法识别收据。"

    try:
        prompt = caption.strip() if caption else "请识别这张图片中的消费信息"
        content, usage = await vision.chat_completion_with_image(
            text=prompt,
            image_url=image_url,
            system_prompt=VISION_PROMPT,
        )
        if usage:
            record_usage(user_id, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0), usage.get("total_tokens", 0), LLM_MODEL)

        # Parse OCR result
        content = content.strip()
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\s*", "", content)
            content = re.sub(r"\s*```$", "", content)

        items = json.loads(content)
        if not isinstance(items, list):
            items = [items]

        if items and items[0].get("error"):
            return f"📷 无法识别图片中的消费信息：{items[0]['error']}\n请手动输入。"

        # Record each expense
        replies = []
        for item in items:
            result = execute_skill("record_expense", user_id, user_name, {
                "category": item.get("category", "其他"),
                "amount": item.get("amount", 0),
                "note": item.get("note", "收据"),
                "currency": item.get("currency", CURRENCY),
            })
            if result.get("success"):
                cur = result.get("currency", CURRENCY)
                line = f"✅ {result['category']}  {result['amount']:.2f} {cur}"
                if result.get("note"):
                    line += f"（{result['note']}）"
                if result.get("amount_sgd") and cur != CURRENCY:
                    line += f" → {result['amount_sgd']:.2f} {CURRENCY}"
                replies.append(line)
                if result.get("budget_alert"):
                    replies.append(result["budget_alert"])

        if replies:
            return "📷 收据识别成功！\n\n" + "\n".join(replies)
        return "📷 未能从图片中提取到消费信息，请手动输入。"

    except Exception:
        logger.exception("Receipt OCR failed")
        return "📷 收据识别失败，请手动输入记账信息。"


# ═══════════════════════════════════════════
#  CSV export helper (returns file content)
# ═══════════════════════════════════════════

async def agent_handle_export(user_id: int, user_name: str, scope: str = "me") -> Optional[str]:
    """Handle /export command. Returns CSV content or None."""
    result = execute_skill("export_csv", user_id, user_name, {"scope": scope})
    if result.get("success"):
        return result.get("csv_content", "")
    return None


# ═══════════════════════════════════════════
#  Regex fallback (when LLM is unavailable)
# ═══════════════════════════════════════════

_EXPENSE_RE = re.compile(r"^(.+?)\s*(\d+(?:\.\d+)?)\s*元?$")

_CATEGORY_KEYWORDS: dict[str, str] = {
    "饭": "餐饮", "餐": "餐饮", "吃": "餐饮", "食": "餐饮",
    "奶茶": "餐饮", "咖啡": "餐饮", "外卖": "餐饮", "零食": "餐饮",
    "车": "交通", "地铁": "交通", "公交": "交通", "打车": "交通",
    "买": "购物", "购": "购物", "超市": "购物",
    "电影": "娱乐", "游戏": "娱乐",
    "水电": "生活", "房租": "生活", "话费": "生活",
    "药": "医疗", "医": "医疗",
}


def _guess_category(note: str) -> str:
    for keyword, cat in _CATEGORY_KEYWORDS.items():
        if keyword in note:
            return cat
    return "其他"


def _fallback_handle(text: str, user_id: int, user_name: str) -> str:
    text = text.strip()

    if "汇总" in text:
        scope = "family" if any(k in text for k in ("家庭", "总", "一共")) else "me"
        if any(k in text for k in ("老婆", "老公", "妻子", "丈夫")):
            scope = "spouse"
        result = execute_skill("query_summary", user_id, user_name, {"scope": scope})
        return _format_summary(result)

    if "花了多少" in text:
        scope = "me"
        if any(k in text for k in ("家庭", "总共", "一共")):
            scope = "family"
        elif any(k in text for k in ("老婆", "老公", "妻子", "丈夫")):
            scope = "spouse"
        from app.config import CATEGORIES
        cat = None
        for c in CATEGORIES:
            if c in text:
                cat = c
                break
        if cat:
            result = execute_skill("query_category_total", user_id, user_name, {"category": cat, "scope": scope})
            return f"📊 {result['label']}本月{result['category']}支出：{result['total']:.2f} {CURRENCY}"
        else:
            result = execute_skill("query_monthly_total", user_id, user_name, {"scope": scope})
            return f"📊 {result['label']}本月总支出：{result['total']:.2f} {CURRENCY}"

    if "预算" in text:
        if any(k in text for k in ("设", "改", "调")):
            return "⚠️ 设置预算请在 LLM 可用时使用，或使用 /help 查看帮助。"
        result = execute_skill("query_budget", user_id, user_name, {})
        return _format_budget(result)

    m = _EXPENSE_RE.match(text)
    if m:
        note = m.group(1).strip()
        amount = float(m.group(2))
        category = _guess_category(note)
        result = execute_skill("record_expense", user_id, user_name, {
            "category": category, "amount": amount, "note": note
        })
        reply = f"✅ 已记录\n{result['category']}  {result['amount']:.2f} {CURRENCY}"
        if result.get("note"):
            reply += f"（{result['note']}）"
        if result.get("budget_alert"):
            reply += f"\n\n{result['budget_alert']}"
        return reply

    return "🤔 无法识别您的消息。请输入记账信息或查询指令，输入 /help 查看帮助。"


def _format_summary(result: dict) -> str:
    summary = result.get("summary", [])
    if not summary:
        return f"📊 {result['label']}本月暂无支出记录。"
    lines = [f"📊 {result['label']} · 本月支出汇总\n"]
    for item in summary:
        lines.append(f"  {item['category']}：{item['total']:.2f} {CURRENCY}")
    lines.append(f"\n💰 合计：{result['grand_total']:.2f} {CURRENCY}")
    return "\n".join(lines)


def _format_budget(result: dict) -> str:
    budgets = result.get("budgets", [])
    if not budgets:
        return "📋 尚未设置任何预算。"
    lines = ["📋 预算使用情况\n"]
    for b in budgets:
        status = "🔴 超支" if b["over_budget"] else "🟢 正常"
        lines.append(
            f"  {b['category']}：{b['spent']:.2f}/{b['monthly_limit']:.2f} {CURRENCY} "
            f"（剩余 {b['remaining']:.2f}）{status}"
        )
    return "\n".join(lines)
