"""
Compatibility handlers for legacy inline keyboards from the old bot UI.

Users may still press buttons on previously sent messages, so these handlers
translate old callback payloads into the current aiogram flows where possible.
"""

import logging

from aiogram import Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from src.bot.keyboards.user_menu import (
    back_button,
    cabinet_menu,
    edu_menu,
    games_menu,
    grammar_rules_keyboard,
    lesson_topics_keyboard,
    resolve_webapp_url,
    test_menu,
    user_main_menu,
)
from src.bot.utils.telegram import escape_html, safe_answer_callback, safe_edit
from src.database.dao import subscription_dao
from src.services.mode_manager import get_mode, set_mode

logger = logging.getLogger(__name__)
router = Router(name="legacy_callbacks")


_LEGACY_ACTIONS = {
    "sponsor_recheck": "sponsor_recheck",
    "menu_back": "main_menu",
    "menu_section_learn": "edu_menu",
    "menu_section_practice": "test_menu",
    "menu_section_progress": "cabinet_menu",
    "menu_section_games": "games_menu",
    "menu_admin_hint": "admin_hint",
    "do_check": "check_mode",
    "do_translate": "translate_mode",
    "do_quiz": "quiz",
    "do_iq": "iqtest",
    "do_daily": "daily_word",
    "do_lesson": "lessons",
    "do_pron": "pronunciation_mode",
    "do_rules": "grammar",
    "do_stats": "stats",
    "do_level": "settings",
    "do_level_auto": "auto_level",
    "do_about": "about",
    "do_webapp": "webapp",
    "menu_subscribe": "subscribe",
    "menu_mypayments": "mypayments",
    "menu_enter_promo": "promo",
    "menu_bonus_center": "bonus",
    "menu_referral_panel": "bonus",
    "menu_progress_panel": "stats",
    "menu_progress_html": "stats_html",
    "menu_leaderboard": "leaderboard",
}

_LEGACY_PREFIX_ACTIONS = (
    ("trdir__", "translate_direction"),
    ("lesson__", "lesson_topic"),
    ("rule__", "rule_topic"),
    ("pron__", "pronounce_word"),
    ("pronaccent__", "pronunciation_accent"),
    ("setlvl__", "set_level"),
    ("games_info_", "games_info"),
    ("qpick_", "restart_quiz"),
    ("qtime_", "restart_quiz"),
    ("qlang_", "restart_quiz"),
    ("qans_", "restart_quiz"),
)


def resolve_legacy_callback_action(data: str | None) -> str | None:
    """Map an old callback payload to a compatibility action."""
    if not data:
        return None
    if data in _LEGACY_ACTIONS:
        return _LEGACY_ACTIONS[data]
    for prefix, action in _LEGACY_PREFIX_ACTIONS:
        if data.startswith(prefix):
            return action
    return None


def _patched_callback(callback: CallbackQuery, data: str) -> CallbackQuery:
    return callback.model_copy(update={"data": data})


def _translate_direction_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇺🇿→🇬🇧 UZ→EN", callback_data="mode:uz_to_en"),
                InlineKeyboardButton(text="🇬🇧→🇺🇿 EN→UZ", callback_data="mode:en_to_uz"),
            ],
            [
                InlineKeyboardButton(text="🇷🇺→🇬🇧 RU→EN", callback_data="mode:ru_to_en"),
                InlineKeyboardButton(text="🇬🇧→🇷🇺 EN→RU", callback_data="mode:en_to_ru"),
            ],
            [InlineKeyboardButton(text="🔙 Ortga", callback_data="back:main")],
        ]
    )


def _pronunciation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇺🇸 US", callback_data="pronaccent__us"),
                InlineKeyboardButton(text="🇬🇧 UK", callback_data="pronaccent__uk"),
            ],
            [InlineKeyboardButton(text="🔙 Ortga", callback_data="back:main")],
        ]
    )


async def _send_reply_menu(callback: CallbackQuery, title: str, reply_markup) -> None:
    await safe_answer_callback(callback)
    await safe_edit(callback, title)
    if callback.message:
        await callback.message.answer("Pastdagi tugmalar orqali davom eting.", reply_markup=reply_markup)


async def _send_main_menu(callback: CallbackQuery, db_user: dict | None) -> None:
    plan_name = await subscription_dao.get_active_plan_name(db_user["user_id"]) if db_user else "free"
    role = db_user.get("role", "user") if db_user else "user"
    await _send_reply_menu(
        callback,
        "🏠 <b>Asosiy menyu</b>\n\nEski inline menyu yangilandi.",
        user_main_menu(plan_name, role=role),
    )


@router.callback_query()
async def callback_legacy_fallback(callback: CallbackQuery, db_user: dict | None = None):
    """Handle legacy callbacks and gracefully absorb unsupported old buttons."""
    data = callback.data or ""
    action = resolve_legacy_callback_action(data)

    if action == "sponsor_recheck":
        from src.bot.handlers.user.start import callback_check_sponsor

        await callback_check_sponsor(_patched_callback(callback, "check_sponsor"), db_user)
        return

    if action == "main_menu":
        await _send_main_menu(callback, db_user)
        return

    if action == "edu_menu":
        await _send_reply_menu(callback, "🎓 <b>Ta'lim bo'limi</b>\nEski menyu yangi tugmalarga ko'chirildi.", edu_menu())
        return

    if action == "test_menu":
        await _send_reply_menu(callback, "🎯 <b>Sinovlar bo'limi</b>", test_menu())
        return

    if action == "cabinet_menu":
        await _send_reply_menu(callback, "👤 <b>Kabinet bo'limi</b>", cabinet_menu())
        return

    if action == "games_menu":
        await _send_reply_menu(callback, "🎮 <b>O'yinlar bo'limi</b>", games_menu())
        return

    if action == "admin_hint":
        if callback.message:
            from src.bot.handlers.admin.dashboard import cmd_admin

            if db_user and db_user.get("role") in {"admin", "owner"}:
                await safe_answer_callback(callback)
                await cmd_admin(callback.message, db_user)
            else:
                await safe_answer_callback(callback, "⚠️ Admin panel faqat adminlar uchun.", show_alert=True)
        return

    if action == "check_mode":
        if not db_user:
            return
        await set_mode(db_user["user_id"], "CORRECTION")
        await safe_answer_callback(callback)
        await safe_edit(
            callback,
            "✅ <b>Grammatika tekshiruv rejimi</b>\n\n"
            "Ingliz tilida matn yozing. Men xatolarni topib, to'g'risini tushuntiraman.",
            reply_markup=back_button(),
        )
        return

    if action == "translate_mode":
        await safe_answer_callback(callback)
        await safe_edit(
            callback,
            "🌐 <b>Tarjima rejimi</b>\n\nYo'nalishni tanlang:",
            reply_markup=_translate_direction_keyboard(),
        )
        return

    if action == "translate_direction":
        from src.bot.handlers.user.start import callback_set_mode

        direction = data.split("__", 1)[1]
        await callback_set_mode(_patched_callback(callback, f"mode:{direction}"), db_user)
        return

    if action == "quiz":
        if callback.message:
            from src.bot.handlers.quiz.quiz_start import cmd_quiz

            await safe_answer_callback(callback)
            await cmd_quiz(callback.message, db_user)
        return

    if action == "iqtest":
        if callback.message:
            from src.bot.handlers.quiz.quiz_start import cmd_iqtest_quiz

            await safe_answer_callback(callback)
            await cmd_iqtest_quiz(callback.message, db_user)
        return

    if action == "daily_word":
        if callback.message and db_user:
            from src.bot.handlers.user.menu import _send_daily_word

            await safe_answer_callback(callback)
            await _send_daily_word(callback.message, db_user["user_id"])
        return

    if action == "lessons":
        await safe_answer_callback(callback)
        await safe_edit(
            callback,
            "📚 <b>Darslar</b>\n\nMavzuni tanlang:",
            reply_markup=lesson_topics_keyboard(),
        )
        return

    if action == "lesson_topic":
        from src.bot.handlers.user.lessons import callback_lesson_select

        topic = data.split("__", 1)[1]
        await callback_lesson_select(_patched_callback(callback, f"lesson:{topic}"), db_user)
        return

    if action == "pronunciation_mode":
        if not db_user:
            return
        await set_mode(db_user["user_id"], "pronunciation:us")
        await safe_answer_callback(callback)
        await safe_edit(
            callback,
            "🔊 <b>Talaffuz rejimi</b>\n\nAksentni tanlang yoki darrov so'z yuboring.",
            reply_markup=_pronunciation_keyboard(),
        )
        return

    if action == "pronunciation_accent":
        if not db_user:
            return
        accent = "uk" if data.endswith("__uk") else "us"
        await set_mode(db_user["user_id"], f"pronunciation:{accent}")
        await safe_answer_callback(callback, f"✅ {accent.upper()} aksent tanlandi.")
        await safe_edit(
            callback,
            f"🔊 <b>{accent.upper()} talaffuz rejimi</b>\n\nEndi so'z yoki ibora yuboring.",
            reply_markup=_pronunciation_keyboard(),
        )
        return

    if action == "pronounce_word":
        if callback.message and db_user:
            from src.bot.handlers.user.pronunciation import process_pronunciation

            word = data.split("__", 1)[1].strip()
            if not word:
                await safe_answer_callback(callback, "⚠️ So'z topilmadi.", show_alert=True)
                return
            current_mode = await get_mode(db_user["user_id"])
            accent = "uk" if current_mode == "pronunciation:uk" else "us"
            await safe_answer_callback(callback)
            await safe_edit(
                callback,
                f"🔊 <b>{escape_html(word)}</b> talaffuzi tayyorlanmoqda...",
                reply_markup=back_button(),
            )
            await process_pronunciation(
                callback.message,
                word,
                db_user["user_id"],
                accent=accent,
                level=db_user.get("level", "A1"),
            )
        return

    if action == "grammar":
        await safe_answer_callback(callback)
        await safe_edit(
            callback,
            "📖 <b>Grammatika qoidalari</b>\n\nMavzuni tanlang:",
            reply_markup=grammar_rules_keyboard(),
        )
        return

    if action == "rule_topic":
        from src.bot.handlers.user.lessons import callback_rule_select

        rule = data.split("__", 1)[1]
        await callback_rule_select(_patched_callback(callback, f"rule:{rule}"), db_user)
        return

    if action == "stats":
        if callback.message:
            from src.bot.handlers.user.profile import cmd_mystats

            await safe_answer_callback(callback)
            await cmd_mystats(callback.message, db_user)
        return

    if action == "settings":
        if callback.message and db_user:
            from src.bot.keyboards.user_menu import level_picker_keyboard

            level = db_user.get("level", "A1")
            username = callback.from_user.username if callback.from_user else ""
            display_name = db_user.get("first_name", "") or ""
            name_line = f"@{username}" if username else display_name or "—"

            kb = level_picker_keyboard()
            kb.inline_keyboard.append([InlineKeyboardButton(text="✏️ Ismni o'zgartirish", callback_data="settings:rename")])

            await safe_answer_callback(callback)
            await callback.message.answer(
                f"⚙️ <b>Sozlamalar</b>\n\n"
                f"👤 Ism: <b>{name_line}</b>\n"
                f"📊 Daraja: <b>{level}</b>\n\n"
                "Darajangizni o'zgartiring:",
                reply_markup=kb,
            )
        return

    if action == "set_level":
        from src.bot.handlers.user.start import callback_set_level

        level = data.split("__", 1)[1]
        await callback_set_level(_patched_callback(callback, f"set_level:{level}"), db_user)
        return

    if action == "auto_level":
        await safe_answer_callback(callback)
        await safe_edit(
            callback,
            "🔍 <b>Auto daraja</b>\n\nQuiz, tekshiruv va mashqlar natijalariga qarab darajangiz avtomatik yangilanadi.",
            reply_markup=back_button(),
        )
        return

    if action == "about":
        if callback.message:
            from src.bot.handlers.user.start import cmd_help

            await safe_answer_callback(callback)
            await cmd_help(callback.message, db_user)
        return

    if action == "webapp":
        if callback.message:
            plan_name = await subscription_dao.get_active_plan_name(db_user["user_id"]) if db_user else "free"
            webapp_url = resolve_webapp_url(plan_name)
            if not webapp_url:
                await safe_answer_callback(callback, "⚠️ WebApp URL ulanmagan.", show_alert=True)
                return
            await safe_answer_callback(callback)
            await safe_edit(
                callback,
                "📱 <b>WebApp</b>\n\nIlovani ochish uchun tugmani bosing.",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="📱 Ilovani ochish", web_app=WebAppInfo(url=webapp_url))],
                        [InlineKeyboardButton(text="🔙 Ortga", callback_data="back:main")],
                    ]
                ),
            )
        return

    if action == "subscribe":
        if callback.message:
            from src.bot.handlers.subscription.plans import cmd_subscribe

            await safe_answer_callback(callback)
            await cmd_subscribe(callback.message, db_user)
        return

    if action == "mypayments":
        if callback.message:
            from src.bot.handlers.subscription.plans import cmd_mypayments

            await safe_answer_callback(callback)
            await cmd_mypayments(callback.message, db_user)
        return

    if action == "promo":
        if not db_user:
            return
        await set_mode(db_user["user_id"], "PROMO_PENDING")
        await safe_answer_callback(callback)
        await safe_edit(
            callback,
            "🎫 <b>Promo kodni yuboring</b>\n\nMasalan: <code>SPRING2026</code>",
            reply_markup=back_button(),
        )
        return

    if action == "bonus":
        if callback.message and db_user:
            from src.bot.handlers.user.profile import send_bonus_panel

            await safe_answer_callback(callback)
            await send_bonus_panel(callback.message, db_user)
        return

    if action == "stats_html":
        if callback.message:
            from src.bot.handlers.user.profile import cmd_mystats

            await safe_answer_callback(callback, "ℹ️ HTML hisobot o'rniga joriy statistika ochildi.")
            await cmd_mystats(callback.message, db_user)
        return

    if action == "leaderboard":
        if callback.message:
            from src.bot.handlers.user.profile import cmd_leaderboard

            await safe_answer_callback(callback)
            await cmd_leaderboard(callback.message, db_user)
        return

    if action == "games_info":
        kind = data.split("_", 2)[2]
        hints = {
            "word": "🔤 So'z topish o'yini yangi menyuda mavjud.",
            "error": "🔎 Xato topish o'yini yangi menyuda mavjud.",
            "translation": "🏃 Tarjima poygasi yangi menyuda mavjud.",
            "rewards": "🏆 Mukofotlar bo'limi hozircha kabinet va reyting orqali ko'rinadi.",
            "admin": "👥 Guruh o'yinlari uchun botni guruhga qo'shib buyruqlar orqali ishlating.",
            "mafia": "🕵️ Mafiya guruhda /mafia buyrug'i orqali ishlaydi.",
        }
        hint_text = hints.get(kind, "🎮 O'yin menyusi yangilangan.")
        await safe_answer_callback(callback)
        await safe_edit(
            callback,
            f"{hint_text}\n\nPastdagi tugmalar orqali davom eting.",
            reply_markup=back_button(),
        )
        if callback.message:
            await callback.message.answer("Yangi o'yinlar menyusi:", reply_markup=games_menu())
        return

    if action == "restart_quiz":
        await safe_answer_callback(
            callback,
            "ℹ️ Bu eski quiz xabari. Iltimos, /quiz yoki /iqtest ni qayta bosing.",
            show_alert=True,
        )
        return

    logger.warning("Unhandled callback_query data=%r from user_id=%s", data, callback.from_user.id if callback.from_user else "?")
    await safe_answer_callback(
        callback,
        "⚠️ Bu tugma eskirgan yoki vaqtincha ishlamayapti. /start ni qayta bosing.",
        show_alert=True,
    )
