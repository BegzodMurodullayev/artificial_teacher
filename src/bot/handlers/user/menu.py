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


@router.message(F.text == "🎓 Ta'lim")
async def _cat_edu(message: Message, db_user: dict | None = None):
    from src.bot.keyboards.user_menu import edu_menu
    await safe_reply(message, "🎓 <b>Ta'lim bo'limi</b>\nNima o'rganamiz?", reply_markup=edu_menu())

@router.message(F.text == "🎯 Sinovlar")
async def _cat_test(message: Message, db_user: dict | None = None):
    from src.bot.keyboards.user_menu import test_menu
    await safe_reply(message, "🎯 <b>Sinovlar</b>\nSizni testlar kutmoqda!", reply_markup=test_menu())

@router.message(F.text == "🎮 Guruh O'yinlari")
async def _cat_games(message: Message, db_user: dict | None = None):
    from src.bot.keyboards.user_menu import games_menu
    await safe_reply(message, "🎮 <b>Guruh O'yinlari</b>\nDo'stlar bilan qiziqarli vaqt o'tkazing!", reply_markup=games_menu())

@router.message(F.text == "👤 Kabinetim")
async def _cat_cabinet(message: Message, db_user: dict | None = None):
    from src.bot.keyboards.user_menu import cabinet_menu
    await safe_reply(message, "👤 <b>Shaxsiy Kabinet</b>\nStatistikangiz va tariflar.", reply_markup=cabinet_menu())

@router.message(F.text == "⚙️ Qo'shimcha")
async def _cat_extra(message: Message, db_user: dict | None = None):
    from src.bot.keyboards.user_menu import extra_menu
    await safe_reply(message, "⚙️ <b>Qo'shimcha sozlamalar</b>", reply_markup=extra_menu())

@router.message(F.text == "🔙 Asosiy Menyu")
async def _cat_back(message: Message, db_user: dict | None = None):
    from src.bot.keyboards.user_menu import user_main_menu
    from src.database.dao import subscription_dao
    plan_name = "free"
    if db_user:
        plan_name = await subscription_dao.get_active_plan_name(db_user["user_id"])
    role = db_user.get("role", "user") if db_user else "user"
    await safe_reply(message, "🏠 <b>Bosh menyu</b>", reply_markup=user_main_menu(plan_name, role))


@router.message(F.text.in_([
    "✅ Tekshirish", "✅ Check",
    "🌐 Tarjima", "🌐 Translate",
    "🔊 Talaffuz", "🔊 Pronunciation",
    "🧠 Quiz", "🧠 IQ Test",
    "📚 Darslar", "📚 Lessons",
    "📖 Grammatika", "📖 Grammar",
    "📈 Darajam", "📊 Statistika",
    "⭐ Obuna", "⭐ Subscribe",
    "⚙️ Sozlamalar", "⚙️ Settings",
    "ℹ️ Aloqa", "ℹ️ Yordam",
    "🛡 Admin Panel",
    "📅 Kunlik so'z", "🎁 Bonuslar"
]))
async def menu_button_handler(message: Message, db_user: dict | None = None):
    """Route menu button presses to the appropriate handler."""
    if not db_user or not message.text:
        return

    from src.bot.keyboards.user_menu import resolve_menu_action
    action = resolve_menu_action(message.text)
    
    # Check for direct matches if not in aliases
    if not action:
        if message.text == "🧠 IQ Test":
            await safe_reply(message, "🧠 <b>IQ Test</b>\n\nSizning mantiqiy fikrlash darajangizni aniqlaydigan testlar. (Tez kunda...)")
            return
        if message.text == "📅 Kunlik so'z":
            await safe_reply(message, "📅 <b>Kunlik so'z</b>\n\nBugungi so'z: <b>Enhance</b> - Yaxshilamoq\n<i>Misol: Reading helps to enhance your vocabulary.</i>")
            return
        if message.text == "🎁 Bonuslar":
            await safe_reply(message, "🎁 <b>Bonuslar</b>\n\nDo'stlaringizni taklif qiling va bonus ballarga ega bo'ling! (Link tayyorlanmoqda...)")
            return
        if message.text == "🕵️ Mafiya" or message.text == "🎮 Mafiya":
            await safe_reply(message, "🕵️ <b>Mafiya O'yini</b>\n\nGuruhda o'ynash uchun botni guruhga qo'shing va <code>/mafia</code> buyrug'ini yozing!")
            return
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
