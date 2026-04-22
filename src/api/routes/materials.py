from fastapi import APIRouter, Query, HTTPException, Request
from typing import List, Dict, Any, Optional

from src.database.dao import material_dao

def _get_uid(request: Request) -> int:
    tg = getattr(request.state, "tg_user", None)
    if not tg:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return tg["id"]

router = APIRouter(prefix="/materials", tags=["Materials"])

@router.get("")
async def get_materials(
    material_type: str = Query(..., description="Type of material: 'book', 'fact', 'quiz', 'quiz_variant'"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    request: Request = None
) -> List[Dict[str, Any]]:
    """Get a list of materials by type."""
    materials = await material_dao.get_materials_by_type(material_type, limit, offset)
    return materials

@router.get("/search")
async def search_materials(
    q: str = Query(..., min_length=1),
    material_type: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=50),
    request: Request = None
) -> List[Dict[str, Any]]:
    """Search materials by query."""
    materials = await material_dao.search_materials(q, material_type, limit)
    return materials

@router.get("/{material_id}")
async def get_material(
    material_id: int,
    request: Request = None
) -> Dict[str, Any]:
    """Get a single material by ID."""
    material = await material_dao.get_material_by_id(material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    # For content field, we can parse it to JSON if it's a string, but the frontend can also parse it.
    import json
    if material.get("content"):
        try:
            material["content"] = json.loads(material["content"])
        except Exception:
            pass
    return material
