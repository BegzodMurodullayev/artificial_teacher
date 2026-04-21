"""
Transcription Service using OpenAI Whisper API.
"""

import logging
import time
from typing import Optional
from io import BytesIO

from aiogram import Bot
import openai
from openai import AsyncOpenAI

from src.config import settings

logger = logging.getLogger(__name__)

# Initialize OpenAI client only if key is available
_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None


async def transcribe_voice(bot: Bot, file_id: str, duration: int) -> Optional[str]:
    """
    Downloads voice/audio file from Telegram and transcribes it using OpenAI Whisper.
    Limits transcription to 60 seconds (unless bypassed by caller).
    
    Returns:
        The transcribed text, or None if failed/too long.
    """
    if not _client:
        logger.error("OpenAI API key not set. Transcription service unavailable.")
        return None
        
    if duration > 60:
        logger.warning(f"Audio too long ({duration}s). Limit is 60s.")
        return None
        
    try:
        # 1. Download file into memory
        file_info = await bot.get_file(file_id)
        if not file_info.file_path:
            logger.error("Could not get file path from Telegram.")
            return None
            
        file_bytes = BytesIO()
        await bot.download_file(file_info.file_path, destination=file_bytes)
        
        # Whisper requires a filename with a recognized extension
        file_bytes.name = "voice.ogg" 
        
        # 2. Call OpenAI Whisper APi
        start_time = time.time()
        response = await _client.audio.transcriptions.create(
            model="whisper-1",
            file=file_bytes,
        )
        
        text = response.text.strip()
        logger.info(f"Transcribed {duration}s audio in {time.time() - start_time:.2f}s. Result: {len(text)} chars")
        
        return text
            
    except openai.OpenAIError as e:
        logger.error(f"Whisper API error: {e}")
        return None
    except Exception as e:
        logger.exception(f"Unexpected error in transcription: {e}")
        return None
