"""
Mode Manager Service.
Tracks the user's current interaction mode in SQLite with an auto-reset timeout.
Modes include: TEACHER, TRANSLATION, CORRECTION, TECHNICAL.
"""

import time
import logging
from typing import Optional

from src.database.connection import get_db

logger = logging.getLogger(__name__)

MODE_EXPIRY_SECONDS = 600  # 10 minutes

async def _ensure_table() -> None:
    """Ensure the user_modes table exists. Safe to call multiple times."""
    db = await get_db()
    await db.execute('''
        CREATE TABLE IF NOT EXISTS user_modes (
            user_id INTEGER PRIMARY KEY,
            mode TEXT NOT NULL,
            updated_at REAL NOT NULL
        )
    ''')
    # No explicit commit needed for DDL in WAL, but safe to do
    await db.commit()


async def set_mode(user_id: int, mode: str) -> None:
    """Set the user's active mode and update the timestamp."""
    await _ensure_table()
    db = await get_db()
    now = time.time()
    await db.execute('''
        INSERT INTO user_modes (user_id, mode, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            mode=excluded.mode,
            updated_at=excluded.updated_at
    ''', (user_id, mode, now))
    await db.commit()
    logger.debug("Set mode=%s for user=%s", mode, user_id)


async def get_mode(user_id: int) -> Optional[str]:
    """
    Get the user's current mode.
    Returns None if the mode has expired or does not exist.
    """
    try:
        db = await get_db()
        cursor = await db.execute("SELECT mode, updated_at FROM user_modes WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        
        if not row:
            return None
            
        mode = row["mode"]
        updated_at = row["updated_at"]
        
        if time.time() - updated_at > MODE_EXPIRY_SECONDS:
            await clear_mode(user_id)
            return None
            
        return mode
    except Exception as e:
        logger.warning(f"Error getting mode for user {user_id}: {e}")
        return None


async def clear_mode(user_id: int) -> None:
    """Clear the user's mode (e.g. on /cancel or timeout)."""
    try:
        db = await get_db()
        await db.execute("DELETE FROM user_modes WHERE user_id = ?", (user_id,))
        await db.commit()
        logger.debug("Cleared mode for user=%s", user_id)
    except Exception:
        pass
