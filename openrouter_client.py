import logging
import os
from typing import Dict, List, Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "sk-or-v1-REPLACE_WITH_YOUR_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")


SYSTEM_PROMPTS = {
    "check": (
        "Sen ingliz tili o'qituvchisisan. Foydalanuvchi matn yuboradi. "
        "Grammatik xatolarni top, qisqa va aniq o'zbekcha izoh ber, "
        "to'g'ri variantni chiqar."
    ),
    "general": (
        "Sen English teacher botsan. O'zbek tilida sodda, tushunarli va motivatsion javob ber. "
        "Kerak bo'lsa misollar bilan tushuntir."
    ),
    "translate": (
        "Sen tarjimon-o'qituvchisan. Inglizcha matnni o'zbekchaga tarjima qil, "
        "keyin 1-2 jumlada izoh ber."
    ),
    "rule": (
        "Sen grammatika mentori. Qoida so'ralganda jadvalga o'xshash tartib bilan, "
        "misollar bilan tushuntir."
    ),
    "lesson": (
        "Sen ingliz tili online teacher botsan. Berilgan mavzu bo'yicha mini dars tuz: "
        "10 ta so'z, 5 ta gap, 3 ta mashq (javoblari bilan). Hammasi o'zbekcha izohli bo'lsin."
    ),
    "uz_to_en": (
        "Foydalanuvchi o'zbekcha gap yuboradi. Inglizcha tabiiy variantni yoz, "
        "keyin qisqa grammatik izoh ber va alternativ variant ham taklif qil."
    ),
    "pronunciation": (
        "Berilgan inglizcha so'z uchun IPA yozuvi, bo'g'inlarga ajratish, "
        "o'zbekcha talaffuzga yaqin yo'riqnoma ber."
    ),
    "auto": (
        "Foydalanuvchi matnini niyatiga qarab tahlil qil: "
        "savol bo'lsa javob ber, xato bo'lsa tekshir, tarjima kerak bo'lsa tarjima qil. "
        "Har doim o'zbek tilida, aniq va foydali javob yoz."
    ),
}


def _build_messages(
    user_text: str,
    mode: str,
    context: Optional[List[Dict[str, str]]] = None,
) -> List[Dict[str, str]]:
    system_prompt = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS["auto"])
    messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]

    if context:
        for item in context[-8:]:
            role = item.get("role", "")
            content = item.get("content", "")
            if role in {"user", "assistant"} and content:
                messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": user_text})
    return messages


async def ask_ai(
    text: str,
    mode: str = "auto",
    context: Optional[List[Dict[str, str]]] = None,
    max_tokens: int = 1024,
    temperature: float = 0.3,
) -> str:
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://t.me/artificial_teacher_bot",
        "X-Title": "Artificial Teacher Bot",
    }

    payload = {
        "model": MODEL,
        "messages": _build_messages(text, mode, context=context),
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    try:
        async with httpx.AsyncClient(timeout=35.0) as client:
            response = await client.post(OPENROUTER_URL, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
    except httpx.TimeoutException:
        logger.error("OpenRouter timeout")
        return "AI javobi kechikdi (timeout). Iltimos qayta urinib ko'ring."
    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        logger.error("OpenRouter HTTP error %s: %s", code, exc.response.text)
        if code == 401:
            return "API kalit noto'g'ri yoki muddati tugagan."
        if code == 429:
            return "So'rovlar limiti tugadi. Bir oz kutib qayta urinib ko'ring."
        return "AI servisi bilan bog'lanishda xato bo'ldi."
    except Exception as exc:
        logger.error("Unexpected AI error: %s", exc)
        return "Texnik xato yuz berdi. Keyinroq qayta urinib ko'ring."
