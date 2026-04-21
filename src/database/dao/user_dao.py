"""
User DAO — all user-related database operations.
"""

import logging
from datetime import datetime

from src.database.connection import get_db

logger = logging.getLogger(__name__)


async def upsert_user(user_id: int, username: str = "", first_name: str = "") -> dict:
    """Insert or update user, return the user dict."""
    db = await get_db()
    now = datetime.utcnow().isoformat(timespec="seconds")

    await db.execute(
        """INSERT INTO users (user_id, username, first_name, joined_at, last_seen)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(user_id) DO UPDATE SET
               username = excluded.username,
               first_name = excluded.first_name,
               last_seen = excluded.last_seen""",
        (user_id, username, first_name, now, now),
    )
    await db.commit()
    return await get_user(user_id)


async def get_user(user_id: int) -> dict | None:
    """Get a user by ID."""
    db = await get_db()
    cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = await cursor.fetchone()
    return dict(row) if row else None


async def set_role(user_id: int, role: str) -> None:
    """Set user role (user|admin|owner)."""
    db = await get_db()
    await db.execute("UPDATE users SET role = ? WHERE user_id = ?", (role, user_id))
    await db.commit()


async def set_level(user_id: int, level: str) -> None:
    """Set user English level (A1-C2)."""
    db = await get_db()
    await db.execute("UPDATE users SET level = ? WHERE user_id = ?", (level, user_id))
    await db.commit()


async def ban_user(user_id: int, is_banned: int = 1) -> None:
    """Ban or unban a user."""
    db = await get_db()
    await db.execute("UPDATE users SET is_banned = ? WHERE user_id = ?", (is_banned, user_id))
    await db.commit()


async def get_all_user_ids() -> list[int]:
    """Get all non-banned user IDs for broadcast."""
    db = await get_db()
    cursor = await db.execute("SELECT user_id FROM users WHERE is_banned = 0")
    rows = await cursor.fetchall()
    return [row[0] for row in rows]


async def count_users() -> int:
    """Count total users."""
    db = await get_db()
    cursor = await db.execute("SELECT COUNT(*) FROM users")
    row = await cursor.fetchone()
    return row[0] if row else 0


async def count_users_by_role(role: str) -> int:
    """Count users by role."""
    db = await get_db()
    cursor = await db.execute("SELECT COUNT(*) FROM users WHERE role = ?", (role,))
    row = await cursor.fetchone()
    return row[0] if row else 0


async def find_user_by_username(username: str) -> dict | None:
    """Find a user by their Telegram username."""
    db = await get_db()
    clean = username.lstrip("@").strip()
    cursor = await db.execute(
        "SELECT * FROM users WHERE LOWER(username) = LOWER(?)",
        (clean,),
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


async def get_admins() -> list[dict]:
    """Get all users with admin or owner role."""
    db = await get_db()
    cursor = await db.execute("SELECT * FROM users WHERE role IN ('admin', 'owner')")
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def get_users_page(offset: int = 0, limit: int = 50) -> list[dict]:
    """Get a page of users ordered by join date."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM users ORDER BY joined_at DESC LIMIT ? OFFSET ?",
        (limit, offset),
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]
