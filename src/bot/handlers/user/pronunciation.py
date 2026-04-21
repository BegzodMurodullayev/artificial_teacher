"""
Pronunciation handler — pronunciation guide + TTS audio.
"""

import logging

from aiogram import Router
from aiogram.types import Message, BufferedInputFile

from src.bot.utils.telegram import safe_reply, escape_html
from src.services import ai_service, tts_service
from src.services.content_service import moderation_warning
from src.database.dao import stats_dao, subscription_dao

logger = logging.getLogger(__name__)
router = Router(name="user_pronunciation")


async def process_pronunciation(
    message: Message,
    text: str,
    user_id: int,
    accent: str = "us",
    level: str = "A1",
) -> None:
    """Core pronunciation logic — AI guide + TTS audio."""

    # Moderation
    warning = moderation_warning(text)
    if warning:
        await safe_reply(message, warning)
        return

    # Check limit
    plan = await subscription_dao.get_user_plan(user_id)
    limit = plan.get("pron_audio_per_day", 5)
    allowed = await stats_dao.check_limit(user_id, "pron_audio", limit)
    if not allowed:
        await safe_reply(
            message,
            f"⚠️ Kunlik talaffuz limiti tugadi ({limit} ta).\n"
            "Obunangizni yangilang: /subscribe"
        )
        return

    await stats_dao.inc_usage(user_id, "pron_audio")
    await stats_dao.inc_stat(user_id, "pron_total")
    await message.chat.do("typing")

    # Get AI pronunciation guide
    result = await ai_service.ask_json(text, mode="pronunciation", level=level, user_id=user_id)

    if result:
        word = escape_html(result.get("word", text))
        ipa_us = escape_html(result.get("ipa_us", ""))
        ipa_uk = escape_html(result.get("ipa_uk", ""))
        syllables = escape_html(result.get("syllables", ""))
        tips = result.get("tips", [])
        examples = result.get("example_sentences", [])
        mistakes = result.get("common_mistakes", [])

        lines = [
            f"🔊 <b>Talaffuz qo'llanmasi</b>\n",
            f"📝 So'z: <b>{word}</b>",
        ]
        if ipa_us:
            lines.append(f"🇺🇸 US: <code>{ipa_us}</code>")
        if ipa_uk:
            lines.append(f"🇬🇧 UK: <code>{ipa_uk}</code>")
        if syllables:
            lines.append(f"📊 Bo'g'inlar: <code>{syllables}</code>")

        if tips:
            lines.append("\n💡 <b>Maslahatlar:</b>")
            for tip in tips[:5]:
                lines.append(f"  • {escape_html(tip)}")

        if examples:
            lines.append("\n📋 <b>Misollar:</b>")
            for ex in examples[:3]:
                lines.append(f"  • <i>{escape_html(ex)}</i>")

        if mistakes:
            lines.append("\n⚠️ <b>Keng tarqalgan xatolar:</b>")
            for m in mistakes[:3]:
                lines.append(f"  • {escape_html(m)}")

        guide_text = "\n".join(lines)
    else:
        guide_text = f"🔊 <b>Talaffuz:</b> <i>{escape_html(text)}</i>"

    await safe_reply(message, guide_text)

    # Generate TTS audio
    await message.chat.do("upload_voice")
    audio_bytes = await tts_service.synthesize_pronunciation(text, accent=accent)

    if audio_bytes:
        audio_file = tts_service.make_audio_file(audio_bytes, f"{text[:30]}.mp3")
        try:
            await message.answer_voice(
                voice=BufferedInputFile(audio_file.read(), filename=audio_file.name),
                caption=f"🔊 {escape_html(text)} ({accent.upper()} accent)",
            )
        except Exception as e:
            logger.warning("Failed to send audio: %s", e)
            await safe_reply(message, "⚠️ Audio fayl yuborib bo'lmadi.")
    else:
        await safe_reply(message, "⚠️ Audio generatsiya qilib bo'lmadi.")
