"""
WebApp data handler.
Processes Telegram WebApp sendData payloads from the main app and hosted materials pages.
"""

import json
import logging

from aiogram import F, Router
from aiogram.types import Message

from src.bot.utils.telegram import safe_reply
from src.database.dao import stats_dao, webapp_dao

logger = logging.getLogger(__name__)
router = Router(name="user_webapp_data")


QUIZ_EVENT_TYPES = {
    "quiz_result",
    "standard_quiz_result",
    "pro_quiz_result",
    "premium_lesson_quiz",
    "premium_exam_reading",
}


def _to_int(value, default: int = 0) -> int:
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return default


def _clean_text(value: object, max_len: int = 160) -> str:
    text = str(value or "").strip()
    return text[:max_len]


async def _store_quiz_like_event(user_id: int, event_type: str, payload: dict) -> tuple[int, int]:
    score = max(0, _to_int(payload.get("score")))
    total = max(score, _to_int(payload.get("total"), 0))
    if total <= 0:
        total = 1

    lessons = 1 if event_type == "premium_lesson_quiz" else 0
    topic = _clean_text(
        payload.get("lessonTitle")
        or payload.get("topicTitle")
        or payload.get("track")
        or payload.get("level")
    )

    await stats_dao.inc_stat(user_id, "quiz_played", 1)
    if score:
        await stats_dao.inc_stat(user_id, "quiz_correct", score)
    if lessons:
        await stats_dao.inc_stat(user_id, "lessons_total", lessons)

    await webapp_dao.upsert_progress(
        user_id=user_id,
        quiz=1,
        lessons=lessons,
        topics=topic,
        note=event_type,
        points=score,
    )
    return score, total


@router.message(F.web_app_data)
async def handle_webapp_data(message: Message, db_user: dict | None = None):
    """Accept and process Telegram WebApp sendData payloads."""
    if not message.web_app_data:
        return

    user_id = db_user["user_id"] if db_user else (message.from_user.id if message.from_user else 0)
    if not user_id:
        return

    raw_data = message.web_app_data.data
    try:
        payload = json.loads(raw_data)
    except json.JSONDecodeError:
        logger.warning("Invalid WebApp payload from user_id=%s: %r", user_id, raw_data)
        await safe_reply(message, "⚠️ WebAppdan kelgan ma'lumotni o'qib bo'lmadi.")
        return

    event_type = _clean_text(payload.get("type") or payload.get("action"))
    if not event_type:
        logger.warning("WebApp payload without event type: %s", payload)
        await safe_reply(message, "⚠️ WebApp xabari turi aniqlanmadi.")
        return

    logger.info("WebApp data received user_id=%s type=%s", user_id, event_type)

    if event_type == "pomodoro_done":
        minutes = max(0, _to_int(payload.get("minutes")))
        await webapp_dao.upsert_progress(
            user_id=user_id,
            focus_minutes=minutes,
            note="pomodoro_done",
            points=max(0, minutes // 5),
        )
        await safe_reply(message, f"⏱ Pomodoro saqlandi: <b>{minutes}</b> daqiqa.")
        return

    if event_type == "tracker_sync":
        words = max(0, _to_int(payload.get("words")))
        quiz = max(0, _to_int(payload.get("quizzes", payload.get("quiz"))))
        lessons = max(0, _to_int(payload.get("lessons")))
        focus_minutes = max(0, _to_int(payload.get("focus_minutes", payload.get("minutes"))))
        await webapp_dao.upsert_progress(
            user_id=user_id,
            words=words,
            quiz=quiz,
            lessons=lessons,
            focus_minutes=focus_minutes,
            note="tracker_sync",
            points=words + quiz + lessons,
        )
        if quiz:
            await stats_dao.inc_stat(user_id, "quiz_played", quiz)
        if lessons:
            await stats_dao.inc_stat(user_id, "lessons_total", lessons)
        await safe_reply(
            message,
            "📈 Progress saqlandi:\n"
            f"• So'zlar: <b>{words}</b>\n"
            f"• Quiz: <b>{quiz}</b>\n"
            f"• Darslar: <b>{lessons}</b>",
        )
        return

    if event_type in QUIZ_EVENT_TYPES:
        score, total = await _store_quiz_like_event(user_id, event_type, payload)
        await safe_reply(message, f"🧠 Natija saqlandi: <b>{score}/{total}</b>.")
        return

    if event_type == "premium_interest":
        await webapp_dao.upsert_progress(
            user_id=user_id,
            topics=_clean_text(payload.get("level") or payload.get("topicId")),
            note="premium_interest",
        )
        await safe_reply(
            message,
            "⭐ Premium qiziqishingiz saqlandi.\n\nTariflarni ko'rish uchun /subscribe ni bosing.",
        )
        return

    if event_type == "pro_iq_result":
        iq_index = max(0, _to_int(payload.get("iqIndex")))
        current_stats = await stats_dao.get_stats(user_id)
        best_iq = max(iq_index, _to_int(current_stats.get("max_iq_score")))
        await stats_dao.set_stat(user_id, "iq_score", iq_index)
        await stats_dao.set_stat(user_id, "max_iq_score", best_iq)
        await webapp_dao.upsert_progress(
            user_id=user_id,
            quiz=1,
            note="pro_iq_result",
            points=max(1, _to_int(payload.get("score"))),
        )
        await safe_reply(message, f"🧩 IQ natijasi saqlandi: <b>{iq_index}</b>.")
        return

    if event_type == "pro_voice_practice":
        pronunciation = max(0, _to_int(payload.get("pronunciation")))
        fluency = max(0, _to_int(payload.get("fluency")))
        rhythm = max(0, _to_int(payload.get("rhythm")))
        seconds = max(0, _to_int(payload.get("seconds")))
        await stats_dao.inc_stat(user_id, "pron_total", 1)
        await webapp_dao.upsert_progress(
            user_id=user_id,
            note="pro_voice_practice",
            topics=_clean_text(payload.get("phrase")),
            points=max(1, round((pronunciation + fluency + rhythm) / 30)),
        )
        await safe_reply(
            message,
            "🔊 Voice practice saqlandi:\n"
            f"• Pronunciation: <b>{pronunciation}</b>\n"
            f"• Fluency: <b>{fluency}</b>\n"
            f"• Davomiylik: <b>{seconds}</b> soniya",
        )
        return

    if event_type in {"premium_exam_writing_practice", "premium_exam_speaking_practice"}:
        track = _clean_text(payload.get("track"))
        await stats_dao.inc_stat(user_id, "lessons_total", 1)
        await webapp_dao.upsert_progress(
            user_id=user_id,
            lessons=1,
            topics=track,
            note=event_type,
            points=1,
        )
        label = "Writing practice" if event_type.endswith("writing_practice") else "Speaking practice"
        await safe_reply(message, f"✍️ {label} holati saqlandi.")
        return

    await webapp_dao.upsert_progress(
        user_id=user_id,
        note=event_type,
        topics=_clean_text(payload.get("track") or payload.get("lessonTitle") or payload.get("topicTitle")),
    )
    await safe_reply(message, "📦 WebApp ma'lumoti qabul qilindi.")
