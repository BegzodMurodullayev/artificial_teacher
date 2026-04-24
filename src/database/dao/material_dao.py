import json
from typing import List, Dict, Any, Optional
from src.database.connection import get_db


def _deserialize_material(row: Any) -> Dict[str, Any]:
    data = dict(row)
    content = data.get("content")
    if isinstance(content, str) and content:
        try:
            data["content"] = json.loads(content)
        except Exception:
            pass
    if not isinstance(data.get("content"), dict):
        data["content"] = {}
    data["content"].setdefault("tier", data.get("tier", "free"))
    return data

async def get_materials_by_type(material_type: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    db = await get_db()
    cursor = await db.execute(
        """
        SELECT id, material_type, category, tier, title, author, description, content, created_at
        FROM materials
        WHERE material_type = ?
        ORDER BY id ASC
        LIMIT ? OFFSET ?
        """,
        (material_type, limit, offset)
    )
    rows = await cursor.fetchall()
    return [_deserialize_material(row) for row in rows]

async def get_material_by_id(material_id: int) -> Optional[Dict[str, Any]]:
    db = await get_db()
    cursor = await db.execute(
        """
        SELECT id, material_type, category, tier, title, author, description, content, created_at
        FROM materials
        WHERE id = ?
        """,
        (material_id,)
    )
    row = await cursor.fetchone()
    return _deserialize_material(row) if row else None

async def search_materials(query: str, material_type: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
    db = await get_db()
    
    if material_type:
        cursor = await db.execute(
            """
            SELECT id, material_type, category, tier, title, author, description, content, created_at
            FROM materials
            WHERE material_type = ? AND (title LIKE ? OR description LIKE ? OR author LIKE ?)
            ORDER BY id ASC
            LIMIT ?
            """,
            (material_type, f"%{query}%", f"%{query}%", f"%{query}%", limit)
        )
    else:
        cursor = await db.execute(
            """
            SELECT id, material_type, category, tier, title, author, description, content, created_at
            FROM materials
            WHERE title LIKE ? OR description LIKE ? OR author LIKE ?
            ORDER BY id ASC
            LIMIT ?
            """,
            (f"%{query}%", f"%{query}%", f"%{query}%", limit)
    )
    rows = await cursor.fetchall()
    return [_deserialize_material(row) for row in rows]

async def insert_material(
    material_type: str,
    title: str,
    category: Optional[str] = None,
    author: Optional[str] = None,
    description: Optional[str] = None,
    content: Optional[str] = None,
    tier: str = "free",
) -> int:
    db = await get_db()
    serialized_content = content
    if serialized_content:
        try:
            payload = json.loads(serialized_content)
            if isinstance(payload, dict):
                payload.setdefault("tier", tier)
                serialized_content = json.dumps(payload, ensure_ascii=False)
        except Exception:
            pass
    cursor = await db.execute(
        """
        INSERT INTO materials (material_type, category, tier, title, author, description, content)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        RETURNING id
        """,
        (material_type, category, tier, title, author, description, serialized_content)
    )
    await db.commit()
    row = await cursor.fetchone()
    return row[0] if row else 0

async def count_materials(material_type: str) -> int:
    db = await get_db()
    cursor = await db.execute("SELECT COUNT(*) FROM materials WHERE material_type = ?", (material_type,))
    row = await cursor.fetchone()
    return row[0] if row else 0
