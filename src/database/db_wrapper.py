"""
Unified Database Wrapper — supports both SQLite (aiosqlite) and PostgreSQL (asyncpg).
Allows DAOs to use a single syntax (SQLite style '?') and handles translations automatically.
"""

import os
import re
import logging
from typing import Any, List, Optional, Tuple, Dict

logger = logging.getLogger(__name__)


def convert_sql_to_postgres(sql: str) -> str:
    """Convert SQLite syntax to PostgreSQL syntax."""
    # 1. Convert ? to $1, $2...
    count = 0
    def repl(match):
        nonlocal count
        count += 1
        return f"${count}"
    
    sql = re.sub(r'\?', repl, sql)
    
    # 2. Convert datetime('now') to CURRENT_TIMESTAMP
    sql = sql.replace("(datetime('now'))", "CAST(CURRENT_TIMESTAMP AS TEXT)")
    sql = sql.replace("datetime('now')", "CAST(CURRENT_TIMESTAMP AS TEXT)")

    # 3. Convert AUTOINCREMENT to SERIAL for schema definitions
    sql = sql.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")

    # 4. In PostgreSQL, LIMIT ? OFFSET ? -> LIMIT $1 OFFSET $2
    # This is handled automatically by the ? replacement above!
    
    return sql


class CursorWrapper:
    """Simulates aiosqlite Cursor interface."""
    def __init__(self, records: List[Any], rowcount: int = 0):
        self.records = records
        self._rowcount = rowcount

    async def fetchone(self) -> Optional[Any]:
        if self.records:
            return self.records.pop(0)
        return None

    async def fetchall(self) -> List[Any]:
        ret = self.records
        self.records = []
        return ret
        
    @property
    def rowcount(self) -> int:
        return self._rowcount


class PostgresConnectionWrapper:
    """Simulates aiosqlite Connection interface using asyncpg."""
    def __init__(self, pool):
        self.pool = pool

    async def execute(self, sql: str, parameters: tuple = None) -> CursorWrapper:
        sql = convert_sql_to_postgres(sql)
        params = parameters or ()
        
        async with self.pool.acquire() as conn:
            if sql.strip().upper().startswith("SELECT") or "RETURNING" in sql.upper():
                # For SELECT, use fetch
                records = await conn.fetch(sql, *params)
                return CursorWrapper(records)
            else:
                # For INSERT, UPDATE, DELETE, use execute
                status = await conn.execute(sql, *params)
                # status is like "UPDATE 1" or "INSERT 0 1"
                parts = status.split()
                rowcount = int(parts[-1]) if parts[-1].isdigit() else 0
                return CursorWrapper([], rowcount=rowcount)

    async def executemany(self, sql: str, parameters_list: List[tuple]) -> None:
        sql = convert_sql_to_postgres(sql)
        async with self.pool.acquire() as conn:
            await conn.executemany(sql, parameters_list)

    async def executescript(self, sql_script: str) -> None:
        # Convert schema SQL to Postgres types
        sql = sql_script
        sql = sql.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
        sql = sql.replace("(datetime('now'))", "CAST(CURRENT_TIMESTAMP AS TEXT)")
        sql = sql.replace("datetime('now')", "CAST(CURRENT_TIMESTAMP AS TEXT)")
        sql = sql.replace("INTEGER DEFAULT 0\n", "INTEGER DEFAULT 0\n")  # no-op, clean
        import re
        sql = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)

        # PostgreSQL can't run a multi-statement script as one query.
        # Split on ';' and execute each statement individually.
        async with self.pool.acquire() as conn:
            for statement in sql.split(";"):
                stmt = statement.strip()
                if stmt:
                    try:
                        await conn.execute(stmt)
                    except Exception as e:
                        # Log but continue — idempotent re-runs may hit "already exists"
                        err_str = str(e)
                        if any(k in err_str for k in ("already exists", "duplicate")):
                            continue
                        logger.warning("Schema statement failed: %s | SQL: %.120s", e, stmt)

    async def commit(self) -> None:
        # asyncpg auto-commits outside of explicit transactions
        pass
    
    async def close(self) -> None:
        await self.pool.close()


class DatabaseFactory:
    """Creates the appropriate connection wrapper based on URL."""
    _instance = None
    _is_postgres = False

    @classmethod
    async def get_db(cls):
        if cls._instance is None:
            from src.config import settings
            db_url = os.environ.get("DATABASE_URL", "")
            
            if db_url and (db_url.startswith("postgres://") or db_url.startswith("postgresql://")):
                import asyncpg
                logger.info("Connecting to PostgreSQL (Neon DB)...")
                # Handle neon specific scheme if needed
                if db_url.startswith("postgres://"):
                    db_url = db_url.replace("postgres://", "postgresql://", 1)
                
                pool = await asyncpg.create_pool(
                    db_url,
                    min_size=1,
                    max_size=10,
                    command_timeout=60
                )
                cls._instance = PostgresConnectionWrapper(pool)
                cls._is_postgres = True
                logger.info("PostgreSQL Pool created.")
            else:
                import aiosqlite
                from pathlib import Path
                db_path = Path(settings.DB_PATH)
                db_path.parent.mkdir(parents=True, exist_ok=True)
                logger.info("Connecting to SQLite database: %s", db_path)

                conn = await aiosqlite.connect(str(db_path), timeout=20)
                conn.row_factory = aiosqlite.Row

                # Performance pragmas
                await conn.execute("PRAGMA journal_mode=WAL")
                await conn.execute("PRAGMA synchronous=NORMAL")
                await conn.execute("PRAGMA busy_timeout=7000")
                await conn.execute("PRAGMA temp_store=MEMORY")
                await conn.execute("PRAGMA foreign_keys=ON")
                
                cls._instance = conn
                cls._is_postgres = False
                logger.info("SQLite connected.")
                
        return cls._instance

    @classmethod
    async def close_db(cls):
        if cls._instance:
            await cls._instance.close()
            cls._instance = None
            logger.info("Database connection closed")
            
    @classmethod
    def is_postgres(cls) -> bool:
        return cls._is_postgres
