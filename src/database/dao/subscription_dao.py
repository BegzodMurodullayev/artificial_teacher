"""
Subscription & Plan DAO — plan definitions, subscription lifecycle.
"""

import logging
from datetime import datetime, timedelta

from src.database.connection import get_db

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════
# PLANS
# ══════════════════════════════════════════════════════════

async def get_plan(name: str) -> dict | None:
    """Get plan by name."""
    db = await get_db()
    cursor = await db.execute("SELECT * FROM plans WHERE name = ?", (name,))
    row = await cursor.fetchone()
    return dict(row) if row else None


async def get_all_plans() -> list[dict]:
    """Get all active plans."""
    db = await get_db()
    cursor = await db.execute("SELECT * FROM plans WHERE is_active = 1 ORDER BY price_monthly ASC")
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def update_plan_field(plan_name: str, field: str, value) -> None:
    """Update a specific plan field. Field must be whitelisted."""
    allowed = {
        "display_name", "price_monthly", "price_yearly",
        "checks_per_day", "quiz_per_day", "lessons_per_day",
        "ai_messages_day", "pron_audio_per_day",
        "voice_enabled", "inline_enabled", "group_enabled",
        "iq_test_enabled", "badge", "is_active",
    }
    if field not in allowed:
        return
    db = await get_db()
    await db.execute(f"UPDATE plans SET {field} = ? WHERE name = ?", (value, plan_name))
    await db.commit()


# ══════════════════════════════════════════════════════════
# SUBSCRIPTIONS
# ══════════════════════════════════════════════════════════

async def get_active_subscription(user_id: int) -> dict | None:
    """Get user's active, non-expired subscription."""
    db = await get_db()
    now = datetime.utcnow().isoformat(timespec="seconds")
    cursor = await db.execute(
        """SELECT * FROM subscriptions
           WHERE user_id = ? AND is_active = 1
             AND (expires_at IS NULL OR expires_at > ?)
           ORDER BY id DESC LIMIT 1""",
        (user_id, now),
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


async def get_active_plan_name(user_id: int) -> str:
    """Get user's current plan name (defaults to 'free')."""
    sub = await get_active_subscription(user_id)
    if sub:
        return sub.get("plan_name", "free")
    return "free"


async def get_user_plan(user_id: int) -> dict:
    """Get full plan details for a user."""
    plan_name = await get_active_plan_name(user_id)
    plan = await get_plan(plan_name)
    if plan:
        return plan
    # Fallback to free plan
    return await get_plan("free") or {
        "name": "free",
        "checks_per_day": 12,
        "quiz_per_day": 5,
        "lessons_per_day": 3,
        "ai_messages_day": 20,
        "pron_audio_per_day": 5,
        "voice_enabled": 0,
        "inline_enabled": 0,
    }


async def activate_subscription(
    user_id: int,
    plan_name: str,
    days: int = 30,
) -> int:
    """Activate a subscription: deactivate old, create new. Returns new subscription ID."""
    db = await get_db()
    now = datetime.utcnow()
    expires = now + timedelta(days=days)

    # Deactivate all existing active subscriptions
    await db.execute(
        "UPDATE subscriptions SET is_active = 0 WHERE user_id = ? AND is_active = 1",
        (user_id,),
    )

    # Create new subscription
    cursor = await db.execute(
        """INSERT INTO subscriptions (user_id, plan_name, started_at, expires_at, granted_days, is_active)
           VALUES (?, ?, ?, ?, ?, 1) RETURNING id""",
        (user_id, plan_name, now.isoformat(timespec="seconds"),
         expires.isoformat(timespec="seconds"), days),
    )
    await db.commit()
    row = await cursor.fetchone()
    return row[0] if row else 0


async def remaining_days(user_id: int) -> int:
    """Get remaining days on current subscription."""
    sub = await get_active_subscription(user_id)
    if not sub or not sub.get("expires_at"):
        return 0
    try:
        expires = datetime.fromisoformat(sub["expires_at"])
        now = datetime.utcnow()
        delta = (expires - now).days
        return max(0, delta)
    except (ValueError, TypeError):
        return 0


async def deactivate_expired() -> int:
    """Deactivate all expired subscriptions. Returns count."""
    db = await get_db()
    now = datetime.utcnow().isoformat(timespec="seconds")
    cursor = await db.execute(
        """UPDATE subscriptions SET is_active = 0
           WHERE is_active = 1 AND expires_at IS NOT NULL AND expires_at <= ?""",
        (now,),
    )
    await db.commit()
    return cursor.rowcount


async def count_paid_users() -> int:
    """Count users with active paid subscriptions."""
    db = await get_db()
    now = datetime.utcnow().isoformat(timespec="seconds")
    cursor = await db.execute(
        """SELECT COUNT(DISTINCT user_id) FROM subscriptions
           WHERE is_active = 1 AND plan_name != 'free'
             AND (expires_at IS NULL OR expires_at > ?)""",
        (now,),
    )
    row = await cursor.fetchone()
    return row[0] if row else 0
