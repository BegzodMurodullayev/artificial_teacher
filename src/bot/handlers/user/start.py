"""
Start handler — /start command, welcome flow, main menu dispatch.
"""

import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo

from src.bot.keyboards.user_menu import (
    level_picker_keyboard, mode_picker_keyboard,
    normalize_plan_name,
    PLAN_LABELS,
    resolve_materials_launch,
    resolve_menu_action,
    user_main_menu,
)
from src.bot.utils.telegram import safe_reply, safe_edit, safe_answer_callback, escape_html
from src.database.dao import user_dao, subscription_dao, stats_dao, reward_dao

logger = logging.getLogger(__name__)
router = Router(name="user_start")


def _plan_display_name(plan_name: str) -> str:
    return PLAN_LABELS.get(normalize_plan_name(plan_name), "Free")


async def _send_materials_panel(message: Message, plan_name: str) -> None:
    materials_url, resolved_plan = resolve_materials_launch(plan_name)
    if not materials_url:
        await safe_reply(
            message,
            "⚠️ Qo'shimcha material sahifalari hali ulanmagan.\n\n"
            "Netlify linklarini `MATERIALS_URL*` env orqali kiriting.",
        )
        return

    current_label = _plan_display_name(plan_name)
    resolved_label = _plan_display_name(resolved_plan)
    note = f"Joriy tarif: <b>{current_label}</b>."
    if resolved_plan != normalize_plan_name(plan_name):
        note += (
            f"\n\nℹ️ {current_label} material linki hali alohida ulanmagan. "
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
        "Tarifingizga mos prezentatsiyalar, practice pack va lesson markazi shu yerda.\n\n"
        f"{note}",
        reply_markup=keyboard,
    )


@router.message(CommandStart())
async def cmd_start(message: Message, db_user: dict | None = None):
    """Handle /start command — welcome + referral + main menu."""
    user = message.from_user
    user_id = user.id

    # Handle referral deep link: /start ref_XXXXXX
    if message.text and " " in message.text:
        param = message.text.split(" ", 1)[1].strip()
        if param.startswith("ref_"):
            ref_code = param[4:]
            referrer = await reward_dao.find_by_referral_code(ref_code)
            if referrer and referrer["user_id"] != user_id:
                await reward_dao.set_referred_by(user_id, referrer["user_id"])
                # Award referral points (configurable)
                await reward_dao.add_points(referrer["user_id"], 25)
                logger.info("Referral: %s referred by %s (code: %s)",
                           user_id, referrer["user_id"], ref_code)

    # Get user's plan for menu customization
    plan_name = await subscription_dao.get_active_plan_name(user_id)
    stats = await stats_dao.get_stats(user_id)

    # Greet with @username if available, else first_name
    if user.username:
        name = escape_html(f"@{user.username}")
    else:
        name = escape_html(user.first_name or "Student")

    welcome = (
        f"👋 <b>Assalomu alaykum, {name}!</b>\n\n"
        "Men <b>Artificial Teacher</b> — sun'iy intellektga asoslangan shaxsiy ingliz tili o'qituvchingizman! 🤖🇬🇧\n\n"
        "✨ <b>Nimalarga qodirman?</b>\n"
        "• ✅ <b>Grammatika</b> — Ingliz tilida matn yozing, men xatolarni to'g'rilab, tushuntirib beraman!\n"
        "• 🌐 <b>Tarjimon</b> — O'zbekcha-Inglizcha erkin ta'limiy tarjima.\n"
        "• 🔊 <b>Talaffuz</b> — So'zning to'g'ri o'qilishini (audio bilan) tashlab beraman.\n"
        "• 🧠 <b>Quiz testi</b> — Ingliz tilidan bilimingizni bellashuv orqali sinang!\n"
        "• 🎮 <b>O'yinlar (Mafiya)</b> — Guruhda do'stlaringiz bilan qiziqarli o'yinlar (/mafia).\n"
        "• 📚 <b>Darslar</b> — Men orqali xohlagan qoida va mavzularingizni yodlang.\n"
        "• 🧩 <b>Materiallar</b> — Tarifingizga mos qo'shimcha prezentatsiya va practice packlarni oching.\n\n"
        "💡 <i>Menga shunchaki o'zbek yoki ingliz tilida matn (yoki ovozli xabar) yuboring! O'rganishni hoziroq boshlaymiz!</i>\n"
        "Barcha menyular pastki tugmalarda joylashgan 👇"
    )

    role = db_user.get("role", "user") if db_user else "user"
    await safe_reply(message, welcome, reply_markup=user_main_menu(plan_name, role=role))


@router.message(Command("help"))
async def cmd_help(message: Message, db_user: dict | None = None):
    """Handle /help command."""
    help_text = (
        "ℹ️ <b>Yordam</b>\n\n"
        "<b>Buyruqlar:</b>\n"
        "/start — Asosiy menyu\n"
        "/materials — Qo'shimcha materiallar\n"
        "/quiz — Quiz boshlash\n"
        "/iqtest — IQ test\n"
        "/mystats — Statistikangiz\n"
        "/clear — Suhbat tarixini tozalash\n"
        "/settings — Sozlamalar\n\n"
        "<b>Guruh buyruqlari:</b>\n"
        "#check — Grammatikani tekshirish\n"
        "#t — Tarjima\n"
        "#p — Talaffuz\n"
        "#bot — AI suhbat\n"
        "/mafia — Mafiya o'yinini boshlash (guruhda)\n"
        "/stopm — Mafiya o'yinini to'xtatish (guruhda)\n\n"
        "<b>Inline rejim:</b>\n"
        "@bot check: text\n"
        "@bot tr: text\n"
        "@bot p: us: word"
    )
    await safe_reply(message, help_text)


@router.message(F.text == "🎁 Bonuslar")
async def btn_bonus(message: Message, db_user: dict | None = None):
    """Open referral and bonus panel from reply keyboard."""
    if not db_user:
        return
    from src.bot.handlers.user.profile import send_bonus_panel
    await send_bonus_panel(message, db_user)


@router.message(Command("materials"))
async def cmd_materials(message: Message, db_user: dict | None = None):
    """Open hosted materials page based on the user's active plan."""
    plan_name = await subscription_dao.get_active_plan_name(db_user["user_id"]) if db_user else "free"
    await _send_materials_panel(message, plan_name)


@router.message(Command("library"))
async def cmd_library(message: Message, db_user: dict | None = None):
    """Handle /library command to open the Library WebApp."""
    from src.bot.keyboards.user_menu import resolve_webapp_url

    plan_name = await subscription_dao.get_active_plan_name(db_user["user_id"]) if db_user else "free"
    web_app_url = resolve_webapp_url(plan_name)
    if web_app_url:
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="📚 Kutubxonaga kirish", web_app=WebAppInfo(url=f"{web_app_url.rstrip('/')}/library"))
        ]])
        await safe_reply(message, "📚 <b>Kutubxona</b>\n\nJahon adabiyoti, faktlar va zakovat savollari markazi!", reply_markup=kb)
    else:
        await safe_reply(message, "🎮 WebApp hozirda ulanmagan.")

@router.message(Command("iqtest"))
async def cmd_iqtest(message: Message, db_user: dict | None = None):
    """Handle /iqtest command — Pro+ only WebApp IQ Test."""
    if not db_user:
        return
    plan = await subscription_dao.get_user_plan(db_user["user_id"])
    if not plan.get("iq_test_enabled"):
        await safe_reply(
            message,
            "🧩 <b>IQ Test</b> faqat <b>Pro</b> va <b>Premium</b> foydalanuvchilar uchun!\n\n"
            "Obunangizni yangilash: /subscribe"
        )
        return
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
    from src.bot.keyboards.user_menu import resolve_webapp_url

    plan_name = await subscription_dao.get_active_plan_name(db_user["user_id"])
    web_app_url = resolve_webapp_url(plan_name)
    if web_app_url:
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🧠 IQ Testni boshlash", web_app=WebAppInfo(url=f"{web_app_url.rstrip('/')}/iqtest"))
        ]])
        await safe_reply(message, "🧠 <b>IQ Test</b>\n\nMantiqiy fikrlash darajangizni aniqlovchi va savollari tez-tez yangilanib turuvchi maxsus test!", reply_markup=kb)
    else:
        await safe_reply(message, "🎮 WebApp hozirda ulanmagan.")


@router.message(Command("settings"))
async def cmd_settings(message: Message, db_user: dict | None = None):
    """Handle /settings — show level, mode and name pickers."""
    if not db_user:
        return

    level = db_user.get("level", "A1")
    display_name = db_user.get("first_name", "") or ""
    username = message.from_user.username if message.from_user else ""
    name_line = f"@{username}" if username else display_name or "—"

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    name_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Ismni o'zgartirish", callback_data="settings:rename")],
    ])

    text = (
        f"⚙️ <b>Sozlamalar</b>\n\n"
        f"👤 Ism: <b>{name_line}</b>\n"
        f"📊 Daraja: <b>{level}</b>\n\n"
        "Darajangizni o'zgartiring:"
    )
    from src.bot.keyboards.user_menu import level_picker_keyboard as _lpk
    full_kb = _lpk()
    # Append name button row
    full_kb.inline_keyboard.append([InlineKeyboardButton(text="✏️ Ismni o'zgartirish", callback_data="settings:rename")])
    await safe_reply(message, text, reply_markup=full_kb)


@router.callback_query(F.data.startswith("set_level:"))
async def callback_set_level(callback: CallbackQuery, db_user: dict | None = None):
    """Handle level selection callback."""
    if not db_user:
        await safe_answer_callback(callback, "❌ Foydalanuvchi topilmadi")
        return

    level = callback.data.split(":")[1]
    from src.config import settings
    if level not in settings.LEVELS:
        await safe_answer_callback(callback, "❌ Noto'g'ri daraja")
        return

    await user_dao.set_level(db_user["user_id"], level)
    await safe_answer_callback(callback, f"✅ Daraja {level} ga o'zgartirildi!")
    await safe_edit(
        callback,
        f"⚙️ <b>Sozlamalar</b>\n\n📊 Joriy daraja: <b>{level}</b> ✅\n\nDarajangizni o'zgartiring:",
        reply_markup=level_picker_keyboard(),
    )


@router.callback_query(F.data.startswith("mode:"))
async def callback_set_mode(callback: CallbackQuery, db_user: dict | None = None):
    """Handle mode selection callback."""
    if not db_user:
        await safe_answer_callback(callback, "❌ Xatolik")
        return
        
    mode = callback.data.split(":")[1]
    mode_names = {
        "check": "✅ Grammatika tekshiruv",
        "uz_to_en": "🌐 UZ→EN Tarjima",
        "en_to_uz": "🌐 EN→UZ Tarjima",
        "ru_to_en": "🇷🇺 RU→EN Tarjima",
        "en_to_ru": "🇬🇧 EN→RU Tarjima",
        "pronunciation": "🔊 Talaffuz",
        "bot": "🤖 AI Suhbat",
    }
    name = mode_names.get(mode, mode)
    await safe_answer_callback(callback, f"✅ Rejim: {name}")

    from src.services.mode_manager import set_mode
    await set_mode(db_user["user_id"], mode)

    await safe_edit(
        callback,
        f"⚙️ <b>Rejim tanlandi:</b> {name}\n\nEndi matn yozing!",
        reply_markup=mode_picker_keyboard(mode),
    )


@router.callback_query(F.data == "settings:rename")
async def callback_settings_rename(callback: CallbackQuery, db_user: dict | None = None):
    """Prompt user to send their preferred display name."""
    if not db_user:
        return
    from src.services.mode_manager import set_mode
    await set_mode(db_user["user_id"], "RENAME_PENDING")
    await safe_answer_callback(callback)
    await safe_edit(callback, "✏️ <b>Yangi ismingizni yozing:</b>\n\n<i>Masalan: Begzod yoki @begzod</i>")


@router.callback_query(F.data == "back:main")
async def callback_back_main(callback: CallbackQuery, db_user: dict | None = None):
    """Handle back to main menu."""
    await safe_answer_callback(callback)
    await safe_edit(callback, "🏠 <b>Asosiy menyu</b>\n\nNima qilmoqchisiz?")


@router.callback_query(F.data == "check_sponsor")
async def callback_check_sponsor(callback: CallbackQuery, db_user: dict | None = None):
    """Re-check sponsor subscription after user claims to have joined."""
    from src.database.dao.sponsor_dao import get_active_sponsors
    from src.bot.loader import bot

    sponsors = await get_active_sponsors()
    user_id = callback.from_user.id
    all_joined = True

    for sponsor in sponsors:
        try:
            member = await bot.get_chat_member(sponsor["channel_id"], user_id)
            if member.status in ("left", "kicked"):
                all_joined = False
                break
        except Exception:
            continue

    if all_joined:
        await safe_answer_callback(callback, "✅ Obuna tasdiqlandi!")
        await safe_edit(callback, "✅ <b>Obuna tasdiqlandi!</b>\n\nEndi botdan foydalanishingiz mumkin. /start bosing.")
    else:
        await safe_answer_callback(callback, "❌ Hali obuna bo'lmadingiz!", show_alert=True)
