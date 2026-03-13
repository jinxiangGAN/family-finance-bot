"""Service layer for expense CRUD operations."""

import logging
from typing import Optional

from app.database import get_connection
from app.models.expense import Expense

logger = logging.getLogger(__name__)


def save_expense(expense: Expense) -> int:
    """Insert an expense record and return the new row id."""
    sql = """
        INSERT INTO expenses (user_id, user_name, category, amount, currency, amount_sgd, note, event_tag, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    with get_connection() as conn:
        cursor = conn.execute(
            sql,
            (
                expense.user_id,
                expense.user_name,
                expense.category,
                expense.amount,
                expense.currency,
                expense.amount_sgd,
                expense.note,
                expense.event_tag,
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


def export_expenses_csv(user_id: Optional[int] = None, event_tag: str = "") -> str:
    """Export expenses to CSV string. Optionally filter by user_id and/or event_tag."""
    conditions = []
    params: list = []
    if user_id is not None:
        conditions.append("user_id = ?")
        params.append(user_id)
    if event_tag:
        conditions.append("event_tag = ?")
        params.append(event_tag)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = f"SELECT * FROM expenses {where} ORDER BY created_at ASC"

    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()

    lines = ["id,user_name,category,amount,currency,amount_sgd,note,event_tag,created_at"]
    for r in rows:
        note_escaped = str(r["note"]).replace('"', '""')
        tag = r["event_tag"] if "event_tag" in r.keys() else ""
        currency = r["currency"] if "currency" in r.keys() else "SGD"
        amount_sgd = r["amount_sgd"] if "amount_sgd" in r.keys() else r["amount"]
        lines.append(
            f'{r["id"]},"{r["user_name"]}","{r["category"]}",{r["amount"]},"{currency}",'
            f'{amount_sgd},"{note_escaped}","{tag}","{r["created_at"]}"'
        )
    return "\n".join(lines)


def _row_to_expense(row) -> Expense:
    # Handle both old (no currency/event_tag columns) and new schemas
    keys = row.keys() if hasattr(row, "keys") else []
    return Expense(
        id=row["id"],
        user_id=row["user_id"],
        user_name=row["user_name"],
        category=row["category"],
        amount=row["amount"],
        currency=row["currency"] if "currency" in keys else "SGD",
        amount_sgd=row["amount_sgd"] if "amount_sgd" in keys else row["amount"],
        note=row["note"],
        event_tag=row["event_tag"] if "event_tag" in keys else "",
        created_at=row["created_at"],
    )
