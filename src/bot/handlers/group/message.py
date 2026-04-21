"""
Group message handler — processes #check, #t, #p, #bot, @mention in groups.
"""

import logging

from aiogram import Router, F
from aiogram.types import Message

from src.bot.utils.telegram import safe_reply, escape_html
from src.bot.handlers.user.check import process_grammar_check
from src.bot.handlers.user.translate import process_translation
from src.bot.handlers.user.pronunciation import process_pronunciation
from src.services import ai_service
from src.database.dao import user_dao

logger = logging.getLogger(__name__)
router = Router(name="group_message")


@router.message(F.chat.type.in_({"group", "supergroup"}), F.text)
async def group_text_handler(message: Message, db_user: dict | None = None):
    """Route group messages based on hashtags and @mentions."""
    if not message.text or not db_user:
        return

    text = message.text.strip()
    user_id = db_user["user_id"]
    level = db_user.get("level", "A1")

    # ── #check mode ──
    if text.lower().startswith("#check"):
        content = text[6:].strip()
        if not content and message.reply_to_message and message.reply_to_message.text:
            content = message.reply_to_message.text
        if content:
            await process_grammar_check(message, content, user_id, level)
        return

    # ── #t translation mode ──
    if text.lower().startswith("#t ") or text.lower().startswith("#tarjima "):
        tag = "#tarjima " if text.lower().startswith("#tarjima") else "#t "
        content = text[len(tag):].strip()
        if content:
            # Detect direction
            import re
            is_latin = bool(re.search(r'[a-zA-Z]', content))
            direction = "en_to_uz" if is_latin else "uz_to_en"
            await process_translation(message, content, user_id, direction, level)
        return

    # ── #p pronunciation mode ──
    if text.lower().startswith("#p ") or text.lower().startswith("#talaffuz "):
        tag = "#talaffuz " if text.lower().startswith("#talaffuz") else "#p "
        content = text[len(tag):].strip()

        # Parse accent
        accent = "us"
        if content.lower().startswith("uk:"):
            accent = "uk"
            content = content[3:].strip()
        elif content.lower().startswith("us:"):
            content = content[3:].strip()

        if content:
            await process_pronunciation(message, content, user_id, accent, level)
        return

    # ── #bot AI chat mode ──
    if text.lower().startswith("#bot"):
        content = text[4:].strip()
        if not content and message.reply_to_message and message.reply_to_message.text:
            content = message.reply_to_message.text
        if content:
            await message.chat.do("typing")
            response = await ai_service.ask_ai(content, mode="bot", user_id=user_id, level=level)
            await safe_reply(message, escape_html(response))
        return

    # ── @mention mode ──
    from src.config import settings
    bot_username = settings.BOT_USERNAME.lstrip("@").lower()
    if f"@{bot_username}" in text.lower():
        content = text.lower().replace(f"@{bot_username}", "").strip()
        if content:
            await process_grammar_check(message, content, user_id, level)
        return


def get_group_router() -> Router:
    r = Router(name="group_root")
    r.include_router(router)
    return r
