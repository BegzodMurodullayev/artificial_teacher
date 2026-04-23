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
from aiogram import Bot

logger = logging.getLogger(__name__)
router = Router(name="menu_dispatch")


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

from aiogram import F
from src.bot.keyboards.user_menu import USER_MENU_ALIASES, resolve_menu_action, user_main_menu

def is_menu_action(message: Message) -> bool:
    """Return True if the message text matches any known menu alias."""
    if not message.text:
        return False
    action = resolve_menu_action(message.text)
    if action:
        logger.debug("is_menu_action: MATCHED %r -> %s", message.text, action)
        return True
    return False

@router.message(is_menu_action)
async def menu_button_handler(message: Message, db_user: dict | None = None):
    """Route menu button presses to the appropriate handler."""
    try:
        action = resolve_menu_action(message.text)
        logger.info("menu_button_handler TRIGGERED: text=%r action=%s user_id=%s", 
                    message.text, action, message.from_user.id if message.from_user else 0)
        
        if not db_user:
            logger.warning("menu_button_handler: db_user is None for user %s", message.from_user.id if message.from_user else 0)
            # Try to fetch user manually if middleware failed
            from src.database.dao.user_dao import upsert_user
            user = message.from_user
            if user:
                db_user = await upsert_user(user.id, user.username or "", user.first_name or "")
        
        if not db_user or not message.text:
            return

        bot = message.bot

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
            msg = await safe_reply(message, "⏳ <i>Kunlik so'z tayyorlanmoqda...</i>")
            if msg:
                from src.services import ai_service
                from src.bot.utils.telegram import safe_edit
                data = await ai_service.ask_json("Give me a daily word.", mode="daily_word", user_id=uid)
                if data:
                    text = (
                        f"📅 <b>Kunlik so'z</b>\n\n"
                        f"🔹 <b>{data.get('word', '').capitalize()}</b> ({data.get('part_of_speech', '')})\n"
                        f"🇺🇿 {data.get('uzbek', '')}\n\n"
                        f"📖 <i>{data.get('definition', '')}</i>\n"
                        f"💡 Misol: {data.get('example', '')}\n"
                        f"🔗 Sinonimlar: {', '.join(data.get('synonyms', []))}"
                    )
                else:
                    text = "❌ So'z tayyorlashda xatolik yuz berdi. Iltimos, qayta urinib ko'ring."
                await safe_edit(msg, text)
        elif txt == "🎁 Bonuslar":
            await safe_reply(message, "🎁 <b>Bonuslar</b>\n\nDo'stlaringizni taklif qiling va bonus ballarga ega bo'ling!")
        elif txt in ("🕵️ Mafiya", "🎮 Mafiya"):
            await safe_reply(message, "🕵️ <b>Mafiya O'yini</b>\n\nGuruhda o'ynash uchun botni guruhga qo'shing va <code>/mafia</code> deb yozing!")
        return

    # ── Route Navigation ─────────────────────────────────
    if action == "edu_menu":
        from src.bot.keyboards.user_menu import edu_menu
        await safe_reply(message, "🎓 <b>Ta'lim bo'limi</b>\nNima o'rganamiz?", reply_markup=edu_menu())
    elif action == "test_menu":
        from src.bot.keyboards.user_menu import test_menu
        await safe_reply(message, "🎯 <b>Sinovlar</b>\nSizni testlar kutmoqda!", reply_markup=test_menu())
    elif action == "games_menu":
        from src.bot.keyboards.user_menu import games_menu
        await safe_reply(message, "🎮 <b>O'yinlar</b>\nBo'sh vaqtingizni qiziqarli va foydali o'tkazing!", reply_markup=games_menu())
    elif action == "cabinet_menu":
        from src.bot.keyboards.user_menu import cabinet_menu
        await safe_reply(message, "👤 <b>Shaxsiy Kabinet</b>\nStatistikangiz va tariflar.", reply_markup=cabinet_menu())
    elif action == "extra_menu":
        from src.bot.keyboards.user_menu import extra_menu
        await safe_reply(message, "⚙️ <b>Qo'shimcha sozlamalar</b>", reply_markup=extra_menu())
    elif action == "main_menu":
        plan_name = await subscription_dao.get_active_plan_name(db_user["user_id"]) if db_user else "free"
        role = db_user.get("role", "user") if db_user else "user"
        await safe_reply(message, "🏠 <b>Bosh menyu</b>", reply_markup=user_main_menu(plan_name, role))

    # ── Route by action key ──────────────────────────────
    elif action == "check":
        from src.services.mode_manager import set_mode
        await set_mode(uid, "CORRECTION")
        await safe_reply(
            message,
            "✅ <b>Grammatika tekshiruv rejimi</b>\n\n"
            "Ingliz tilida matn yozing — men xatolarni topaman!\n\n"
            "💡 <i>Masalan: \"I goes to school yesterday\"</i>"
        )

    elif action == "translate":
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🇺🇿→🇬🇧 UZ→EN", callback_data="mode:uz_to_en"),
                InlineKeyboardButton(text="🇬🇧→🇺🇿 EN→UZ", callback_data="mode:en_to_uz"),
            ],
            [
                InlineKeyboardButton(text="🇷🇺→🇬🇧 RU→EN", callback_data="mode:ru_to_en"),
                InlineKeyboardButton(text="🇬🇧→🇷🇺 EN→RU", callback_data="mode:en_to_ru"),
            ]
        ])
        await safe_reply(message, "🌐 <b>Tarjima rejimi</b>\n\nYo'nalishni tanlang:", reply_markup=kb)

    elif action == "pronunciation":
        from src.services.mode_manager import set_mode
        await set_mode(uid, "PRONUNCIATION")
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
            msg = await safe_reply(message, "⏳ <i>Kunlik so'z tayyorlanmoqda...</i>")
            if not msg:
                return
            from src.services import ai_service
            from src.bot.utils.telegram import safe_edit
            data = await ai_service.ask_json("Give me a daily word.", mode="daily_word", user_id=uid)
            if data:
                text = (
                    f"📅 <b>Kunlik so'z</b>\n\n"
                    f"🔹 <b>{data.get('word', '').capitalize()}</b> ({data.get('part_of_speech', '')})\n"
                    f"🇺🇿 {data.get('uzbek', '')}\n\n"
                    f"📖 <i>{data.get('definition', '')}</i>\n"
                    f"💡 Misol: {data.get('example', '')}\n"
                    f"🔗 Sinonimlar: {', '.join(data.get('synonyms', []))}"
                )
            else:
                text = "❌ So'z tayyorlashda xatolik yuz berdi. Iltimos, qayta urinib ko'ring."
            await safe_edit(msg, text)

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
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
        from src.config import settings
        if settings.WEB_APP_URL:
            base = settings.WEB_APP_URL.rstrip('/')
            kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="📚 Kutubxonaga kirish", web_app=WebAppInfo(url=f"{base}/library?tab=book"))
            ]])
            await safe_reply(message, "📚 <b>Kutubxona</b>\n\nJahon adabiyoti, ingliz tili qoidalari va ko'proq!", reply_markup=kb)
        else:
            await safe_reply(message, "📚 <b>Kutubxona</b>\n\nJahon adabiyoti va qoidalar bo'limi (WebApp ulanmagan).")

    elif action == "evrika":
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
        from src.config import settings
        if settings.WEB_APP_URL:
            base = settings.WEB_APP_URL.rstrip('/')
            kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="💡 Faktlarni o'qish", web_app=WebAppInfo(url=f"{base}/library?tab=fact"))
            ]])
            await safe_reply(message, "💡 <b>Evrika!</b>\n\nQiziqarli kashfiyotlar va ilmiy faktlar bilan tanishing!", reply_markup=kb)
        else:
            await safe_reply(message, "💡 <b>Evrika!</b>\n\nQiziqarli faktlar bo'limi (WebApp ulanmagan).")

    elif action == "zakovat":
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
        from src.config import settings
        if settings.WEB_APP_URL:
            base = settings.WEB_APP_URL.rstrip('/')
            kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🧠 Zakovat savollari", web_app=WebAppInfo(url=f"{base}/library?tab=quiz"))
            ]])
            await safe_reply(message, "🧠 <b>Zakovat</b>\n\nMantiqiy va qiyin savollar olimpiadasiga xush kelibsiz!", reply_markup=kb)
        else:
            await safe_reply(message, "🧠 <b>Zakovat</b>\n\nMantiqiy savollar bo'limi (WebApp ulanmagan).")

    elif action == "iq_test":
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
        from src.config import settings
        # Check subscription
        plan = await subscription_dao.get_user_plan(db_user["user_id"]) if db_user else {}
        if not plan.get("iq_test_enabled"):
            await safe_reply(
                message,
                "🧩 <b>IQ Test</b> faqat <b>Pro</b> va <b>Premium</b> foydalanuvchilar uchun!\n\n"
                "Obunangizni yangilash: /subscribe"
            )
            return
        if settings.WEB_APP_URL:
            kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🧠 IQ Testni boshlash", web_app=WebAppInfo(url=f"{settings.WEB_APP_URL.rstrip('/')}/iqtest"))
            ]])
            await safe_reply(message, "🧠 <b>IQ Test</b>\n\nMantiqiy fikrlash darajangizni aniqlovchi va savollari tez-tez yangilanib turuvchi maxsus test! Test yakunida natijangiz statistikangizga saqlanadi.", reply_markup=kb)
        else:
            await safe_reply(message, "🎮 WebApp hozirda ulanmagan.")


    elif action == "pomodoro":
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
        from src.config import settings
        if settings.WEB_APP_URL:
            kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="⏱ Pomodoro taymerni ochish", web_app=WebAppInfo(url=f"{settings.WEB_APP_URL.rstrip('/')}/pomodoro"))
            ]])
            await safe_reply(message, "⏱ <b>Pomodoro Timer</b>\n\nDiqqatingizni jamlab o'qish yoki ishlash uchun maxsus taymer!\n\n100% tugatilgan fokus vaqti sizga XP taqdim etadi.", reply_markup=kb)
        else:
            await safe_reply(message, "🎮 WebApp hozirda ulanmagan.")

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
        from src.bot.handlers.game.mini_games_handler import cmd_raqam_top
        await cmd_raqam_top(message, bot)
        # await safe_reply(message, "🔢 <b>Raqam Topish</b>\n\nBoshlamoqmi? <code>/raqamtop</code> deb yozing!")

    elif action == "game_math":
        from src.bot.handlers.game.mini_games_handler import cmd_tez_hisob
        await cmd_tez_hisob(message, bot)
        # await safe_reply(message, "⚡ <b>Tez Hisob</b>\n\nBoshlamoqmi? <code>/tezhisob</code> deb yozing!")

    elif action == "game_word":
        from src.bot.handlers.game.word_games_handler import cmd_soz_topish
        await cmd_soz_topish(message, bot)
        # await safe_reply(message, "🔤 <b>So'z Topish</b>\n\nBoshlamoqmi? <code>/soztopish</code> deb yozing!")

    elif action == "game_translate":
        from src.bot.handlers.game.word_games_handler import cmd_tarjima_poyga
        await cmd_tarjima_poyga(message, bot)
        # await safe_reply(message, "🏃 <b>Tarjima Poygasi</b>\n\nBoshlamoqmi? <code>/tarjimapoyga</code> deb yozing!")

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
    except Exception as e:
        logger.exception("Error in menu_button_handler: %s", e)
        await safe_reply(message, "⚠️ Menyuda xatolik yuz berdi. Iltimos qayta urinib ko'ring.")
