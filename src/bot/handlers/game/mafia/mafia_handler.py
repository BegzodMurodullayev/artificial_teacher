"""
Mafia Game Handler — to'liq ishlaydigan versiya.

Bosqichlar:
  WAITING → NIGHT → DAY → (loop) → GAME_OVER

Tuzatilgan:
  - asyncio.sleep handler ichida emas, background task sifatida
  - DM callback'larida chat_id payload'dan olinadi
  - /stopm buyrug'i bilan to'xtatish
  - Mafiya bir-birini ko'radi (DM)
  - Har bir round alohida task, eski task overlap qilmaydi
"""

import asyncio
import json
import logging
import random

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
)

from src.bot.utils.telegram import safe_reply, safe_edit, safe_answer_callback
from src.database.dao import game_dao
from src.database.connection import get_db

logger = logging.getLogger(__name__)
router = Router(name="mafia_game")

# ── CONSTANTS ──────────────────────────────────────────
MIN_PLAYERS = 4
MAX_PLAYERS = 12
NIGHT_SECONDS = 90
DAY_SECONDS   = 120
JOIN_SECONDS  = 120

ROLES = {
    "mafia":     "🔪 Mafiya",
    "detective": "🔍 Detektiv",
    "doctor":    "💊 Doktor",
    "civilian":  "👤 Fuqaro",
}

ROLE_DESC = {
    "mafia":     "🔪 Siz <b>Mafiya</b>siz. Kechasi qurbonni tanlang!",
    "detective": "🔍 Siz <b>Detektiv</b>siz. Kechasi birortasini tekshiring!",
    "doctor":    "💊 Siz <b>Doktor</b>siz. Kechasi birortasini himoya qiling!",
    "civilian":  "👤 Siz <b>Fuqaro</b>siz. Kunduzi mafiyani toping!",
}


# ── HELPERS ────────────────────────────────────────────

def _assign_roles(player_ids: list[int]) -> dict[int, str]:
    n = len(player_ids)
    mafia_count = max(1, n // 3)
    shuffled = list(player_ids)
    random.shuffle(shuffled)
    roles = {}
    for i, pid in enumerate(shuffled):
        if i < mafia_count:
            roles[pid] = "mafia"
        elif i == mafia_count:
            roles[pid] = "detective"
        elif i == mafia_count + 1:
            roles[pid] = "doctor"
        else:
            roles[pid] = "civilian"
    return roles


def _alive_keyboard(payload: dict, action: str, exclude_id: int = 0) -> InlineKeyboardMarkup:
    alive = payload.get("alive", {})
    names = payload.get("names", {})
    sid   = payload["session_id"]
    buttons = []
    for uid_str in alive:
        uid = int(uid_str)
        if uid == exclude_id:
            continue
        name = names.get(uid_str, f"Player {uid_str}")
        buttons.append([InlineKeyboardButton(
            text=f"👤 {name}",
            callback_data=f"mf:{action}:{sid}:{uid}",
        )])
    return InlineKeyboardMarkup(inline_keyboard=buttons or [[
        InlineKeyboardButton(text="—", callback_data="mf:noop")
    ]])


def _count_alive(payload: dict) -> dict:
    alive = payload.get("alive", {})
    mafia = sum(1 for r in alive.values() if r == "mafia")
    town  = sum(1 for r in alive.values() if r != "mafia")
    return {"mafia": mafia, "town": town, "total": mafia + town}


def _vote_summary(payload: dict) -> str:
    """Return a formatted vote count string for the day phase."""
    day_votes  = payload.get("day_votes", {})
    names      = payload.get("names", {})
    alive      = payload.get("alive", {})
    vote_counts: dict[int, int] = {}
    for _, t in day_votes.items():
        vote_counts[t] = vote_counts.get(t, 0) + 1
    lines = []
    for uid_str in alive:
        uid_int = int(uid_str)
        cnt  = vote_counts.get(uid_int, 0)
        name = names.get(uid_str, "?")
        bar  = "🟥" * cnt + (" " + str(cnt) + " ta" if cnt else "")
        lines.append(f"  👤 {name}: {bar}")
    return "\n".join(lines)


async def _get_game_by_session(session_id: int) -> dict | None:
    db = await get_db()
    cursor = await db.execute("SELECT * FROM game_sessions WHERE id = ?", (session_id,))
    row = await cursor.fetchone()
    if not row:
        return None
    game = dict(row)
    try:
        game["payload"] = json.loads(game.get("payload", "{}"))
    except (json.JSONDecodeError, TypeError):
        game["payload"] = {}
    return game


async def _award_mafia_points(chat_id: int, payload: dict, winner: str) -> None:
    """Award game points to winners and losers. winner = 'mafia' | 'town'"""
    names  = payload.get("names", {})
    orig   = payload.get("original_roles", {})
    alive  = payload.get("alive", {})
    for uid_str, role in orig.items():
        uid    = int(uid_str)
        name   = names.get(uid_str, "Player")
        is_alv = uid_str in alive
        if winner == "mafia" and role == "mafia":
            pts, won = (30 if is_alv else 15), 1
        elif winner == "town" and role != "mafia":
            pts, won = (25 if is_alv else 10), 1
        else:
            pts, won = 5, 0
        try:
            await game_dao.add_game_points(chat_id, uid, name, points=pts, won=won)
        except Exception as e:
            logger.warning("add_game_points failed for %s: %s", uid, e)


async def _show_roles(bot: Bot, chat_id: int, payload: dict):
    players = payload.get("players", {})
    names   = payload.get("names", {})
    alive   = payload.get("alive", {})
    orig    = payload.get("original_roles", {})
    lines   = ["📋 <b>Barcha rollar:</b>\n"]
    for uid_str, name in names.items():
        role   = alive.get(uid_str) or orig.get(uid_str, "?")
        label  = ROLES.get(role, role)
        status = "" if uid_str in alive else " (💀)"
        lines.append(f"  {label} — {name}{status}")
    try:
        await bot.send_message(chat_id, "\n".join(lines))
    except Exception as e:
        logger.warning("_show_roles failed: %s", e)


# ══════════════════════════════════════════════════════
# PHASE RUNNERS  (background tasks — non-blocking)
# ══════════════════════════════════════════════════════

async def _run_night(bot: Bot, chat_id: int, session_id: int, round_num: int):
    """Background task: wait NIGHT_SECONDS then resolve night."""
    await asyncio.sleep(NIGHT_SECONDS)
    game = await _get_game_by_session(session_id)
    if (
        game
        and game["status"] == "night"
        and game["payload"].get("round") == round_num
    ):
        await _resolve_night(bot, chat_id, session_id)


async def _run_day(bot: Bot, chat_id: int, session_id: int, round_num: int):
    """Background task: wait DAY_SECONDS then resolve day."""
    await asyncio.sleep(DAY_SECONDS)
    game = await _get_game_by_session(session_id)
    if (
        game
        and game["status"] == "day"
        and game["payload"].get("round") == round_num
    ):
        await _resolve_day(bot, chat_id, session_id)


# ══════════════════════════════════════════════════════
# START / JOIN / CANCEL / STOP
# ══════════════════════════════════════════════════════

@router.message(Command("mafia"))
async def cmd_mafia(message: Message, db_user: dict | None = None):
    if message.chat.type == "private":
        await safe_reply(message, "🔪 Mafiya faqat guruhda o'ynaladi!")
        return

    existing = await game_dao.get_active_game(message.chat.id)
    if existing:
        await safe_reply(message, "⚠️ Bu guruhda allaqachon faol o'yin bor!")
        return

    uid  = message.from_user.id
    name = message.from_user.first_name or "Player"

    session_id = await game_dao.create_game_session(
        chat_id=message.chat.id,
        game_type="mafia",
        created_by=uid,
        payload={
            "players": {str(uid): name},
            "names":   {str(uid): name},
            "creator": uid,
            "chat_id": message.chat.id,
        },
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎮 Qo'shilish",    callback_data=f"mf:join:{session_id}")],
        [InlineKeyboardButton(text="🚀 Boshlash",       callback_data=f"mf:start:{session_id}")],
        [InlineKeyboardButton(text="❌ Bekor qilish",   callback_data=f"mf:cancel:{session_id}")],
    ])
    await safe_reply(
        message,
        f"🔪 <b>MAFIYA O'YINI</b>\n\n"
        f"👤 O'yinchilar: <b>1/{MAX_PLAYERS}</b>\n"
        f"1. {name}\n\n"
        f"⏳ {JOIN_SECONDS}s ichida qo'shiling!\n"
        f"Kamida <b>{MIN_PLAYERS}</b> ta o'yinchi kerak.",
        reply_markup=kb,
    )


@router.message(Command("mstatus"))
async def cmd_mafia_status(message: Message):
    """Show current mafia game status."""
    if message.chat.type == "private":
        return
    game = await game_dao.get_active_game(message.chat.id)
    if not game or game["game_type"] != "mafia":
        await safe_reply(message, "❌ Faol Mafiya o'yini yo'q.")
        return
    payload = game["payload"]
    counts  = _count_alive(payload)
    names   = payload.get("names", {})
    alive   = payload.get("alive", {})
    status  = game["status"]
    rnd     = payload.get("round", 1)
    phase   = {"night": "🌙 Kecha", "day": "☀️ Kunduz", "waiting": "⏳ Kutish"}.get(status, status)
    alive_list = "\n".join(f"  ⚪ {names.get(u, '?')}" for u in alive)
    await safe_reply(
        message,
        f"🔪 <b>Mafiya O'yini — {phase} #{rnd}</b>\n\n"
        f"👥 Tirik: {counts['total']} | 🔪 Mafiya: {counts['mafia']} | 🏘 Shahar: {counts['town']}\n\n"
        f"<b>Tirik o'yinchilar:</b>\n{alive_list}",
    )


@router.message(Command("stopm"))
async def cmd_stop_mafia(message: Message, db_user: dict | None = None):
    if message.chat.type == "private":
        return
    game = await game_dao.get_active_game(message.chat.id)
    if not game:
        await safe_reply(message, "❌ Faol o'yin yo'q.")
        return
    role = (db_user or {}).get("role", "user")
    if message.from_user.id != game["payload"].get("creator") and role not in ("admin", "owner"):
        await safe_reply(message, "❌ Faqat o'yin tashkil etuvchi yoki admin to'xtatishi mumkin.")
        return
    await game_dao.finish_game_session(game["id"])
    await safe_reply(message, "🛑 <b>Mafiya o'yini to'xtatildi.</b>")


@router.callback_query(F.data.startswith("mf:join:"))
async def cb_join(callback: CallbackQuery):
    session_id = int(callback.data.split(":")[2])
    game = await game_dao.get_active_game(callback.message.chat.id)
    if not game or game["id"] != session_id or game["status"] != "waiting":
        await safe_answer_callback(callback, "❌ O'yin topilmadi")
        return

    payload  = game["payload"]
    uid_str  = str(callback.from_user.id)
    username = callback.from_user.first_name or "Player"

    if uid_str in payload.get("players", {}):
        await safe_answer_callback(callback, "⚠️ Siz allaqachon qo'shilgansiz!", show_alert=True)
        return
    if len(payload["players"]) >= MAX_PLAYERS:
        await safe_answer_callback(callback, f"⚠️ Maksimum {MAX_PLAYERS} ta o'yinchi!", show_alert=True)
        return

    payload["players"][uid_str] = username
    payload["names"][uid_str]   = username
    await game_dao.update_game_session(session_id, "waiting", payload)

    player_list = "\n".join(
        f"{i}. {n}" for i, (_, n) in enumerate(payload["players"].items(), 1)
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎮 Qo'shilish",  callback_data=f"mf:join:{session_id}")],
        [InlineKeyboardButton(text="🚀 Boshlash",     callback_data=f"mf:start:{session_id}")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"mf:cancel:{session_id}")],
    ])
    await safe_edit(
        callback,
        f"🔪 <b>MAFIYA O'YINI</b>\n\n"
        f"👤 O'yinchilar: <b>{len(payload['players'])}/{MAX_PLAYERS}</b>\n"
        f"{player_list}\n\n"
        f"Kamida <b>{MIN_PLAYERS}</b> ta o'yinchi kerak.",
        reply_markup=kb,
    )
    await safe_answer_callback(callback, f"✅ {username} qo'shildi!")


@router.callback_query(F.data.startswith("mf:cancel:"))
async def cb_cancel(callback: CallbackQuery):
    session_id = int(callback.data.split(":")[2])
    game = await game_dao.get_active_game(callback.message.chat.id)
    if not game or game["id"] != session_id:
        return
    if callback.from_user.id != game["payload"].get("creator"):
        await safe_answer_callback(callback, "❌ Faqat tashkil etuvchi bekor qila oladi!", show_alert=True)
        return
    await game_dao.finish_game_session(session_id)
    await safe_edit(callback, "❌ <b>Mafiya o'yini bekor qilindi.</b>")
    await safe_answer_callback(callback)


@router.callback_query(F.data == "mf:noop")
async def cb_noop(callback: CallbackQuery):
    await safe_answer_callback(callback)


# ══════════════════════════════════════════════════════
# START GAME
# ══════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("mf:start:"))
async def cb_start_game(callback: CallbackQuery, bot: Bot):
    session_id = int(callback.data.split(":")[2])
    game = await game_dao.get_active_game(callback.message.chat.id)
    if not game or game["id"] != session_id or game["status"] != "waiting":
        return

    payload = game["payload"]
    if callback.from_user.id != payload.get("creator"):
        await safe_answer_callback(callback, "❌ Faqat tashkil etuvchi boshlashi mumkin!", show_alert=True)
        return

    players = payload["players"]
    if len(players) < MIN_PLAYERS:
        await safe_answer_callback(
            callback,
            f"⚠️ Kamida {MIN_PLAYERS} ta o'yinchi kerak! Hozir: {len(players)}",
            show_alert=True,
        )
        return

    player_ids = [int(p) for p in players]
    roles = _assign_roles(player_ids)

    payload["alive"]          = {str(uid): role for uid, role in roles.items()}
    payload["original_roles"] = {str(uid): role for uid, role in roles.items()}
    payload["session_id"]     = session_id
    payload["chat_id"]        = callback.message.chat.id
    payload["round"]          = 1
    payload["night_votes"]    = {}
    payload["day_votes"]      = {}
    payload["doctor_target"]  = None
    payload["detective_result"] = None

    await game_dao.update_game_session(session_id, "night", payload, round_number=1)
    await safe_answer_callback(callback)

    counts = _count_alive(payload)
    await safe_edit(
        callback,
        f"🌙 <b>MAFIYA O'YINI BOSHLANDI!</b>\n\n"
        f"👥 O'yinchilar: {counts['total']}\n"
        f"🔪 Mafiya: {counts['mafia']} ta\n"
        f"🏘 Shahar: {counts['town']} ta\n\n"
        f"📩 Har bir o'yinchiga roli yuborildi.\n"
        f"🌙 <b>1-KECHA boshlandi!</b>",
    )

    # Notify roles via DM
    mafia_ids = [uid for uid, r in roles.items() if r == "mafia"]
    mafia_names = [payload["names"].get(str(uid), "?") for uid in mafia_ids]
    mafia_list  = ", ".join(mafia_names)

    for uid, role in roles.items():
        try:
            extra = ""
            if role == "mafia" and len(mafia_ids) > 1:
                others = [payload["names"].get(str(m), "?") for m in mafia_ids if m != uid]
                extra = f"\n\n👥 Jamoa mafiyangiz: <b>{', '.join(others)}</b>"
            await bot.send_message(uid, ROLE_DESC[role] + extra)
        except Exception as e:
            logger.warning("DM role to %s failed: %s", uid, e)

    await _start_night_phase(bot, callback.message.chat.id, session_id, payload)


# ══════════════════════════════════════════════════════
# NIGHT PHASE
# ══════════════════════════════════════════════════════

async def _start_night_phase(bot: Bot, chat_id: int, session_id: int, payload: dict):
    """Send night DMs and launch background timer."""
    alive     = payload.get("alive", {})
    round_num = payload.get("round", 1)

    payload["night_votes"]     = {}
    payload["doctor_target"]   = None
    payload["detective_result"] = None
    await game_dao.update_game_session(session_id, "night", payload, round_number=round_num)

    for uid_str, role in alive.items():
        uid = int(uid_str)
        try:
            if role == "mafia":
                kb = _alive_keyboard(payload, "kill", exclude_id=uid)
                await bot.send_message(
                    uid,
                    f"🌙 <b>Kecha #{round_num}</b>\n🔪 Kimni o'ldirasiz?",
                    reply_markup=kb,
                )
            elif role == "doctor":
                kb = _alive_keyboard(payload, "heal", exclude_id=0)
                await bot.send_message(
                    uid,
                    f"🌙 <b>Kecha #{round_num}</b>\n💊 Kimni himoya qilasiz?",
                    reply_markup=kb,
                )
            elif role == "detective":
                kb = _alive_keyboard(payload, "check", exclude_id=uid)
                await bot.send_message(
                    uid,
                    f"🌙 <b>Kecha #{round_num}</b>\n🔍 Kimni tekshirasiz?",
                    reply_markup=kb,
                )
        except Exception as e:
            logger.warning("Night DM failed for %s: %s", uid, e)

    asyncio.create_task(_run_night(bot, chat_id, session_id, round_num))


# ── Night action callbacks ──

@router.callback_query(F.data.startswith("mf:kill:"))
async def cb_mafia_kill(callback: CallbackQuery):
    parts      = callback.data.split(":")
    session_id = int(parts[2])
    target_id  = int(parts[3])

    game = await _get_game_by_session(session_id)
    if not game or game["status"] != "night":
        await safe_answer_callback(callback, "❌ Kecha tugagan")
        return

    payload = game["payload"]
    uid     = str(callback.from_user.id)
    if payload.get("alive", {}).get(uid) != "mafia":
        await safe_answer_callback(callback, "❌ Siz mafiya emassiz!")
        return

    payload.setdefault("night_votes", {})[uid] = target_id
    await game_dao.update_game_session(session_id, "night", payload)

    name = payload.get("names", {}).get(str(target_id), "?")
    await safe_answer_callback(callback, f"🔪 {name} tanlandi!")
    try:
        await callback.message.edit_text(f"🔪 Siz <b>{name}</b>ni tanladingiz. Kechani kuting...")
    except Exception:
        pass


@router.callback_query(F.data.startswith("mf:heal:"))
async def cb_doctor_heal(callback: CallbackQuery):
    parts      = callback.data.split(":")
    session_id = int(parts[2])
    target_id  = int(parts[3])

    game = await _get_game_by_session(session_id)
    if not game or game["status"] != "night":
        await safe_answer_callback(callback, "❌ Kecha tugagan")
        return

    payload = game["payload"]
    payload["doctor_target"] = target_id
    await game_dao.update_game_session(session_id, "night", payload)

    name = payload.get("names", {}).get(str(target_id), "?")
    await safe_answer_callback(callback, f"💊 {name} himoya qilindi!")
    try:
        await callback.message.edit_text(f"💊 <b>{name}</b>ni himoya qildingiz. Kechani kuting...")
    except Exception:
        pass


@router.callback_query(F.data.startswith("mf:check:"))
async def cb_detective_check(callback: CallbackQuery):
    parts      = callback.data.split(":")
    session_id = int(parts[2])
    target_id  = int(parts[3])

    game = await _get_game_by_session(session_id)
    if not game or game["status"] != "night":
        await safe_answer_callback(callback, "❌ Kecha tugagan")
        return

    payload     = game["payload"]
    target_role = payload.get("alive", {}).get(str(target_id), "civilian")
    name        = payload.get("names", {}).get(str(target_id), "?")
    is_mafia    = target_role == "mafia"

    payload["detective_result"] = {"target": target_id, "is_mafia": is_mafia}
    await game_dao.update_game_session(session_id, "night", payload)

    result = f"🔍 <b>{name}</b> — {'🔪 MAFIYA!' if is_mafia else '👤 Begunoh'}"
    await safe_answer_callback(callback, "🔍 Natija olindi!")
    try:
        await callback.message.edit_text(result)
    except Exception:
        pass


# ── Resolve night ──

async def _resolve_night(bot: Bot, chat_id: int, session_id: int):
    game = await _get_game_by_session(session_id)
    if not game:
        return

    payload      = game["payload"]
    alive        = dict(payload.get("alive", {}))
    names        = payload.get("names", {})
    night_votes  = payload.get("night_votes", {})
    doctor_target = payload.get("doctor_target")
    round_num    = payload.get("round", 1)

    # Majority vote
    vote_counts: dict[int, int] = {}
    for _, target in night_votes.items():
        vote_counts[target] = vote_counts.get(target, 0) + 1

    victim_id = max(vote_counts, key=vote_counts.get) if vote_counts else None
    saved     = victim_id is not None and victim_id == doctor_target

    lines = [f"☀️ <b>Kunduz #{round_num}</b>\n"]

    if victim_id and not saved:
        victim_name = names.get(str(victim_id), "?")
        victim_role = alive.pop(str(victim_id), "civilian")
        lines.append(f"💀 <b>{victim_name}</b> o'ldirildi! ({ROLES.get(victim_role, '?')})")
    elif saved:
        victim_name = names.get(str(victim_id), "?")
        lines.append(f"💊 <b>{victim_name}</b> doktor tomonidan saqlab qolindi!")
    else:
        lines.append("🌅 Tungi hech kim o'lmadi.")

    payload["alive"] = alive
    counts = _count_alive(payload)

    # Win checks
    if counts["mafia"] == 0:
        await game_dao.finish_game_session(session_id)
        await _award_mafia_points(chat_id, payload, "town")
        lines.append("\n🎉 <b>SHAHAR G'ALABA QOZONDI!</b> 🏘")
        await bot.send_message(chat_id, "\n".join(lines))
        await _show_roles(bot, chat_id, payload)
        return

    if counts["mafia"] >= counts["town"]:
        await game_dao.finish_game_session(session_id)
        await _award_mafia_points(chat_id, payload, "mafia")
        lines.append("\n🔪 <b>MAFIYA G'ALABA QOZONDI!</b>")
        await bot.send_message(chat_id, "\n".join(lines))
        await _show_roles(bot, chat_id, payload)
        return

    # Day phase
    payload["day_votes"] = {}
    await game_dao.update_game_session(session_id, "day", payload)

    alive_list = "\n".join(
        f"  ⚪ {names.get(u, '?')}" for u in alive
    )
    lines.append(f"\n👥 <b>Tirik ({counts['total']}):</b>\n{alive_list}")
    lines.append(f"\n⏱ Muhokama: {DAY_SECONDS}s")

    kb = _alive_keyboard(payload, "vote", exclude_id=0)
    await bot.send_message(
        chat_id,
        "\n".join(lines) + "\n\n🗳 Kimni chiqarasiz? Ovoz bering:",
        reply_markup=kb,
    )

    asyncio.create_task(_run_day(bot, chat_id, session_id, round_num))


# ══════════════════════════════════════════════════════
# DAY PHASE
# ══════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("mf:vote:"))
async def cb_day_vote(callback: CallbackQuery):
    parts      = callback.data.split(":")
    session_id = int(parts[2])
    target_id  = int(parts[3])

    game = await _get_game_by_session(session_id)
    if not game or game["status"] != "day":
        await safe_answer_callback(callback, "❌ Ovoz berish tugagan")
        return

    payload = game["payload"]
    uid     = str(callback.from_user.id)
    if uid not in payload.get("alive", {}):
        await safe_answer_callback(callback, "❌ Siz o'yinda emassiz!", show_alert=True)
        return

    payload.setdefault("day_votes", {})[uid] = target_id
    await game_dao.update_game_session(session_id, "day", payload)

    target_name = payload.get("names", {}).get(str(target_id), "?")
    await safe_answer_callback(callback, f"🗳 {target_name} uchun ovoz berdingiz!")

    # Live vote count — edit the group message
    try:
        counts    = _count_alive(payload)
        voted_cnt = len(payload.get("day_votes", {}))
        rnd       = payload.get("round", 1)
        summary   = _vote_summary(payload)
        kb        = _alive_keyboard(payload, "vote", exclude_id=0)
        await callback.message.edit_text(
            f"☀️ <b>Kunduz #{rnd}</b> — Ovoz berish ({voted_cnt}/{counts['total']})\n\n"
            f"{summary}\n\n"
            "🗳 Kimni chiqarasiz?",
            reply_markup=kb,
        )
    except Exception as e:
        logger.debug("Vote live-edit failed: %s", e)


async def _resolve_day(bot: Bot, chat_id: int, session_id: int):
    game = await _get_game_by_session(session_id)
    if not game:
        return

    payload   = game["payload"]
    alive     = dict(payload.get("alive", {}))
    names     = payload.get("names", {})
    day_votes = payload.get("day_votes", {})

    vote_counts: dict[int, int] = {}
    for _, target in day_votes.items():
        vote_counts[target] = vote_counts.get(target, 0) + 1

    if vote_counts:
        max_v = max(vote_counts.values())
        top   = [t for t, c in vote_counts.items() if c == max_v]
        if len(top) == 1:
            expelled_id   = top[0]
            expelled_name = names.get(str(expelled_id), "?")
            expelled_role = alive.pop(str(expelled_id), "civilian")
            msg = (
                f"🗳 <b>Ovoz berish natijasi:</b>\n\n"
                f"🚪 <b>{expelled_name}</b> chiqarildi! ({ROLES.get(expelled_role, '?')})\n"
            )
        else:
            msg = "🗳 <b>Ovozlar teng!</b> Hech kim chiqarilmadi.\n"
    else:
        msg = "🗳 <b>Hech kim ovoz bermadi.</b> Hech kim chiqarilmadi.\n"

    payload["alive"] = alive
    counts = _count_alive(payload)

    if counts["mafia"] == 0:
        await game_dao.finish_game_session(session_id)
        await _award_mafia_points(chat_id, payload, "town")
        msg += "\n🎉 <b>SHAHAR G'ALABA QOZONDI!</b> 🏘"
        await bot.send_message(chat_id, msg)
        await _show_roles(bot, chat_id, payload)
        return

    if counts["mafia"] >= counts["town"]:
        await game_dao.finish_game_session(session_id)
        await _award_mafia_points(chat_id, payload, "mafia")
        msg += "\n🔪 <b>MAFIYA G'ALABA QOZONDI!</b>"
        await bot.send_message(chat_id, msg)
        await _show_roles(bot, chat_id, payload)
        return

    # Next round
    payload["round"] = payload.get("round", 1) + 1
    await game_dao.update_game_session(
        session_id, "night", payload, round_number=payload["round"]
    )
    msg += f"\n🌙 <b>Kecha #{payload['round']} boshlandi!</b>\n📩 Shaxsiy xabarlarni tekshiring."
    await bot.send_message(chat_id, msg)

    await _start_night_phase(bot, chat_id, session_id, payload)
