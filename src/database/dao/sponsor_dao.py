"""
Sponsor DAO — mandatory channel subscription management.
"""

from src.database.connection import get_db


async def get_active_sponsors() -> list[dict]:
    """Get all active sponsor channels."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM sponsor_channels WHERE is_active = 1"
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def get_all_sponsors() -> list[dict]:
    """Get all sponsor channels, active and inactive."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM sponsor_channels ORDER BY is_active DESC, id ASC"
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def add_sponsor(channel_id: int, username: str = "", title: str = "") -> int:
    """Add a sponsor channel. Returns row ID."""
    db = await get_db()
    cursor = await db.execute(
        """INSERT INTO sponsor_channels (channel_id, channel_username, title, is_active)
           VALUES (?, ?, ?, 1)
           ON CONFLICT(channel_id) DO UPDATE SET
               channel_username = excluded.channel_username,
               title = excluded.title,
               is_active = 1 RETURNING id""",
        (channel_id, username, title),
    )
    await db.commit()
    row = await cursor.fetchone()
    return row[0] if row else 0


async def remove_sponsor(channel_id: int) -> None:
    """Deactivate a sponsor channel."""
    db = await get_db()
    await db.execute(
        "UPDATE sponsor_channels SET is_active = 0 WHERE channel_id = ?",
        (channel_id,),
    )
    await db.commit()


async def set_sponsor_active(channel_id: int, is_active: int) -> None:
    """Toggle sponsor channel state."""
    db = await get_db()
    await db.execute(
        "UPDATE sponsor_channels SET is_active = ? WHERE channel_id = ?",
        (is_active, channel_id),
    )
    await db.commit()


async def delete_sponsor(channel_id: int) -> None:
    """Permanently delete a sponsor channel."""
    db = await get_db()
    await db.execute("DELETE FROM sponsor_channels WHERE channel_id = ?", (channel_id,))
    await db.commit()
