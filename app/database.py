"""SQLite database initialization and connection management."""

import logging
import os
import sqlite3
from contextlib import contextmanager
from typing import Generator

from app.config import DATABASE_PATH

logger = logging.getLogger(__name__)

CREATE_TABLES_SQL = [
    # Expenses table (with currency and event tag)
    """
    CREATE TABLE IF NOT EXISTS expenses (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     INTEGER NOT NULL,
        user_name   TEXT    NOT NULL DEFAULT '',
        category    TEXT    NOT NULL,
        amount      REAL    NOT NULL,
        currency    TEXT    NOT NULL DEFAULT 'SGD',
        amount_sgd  REAL    NOT NULL DEFAULT 0,
        note        TEXT    NOT NULL DEFAULT '',
        event_tag   TEXT    NOT NULL DEFAULT '',
        created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """,
    # Budgets table
    """
    CREATE TABLE IF NOT EXISTS budgets (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     INTEGER NOT NULL,
        category    TEXT    NOT NULL DEFAULT '_total',
        monthly_limit REAL  NOT NULL,
        updated_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, category)
    );
    """,
    # API usage tracking table
    """
    CREATE TABLE IF NOT EXISTS api_usage (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id         INTEGER NOT NULL,
        prompt_tokens   INTEGER NOT NULL DEFAULT 0,
        completion_tokens INTEGER NOT NULL DEFAULT 0,
        total_tokens    INTEGER NOT NULL DEFAULT 0,
        model           TEXT    NOT NULL DEFAULT '',
        created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """,
    # Event tags table
    """
    CREATE TABLE IF NOT EXISTS events (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     INTEGER NOT NULL,
        tag         TEXT    NOT NULL,
        description TEXT    NOT NULL DEFAULT '',
        is_active   INTEGER NOT NULL DEFAULT 1,
        created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, tag)
    );
    """,
    # Semantic memory table
    """
    CREATE TABLE IF NOT EXISTS memories (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     INTEGER NOT NULL,
        content     TEXT    NOT NULL,
        category    TEXT    NOT NULL DEFAULT 'general',
        importance  INTEGER NOT NULL DEFAULT 5,
        created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """,
]

# FTS5 virtual table (created separately as it needs special handling)
CREATE_FTS_SQL = """
    CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts
    USING fts5(content, content_rowid='rowid');
"""

CREATE_INDEX_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_expenses_user_id    ON expenses(user_id);",
    "CREATE INDEX IF NOT EXISTS idx_expenses_category   ON expenses(category);",
    "CREATE INDEX IF NOT EXISTS idx_expenses_created_at ON expenses(created_at);",
    "CREATE INDEX IF NOT EXISTS idx_expenses_event_tag  ON expenses(event_tag);",
    "CREATE INDEX IF NOT EXISTS idx_budgets_user_id     ON budgets(user_id);",
    "CREATE INDEX IF NOT EXISTS idx_api_usage_created   ON api_usage(created_at);",
    "CREATE INDEX IF NOT EXISTS idx_events_user_id      ON events(user_id);",
    "CREATE INDEX IF NOT EXISTS idx_memories_user_id    ON memories(user_id);",
    "CREATE INDEX IF NOT EXISTS idx_memories_category   ON memories(category);",
    "CREATE INDEX IF NOT EXISTS idx_memories_importance  ON memories(importance);",
]

# Migration: add new columns to existing databases
MIGRATIONS = [
    "ALTER TABLE expenses ADD COLUMN currency TEXT NOT NULL DEFAULT 'SGD';",
    "ALTER TABLE expenses ADD COLUMN amount_sgd REAL NOT NULL DEFAULT 0;",
    "ALTER TABLE expenses ADD COLUMN event_tag TEXT NOT NULL DEFAULT '';",
]


def init_db() -> None:
    """Create the database file, tables, and indexes if they don't exist."""
    db_dir = os.path.dirname(DATABASE_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    with get_connection() as conn:
        for table_sql in CREATE_TABLES_SQL:
            conn.execute(table_sql)
        # FTS5 virtual table (separate handling)
        try:
            conn.execute(CREATE_FTS_SQL)
        except sqlite3.OperationalError:
            pass  # May already exist
        for idx_sql in CREATE_INDEX_SQL:
            conn.execute(idx_sql)
        # Run migrations (ignore errors for already-applied)
        for migration in MIGRATIONS:
            try:
                conn.execute(migration)
            except sqlite3.OperationalError:
                pass  # Column already exists
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
