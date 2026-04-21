"""
Leaderboard DAO — global and group learning leaderboards.
"""

from src.database.connection import get_db


async def get_global_leaderboard(limit: int = 20) -> list[dict]:
    """Get global leaderboard by learning score."""
    db = await get_db()
    cursor = await db.execute(
        """SELECT u.user_id, u.username, u.first_name, u.level,
                  s.checks_total, s.quiz_played, s.quiz_correct, s.streak_days,
                  s.learning_score,
                  COALESCE(x.total_xp, 0) AS total_xp,
                  COALESCE(x.current_level, 1) AS xp_level
           FROM users u
           LEFT JOIN stats s ON u.user_id = s.user_id
           LEFT JOIN user_xp x ON u.user_id = x.user_id
           WHERE u.is_banned = 0
           ORDER BY COALESCE(s.learning_score, 0) DESC, COALESCE(x.total_xp, 0) DESC
           LIMIT ?""",
        (limit,),
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def get_user_rank(user_id: int) -> int:
    """Get user's rank in global leaderboard."""
    db = await get_db()
    cursor = await db.execute(
        """SELECT COUNT(*) + 1 AS rank FROM stats
           WHERE learning_score > COALESCE(
               (SELECT learning_score FROM stats WHERE user_id = ?), 0
           )""",
        (user_id,),
    )
    row = await cursor.fetchone()
    return row[0] if row else 0


async def get_group_leaderboard(chat_id: int, limit: int = 10) -> list[dict]:
    """Get group game leaderboard."""
    db = await get_db()
    cursor = await db.execute(
        """SELECT user_id, username, points, wins
           FROM group_game_scores
           WHERE chat_id = ?
           ORDER BY points DESC
           LIMIT ?""",
        (chat_id, limit),
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]
