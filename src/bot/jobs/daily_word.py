"""
Daily Word Scheduler — sends a daily English word to all active users.
Registered with APScheduler in main.py.
"""

import logging

from src.services import ai_service
from src.bot.utils.telegram import escape_html
from src.database.connection import get_db

logger = logging.getLogger(__name__)


async def send_daily_word():
    """Generate and send a daily word to opted-in groups and all active users."""
    from src.bot.loader import bot

    logger.info("📖 Daily Word job started")

    # Generate word via AI
    result = await ai_service.ask_json("Generate a useful English word", mode="daily_word")
    if not result:
        logger.warning("Daily word generation failed")
        return

    word = escape_html(result.get("word", "hello"))
    pos = escape_html(result.get("part_of_speech", "noun"))
    definition = escape_html(result.get("definition", ""))
    example = escape_html(result.get("example", ""))
    synonyms = result.get("synonyms", [])
    uzbek = escape_html(result.get("uzbek", ""))

    syn_text = ", ".join(escape_html(s) for s in synonyms[:3]) if synonyms else "—"

    message_text = (
        f"📖 <b>Kunlik so'z</b>\n\n"
        f"🔤 <b>{word}</b> ({pos})\n"
        f"📝 {definition}\n\n"
        f"💬 <i>\"{example}\"</i>\n\n"
        f"🔄 Sinonimlar: {syn_text}\n"
        f"🇺🇿 O'zbekcha: <b>{uzbek}</b>"
    )

    # Send to groups with daily_word enabled
    db = await get_db()
    cursor = await db.execute(
        "SELECT chat_id FROM group_settings WHERE daily_word = 1 AND bot_enabled = 1"
    )
    groups = await cursor.fetchall()

    sent_count = 0
    for row in groups:
        try:
            await bot.send_message(row[0], message_text)
            sent_count += 1
        except Exception as e:
            logger.debug("Daily word to group %s failed: %s", row[0], e)

    logger.info("📖 Daily Word sent to %d groups", sent_count)
