"""
Games API routes — /api/games/*
Handles webapp game results and XP integration.
"""

from fastapi import APIRouter, Request, HTTPException

from src.api.schemas.models import GameResultIn
from src.database.dao import webapp_game_dao

router = APIRouter(prefix="/api/games", tags=["Games"])


def _get_uid(request: Request) -> int:
    tg = getattr(request.state, "tg_user", None)
    if not tg:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return tg["id"]


@router.post("/result")
async def save_game_result(request: Request, body: GameResultIn):
    """Save game result and award XP."""
    uid = _get_uid(request)
    result = await webapp_game_dao.save_game_result(
        user_id=uid,
        game_name=body.game_name,
        difficulty=body.difficulty,
        score=body.score,
        won=body.won,
    )
    return {"status": "ok", "data": result}
