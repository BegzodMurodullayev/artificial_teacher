"""
Keyboards — user menu, admin menu, and reusable inline keyboard builders.
"""

from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    WebAppInfo,
)
from src.config import settings


# ══════════════════════════════════════════════════════════
# USER REPLY KEYBOARD
# ══════════════════════════════════════════════════════════

def user_main_menu(plan_name: str = "free", role: str = "user") -> ReplyKeyboardMarkup:
    """Build the main user reply keyboard based on plan and role."""
    rows = [
        [KeyboardButton(text="🎓 Ta'lim"), KeyboardButton(text="🎯 Sinovlar")],
        [KeyboardButton(text="🎮 Guruh O'yinlari"), KeyboardButton(text="👤 Kabinetim")],
        [KeyboardButton(text="⚙️ Qo'shimcha")],
    ]

    # Add WebApp button if URL is configured
    if settings.WEB_APP_URL:
        rows.append([
            KeyboardButton(
                text="📱 Ilovani ochish",
                web_app=WebAppInfo(url=settings.WEB_APP_URL),
            )
        ])

    # Show admin button only for admins/owners
    if role in ("admin", "owner"):
        rows.append([KeyboardButton(text="🛡 Admin Panel")])

    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        input_field_placeholder="Yo'nalishni tanlang...",
    )

def edu_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="✅ Tekshirish"), KeyboardButton(text="🌐 Tarjima")],
        [KeyboardButton(text="🔊 Talaffuz"), KeyboardButton(text="📚 Darslar")],
        [KeyboardButton(text="📖 Grammatika"), KeyboardButton(text="📅 Kunlik so'z")],
        [KeyboardButton(text="📚 Kutubxona"), KeyboardButton(text="💡 Evrika")],
        [KeyboardButton(text="🔙 Asosiy Menyu")]
    ], resize_keyboard=True)

def test_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🧠 Quiz"), KeyboardButton(text="🧠 IQ Test")],
        [KeyboardButton(text="🧠 Zakovat"), KeyboardButton(text="🔙 Asosiy Menyu")]
    ], resize_keyboard=True)

def games_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🔢 Raqam Topish"), KeyboardButton(text="⚡ Tez Hisob")],
        [KeyboardButton(text="🔤 So'z Topish"), KeyboardButton(text="🏃 Tarjima Poygasi")],
        [KeyboardButton(text="🕵️ Mafiya"), KeyboardButton(text="🕹️ WebApp O'yinlar")],
        [KeyboardButton(text="🔙 Asosiy Menyu")]
    ], resize_keyboard=True)

def cabinet_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📈 Darajam"), KeyboardButton(text="⭐ Obuna")],
        [KeyboardButton(text="🎁 Bonuslar"), KeyboardButton(text="🔙 Asosiy Menyu")]
    ], resize_keyboard=True)

def extra_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="⚙️ Sozlamalar"), KeyboardButton(text="ℹ️ Aloqa")],
        [KeyboardButton(text="🔙 Asosiy Menyu")]
    ], resize_keyboard=True)

def admin_main_menu() -> ReplyKeyboardMarkup:
    """Build the admin dashboard reply keyboard."""
    rows = [
        [KeyboardButton(text="💳 To'lovlar"), KeyboardButton(text="👥 Foydalanuvchilar")],
        [KeyboardButton(text="📢 Broadcast"), KeyboardButton(text="📈 Statistika")],
        [KeyboardButton(text="⚙️ Rejalar"), KeyboardButton(text="🏆 Reyting")],
        [KeyboardButton(text="🔙 Asosiy Menyu")],
    ]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, input_field_placeholder="Admin menyusidan tanlang...")


# ══════════════════════════════════════════════════════════
# MENU ALIASES (for text matching)
# ══════════════════════════════════════════════════════════

USER_MENU_ALIASES = {
    "check":         ["✅ Tekshirish", "✅ Check", "check", "tekshirish"],
    "translate":     ["🌐 Tarjima", "🌐 Translate", "translate", "tarjima"],
    "pronunciation": ["🔊 Talaffuz", "🔊 Pronunciation", "pronunciation", "talaffuz"],
    "quiz":          ["🧠 Quiz", "quiz"],
    "lessons":       ["📚 Darslar", "📚 Lessons", "lessons", "darslar"],
    "grammar":       ["📖 Grammatika", "📖 Grammar", "grammar", "grammatika"],
    "daily_word":    ["📅 Kunlik so'z"],
    "stats":         ["📊 Statistika", "📈 Darajam", "stats", "statistika", "darajam"],
    "subscribe":     ["⭐ Obuna", "⭐ Subscribe", "subscribe", "obuna"],
    "settings":      ["⚙️ Sozlamalar", "⚙️ Settings", "settings", "sozlamalar"],
    "help":          ["ℹ️ Yordam", "ℹ️ Aloqa", "help", "yordam", "aloqa"],
    "iq_test":       ["🧠 IQ Test", "iq test"],
    "library":       ["📚 Kutubxona"],
    "evrika":        ["💡 Evrika"],
    "zakovat":       ["🧠 Zakovat"],
    "game_number":   ["🔢 Raqam Topish"],
    "game_math":     ["⚡ Tez Hisob"],
    "game_mafia":    ["🕵️ Mafiya", "🎮 Mafiya"],
    "game_word":     ["🔤 So'z Topish"],
    "game_translate": ["🏃 Tarjima Poygasi"],
    "game_webapp":   ["🕹️ WebApp O'yinlar"],
    # ── Navigation ────
    "main_menu":     ["🔙 Asosiy Menyu"],
    "edu_menu":      ["🎓 Ta'lim"],
    "test_menu":     ["🎯 Sinovlar"],
    "games_menu":    ["🎮 Guruh O'yinlari"],
    "cabinet_menu":  ["👤 Kabinetim"],
    "extra_menu":    ["⚙️ Qo'shimcha"],
    "admin":         ["🛡 Admin Panel", "admin panel"],
    # ── Admin Panel buttons (must always be skipped by message_handler) ────
    "adm_payments":  ["💳 To'lovlar"],
    "adm_users":     ["👥 Foydalanuvchilar"],
    "adm_broadcast": ["📢 Broadcast"],
    "adm_stats":     ["📈 Statistika"],
    "adm_plans":     ["⚙️ Rejalar"],
    "adm_leaderboard": ["🏆 Reyting"],
    "bonuses":       ["🎁 Bonuslar"],
}


def resolve_menu_action(text: str) -> str | None:
    """Resolve user text to a menu action key."""
    clean = text.strip()
    for action, aliases in USER_MENU_ALIASES.items():
        if clean in aliases:
            return action
    return None


# ══════════════════════════════════════════════════════════
# INLINE KEYBOARDS
# ══════════════════════════════════════════════════════════

def level_picker_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting English level."""
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
    """Keyboard for selecting bot mode."""
    modes = [
        ("✅ Check", "mode:check"),
        ("🌐 UZ→EN", "mode:uz_to_en"),
        ("🌐 EN→UZ", "mode:en_to_uz"),
        ("🔊 Pronunciation", "mode:pronunciation"),
        ("🤖 AI Chat", "mode:bot"),
    ]
    buttons = []
    for label, data in modes:
        prefix = "▶️ " if data.split(":")[1] == current_mode else ""
        buttons.append([InlineKeyboardButton(text=f"{prefix}{label}", callback_data=data)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def confirm_keyboard(action: str, label_yes: str = "✅ Ha", label_no: str = "❌ Yo'q") -> InlineKeyboardMarkup:
    """Generic confirmation keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=label_yes, callback_data=f"confirm:{action}:yes"),
            InlineKeyboardButton(text=label_no, callback_data=f"confirm:{action}:no"),
        ]
    ])


def back_button(callback_data: str = "back:main") -> InlineKeyboardMarkup:
    """Simple back button."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Ortga", callback_data=callback_data)]
    ])


def lesson_topics_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting lesson topics."""
    from src.services.content_service import get_available_lesson_topics
    topics = get_available_lesson_topics()
    buttons = []
    icons = {"greetings": "🤝", "shopping": "🛍️", "travel": "✈️"}
    for topic in topics:
        icon = icons.get(topic, "📚")
        buttons.append([InlineKeyboardButton(
            text=f"{icon} {topic.title()}",
            callback_data=f"lesson:{topic}",
        )])
    buttons.append([InlineKeyboardButton(text="✏️ Custom Topic", callback_data="lesson:custom")])
    buttons.append([InlineKeyboardButton(text="🔙 Ortga", callback_data="back:main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def grammar_rules_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting grammar rules."""
    from src.services.content_service import get_available_rules
    rules = get_available_rules()
    buttons = []
    icons = {
        "tenses": "⏰", "articles": "📝", "prepositions": "📍",
        "questions": "❓", "conditionals": "🔀", "passive": "🔄",
    }
    for i in range(0, len(rules), 2):
        row = []
        for rule in rules[i:i+2]:
            icon = icons.get(rule, "📖")
            row.append(InlineKeyboardButton(
                text=f"{icon} {rule.title()}",
                callback_data=f"rule:{rule}",
            ))
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="✏️ Custom Rule", callback_data="rule:custom")])
    buttons.append([InlineKeyboardButton(text="🔙 Ortga", callback_data="back:main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def subscription_plans_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting subscription plans."""
    buttons = [
        [InlineKeyboardButton(text="⭐ Standard — 29,000 so'm/oy", callback_data="plan:standard")],
        [InlineKeyboardButton(text="💎 Pro — 59,000 so'm/oy", callback_data="plan:pro")],
        [InlineKeyboardButton(text="👑 Premium — 99,000 so'm/oy", callback_data="plan:premium")],
        [InlineKeyboardButton(text="📋 Rejalarni solishtirish", callback_data="plan:compare")],
        [InlineKeyboardButton(text="🔙 Ortga", callback_data="back:main")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
