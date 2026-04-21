"""
Unified message handler (Smart Router).
Handles text, voice messages, intent detection, and mode switching.
"""

import re
import logging

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message

from src.services import ai_teacher_service, mode_manager, transcription_service, ai_service
from src.bot.handlers.user.check import process_grammar_check
from src.bot.handlers.user.translate import process_translation
from src.bot.utils.telegram import safe_reply, escape_html
from src.database.dao.history_dao import add_history
from src.database.dao import stats_dao

logger = logging.getLogger(__name__)
router = Router(name="user_message")

# ══════════════════════════════════════════════════════════
# MODE COMMANDS
# ══════════════════════════════════════════════════════════

@router.message(Command("teacher", "translate", "correct", "tech", "cancel"))
async def handle_mode_commands(message: Message, db_user: dict | None = None):
    if not db_user:
        return

    cmd = message.text.split()[0][1:].lower()
    user_id = message.from_user.id

    if cmd == "cancel":
        await mode_manager.clear_mode(user_id)
        await safe_reply(message, "🔄 Rejim bekor qilindi. Endi bot avtomatik rejimda ishlaydi.")
        return

    mode_map = {
        "teacher": "TEACHER",
        "translate": "TRANSLATION",
        "correct": "CORRECTION",
        "tech": "TECHNICAL"
    }

    selected_mode = mode_map.get(cmd)
    if selected_mode:
        await mode_manager.set_mode(user_id, selected_mode)
        await safe_reply(message, f"✅ <b>{selected_mode}</b> rejimi yoqildi.\nO'chirish uchun /cancel tugmasini bosing.")


# ══════════════════════════════════════════════════════════
# MAIN MESSAGE HANDLER
# ══════════════════════════════════════════════════════════

@router.message(F.text | F.voice)
async def smart_message_handler(message: Message, bot: Bot, db_user: dict | None = None):
    """
    Catch-all handler for text and voice.
    Routes messages to grammar check, translation, or AI teacher based on mode or intent.
    Must be registered LAST.
    """
    if not db_user:
        return

    user_id = db_user["user_id"]
    level = db_user.get("level", "A1")

    # ── 1. Process Voice ──
    text = ""
    is_voice = False
    if message.voice:
        is_voice = True
        duration = message.voice.duration
        await message.chat.do("record_voice")

        transcript = await transcription_service.transcribe_voice(
            bot=bot,
            file_id=message.voice.file_id,
            duration=duration,
        )
        if not transcript:
            await safe_reply(message, "❌ Ovozli xabarni tanib bo'lmadi yoki u juda uzun (max 60s).")
            return

        await stats_dao.inc_stat(user_id, "voice_total")
        text = transcript
        await safe_reply(message, f"🎙 <i>{escape_html(text)}</i>")
    elif message.text:
        text = message.text

    if not text:
        return

    # Skip menu button texts
    from src.bot.keyboards.user_menu import resolve_menu_action
    if resolve_menu_action(text):
        return

    # Skip commands
    if text.startswith("/"):
        return

    await stats_dao.inc_stat(user_id, "messages_total")

    # ── 2. Save to history ──
    await add_history(user_id, role="user", content=text)

    # ── 3. Determine Mode ──
    current_mode = await mode_manager.get_mode(user_id)
    selected_mode = current_mode

    if not selected_mode:
        # Rule-based Intent Routing
        text_lower = text.lower()
        is_latin = bool(re.search(r'[a-zA-Z]', text))
        is_cyrillic = bool(re.search(r'[а-яА-Я]', text))
        
        # Support/Bot questions
        bot_keywords = ["bot", "nima", "qanday", "yordam", "ishla", "kim", "qil", "salom", "qanaqa"]
        
        if len(text.split()) > 100 or "def " in text or "```" in text:
            selected_mode = "TECHNICAL"
        elif any(kw in text_lower for kw in bot_keywords) and len(text.split()) < 10:
            selected_mode = "SUPPORT"
        elif is_latin and not is_cyrillic and len(text.split()) >= 1:
            selected_mode = "CORRECTION"
        else:
            selected_mode = "UNCLEAR"

    logger.info("Routing user=%s mode=%s text=%.60s", user_id, selected_mode, text)

    # ── 4. Route ──
    await message.chat.do("typing")

    if selected_mode == "TEACHER":
        response = await ai_teacher_service.ask_teacher(text, user_id)
        await safe_reply(message, response)
        await add_history(user_id, role="assistant", content=response)

    elif selected_mode == "TRANSLATION":
        is_latin = bool(re.search(r'[a-zA-Z]', text))
        is_cyrillic = bool(re.search(r'[а-яА-Я]', text))
        direction = "en_to_uz" if is_latin and not is_cyrillic else "uz_to_en"
        await process_translation(message, text, user_id, direction=direction, level=level)

    elif selected_mode == "PRONUNCIATION":
        from src.bot.handlers.user.pronunciation import process_pronunciation
        await process_pronunciation(message, text, user_id)

    elif selected_mode in ("TECHNICAL", "SUPPORT"):
        response = await ai_service.ask_ai(text, mode="bot", user_id=user_id, level=level)
        await safe_reply(message, response)
        
    elif selected_mode == "CORRECTION":
        await process_grammar_check(message, text, user_id, level)
        
    else:
        # UNCLEAR
        from src.bot.keyboards.user_menu import edu_menu
        await safe_reply(
            message, 
            "🤔 Tushunmadim, sizga qanday yordam bera olaman?\n\n"
            "Iltimos, kerakli rejimni tanlang:\n"
            "• Tarjima (Matn yuboring va /translate)\n"
            "• Xatolarni tekshirish (Inglizcha yuboring)\n"
            "• Suhbat (/teacher)\n\n"
            "Yoki menyudan tanlang:",
            reply_markup=edu_menu()
        )
