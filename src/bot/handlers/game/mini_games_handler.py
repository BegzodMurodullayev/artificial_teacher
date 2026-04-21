import logging
import random
import asyncio
from typing import Optional

from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.filters import Command

from src.database.dao import game_dao
from src.bot.utils.telegram import safe_reply

logger = logging.getLogger(__name__)
router = Router(name="mini_games")

# ══════════════════════════════════════════════════════════
# RAQAM TOP (NUMBER GUESS)
# ══════════════════════════════════════════════════════════

@router.message(Command(commands=["raqamtop", "numberguess"]))
async def cmd_raqam_top(message: Message):
    """Start a Number Guess game."""
    chat_id = message.chat.id
    
    active_game = await game_dao.get_active_game(chat_id)
    if active_game:
        await safe_reply(message, f"⚠️ Bu chatda allaqachon o'yin ketyapti! (Turi: {active_game['game_type']})")
        return

    secret_number = random.randint(1, 100)
    
    payload = {
        "secret": secret_number,
        "attempts": 0,
        "max_attempts": 10,
        "players": {}
    }
    
    await game_dao.create_game_session(
        chat_id=chat_id,
        game_type="raqam_top",
        created_by=message.from_user.id if message.from_user else 0,
        payload=payload
    )
    
    await safe_reply(
        message,
        "🎮 <b>Raqam Top O'yini boshlandi!</b>\n\n"
        "Men 1 dan 100 gacha bo'lgan bir raqam o'yladim.\n"
        "Qani, kim birinchi bo'lib to'g'ri topadi? Raqam yozib yuboring! (Sizda 10 ta urinish bor)"
    )


# ══════════════════════════════════════════════════════════
# TEZ HISOB (MATH GAME)
# ══════════════════════════════════════════════════════════

@router.message(Command(commands=["tezhisob", "mathgame"]))
async def cmd_tez_hisob(message: Message, bot: Bot):
    """Start a Math game."""
    chat_id = message.chat.id
    
    active_game = await game_dao.get_active_game(chat_id)
    if active_game:
        await safe_reply(message, f"⚠️ Bu chatda allaqachon o'yin ketyapti! (Turi: {active_game['game_type']})")
        return

    a = random.randint(10, 50)
    b = random.randint(5, 30)
    ops = [("+", lambda x,y: x+y), ("-", lambda x,y: x-y), ("*", lambda x,y: x*y)]
    op_str, op_func = random.choice(ops)
    
    if op_str == "*":
        a = random.randint(2, 12)
        b = random.randint(2, 12)
        
    answer = op_func(a, b)
    
    payload = {
        "answer": answer,
        "task": f"{a} {op_str} {b}"
    }
    
    session_id = await game_dao.create_game_session(
        chat_id=chat_id,
        game_type="tez_hisob",
        created_by=message.from_user.id if message.from_user else 0,
        payload=payload
    )
    
    await safe_reply(
        message,
        "⚡ <b>Tez Hisob O'yini boshlandi!</b>\n\n"
        f"Misol: <b>{payload['task']} = ?</b>\n\n"
        "Birinchi bo'lib to'g'ri javobni yozgan o'yinchi yutadi! (Vaqt: 30s)"
    )
    
    # Auto-finish after 30 seconds
    async def finish_math_timeout():
        await asyncio.sleep(30)
        game = await game_dao.get_active_game(chat_id)
        if game and game["id"] == session_id and game["status"] != "finished":
            await game_dao.finish_game_session(session_id)
            await bot.send_message(chat_id, f"⏱ Vaqt tugadi! To'g'ri javob <b>{answer}</b> edi.")

    asyncio.create_task(finish_math_timeout())


# ══════════════════════════════════════════════════════════
# CATCH GAME INPUTS
# ══════════════════════════════════════════════════════════

@router.message(F.text.regexp(r'^-?\d+$'))
async def process_number_input(message: Message):
    """Catch numbers for Raqam Top and Tez Hisob."""
    from aiogram.dispatcher.event.exceptions import SkipHandler
    chat_id = message.chat.id
    
    active_game = await game_dao.get_active_game(chat_id)
    if not active_game or active_game["game_type"] not in ["raqam_top", "tez_hisob"]:
        raise SkipHandler() # Let it fall through to other handlers

    user_val = int(message.text)
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    payload = active_game["payload"]
    
    if active_game["game_type"] == "raqam_top":
        secret = payload.get("secret")
        attempts = payload.get("attempts", 0) + 1
        
        if user_val == secret:
            await game_dao.finish_game_session(active_game["id"])
            await game_dao.add_game_points(chat_id, user_id, user_name, points=10, won=1)
            await safe_reply(message, f"🎉 <b>Tabriklaymiz, {user_name}!</b>\n\nSiz raqamni topdingiz: <b>{secret}</b>!\n(+10 ball)")
        else:
            if attempts >= payload.get("max_attempts", 10):
                await game_dao.finish_game_session(active_game["id"])
                await safe_reply(message, f"😔 Imkoniyatlar tugadi!\nMen o'ylagan raqam <b>{secret}</b> edi.")
            else:
                payload["attempts"] = attempts
                await game_dao.update_game_session(active_game["id"], "waiting", payload)
                
                hint = "📈 Kattaroq" if user_val < secret else "📉 Kichikroq"
                await safe_reply(message, f"{hint} raqam o'yladim. (Urinishlar: {attempts}/{payload.get('max_attempts', 10)})")
                
    elif active_game["game_type"] == "tez_hisob":
        answer = payload.get("answer")
        
        if user_val == answer:
            await game_dao.finish_game_session(active_game["id"])
            await game_dao.add_game_points(chat_id, user_id, user_name, points=15, won=1)
            await safe_reply(message, f"⚡ <b>Qoyil, {user_name}!</b>\n\nSiz birinchi bo'lib to'g'ri javobni topdingiz: <b>{answer}</b>!\n(+15 ball)")
        else:
            await safe_reply(message, "❌ Xato javob!")
