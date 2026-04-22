"""
Games API routes — /api/games/*
Handles webapp game results and XP integration.
"""

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Dict

from src.api.schemas.models import GameResultIn
from src.database.dao import webapp_game_dao, stats_dao
from src.services.iq_service import get_iq_test_questions, calculate_iq_score

router = APIRouter(prefix="/api/games", tags=["Games"])

class IQTestResultIn(BaseModel):
    answers: Dict[int, int] # question_id -> selected_option_index


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

@router.get("/iqtest/questions")
async def get_iq_questions(request: Request):
    """Fetch IQ test questions."""
    uid = _get_uid(request)
    questions = get_iq_test_questions(limit=10)
    return {"status": "ok", "questions": questions}

@router.post("/iqtest/result")
async def submit_iq_result(request: Request, body: IQTestResultIn):
    """Submit IQ test answers, calculate score, update stats, and award XP."""
    uid = _get_uid(request)
    
    score = calculate_iq_score(body.answers)
    
    # 1. Update stats (we need a dao method or raw sql to update max_iq_score and iq_score)
    from src.database.connection import get_db
    db = await get_db()
    
    # Check current max score
    cursor = await db.execute("SELECT iq_score, max_iq_score FROM stats WHERE user_id = ?", (uid,))
    row = await cursor.fetchone()
    
    current_max = row["max_iq_score"] if row else 0
    new_max = max(current_max, score)
    
    if row:
        await db.execute(
            "UPDATE stats SET iq_score = ?, max_iq_score = ? WHERE user_id = ?",
            (score, new_max, uid)
        )
    else:
        await db.execute(
            "INSERT INTO stats (user_id, iq_score, max_iq_score) VALUES (?, ?, ?)",
            (uid, score, new_max)
        )
        
    await db.commit()
    
    # 2. Record game result for XP tracking (gamification)
    await webapp_game_dao.save_game_result(
        user_id=uid,
        game_name="IQ Test",
        difficulty="hard",
        score=score,
        won=True if score > 100 else False
    )
    
    return {"status": "ok", "score": score, "new_best": score > current_max}
