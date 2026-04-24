"""
Mode Manager Service.
Tracks the user's current interaction mode with an auto-reset timeout.
Repairs the legacy user_modes table when user_id was created as int32.
"""

import logging
import time
from typing import Optional

from src.database.connection import get_db
from src.database.db_wrapper import DatabaseFactory

logger = logging.getLogger(__name__)

MODE_EXPIRY_SECONDS = 600  # 10 minutes
_TABLE_READY = False


async def _repair_table_if_needed(db) -> None:
    """Upgrade old user_modes schemas so Telegram BIGINT IDs fit."""
    if DatabaseFactory.is_postgres():
        cursor = await db.execute(
            """
            SELECT data_type
            FROM information_schema.columns
            WHERE table_name = ? AND column_name = ?
            """,
            ("user_modes", "user_id"),
        )
        row = await cursor.fetchone()
        if row and row[0] != "bigint":
            await db.execute("ALTER TABLE user_modes ALTER COLUMN user_id TYPE BIGINT")
            logger.info("Migrated user_modes.user_id to BIGINT on PostgreSQL")
        return

    cursor = await db.execute("PRAGMA table_info(user_modes)")
    rows = await cursor.fetchall()
    user_id_column = next((row for row in rows if row[1] == "user_id"), None)
    current_type = str(user_id_column[2] if user_id_column else "").upper()
    if "BIGINT" in current_type:
        return

    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS user_modes_new (
            user_id BIGINT PRIMARY KEY,
            mode TEXT NOT NULL,
            updated_at REAL NOT NULL
        )
        """
    )
    await db.execute(
        """
        INSERT OR REPLACE INTO user_modes_new (user_id, mode, updated_at)
        SELECT CAST(user_id AS BIGINT), mode, updated_at
        FROM user_modes
        """
    )
    await db.execute("DROP TABLE user_modes")
    await db.execute("ALTER TABLE user_modes_new RENAME TO user_modes")
    logger.info("Migrated user_modes.user_id to BIGINT on SQLite")


async def _ensure_table() -> None:
    """Ensure the user_modes table exists and is compatible."""
    global _TABLE_READY
    if _TABLE_READY:
        return

    db = await get_db()
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS user_modes (
            user_id BIGINT PRIMARY KEY,
            mode TEXT NOT NULL,
            updated_at REAL NOT NULL
        )
        """
    )
    await _repair_table_if_needed(db)
    await db.commit()
    _TABLE_READY = True


async def set_mode(user_id: int, mode: str) -> None:
    """Set the user's active mode and update the timestamp."""
    await _ensure_table()
    db = await get_db()
    now = time.time()
    await db.execute(
        """
        INSERT INTO user_modes (user_id, mode, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            mode=excluded.mode,
            updated_at=excluded.updated_at
        """,
        (user_id, mode, now),
    )
    await db.commit()
    logger.debug("Set mode=%s for user=%s", mode, user_id)


async def get_mode(user_id: int) -> Optional[str]:
    """
    Get the user's current mode.
    Returns None if the mode has expired or does not exist.
    """
    try:
        await _ensure_table()
        db = await get_db()
        cursor = await db.execute(
            "SELECT mode, updated_at FROM user_modes WHERE user_id = ?",
            (user_id,),
        )
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
        logger.warning("Error getting mode for user %s: %s", user_id, e)
        return None


async def clear_mode(user_id: int) -> None:
    """Clear the user's mode (e.g. on /cancel or timeout)."""
    try:
        await _ensure_table()
        db = await get_db()
        await db.execute("DELETE FROM user_modes WHERE user_id = ?", (user_id,))
        await db.commit()
        logger.debug("Cleared mode for user=%s", user_id)
    except Exception:
        pass
