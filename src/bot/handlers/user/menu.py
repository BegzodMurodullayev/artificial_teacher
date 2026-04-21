"""
Menu dispatcher — handles reply keyboard button presses.
Maps button text (✅ Check, 🌐 Translate, etc.) to appropriate actions.
"""

import logging

from aiogram import Router, F
from aiogram.types import Message

from src.bot.keyboards.user_menu import resolve_menu_action, user_main_menu
from src.bot.utils.telegram import safe_reply
from src.database.dao import subscription_dao

logger = logging.getLogger(__name__)
router = Router(name="menu_dispatch")


@router.message(F.text.in_([
    "✅ Tekshirish", "✅ Check",
    "🌐 Tarjima", "🌐 Translate",
    "🔊 Talaffuz", "🔊 Pronunciation",
    "🧠 Quiz",
    "📚 Darslar", "📚 Lessons",
    "📖 Grammatika", "📖 Grammar",
    "📊 Statistika", "📊 My Stats",
    "⭐ Obuna", "⭐ Subscribe",
    "⚙️ Sozlamalar", "⚙️ Settings",
    "ℹ️ Yordam", "ℹ️ Help",
    "🛡 Admin Panel",
]))
async def menu_button_handler(message: Message, db_user: dict | None = None):
    """Route menu button presses to the appropriate handler."""
    if not db_user or not message.text:
        return

    action = resolve_menu_action(message.text)
    if not action:
        return

    user_id = db_user["user_id"]
    level = db_user.get("level", "A1")

    if action == "check":
        await safe_reply(
            message,
            "✅ <b>Grammatika tekshiruv rejimi</b>\n\n"
            "Ingliz tilida matn yozing — men xatolarni topaman va tuzataman!\n\n"
            "💡 <i>Masalan: \"I goes to school yesterday\"</i>"
        )

    elif action == "translate":
        from src.bot.keyboards.user_menu import InlineKeyboardMarkup, InlineKeyboardButton
        buttons = [
            [
                InlineKeyboardButton(text="🇺🇿→🇬🇧 UZ→EN", callback_data="tr_mode:uz_to_en"),
                InlineKeyboardButton(text="🇬🇧→🇺🇿 EN→UZ", callback_data="tr_mode:en_to_uz"),
            ],
        ]
        await safe_reply(
            message,
            "🌐 <b>Tarjima rejimi</b>\n\nYo'nalishni tanlang:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        )

    elif action == "pronunciation":
        await safe_reply(
            message,
            "🔊 <b>Talaffuz rejimi</b>\n\n"
            "Ingliz tilidagi so'z yoki ibora yuboring.\n"
            "Men IPA transkripsiyasi va audio bilan javob beraman.\n\n"
            "💡 <i>Masalan: \"pronunciation\"</i>"
        )

    elif action == "quiz":
        # Forward to quiz command handler
        from src.bot.handlers.quiz.quiz_start import cmd_quiz
        await cmd_quiz(message, db_user)

    elif action == "lessons":
        from src.bot.keyboards.user_menu import lesson_topics_keyboard
        await safe_reply(
            message,
            "📚 <b>Darslar</b>\n\nMavzuni tanlang:",
            reply_markup=lesson_topics_keyboard(),
        )

    elif action == "grammar":
        from src.bot.keyboards.user_menu import grammar_rules_keyboard
        await safe_reply(
            message,
            "📖 <b>Grammatika qoidalari</b>\n\nMavzuni tanlang:",
            reply_markup=grammar_rules_keyboard(),
        )

    elif action == "stats":
        from src.bot.handlers.user.profile import cmd_mystats
        await cmd_mystats(message, db_user)

    elif action == "subscribe":
        from src.bot.handlers.subscription.plans import cmd_subscribe
        await cmd_subscribe(message, db_user)

    elif action == "settings":
        from src.bot.handlers.user.start import cmd_settings
        await cmd_settings(message, db_user)

    elif action == "help":
        from src.bot.handlers.user.start import cmd_help
        await cmd_help(message, db_user)

    elif action == "admin":
        role = (db_user or {}).get("role", "user")
        if role in ("admin", "owner"):
            from src.bot.handlers.admin.dashboard import cmd_admin
            await cmd_admin(message, db_user)
        else:
            await safe_reply(message, "⚠️ Sizda admin huquqi yo'q.")
