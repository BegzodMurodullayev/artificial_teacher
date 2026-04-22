"""
Translate handler — bidirectional UZ↔EN translation.
"""

import logging

from aiogram import Router
from aiogram.types import Message

from src.bot.utils.telegram import safe_reply, escape_html
from src.services import ai_service
from src.database.dao import stats_dao, subscription_dao

logger = logging.getLogger(__name__)
router = Router(name="user_translate")


async def process_translation(
    message: Message,
    text: str,
    user_id: int,
    direction: str = "uz_to_en",
    level: str = "A1",
) -> None:
    """Core translation logic."""

    # Check daily limit
    plan = await subscription_dao.get_user_plan(user_id)
    limit = plan.get("ai_messages_day", 20)
    allowed = await stats_dao.check_limit(user_id, "ai_messages", limit)
    if not allowed:
        await safe_reply(
            message,
            f"⚠️ Kunlik AI limit tugadi ({limit} ta).\nObunangizni yangilang: /subscribe"
        )
        return

    await stats_dao.inc_usage(user_id, "ai_messages")
    await stats_dao.inc_stat(user_id, "translations_total")
    await message.chat.do("typing")

    mode = f"translate_{direction}"
    result = await ai_service.ask_json(text, mode=mode, level=level, user_id=user_id)

    if not result:
        await safe_reply(message, "❌ Tarjima qilib bo'lmadi. Qayta urinib ko'ring.")
        return

    original = escape_html(result.get("original", text))
    translation = escape_html(result.get("translation", ""))
    notes = escape_html(result.get("notes", ""))

    if direction == "uz_to_en":
        header = "🌐 <b>UZ → EN Tarjima</b>"
        orig_label = "🇺🇿"
        trans_label = "🇬🇧"
    elif direction == "en_to_uz":
        header = "🌐 <b>EN → UZ Tarjima</b>"
        orig_label = "🇬🇧"
        trans_label = "🇺🇿"
    elif direction == "ru_to_en":
        header = "🌐 <b>RU → EN Tarjima</b>"
        orig_label = "🇷🇺"
        trans_label = "🇬🇧"
    elif direction == "en_to_ru":
        header = "🌐 <b>EN → RU Tarjima</b>"
        orig_label = "🇬🇧"
        trans_label = "🇷🇺"
    else:
        header = "🌐 <b>Tarjima</b>"
        orig_label = "📝"
        trans_label = "📝"

    response = (
        f"{header}\n\n"
        f"{orig_label} <i>{original}</i>\n\n"
        f"{trans_label} <b>{translation}</b>"
    )
    if notes:
        response += f"\n\n📌 <i>{notes}</i>"

    await safe_reply(message, response)
