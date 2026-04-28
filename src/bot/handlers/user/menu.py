"""
Reply-keyboard menu dispatcher.
Routes button presses to the right user/admin handlers.
"""

import logging

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo

from src.bot.keyboards.user_menu import (
    PLAN_LABELS,
    USER_MENU_ALIASES,
    edu_menu,
    extra_menu,
    games_menu,
    grammar_rules_keyboard,
    lesson_topics_keyboard,
    normalize_plan_name,
    resolve_menu_action,
    resolve_materials_launch,
    resolve_webapp_url,
    test_menu,
    user_main_menu,
    cabinet_menu,
)
from src.bot.utils.telegram import safe_edit, safe_reply
from src.database.dao import subscription_dao

logger = logging.getLogger(__name__)
router = Router(name="menu_dispatch")


def _plan_display_name(plan_name: str) -> str:
    return PLAN_LABELS.get(normalize_plan_name(plan_name), "Free")


def _is_admin(db_user: dict | None, user_id: int) -> bool:
    role = (db_user or {}).get("role", "user")
    if role in ("admin", "owner"):
        return True
    try:
        from src.config import settings

        admin_ids = [
            int(item.strip())
            for item in settings.ADMIN_IDS.split(",")
            if item.strip().isdigit()
        ]
        return user_id == settings.OWNER_ID or user_id in admin_ids
    except Exception:
        return False


def is_menu_action(message: Message) -> bool:
    if not message.text:
        return False
    action = resolve_menu_action(message.text)
    if action:
        logger.debug("Menu action matched: %r -> %s", message.text, action)
        return True
    return False


async def _ensure_db_user(message: Message, db_user: dict | None) -> dict | None:
    if db_user:
        return db_user
    user = message.from_user
    if not user:
        return None
    from src.database.dao.user_dao import upsert_user

    return await upsert_user(user.id, user.username or "", user.first_name or "")


async def _send_daily_word(message: Message, user_id: int) -> None:
    from src.services import ai_service

    placeholder = await safe_reply(message, "⏳ <i>Kunlik so'z tayyorlanmoqda...</i>")
    if not placeholder:
        return

    data = await ai_service.ask_json("Give me a daily word.", mode="daily_word", user_id=user_id)
    if data:
        text = (
            "🗓 <b>Kunlik so'z</b>\n\n"
            f"🔹 <b>{data.get('word', '').capitalize()}</b> ({data.get('part_of_speech', '')})\n"
            f"🇺🇿 {data.get('uzbek', '')}\n\n"
            f"📖 <i>{data.get('definition', '')}</i>\n"
            f"💡 Misol: {data.get('example', '')}\n"
            f"🔗 Sinonimlar: {', '.join(data.get('synonyms', []))}"
        )
    else:
        text = "❌ So'z tayyorlashda xatolik yuz berdi. Iltimos, qayta urinib ko'ring."

    await safe_edit(placeholder, text)


async def _send_webapp_entry(
    message: Message,
    title: str,
    body: str,
    path: str,
    button_text: str,
    plan_name: str = "free",
) -> None:
    web_app_url = resolve_webapp_url(plan_name)
    if not web_app_url:
        await safe_reply(message, "⚠️ WebApp hozircha ulanmagan.")
        return

    base = web_app_url.rstrip("/")
    route = path if path.startswith("/") else f"/{path}"
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=button_text, web_app=WebAppInfo(url=f"{base}{route}"))]
        ]
    )
    await safe_reply(message, f"{title}\n\n{body}", reply_markup=keyboard)


async def _send_materials_entry(message: Message, plan_name: str = "free") -> None:
    materials_url, resolved_plan = resolve_materials_launch(plan_name)
    if not materials_url:
        await _send_webapp_entry(
            message,
            "🧩 <b>Materiallar</b>",
            "Qo'shimcha material sahifalari hali ulanmagan. Hozircha kutubxona bo'limi ochiladi.",
            "/library?tab=book",
            "📚 Kutubxonaga kirish",
            plan_name=plan_name,
        )
        return

    current_label = _plan_display_name(plan_name)
    resolved_label = _plan_display_name(resolved_plan)
    note = f"Joriy tarif: <b>{current_label}</b>."
    if resolved_plan != normalize_plan_name(plan_name):
        note += (
            f"\n\nℹ️ {current_label} uchun alohida material linki hali kiritilmagan. "
            f"Vaqtincha <b>{resolved_label}</b> pack ochiladi."
        )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🧩 Materiallarni ochish", web_app=WebAppInfo(url=materials_url))]
        ]
    )
    await safe_reply(
        message,
        "🧩 <b>Qo'shimcha Materiallar</b>\n\n"
        "Tarifingizga mos prezentatsiyalar, mashqlar va tayyor lesson packlar shu yerda.\n\n"
        f"{note}",
        reply_markup=keyboard,
    )


@router.message(is_menu_action)
async def menu_button_handler(message: Message, db_user: dict | None = None, state: FSMContext | None = None):
    try:
        db_user = await _ensure_db_user(message, db_user)
        if not db_user or not message.text or not message.from_user:
            return

        action = resolve_menu_action(message.text)
        if not action:
            return

        uid = message.from_user.id
        plan_name = await subscription_dao.get_active_plan_name(db_user["user_id"])
        bot = message.bot

        admin_actions = {
            "adm_payments",
            "adm_users",
            "adm_broadcast",
            "adm_stats",
            "adm_plans",
            "adm_leaderboard",
            "adm_admins",
            "adm_payment_settings",
            "adm_sponsors",
        }
        if action in admin_actions:
            if not _is_admin(db_user, uid):
                await safe_reply(message, "⚠️ Sizda admin huquqi yo'q.")
                return

            from src.bot.handlers.admin import dashboard as admin_dashboard
            from src.bot.handlers.admin import management as admin_management

            handler_map = {
                "adm_payments": admin_dashboard._btn_adm_payments,
                "adm_users": admin_dashboard._btn_adm_users,
                "adm_stats": admin_dashboard._btn_adm_stats,
                "adm_plans": admin_dashboard._btn_adm_plans,
                "adm_leaderboard": admin_dashboard._btn_adm_leaderboard,
                "adm_admins": admin_management._btn_adm_admins,
                "adm_payment_settings": admin_management._btn_adm_payment_settings,
                "adm_sponsors": admin_management._btn_adm_sponsors,
            }
            if action == "adm_broadcast":
                await admin_dashboard._btn_adm_broadcast(message, db_user, state)
            else:
                await handler_map[action](message, db_user)
            return

        if action == "edu_menu":
            await safe_reply(message, "🎓 <b>Ta'lim bo'limi</b>\nNima o'rganamiz?", reply_markup=edu_menu())
            return

        if action == "test_menu":
            await safe_reply(message, "🎯 <b>Sinovlar</b>\nSizni testlar kutmoqda!", reply_markup=test_menu())
            return

        if action == "games_menu":
            await safe_reply(
                message,
                "🎮 <b>O'yinlar</b>\nBo'sh vaqtingizni qiziqarli va foydali o'tkazing!",
                reply_markup=games_menu(),
            )
            return

        if action == "cabinet_menu":
            await safe_reply(
                message,
                "👤 <b>Shaxsiy kabinet</b>\nStatistikangiz, tariflar va bonuslar shu yerda.",
                reply_markup=cabinet_menu(),
            )
            return

        if action == "extra_menu":
            await safe_reply(message, "⚙️ <b>Qo'shimcha bo'lim</b>", reply_markup=extra_menu())
            return

        if action == "main_menu":
            await safe_reply(
                message,
                "🏠 <b>Bosh menyu</b>",
                reply_markup=user_main_menu(plan_name, db_user.get("role", "user")),
            )
            return

        if action == "check":
            from src.services.mode_manager import set_mode

            await set_mode(uid, "CORRECTION")
            await safe_reply(
                message,
                "✅ <b>Grammatika tekshiruv rejimi</b>\n\n"
                "Ingliz tilida matn yozing — men xatolarni topaman va tushuntiraman.\n\n"
                "💡 <i>Masalan: I goes to school yesterday</i>",
            )
            return

        if action == "translate":
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(text="🇺🇿→🇬🇧 UZ→EN", callback_data="mode:uz_to_en"),
                        InlineKeyboardButton(text="🇬🇧→🇺🇿 EN→UZ", callback_data="mode:en_to_uz"),
                    ],
                    [
                        InlineKeyboardButton(text="🇷🇺→🇬🇧 RU→EN", callback_data="mode:ru_to_en"),
                        InlineKeyboardButton(text="🇬🇧→🇷🇺 EN→RU", callback_data="mode:en_to_ru"),
                    ],
                ]
            )
            await safe_reply(message, "🌐 <b>Tarjima rejimi</b>\n\nYo'nalishni tanlang:", reply_markup=keyboard)
            return

        if action == "pronunciation":
            from src.services.mode_manager import set_mode

            await set_mode(uid, "PRONUNCIATION")
            await safe_reply(
                message,
                "🔊 <b>Talaffuz rejimi</b>\n\n"
                "Ingliz tilidagi so'z yoki ibora yuboring.\n"
                "Men IPA transkripsiyasi va audio bilan javob beraman.\n\n"
                "💡 <i>Masalan: pronunciation</i>",
            )
            return

        if action == "quiz":
            from src.bot.handlers.quiz.quiz_start import cmd_quiz

            await cmd_quiz(message, db_user)
            return

        if action == "lessons":
            await safe_reply(message, "📚 <b>Darslar</b>\n\nMavzuni tanlang:", reply_markup=lesson_topics_keyboard())
            return

        if action == "grammar":
            await safe_reply(
                message,
                "📖 <b>Grammatika qoidalari</b>\n\nMavzuni tanlang:",
                reply_markup=grammar_rules_keyboard(),
            )
            return

        if action == "stats":
            from src.bot.handlers.user.profile import cmd_mystats

            await cmd_mystats(message, db_user)
            return

        if action == "daily_word":
            await _send_daily_word(message, uid)
            return

        if action == "materials":
            await _send_materials_entry(message, plan_name=plan_name)
            return

        if action == "subscribe":
            from src.bot.handlers.subscription.plans import cmd_subscribe

            await cmd_subscribe(message, db_user)
            return

        if action == "settings":
            from src.bot.handlers.user.start import cmd_settings

            await cmd_settings(message, db_user)
            return

        if action == "help":
            from src.bot.handlers.user.start import cmd_help

            await cmd_help(message, db_user)
            return

        if action == "admin":
            if _is_admin(db_user, uid):
                from src.bot.handlers.admin.dashboard import cmd_admin

                await cmd_admin(message, db_user)
            else:
                await safe_reply(message, "⚠️ Sizda admin huquqi yo'q.")
            return

        if action == "library":
            await _send_webapp_entry(
                message,
                "📚 <b>Kutubxona</b>",
                "Jahon adabiyoti, qo'llanmalar va keng materiallar bazasi.",
                "/library?tab=book",
                "📚 Kutubxonaga kirish",
                plan_name=plan_name,
            )
            return

        if action == "evrika":
            await _send_webapp_entry(
                message,
                "💡 <b>Evrika</b>",
                "Qiziqarli ilmiy faktlar va foydali bilimlar bo'limi.",
                "/library?tab=fact",
                "💡 Faktlarni ochish",
                plan_name=plan_name,
            )
            return

        if action == "zakovat":
            await _send_webapp_entry(
                message,
                "🧠 <b>Zakovat</b>",
                "Mantiqiy savollar, mini challenge va javobli materiallar shu yerda.",
                "/library?tab=quiz",
                "🧠 Zakovatga o'tish",
                plan_name=plan_name,
            )
            return

        if action == "iq_test":
            plan = await subscription_dao.get_user_plan(db_user["user_id"])
            if not plan.get("iq_test_enabled"):
                await safe_reply(
                    message,
                    "🧩 <b>IQ Test</b> faqat <b>Pro</b> va <b>Premium</b> foydalanuvchilar uchun.\n\n"
                    "Obunangizni yangilash uchun /subscribe ni bosing.",
                )
                return
            await _send_webapp_entry(
                message,
                "🧠 <b>IQ Test</b>",
                "Mantiqiy fikrlash darajangizni tekshiruvchi maxsus test.",
                "/iqtest",
                "🧠 IQ Testni boshlash",
                plan_name=plan_name,
            )
            return

        if action == "pomodoro":
            await _send_webapp_entry(
                message,
                "⏱ <b>Pomodoro Timer</b>",
                "Diqqatni jamlash va fokus bloklarini yig'ish uchun taymer.",
                "/pomodoro",
                "⏱ Pomodoro taymerni ochish",
                plan_name=plan_name,
            )
            return

        if action == "bonuses":
            from src.bot.handlers.user.profile import send_bonus_panel

            await send_bonus_panel(message, db_user)
            return

        if action == "game_mafia":
            await safe_reply(
                message,
                "🕵️ <b>Mafiya o'yini</b>\n\n"
                "Bu o'yin <b>guruhda</b> ishlaydi.\n\n"
                "📌 <b>Qadamlar:</b>\n"
                "1. Botni guruhga qo'shing\n"
                "2. Guruhda <code>/mafia</code> yozing\n"
                "3. Do'stlaringiz <b>🎮 Qo'shilish</b> tugmasini bossin\n"
                "4. Kamida 4 kishi to'lganda <b>🚀 Boshlash</b>ni bosing\n\n"
                "📋 <b>Rollar:</b>\n"
                "🔪 Mafiya — kechasi qurbon tanlaydi\n"
                "💊 Doktor — kechasi birini himoya qiladi\n"
                "🔍 Detektiv — kechasi birini tekshiradi\n"
                "👤 Fuqaro — kunduzi mafiyani ovoz bilan topadi\n\n"
                "⏱ Kecha: 90s | Kunduz: 120s\n"
                "👥 Min: 4 | Max: 12 o'yinchi\n\n"
                "<i>O'yinni to'xtatish uchun guruhda /stopm yozing.</i>",
            )
            return

        if action == "game_xo":
            await _send_webapp_entry(
                message,
                "❌ <b>X-O</b>",
                "AI yoki do'stingizga qarshi X-O o'ynang.",
                "/games/xo",
                "❌ X-O o'ynash",
                plan_name=plan_name,
            )
            return

        if action == "game_memory":
            await _send_webapp_entry(
                message,
                "🃏 <b>Xotira o'yini</b>",
                "Juftliklarni toping va xotirangizni mustahkamlang.",
                "/games/memory",
                "🃏 Xotira o'yinini ochish",
                plan_name=plan_name,
            )
            return

        if action == "game_sudoku":
            await safe_reply(message, "🧩 <b>Sudoku</b>\n\nSudoku WebApp bo'limida tez orada yanada boyitiladi.")
            return

        if action == "game_number":
            from src.bot.handlers.game.mini_games_handler import cmd_raqam_top

            await cmd_raqam_top(message, bot)
            return

        if action == "game_math":
            from src.bot.handlers.game.mini_games_handler import cmd_tez_hisob

            await cmd_tez_hisob(message, bot)
            return

        if action == "game_word":
            from src.bot.handlers.game.word_games_handler import cmd_soz_topish

            await cmd_soz_topish(message, bot)
            return

        if action == "game_translate":
            from src.bot.handlers.game.word_games_handler import cmd_tarjima_poyga

            await cmd_tarjima_poyga(message, bot)
            return

        if action == "game_error":
            from src.bot.handlers.game.group_games_handler import cmd_xato_topish

            await cmd_xato_topish(message, bot)
            return

        if action == "game_webapp":
            await _send_webapp_entry(
                message,
                "🎮 <b>Katta o'yinlar</b>",
                "WebApp ichida X-O, xotira, sudoku va boshqa o'yinlar markazi.",
                "/games",
                "🕹️ O'yinlar markazini ochish",
                plan_name=plan_name,
            )
            return

        fallback_aliases = USER_MENU_ALIASES.get(action, [])
        if fallback_aliases:
            await safe_reply(message, "⚠️ Bu tugma hali qayta ishlanmagan. Iltimos, boshqa bo'limni tanlang.")

    except Exception as exc:
        logger.exception("Error in menu_button_handler: %s", exc)
        await safe_reply(message, "⚠️ Menyuda xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")
