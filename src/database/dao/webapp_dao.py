"""
WebApp DAO — webapp progress tracking.
"""

from datetime import date
from src.database.connection import get_db


async def upsert_progress(
    user_id: int,
    words: int = 0,
    quiz: int = 0,
    lessons: int = 0,
    focus_minutes: int = 0,
    topics: str = "",
    note: str = "",
    points: int = 0,
) -> None:
    """Upsert today's webapp progress."""
    db = await get_db()
    today = date.today().isoformat()

    cursor = await db.execute(
        "SELECT id FROM webapp_progress WHERE user_id = ? AND progress_date = ?",
        (user_id, today),
    )
    row = await cursor.fetchone()

    if row:
        await db.execute(
            """UPDATE webapp_progress SET
                words = words + ?, quiz = quiz + ?, lessons = lessons + ?,
                focus_minutes = focus_minutes + ?, topics = ?, note = ?,
                points = points + ?
               WHERE id = ?""",
            (words, quiz, lessons, focus_minutes, topics, note, points, row[0]),
        )
    else:
        await db.execute(
            """INSERT INTO webapp_progress
               (user_id, progress_date, words, quiz, lessons, focus_minutes, topics, note, points)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, today, words, quiz, lessons, focus_minutes, topics, note, points),
        )
    await db.commit()


async def get_progress(user_id: int, days: int = 7) -> list[dict]:
    """Get user's progress for the last N days."""
    db = await get_db()
    cursor = await db.execute(
        """SELECT * FROM webapp_progress WHERE user_id = ?
           ORDER BY progress_date DESC LIMIT ?""",
        (user_id, days),
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def get_today_progress(user_id: int) -> dict:
    """Get today's progress."""
    db = await get_db()
    today = date.today().isoformat()
    cursor = await db.execute(
        "SELECT * FROM webapp_progress WHERE user_id = ? AND progress_date = ?",
        (user_id, today),
    )
    row = await cursor.fetchone()
    return dict(row) if row else {
        "user_id": user_id, "progress_date": today,
        "words": 0, "quiz": 0, "lessons": 0, "focus_minutes": 0,
        "topics": "", "note": "", "points": 0,
    }
