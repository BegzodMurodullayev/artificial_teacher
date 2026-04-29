"""
Keyboards for user/admin reply menus and reusable inline builders.
"""

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)

from src.config import settings

PLAN_ORDER = ("free", "standard", "pro", "premium")
PLAN_LABELS = {
    "free": "Free",
    "standard": "Standard",
    "pro": "Pro",
    "premium": "Premium",
}


def normalize_plan_name(plan_name: str = "free") -> str:
    plan = (plan_name or "free").strip().lower()
    return plan if plan in PLAN_ORDER else "free"


def resolve_webapp_url(plan_name: str = "free") -> str:
    """Resolve plan-specific WebApp URL with graceful fallback."""
    plan = normalize_plan_name(plan_name)
    plan_url_map = {
        "free": settings.WEB_APP_URL_FREE,
        "standard": settings.WEB_APP_URL_STANDARD,
        "pro": settings.WEB_APP_URL_PRO,
        "premium": settings.WEB_APP_URL_PREMIUM,
    }
    url = plan_url_map.get(plan) or settings.WEB_APP_URL
    return (url or "").strip()


def resolve_materials_launch(plan_name: str = "free") -> tuple[str, str]:
    """Resolve the hosted materials URL. Returns ("", plan) if no MATERIALS_URL is set.

    NOTE: Does NOT fall back to WEB_APP_URL — the main WebApp and Materials are separate.
    Set MATERIALS_URL or MATERIALS_URL_* in .env to enable this feature.
    """
    plan = normalize_plan_name(plan_name)
    materials_url_map = {
        "free":     settings.MATERIALS_URL_FREE,
        "standard": settings.MATERIALS_URL_STANDARD,
        "pro":      settings.MATERIALS_URL_PRO,
        "premium":  settings.MATERIALS_URL_PREMIUM,
    }

    # 1. Plan-specific MATERIALS_URL
    direct = (materials_url_map.get(plan) or "").strip()
    if direct:
        return direct, plan

    # 2. Generic MATERIALS_URL
    generic = (settings.MATERIALS_URL or "").strip()
    if generic:
        return generic, plan

    # 3. Fallback to lower-tier MATERIALS_URL only (never WEB_APP_URL)
    plan_index = PLAN_ORDER.index(plan)
    for candidate in reversed(PLAN_ORDER[:plan_index]):
        fallback = (materials_url_map.get(candidate) or "").strip()
        if fallback:
            return fallback, candidate

    return "", plan


def resolve_materials_url(plan_name: str = "free") -> str:
    return resolve_materials_launch(plan_name)[0]


def user_main_menu(plan_name: str = "free", role: str = "user") -> ReplyKeyboardMarkup:
    """Build the main user reply keyboard based on plan and role."""
    rows = [
        [KeyboardButton(text="🎓 Ta'lim"), KeyboardButton(text="🎯 Sinovlar")],
        [KeyboardButton(text="🎮 O'yinlar"), KeyboardButton(text="👤 Kabinetim")],
        [KeyboardButton(text="⚙️ Qo'shimcha")],
    ]

    webapp_url = resolve_webapp_url(plan_name)
    if webapp_url:
        rows.append(
            [
                KeyboardButton(
                    text="📱 Ilovani ochish",
                    web_app=WebAppInfo(url=webapp_url),
                )
            ]
        )

    if role in ("admin", "owner"):
        rows.append([KeyboardButton(text="🛡 Admin Panel")])

    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        input_field_placeholder="Yo'nalishni tanlang...",
    )


def edu_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Tekshirish"), KeyboardButton(text="🌐 Tarjima")],
            [KeyboardButton(text="🔊 Talaffuz"), KeyboardButton(text="📚 Darslar")],
            [KeyboardButton(text="📖 Grammatika"), KeyboardButton(text="🗓 Kunlik so'z")],
            [KeyboardButton(text="🧩 Materiallar")],
            [KeyboardButton(text="📚 Kutubxona"), KeyboardButton(text="💡 Evrika")],
            [KeyboardButton(text="🔙 Asosiy Menyu")],
        ],
        resize_keyboard=True,
    )


def test_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🧠 Quiz"), KeyboardButton(text="🧠 IQ Test")],
            [KeyboardButton(text="🧠 Zakovat"), KeyboardButton(text="🔙 Asosiy Menyu")],
        ],
        resize_keyboard=True,
    )


def games_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🕹️ Katta O'yinlar (WebApp)")],
            [KeyboardButton(text="❌ X-O (Tic-Tac)"), KeyboardButton(text="🃏 Xotira")],
            [KeyboardButton(text="🔢 Raqam Topish"), KeyboardButton(text="⚡ Tez Hisob")],
            [KeyboardButton(text="🔤 So'z Topish"), KeyboardButton(text="🏃 Tarjima Poygasi")],
            [KeyboardButton(text="🔎 Xato Topish"), KeyboardButton(text="🕵️ Mafiya")],
            [KeyboardButton(text="🧩 Sudoku"), KeyboardButton(text="🔙 Asosiy Menyu")],
        ],
        resize_keyboard=True,
    )


def cabinet_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📈 Darajam"), KeyboardButton(text="⭐ Obuna")],
            [KeyboardButton(text="🎁 Bonuslar"), KeyboardButton(text="🔙 Asosiy Menyu")],
        ],
        resize_keyboard=True,
    )


def extra_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⏱ Pomodoro Timer")],
            [KeyboardButton(text="⚙️ Sozlamalar"), KeyboardButton(text="ℹ️ Aloqa")],
            [KeyboardButton(text="🔙 Asosiy Menyu")],
        ],
        resize_keyboard=True,
    )


def admin_main_menu() -> ReplyKeyboardMarkup:
    """Build the admin dashboard reply keyboard."""
    rows = [
        [KeyboardButton(text="💳 To'lovlar"), KeyboardButton(text="👥 Foydalanuvchilar")],
        [KeyboardButton(text="📢 Broadcast"), KeyboardButton(text="📈 Statistika")],
        [KeyboardButton(text="⚙️ Rejalar"), KeyboardButton(text="🏆 Reyting")],
        [KeyboardButton(text="🛡 Adminlar"), KeyboardButton(text="💰 To'lov Sozlamalari")],
        [KeyboardButton(text="📢 Homiy Kanallar")],
        [KeyboardButton(text="🔙 Asosiy Menyu")],
    ]
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        input_field_placeholder="Admin menyusidan tanlang...",
    )


USER_MENU_ALIASES = {
    "check": ["✅ Tekshirish", "✅ Check", "check", "tekshirish"],
    "translate": ["🌐 Tarjima", "🌐 Translate", "translate", "tarjima"],
    "pronunciation": ["🔊 Talaffuz", "🔊 Pronunciation", "pronunciation", "talaffuz"],
    "quiz": ["🧠 Quiz", "quiz"],
    "lessons": ["📚 Darslar", "📚 Lessons", "lessons", "darslar"],
    "grammar": ["📖 Grammatika", "📖 Grammar", "grammar", "grammatika"],
    "daily_word": ["🗓 Kunlik so'z", "📅 Kunlik so'z", "kunlik so'z"],
    "stats": [
        "📊 Statistika",
        "📈 Darajam",
        "📊 Natijalarim",
        "stats",
        "statistika",
        "darajam",
        "natijalarim",
        "darajam / reyting",
    ],
    "subscribe": ["⭐ Obuna", "⭐ Subscribe", "subscribe", "obuna", "💳 Tariflar", "💎 Tariflar", "tariflar"],
    "settings": ["⚙️ Sozlamalar", "⚙️ Settings", "settings", "sozlamalar"],
    "help": ["ℹ️ Yordam", "ℹ️ Aloqa", "💬 Aloqa", "help", "yordam", "aloqa"],
    "iq_test": ["🧠 IQ Test", "iq test"],
    "materials": ["🧩 Materiallar", "materiallar", "materials"],
    "library": ["📚 Kutubxona"],
    "evrika": ["💡 Evrika"],
    "zakovat": ["🧠 Zakovat"],
    "pomodoro": ["⏱ Pomodoro Timer", "pomodoro"],
    "game_xo": ["❌ X-O (Tic-Tac)"],
    "game_memory": ["🃏 Xotira"],
    "game_sudoku": ["🧩 Sudoku"],
    "game_number": ["🔢 Raqam Topish"],
    "game_math": ["⚡ Tez Hisob"],
    "game_mafia": ["🕵️ Mafiya", "🎮 Mafiya"],
    "game_word": ["🔤 So'z Topish"],
    "game_translate": ["🏃 Tarjima Poygasi"],
    "game_error": ["🔎 Xato Topish"],
    "game_webapp": ["🕹️ Katta O'yinlar (WebApp)", "🕹️ WebApp O'yinlar"],
    "main_menu": [
        "🔙 Asosiy Menyu",
        "Menu",
        "menu",
        "Menyu",
        "menyu",
        "Bosh menyu",
        "bosh menyu",
        "🏠 Menyu",
        "🏠 Bosh menyu",
    ],
    "edu_menu": ["🎓 Ta'lim"],
    "test_menu": ["🎯 Sinovlar"],
    "games_menu": ["🎮 O'yinlar", "🎮 Guruh O'yinlari"],
    "cabinet_menu": ["👤 Kabinetim"],
    "extra_menu": ["⚙️ Qo'shimcha"],
    "admin": ["🛡 Admin Panel", "admin panel"],
    "adm_payments": ["💳 To'lovlar"],
    "adm_users": ["👥 Foydalanuvchilar"],
    "adm_broadcast": ["📢 Broadcast"],
    "adm_stats": ["📈 Statistika"],
    "adm_plans": ["⚙️ Rejalar"],
    "adm_leaderboard": ["🏆 Reyting"],
    "adm_admins": ["🛡 Adminlar"],
    "adm_payment_settings": ["💰 To'lov Sozlamalari"],
    "adm_sponsors": ["📢 Homiy Kanallar"],
    "bonuses": ["🎁 Bonuslar", "🎁 Bonus markazi", "bonuslar", "bonus markazi"],
}


def resolve_menu_action(text: str) -> str | None:
    """Resolve user text to a menu action key."""
    clean = text.strip()
    clean_folded = clean.casefold()
    for action, aliases in USER_MENU_ALIASES.items():
        if any(clean_folded == alias.strip().casefold() for alias in aliases):
            return action
    return None


def level_picker_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="A1 🟢", callback_data="set_level:A1"),
            InlineKeyboardButton(text="A2 🟡", callback_data="set_level:A2"),
        ],
        [
            InlineKeyboardButton(text="B1 🟠", callback_data="set_level:B1"),
            InlineKeyboardButton(text="B2 🔵", callback_data="set_level:B2"),
        ],
        [
            InlineKeyboardButton(text="C1 🟣", callback_data="set_level:C1"),
            InlineKeyboardButton(text="C2 🔴", callback_data="set_level:C2"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def mode_picker_keyboard(current_mode: str = "check") -> InlineKeyboardMarkup:
    modes = [
        ("✅ Check", "mode:check"),
        ("🌐 UZ→EN", "mode:uz_to_en"),
        ("🌐 EN→UZ", "mode:en_to_uz"),
        ("🇷🇺 RU→EN", "mode:ru_to_en"),
        ("🇬🇧 EN→RU", "mode:en_to_ru"),
        ("🔊 Pronunciation", "mode:pronunciation"),
        ("🤖 AI Chat", "mode:bot"),
    ]
    buttons = []
    for label, data in modes:
        prefix = "▶️ " if data.split(":")[1] == current_mode else ""
        buttons.append([InlineKeyboardButton(text=f"{prefix}{label}", callback_data=data)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def confirm_keyboard(
    action: str,
    label_yes: str = "✅ Ha",
    label_no: str = "❌ Yo'q",
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=label_yes, callback_data=f"confirm:{action}:yes"),
                InlineKeyboardButton(text=label_no, callback_data=f"confirm:{action}:no"),
            ]
        ]
    )


def back_button(callback_data: str = "back:main") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 Ortga", callback_data=callback_data)]]
    )


def lesson_topics_keyboard() -> InlineKeyboardMarkup:
    from src.services.content_service import get_available_lesson_topics

    topics = get_available_lesson_topics()
    buttons = []
    icons = {"greetings": "🤝", "shopping": "🛍️", "travel": "✈️"}
    for topic in topics:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{icons.get(topic, '📚')} {topic.title()}",
                    callback_data=f"lesson:{topic}",
                )
            ]
        )
    buttons.append([InlineKeyboardButton(text="✏️ Custom Topic", callback_data="lesson:custom")])
    buttons.append([InlineKeyboardButton(text="🔙 Ortga", callback_data="back:main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def grammar_rules_keyboard() -> InlineKeyboardMarkup:
    from src.services.content_service import get_available_rules

    rules = get_available_rules()
    buttons = []
    icons = {
        "tenses": "⏰",
        "articles": "📝",
        "prepositions": "📍",
        "questions": "❓",
        "conditionals": "🔁",
        "passive": "🔄",
    }
    for index in range(0, len(rules), 2):
        row = []
        for rule in rules[index:index + 2]:
            row.append(
                InlineKeyboardButton(
                    text=f"{icons.get(rule, '📖')} {rule.title()}",
                    callback_data=f"rule:{rule}",
                )
            )
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="✏️ Custom Rule", callback_data="rule:custom")])
    buttons.append([InlineKeyboardButton(text="🔙 Ortga", callback_data="back:main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def subscription_plans_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="⭐ Standard — 29,000 so'm/oy", callback_data="plan:standard")],
        [InlineKeyboardButton(text="💎 Pro — 59,000 so'm/oy", callback_data="plan:pro")],
        [InlineKeyboardButton(text="👑 Premium — 99,000 so'm/oy", callback_data="plan:premium")],
        [InlineKeyboardButton(text="📋 Rejalarni solishtirish", callback_data="plan:compare")],
        [InlineKeyboardButton(text="🔙 Ortga", callback_data="back:main")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
