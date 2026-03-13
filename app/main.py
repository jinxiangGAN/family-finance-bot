"""Entry point for the Family Finance Telegram Bot."""

import logging
import sys

from app.config import LLM_API_KEY, LLM_PROVIDER, TELEGRAM_BOT_TOKEN
from app.database import init_db
from app.telegram_bot import build_application

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def main() -> None:
    # Validate required config
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is not set. Please check your .env file.")
        sys.exit(1)
    if not LLM_API_KEY:
        logger.warning("LLM_API_KEY is not set. Will use regex fallback only.")
    else:
        logger.info("LLM provider: %s", LLM_PROVIDER)

    # Initialize database
    init_db()

    # Build and run bot (polling mode)
    logger.info("Starting Family Finance Bot (polling mode)...")
    app = build_application()
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
