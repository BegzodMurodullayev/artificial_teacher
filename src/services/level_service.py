"""
Level Service — auto-level adjustment based on quiz/check signals.
Ported from the signal-based algorithm in the original db.py.
"""

import logging
from src.config import settings
from src.database.dao import quiz_dao, user_dao

logger = logging.getLogger(__name__)

LEVELS = settings.LEVELS  # ["A1", "A2", "B1", "B2", "C1", "C2"]


def _level_index(level: str) -> float:
    """Convert level string to numeric index."""
    try:
        return float(LEVELS.index(level))
    except ValueError:
        return 0.0


def _index_to_level(index: float) -> str:
    """Convert numeric index back to level string."""
    idx = max(0, min(len(LEVELS) - 1, round(index)))
    return LEVELS[idx]


async def record_signal(
    user_id: int,
    source: str,
    estimated_level: str,
    weight: float = 1.0,
) -> None:
    """Record a level estimation signal from any source (check, quiz, etc.)."""
    if estimated_level not in LEVELS:
        return
    await quiz_dao.add_level_signal(user_id, source, estimated_level, weight)
    logger.debug("Signal: user=%s source=%s level=%s weight=%.1f",
                 user_id, source, estimated_level, weight)


async def auto_adjust_from_signals(user_id: int) -> dict:
    """
    Auto-adjust user level based on accumulated signals.
    Algorithm:
    - Get last 6 signals
    - Calculate weighted average
    - If avg >= current + 0.9 and count >= 3 → level up
    - If avg <= current - 0.9 and count >= 3 → level down
    Returns {"changed": bool, "old": str, "new": str}
    """
    user = await user_dao.get_user(user_id)
    if not user:
        return {"changed": False, "old": "A1", "new": "A1"}

    current = user.get("level", "A1")
    current_idx = _level_index(current)

    signals = await quiz_dao.get_recent_signals(user_id, limit=6)
    if len(signals) < 3:
        return {"changed": False, "old": current, "new": current}

    # Calculate weighted average
    total_weight = 0
    weighted_sum = 0
    for sig in signals:
        w = sig.get("weight", 1.0)
        idx = _level_index(sig.get("estimated_level", "A1"))
        weighted_sum += idx * w
        total_weight += w

    if total_weight == 0:
        return {"changed": False, "old": current, "new": current}

    avg = weighted_sum / total_weight
    new_level = current

    if avg >= current_idx + 0.9 and current_idx < len(LEVELS) - 1:
        new_level = _index_to_level(current_idx + 1)
        logger.info("Level UP: user=%s %s → %s (avg=%.2f)", user_id, current, new_level, avg)
    elif avg <= current_idx - 0.9 and current_idx > 0:
        new_level = _index_to_level(current_idx - 1)
        logger.info("Level DOWN: user=%s %s → %s (avg=%.2f)", user_id, current, new_level, avg)

    if new_level != current:
        await user_dao.set_level(user_id, new_level)
        return {"changed": True, "old": current, "new": new_level}

    return {"changed": False, "old": current, "new": current}


async def auto_adjust_from_quiz(
    user_id: int,
    correct: int,
    total: int,
    quiz_level: str = "A1",
) -> dict:
    """
    Auto-adjust level based on quiz performance.
    - 90%+ at current level → level up signal
    - 40%- at current level → level down signal
    """
    if total < 3:
        return {"changed": False, "old": quiz_level, "new": quiz_level}

    accuracy = correct / total
    quiz_idx = _level_index(quiz_level)

    if accuracy >= 0.9:
        # Strong performance → signal higher level
        estimated = _index_to_level(min(quiz_idx + 1, len(LEVELS) - 1))
        await record_signal(user_id, "quiz_high", estimated, weight=1.5)
    elif accuracy >= 0.7:
        # Good performance → signal current level
        await record_signal(user_id, "quiz_good", quiz_level, weight=1.0)
    elif accuracy <= 0.4:
        # Poor performance → signal lower level
        estimated = _index_to_level(max(quiz_idx - 1, 0))
        await record_signal(user_id, "quiz_low", estimated, weight=1.5)
    else:
        # Average → weak signal at current level
        await record_signal(user_id, "quiz_avg", quiz_level, weight=0.5)

    return await auto_adjust_from_signals(user_id)


def calculate_iq_score(
    correct: int,
    total: int,
    avg_difficulty: float = 0.5,
) -> int:
    """
    Calculate IQ score estimate from quiz results.
    Formula: 86 + (accuracy * 17) + (total * 0.35) + (difficulty * 10)
    """
    if total == 0:
        return 85
    accuracy = correct / total
    score = 86 + (accuracy * 17) + (total * 0.35) + (avg_difficulty * 10)
    return max(70, min(160, round(score)))
