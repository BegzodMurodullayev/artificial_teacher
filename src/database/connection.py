"""
Async SQLite connection manager using aiosqlite.
Provides a singleton connection with WAL mode and performance pragmas.
"""

import logging
from pathlib import Path

from src.database.db_wrapper import DatabaseFactory

logger = logging.getLogger(__name__)


async def get_db():
    """Get the singleton database connection (SQLite or PostgreSQL)."""
    return await DatabaseFactory.get_db()


async def close_db() -> None:
    """Close the database connection gracefully."""
    await DatabaseFactory.close_db()


async def init_db() -> None:
    """Initialize database schema — create tables, run migrations, seed defaults."""
    db = await get_db()

    # Read and execute the init schema SQL
    schema_path = Path(__file__).parent / "migrations" / "init_schema.sql"
    if schema_path.exists():
        schema_sql = schema_path.read_text(encoding="utf-8")
        await db.executescript(schema_sql)
        logger.info("Database schema initialized from init_schema.sql")
    else:
        logger.warning("init_schema.sql not found at %s", schema_path)

    # Run backward-compatibility migrations
    await _run_migrations(db)

    # Seed default plans if empty
    await _seed_default_plans(db)

    await db.commit()
    logger.info("Database initialization complete")


async def _run_migrations(db) -> None:
    """Run ALTER TABLE migrations for backward compatibility."""
    
    if DatabaseFactory.is_postgres():
        # PostgreSQL syntax for checking columns
        async def _table_columns(table: str) -> set[str]:
            cursor = await db.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = $1", 
                (table,)
            )
            rows = await cursor.fetchall()
            return {row[0] for row in rows}
    else:
        # SQLite syntax for checking columns
        async def _table_columns(table: str) -> set[str]:
            cursor = await db.execute(f"PRAGMA table_info({table})")
            rows = await cursor.fetchall()
            return {row[1] for row in rows}

    async def _add_column_if_missing(table: str, column: str, definition: str) -> None:
        cols = await _table_columns(table)
        if column not in cols:
            await db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
            logger.info("Migration: added %s.%s", table, column)

    # Users table migrations
    await _add_column_if_missing("users", "role", "TEXT DEFAULT 'user'")
    await _add_column_if_missing("users", "is_banned", "INTEGER DEFAULT 0")

    # Plans table migrations
    await _add_column_if_missing("plans", "pron_audio_per_day", "INTEGER DEFAULT 5")

    # Subscriptions table migrations
    await _add_column_if_missing("subscriptions", "granted_days", "INTEGER DEFAULT 30")

    # Payments table migrations
    await _add_column_if_missing("payments", "duration_days", "INTEGER DEFAULT 30")
    await _add_column_if_missing("materials", "tier", "TEXT DEFAULT 'free'")

    # Ensure defaults
    await db.execute("UPDATE users SET role='user' WHERE role IS NULL OR role=''")
    await db.execute("UPDATE users SET is_banned=0 WHERE is_banned IS NULL")
    await db.execute("UPDATE subscriptions SET granted_days=30 WHERE granted_days IS NULL OR granted_days=0")
    await db.execute("UPDATE payments SET duration_days=30 WHERE duration_days IS NULL OR duration_days=0")
    await db.execute("UPDATE materials SET tier='free' WHERE tier IS NULL OR tier=''")


async def _seed_default_plans(db) -> None:
    """Insert default subscription plans if the plans table is empty."""
    cursor = await db.execute("SELECT COUNT(*) FROM plans")
    row = await cursor.fetchone()
    if row and row[0] > 0:
        return

    default_plans = [
        ("free", "Free ✨", 0, 0, 12, 5, 3, 20, 5, 0, 0, 0, 0, "", 1),
        ("standard", "Standard ⭐", 29000, 290000, 40, 15, 8, 80, 10, 0, 1, 1, 0, "⭐", 1),
        ("pro", "Pro 💎", 59000, 590000, 120, 40, 20, 250, 20, 1, 1, 1, 1, "💎", 1),
        ("premium", "Premium 👑", 99000, 990000, 999, 999, 50, 999, 40, 1, 1, 1, 1, "👑", 1),
    ]
    await db.executemany(
        """INSERT INTO plans (
            name, display_name, price_monthly, price_yearly,
            checks_per_day, quiz_per_day, lessons_per_day, ai_messages_day,
            pron_audio_per_day, voice_enabled, inline_enabled, group_enabled,
            iq_test_enabled, badge, is_active
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        default_plans,
    )
    logger.info("Seeded %d default plans", len(default_plans))
