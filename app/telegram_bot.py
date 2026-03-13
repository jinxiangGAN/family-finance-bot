"""Telegram bot handlers and command definitions (Agent architecture v2)."""

import io
import logging
from datetime import datetime, time

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from zoneinfo import ZoneInfo

from app.agent import agent_handle, agent_handle_export, agent_handle_image
from app.api_tracker import get_usage_stats
from app.config import (
    ALLOWED_USER_IDS,
    CATEGORIES,
    CURRENCY,
    LLM_PROVIDER,
    TELEGRAM_BOT_TOKEN,
    TIMEZONE,
    WEEKLY_SUMMARY_DAY,
    WEEKLY_SUMMARY_HOUR,
)
from app.scheduler import weekly_summary_job
from app.services.expense_service import delete_last_expense

logger = logging.getLogger(__name__)


# ───────────────── Access control ─────────────────

def _is_allowed(user_id: int) -> bool:
    if not ALLOWED_USER_IDS:
        return True
    return user_id in ALLOWED_USER_IDS


async def _check_access(update: Update) -> bool:
    if _is_allowed(update.effective_user.id):  # type: ignore[union-attr]
        return True
    await update.message.reply_text("⛔ 你没有使用权限。")  # type: ignore[union-attr]
    return False


# ───────────────── Commands ─────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _check_access(update):
        return
    await update.message.reply_text(  # type: ignore[union-attr]
        "👋 欢迎使用家庭记账机器人！\n\n"
        "📝 *记账*：发送文字 `午饭 35` 或拍照发送收据\n"
        "🔍 *查询*：\n"
        "  `本月花了多少` / `老婆花了多少` / `总共花了多少`\n"
        "📊 *汇总*：`本月汇总` / `家庭汇总`\n"
        "💰 *预算*：`餐饮预算设为1000` / `预算还剩多少`\n"
        "🏷 *事件*：`开始日本旅行` / `结束旅行` / `日本旅行汇总`\n"
        "📈 *分析*：`分析一下消费` / `怎么省钱`\n"
        "📷 *收据*：直接发送收据照片自动识别\n"
        "📤 *导出*：/export 导出 CSV\n"
        "🗑 *撤销*：/delete\n"
        "❓ *帮助*：/help\n\n"
        f"💰 默认货币：{CURRENCY} | LLM: {LLM_PROVIDER}",
        parse_mode="Markdown",
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _check_access(update):
        return
    cats = "、".join(CATEGORIES)
    await update.message.reply_text(  # type: ignore[union-attr]
        "📖 *使用帮助*\n\n"
        "*记账*\n"
        "  文字：`午饭 35`  `打车 18`\n"
        "  多币种：`午饭 50 人民币`  `taxi 15 AUD`\n"
        "  拍照：发送收据照片自动识别\n\n"
        "*查询*（三个视角）\n"
        "  👤 `本月花了多少` / `餐饮花了多少`\n"
        "  👫 `老婆花了多少`\n"
        "  👨‍👩‍👧 `总共花了多少` / `家庭汇总`\n\n"
        "*预算管理*\n"
        "  `餐饮预算设为1000` / `总预算设为5000`\n"
        "  `预算还剩多少`\n\n"
        "*事件/旅行标签*\n"
        "  `开始日本旅行` — 后续记账自动标记\n"
        "  `结束旅行` — 关闭标签\n"
        "  `日本旅行汇总` — 查看事件花费和AA结算\n\n"
        "*智能功能*\n"
        "  `分析一下消费` / `怎么省钱` / `财务规划`\n\n"
        "*命令*\n"
        "  /start — 开始\n"
        "  /help — 帮助\n"
        "  /delete — 删除最近一条\n"
        "  /export — 导出 CSV 文件\n"
        "  /usage — API 用量\n\n"
        f"*分类*：{cats}\n"
        f"*货币*：{CURRENCY}（支持 CNY/USD/AUD/JPY/MYR/EUR 等）",
        parse_mode="Markdown",
    )


async def cmd_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _check_access(update):
        return
    user_id = update.effective_user.id  # type: ignore[union-attr]
    deleted = delete_last_expense(user_id)
    if deleted:
        await update.message.reply_text(  # type: ignore[union-attr]
            f"🗑 已删除：{deleted.category} {deleted.amount:.2f} {deleted.currency}（{deleted.note}）"
        )
    else:
        await update.message.reply_text("没有可以删除的记录。")  # type: ignore[union-attr]


async def cmd_export(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Export expenses as CSV file."""
    if not await _check_access(update):
        return
    user_id = update.effective_user.id  # type: ignore[union-attr]
    user_name = update.effective_user.full_name or str(user_id)  # type: ignore[union-attr]

    # Check if user wants family export
    scope = "family" if context.args and context.args[0] == "family" else "me"

    csv_content = await agent_handle_export(user_id, user_name, scope)
    if csv_content:
        tz = ZoneInfo(TIMEZONE)
        now = datetime.now(tz)
        filename = f"expenses_{scope}_{now.strftime('%Y%m%d')}.csv"
        buf = io.BytesIO(csv_content.encode("utf-8-sig"))  # BOM for Excel compat
        buf.name = filename
        await update.message.reply_document(  # type: ignore[union-attr]
            document=buf,
            filename=filename,
            caption=f"📤 {scope} 账单导出完成（{csv_content.count(chr(10))} 条记录）",
        )
    else:
        await update.message.reply_text("没有可导出的数据。")  # type: ignore[union-attr]


async def cmd_usage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _check_access(update):
        return
    stats = get_usage_stats()
    if stats["monthly_limit"] > 0:
        await update.message.reply_text(  # type: ignore[union-attr]
            f"📉 *LLM API 本月用量*（{LLM_PROVIDER}）\n\n"
            f"  已用 tokens：{stats['monthly_used']:,}\n"
            f"  月度上限：{stats['monthly_limit']:,}\n"
            f"  剩余：{stats['remaining']:,}\n"
            f"  使用率：{stats['usage_pct']:.1f}%",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(  # type: ignore[union-attr]
            f"📉 *LLM API 本月用量*（{LLM_PROVIDER}）\n\n"
            f"  已用 tokens：{stats['monthly_used']:,}\n"
            f"  月度上限：无限制",
            parse_mode="Markdown",
        )


# ───────────────── Message handlers ─────────────────

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route text messages through the LLM agent."""
    if not await _check_access(update):
        return

    text = update.message.text.strip()  # type: ignore[union-attr]
    if not text:
        return

    user = update.effective_user  # type: ignore[union-attr]
    user_id: int = user.id
    user_name: str = user.full_name or user.username or str(user_id)

    await update.message.chat.send_action("typing")  # type: ignore[union-attr]

    reply = await agent_handle(text, user_id, user_name)
    await update.message.reply_text(reply)  # type: ignore[union-attr]


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle photo messages: Receipt OCR."""
    if not await _check_access(update):
        return

    user = update.effective_user  # type: ignore[union-attr]
    user_id: int = user.id
    user_name: str = user.full_name or user.username or str(user_id)

    # Get the highest resolution photo
    photo = update.message.photo[-1]  # type: ignore[union-attr]
    file = await photo.get_file()
    image_url = file.file_path  # Telegram file URL

    caption = update.message.caption or ""  # type: ignore[union-attr]

    await update.message.chat.send_action("typing")  # type: ignore[union-attr]

    reply = await agent_handle_image(image_url, caption, user_id, user_name)
    await update.message.reply_text(reply)  # type: ignore[union-attr]


# ───────────────── Bot builder ─────────────────

def build_application() -> Application:
    """Create and configure the Telegram bot Application."""
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("delete", cmd_delete))
    app.add_handler(CommandHandler("export", cmd_export))
    app.add_handler(CommandHandler("usage", cmd_usage))

    # Text messages → agent
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Photo messages → Receipt OCR
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # Weekly summary job
    tz = ZoneInfo(TIMEZONE)
    app.job_queue.run_daily(  # type: ignore[union-attr]
        weekly_summary_job,
        time=time(hour=WEEKLY_SUMMARY_HOUR, minute=0, tzinfo=tz),
        days=(WEEKLY_SUMMARY_DAY,),
        name="weekly_summary",
    )
    logger.info(
        "Weekly summary scheduled: day=%s hour=%s tz=%s",
        WEEKLY_SUMMARY_DAY, WEEKLY_SUMMARY_HOUR, TIMEZONE,
    )

    return app
