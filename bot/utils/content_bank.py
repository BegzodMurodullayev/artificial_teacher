"""Static content bank for fast responses and basic safety checks."""

from __future__ import annotations

import re


_BLOCKED_PATTERNS = [
    r"\bfuck(?:ing|er|ed)?\b",
    r"\bshit(?:ty)?\b",
    r"\bbitch(?:es)?\b",
    r"\bbastard\b",
    r"\bdick\b",
    r"\bpussy\b",
    r"\bslut\b",
    r"\bwhore\b",
    r"\bporn\b",
    r"\bsex\b",
    r"\bsuka\b",
    r"\bblya+t\b",
    r"\bhuy\b",
    r"\bxuy\b",
    r"\bgandon\b",
    r"\bsik\b",
]

_BLOCKED_RE = re.compile("|".join(_BLOCKED_PATTERNS), re.IGNORECASE)


def moderation_warning(text: str) -> str | None:
    source = (text or "").strip()
    if not source:
        return None
    if not _BLOCKED_RE.search(source):
        return None
    return (
        "Bu so'z yoki ibora bolalar auditoriyasi uchun mos emas. "
        "Bot bunday so'zlar uchun talaffuz, tarjima yoki qo'shimcha izoh bermaydi."
    )


def _normalize_key(text: str) -> str:
    cleaned = (text or "").strip().lower()
    cleaned = cleaned.replace("_", " ").replace("-", " ")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


_RULE_ALIASES = {
    "tenses": "tenses",
    "zamonlar": "tenses",
    "articles": "articles",
    "article": "articles",
    "artikl": "articles",
    "prepositions": "prepositions",
    "preposition": "prepositions",
    "questions": "questions",
    "savollar": "questions",
    "conditionals": "conditionals",
    "conditional": "conditionals",
    "passive": "passive",
    "passive voice": "passive",
}


_STATIC_RULES = {
    "tenses": """📘 *Ingliz tilidagi zamonlar*

*1. Simple tenses*
- Present Simple: odatiy ish-harakat. Misol: `I go to school every day.`
- Past Simple: o'tgan zamondagi tugagan ish. Misol: `I went yesterday.`
- Future Simple: kelajak reja yoki taxmin. Misol: `I will call you.`

*2. Continuous tenses*
- Davom etayotgan jarayonni bildiradi.
- Misol: `She is reading now.`

*3. Perfect tenses*
- Natija yoki tajribani ko'rsatadi.
- Misol: `They have finished the task.`

*4. Perfect Continuous*
- Davomiylik + natija.
- Misol: `I have been learning English for two years.`

*Ko'p xato qilinadigan joy*
- Present Simple va Present Continuous aralashib ketadi.
- Har bir zamonda signal so'zlarni yodlang: `every day`, `now`, `already`, `for/since`.""",
    "articles": """📘 *Articles: a, an, the*

*a / an*
- Bir dona, noaniq narsa uchun.
- `a book`, `a university`
- `an apple`, `an hour`

*the*
- Aniq yoki oldin tilga olingan narsa uchun.
- `the sun`, `the book on the table`

*Article ishlatilmaydigan holatlar*
- Umumiy ko'plik: `Books are useful.`
- Fanlar va tillar: `English is important.`

*Maslahat*
- Tovushga qarab tanlang: `an honest man`, lekin `a European city`.""",
    "prepositions": """📘 *Asosiy prepositions*

*Joy*
- `in` - ichida: `in the room`
- `on` - ustida: `on the table`
- `at` - nuqtada: `at school`

*Vaqt*
- `in` - oy, yil, uzoq davr: `in July`, `in 2026`
- `on` - kun, sana: `on Monday`
- `at` - aniq vaqt: `at 7:00`

*Boshqa foydali prepositions*
- `for` - davomiylik yoki maqsad
- `to` - yo'nalish
- `with` - bilan
- `by` - orqali yoki yonida

*Ko'p xato*
- `in Monday` emas, `on Monday`
- `at night` lekin `in the morning`""",
    "questions": """📘 *Savol tuzish*

*Yes/No questions*
- Yordamchi fe'l oldinga chiqadi.
- `Do you like coffee?`
- `Is she ready?`

*Wh- questions*
- `What`, `Where`, `When`, `Why`, `Who`, `How`
- `Where do you live?`
- `Why did he leave?`

*Formula*
- Wh-word + auxiliary + subject + main verb

*Ko'p xato*
- `Where you live?` noto'g'ri
- To'g'ri: `Where do you live?`""",
    "conditionals": """📘 *Conditionals*

*Zero conditional*
- Umumiy haqiqat: `If you heat ice, it melts.`

*First conditional*
- Real kelajak ehtimoli: `If it rains, I will stay home.`

*Second conditional*
- Hozirgi noreal holat: `If I were rich, I would travel more.`

*Third conditional*
- O'tgan zamondagi afsus: `If she had studied, she would have passed.`

*Maslahat*
- `if` qismida odatda `will` ishlatilmaydi.""",
    "passive": """📘 *Passive Voice*

*Formula*
- `be` fe'li + V3
- `The room is cleaned every day.`
- `The homework was finished.`

*Qachon ishlatiladi*
- Ishni kim qilgani muhim bo'lmasa
- Natija muhim bo'lsa

*Active vs Passive*
- Active: `Ali wrote the letter.`
- Passive: `The letter was written by Ali.`

*Ko'p xato*
- `is write` emas
- To'g'ri: `is written`""",
}


def get_static_rule_text(topic: str) -> str | None:
    key = _RULE_ALIASES.get(_normalize_key(topic))
    if not key:
        return None
    return _STATIC_RULES.get(key)


_LESSON_BANK = {
    "greetings": {
        "intro": "Bu dars salomlashish va oddiy tanishuv gaplarini o'rganish uchun mo'ljallangan.",
        "words": [
            {"word": "hello", "meaning": "salom", "example": "Hello, how are you?"},
            {"word": "hi", "meaning": "salom", "example": "Hi, nice to see you."},
            {"word": "good morning", "meaning": "xayrli tong", "example": "Good morning, teacher."},
            {"word": "good evening", "meaning": "xayrli kech", "example": "Good evening, everyone."},
            {"word": "name", "meaning": "ism", "example": "My name is Ali."},
            {"word": "meet", "meaning": "tanishmoq", "example": "Nice to meet you."},
        ],
        "phrases": ["How are you?", "Nice to meet you.", "See you later."],
        "dialogue": "A: Hello! My name is Sara. B: Hi, I am Tom. Nice to meet you.",
        "exercises": ["O'zingizni inglizcha tanishtiring.", "3 ta salomlashish iborasi yozing."],
        "tips": ["Rasmiy joyda `Good morning` ishlating.", "Do'stlar bilan `Hi` tabiiyroq eshitiladi."],
    },
    "shopping": {
        "intro": "Bu dars xarid paytida kerak bo'ladigan asosiy so'z va iboralarni beradi.",
        "words": [
            {"word": "price", "meaning": "narx", "example": "What is the price of this bag?"},
            {"word": "cheap", "meaning": "arzon", "example": "This shirt is cheap."},
            {"word": "expensive", "meaning": "qimmat", "example": "That phone is expensive."},
            {"word": "size", "meaning": "o'lcham", "example": "Do you have this in my size?"},
            {"word": "cash", "meaning": "naqd pul", "example": "Can I pay in cash?"},
            {"word": "receipt", "meaning": "chek", "example": "Please keep the receipt."},
        ],
        "phrases": ["Can I try this on?", "Do you have a smaller size?", "I would like to buy this."],
        "dialogue": "A: Can I help you? B: Yes, I am looking for a jacket.",
        "exercises": ["Do'konda sotuvchi va xaridor dialogi tuzing.", "3 ta shopping savoli yozing."],
        "tips": ["Narx so'rashda `How much is this?` juda foydali.", "Kiyim uchun `try on` iborasini yodlang."],
    },
    "travel": {
        "intro": "Sayohat va transport bo'yicha eng kerakli iboralar shu darsda jamlangan.",
        "words": [
            {"word": "ticket", "meaning": "chipta", "example": "I need a train ticket."},
            {"word": "airport", "meaning": "aeroport", "example": "We arrived at the airport early."},
            {"word": "hotel", "meaning": "mehmonxona", "example": "Our hotel is near the station."},
            {"word": "passport", "meaning": "pasport", "example": "Show me your passport, please."},
            {"word": "map", "meaning": "xarita", "example": "I need a city map."},
            {"word": "luggage", "meaning": "yuk", "example": "My luggage is heavy."},
        ],
        "phrases": ["Where is the station?", "I have a reservation.", "What time does it leave?"],
        "dialogue": "A: Excuse me, where is the bus stop? B: It is across the street.",
        "exercises": ["Aeroportda ishlatiladigan 3 ta gap yozing.", "Yo'l so'rash uchun mini dialog yozing."],
        "tips": ["`Excuse me` bilan boshlasangiz gap muloyim chiqadi.", "`reservation` va `booking` ko'p ishlatiladi."],
    },
}


def get_static_lesson_pack(topic: str, level: str) -> dict | None:
    key = _normalize_key(topic)
    data = _LESSON_BANK.get(key)
    if not data:
        return None
    return {
        "title": f"{topic.title()} lesson",
        "intro": data["intro"],
        "words": data["words"],
        "phrases": data["phrases"],
        "dialogue": data["dialogue"],
        "exercises": data["exercises"],
        "tips": data["tips"] + [f"Daraja: {level} uchun soddalashtirilgan tushuntirish bilan ishlang."],
    }
