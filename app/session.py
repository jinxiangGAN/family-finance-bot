"""Session management — tracks per-user state and chat context.

Distinguishes between:
- Private chat: personal space, more empathetic tone, shows individual data
- Group chat: shared space, objective tone, shows family-level data

Each session carries:
- chat_type: 'private' | 'group' | 'supergroup'
- user_id / user_name
- recent interaction count (for proactive engagement)
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from zoneinfo import ZoneInfo

from app.config import FAMILY_MEMBERS, TIMEZONE

logger = logging.getLogger(__name__)


@dataclass
class Session:
    """Represents a user's current session context."""

    user_id: int
    user_name: str
    chat_id: int
    chat_type: str  # "private" | "group" | "supergroup"
    display_name: str = ""
    interaction_count: int = 0
    last_active: str = ""

    def __post_init__(self):
        if not self.display_name:
            self.display_name = FAMILY_MEMBERS.get(self.user_id, self.user_name)
        if not self.last_active:
            tz = ZoneInfo(TIMEZONE)
            self.last_active = datetime.now(tz).isoformat()

    @property
    def is_private(self) -> bool:
        return self.chat_type == "private"

    @property
    def is_group(self) -> bool:
        return self.chat_type in ("group", "supergroup")


# Simple in-memory session store (per user_id)
_sessions: dict[int, Session] = {}


def get_or_create_session(
    user_id: int,
    user_name: str,
    chat_id: int,
    chat_type: str,
) -> Session:
    """Get existing session or create a new one."""
    session = _sessions.get(user_id)
    if session is None or session.chat_id != chat_id:
        session = Session(
            user_id=user_id,
            user_name=user_name,
            chat_id=chat_id,
            chat_type=chat_type,
        )
        _sessions[user_id] = session
    else:
        # Update activity
        tz = ZoneInfo(TIMEZONE)
        session.last_active = datetime.now(tz).isoformat()
        session.interaction_count += 1
        session.chat_type = chat_type
    return session


def build_system_prompt_for_session(session: Session, base_prompt: str, memories_text: str) -> str:
    """Build a context-aware system prompt based on session type.

    - Private chat: warmer, more personal, includes individual memories
    - Group chat: objective, concise, family-oriented
    """
    parts = [base_prompt]

    if memories_text:
        parts.append(f"\n{memories_text}")

    if session.is_private:
        parts.append(
            f"\n当前对话场景：私聊（{session.display_name}）\n"
            "回复风格：温暖、贴心，可以用更感性的语气给出建议。"
            "可以主动关心对方的消费习惯，适当给出鼓励或温馨提醒。"
            f"称呼用户为「{session.display_name}」。"
        )
    elif session.is_group:
        parts.append(
            "\n当前对话场景：家庭群聊\n"
            "回复风格：客观、简洁。播报数据时用家庭视角。"
            "不要过于感性，保持中立和专业。"
            "如果涉及个人消费细节，注意隐私，不要在群里展示过多个人信息。"
        )

    return "\n".join(parts)
