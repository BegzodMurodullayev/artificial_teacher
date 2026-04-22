import json
from typing import List, Dict, Any, Optional
from src.database.connection import get_db

async def get_materials_by_type(material_type: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    db = await get_db()
    cursor = await db.execute(
        """
        SELECT id, material_type, category, title, author, description, content, created_at
        FROM materials
        WHERE material_type = ?
        ORDER BY id ASC
        LIMIT ? OFFSET ?
        """,
        (material_type, limit, offset)
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]

async def get_material_by_id(material_id: int) -> Optional[Dict[str, Any]]:
    db = await get_db()
    cursor = await db.execute(
        """
        SELECT id, material_type, category, title, author, description, content, created_at
        FROM materials
        WHERE id = ?
        """,
        (material_id,)
    )
    row = await cursor.fetchone()
    return dict(row) if row else None

async def search_materials(query: str, material_type: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
    db = await get_db()
    
    if material_type:
        cursor = await db.execute(
            """
            SELECT id, material_type, category, title, author, description, content, created_at
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
            SELECT id, material_type, category, title, author, description, content, created_at
            FROM materials
            WHERE title LIKE ? OR description LIKE ? OR author LIKE ?
            ORDER BY id ASC
            LIMIT ?
            """,
            (f"%{query}%", f"%{query}%", f"%{query}%", limit)
        )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]

async def insert_material(material_type: str, title: str, category: Optional[str] = None, 
                         author: Optional[str] = None, description: Optional[str] = None, 
                         content: Optional[str] = None) -> int:
    db = await get_db()
    cursor = await db.execute(
        """
        INSERT INTO materials (material_type, category, title, author, description, content)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (material_type, category, title, author, description, content)
    )
    await db.commit()
    row = await cursor.fetchone()
    return row[0] if row else 0

async def count_materials(material_type: str) -> int:
    db = await get_db()
    cursor = await db.execute("SELECT COUNT(*) FROM materials WHERE material_type = ?", (material_type,))
    row = await cursor.fetchone()
    return row[0] if row else 0
