"""Service layer for expense statistics and queries."""

import logging
from datetime import datetime
from typing import Optional

from zoneinfo import ZoneInfo

from app.config import FAMILY_MEMBERS, TIMEZONE
from app.database import get_connection

logger = logging.getLogger(__name__)


def _month_range() -> tuple[str, str]:
    """Return (start, end) ISO strings for the current month in configured timezone."""
    tz = ZoneInfo(TIMEZONE)
    now = datetime.now(tz)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if now.month == 12:
        end = start.replace(year=now.year + 1, month=1)
    else:
        end = start.replace(month=now.month + 1)
    return start.isoformat(), end.isoformat()


def get_spouse_id(my_user_id: int) -> Optional[int]:
    """Return the other family member's user_id, or None if not configured."""
    for uid in FAMILY_MEMBERS:
        if uid != my_user_id:
            return uid
    return None


def get_member_name(user_id: int) -> str:
    """Return the display name for a family member."""
    return FAMILY_MEMBERS.get(user_id, str(user_id))


def resolve_user_ids(scope: str, my_user_id: int) -> Optional[list[int]]:
    """Resolve scope to a list of user_ids.

    - "me"     → [my_user_id]
    - "spouse" → [spouse_id] (or None if unknown)
    - "family" → None (meaning all users, no filter)
    """
    if scope == "me":
        return [my_user_id]
    elif scope == "spouse":
        spouse = get_spouse_id(my_user_id)
        if spouse is not None:
            return [spouse]
        return None
    else:  # "family"
        return None


def get_month_total(user_ids: Optional[list[int]] = None) -> float:
    """Get total expense amount (in default currency) for the current month.

    Uses amount_sgd for multi-currency support, falling back to amount for old data.
    """
    start, end = _month_range()
    # Use amount_sgd if available; fall back to amount for old rows where amount_sgd=0
    sum_expr = "COALESCE(SUM(CASE WHEN amount_sgd > 0 THEN amount_sgd ELSE amount END), 0)"
    if user_ids:
        placeholders = ",".join("?" for _ in user_ids)
        sql = (
            f"SELECT {sum_expr} AS total FROM expenses "
            f"WHERE user_id IN ({placeholders}) AND created_at >= ? AND created_at < ?"
        )
        params = [*user_ids, start, end]
    else:
        sql = (
            f"SELECT {sum_expr} AS total FROM expenses "
            "WHERE created_at >= ? AND created_at < ?"
        )
        params = [start, end]

    with get_connection() as conn:
        row = conn.execute(sql, params).fetchone()
    return float(row["total"])


def get_category_total(category: str, user_ids: Optional[list[int]] = None) -> float:
    """Get total expense amount for a specific category in the current month."""
    start, end = _month_range()
    sum_expr = "COALESCE(SUM(CASE WHEN amount_sgd > 0 THEN amount_sgd ELSE amount END), 0)"
    if user_ids:
        placeholders = ",".join("?" for _ in user_ids)
        sql = (
            f"SELECT {sum_expr} AS total FROM expenses "
            f"WHERE user_id IN ({placeholders}) AND category = ? "
            f"AND created_at >= ? AND created_at < ?"
        )
        params = [*user_ids, category, start, end]
    else:
        sql = (
            f"SELECT {sum_expr} AS total FROM expenses "
            "WHERE category = ? AND created_at >= ? AND created_at < ?"
        )
        params = [category, start, end]

    with get_connection() as conn:
        row = conn.execute(sql, params).fetchone()
    return float(row["total"])


def get_month_summary(user_ids: Optional[list[int]] = None) -> list[dict]:
    """Get per-category summary for the current month.

    Returns a list of {"category": str, "total": float} sorted by total descending.
    """
    start, end = _month_range()
    sum_expr = "COALESCE(SUM(CASE WHEN amount_sgd > 0 THEN amount_sgd ELSE amount END), 0)"
    if user_ids:
        placeholders = ",".join("?" for _ in user_ids)
        sql = (
            f"SELECT category, {sum_expr} AS total FROM expenses "
            f"WHERE user_id IN ({placeholders}) AND created_at >= ? AND created_at < ? "
            f"GROUP BY category ORDER BY total DESC"
        )
        params = [*user_ids, start, end]
    else:
        sql = (
            f"SELECT category, {sum_expr} AS total FROM expenses "
            "WHERE created_at >= ? AND created_at < ? "
            "GROUP BY category ORDER BY total DESC"
        )
        params = [start, end]

    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [{"category": r["category"], "total": float(r["total"])} for r in rows]
