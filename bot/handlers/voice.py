"""
handlers/voice.py — Ovozli xabarni matnga aylantirish + grammatik tekshiruv
Whisper API (OpenAI) ishlatiladi
"""
import os
import httpx
import logging
import tempfile
from telegram import Update
from telegram.ext import ContextTypes
from utils.ai import ask_ai
from database.db import upsert_user, inc_stat

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
# Agar OpenAI kaliti bo'lmasa, OpenRouter orqali ham urinib ko'ramiz
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")


async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ovozli yoki audio xabarni qabul qilish"""
    user = update.effective_user
    upsert_user(user.id, user.username, user.first_name)
    message = update.message

    voice = message.voice or message.audio
    if not voice:
        return

    await message.reply_text("🎙️ Ovozli xabar qabul qilindi. Aylantirmoqda...")

    # Faylni yuklab olish
    try:
        file = await context.bot.get_file(voice.file_id)
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            tmp_path = tmp.name
        await file.download_to_drive(tmp_path)
    except Exception as e:
        logger.error(f"Fayl yuklab olishda xato: {e}")
        await message.reply_text("❌ Ovozli xabarni yuklab bo'lmadi.")
        return

    # Whisper API
    transcript = await transcribe_audio(tmp_path)

    # Vaqtinchalik faylni o'chirish
    try:
        os.unlink(tmp_path)
    except Exception:
        pass

    if not transcript:
        await message.reply_text(
            "❌ Ovozni matnga aylantirish muvaffaqiyatsiz.\n\n"
            "💡 *Sabab:* OpenAI Whisper API kaliti kerak.\n"
            "`.env` fayliga `OPENAI_API_KEY=...` qo'shing.",
            parse_mode="Markdown"
        )
        return

    await message.reply_text(
        f"📝 *Matnga aylandi:*\n\n_{transcript}_\n\n"
        "🔍 Grammatik tekshirilmoqda...",
        parse_mode="Markdown"
    )

    # Grammatik tekshiruv
    check_result = await ask_ai(transcript, mode="check", user_id=user.id)
    await message.reply_text(check_result, parse_mode="Markdown")
    inc_stat(user.id, "checks_total")
    inc_stat(user.id, "messages_total")


async def transcribe_audio(file_path: str) -> str | None:
    """OpenAI Whisper API orqali ovozni matnga aylantirish"""
    api_key = OPENAI_API_KEY or OPENROUTER_API_KEY
    if not api_key:
        return None

    url = "https://api.openai.com/v1/audio/transcriptions"

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            with open(file_path, "rb") as f:
                files = {"file": ("audio.ogg", f, "audio/ogg")}
                data = {"model": "whisper-1", "language": "en"}
                headers = {"Authorization": f"Bearer {api_key}"}
                resp = await client.post(url, files=files, data=data, headers=headers)
                resp.raise_for_status()
                return resp.json().get("text", "")
    except Exception as e:
        logger.error(f"Whisper xato: {e}")
        return None