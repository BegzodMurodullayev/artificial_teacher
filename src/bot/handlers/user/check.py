"""
Check handler — grammar checking in private and group modes.
Includes HTML report generation with Private/Public share options.
"""

import logging
import hashlib

from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from src.bot.utils.telegram import safe_reply, escape_html
from src.services import ai_service
from src.services.content_service import moderation_warning
from src.services.level_service import record_signal
from src.database.dao import stats_dao, subscription_dao

logger = logging.getLogger(__name__)
router = Router(name="user_check")

# ── In-memory cache: short_key → (html_bytes, filename, caption) ──
_REPORT_CACHE: dict[str, tuple[bytes, str, str]] = {}


def _cache_key(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()[:16]


async def process_grammar_check(
    message: Message,
    text: str,
    user_id: int,
    level: str = "A1",
) -> None:
    """Core grammar check logic — private and group handlers."""

    warning = moderation_warning(text)
    if warning:
        await safe_reply(message, warning)
        return

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

    await stats_dao.inc_usage(user_id, "checks")
    await stats_dao.inc_stat(user_id, "checks_total")
    await message.chat.do("typing")

    result = await ai_service.ask_json(text, mode="check", level=level, user_id=user_id)

    if not result:
        await safe_reply(message, "❌ Grammatikani tekshirib bo'lmadi. Qayta urinib ko'ring.")
        return

    analysis = result.get("analysis", [])
    corrected = result.get("corrected", text)
    summary = result.get("summary", "")
    estimated_level = result.get("level", "")

    if estimated_level:
        await record_signal(user_id, "check", estimated_level)

    if not analysis:
        response = (
            "✅ <b>Xato topilmadi!</b>\n\n"
            f"📝 <i>{escape_html(text)}</i>\n\n"
            f"📊 Taxminiy daraja: <b>{estimated_level or '?'}</b>\n"
            f"{summary}"
        )
    else:
        lines = [
            "📝 <b>Grammatika tekshiruvi</b>\n",
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

    # ── Build HTML report + Private/Public keyboard ──
    username = message.from_user.username or message.from_user.first_name or "" if message.from_user else ""
    kb = _build_share_keyboard(
        text=text, corrected=corrected, analysis=analysis,
        summary=summary, level=estimated_level, username=username,
        rtype="check",
    )
    await safe_reply(message, response, reply_markup=kb)


def _build_share_keyboard(
    text: str,
    corrected: str,
    analysis: list,
    summary: str,
    level: str,
    username: str,
    rtype: str = "check",
    extra: dict = None,
) -> InlineKeyboardMarkup:
    """Build HTML report, cache it, return Private/Public inline keyboard."""
    try:
        from src.bot.utils.html_report import (
            build_check_report, build_translate_report,
            build_pronunciation_report,
        )

        if rtype == "check":
            html_content = build_check_report(
                original=text, corrected=corrected, analysis=analysis,
                summary=summary, level=level, username=username,
            )
            filename = "grammatika_hisobot.html"
            caption = f"📄 Grammatika Tekshiruv Hisoboti\n👤 @{username}" if username else "📄 Grammatika Hisoboti"
        elif rtype == "translate":
            d = extra or {}
            html_content = build_translate_report(
                original=text, translation=corrected,
                direction=d.get("direction", "uz_to_en"),
                notes=summary, username=username,
            )
            filename = "tarjima_hisobot.html"
            caption = f"🌐 Tarjima Hisoboti\n👤 @{username}" if username else "🌐 Tarjima Hisoboti"
        elif rtype == "pron":
            d = extra or {}
            html_content = build_pronunciation_report(
                word=text, ipa_us=d.get("ipa_us",""), ipa_uk=d.get("ipa_uk",""),
                syllables=d.get("syllables",""), tips=d.get("tips",[]),
                examples=d.get("examples",[]), mistakes=d.get("mistakes",[]),
                username=username,
            )
            filename = "talaffuz_hisobot.html"
            caption = f"🔊 Talaffuz Hisoboti — {text}\n👤 @{username}" if username else f"🔊 Talaffuz Hisoboti — {text}"
        else:
            return None

        html_bytes = html_content.encode("utf-8")
        key = _cache_key(html_content)
        _REPORT_CACHE[key] = (html_bytes, filename, caption)

        buttons = [[
            InlineKeyboardButton(text="🔒 Private", callback_data=f"rpt_prv:{key}"),
            InlineKeyboardButton(text="📢 Public",  callback_data=f"rpt_pub:{key}"),
        ]]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    except Exception as e:
        logger.warning("_build_share_keyboard error: %s", e)
        return None


# ══════════════════════════════════════════════════════════
# CALLBACK HANDLERS — Private / Public
# ══════════════════════════════════════════════════════════

_cb_router = Router(name="report_callbacks")


@_cb_router.callback_query(F.data.startswith("rpt_prv:"))
async def callback_report_private(callback: CallbackQuery):
    """Send HTML report privately to the user."""
    key = callback.data.split(":")[1]
    entry = _REPORT_CACHE.get(key)
    if not entry:
        await callback.answer("⚠️ Hisobot muddati o'tdi, qayta so'rang.", show_alert=True)
        return

    html_bytes, filename, caption = entry
    try:
        from aiogram.types import BufferedInputFile
        doc = BufferedInputFile(html_bytes, filename=filename)
        await callback.message.answer_document(
            document=doc,
            caption=f"🔒 <b>Shaxsiy hisobot</b>\n{caption}",
            parse_mode="HTML",
        )
        await callback.answer("✅ Hisobot yuborildi!")
    except Exception as e:
        logger.warning("report_private send failed: %s", e)
        await callback.answer("❌ Yuborib bo'lmadi.", show_alert=True)


@_cb_router.callback_query(F.data.startswith("rpt_pub:"))
async def callback_report_public(callback: CallbackQuery):
    """Post HTML report to public INLINE_HTML_CHANNEL with user ID label."""
    key = callback.data.split(":")[1]
    entry = _REPORT_CACHE.get(key)
    if not entry:
        await callback.answer("⚠️ Hisobot muddati o'tdi, qayta so'rang.", show_alert=True)
        return

    html_bytes, filename, caption = entry
    user = callback.from_user
    uid = user.id if user else 0
    uname = f"@{user.username}" if user and user.username else (user.first_name if user else "")

    try:
        from src.config import settings
        from src.bot.loader import bot as _bot
        from aiogram.types import BufferedInputFile

        channel = settings.INLINE_HTML_CHANNEL
        if not channel or channel in (0, "0", ""):
            await callback.answer("⚠️ Kanal sozlanmagan.", show_alert=True)
            return

        # Add user ID label to channel caption
        pub_caption = (
            f"📂 <b>Hisobot</b>\n"
            f"{caption}\n"
            f"🆔 <code>#{uid}</code> | {uname}"
        )

        doc = BufferedInputFile(html_bytes, filename=filename)
        msg = await _bot.send_document(
            chat_id=channel,
            document=doc,
            caption=pub_caption,
            parse_mode="HTML",
        )
        # Build link to channel message with ID label
        channel_str = str(channel).lstrip("@")
        if msg and hasattr(msg, "message_id"):
            mid = msg.message_id
            link = f"https://t.me/{channel_str}/{mid}"
            await callback.message.answer(
                f"📢 <b>Kanalga joylashtirildi!</b>\n"
                f"🔗 <a href='{link}'>👆 Ko'rish (#{mid})</a>\n"
                f"🆔 Sizning ID: <code>#{uid}</code>",
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
        await callback.answer("✅ Kanalga joylashtirildi!")
    except Exception as e:
        logger.warning("report_public send failed: %s", e)
        await callback.answer("❌ Kanalga joylashtirib bo'lmadi.", show_alert=True)


def get_check_callback_router():
    return _cb_router


# Export share keyboard builder for reuse in other handlers
build_report_keyboard = _build_share_keyboard
