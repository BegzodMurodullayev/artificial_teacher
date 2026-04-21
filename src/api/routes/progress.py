"""
Progress API routes — /api/progress/*
Sync progress data between WebApp and backend.
"""

from fastapi import APIRouter, Request, HTTPException

from src.api.schemas.models import ProgressIn, ProgressOut
from src.database.dao import webapp_dao

router = APIRouter(prefix="/api/progress", tags=["Progress"])


def _get_uid(request: Request) -> int:
    tg = getattr(request.state, "tg_user", None)
    if not tg:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return tg["id"]


@router.get("/today", response_model=ProgressOut)
async def get_today(request: Request):
    """Get today's progress."""
    uid = _get_uid(request)
    data = await webapp_dao.get_today_progress(uid)
    return ProgressOut(**{k: data.get(k, 0) for k in ProgressOut.model_fields})


@router.get("/week", response_model=list[ProgressOut])
async def get_week(request: Request):
    """Get last 7 days progress."""
    uid = _get_uid(request)
    rows = await webapp_dao.get_progress(uid, days=7)
    return [
        ProgressOut(**{k: r.get(k, 0) for k in ProgressOut.model_fields})
        for r in rows
    ]


@router.post("/sync")
async def sync_progress(request: Request, body: ProgressIn):
    """Sync progress from WebApp to backend."""
    uid = _get_uid(request)
    await webapp_dao.upsert_progress(
        user_id=uid,
        words=body.words,
        quiz=body.quiz,
        lessons=body.lessons,
        focus_minutes=body.focus_minutes,
        topics=body.topics,
        note=body.note,
        points=body.points,
    )
    return {"status": "ok", "synced": True}
