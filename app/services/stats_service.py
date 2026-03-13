"""Service layer for expense statistics and queries."""

import logging
from datetime import datetime

from zoneinfo import ZoneInfo

from app.config import TIMEZONE
from app.database import get_connection

logger = logging.getLogger(__name__)


def _month_range() -> tuple[str, str]:
    """Return (start, end) ISO strings for the current month in configured timezone."""
    tz = ZoneInfo(TIMEZONE)
    now = datetime.now(tz)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # End: first day of next month
    if now.month == 12:
        end = start.replace(year=now.year + 1, month=1)
    else:
        end = start.replace(month=now.month + 1)
    return start.isoformat(), end.isoformat()


def get_month_total(user_id: int) -> float:
    """Get total expense amount for the current month."""
    start, end = _month_range()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total FROM expenses "
            "WHERE user_id = ? AND created_at >= ? AND created_at < ?",
            (user_id, start, end),
        ).fetchone()
    return float(row["total"])


def get_category_total(user_id: int, category: str) -> float:
    """Get total expense amount for a specific category in the current month."""
    start, end = _month_range()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total FROM expenses "
            "WHERE user_id = ? AND category = ? AND created_at >= ? AND created_at < ?",
            (user_id, category, start, end),
        ).fetchone()
    return float(row["total"])


def get_month_summary(user_id: int) -> list[dict]:
    """Get per-category summary for the current month.

    Returns a list of {"category": str, "total": float} sorted by total descending.
    """
    start, end = _month_range()
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT category, COALESCE(SUM(amount), 0) AS total FROM expenses "
            "WHERE user_id = ? AND created_at >= ? AND created_at < ? "
            "GROUP BY category ORDER BY total DESC",
            (user_id, start, end),
        ).fetchall()
    return [{"category": r["category"], "total": float(r["total"])} for r in rows]
