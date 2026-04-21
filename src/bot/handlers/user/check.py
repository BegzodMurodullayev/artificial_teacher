"""
Check handler — grammar checking in private and group modes.
"""

import logging

from aiogram import Router, F
from aiogram.types import Message, BufferedInputFile

from src.bot.utils.telegram import safe_reply, escape_html
from src.services import ai_service
from src.services.content_service import moderation_warning
from src.services.level_service import record_signal
from src.database.dao import stats_dao, subscription_dao

logger = logging.getLogger(__name__)
router = Router(name="user_check")


async def process_grammar_check(
    message: Message,
    text: str,
    user_id: int,
    level: str = "A1",
) -> None:
    """Core grammar check logic — used by both private and group handlers."""

    # Moderation check
    warning = moderation_warning(text)
    if warning:
        await safe_reply(message, warning)
        return

    # Check daily limit
    plan = await subscription_dao.get_user_plan(user_id)
    limit = plan.get("checks_per_day", 12)
    allowed = await stats_dao.check_limit(user_id, "checks", limit)
    if not allowed:
        await safe_reply(
            message,
            f"⚠️ Kunlik limit tugadi ({limit} ta tekshiruv).\n"
            "Obunangizni yangilang: /subscribe"
        )
        return

    # Increment usage
    await stats_dao.inc_usage(user_id, "checks")
    await stats_dao.inc_stat(user_id, "checks_total")

    # Show typing indicator
    await message.chat.do("typing")

    # Call AI
    result = await ai_service.ask_json(text, mode="check", level=level, user_id=user_id)

    if not result:
        await safe_reply(message, "❌ Grammatikani tekshirib bo'lmadi. Qayta urinib ko'ring.")
        return

    # Format response
    analysis = result.get("analysis", [])
    corrected = result.get("corrected", text)
    summary = result.get("summary", "")
    estimated_level = result.get("level", "")

    # Record level signal
    if estimated_level:
        await record_signal(user_id, "check", estimated_level)

    if not analysis:
        # No errors found
        response = (
            "✅ <b>Xato topilmadi!</b>\n\n"
            f"📝 <i>{escape_html(text)}</i>\n\n"
            f"📊 Taxminiy daraja: <b>{estimated_level or '?'}</b>\n"
            f"{summary}"
        )
    else:
        # Errors found
        lines = [
            f"📝 <b>Grammatika tekshiruvi</b>\n",
            f"<i>{escape_html(text)}</i>\n",
        ]

        for i, err in enumerate(analysis[:10], 1):
            error = escape_html(err.get("error", ""))
            correction = escape_html(err.get("correction", ""))
            explanation = escape_html(err.get("explanation", ""))
            lines.append(f"\n❌ <b>Xato {i}:</b> <code>{error}</code>")
            lines.append(f"✅ <b>To'g'ri:</b> <code>{correction}</code>")
            if explanation:
                lines.append(f"💡 {explanation}")

        lines.append(f"\n📋 <b>To'g'ri variant:</b>\n<i>{escape_html(corrected)}</i>")

        if estimated_level:
            lines.append(f"\n📊 Taxminiy daraja: <b>{estimated_level}</b>")
        if summary:
            lines.append(f"\n📌 {escape_html(summary)}")

        response = "\n".join(lines)

    await safe_reply(message, response)


# private_check_handler moved to message_handler.py
