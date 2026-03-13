"""Telegram bot handlers and command definitions."""

import logging
from datetime import datetime

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from zoneinfo import ZoneInfo

from app.config import ALLOWED_USER_IDS, CATEGORIES, CURRENCY, TELEGRAM_BOT_TOKEN, TIMEZONE
from app.models.expense import Expense, ParsedExpense
from app.parser import parse_expense
from app.services.expense_service import delete_last_expense, save_expense
from app.services.stats_service import (
    get_category_total,
    get_month_summary,
    get_month_total,
)

logger = logging.getLogger(__name__)


# ───────────────── Access control ─────────────────

def _is_allowed(user_id: int) -> bool:
    """Check whether the user is in the allow-list (empty list = allow all)."""
    if not ALLOWED_USER_IDS:
        return True
    return user_id in ALLOWED_USER_IDS


async def _check_access(update: Update) -> bool:
    """Reply with a rejection and return False if the user is not allowed."""
    if _is_allowed(update.effective_user.id):  # type: ignore[union-attr]
        return True
    await update.message.reply_text("⛔ 你没有使用权限。")  # type: ignore[union-attr]
    return False


# ───────────────── Commands ─────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    if not await _check_access(update):
        return
    await update.message.reply_text(  # type: ignore[union-attr]
        "👋 欢迎使用家庭记账机器人！\n\n"
        "📝 *记账*：直接发送消息，例如 `午饭 35`\n"
        "🔍 *查询*：发送 `本月花了多少` 或 `餐饮花了多少`\n"
        "📊 *汇总*：发送 `本月汇总`\n"
        "🗑 *撤销*：/delete 删除最近一条记录\n"
        "❓ *帮助*：/help\n\n"
        f"💰 默认货币：{CURRENCY}",
        parse_mode="Markdown",
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    if not await _check_access(update):
        return
    cats = "、".join(CATEGORIES)
    await update.message.reply_text(  # type: ignore[union-attr]
        "📖 *使用帮助*\n\n"
        "*记账方式*\n"
        "直接发送文字即可记账：\n"
        "  `午饭 35`\n"
        "  `打车 18`\n"
        "  `奶茶 20`\n\n"
        "*查询方式*\n"
        "  `本月花了多少` — 本月总支出\n"
        "  `餐饮花了多少` — 按分类查询\n"
        "  `本月汇总` — 按分类汇总\n\n"
        "*命令*\n"
        "  /start — 开始\n"
        "  /help — 帮助\n"
        "  /delete — 删除最近一条记录\n"
        "  /summary — 本月汇总\n\n"
        f"*支持分类*：{cats}\n"
        f"*默认货币*：{CURRENCY}",
        parse_mode="Markdown",
    )


async def cmd_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /delete command — remove the user's most recent expense."""
    if not await _check_access(update):
        return
    user_id = update.effective_user.id  # type: ignore[union-attr]
    deleted = delete_last_expense(user_id)
    if deleted:
        await update.message.reply_text(  # type: ignore[union-attr]
            f"🗑 已删除最近一条记录：\n"
            f"{deleted.category} {deleted.amount:.2f} {CURRENCY}（{deleted.note}）"
        )
    else:
        await update.message.reply_text("没有可以删除的记录。")  # type: ignore[union-attr]


async def cmd_summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /summary command — show monthly summary."""
    if not await _check_access(update):
        return
    user_id = update.effective_user.id  # type: ignore[union-attr]
    await _reply_summary(update, user_id)


# ───────────────── Message handler ─────────────────

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle free-text messages: parse intent and dispatch."""
    if not await _check_access(update):
        return

    text = update.message.text.strip()  # type: ignore[union-attr]
    if not text:
        return

    user = update.effective_user  # type: ignore[union-attr]
    user_id: int = user.id
    user_name: str = user.full_name or user.username or str(user_id)

    parsed_list: list[ParsedExpense] = await parse_expense(text)

    for parsed in parsed_list:
        if parsed.intent == "expense":
            await _handle_expense(update, user_id, user_name, parsed)
        elif parsed.intent == "query":
            await _handle_query(update, user_id, parsed)
        else:
            await update.message.reply_text(  # type: ignore[union-attr]
                "🤔 无法识别您的消息，请输入记账信息或查询指令。\n"
                "输入 /help 查看使用帮助。"
            )


async def _handle_expense(
    update: Update, user_id: int, user_name: str, parsed: ParsedExpense
) -> None:
    """Save a single expense and reply confirmation."""
    tz = ZoneInfo(TIMEZONE)
    now = datetime.now(tz)
    expense = Expense(
        user_id=user_id,
        user_name=user_name,
        category=parsed.category or "其他",
        amount=parsed.amount or 0.0,
        note=parsed.note or "",
        created_at=now.isoformat(),
    )
    save_expense(expense)
    await update.message.reply_text(  # type: ignore[union-attr]
        f"✅ 已记录\n"
        f"{expense.category}  {expense.amount:.2f} {CURRENCY}"
        f"{'  (' + expense.note + ')' if expense.note else ''}"
    )


async def _handle_query(update: Update, user_id: int, parsed: ParsedExpense) -> None:
    """Dispatch query by query_type."""
    qtype = parsed.query_type
    if qtype == "monthly_total":
        total = get_month_total(user_id)
        await update.message.reply_text(  # type: ignore[union-attr]
            f"📊 本月总支出：{total:.2f} {CURRENCY}"
        )
    elif qtype == "category_total":
        cat = parsed.category or "其他"
        total = get_category_total(user_id, cat)
        await update.message.reply_text(  # type: ignore[union-attr]
            f"📊 本月{cat}支出：{total:.2f} {CURRENCY}"
        )
    elif qtype == "summary":
        await _reply_summary(update, user_id)
    else:
        await update.message.reply_text("🤔 暂不支持该查询类型。")  # type: ignore[union-attr]


async def _reply_summary(update: Update, user_id: int) -> None:
    """Build and send a monthly summary message."""
    summary = get_month_summary(user_id)
    if not summary:
        await update.message.reply_text("📊 本月暂无支出记录。")  # type: ignore[union-attr]
        return

    grand_total = sum(item["total"] for item in summary)
    lines = [f"📊 *本月支出汇总*\n"]
    for item in summary:
        lines.append(f"  {item['category']}：{item['total']:.2f} {CURRENCY}")
    lines.append(f"\n💰 *合计*：{grand_total:.2f} {CURRENCY}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")  # type: ignore[union-attr]


# ───────────────── Bot builder ─────────────────

def build_application() -> Application:
    """Create and configure the Telegram bot Application."""
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("delete", cmd_delete))
    app.add_handler(CommandHandler("summary", cmd_summary))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    return app
