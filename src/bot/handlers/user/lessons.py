"""
Lesson & Grammar callback handlers — handles topic selection and AI lesson generation.
"""

import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery

from src.bot.utils.telegram import safe_edit, safe_answer_callback, escape_html
from src.services import ai_service
from src.services.content_service import get_static_lesson_pack, get_static_rule_text
from src.database.dao import stats_dao, subscription_dao

logger = logging.getLogger(__name__)
router = Router(name="user_lessons")


@router.callback_query(F.data.startswith("lesson:"))
async def callback_lesson_select(callback: CallbackQuery, db_user: dict | None = None):
    """Handle lesson topic selection."""
    if not db_user:
        return

    topic = callback.data.split(":")[1]
    user_id = db_user["user_id"]
    level = db_user.get("level", "A1")

    # Check limit
    plan = await subscription_dao.get_user_plan(user_id)
    limit = plan.get("lessons_per_day", 3)
    allowed = await stats_dao.check_limit(user_id, "lessons", limit)
    if not allowed:
        await safe_answer_callback(callback, f"⚠️ Kunlik dars limiti tugadi ({limit})", show_alert=True)
        return

    await stats_dao.inc_usage(user_id, "lessons")
    await stats_dao.inc_stat(user_id, "lessons_total")

    if topic == "custom":
        # Set pending state so the next plain message becomes the lesson topic
        try:
            from src.bot.handlers.user.message_handler import set_pending_custom_lesson
            set_pending_custom_lesson(user_id)
        except Exception:
            pass
        await safe_edit(
            callback,
            "✏️ <b>Custom dars</b>\n\nDars mavzusini yozing (masalan: \"Present Perfect\"):\n"
            "<i>Keyingi xabaringiz dars mavzusi sifatida qabul qilinadi.</i>"
        )
        await safe_answer_callback(callback)
        return

    # Try static pack first
    pack = get_static_lesson_pack(topic)
    if pack:
        lines = [f"📚 <b>{escape_html(pack['title'])}</b>\n"]
        lines.append(f"📊 Daraja: <b>{pack['level']}</b>\n")

        if pack.get("objectives"):
            lines.append("\n🎯 <b>Maqsadlar:</b>")
            for obj in pack["objectives"]:
                lines.append(f"  • {escape_html(obj)}")

        if pack.get("vocabulary"):
            lines.append("\n📝 <b>Lug'at:</b>")
            for v in pack["vocabulary"][:8]:
                word = escape_html(v.get("word", ""))
                defn = escape_html(v.get("definition", ""))
                example = escape_html(v.get("example", ""))
                uz = escape_html(v.get("uz", ""))
                lines.append(f"  • <b>{word}</b> — {defn}")
                lines.append(f"    💡 <i>{example}</i>")
                if uz:
                    lines.append(f"    🇺🇿 {uz}")

        if pack.get("grammar"):
            lines.append(f"\n📖 <b>Grammatika:</b>\n{escape_html(pack['grammar'])}")

        if pack.get("exercises"):
            lines.append("\n✏️ <b>Mashqlar:</b>")
            for ex in pack["exercises"]:
                lines.append(f"  • {escape_html(ex)}")

        await safe_edit(callback, "\n".join(lines))
        await safe_answer_callback(callback)
        return

    # AI-generated lesson
    await safe_edit(callback, f"📚 <b>{escape_html(topic.title())}</b>\n\n⏳ Dars tayyorlanmoqda...")
    await safe_answer_callback(callback)

    prompt = f"Create a lesson about '{topic}' for level {level}."
    response = await ai_service.ask_ai(prompt, mode="lesson", level=level, user_id=user_id)
    await safe_edit(callback, f"📚 <b>{escape_html(topic.title())}</b>\n\n{escape_html(response)}")


@router.callback_query(F.data.startswith("rule:"))
async def callback_rule_select(callback: CallbackQuery, db_user: dict | None = None):
    """Handle grammar rule selection."""
    if not db_user:
        return

    rule = callback.data.split(":")[1]
    user_id = db_user["user_id"]
    level = db_user.get("level", "A1")

    if rule == "custom":
        # Set pending state
        try:
            from src.bot.handlers.user.message_handler import set_pending_custom_lesson
            set_pending_custom_lesson(user_id)
        except Exception:
            pass
        await safe_edit(
            callback,
            "✏️ <b>Custom qoida</b>\n\nGrammatika mavzusini yozing (masalan: \"reported speech\"):\n"
            "<i>Keyingi xabaringiz qoida mavzusi sifatida qabul qilinadi.</i>"
        )
        await safe_answer_callback(callback)
        return

    # Try static rule first
    static = get_static_rule_text(rule)
    if static:
        await safe_edit(callback, static)
        await safe_answer_callback(callback)
        return

    # AI-generated explanation
    await safe_edit(callback, f"📖 <b>{escape_html(rule.title())}</b>\n\n⏳ Qoida tayyorlanmoqda...")
    await safe_answer_callback(callback)

    prompt = f"Explain the grammar rule '{rule}' for level {level}."
    response = await ai_service.ask_ai(prompt, mode="grammar_rule", level=level, user_id=user_id)
    await safe_edit(callback, f"📖 <b>{escape_html(rule.title())}</b>\n\n{escape_html(response)}")
