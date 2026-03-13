"""Service layer for expense CRUD operations."""

import logging
from typing import Optional

from app.database import get_connection
from app.models.expense import Expense

logger = logging.getLogger(__name__)


def save_expense(expense: Expense) -> int:
    """Insert an expense record and return the new row id."""
    sql = """
        INSERT INTO expenses (user_id, user_name, category, amount, note, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """
    with get_connection() as conn:
        cursor = conn.execute(
            sql,
            (
                expense.user_id,
                expense.user_name,
                expense.category,
                expense.amount,
                expense.note,
                expense.created_at,
            ),
        )
        conn.commit()
        row_id = cursor.lastrowid
    logger.info("Saved expense id=%s for user=%s", row_id, expense.user_id)
    return row_id  # type: ignore[return-value]


def delete_last_expense(user_id: int) -> Optional[Expense]:
    """Delete the most recent expense for a user. Returns the deleted record or None."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM expenses WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (user_id,),
        ).fetchone()
        if row is None:
            return None
        expense = _row_to_expense(row)
        conn.execute("DELETE FROM expenses WHERE id = ?", (row["id"],))
        conn.commit()
    logger.info("Deleted expense id=%s for user=%s", expense.id, user_id)
    return expense


def get_recent_expenses(user_id: int, limit: int = 10) -> list[Expense]:
    """Get the most recent expenses for a user."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM expenses WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [_row_to_expense(r) for r in rows]


def _row_to_expense(row) -> Expense:
    return Expense(
        id=row["id"],
        user_id=row["user_id"],
        user_name=row["user_name"],
        category=row["category"],
        amount=row["amount"],
        note=row["note"],
        created_at=row["created_at"],
    )
