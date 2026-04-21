"""
Menu dispatcher — handles reply keyboard button presses.
Maps button text to appropriate actions. Admin buttons are also routed here
as a safe fallback (admin router catches them first when role is correct).
"""

import logging

from aiogram import Router, F
from aiogram.types import Message

from src.bot.keyboards.user_menu import resolve_menu_action, user_main_menu
from src.bot.utils.telegram import safe_reply
from src.database.dao import subscription_dao

logger = logging.getLogger(__name__)
router = Router(name="menu_dispatch")


# ══════════════════════════════════════════════════════════
# CATEGORY NAVIGATION (Main Menu → Sub-Menu)
# ══════════════════════════════════════════════════════════

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
    plan_name = "free"
    if db_user:
        plan_name = await subscription_dao.get_active_plan_name(db_user["user_id"])
    role = db_user.get("role", "user") if db_user else "user"
    await safe_reply(message, "🏠 <b>Bosh menyu</b>", reply_markup=user_main_menu(plan_name, role))


# ══════════════════════════════════════════════════════════
# HELPER: admin role check with config fallback
# ══════════════════════════════════════════════════════════

def _is_admin(db_user: dict, user_id: int) -> bool:
    role = (db_user or {}).get("role", "user")
    if role in ("admin", "owner"):
        return True
    try:
        from src.config import settings
        admin_ids = [int(i.strip()) for i in settings.ADMIN_IDS.split(",") if i.strip().isdigit()]
        return user_id == settings.OWNER_ID or user_id in admin_ids
    except Exception:
        return False


# ══════════════════════════════════════════════════════════
# MAIN MENU BUTTON DISPATCHER
# ══════════════════════════════════════════════════════════

@router.message(F.text.in_([
    # ── Education ────────────────────────
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
    "📅 Kunlik so'z", "🎁 Bonuslar",
    "📚 Kutubxona", "💡 Evrika",
    "🧠 Zakovat", "🔢 Raqam Topish",
    "⚡ Tez Hisob", "🕵️ Mafiya", "🎮 Mafiya",
    "🔤 So'z Topish", "🏃 Tarjima Poygasi",
    "🕹️ WebApp O'yinlar", "🕹️ Katta O'yinlar (WebApp)",
    "❌ X-O (Tic-Tac)", "🃏 Xotira", "🧩 Sudoku",
    # ── Admin Panel buttons (safety fallback) ────
    "💳 To'lovlar", "👥 Foydalanuvchilar",
    "📢 Broadcast", "📈 Statistika",
    "⚙️ Rejalar", "🏆 Reyting",
]))
async def menu_button_handler(message: Message, db_user: dict | None = None):
    """Route menu button presses to the appropriate handler."""
    if not db_user or not message.text:
        return

    action = resolve_menu_action(message.text)
    uid = message.from_user.id if message.from_user else 0

    # ── Admin panel buttons ──────────────────────────────
    ADMIN_ACTIONS = {
        "adm_payments", "adm_users", "adm_broadcast",
        "adm_stats", "adm_plans", "adm_leaderboard"
    }
    if action in ADMIN_ACTIONS:
        if _is_admin(db_user, uid):
            from src.bot.handlers.admin import dashboard as adm
            handler_map = {
                "adm_payments":    adm._btn_adm_payments,
                "adm_users":       adm._btn_adm_users,
                "adm_broadcast":   adm._btn_adm_broadcast,
                "adm_stats":       adm._btn_adm_stats,
                "adm_plans":       adm._btn_adm_plans,
                "adm_leaderboard": adm._btn_adm_leaderboard,
            }
            fn = handler_map.get(action)
            if fn:
                await fn(message, db_user)
        else:
            await safe_reply(message, "⚠️ Sizda admin huquqi yo'q.")
        return

    # ── Direct text matches not in aliases ───────────────
    if not action:
        txt = message.text
        if txt == "🧠 IQ Test":
            await safe_reply(message, "🧠 <b>IQ Test</b>\n\nMantiqiy fikrlash darajangizni aniqlaydigan testlar. (Tez kunda...)")
        elif txt == "📅 Kunlik so'z":
            await safe_reply(message, "📅 <b>Kunlik so'z</b>\n\nBugungi so'z: <b>Enhance</b> — Yaxshilamoq\n<i>Misol: Reading helps to enhance your vocabulary.</i>")
        elif txt == "🎁 Bonuslar":
            await safe_reply(message, "🎁 <b>Bonuslar</b>\n\nDo'stlaringizni taklif qiling va bonus ballarga ega bo'ling!")
        elif txt in ("🕵️ Mafiya", "🎮 Mafiya"):
            await safe_reply(message, "🕵️ <b>Mafiya O'yini</b>\n\nGuruhda o'ynash uchun botni guruhga qo'shing va <code>/mafia</code> deb yozing!")
        return

    # ── Route by action key ──────────────────────────────
    if action == "check":
        await safe_reply(
            message,
            "✅ <b>Grammatika tekshiruv rejimi</b>\n\n"
            "Ingliz tilida matn yozing — men xatolarni topaman!\n\n"
            "💡 <i>Masalan: \"I goes to school yesterday\"</i>"
        )

    elif action == "translate":
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🇺🇿→🇬🇧 UZ→EN", callback_data="tr_mode:uz_to_en"),
            InlineKeyboardButton(text="🇬🇧→🇺🇿 EN→UZ", callback_data="tr_mode:en_to_uz"),
        ]])
        await safe_reply(message, "🌐 <b>Tarjima rejimi</b>\n\nYo'nalishni tanlang:", reply_markup=kb)

    elif action == "pronunciation":
        await safe_reply(
            message,
            "🔊 <b>Talaffuz rejimi</b>\n\n"
            "Ingliz tilidagi so'z yoki ibora yuboring.\n"
            "Men IPA transkripsiyasi va audio bilan javob beraman.\n\n"
            "💡 <i>Masalan: \"pronunciation\"</i>"
        )

    elif action == "quiz":
        from src.bot.handlers.quiz.quiz_start import cmd_quiz
        await cmd_quiz(message, db_user)

    elif action == "lessons":
        from src.bot.keyboards.user_menu import lesson_topics_keyboard
        await safe_reply(message, "📚 <b>Darslar</b>\n\nMavzuni tanlang:", reply_markup=lesson_topics_keyboard())

    elif action == "grammar":
        from src.bot.keyboards.user_menu import grammar_rules_keyboard
        await safe_reply(message, "📖 <b>Grammatika qoidalari</b>\n\nMavzuni tanlang:", reply_markup=grammar_rules_keyboard())

    elif action in ("stats", "daily_word"):
        if action == "stats":
            from src.bot.handlers.user.profile import cmd_mystats
            await cmd_mystats(message, db_user)
        else:
            await safe_reply(message, "📅 <b>Kunlik so'z</b>\n\nBugungi so'z: <b>Enhance</b> — Yaxshilamoq\n<i>Misol: Reading helps to enhance your vocabulary.</i>")

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
        if _is_admin(db_user, uid):
            from src.bot.handlers.admin.dashboard import cmd_admin
            await cmd_admin(message, db_user)
        else:
            await safe_reply(message, "⚠️ Sizda admin huquqi yo'q.")

    elif action == "library":
        await safe_reply(message, "📚 <b>Kutubxona</b>\n\nAsarlar va maqolalar tez kunda WebApp orqali taqdim etiladi!")

    elif action == "evrika":
        await safe_reply(message, "💡 <b>Evrika!</b>\n\nQiziqarli faktlar ustida ishlayapmiz.")

    elif action == "zakovat":
        await safe_reply(message, "🧠 <b>Zakovat</b>\n\nMantiqiy savollar olimpiadasiga tayyor bo'ling! (Tez kunda)")

    elif action == "iq_test":
        await safe_reply(message, "🧠 <b>IQ Test</b>\n\nMantiqiy fikrlash testi. (Tez kunda)")

    elif action == "bonuses":
        await safe_reply(message, "🎁 <b>Bonuslar</b>\n\nDo'stlaringizni taklif qiling va bonus ballarga ega bo'ling!")

    elif action == "game_mafia":
        await safe_reply(message, "🕵️ <b>Mafiya O'yini</b>\n\nBotni guruhga qo'shing va <code>/mafia</code> deb yozing!")

    elif action == "game_xo":
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
        from src.config import settings
        if settings.WEB_APP_URL:
            kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🕹️ X-O o'ynash", web_app=WebAppInfo(url=f"{settings.WEB_APP_URL.rstrip('/')}/games/xo"))
            ]])
            await safe_reply(message, "❌ <b>X-O (Krestiki-Noliki)</b>\n\nAI yoki do'stingizga qarshi WebApp'da o'ynang!", reply_markup=kb)
        else:
            await safe_reply(message, "🎮 WebApp ulanmagan.")

    elif action == "game_memory":
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
        from src.config import settings
        if settings.WEB_APP_URL:
            kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🕹️ Xotira o'yini", web_app=WebAppInfo(url=f"{settings.WEB_APP_URL.rstrip('/')}/games/memory"))
            ]])
            await safe_reply(message, "🃏 <b>Xotira O'yini</b>\n\nJuftliklarni toping va xotirangizni sinang!", reply_markup=kb)
        else:
            await safe_reply(message, "🎮 WebApp ulanmagan.")

    elif action == "game_sudoku":
        await safe_reply(message, "🧩 <b>Sudoku</b>\n\nTez kunda WebApp'ga qo'shiladi!")

    elif action == "game_number":
        await safe_reply(message, "🔢 <b>Raqam Topish</b>\n\nBoshlamoqmi? <code>/raqamtop</code> deb yozing!")

    elif action == "game_math":
        await safe_reply(message, "⚡ <b>Tez Hisob</b>\n\nBoshlamoqmi? <code>/tezhisob</code> deb yozing!")

    elif action == "game_word":
        await safe_reply(message, "🔤 <b>So'z Topish</b>\n\nBoshlamoqmi? <code>/soztopish</code> deb yozing!")

    elif action == "game_translate":
        await safe_reply(message, "🏃 <b>Tarjima Poygasi</b>\n\nBoshlamoqmi? <code>/tarjimapoyga</code> deb yozing!")

    elif action == "game_webapp":
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
        from src.config import settings
        if settings.WEB_APP_URL:
            kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🕹️ WebApp orqali o'ynash", web_app=WebAppInfo(url=f"{settings.WEB_APP_URL.rstrip('/')}/games"))
            ]])
            await safe_reply(message, "🎮 <b>Katta O'yinlar (WebApp)</b>\n\nX-O, Xotira, Sudoku va boshqa o'yinlar markazi!", reply_markup=kb)
        else:
            await safe_reply(message, "🎮 WebApp hozirda ulanmagan.")
