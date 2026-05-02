"""
Quiz DAO — quiz sessions, question history, level signals.
"""

import json
import logging
from datetime import datetime

from src.database.connection import get_db

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════
# QUIZ SESSIONS (DB-backed, replaces in-memory dict)
# ══════════════════════════════════════════════════════════

async def create_quiz_session(
    user_id: int,
    qtype: str = "quiz",
    level: str = "A1",
    language: str = "en",
    total_questions: int = 10,
    question_timeout: int = 45,
    chat_id: int = 0,
) -> int:
    """Create a new quiz session. Returns session ID."""
    db = await get_db()
    await db.execute("UPDATE quiz_sessions SET status = 'abandoned' WHERE user_id = ? AND status = 'active'", (user_id,))
    cursor = await db.execute(
        """INSERT INTO quiz_sessions
           (user_id, qtype, level, language, total_questions, question_timeout, chat_id, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'active')
           RETURNING id""",
        (user_id, qtype, level, language, total_questions, question_timeout, chat_id),
    )
    await db.commit()
    row = await cursor.fetchone()
    return row[0] if row else 0


async def get_quiz_session(session_id: int) -> dict | None:
    """Get quiz session by ID."""
    db = await get_db()
    cursor = await db.execute("SELECT * FROM quiz_sessions WHERE id = ?", (session_id,))
    row = await cursor.fetchone()
    return dict(row) if row else None


async def get_active_quiz_session(user_id: int) -> dict | None:
    """Get user's active quiz session."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM quiz_sessions WHERE user_id = ? AND status = 'active' ORDER BY id DESC LIMIT 1",
        (user_id,),
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


async def update_quiz_session(session_id: int, **fields) -> None:
    """Update quiz session fields."""
    allowed = {
        "asked", "answered", "correct", "xp_earned", "status",
        "current_question", "history", "used_keys",
        "message_id", "finished_at",
    }
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return

    db = await get_db()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [session_id]
    await db.execute(f"UPDATE quiz_sessions SET {set_clause} WHERE id = ?", values)
    await db.commit()


async def finish_quiz_session(session_id: int) -> None:
    """Mark quiz session as finished."""
    db = await get_db()
    now = datetime.utcnow().isoformat(timespec="seconds")
    await db.execute(
        "UPDATE quiz_sessions SET status = 'finished', finished_at = ? WHERE id = ?",
        (now, session_id),
    )
    await db.commit()


# ══════════════════════════════════════════════════════════
# QUIZ ATTEMPTS (historical records)
# ══════════════════════════════════════════════════════════

async def record_quiz_attempt(
    user_id: int,
    qtype: str,
    total: int,
    correct: int,
    wrong: int,
    mode: str = "en",
    level_before: str = "A1",
    level_after: str = "A1",
    iq_score: int = 0,
) -> int:
    """Record a completed quiz attempt."""
    db = await get_db()
    cursor = await db.execute(
        """INSERT INTO quiz_attempts
           (user_id, qtype, total, correct, wrong, mode, level_before, level_after, iq_score)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
           RETURNING id""",
        (user_id, qtype, total, correct, wrong, mode, level_before, level_after, iq_score),
    )
    await db.commit()
    row = await cursor.fetchone()
    return row[0] if row else 0


# ══════════════════════════════════════════════════════════
# QUESTION HISTORY (avoid repeats)
# ══════════════════════════════════════════════════════════

async def get_recent_question_keys(user_id: int, limit: int = 50) -> list[str]:
    """Get recently asked question keys for a user."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT question_key FROM question_history WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (user_id, limit),
    )
    rows = await cursor.fetchall()
    return [row[0] for row in rows]


async def add_question_key(user_id: int, key: str) -> None:
    """Record a question key as asked."""
    db = await get_db()
    await db.execute(
        "INSERT INTO question_history (user_id, question_key) VALUES (?, ?)",
        (user_id, key),
    )
    await db.commit()


# ══════════════════════════════════════════════════════════
# LEVEL SIGNALS
# ══════════════════════════════════════════════════════════

async def add_level_signal(
    user_id: int,
    source: str,
    estimated_level: str,
    weight: float = 1.0,
) -> None:
    """Record a level estimation signal."""
    db = await get_db()
    await db.execute(
        "INSERT INTO level_signals (user_id, source, estimated_level, weight) VALUES (?, ?, ?, ?)",
        (user_id, source, estimated_level, weight),
    )
    await db.commit()


async def get_recent_signals(user_id: int, limit: int = 10) -> list[dict]:
    """Get recent level signals for auto-adjustment."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM level_signals WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (user_id, limit),
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]
