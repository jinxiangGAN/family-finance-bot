"""Semantic Memory Layer — lightweight long-term memory for the agent.

Design:
- Memories are stored in SQLite with full-text search (FTS5).
- The LLM decides WHEN to store via the `store_memory` skill.
- Before each LLM call, relevant memories are auto-recalled and injected into context.
- After each interaction, the agent does a lightweight "reflection" to extract memories.

No vector DB dependency — uses SQLite FTS5 for fast text retrieval.
"""

import json
import logging
from datetime import datetime
from typing import Optional

from zoneinfo import ZoneInfo

from app.config import TIMEZONE
from app.database import get_connection

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════
#  Memory CRUD
# ═══════════════════════════════════════════

def store_memory(user_id: int, content: str, category: str = "general", importance: int = 5) -> int:
    """Store a new memory. Returns the memory ID.

    Args:
        user_id: Whose memory this is (0 = family-shared).
        content: The memory text.
        category: e.g. 'preference', 'goal', 'decision', 'habit', 'general'.
        importance: 1-10 scale (10 = critical).
    """
    tz = ZoneInfo(TIMEZONE)
    now = datetime.now(tz)
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO memories (user_id, content, category, importance, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, content, category, min(max(importance, 1), 10), now.isoformat()),
        )
        memory_id = cursor.lastrowid
        # Also insert into FTS index
        conn.execute(
            "INSERT INTO memories_fts (rowid, content) VALUES (?, ?)",
            (memory_id, content),
        )
        conn.commit()
    logger.info("Stored memory #%d for user %d: %s", memory_id, user_id, content[:60])
    return memory_id  # type: ignore[return-value]


def recall_memories(
    user_id: int,
    query: str,
    limit: int = 5,
    include_shared: bool = True,
) -> list[dict]:
    """Recall relevant memories using FTS5 full-text search.

    Args:
        user_id: Current user (also searches shared memories with user_id=0).
        query: Search query text.
        limit: Maximum memories to return.
        include_shared: Also include family-shared memories (user_id=0).
    """
    user_filter = f"m.user_id IN ({user_id}, 0)" if include_shared else f"m.user_id = {user_id}"

    with get_connection() as conn:
        # Try FTS search first
        fts_results = []
        try:
            # Build FTS query: split into terms, join with OR
            terms = [t.strip() for t in query.split() if len(t.strip()) >= 2]
            if terms:
                fts_query = " OR ".join(terms)
                fts_results = conn.execute(
                    f"SELECT m.id, m.user_id, m.content, m.category, m.importance, m.created_at, "
                    f"       rank "
                    f"FROM memories_fts f "
                    f"JOIN memories m ON m.id = f.rowid "
                    f"WHERE memories_fts MATCH ? AND {user_filter} "
                    f"ORDER BY m.importance DESC, rank "
                    f"LIMIT ?",
                    (fts_query, limit),
                ).fetchall()
        except Exception:
            logger.debug("FTS search failed, falling back to LIKE", exc_info=True)

        # Fallback: LIKE search if FTS returned nothing
        if not fts_results:
            like_clauses = [f"m.content LIKE ?" for _ in query.split() if len(_.strip()) >= 2]
            if not like_clauses:
                return []
            like_params = [f"%{t.strip()}%" for t in query.split() if len(t.strip()) >= 2]
            where = " OR ".join(like_clauses)
            fts_results = conn.execute(
                f"SELECT m.id, m.user_id, m.content, m.category, m.importance, m.created_at "
                f"FROM memories m "
                f"WHERE ({where}) AND {user_filter} "
                f"ORDER BY m.importance DESC, m.created_at DESC "
                f"LIMIT ?",
                (*like_params, limit),
            ).fetchall()

    return [
        {
            "id": r["id"],
            "user_id": r["user_id"],
            "content": r["content"],
            "category": r["category"],
            "importance": r["importance"],
            "created_at": r["created_at"],
        }
        for r in fts_results
    ]


def get_recent_memories(user_id: int, limit: int = 10) -> list[dict]:
    """Get the most recent memories for context injection."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, user_id, content, category, importance, created_at "
            "FROM memories "
            "WHERE user_id IN (?, 0) "
            "ORDER BY importance DESC, created_at DESC "
            "LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [
        {
            "id": r["id"],
            "content": r["content"],
            "category": r["category"],
            "importance": r["importance"],
        }
        for r in rows
    ]


def delete_memory(memory_id: int) -> bool:
    """Delete a specific memory."""
    with get_connection() as conn:
        conn.execute("DELETE FROM memories_fts WHERE rowid = ?", (memory_id,))
        cursor = conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        conn.commit()
    return cursor.rowcount > 0


def format_memories_for_prompt(memories: list[dict]) -> str:
    """Format memories into a string for system prompt injection."""
    if not memories:
        return ""
    lines = ["以下是你记住的关于这个家庭的重要信息："]
    for m in memories:
        prefix = "🔴" if m["importance"] >= 8 else "🟡" if m["importance"] >= 5 else "🟢"
        lines.append(f"{prefix} [{m['category']}] {m['content']}")
    return "\n".join(lines)
