"""
Group Games Handler — /scores, /stopoyun, /xatotopish, /guruhoyinlar
"""

import asyncio
import logging

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message

from src.database.dao import game_dao
from src.bot.utils.telegram import safe_reply

logger = logging.getLogger(__name__)
router = Router(name="group_games")

# ══════════════════════════════════════════════════════════
# XATO TOPISH O'YINI
# ══════════════════════════════════════════════════════════

FALLBACK_ERROR_SENTENCES = [
    {
        "wrong": "She go to school every day.",
        "correct": "She goes to school every day.",
        "explain": "<b>goes</b> ishlatiladi — 3-shaxs birlik (he/she/it) uchun Present Simple'da fe'lga -s/-es qo'shiladi.",
    },
    {
        "wrong": "I am agree with you.",
        "correct": "I agree with you.",
        "explain": "<b>agree</b> — 'agree' fe'li bilan 'am' ishlatilmaydi.",
    },
    {
        "wrong": "He don't like coffee.",
        "correct": "He doesn't like coffee.",
        "explain": "<b>doesn't</b> — 3-shaxs birlik uchun 'don't' emas, 'doesn't' ishlatiladi.",
    },
    {
        "wrong": "They was happy yesterday.",
        "correct": "They were happy yesterday.",
        "explain": "<b>were</b> — ko'plik uchun 'was' emas, 'were' ishlatiladi.",
    },
    {
        "wrong": "I have been to London last year.",
        "correct": "I went to London last year.",
        "explain": "<b>went</b> — aniq vaqt (last year) bilan Present Perfect emas, Past Simple ishlatiladi.",
    },
    {
        "wrong": "She is more taller than her sister.",
        "correct": "She is taller than her sister.",
        "explain": "<b>taller</b> — qiyosiy darajada 'more' va '-er' birga ishlatilmaydi.",
    },
    {
        "wrong": "I didn't went to the party.",
        "correct": "I didn't go to the party.",
        "explain": "<b>go</b> — did/didn't dan keyin fe'lning asosiy shakli (infinitive) ishlatiladi.",
    },
    {
        "wrong": "Can you speak more slow?",
        "correct": "Can you speak more slowly?",
        "explain": "<b>slowly</b> — fe'lni o'zgartiruvchi so'z ravish bo'lishi kerak (slow → slowly).",
    },
]


@router.message(Command("xatotopish", "errorgame"))
async def cmd_xato_topish(message: Message, bot: Bot):
    """Start an Error Finding game in the group."""
    if message.chat.type == "private":
        await safe_reply(message, "🎮 Bu o'yin faqat guruhda ishlaydi!")
        return

    chat_id = message.chat.id
    active_game = await game_dao.get_active_game(chat_id)
    if active_game:
        await safe_reply(
            message,
            f"⚠️ Bu chatda allaqachon o'yin ketyapti! (Turi: {active_game['game_type']})\n"
            "Avval /stopoyun bilan to'xtating.",
        )
        return

    msg = await safe_reply(message, "⏳ <i>O'yin tayyorlanmoqda...</i>")
    if not msg:
        return

    from src.bot.utils.telegram import safe_edit

    # Try AI first
    import random
    challenge = None
    try:
        from src.services import ai_service
        data = await ai_service.ask_json(
            "Give me a sentence with a grammar error and its correction.",
            mode="game_error",
        )
        if data and "wrong" in data and "correct" in data:
            challenge = data
    except Exception as e:
        logger.warning("AI error challenge failed: %s", e)

    if not challenge:
        challenge = random.choice(FALLBACK_ERROR_SENTENCES).copy()

    payload = {
        "wrong":   challenge["wrong"],
        "correct": challenge["correct"],
        "explain": challenge.get("explain", ""),
        "creator": message.from_user.id,
    }

    session_id = await game_dao.create_game_session(
        chat_id=chat_id,
        game_type="xato_topish",
        created_by=message.from_user.id,
        payload=payload,
    )

    await safe_edit(
        msg,
        f"🔎 <b>Xato Topish O'yini!</b>\n\n"
        f"Quyidagi gapda grammatik xato bor. To'g'ri variantini yozing:\n\n"
        f"❌ <i>{challenge['wrong']}</i>\n\n"
        f"⏱ Vaqt: 45 soniya. Birinchi to'g'ri javob yutadi!",
    )

    async def finish_error_timeout():
        await asyncio.sleep(45)
        game = await game_dao.get_active_game(chat_id)
        if game and game["id"] == session_id and game["status"] != "finished":
            await game_dao.finish_game_session(session_id)
            explain = payload.get("explain", "")
            await bot.send_message(
                chat_id,
                f"⏱ <b>Vaqt tugadi!</b>\n\n"
                f"✅ To'g'ri javob: <b>{payload['correct']}</b>\n\n"
                + (f"💡 {explain}" if explain else ""),
            )

    asyncio.create_task(finish_error_timeout())


# ══════════════════════════════════════════════════════════
# XATO TOPISH — CATCH INPUT
# ══════════════════════════════════════════════════════════

def _normalize(text: str) -> str:
    return text.lower().strip().rstrip(".")


async def _is_error_game_active(message: Message) -> bool:
    if not message.text or message.text.startswith("/"):
        return False
    from src.bot.keyboards.user_menu import resolve_menu_action
    if resolve_menu_action(message.text):
        return False
    active = await game_dao.get_active_game(message.chat.id)
    return active is not None and active["game_type"] == "xato_topish"


@router.message(_is_error_game_active)
async def process_error_input(message: Message):
    """Check if user found the correct sentence."""
    chat_id = message.chat.id
    active_game = await game_dao.get_active_game(chat_id)
    if not active_game:
        return

    user_text = _normalize(message.text)
    payload   = active_game["payload"]
    correct   = _normalize(payload.get("correct", ""))
    explain   = payload.get("explain", "")

    if user_text == correct:
        user_id   = message.from_user.id
        user_name = message.from_user.first_name or "Player"
        await game_dao.finish_game_session(active_game["id"])
        await game_dao.add_game_points(chat_id, user_id, user_name, points=20, won=1)
        await safe_reply(
            message,
            f"🎉 <b>To'g'ri, {user_name}!</b>\n\n"
            f"✅ <b>{payload['correct']}</b>\n\n"
            + (f"💡 {explain}\n\n" if explain else "")
            + "(+20 ball)",
        )


# ══════════════════════════════════════════════════════════
# SCORES / LEADERBOARD
# ══════════════════════════════════════════════════════════

@router.message(Command("scores", "top", "reyting"))
async def cmd_scores(message: Message):
    """Show group game leaderboard."""
    if message.chat.type == "private":
        await safe_reply(message, "📊 Bu buyruq faqat guruhda ishlaydi!")
        return

    scores = await game_dao.get_game_scores(message.chat.id, limit=10)
    if not scores:
        await safe_reply(
            message,
            "📊 <b>Guruh O'yin Reytingi</b>\n\nHali o'yin natijalari yo'q!\n"
            "O'yin boshlash uchun /guruhoyinlar",
        )
        return

    medals = ["🥇", "🥈", "🥉"]
    lines  = ["🏆 <b>Guruh O'yin Reytingi</b>\n"]
    for i, s in enumerate(scores):
        medal = medals[i] if i < 3 else f"{i + 1}."
        lines.append(
            f"{medal} <b>{s['username']}</b> — {s['points']} ball "
            f"({s.get('wins', 0)} g'alaba)"
        )
    await safe_reply(message, "\n".join(lines))


@router.message(Command("resetscores"))
async def cmd_reset_scores(message: Message, db_user: dict | None = None):
    """Reset group game scores (admin/owner only)."""
    if message.chat.type == "private":
        return
    role = (db_user or {}).get("role", "user")
    if role not in ("admin", "owner"):
        await safe_reply(message, "❌ Faqat admin yoki owner reset qila oladi!")
        return
    await game_dao.reset_game_scores(message.chat.id)
    await safe_reply(message, "✅ <b>Guruh o'yin reytingi tozalandi!</b>")


# ══════════════════════════════════════════════════════════
# STOP ANY ACTIVE GAME
# ══════════════════════════════════════════════════════════

@router.message(Command("stopoyun"))
async def cmd_stop_oyun(message: Message, db_user: dict | None = None):
    """Stop any active non-mafia game (creator or admin)."""
    if message.chat.type == "private":
        return

    game = await game_dao.get_active_game(message.chat.id)
    if not game:
        await safe_reply(message, "❌ Faol o'yin yo'q.")
        return

    if game["game_type"] == "mafia":
        await safe_reply(message, "ℹ️ Mafiya o'yinini to'xtatish uchun /stopm buyrug'ini ishlating.")
        return

    uid  = message.from_user.id
    role = (db_user or {}).get("role", "user")
    is_creator = game.get("payload", {}).get("creator") == uid or game.get("created_by") == uid

    if not is_creator and role not in ("admin", "owner"):
        await safe_reply(message, "❌ Faqat o'yin tashkil etuvchi yoki admin to'xtatishi mumkin!")
        return

    game_names = {
        "raqam_top":      "🎲 Raqam Top",
        "tez_hisob":      "⚡ Tez Hisob",
        "soz_topish":     "🔤 So'z Topish",
        "tarjima_poygasi":"🏃 Tarjima Poygasi",
        "xato_topish":    "🔎 Xato Topish",
    }
    gname = game_names.get(game["game_type"], game["game_type"])
    await game_dao.finish_game_session(game["id"])
    await safe_reply(message, f"🛑 <b>{gname}</b> o'yini to'xtatildi.")


# ══════════════════════════════════════════════════════════
# GURUH O'YINLAR MENYUSI
# ══════════════════════════════════════════════════════════

@router.message(Command("guruhoyinlar", "games"))
async def cmd_guruh_oyinlar(message: Message):
    """Show all available group game commands."""
    await safe_reply(
        message,
        "🎮 <b>Guruh O'yinlari</b>\n\n"
        "📝 <b>So'z o'yinlari:</b>\n"
        "/soztopish — Sinonim/Antonim toping (30s)\n"
        "/tarjimapoyga — Gapni tarjima qiling (45s)\n"
        "/xatotopish — Grammatik xatoni toping (45s)\n\n"
        "🔢 <b>Mini o'yinlar:</b>\n"
        "/raqamtop — 1-100 orasidagi raqamni toping (10 urinish)\n"
        "/tezhisob — Matematik misolni tez yeching (30s)\n\n"
        "🔪 <b>Rol o'yini:</b>\n"
        "/mafia — Mafiya o'yinini boshlash (4-12 o'yinchi)\n"
        "/mstatus — Mafiya o'yin holati\n"
        "/stopm — Mafiya o'yinini to'xtatish\n\n"
        "📊 <b>Reyting:</b>\n"
        "/scores — Guruh reytingini ko'rish\n"
        "/resetscores — Reytingni tozalash (admin)\n\n"
        "🛑 <b>Boshqaruv:</b>\n"
        "/stopoyun — Aktiv o'yinni to'xtatish",
    )
