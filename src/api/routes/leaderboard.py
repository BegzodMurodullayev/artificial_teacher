"""
Leaderboard API routes — /api/leaderboard/*
"""

from fastapi import APIRouter, Request, HTTPException

from src.api.schemas.models import LeaderboardEntry
from src.database.dao import leaderboard_dao

router = APIRouter(prefix="/api/leaderboard", tags=["Leaderboard"])


def _get_uid(request: Request) -> int:
    tg = getattr(request.state, "tg_user", None)
    if not tg:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return tg["id"]


@router.get("/global", response_model=list[LeaderboardEntry])
async def get_global(request: Request, limit: int = 20):
    """Get global learning leaderboard."""
    rows = await leaderboard_dao.get_global_leaderboard(min(limit, 50))
    result = []
    for i, r in enumerate(rows, 1):
        result.append(LeaderboardEntry(
            rank=i,
            user_id=r.get("user_id", 0),
            username=r.get("username", ""),
            first_name=r.get("first_name", ""),
            level=r.get("level", "A1"),
            total_xp=r.get("total_xp", 0),
            learning_score=r.get("learning_score", 0),
            streak_days=r.get("streak_days", 0),
        ))
    return result


@router.get("/myrank")
async def get_my_rank(request: Request):
    """Get current user's rank."""
    uid = _get_uid(request)
    rank = await leaderboard_dao.get_user_rank(uid)
    return {"rank": rank, "user_id": uid}
