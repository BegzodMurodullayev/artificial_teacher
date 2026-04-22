"""
WebApp Game DAO — persistence for webapp games.
"""

import logging
from src.database.connection import get_db
from src.database.dao.xp_dao import add_xp

logger = logging.getLogger(__name__)


async def save_game_result(user_id: int, game_name: str, difficulty: str, score: int, won: bool) -> dict:
    """Save webapp game result and award XP."""
    db = await get_db()
    won_int = 1 if won else 0
    
    # Save result
    await db.execute(
        """INSERT INTO webapp_game_results 
           (user_id, game_name, difficulty, score, won) 
           VALUES (?, ?, ?, ?, ?)""",
        (user_id, game_name, difficulty, score, won_int),
    )
    await db.commit()
    
    # Award XP based on score or just a fixed amount
    # Let's say XP = score (assuming score is reasonably balanced)
    # or if score is too big, maybe we cap it or calculate it
    # But usually frontend calculates score. Let's just award the score as XP directly.
    xp_awarded = 0
    xp_data = {}
    
    if score > 0:
        xp_awarded = score
        # Cap XP from a single game to prevent abuse (e.g. max 200 XP)
        if xp_awarded > 200:
            xp_awarded = 200
            
        xp_data = await add_xp(
            user_id=user_id,
            amount=xp_awarded,
            source=f"webapp_game_{game_name}",
            metadata={"difficulty": difficulty, "won": won, "original_score": score}
        )
        logger.info(f"User {user_id} earned {xp_awarded} XP from {game_name}")

    return {
        "saved": True,
        "xp_awarded": xp_awarded,
        "total_xp": xp_data.get("total_xp", 0),
        "current_level": xp_data.get("current_level", 1)
    }
