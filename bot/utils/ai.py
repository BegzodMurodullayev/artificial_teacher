"""utils/ai.py - OpenRouter AI client"""
import os
import httpx
import logging
import re
import json
import asyncio
from database.db import get_user, get_history, add_history
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


MODEL = _env_text("AI_MODEL", "openai/gpt-4o-mini")
OR_URL = "https://openrouter.ai/api/v1/chat/completions"

_CLIENT = None
_TIMEOUT = httpx.Timeout(_env_float("AI_REQUEST_TIMEOUT", 30.0), connect=_env_float("AI_CONNECT_TIMEOUT", 10.0))
_LIMITS = httpx.Limits(max_connections=_env_int("AI_MAX_CONNECTIONS", 50), max_keepalive_connections=_env_int("AI_KEEPALIVE_CONNECTIONS", 20))
_AI_CONCURRENCY = _env_int("AI_CONCURRENCY", 20)
_SEMAPHORE_WAIT_SEC = _env_float("AI_QUEUE_WAIT_SEC", 12)
_AI_SEMAPHORE = asyncio.Semaphore(max(1, _AI_CONCURRENCY))


async def _get_client():
    global _CLIENT
    if _CLIENT is None or _CLIENT.is_closed:
        _CLIENT = httpx.AsyncClient(timeout=_TIMEOUT, limits=_LIMITS)
    return _CLIENT


PROMPTS = {
    "check": """Sen ingliz tili o'qituvchisisiz. Foydalanuvchi darajasi: {level}.
Matnni grammatik tekshiring:
1. Har bir xatoni aniqlang va o'zbekcha tushuntiring
2. To'g'ri variantni ko'rsating
3. Oxirida qisqacha baho (A1-C2)
4. Daraja bahosida konservativ bo'l. Oddiy 1-2 ta xatolik uchun asossiz ravishda C1/C2 bermang.
5. Juda sodda xatolar bo'lsa, odatda A1 yoki A2 dan oshirmang.

Format:
Tahlil:
[xatolar yoki Xato topilmadi]

To'g'ri variant:
[matn]

Daraja taxmini: [A1-C2]
Asosiy qoida: [qisqacha]""",

    "general": "Sen ingliz tili o'qituvchisisiz. Daraja: {level}. O'zbekcha, do'stona, aniq javob ber.",

    "translate": """Tarjima yordamchisi bo'l.
Natijani quyidagi formatda ber:
Tarjima:
[asosiy tarjima]

Muqobil variantlar:
- ...
- ...

Qisqa izoh:
- ...
- ...""",

    "uz_to_en": """Foydalanuvchi o'zbekcha matn yuboradi. Uni inglizchaga tabiiy va grammatik to'g'ri tarjima qil.
Natijani quyidagi formatda ber:
Tarjima:
[asosiy inglizcha variant]

Muqobil variantlar:
- [1-2 ta foydali variant]

Qisqa izoh:
- [grammatik yoki uslubiy qisqa tushuntirish]
- [zarur bo'lsa 1 ta foydalanish eslatmasi]""",

    "en_to_uz": """Foydalanuvchi inglizcha matn yuboradi. Uni o'zbekchaga tabiiy va aniq tarjima qil.
Natijani quyidagi formatda ber:
Tarjima:
[asosiy o'zbekcha variant]

Muqobil variantlar:
- [1-2 ta foydali variant]

Qisqa izoh:
- [asosiy ma'no yoki grammatik izoh]
- [zarur bo'lsa kontekst eslatmasi]""",

    "pronunciation": """So'z talaffuzi:
1. IPA transkripsiyasi
2. O'zbekcha talaffuz yordami
3. Keng tarqalgan xatolar
4. Minimal juftlar bo'lmasa "Aniq minimal juft topilmadi." deb yoz
5. Keraksiz takrorlarni yozma""",

    "rule": "Grammatika qoidasini batafsil, misol va jadval bilan o'zbekcha tushuntir.",

    "quiz_generate": """Daraja: {level}. Real English learners uchun grammar/vocabulary quiz savoli yarat.
- Question and options must be in ENGLISH only.
- Avoid childish, too easy, or repetitive classroom clichés.
- Do NOT use the same question families repeatedly.
- Avoid questions about the exact sequence 2,4,8,16 or other IQ-style patterns.
- Make the question level-appropriate and practical.
- Explanation must be in Uzbek.
- Return ONLY JSON.
Schema:
{{"question":"...","options":["A) ...","B) ...","C) ...","D) ..."],"answer":"A","explanation":"o'zbekcha"}}""",

    "quiz_generate_strict": """Create one ENGLISH quiz question for level {level}.
- Question in English.
- Options in English only, exactly 4.
- Answer must be one letter: A/B/C/D.
- Do not repeat classic schoolbook wording if avoidable.
- No IQ pattern or number-sequence questions.
- Explanation in Uzbek.
- Return ONLY JSON.
Schema:
{{"question":"...","options":["A) ...","B) ...","C) ...","D) ..."],"answer":"A","explanation":"o'zbekcha"}}""",

    "quiz_generate_uz": """Daraja: {level}. Ingliz tilini o'rganayotganlar uchun quiz savoli yarat.
- Savol va yo'riqnoma O'ZBEKCHA bo'lsin.
- Variantlar o'quvchi uchun mantiqli va darajaga mos bo'lsin.
- Keraksiz IQ savollariga o'xshash yoki son ketma-ketligi savollarini bermang.
- Juda sodda, zerikarli yoki takroriy savollarni bermang.
- Tushuntirish o'zbekcha bo'lsin.
- Return ONLY JSON.
Schema:
{{"question":"...","options":["A) ...","B) ...","C) ...","D) ..."],"answer":"A","explanation":"o'zbekcha"}}""",

    "quiz_generate_uz_strict": """Create one Uzbek-interface English-learning quiz question for level {level}.
- Question in Uzbek.
- Exactly 4 options.
- No trivial repeats.
- No IQ or sequence questions.
- Explanation in Uzbek.
- Return ONLY JSON.
Schema:
{{"question":"...","options":["A) ...","B) ...","C) ...","D) ..."],"answer":"A","explanation":"o'zbekcha"}}""",

    "daily_word": """Bitta yangi ingliz so'zi. FAQAT JSON:
{{"word":"...","pos":"...","translation":"...","example":"...","example_uz":"...","tip":"..."}}""",

    "level_test": """Matn asosida daraja aniql. FAQAT JSON:
{{"level":"A1/A2/B1/B2/C1/C2","reason":"o'zbekcha 1-2 jumla"}}""",

    "lesson": "Daraja: {level}. Mavzu: 5 so'z, qisqa matn, 3 mashq, 1 ibora. O'zbekcha tushuntirish.",

    "lesson_pack": """Daraja: {level}. Ingliz tili darsi tayyorla.
- Mavzu inglizcha bo'ladi.
- Izoh va tushuntirishlar o'zbekcha bo'ladi.
- Qismlar aniq va foydali bo'lsin.
- 8-10 ta foydali so'z ber.
- Material kitobcha yoki mini qo'llanma kabi ko'rinsin.
- Return ONLY JSON.
Schema:
{{"title":"...","intro":"...","words":[{{"word":"...","meaning":"...","example":"..."}}],"phrases":["..."],"dialogue":"...","exercises":["..."],"tips":["..."]}}""",

    "iq_question": """IQ question (logic/reasoning) for general audience.
- Question and options in English only.
- Use medium difficulty, not a child's puzzle.
- Avoid classic trivial sequences like 2,4,8,16 or Fibonacci.
- Avoid repeating the same number-pattern family.
- Prefer analogy, logic, ordering, time, spatial, or arithmetic-reasoning.
- Explanation in Uzbek.
- Return ONLY JSON.
Schema:
{{"question":"...","options":["A) ...","B) ...","C) ...","D) ..."],"answer":"A","explanation":"o'zbekcha"}}""",

    "iq_question_strict": """Create one IQ question.
- Question in English.
- Exactly 4 options.
- Answer must be A/B/C/D.
- Avoid 2,4,8,16, Fibonacci, or overused textbook sequences.
- Avoid repeating the same pattern family.
- Explanation in Uzbek.
- Return ONLY JSON.
Schema:
{{"question":"...","options":["A) ...","B) ...","C) ...","D) ..."],"answer":"A","explanation":"o'zbekcha"}}""",

    "iq_question_uz": """IQ question (logic/reasoning) for general audience.
- Question and options in Uzbek only.
- Use medium difficulty.
- Avoid trivial classic sequences like 2,4,8,16 or Fibonacci.
- Avoid repeating the same pattern family.
- Prefer analogy, logic, ordering, time, spatial, or arithmetic reasoning.
- Explanation in Uzbek.
- Return ONLY JSON.
Schema:
{{"question":"...","options":["A) ...","B) ...","C) ...","D) ..."],"answer":"A","explanation":"o'zbekcha"}}""",

    "iq_question_uz_strict": """Create one IQ question in Uzbek.
- Question in Uzbek.
- Exactly 4 options.
- Avoid trivial classic sequences.
- Avoid repeated question families.
- Explanation in Uzbek.
- Return ONLY JSON.
Schema:
{{"question":"...","options":["A) ...","B) ...","C) ...","D) ..."],"answer":"A","explanation":"o'zbekcha"}}""",

    "auto": """Sen ingliz tili o'qituvchisisiz. Daraja: {level}.
- Inglizcha matn -> grammatik tekshir
- O'zbek savollar -> ingliz tili haqida javob
- O'zbekcha gap -> inglizchaga o'girish taklif qil
Do'stona, rag'batlantiruvchi bo'l.""",
}


async def _call(messages, max_tokens=1500, temp=0.4):
    api_key = _env_text("OPENROUTER_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://t.me/english_teacher_bot",
        "X-Title": "English Teacher Bot",
    }
    payload = {"model": MODEL, "messages": messages, "max_tokens": max_tokens, "temperature": temp}

    client = await _get_client()
    last_exc = None
    for attempt in range(3):
        try:
            await asyncio.wait_for(_AI_SEMAPHORE.acquire(), timeout=_SEMAPHORE_WAIT_SEC)
            try:
                r = await client.post(OR_URL, json=payload, headers=headers)
                r.raise_for_status()
                return r.json()["choices"][0]["message"]["content"].strip()
            finally:
                _AI_SEMAPHORE.release()
        except httpx.HTTPStatusError as e:
            last_exc = e
            if e.response.status_code in (429, 500, 502, 503, 504) and attempt < 2:
                await asyncio.sleep(1.0 + (attempt * 0.6))
                continue
            raise
        except httpx.RequestError as e:
            last_exc = e
            if attempt < 2:
                await asyncio.sleep(0.8 + (attempt * 0.5))
                continue
            raise
        except TimeoutError as e:
            last_exc = e
            raise RuntimeError("AI queue is full") from e
    if last_exc:
        raise last_exc


async def ask_ai(text, mode="auto", user_id=None, use_history=False):
    if mode in ("pronunciation", "translate", "uz_to_en", "en_to_uz"):
        warning = moderation_warning(text)
        if warning:
            return warning

    level = "A1"
    if user_id:
        u = get_user(user_id)
        if u:
            level = u.get("level", "A1")

    system = PROMPTS.get(mode, PROMPTS["auto"]).format(level=level)
    msgs = [{"role": "system", "content": system}]
    if use_history and user_id:
        msgs += get_history(user_id)
    msgs.append({"role": "user", "content": text})

    try:
        ans = await _call(msgs)
        if use_history and user_id:
            add_history(user_id, "user", text)
            add_history(user_id, "assistant", ans)
        return ans
    except RuntimeError as e:
        if "queue is full" in str(e).lower():
            return "⏳ Server yuklamasi yuqori. 10-20 soniyadan keyin qayta urinib ko'ring."
        if "api_key" in str(e).lower():
            return "❌ API kalit topilmadi."
        return "❌ Texnik xato. Iltimos, keyinroq qayta urinib ko'ring."
    except httpx.TimeoutException:
        return "⏰ AI javob bermadi. Qayta urining."
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            return "❌ API kalit noto'g'ri."
        if e.response.status_code == 429:
            return "⚠️ Limit oshdi. Bir oz kuting."
        return "❌ AI xato. Qayta urining."
    except Exception as e:
        logger.error(f"AI: {e}")
        return "❌ Texnik xato. @murodullayev_web"


async def ask_json(text, mode, level="A1"):
    system = PROMPTS.get(mode, "").format(level=level)
    msgs = [{"role": "system", "content": system}, {"role": "user", "content": text}]
    try:
        raw = await _call(msgs, max_tokens=600, temp=0.3)
        raw = re.sub(r"```json|```", "", raw).strip()
        return json.loads(raw)
    except RuntimeError:
        return None
    except Exception as e:
        logger.error(f"JSON AI: {e}")
        return None
