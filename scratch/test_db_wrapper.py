import asyncio
from src.database.connection import get_db, init_db, close_db

async def test_db():
    print("Testing DB connection...")
    await init_db()
    db = await get_db()
    
    print("DB initialized.")
    cursor = await db.execute("SELECT COUNT(*) FROM users")
    row = await cursor.fetchone()
    print("User count:", row[0] if row else 0)
    
    await close_db()

if __name__ == "__main__":
    asyncio.run(test_db())
