import asyncio
import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
SEED_FILE = BASE_DIR / "src" / "data" / "materials_seed.json"


def _load_seed_items() -> list[dict]:
    if not SEED_FILE.exists():
        raise FileNotFoundError(f"Seed file not found: {SEED_FILE}")
    return json.loads(SEED_FILE.read_text(encoding="utf-8"))


async def seed_materials_async() -> int:
    from src.database.connection import get_db

    db = await get_db()
    items = _load_seed_items()

    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_type TEXT NOT NULL,
            category TEXT,
            tier TEXT DEFAULT 'free',
            title TEXT NOT NULL,
            author TEXT,
            description TEXT,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    try:
        await db.execute("ALTER TABLE materials ADD COLUMN tier TEXT DEFAULT 'free'")
    except Exception:
        pass

    await db.execute("DELETE FROM materials")

    for item in items:
        payload = dict(item.get("content", {}))
        tier = payload.get("tier") or item.get("tier", "free")
        payload["tier"] = tier
        await db.execute(
            """
            INSERT INTO materials (material_type, category, tier, title, author, description, content)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item.get("material_type", "book"),
                item.get("category"),
                tier,
                item.get("title", "Untitled"),
                item.get("author"),
                item.get("description"),
                json.dumps(payload, ensure_ascii=False),
            ),
        )

    await db.commit()
    return len(items)


def seed_materials() -> int:
    return asyncio.run(seed_materials_async())


if __name__ == "__main__":
    count = seed_materials()
    print(f"Seeded {count} materials from {SEED_FILE}")
