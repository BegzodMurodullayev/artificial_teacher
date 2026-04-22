"""
Payment DAO — payment creation, approval, rejection, querying.
"""

import logging
from datetime import datetime

from src.database.connection import get_db

logger = logging.getLogger(__name__)


async def create_payment(
    user_id: int,
    plan_name: str,
    amount: float,
    duration_days: int = 30,
    currency: str = "UZS",
    method: str = "manual",
    receipt_file_id: str = "",
    note: str = "",
) -> int:
    """Create a new pending payment. Returns payment ID."""
    db = await get_db()
    cursor = await db.execute(
        """INSERT INTO payments (user_id, plan_name, amount, duration_days,
           currency, method, status, receipt_file_id, note)
           VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)""",
        (user_id, plan_name, amount, duration_days, currency, method, receipt_file_id, note),
    )
    await db.commit()
    row = await cursor.fetchone()
    return row[0] if row else 0


async def get_payment(payment_id: int) -> dict | None:
    """Get a payment by ID."""
    db = await get_db()
    cursor = await db.execute("SELECT * FROM payments WHERE id = ?", (payment_id,))
    row = await cursor.fetchone()
    return dict(row) if row else None


async def approve_payment(payment_id: int, admin_id: int) -> None:
    """Mark payment as approved."""
    db = await get_db()
    now = datetime.utcnow().isoformat(timespec="seconds")
    await db.execute(
        "UPDATE payments SET status = 'approved', reviewed_at = ?, reviewed_by = ? WHERE id = ?",
        (now, admin_id, payment_id),
    )
    await db.commit()


async def reject_payment(payment_id: int, admin_id: int, note: str = "") -> None:
    """Mark payment as rejected."""
    db = await get_db()
    now = datetime.utcnow().isoformat(timespec="seconds")
    await db.execute(
        "UPDATE payments SET status = 'rejected', reviewed_at = ?, reviewed_by = ?, note = ? WHERE id = ?",
        (now, admin_id, note, payment_id),
    )
    await db.commit()


async def get_pending_payments() -> list[dict]:
    """Get all pending payments, newest first."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM payments WHERE status = 'pending' ORDER BY created_at DESC"
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def count_pending_payments() -> int:
    """Count pending payments."""
    db = await get_db()
    cursor = await db.execute("SELECT COUNT(*) FROM payments WHERE status = 'pending'")
    row = await cursor.fetchone()
    return row[0] if row else 0


async def get_user_payments(user_id: int, limit: int = 20) -> list[dict]:
    """Get user's payment history."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM payments WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit),
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def get_total_revenue() -> float:
    """Get total approved revenue."""
    db = await get_db()
    cursor = await db.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM payments WHERE status = 'approved'"
    )
    row = await cursor.fetchone()
    return row[0] if row else 0


async def update_receipt(payment_id: int, file_id: str) -> None:
    """Update the receipt file ID for a payment."""
    db = await get_db()
    await db.execute(
        "UPDATE payments SET receipt_file_id = ? WHERE id = ?",
        (file_id, payment_id),
    )
    await db.commit()
