"""Entry point for the Family Finance Telegram Bot."""

import logging
import sys

from app.config import MINIMAX_API_KEY, TELEGRAM_BOT_TOKEN
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
    if not MINIMAX_API_KEY:
        logger.warning("MINIMAX_API_KEY is not set. Will use regex fallback only.")

    # Initialize database
    init_db()

    # Build and run bot (polling mode)
    logger.info("Starting Family Finance Bot (polling mode)...")
    app = build_application()
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
