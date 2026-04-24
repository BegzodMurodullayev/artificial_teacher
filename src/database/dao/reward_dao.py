"""
Reward DAO — wallet, referral, promo codes, promo packs, and config.
"""

import uuid
import logging
from src.database.connection import get_db

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════
# REWARD WALLET
# ══════════════════════════════════════════════════════════

async def get_wallet(user_id: int) -> dict:
    """Get or create user's reward wallet."""
    db = await get_db()
    cursor = await db.execute("SELECT * FROM reward_wallet WHERE user_id = ?", (user_id,))
    row = await cursor.fetchone()
    if row:
        return dict(row)
    ref_code = uuid.uuid4().hex[:8].upper()
    await db.execute(
        "INSERT INTO reward_wallet (user_id, referral_code) VALUES (?, ?) ON CONFLICT (user_id) DO NOTHING",
        (user_id, ref_code),
    )
    await db.commit()
    cursor = await db.execute("SELECT * FROM reward_wallet WHERE user_id = ?", (user_id,))
    row = await cursor.fetchone()
    return dict(row) if row else {"user_id": user_id, "points": 0, "referral_code": ref_code}


async def add_points(user_id: int, amount: float) -> None:
    """Add points to user's wallet."""
    await get_wallet(user_id)  # ensure exists
    db = await get_db()
    await db.execute(
        "UPDATE reward_wallet SET points = points + ? WHERE user_id = ?",
        (amount, user_id),
    )
    await db.commit()


async def deduct_points(user_id: int, amount: float) -> bool:
    """Deduct points. Returns False if insufficient."""
    wallet = await get_wallet(user_id)
    if wallet.get("points", 0) < amount:
        return False
    db = await get_db()
    await db.execute(
        "UPDATE reward_wallet SET points = points - ? WHERE user_id = ?",
        (amount, user_id),
    )
    await db.commit()
    return True


async def find_by_referral_code(code: str) -> dict | None:
    """Find wallet by referral code."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM reward_wallet WHERE referral_code = ?", (code.upper(),)
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


async def set_referred_by(user_id: int, referrer_id: int) -> None:
    """Set who referred this user."""
    await get_wallet(user_id)
    db = await get_db()
    await db.execute(
        "UPDATE reward_wallet SET referred_by = ? WHERE user_id = ? AND referred_by = 0",
        (referrer_id, user_id),
    )
    await db.execute(
        "UPDATE reward_wallet SET total_referrals = total_referrals + 1 WHERE user_id = ?",
        (referrer_id,),
    )
    await db.commit()


# ══════════════════════════════════════════════════════════
# PROMO CODES
# ══════════════════════════════════════════════════════════

async def get_promo_code(code: str) -> dict | None:
    """Get promo code details."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM promo_codes WHERE UPPER(code) = UPPER(?) AND is_active = 1",
        (code,),
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


async def use_promo_code(code: str) -> None:
    """Increment promo code usage count."""
    db = await get_db()
    await db.execute(
        "UPDATE promo_codes SET used_count = used_count + 1 WHERE UPPER(code) = UPPER(?)",
        (code,),
    )
    await db.commit()


async def create_promo_code(
    code: str, plan_name: str, days: int, max_uses: int = 1, created_by: int = 0
) -> int:
    """Create a new promo code."""
    db = await get_db()
    cursor = await db.execute(
        """INSERT INTO promo_codes (code, plan_name, days, max_uses, created_by, is_active)
           VALUES (?, ?, ?, ?, ?, 1)
           RETURNING id""",
        (code.upper(), plan_name, days, max_uses, created_by),
    )
    await db.commit()
    row = await cursor.fetchone()
    return row[0] if row else 0


# ══════════════════════════════════════════════════════════
# CONFIG (payment_config, reward_settings)
# ══════════════════════════════════════════════════════════

async def get_config(table: str, key: str, default: str = "") -> str:
    """Get a config value."""
    if table not in ("payment_config", "reward_settings"):
        return default
    db = await get_db()
    cursor = await db.execute(f"SELECT value FROM {table} WHERE key = ?", (key,))
    row = await cursor.fetchone()
    return row[0] if row else default


async def set_config(table: str, key: str, value: str) -> None:
    """Set a config value."""
    if table not in ("payment_config", "reward_settings"):
        return
    db = await get_db()
    await db.execute(
        f"INSERT INTO {table} (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    await db.commit()


async def get_all_config(table: str) -> dict[str, str]:
    """Get all config values from a table."""
    if table not in ("payment_config", "reward_settings"):
        return {}
    db = await get_db()
    cursor = await db.execute(f"SELECT key, value FROM {table}")
    rows = await cursor.fetchall()
    return {row[0]: row[1] for row in rows}
