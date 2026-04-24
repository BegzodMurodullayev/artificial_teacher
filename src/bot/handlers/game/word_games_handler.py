import logging
import random
import asyncio

from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.filters import Command

from src.database.dao import game_dao
from src.bot.utils.telegram import safe_reply

logger = logging.getLogger(__name__)
router = Router(name="word_games")

FALLBACK_WORD_CHALLENGES = [
    {"word": "happy", "type": "sinonim", "answers": ["glad", "joyful", "cheerful"]},
    {"word": "big", "type": "sinonim", "answers": ["large", "huge", "great"]},
    {"word": "difficult", "type": "antonim", "answers": ["easy", "simple"]},
    {"word": "fast", "type": "antonim", "answers": ["slow"]},
]

FALLBACK_TRANSLATION_CHALLENGES = [
    {"uz": "Men har kuni ingliz tilini mashq qilaman.", "answers": ["i practice english every day", "i practise english every day"]},
    {"uz": "U hozir kitob o'qiyapti.", "answers": ["she is reading a book now", "he is reading a book now"]},
    {"uz": "Biz ertaga maktabga boramiz.", "answers": ["we will go to school tomorrow", "we are going to school tomorrow"]},
    {"uz": "Bu savol juda qiziq ekan.", "answers": ["this question is very interesting", "it is a very interesting question"]},
]


def _normalize_answers(items: list[str]) -> list[str]:
    return [str(ans).lower().replace(".", "").replace("?", "").replace("!", "").strip() for ans in items]


def _fallback_word_challenge() -> dict:
    return random.choice(FALLBACK_WORD_CHALLENGES).copy()


def _fallback_translation_challenge() -> dict:
    return random.choice(FALLBACK_TRANSLATION_CHALLENGES).copy()

# ══════════════════════════════════════════════════════════
# SO'Z TOPISH
# ══════════════════════════════════════════════════════════

@router.message(Command(commands=["soztopish", "wordgame"]))
async def cmd_soz_topish(message: Message, bot: Bot):
    """Start a word game (synonyms/antonyms)."""
    logger.info("cmd_soz_topish TRIGGERED by user_id=%s", message.from_user.id if message.from_user else 0)
    chat_id = message.chat.id
    
    active_game = await game_dao.get_active_game(chat_id)
    if active_game:
        await safe_reply(message, f"⚠️ Bu chatda allaqachon o'yin ketyapti! (Turi: {active_game['game_type']})")
        return

    msg = await safe_reply(message, "⏳ <i>O'yin tayyorlanmoqda...</i>")
    if not msg:
        return
        
    from src.services import ai_service
    from src.bot.utils.telegram import safe_edit
    word_data = await ai_service.ask_json("Give me a word game challenge.", mode="game_word")
    
    if not word_data or "word" not in word_data or "answers" not in word_data:
        word_data = _fallback_word_challenge()
        
    payload = {
        "word": word_data["word"],
        "type": word_data.get("type", "sinonim"),
        "answers": _normalize_answers(word_data["answers"])
    }
    
    session_id = await game_dao.create_game_session(
        chat_id=chat_id,
        game_type="soz_topish",
        created_by=message.from_user.id if message.from_user else 0,
        payload=payload
    )
    
    await safe_edit(
        msg,
        f"🔤 <b>So'z Topish O'yini!</b>\n\n"
        f"Quyidagi so'zning <b>{payload['type']}</b>ini ingliz tilida yozing:\n"
        f"👉 <b>{payload['word']}</b>\n\n"
        "Vaqt: 30 soniya."
    )
    
    async def finish_word_timeout():
        await asyncio.sleep(30)
        game = await game_dao.get_active_game(chat_id)
        if game and game["id"] == session_id and game["status"] != "finished":
            await game_dao.finish_game_session(session_id)
            ans_str = ", ".join(payload["answers"])
            await bot.send_message(chat_id, f"⏱ Vaqt tugadi!\nTo'g'ri javoblar bo'lishi mumkin edi: <b>{ans_str}</b>.")

    asyncio.create_task(finish_word_timeout())


# ══════════════════════════════════════════════════════════
# TARJIMA POYGASI
# ══════════════════════════════════════════════════════════

@router.message(Command(commands=["tarjimapoyga", "translategame"]))
async def cmd_tarjima_poyga(message: Message, bot: Bot):
    """Start a translation game."""
    logger.info("cmd_tarjima_poyga TRIGGERED by user_id=%s", message.from_user.id if message.from_user else 0)
    chat_id = message.chat.id
    
    active_game = await game_dao.get_active_game(chat_id)
    if active_game:
        await safe_reply(message, f"⚠️ Bu chatda allaqachon o'yin ketyapti! (Turi: {active_game['game_type']})")
        return

    msg = await safe_reply(message, "⏳ <i>O'yin tayyorlanmoqda...</i>")
    if not msg:
        return
        
    from src.services import ai_service
    from src.bot.utils.telegram import safe_edit
    phrase_data = await ai_service.ask_json("Give me a translation game challenge.", mode="game_translation")
    
    if not phrase_data or "uz" not in phrase_data or "answers" not in phrase_data:
        phrase_data = _fallback_translation_challenge()
        
    payload = {
        "uz": phrase_data["uz"],
        "answers": _normalize_answers(phrase_data["answers"])
    }
    
    session_id = await game_dao.create_game_session(
        chat_id=chat_id,
        game_type="tarjima_poygasi",
        created_by=message.from_user.id if message.from_user else 0,
        payload=payload
    )
    
    await safe_edit(
        msg,
        f"🏃 <b>Tarjima Poygasi!</b>\n\n"
        f"Quyidagi gapni ingliz tiliga tarjima qiling:\n"
        f"👉 <b>{payload['uz']}</b>\n\n"
        "Vaqt: 45 soniya."
    )
    
    async def finish_trans_timeout():
        await asyncio.sleep(45)
        game = await game_dao.get_active_game(chat_id)
        if game and game["id"] == session_id and game["status"] != "finished":
            await game_dao.finish_game_session(session_id)
            ans_str = phrase_data["answers"][0] if phrase_data["answers"] else "Noma'lum"
            await bot.send_message(chat_id, f"⏱ Vaqt tugadi!\nTo'g'ri tarjima: <b>{ans_str}</b>.")

    asyncio.create_task(finish_trans_timeout())


# ══════════════════════════════════════════════════════════
# CATCH GAME INPUTS
# ══════════════════════════════════════════════════════════

async def is_word_game_active(message: Message) -> bool:
    """Filter to check if a word game is active in this chat."""
    if not message.text or message.text.startswith("/"):
        return False
    
    # Do not catch menu buttons
    from src.bot.keyboards.user_menu import resolve_menu_action
    if resolve_menu_action(message.text):
        return False

    active_game = await game_dao.get_active_game(message.chat.id)
    return active_game is not None and active_game["game_type"] in ["soz_topish", "tarjima_poygasi"]

@router.message(is_word_game_active)
async def process_word_input(message: Message):
    """Catch words for So'z Topish and Tarjima."""
    chat_id = message.chat.id
    active_game = await game_dao.get_active_game(chat_id)
    if not active_game:
        return
        
    user_val = message.text.lower().strip().replace(".", "").replace("?", "").replace("!", "")
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    payload = active_game["payload"]
    answers = payload.get("answers", [])
    
    if active_game["game_type"] == "soz_topish":
        if user_val in answers:
            await game_dao.finish_game_session(active_game["id"])
            await game_dao.add_game_points(chat_id, user_id, user_name, points=10, won=1)
            await safe_reply(message, f"🎉 <b>Qoyil, {user_name}!</b>\n\nTo'g'ri so'z topdingiz: <b>{message.text}</b>\n(+10 ball)")

    elif active_game["game_type"] == "tarjima_poygasi":
        if user_val in answers:
            await game_dao.finish_game_session(active_game["id"])
            await game_dao.add_game_points(chat_id, user_id, user_name, points=15, won=1)
            await safe_reply(message, f"🏆 <b>Ajoyib, {user_name}!</b>\n\nTo'g'ri tarjima qildingiz!\n(+15 ball)")
