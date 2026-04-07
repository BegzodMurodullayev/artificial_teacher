"""TopMediaI TTS helpers for pronunciation audio."""
import asyncio
import base64
import logging
import os
import re
from io import BytesIO
from typing import Any

import httpx
from utils.content_bank import moderation_warning

logger = logging.getLogger(__name__)


def _env_text(name: str, default: str = "") -> str:
    return str(os.getenv(name, default) or default).strip().strip('"').strip("'")


def _env_int(name: str, default: int) -> int:
    try:
        return int(_env_text(name, str(default)) or default)
    except ValueError:
        return int(default)


def _env_float(name: str, default: float) -> float:
    try:
        return float(_env_text(name, str(default)) or default)
    except ValueError:
        return float(default)


TOPMEDIAI_API_KEY = _env_text("TOPMEDIAI_API_KEY", "")
TOPMEDIAI_API_BASE = _env_text("TOPMEDIAI_API_BASE", "https://api.topmediai.com/v1").rstrip("/")
TOPMEDIAI_SPEAKER_US = _env_text("TOPMEDIAI_SPEAKER_US", "")
TOPMEDIAI_SPEAKER_UK = _env_text("TOPMEDIAI_SPEAKER_UK", "")
TOPMEDIAI_AUDIO_FORMAT = _env_text("TOPMEDIAI_AUDIO_FORMAT", "mp3").lower() or "mp3"

_CLIENT = None
_TIMEOUT = httpx.Timeout(_env_float("TTS_REQUEST_TIMEOUT", 45.0), connect=_env_float("TTS_CONNECT_TIMEOUT", 10.0))
_LIMITS = httpx.Limits(max_connections=_env_int("TTS_MAX_CONNECTIONS", 25), max_keepalive_connections=_env_int("TTS_KEEPALIVE_CONNECTIONS", 15))
_TTS_CONCURRENCY = _env_int("TTS_CONCURRENCY", 10)
_TTS_WAIT_SEC = _env_float("TTS_QUEUE_WAIT_SEC", 10)
_TTS_SEMAPHORE = asyncio.Semaphore(max(1, _TTS_CONCURRENCY))

_VOICE_CACHE: dict[str, Any] = {"ts": 0.0, "voices": []}
_VOICE_CACHE_TTL = 30 * 60


def _now() -> float:
    return asyncio.get_running_loop().time()


async def _get_client():
    global _CLIENT
    if _CLIENT is None or _CLIENT.is_closed:
        _CLIENT = httpx.AsyncClient(timeout=_TIMEOUT, limits=_LIMITS, follow_redirects=True)
    return _CLIENT


def _headers() -> dict[str, str]:
    return {
        "x-api-key": TOPMEDIAI_API_KEY,
        "Content-Type": "application/json",
    }


def _looks_english_voice(row: dict[str, Any]) -> bool:
    blob = " ".join(
        [
            str(row.get("Languagename", "")),
            str(row.get("name", "")),
            str(row.get("urlname", "")),
            str(row.get("classification", "")),
            str(row.get("classnamearray", "")),
            str(row.get("describe", "")),
        ]
    ).lower()
    return ("english" in blob) or ("en-" in blob) or ("en_" in blob) or (" eng " in f" {blob} ")


def _score_voice_for_accent(row: dict[str, Any], accent: str) -> int:
    blob = " ".join(
        [
            str(row.get("Languagename", "")),
            str(row.get("name", "")),
            str(row.get("urlname", "")),
            str(row.get("classification", "")),
            str(row.get("classnamearray", "")),
            str(row.get("describe", "")),
        ]
    ).lower()
    score = 0
    if not _looks_english_voice(row):
        return -1000
    score += 10
    if accent == "uk":
        if any(token in blob for token in ("uk", "british", "en-gb", "en_gb", "england")):
            score += 25
    else:
        if any(token in blob for token in ("us", "american", "en-us", "en_us", "united states")):
            score += 25
    if row.get("isFree"):
        score += 3
    if not row.get("isvip"):
        score += 2
    if "female" in blob:
        score += 1
    return score


async def _fetch_voices() -> list[dict[str, Any]]:
    if not TOPMEDIAI_API_KEY:
        return []
    now = _now()
    if _VOICE_CACHE["voices"] and now - float(_VOICE_CACHE["ts"]) < _VOICE_CACHE_TTL:
        return list(_VOICE_CACHE["voices"])
    client = await _get_client()
    resp = await client.get(f"{TOPMEDIAI_API_BASE}/voices_list", headers={"x-api-key": TOPMEDIAI_API_KEY})
    resp.raise_for_status()
    data = resp.json() if "application/json" in resp.headers.get("content-type", "") else {}
    voices = data.get("Voice", []) if isinstance(data, dict) else []
    if isinstance(voices, list):
        _VOICE_CACHE["voices"] = voices
        _VOICE_CACHE["ts"] = now
        return voices
    return []


async def _pick_speaker(accent: str) -> str | None:
    if accent == "uk" and TOPMEDIAI_SPEAKER_UK:
        return TOPMEDIAI_SPEAKER_UK
    if accent == "us" and TOPMEDIAI_SPEAKER_US:
        return TOPMEDIAI_SPEAKER_US

    voices = await _fetch_voices()
    if not voices:
        return TOPMEDIAI_SPEAKER_US or TOPMEDIAI_SPEAKER_UK or None
    ranked = sorted(voices, key=lambda row: _score_voice_for_accent(row, accent), reverse=True)
    best = ranked[0] if ranked else {}
    speaker = str(best.get("speaker", "")).strip()
    return speaker or (TOPMEDIAI_SPEAKER_US if accent == "us" else TOPMEDIAI_SPEAKER_UK) or None


def _iter_strings(obj: Any):
    if isinstance(obj, dict):
        for k, v in obj.items():
            for p, s in _iter_strings(v):
                yield f"{k}.{p}" if p else str(k), s
    elif isinstance(obj, list):
        for idx, v in enumerate(obj):
            for p, s in _iter_strings(v):
                yield f"{idx}.{p}" if p else str(idx), s
    elif isinstance(obj, str):
        yield "", obj


def _extract_audio_url(payload: Any) -> str | None:
    urls = []
    for path, text in _iter_strings(payload):
        if text.startswith("http://") or text.startswith("https://"):
            score = 0
            low = text.lower()
            if any(ext in low for ext in (".mp3", ".wav", ".ogg", ".m4a", ".aac")):
                score += 5
            if any(token in path.lower() for token in ("audio", "voice", "url", "file", "result")):
                score += 4
            if "audio" in low or "voice" in low:
                score += 2
            urls.append((score, text))
    if not urls:
        return None
    urls.sort(key=lambda x: x[0], reverse=True)
    return urls[0][1]


def _extract_audio_bytes(payload: Any) -> bytes | None:
    for path, text in _iter_strings(payload):
        low_path = path.lower()
        if text.startswith("data:audio") and ";base64," in text:
            raw = text.split(";base64,", 1)[1]
            try:
                return base64.b64decode(raw)
            except Exception:
                continue
        if any(token in low_path for token in ("audio", "base64", "content", "blob")):
            sample = text.strip()
            if re.fullmatch(r"[A-Za-z0-9+/=\s]{200,}", sample):
                try:
                    return base64.b64decode(sample)
                except Exception:
                    continue
    return None


async def synthesize_pronunciation(text: str, accent: str = "us") -> dict[str, Any]:
    if not TOPMEDIAI_API_KEY:
        return {"ok": False, "error": "missing_api_key"}
    clean_text = (text or "").strip()
    if not clean_text:
        return {"ok": False, "error": "empty_text"}
    if moderation_warning(clean_text):
        return {"ok": False, "error": "blocked"}
    if len(clean_text) > 500:
        clean_text = clean_text[:500]
    accent = "uk" if accent == "uk" else "us"

    try:
        await asyncio.wait_for(_TTS_SEMAPHORE.acquire(), timeout=_TTS_WAIT_SEC)
    except TimeoutError:
        return {"ok": False, "error": "busy"}

    try:
        speaker = await _pick_speaker(accent)
        if not speaker:
            return {"ok": False, "error": "speaker_not_found"}
        body = {
            "text": clean_text,
            "speaker": speaker,
            "emotion": "Neutral",
            # Request mp3 output explicitly (provider may ignore unknown keys).
            "audio_type": TOPMEDIAI_AUDIO_FORMAT,
            "output_format": TOPMEDIAI_AUDIO_FORMAT,
            "format": TOPMEDIAI_AUDIO_FORMAT,
        }
        client = await _get_client()
        resp = await client.post(f"{TOPMEDIAI_API_BASE}/text2speech", headers=_headers(), json=body)
        resp.raise_for_status()

        ctype = (resp.headers.get("content-type") or "").lower()
        if ctype.startswith("audio/"):
            ext = "mp3"
            if "wav" in ctype:
                ext = "wav"
            elif "ogg" in ctype:
                ext = "ogg"
            if TOPMEDIAI_AUDIO_FORMAT == "mp3":
                # Keep mp3 preference for downstream naming/sending.
                ext = "mp3"
            return {"ok": True, "audio": resp.content, "ext": ext, "speaker": speaker}

        payload = resp.json() if "application/json" in ctype else {}
        audio_blob = _extract_audio_bytes(payload)
        if audio_blob:
            return {"ok": True, "audio": audio_blob, "ext": "mp3", "speaker": speaker}
        url = _extract_audio_url(payload)
        if not url:
            return {"ok": False, "error": "no_audio_url"}

        audio_resp = await client.get(url)
        audio_resp.raise_for_status()
        ext = "mp3"
        path = url.lower()
        if ".wav" in path:
            ext = "wav"
        elif ".ogg" in path:
            ext = "ogg"
        if TOPMEDIAI_AUDIO_FORMAT == "mp3":
            ext = "mp3"
        return {"ok": True, "audio": audio_resp.content, "ext": ext, "speaker": speaker}
    except httpx.HTTPStatusError as e:
        code = e.response.status_code if e.response is not None else 500
        logger.error("TopMediaI HTTP error: %s", code)
        return {"ok": False, "error": f"http_{code}"}
    except httpx.RequestError as e:
        logger.error("TopMediaI request error: %s", e)
        return {"ok": False, "error": "request"}
    except Exception as e:
        logger.error("TopMediaI unknown error: %s", e)
        return {"ok": False, "error": "unknown"}
    finally:
        _TTS_SEMAPHORE.release()


def make_audio_file(audio_bytes: bytes, filename: str) -> BytesIO:
    buff = BytesIO(audio_bytes)
    buff.name = filename
    buff.seek(0)
    return buff
