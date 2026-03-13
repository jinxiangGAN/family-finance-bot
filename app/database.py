"""SQLite database initialization and connection management."""

import logging
import os
import sqlite3
from contextlib import contextmanager
from typing import Generator

from app.config import DATABASE_PATH

logger = logging.getLogger(__name__)

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS expenses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    user_name   TEXT    NOT NULL DEFAULT '',
    category    TEXT    NOT NULL,
    amount      REAL    NOT NULL,
    note        TEXT    NOT NULL DEFAULT '',
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_INDEX_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_expenses_user_id    ON expenses(user_id);",
    "CREATE INDEX IF NOT EXISTS idx_expenses_category   ON expenses(category);",
    "CREATE INDEX IF NOT EXISTS idx_expenses_created_at ON expenses(created_at);",
]


def init_db() -> None:
    """Create the database file, table, and indexes if they don't exist."""
    db_dir = os.path.dirname(DATABASE_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    with get_connection() as conn:
        conn.execute(CREATE_TABLE_SQL)
        for idx_sql in CREATE_INDEX_SQL:
            conn.execute(idx_sql)
        conn.commit()
    logger.info("Database initialized at %s", DATABASE_PATH)


@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    """Yield a SQLite connection with row_factory set to sqlite3.Row."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
