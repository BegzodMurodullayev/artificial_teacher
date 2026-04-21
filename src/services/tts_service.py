"""
TTS Service — TopMediaI text-to-speech integration.
Ported from utils/tts.py with async support and concurrency control.
"""

import asyncio
import io
import logging
import time
from typing import Optional

import httpx

from src.config import settings

logger = logging.getLogger(__name__)

_tts_semaphore: asyncio.Semaphore | None = None


def _get_semaphore() -> asyncio.Semaphore:
    global _tts_semaphore
    if _tts_semaphore is None:
        _tts_semaphore = asyncio.Semaphore(settings.TTS_CONCURRENCY)
    return _tts_semaphore


# Voice ID mappings
VOICE_IDS = {
    "us_male":   "en-US-ChristopherNeural",
    "us_female": "en-US-JennyNeural",
    "uk_male":   "en-GB-RyanNeural",
    "uk_female": "en-GB-SoniaNeural",
}

DEFAULT_VOICE = "us_female"


async def synthesize_pronunciation(
    text: str,
    accent: str = "us",
    gender: str = "female",
) -> Optional[bytes]:
    """
    Synthesize speech audio for the given text.
    Returns raw audio bytes (MP3) or None on failure.
    """
    if not settings.TOPMEDIAI_API_KEY:
        logger.warning("TOPMEDIAI_API_KEY not set, skipping TTS")
        return None

    voice_key = f"{accent}_{gender}"
    voice_id = VOICE_IDS.get(voice_key, VOICE_IDS[DEFAULT_VOICE])
    sem = _get_semaphore()

    async with sem:
        try:
            # Step 1: Submit synthesis job
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{settings.TOPMEDIAI_API_BASE}/tts",
                    headers={
                        "Authorization": f"Bearer {settings.TOPMEDIAI_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "text": text[:500],  # Limit text length
                        "voice_id": voice_id,
                        "format": "mp3",
                    },
                )
                response.raise_for_status()
                data = response.json()

            # Handle different API response formats
            audio_url = None
            if isinstance(data, dict):
                audio_url = data.get("data", {}).get("audio_url") or data.get("audio_url")

                # If we got direct audio data
                if data.get("data", {}).get("audio"):
                    import base64
                    return base64.b64decode(data["data"]["audio"])

            if not audio_url:
                # Maybe polling is needed
                task_id = data.get("data", {}).get("task_id") or data.get("task_id")
                if task_id:
                    audio_url = await _poll_tts_result(task_id)

            if not audio_url:
                logger.warning("No audio URL in TTS response: %s", str(data)[:200])
                return None

            # Step 2: Download audio
            async with httpx.AsyncClient(timeout=20) as client:
                audio_response = await client.get(audio_url)
                audio_response.raise_for_status()
                return audio_response.content

        except httpx.TimeoutException:
            logger.warning("TTS timeout for text: %.50s", text)
            return None
        except Exception as e:
            logger.exception("TTS error: %s", e)
            return None


async def _poll_tts_result(task_id: str, max_wait: int = 30) -> Optional[str]:
    """Poll for TTS result using task ID."""
    start = time.monotonic()
    async with httpx.AsyncClient(timeout=10) as client:
        while time.monotonic() - start < max_wait:
            try:
                response = await client.get(
                    f"{settings.TOPMEDIAI_API_BASE}/tts/result",
                    params={"task_id": task_id},
                    headers={"Authorization": f"Bearer {settings.TOPMEDIAI_API_KEY}"},
                )
                data = response.json()
                status = data.get("data", {}).get("status") or data.get("status")

                if status == "completed":
                    return data.get("data", {}).get("audio_url") or data.get("audio_url")
                elif status == "failed":
                    logger.warning("TTS task %s failed", task_id)
                    return None

            except Exception as e:
                logger.warning("TTS poll error: %s", e)

            await asyncio.sleep(1.5)

    logger.warning("TTS poll timeout for task %s", task_id)
    return None


def make_audio_file(audio_bytes: bytes, filename: str = "pronunciation.mp3") -> io.BytesIO:
    """Wrap audio bytes in a BytesIO object for Telegram sending."""
    buf = io.BytesIO(audio_bytes)
    buf.name = filename
    buf.seek(0)
    return buf
