"""Application configuration loaded from environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")

# MiniMax
MINIMAX_API_KEY: str = os.getenv("MINIMAX_API_KEY", "")
MINIMAX_GROUP_ID: str = os.getenv("MINIMAX_GROUP_ID", "")
MINIMAX_MODEL: str = os.getenv("MINIMAX_MODEL", "abab6.5s-chat")

# Database
DATABASE_PATH: str = os.getenv("DATABASE_PATH", "data/expenses.db")

# Allowed Telegram user IDs (comma-separated)
_allowed = os.getenv("ALLOWED_USER_IDS", "")
ALLOWED_USER_IDS: list[int] = [int(uid.strip()) for uid in _allowed.split(",") if uid.strip()]

# Timezone
TIMEZONE: str = os.getenv("TIMEZONE", "Asia/Singapore")

# Currency
CURRENCY: str = os.getenv("CURRENCY", "SGD")

# Expense categories
CATEGORIES: list[str] = ["餐饮", "交通", "购物", "娱乐", "生活", "医疗", "其他"]
