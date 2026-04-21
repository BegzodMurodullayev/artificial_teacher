"""
Game DAO — game sessions, participation, and group scores.
"""

import json
import logging
from datetime import datetime

from src.database.connection import get_db

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════
# GAME SESSIONS
# ══════════════════════════════════════════════════════════

async def create_game_session(
    chat_id: int,
    game_type: str,
    created_by: int = 0,
    payload: dict | None = None,
) -> int:
    """Create a new game session. Returns session ID."""
    db = await get_db()
    payload_json = json.dumps(payload or {}, ensure_ascii=False)
    cursor = await db.execute(
        """INSERT INTO game_sessions (chat_id, game_type, status, payload, created_by)
           VALUES (?, ?, 'waiting', ?, ?)""",
        (chat_id, game_type, payload_json, created_by),
    )
    await db.commit()
    return cursor.lastrowid


async def get_active_game(chat_id: int) -> dict | None:
    """Get active (non-finished) game for a chat."""
    db = await get_db()
    cursor = await db.execute(
        """SELECT * FROM game_sessions
           WHERE chat_id = ? AND status != 'finished'
           ORDER BY id DESC LIMIT 1""",
        (chat_id,),
    )
    row = await cursor.fetchone()
    if not row:
        return None
    result = dict(row)
    try:
        result["payload"] = json.loads(result.get("payload", "{}"))
    except (json.JSONDecodeError, TypeError):
        result["payload"] = {}
    return result


async def update_game_session(session_id: int, status: str, payload: dict | None = None, round_number: int | None = None) -> None:
    """Update game session status and/or payload."""
    db = await get_db()
    now = datetime.utcnow().isoformat(timespec="seconds")

    if payload is not None and round_number is not None:
        await db.execute(
            "UPDATE game_sessions SET status = ?, payload = ?, round_number = ?, updated_at = ? WHERE id = ?",
            (status, json.dumps(payload, ensure_ascii=False), round_number, now, session_id),
        )
    elif payload is not None:
        await db.execute(
            "UPDATE game_sessions SET status = ?, payload = ?, updated_at = ? WHERE id = ?",
            (status, json.dumps(payload, ensure_ascii=False), now, session_id),
        )
    else:
        await db.execute(
            "UPDATE game_sessions SET status = ?, updated_at = ? WHERE id = ?",
            (status, now, session_id),
        )
    await db.commit()


async def finish_game_session(session_id: int) -> None:
    """Mark game session as finished."""
    db = await get_db()
    now = datetime.utcnow().isoformat(timespec="seconds")
    await db.execute(
        "UPDATE game_sessions SET status = 'finished', finished_at = ?, updated_at = ? WHERE id = ?",
        (now, now, session_id),
    )
    await db.commit()


# ══════════════════════════════════════════════════════════
# GROUP GAME SCORES (leaderboard)
# ══════════════════════════════════════════════════════════

async def add_game_points(chat_id: int, user_id: int, username: str, points: int, won: int = 0) -> None:
    """Add points and wins to a user's group score."""
    db = await get_db()
    await db.execute(
        """INSERT INTO group_game_scores (chat_id, user_id, username, points, wins)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(chat_id, user_id) DO UPDATE SET
               username = excluded.username,
               points = points + excluded.points,
               wins = wins + excluded.wins""",
        (chat_id, user_id, username, points, won),
    )
    await db.commit()


async def get_game_scores(chat_id: int, limit: int = 10) -> list[dict]:
    """Get top scores for a chat."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM group_game_scores WHERE chat_id = ? ORDER BY points DESC LIMIT ?",
        (chat_id, limit),
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def reset_game_scores(chat_id: int) -> None:
    """Reset all game scores for a chat."""
    db = await get_db()
    await db.execute("DELETE FROM group_game_scores WHERE chat_id = ?", (chat_id,))
    await db.commit()


# ══════════════════════════════════════════════════════════
# GROUP GAME SETTINGS
# ══════════════════════════════════════════════════════════

DEFAULT_GAME_SETTINGS = {
    "word_time_limit": 30,
    "word_points": 10,
    "error_time_limit": 45,
    "error_points": 15,
    "translation_time_limit": 60,
    "translation_points_perfect": 25,
    "translation_points_close": 15,
    "mafia_min_players": 4,
    "mafia_max_players": 12,
    "mafia_night_time": 120,
    "mafia_day_time": 180,
}


async def get_game_settings(chat_id: int) -> dict:
    """Get game settings for a chat, with defaults."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM group_settings WHERE chat_id = ?", (chat_id,)
    )
    row = await cursor.fetchone()
    # Game settings are stored in game_sessions or a separate config
    # For now, return defaults merged with any overrides
    return dict(DEFAULT_GAME_SETTINGS)
