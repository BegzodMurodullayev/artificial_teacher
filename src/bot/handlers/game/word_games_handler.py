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

WORDS_DB = [
    {"word": "beautiful", "type": "sinonim", "answers": ["pretty", "gorgeous", "lovely", "attractive"]},
    {"word": "big", "type": "antonim", "answers": ["small", "tiny", "little"]},
    {"word": "fast", "type": "sinonim", "answers": ["quick", "rapid", "swift"]},
    {"word": "good", "type": "antonim", "answers": ["bad", "awful", "terrible", "poor"]},
    {"word": "smart", "type": "sinonim", "answers": ["clever", "intelligent", "bright", "brilliant"]},
    {"word": "hot", "type": "antonim", "answers": ["cold", "cool", "freezing"]},
    {"word": "happy", "type": "sinonim", "answers": ["glad", "joyful", "cheerful"]},
    {"word": "hard", "type": "antonim", "answers": ["easy", "simple", "soft"]},
]

TRANSLATION_DB = [
    {"uz": "Men maktabga boraman.", "en": ["I go to school.", "I am going to school."]},
    {"uz": "U juda aqlli qiz.", "en": ["She is a very smart girl.", "She is a very intelligent girl."]},
    {"uz": "Biz kecha kitob o'qidik.", "en": ["We read a book yesterday."]},
    {"uz": "Sen qachon kelasan?", "en": ["When will you come?", "When are you coming?"]},
    {"uz": "Menga olma yoqadi.", "en": ["I like apples.", "I love apples."]},
]

# ══════════════════════════════════════════════════════════
# SO'Z TOPISH
# ══════════════════════════════════════════════════════════

@router.message(Command(commands=["soztopish", "wordgame"]))
async def cmd_soz_topish(message: Message, bot: Bot):
    """Start a word game (synonyms/antonyms)."""
    chat_id = message.chat.id
    
    active_game = await game_dao.get_active_game(chat_id)
    if active_game:
        await safe_reply(message, f"⚠️ Bu chatda allaqachon o'yin ketyapti! (Turi: {active_game['game_type']})")
        return

    word_data = random.choice(WORDS_DB)
    
    payload = {
        "word": word_data["word"],
        "type": word_data["type"],
        "answers": [ans.lower() for ans in word_data["answers"]]
    }
    
    session_id = await game_dao.create_game_session(
        chat_id=chat_id,
        game_type="soz_topish",
        created_by=message.from_user.id if message.from_user else 0,
        payload=payload
    )
    
    await safe_reply(
        message,
        f"🔤 <b>So'z Topish O'yini!</b>\n\n"
        f"Quyidagi so'zning <b>{word_data['type']}</b>ini ingliz tilida yozing:\n"
        f"👉 <b>{word_data['word']}</b>\n\n"
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
    chat_id = message.chat.id
    
    active_game = await game_dao.get_active_game(chat_id)
    if active_game:
        await safe_reply(message, f"⚠️ Bu chatda allaqachon o'yin ketyapti! (Turi: {active_game['game_type']})")
        return

    phrase_data = random.choice(TRANSLATION_DB)
    
    payload = {
        "uz": phrase_data["uz"],
        "answers": [ans.lower().replace(".", "").replace("?", "").replace("!", "") for ans in phrase_data["en"]]
    }
    
    session_id = await game_dao.create_game_session(
        chat_id=chat_id,
        game_type="tarjima_poygasi",
        created_by=message.from_user.id if message.from_user else 0,
        payload=payload
    )
    
    await safe_reply(
        message,
        f"🏃 <b>Tarjima Poygasi!</b>\n\n"
        f"Quyidagi gapni ingliz tiliga tarjima qiling:\n"
        f"👉 <b>{phrase_data['uz']}</b>\n\n"
        "Vaqt: 45 soniya."
    )
    
    async def finish_trans_timeout():
        await asyncio.sleep(45)
        game = await game_dao.get_active_game(chat_id)
        if game and game["id"] == session_id and game["status"] != "finished":
            await game_dao.finish_game_session(session_id)
            ans_str = phrase_data["en"][0]
            await bot.send_message(chat_id, f"⏱ Vaqt tugadi!\nTo'g'ri tarjima: <b>{ans_str}</b>.")

    asyncio.create_task(finish_trans_timeout())


# ══════════════════════════════════════════════════════════
# CATCH GAME INPUTS
# ══════════════════════════════════════════════════════════

@router.message(F.text & ~F.text.startswith("/"))
async def process_word_input(message: Message):
    """Catch words for So'z Topish and Tarjima."""
    from aiogram.dispatcher.event.exceptions import SkipHandler
    chat_id = message.chat.id
    
    active_game = await game_dao.get_active_game(chat_id)
    if not active_game or active_game["game_type"] not in ["soz_topish", "tarjima_poygasi"]:
        raise SkipHandler() # Let it fall through
        
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
