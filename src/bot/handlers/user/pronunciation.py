"""
Pronunciation handler — pronunciation guide + TTS audio + HTML report.
Audio is sent directly to the user in chat.
HTML and Audio have separate Private/Public share keyboards.
"""

import logging

from aiogram import Router
from aiogram.types import Message, BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton

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
    """Core pronunciation logic — AI guide + TTS audio + HTML report."""

    warning = moderation_warning(text)
    if warning:
        await safe_reply(message, warning)
        return

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

    result = await ai_service.ask_json(text, mode="pronunciation", level=level, user_id=user_id)

    ipa_us = ipa_uk = syllables = ""
    tips = examples = mistakes = []

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

    # ── Build HTML report keyboard (Private / Public) ──
    username = ""
    if message.from_user:
        username = message.from_user.username or message.from_user.first_name or ""

    html_kb = None
    try:
        from src.bot.handlers.user.check import build_report_keyboard
        html_kb = build_report_keyboard(
            text=text,
            corrected="",
            analysis=[],
            summary="",
            level="",
            username=username,
            rtype="pron",
            extra={
                "ipa_us": ipa_us, "ipa_uk": ipa_uk,
                "syllables": syllables, "tips": tips,
                "examples": examples, "mistakes": mistakes,
            },
        )
    except Exception as e:
        logger.warning("pronunciation HTML report keyboard error: %s", e)

    # Send guide text + HTML share keyboard
    await safe_reply(message, guide_text, reply_markup=html_kb)

    # ── TTS Audio — always send directly to user ──
    await message.chat.do("upload_voice")
    try:
        audio_bytes = await tts_service.synthesize_pronunciation(text, accent=accent)
    except Exception as e:
        logger.warning("TTS synthesis error: %s", e)
        audio_bytes = None

    if audio_bytes:
        audio_caption = f"🔊 <b>{escape_html(text)}</b> ({accent.upper()} accent)"

        # Send audio directly to user
        try:
            sent_voice = await message.answer_voice(
                voice=BufferedInputFile(audio_bytes, filename=f"{text[:30]}.ogg"),
                caption=audio_caption,
                parse_mode="HTML",
            )
        except Exception as e:
            logger.warning("Failed to send voice: %s", e)
            sent_voice = None

        # Cache audio + show Audio Private/Public share keyboard
        try:
            import hashlib
            from src.bot.handlers.inline.inline_handler import _AUDIO_CACHE

            key = hashlib.md5(audio_bytes[:256] if len(audio_bytes) > 256 else audio_bytes).hexdigest()[:16]
            _AUDIO_CACHE[key] = (
                audio_bytes,
                f"{text[:20]}.ogg",
                f"🔊 {text} ({accent.upper()}) | 👤 @{username}" if username else f"🔊 {text} ({accent.upper()})"
            )

            audio_share_kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🔒 Audio (Private)", callback_data=f"aud_prv:{key}"),
                InlineKeyboardButton(text="📢 Audio (Public)",  callback_data=f"aud_pub:{key}"),
            ]])

            await message.answer(
                "🎙 <b>Audio ulashish:</b>",
                reply_markup=audio_share_kb,
                parse_mode="HTML",
            )
        except Exception as e:
            logger.warning("Audio cache/share keyboard error: %s", e)
    else:
        await safe_reply(
            message,
            "⚠️ Audio generatsiya qilib bo'lmadi.\n"
            "<i>TTS xizmati vaqtincha ishlamayapti yoki so'z qo'llab-quvvatlanmaydi.</i>"
        )
