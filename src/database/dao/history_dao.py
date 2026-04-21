"""
History DAO — chat history management.
"""

from src.database.connection import get_db


async def add_history(user_id: int, role: str, content: str) -> None:
    """Add a message to chat history."""
    db = await get_db()
    await db.execute(
        "INSERT INTO history (user_id, role, content) VALUES (?, ?, ?)",
        (user_id, role, content),
    )
    # Keep only last 10 messages per user
    await db.execute(
        """DELETE FROM history WHERE id NOT IN (
            SELECT id FROM history WHERE user_id = ? ORDER BY id DESC LIMIT 10
        ) AND user_id = ?""",
        (user_id, user_id),
    )
    await db.commit()


async def get_history(user_id: int, limit: int = 10) -> list[dict]:
    """Get recent chat history for a user."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT role, content FROM history WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (user_id, limit),
    )
    rows = await cursor.fetchall()
    # Reverse to get chronological order
    return [{"role": row[0], "content": row[1]} for row in reversed(rows)]


async def clear_history(user_id: int) -> None:
    """Clear all chat history for a user."""
    db = await get_db()
    await db.execute("DELETE FROM history WHERE user_id = ?", (user_id,))
    await db.commit()
