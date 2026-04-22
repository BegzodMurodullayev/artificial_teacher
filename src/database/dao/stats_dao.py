"""
Stats DAO — user statistics and daily usage tracking.
"""

import logging
from datetime import date

from src.database.connection import get_db

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════
# STATS
# ══════════════════════════════════════════════════════════

async def get_stats(user_id: int) -> dict:
    """Get user stats, creating row if missing."""
    db = await get_db()
    cursor = await db.execute("SELECT * FROM stats WHERE user_id = ?", (user_id,))
    row = await cursor.fetchone()
    if row:
        return dict(row)
    # Create stats row
    await db.execute("INSERT INTO stats (user_id) VALUES (?) ON CONFLICT (user_id) DO NOTHING", (user_id,))
    await db.commit()
    cursor = await db.execute("SELECT * FROM stats WHERE user_id = ?", (user_id,))
    row = await cursor.fetchone()
    return dict(row) if row else {"user_id": user_id}


async def inc_stat(user_id: int, field: str, amount: int = 1) -> None:
    """Increment a stats field. Field must be whitelisted."""
    allowed = {
        "checks_total", "translations_total", "pron_total",
        "quiz_played", "quiz_correct", "lessons_total",
        "messages_total", "voice_total", "streak_days",
        "iq_score", "max_iq_score", "learning_score",
    }
    if field not in allowed:
        logger.warning("Rejected inc_stat for unknown field: %s", field)
        return

    db = await get_db()
    await db.execute("INSERT INTO stats (user_id) VALUES (?) ON CONFLICT (user_id) DO NOTHING", (user_id,))
    await db.execute(
        f"UPDATE stats SET {field} = {field} + ? WHERE user_id = ?",
        (amount, user_id),
    )
    await db.commit()


async def set_stat(user_id: int, field: str, value: int) -> None:
    """Set a stats field to specific value."""
    allowed = {
        "checks_total", "translations_total", "pron_total",
        "quiz_played", "quiz_correct", "lessons_total",
        "messages_total", "voice_total", "streak_days",
        "iq_score", "max_iq_score", "learning_score",
    }
    if field not in allowed:
        return

    db = await get_db()
    await db.execute("INSERT INTO stats (user_id) VALUES (?) ON CONFLICT (user_id) DO NOTHING", (user_id,))
    await db.execute(
        f"UPDATE stats SET {field} = ? WHERE user_id = ?",
        (value, user_id),
    )
    await db.commit()


# ══════════════════════════════════════════════════════════
# DAILY USAGE
# ══════════════════════════════════════════════════════════

async def inc_usage(user_id: int, field: str, amount: int = 1) -> None:
    """Increment daily usage counter."""
    allowed = {"checks", "quiz", "lessons", "ai_messages", "pron_audio"}
    if field not in allowed:
        return

    db = await get_db()
    today = date.today().isoformat()
    await db.execute(
        """INSERT INTO daily_usage (user_id, usage_date) VALUES (?, ?)
           ON CONFLICT(user_id, usage_date) DO NOTHING""",
        (user_id, today),
    )
    await db.execute(
        f"UPDATE daily_usage SET {field} = {field} + ? WHERE user_id = ? AND usage_date = ?",
        (amount, user_id, today),
    )
    await db.commit()


async def get_usage_today(user_id: int) -> dict:
    """Get today's usage counters."""
    db = await get_db()
    today = date.today().isoformat()
    cursor = await db.execute(
        "SELECT * FROM daily_usage WHERE user_id = ? AND usage_date = ?",
        (user_id, today),
    )
    row = await cursor.fetchone()
    if row:
        return dict(row)
    return {
        "user_id": user_id,
        "usage_date": today,
        "checks": 0,
        "quiz": 0,
        "lessons": 0,
        "ai_messages": 0,
        "pron_audio": 0,
    }


async def check_limit(user_id: int, field: str, plan_limit: int) -> bool:
    """Check if user is within daily limit. Returns True if allowed."""
    usage = await get_usage_today(user_id)
    current = usage.get(field, 0)
    return current < plan_limit
