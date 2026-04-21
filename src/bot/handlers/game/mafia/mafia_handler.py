"""
Mafia Game Handler — Telegram rasmiy Mafia o'yiniga o'xshash to'liq inline o'yin.

O'yin bosqichlari:
1. WAITING — O'yinchilar qo'shiladi (min 4, max 12)
2. NIGHT  — Mafiya qurbonni tanlaydi, Doktor davolaydi, Detektiv tekshiradi
3. DAY    — Muhokama + ovoz berish
4. GAME_OVER — G'olib e'lon qilinadi
"""

import asyncio
import json
import logging
import random
from datetime import datetime

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
)

from src.bot.utils.telegram import safe_reply, safe_edit, safe_answer_callback
from src.database.dao import game_dao

logger = logging.getLogger(__name__)
router = Router(name="mafia_game")

# ── CONSTANTS ──────────────────────────────────────────────
MIN_PLAYERS = 4
MAX_PLAYERS = 12
NIGHT_SECONDS = 90
DAY_SECONDS = 120
JOIN_SECONDS = 120

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

# ── HELPERS ────────────────────────────────────────────────

def _assign_roles(player_ids: list[int]) -> dict[int, str]:
    """Distribute roles: ~1/3 mafia, 1 detective, 1 doctor, rest civilians."""
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
    """Build keyboard with alive players as buttons."""
    alive = payload.get("alive", {})
    names = payload.get("names", {})
    buttons = []
    for uid_str, role in alive.items():
        uid = int(uid_str)
        if uid == exclude_id:
            continue
        name = names.get(uid_str, f"Player {uid_str}")
        buttons.append([InlineKeyboardButton(
            text=f"👤 {name}",
            callback_data=f"mf:{action}:{payload['session_id']}:{uid}",
        )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _count_alive(payload: dict) -> dict:
    """Count alive mafia vs town."""
    alive = payload.get("alive", {})
    mafia = sum(1 for r in alive.values() if r == "mafia")
    town = sum(1 for r in alive.values() if r != "mafia")
    return {"mafia": mafia, "town": town, "total": mafia + town}


# ══════════════════════════════════════════════════════════
# START COMMAND
# ══════════════════════════════════════════════════════════

@router.message(Command("mafia"))
async def cmd_mafia(message: Message, db_user: dict | None = None):
    """Start a new Mafia game in the group."""
    if message.chat.type == "private":
        await safe_reply(message, "🔪 Mafiya faqat guruhda o'ynaladi!\nBotni guruhga qo'shing.")
        return

    # Check for existing game
    existing = await game_dao.get_active_game(message.chat.id)
    if existing:
        await safe_reply(message, "⚠️ Bu guruhda allaqachon faol o'yin bor!")
        return

    user_id = message.from_user.id
    username = message.from_user.first_name or "Player"

    # Create session
    session_id = await game_dao.create_game_session(
        chat_id=message.chat.id,
        game_type="mafia",
        created_by=user_id,
        payload={
            "players": {str(user_id): username},
            "names": {str(user_id): username},
            "creator": user_id,
        },
    )

    join_btn = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎮 Qo'shilish", callback_data=f"mf:join:{session_id}")],
        [InlineKeyboardButton(text="🚀 Boshlash", callback_data=f"mf:start:{session_id}")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"mf:cancel:{session_id}")],
    ])

    await safe_reply(
        message,
        f"🔪 <b>MAFIYA O'YINI</b>\n\n"
        f"👤 O'yinchilar: <b>1/{MAX_PLAYERS}</b>\n"
        f"1. {username}\n\n"
        f"⏳ {JOIN_SECONDS}s ichida qo'shiling!\n"
        f"Kamida <b>{MIN_PLAYERS}</b> ta o'yinchi kerak.",
        reply_markup=join_btn,
    )


# ══════════════════════════════════════════════════════════
# JOIN / START / CANCEL
# ══════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("mf:join:"))
async def cb_join(callback: CallbackQuery):
    session_id = int(callback.data.split(":")[2])
    game = await game_dao.get_active_game(callback.message.chat.id)
    if not game or game["id"] != session_id or game["status"] != "waiting":
        await safe_answer_callback(callback, "❌ O'yin topilmadi")
        return

    payload = game["payload"]
    user_id = str(callback.from_user.id)
    username = callback.from_user.first_name or "Player"

    if user_id in payload.get("players", {}):
        await safe_answer_callback(callback, "⚠️ Siz allaqachon qo'shilgansiz!", show_alert=True)
        return

    if len(payload["players"]) >= MAX_PLAYERS:
        await safe_answer_callback(callback, f"⚠️ Maksimum {MAX_PLAYERS} ta o'yinchi!", show_alert=True)
        return

    payload["players"][user_id] = username
    payload["names"][user_id] = username
    await game_dao.update_game_session(session_id, "waiting", payload)

    player_list = "\n".join(
        f"{i}. {name}" for i, (_, name) in enumerate(payload["players"].items(), 1)
    )

    join_btn = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎮 Qo'shilish", callback_data=f"mf:join:{session_id}")],
        [InlineKeyboardButton(text="🚀 Boshlash", callback_data=f"mf:start:{session_id}")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"mf:cancel:{session_id}")],
    ])

    await safe_edit(
        callback,
        f"🔪 <b>MAFIYA O'YINI</b>\n\n"
        f"👤 O'yinchilar: <b>{len(payload['players'])}/{MAX_PLAYERS}</b>\n"
        f"{player_list}\n\n"
        f"Kamida <b>{MIN_PLAYERS}</b> ta o'yinchi kerak.",
        reply_markup=join_btn,
    )
    await safe_answer_callback(callback, f"✅ {username} qo'shildi!")


@router.callback_query(F.data.startswith("mf:cancel:"))
async def cb_cancel(callback: CallbackQuery):
    session_id = int(callback.data.split(":")[2])
    game = await game_dao.get_active_game(callback.message.chat.id)
    if not game or game["id"] != session_id:
        return

    payload = game["payload"]
    if callback.from_user.id != payload.get("creator"):
        await safe_answer_callback(callback, "❌ Faqat tashkil etuvchi bekor qila oladi!", show_alert=True)
        return

    await game_dao.finish_game_session(session_id)
    await safe_edit(callback, "❌ <b>Mafiya o'yini bekor qilindi.</b>")
    await safe_answer_callback(callback)


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

    # Assign roles
    player_ids = [int(pid) for pid in players.keys()]
    roles = _assign_roles(player_ids)

    payload["alive"] = {str(uid): role for uid, role in roles.items()}
    payload["session_id"] = session_id
    payload["round"] = 1
    payload["night_votes"] = {}
    payload["day_votes"] = {}
    payload["doctor_target"] = None
    payload["detective_result"] = None

    await game_dao.update_game_session(session_id, "night", payload, round_number=1)
    await safe_answer_callback(callback)

    # Announce
    count = _count_alive(payload)
    await safe_edit(
        callback,
        f"🌙 <b>MAFIYA O'YINI BOSHLANDI!</b>\n\n"
        f"👥 O'yinchilar: {count['total']}\n"
        f"🔪 Mafiya: {count['mafia']} ta\n"
        f"🏘 Shahar: {count['town']} ta\n\n"
        f"📩 Har bir o'yinchiga roli yuborildi.\n"
        f"🌙 <b>1-KECHA boshlandi!</b>",
    )

    # DM roles to all players
    for uid, role in roles.items():
        try:
            await bot.send_message(uid, ROLE_DESC[role])
        except Exception as e:
            logger.warning("Could not DM role to %s: %s", uid, e)

    # Start night phase
    await _start_night(bot, callback.message.chat.id, session_id, payload)


# ══════════════════════════════════════════════════════════
# NIGHT PHASE
# ══════════════════════════════════════════════════════════

async def _start_night(bot: Bot, chat_id: int, session_id: int, payload: dict):
    """Send night action buttons to role players via DM."""
    alive = payload.get("alive", {})
    names = payload.get("names", {})
    round_num = payload.get("round", 1)

    # Reset night state
    payload["night_votes"] = {}
    payload["doctor_target"] = None
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
                kb = _alive_keyboard(payload, "heal", exclude_id=0)  # doctor can heal self
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

    # Auto-advance after timeout
    await asyncio.sleep(NIGHT_SECONDS)

    # Re-read to check if game still active
    game = await game_dao.get_active_game(chat_id)
    if game and game["id"] == session_id and game["status"] == "night":
        p = game["payload"]
        if p.get("round") == round_num:
            await _resolve_night(bot, chat_id, session_id)


# ── Night Callbacks ──

@router.callback_query(F.data.startswith("mf:kill:"))
async def cb_mafia_kill(callback: CallbackQuery):
    parts = callback.data.split(":")
    session_id, target_id = int(parts[2]), int(parts[3])

    game = await game_dao.get_active_game(callback.message.chat.id if callback.message else 0)
    # fallback: get from DB directly
    if not game:
        from src.database.connection import get_db
        db = await get_db()
        cursor = await db.execute("SELECT * FROM game_sessions WHERE id = ? AND status = 'night'", (session_id,))
        row = await cursor.fetchone()
        if row:
            game = dict(row)
            game["payload"] = json.loads(game.get("payload", "{}"))

    if not game or game["status"] != "night":
        await safe_answer_callback(callback, "❌ Kecha tugagan")
        return

    payload = game["payload"]
    uid = str(callback.from_user.id)
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
    parts = callback.data.split(":")
    session_id, target_id = int(parts[2]), int(parts[3])

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
    parts = callback.data.split(":")
    session_id, target_id = int(parts[2]), int(parts[3])

    game = await _get_game_by_session(session_id)
    if not game or game["status"] != "night":
        await safe_answer_callback(callback, "❌ Kecha tugagan")
        return

    payload = game["payload"]
    target_role = payload.get("alive", {}).get(str(target_id), "civilian")
    name = payload.get("names", {}).get(str(target_id), "?")
    is_mafia = target_role == "mafia"

    result = f"🔍 <b>{name}</b> — {'🔪 MAFIYA!' if is_mafia else '👤 Begunoh'}"
    payload["detective_result"] = {"target": target_id, "is_mafia": is_mafia}
    await game_dao.update_game_session(session_id, "night", payload)

    await safe_answer_callback(callback, "🔍 Natija olindi!")
    try:
        await callback.message.edit_text(result)
    except Exception:
        pass


async def _get_game_by_session(session_id: int) -> dict | None:
    """Helper to get game by session_id."""
    from src.database.connection import get_db
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM game_sessions WHERE id = ?", (session_id,)
    )
    row = await cursor.fetchone()
    if not row:
        return None
    game = dict(row)
    try:
        game["payload"] = json.loads(game.get("payload", "{}"))
    except (json.JSONDecodeError, TypeError):
        game["payload"] = {}
    return game


# ── Resolve Night ──

async def _resolve_night(bot: Bot, chat_id: int, session_id: int):
    """Process night results and transition to day."""
    game = await _get_game_by_session(session_id)
    if not game:
        return

    payload = game["payload"]
    alive = payload.get("alive", {})
    names = payload.get("names", {})
    night_votes = payload.get("night_votes", {})
    doctor_target = payload.get("doctor_target")

    # Determine victim (majority vote from mafia)
    vote_counts: dict[int, int] = {}
    for _, target in night_votes.items():
        vote_counts[target] = vote_counts.get(target, 0) + 1

    victim_id = max(vote_counts, key=vote_counts.get) if vote_counts else None

    # Check if doctor saved the victim
    saved = victim_id is not None and victim_id == doctor_target

    result_lines = [f"☀️ <b>Kunduz #{payload.get('round', 1)}</b>\n"]

    if victim_id and not saved:
        victim_name = names.get(str(victim_id), "?")
        victim_role = alive.pop(str(victim_id), "civilian")
        result_lines.append(f"💀 <b>{victim_name}</b> o'ldirildi! ({ROLES.get(victim_role, '?')})")
    elif saved:
        victim_name = names.get(str(victim_id), "?")
        result_lines.append(f"💊 <b>{victim_name}</b> doktor tomonidan saqlab qolindi!")
    else:
        result_lines.append("🌅 Tungi hech kim o'lmadi.")

    payload["alive"] = alive

    # Check win conditions
    counts = _count_alive(payload)
    if counts["mafia"] == 0:
        # Town wins
        await game_dao.finish_game_session(session_id)
        result_lines.append("\n🎉 <b>SHAHAR G'ALABA QOZONDI!</b> 🏘")
        result_lines.append("\nBarcha mafiyalar yo'q qilindi!")
        await bot.send_message(chat_id, "\n".join(result_lines))
        await _show_roles(bot, chat_id, payload)
        return

    if counts["mafia"] >= counts["town"]:
        # Mafia wins
        await game_dao.finish_game_session(session_id)
        result_lines.append("\n🔪 <b>MAFIYA G'ALABA QOZONDI!</b>")
        result_lines.append("\nMafiya shaharni qo'lga kiritdi!")
        await bot.send_message(chat_id, "\n".join(result_lines))
        await _show_roles(bot, chat_id, payload)
        return

    # Continue to day phase
    payload["day_votes"] = {}
    await game_dao.update_game_session(session_id, "day", payload)

    # Alive list
    alive_list = "\n".join(
        f"  {'🔴' if i == 0 else '⚪'} {names.get(uid_str, '?')}"
        for i, uid_str in enumerate(alive.keys())
    )
    result_lines.append(f"\n👥 <b>Tirik o'yinchilar ({counts['total']}):</b>\n{alive_list}")
    result_lines.append(f"\n⏱ Muhokama va ovoz berish: {DAY_SECONDS}s")

    kb = _alive_keyboard(payload, "vote", exclude_id=0)
    await bot.send_message(
        chat_id,
        "\n".join(result_lines) + "\n\n🗳 Kimni chiqarasiz? Ovoz bering:",
        reply_markup=kb,
    )

    # Auto-advance
    await asyncio.sleep(DAY_SECONDS)
    game = await _get_game_by_session(session_id)
    if game and game["status"] == "day" and game["payload"].get("round") == payload.get("round"):
        await _resolve_day(bot, chat_id, session_id)


# ══════════════════════════════════════════════════════════
# DAY PHASE
# ══════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("mf:vote:"))
async def cb_day_vote(callback: CallbackQuery):
    parts = callback.data.split(":")
    session_id, target_id = int(parts[2]), int(parts[3])

    game = await _get_game_by_session(session_id)
    if not game or game["status"] != "day":
        await safe_answer_callback(callback, "❌ Ovoz berish tugagan")
        return

    payload = game["payload"]
    uid = str(callback.from_user.id)
    if uid not in payload.get("alive", {}):
        await safe_answer_callback(callback, "❌ Siz o'yinda emassiz!", show_alert=True)
        return

    payload.setdefault("day_votes", {})[uid] = target_id
    await game_dao.update_game_session(session_id, "day", payload)

    voter = callback.from_user.first_name
    target_name = payload.get("names", {}).get(str(target_id), "?")
    await safe_answer_callback(callback, f"🗳 {target_name} uchun ovoz berdingiz!")

    # Announce in chat
    try:
        await callback.message.chat.do("typing")
    except Exception:
        pass


async def _resolve_day(bot: Bot, chat_id: int, session_id: int):
    """Process day vote results and transition to night."""
    game = await _get_game_by_session(session_id)
    if not game:
        return

    payload = game["payload"]
    alive = payload.get("alive", {})
    names = payload.get("names", {})
    day_votes = payload.get("day_votes", {})

    vote_counts: dict[int, int] = {}
    for _, target in day_votes.items():
        vote_counts[target] = vote_counts.get(target, 0) + 1

    if vote_counts:
        max_votes = max(vote_counts.values())
        top_targets = [t for t, c in vote_counts.items() if c == max_votes]
        # If tie, no one is expelled
        if len(top_targets) == 1:
            expelled_id = top_targets[0]
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

    # Check win
    counts = _count_alive(payload)
    if counts["mafia"] == 0:
        await game_dao.finish_game_session(session_id)
        msg += "\n🎉 <b>SHAHAR G'ALABA QOZONDI!</b> 🏘"
        await bot.send_message(chat_id, msg)
        await _show_roles(bot, chat_id, payload)
        return

    if counts["mafia"] >= counts["town"]:
        await game_dao.finish_game_session(session_id)
        msg += "\n🔪 <b>MAFIYA G'ALABA QOZONDI!</b>"
        await bot.send_message(chat_id, msg)
        await _show_roles(bot, chat_id, payload)
        return

    # Move to next night
    payload["round"] = payload.get("round", 1) + 1
    await game_dao.update_game_session(session_id, "night", payload, round_number=payload["round"])

    msg += f"\n🌙 <b>Kecha #{payload['round']} boshlandi!</b>\n📩 Rollar uchun shaxsiy xabarlarni tekshiring."
    await bot.send_message(chat_id, msg)

    await _start_night(bot, chat_id, session_id, payload)


# ── End Result ──

async def _show_roles(bot: Bot, chat_id: int, payload: dict):
    """Show all player roles at game end."""
    players = payload.get("players", {})
    all_roles = {}
    # Merge alive and dead
    for uid_str, name in players.items():
        role = payload.get("alive", {}).get(uid_str, None)
        if not role:
            # Was killed — check initial assignment
            # Find from the names + we need original roles
            role = "?"
        all_roles[uid_str] = role

    # Build role list
    names = payload.get("names", {})
    lines = ["📋 <b>Barcha rollar:</b>\n"]
    for uid_str, name in names.items():
        role = payload.get("alive", {}).get(uid_str, "💀 O'lgan")
        if isinstance(role, str) and role in ROLES:
            role_label = ROLES[role]
        else:
            role_label = str(role)
        lines.append(f"  {role_label} — {name}")

    try:
        await bot.send_message(chat_id, "\n".join(lines))
    except Exception as e:
        logger.warning("Failed to show roles: %s", e)
