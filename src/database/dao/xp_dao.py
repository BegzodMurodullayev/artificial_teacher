"""
XP DAO — gamification experience points and achievements.
"""

import json
import logging
import math
from datetime import date, datetime

from src.database.connection import get_db

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════
# XP TRANSACTIONS
# ══════════════════════════════════════════════════════════

async def add_xp(user_id: int, amount: int, source: str, source_id: str = "", metadata: dict | None = None) -> dict:
    """
    Award XP to a user. Returns updated XP summary.
    Sources: quiz_correct, check, game_win, streak, daily_login, lesson, pomodoro
    """
    db = await get_db()
    
    # Check for XP Multipliers (Weekend / Night Owl)
    multiplier = 1.0
    now = datetime.now()
    if now.weekday() >= 5: # Saturday = 5, Sunday = 6
        multiplier *= 1.5
    if now.hour >= 22 or now.hour <= 4:
        multiplier *= 1.2
        
    amount = int(amount * multiplier)
    
    meta_json = json.dumps(metadata or {}, ensure_ascii=False)

    # Record transaction
    await db.execute(
        "INSERT INTO xp_transactions (user_id, amount, source, source_id, metadata) VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, source, source_id, meta_json),
    )

    # Ensure user_xp row exists
    await db.execute("INSERT OR IGNORE INTO user_xp (user_id) VALUES (?)", (user_id,))

    # Update daily XP
    today = date.today().isoformat()
    await db.execute(
        """UPDATE user_xp SET
            total_xp = total_xp + ?,
            daily_xp_today = CASE WHEN daily_xp_date = ? THEN daily_xp_today + ? ELSE ? END,
            daily_xp_date = ?
           WHERE user_id = ?""",
        (amount, today, amount, amount, today, user_id),
    )

    # Recalculate level
    summary = await get_xp_summary(user_id)
    new_level = _calc_level(summary.get("total_xp", 0))
    xp_to_next = _xp_for_level(new_level + 1) - summary.get("total_xp", 0)

    await db.execute(
        "UPDATE user_xp SET current_level = ?, xp_to_next = ? WHERE user_id = ?",
        (new_level, max(0, xp_to_next), user_id),
    )
    await db.commit()

    return {
        "total_xp": summary.get("total_xp", 0) + amount,
        "current_level": new_level,
        "xp_to_next": max(0, xp_to_next),
        "xp_earned": amount,
        "source": source,
    }


def _calc_level(total_xp: int) -> int:
    """Calculate gamification level from total XP. Log scale: level = floor(sqrt(xp/50)) + 1"""
    if total_xp <= 0:
        return 1
    return min(100, int(math.sqrt(total_xp / 50)) + 1)


def _xp_for_level(level: int) -> int:
    """Calculate total XP needed to reach a level."""
    return 50 * ((level - 1) ** 2)


async def get_xp_summary(user_id: int) -> dict:
    """Get user's XP summary."""
    db = await get_db()
    await db.execute("INSERT OR IGNORE INTO user_xp (user_id) VALUES (?)", (user_id,))
    await db.commit()

    cursor = await db.execute("SELECT * FROM user_xp WHERE user_id = ?", (user_id,))
    row = await cursor.fetchone()
    return dict(row) if row else {"user_id": user_id, "total_xp": 0, "current_level": 1}


async def update_streak(user_id: int) -> dict:
    """Update user's streak. Call once per day on first activity."""
    db = await get_db()
    today = date.today().isoformat()

    summary = await get_xp_summary(user_id)
    last_active = summary.get("last_active_date", "")
    streak = summary.get("streak_days", 0)
    longest = summary.get("longest_streak", 0)

    if last_active == today:
        return {"streak_days": streak, "longest_streak": longest, "is_new_day": False}

    # Check if consecutive
    if last_active:
        try:
            last_date = date.fromisoformat(last_active)
            diff = (date.today() - last_date).days
            if diff == 1:
                streak += 1
            elif diff > 1:
                streak = 1
        except ValueError:
            streak = 1
    else:
        streak = 1

    longest = max(longest, streak)

    await db.execute(
        """UPDATE user_xp SET
            streak_days = ?, longest_streak = ?, last_active_date = ?
           WHERE user_id = ?""",
        (streak, longest, today, user_id),
    )
    await db.commit()

    # Also update stats.streak_days
    from src.database.dao.stats_dao import set_stat
    await set_stat(user_id, "streak_days", streak)

    return {"streak_days": streak, "longest_streak": longest, "is_new_day": True}


# ══════════════════════════════════════════════════════════
# ACHIEVEMENTS
# ══════════════════════════════════════════════════════════

async def get_achievements() -> list[dict]:
    """Get all active achievements."""
    db = await get_db()
    cursor = await db.execute("SELECT * FROM achievements WHERE is_active = 1")
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def get_user_achievements(user_id: int) -> list[dict]:
    """Get achievements earned by a user."""
    db = await get_db()
    cursor = await db.execute(
        """SELECT a.*, ua.earned_at
           FROM user_achievements ua
           JOIN achievements a ON ua.achievement_code = a.code
           WHERE ua.user_id = ?
           ORDER BY ua.earned_at DESC""",
        (user_id,),
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def grant_achievement(user_id: int, code: str) -> dict | None:
    """Grant an achievement to a user (idempotent). Returns achievement if newly granted."""
    db = await get_db()

    # Check if already earned
    cursor = await db.execute(
        "SELECT id FROM user_achievements WHERE user_id = ? AND achievement_code = ?",
        (user_id, code),
    )
    if await cursor.fetchone():
        return None  # Already earned

    # Get achievement details
    cursor = await db.execute("SELECT * FROM achievements WHERE code = ? AND is_active = 1", (code,))
    achievement = await cursor.fetchone()
    if not achievement:
        return None

    achievement = dict(achievement)

    # Grant
    await db.execute(
        "INSERT INTO user_achievements (user_id, achievement_code) VALUES (?, ?)",
        (user_id, code),
    )
    await db.commit()

    # Award XP
    xp_reward = achievement.get("xp_reward", 0)
    if xp_reward > 0:
        await add_xp(user_id, xp_reward, "achievement", code)

    logger.info("Achievement granted: user=%s code=%s xp=%s", user_id, code, xp_reward)
    return achievement


async def seed_achievements() -> None:
    """Seed default achievements if table is empty."""
    db = await get_db()
    cursor = await db.execute("SELECT COUNT(*) FROM achievements")
    row = await cursor.fetchone()
    if row and row[0] > 0:
        return

    defaults = [
        ("first_check", "First Step", "Birinchi grammatika tekshiruvi", "👣", 10, "general", '{"checks_total": 1}'),
        ("check_10", "Grammar Fan", "10 ta tekshiruv", "📝", 25, "general", '{"checks_total": 10}'),
        ("check_100", "Grammar Master", "100 ta tekshiruv", "🏆", 100, "general", '{"checks_total": 100}'),
        ("quiz_first", "Quiz Starter", "Birinchi quiz", "🧠", 10, "quiz", '{"quiz_played": 1}'),
        ("quiz_perfect", "Perfect Score", "100% to'g'ri javob", "💯", 50, "quiz", '{"quiz_accuracy": 100}'),
        ("quiz_50", "Quiz Champion", "50 ta quiz", "🥇", 150, "quiz", '{"quiz_played": 50}'),
        ("streak_3", "3-Day Streak", "3 kunlik streak", "🔥", 20, "streak", '{"streak_days": 3}'),
        ("streak_7", "Weekly Warrior", "7 kunlik streak", "⚡", 50, "streak", '{"streak_days": 7}'),
        ("streak_30", "Monthly Master", "30 kunlik streak", "🌟", 200, "streak", '{"streak_days": 30}'),
        ("game_win", "Game Winner", "Guruh o'yinini yutish", "🎮", 30, "game", '{"game_wins": 1}'),
        ("level_b1", "Intermediate", "B1 darajaga yetish", "📊", 100, "general", '{"level": "B1"}'),
        ("level_c1", "Advanced", "C1 darajaga yetish", "🎓", 300, "general", '{"level": "C1"}'),
        ("referral_3", "Influencer", "3 ta do'stni taklif qilish", "👥", 75, "social", '{"referrals": 3}'),
        ("night_owl", "Night Owl", "Tunda o'qish (22:00-04:00)", "🦉", 25, "event", '{"time": "night"}'),
        ("weekend_warrior", "Weekend Warrior", "Dam olish kuni faol bo'lish", "🌴", 40, "event", '{"time": "weekend"}'),
        ("pomodoro_10", "Focus Master", "10 ta Pomodoro blokini tugatish", "🍅", 100, "general", '{"pomodoro": 10}'),
        ("iq_genius", "IQ Genius", "IQ testda 120+ ball", "🧠", 200, "quiz", '{"iq_score": 120}'),
    ]
    await db.executemany(
        """INSERT INTO achievements (code, title, description, icon, xp_reward, category, condition)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        defaults,
    )
    await db.commit()
    logger.info("Seeded %d default achievements", len(defaults))
