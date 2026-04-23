"""
Content Service — static lessons, grammar rules, moderation.
Ported from utils/content_bank.py.
"""

import re
from typing import Optional


# ══════════════════════════════════════════════════════════
# STATIC LESSONS
# ══════════════════════════════════════════════════════════

LESSON_PACKS = {
    "greetings": {
        "title": "🤝 Greetings & Introductions",
        "level": "A1",
        "intro": "Bu dars salomlashish va oddiy tanishuv gaplarini o'rganish uchun mo'ljallangan.",
        "objectives": ["Learn basic greetings", "Introduce yourself", "Ask about someone"],
        "vocabulary": [
            {"word": "Hello", "definition": "A common greeting", "example": "Hello, how are you?", "uz": "Salom"},
            {"word": "Goodbye", "definition": "Used when leaving", "example": "Goodbye, see you later!", "uz": "Xayr"},
            {"word": "Nice to meet you", "definition": "Said when meeting someone new", "example": "Nice to meet you, I'm Ali.", "uz": "Tanishganimdan xursandman"},
            {"word": "How are you?", "definition": "Asking about wellbeing", "example": "How are you today?", "uz": "Qalaysiz?"},
            {"word": "Thank you", "definition": "Expressing gratitude", "example": "Thank you for your help.", "uz": "Rahmat"},
        ],
        "phrases": ["How are you?", "Nice to meet you.", "See you later."],
        "dialogue": "A: Hello! My name is Sara.\nB: Hi, I am Tom. Nice to meet you.",
        "grammar": "Present tense of 'to be': I am, You are, He/She is",
        "exercises": [
            "O'zingizni inglizcha tanishtiring.",
            "Fill in: Hello, my name ___ Ali. (is)",
            "Translate: Tanishganimdan xursandman → ?",
            "Complete: How ___ you? I ___ fine. (are, am)",
        ],
        "tips": ["Rasmiy joyda 'Good morning' ishlating.", "Do'stlar bilan 'Hi' tabiiyroq eshitiladi."],
    },
    "shopping": {
        "title": "🛍️ Shopping & Money",
        "level": "A2",
        "intro": "Bu dars xarid paytida kerak bo'ladigan asosiy so'z va iboralarni beradi.",
        "objectives": ["Learn shopping vocabulary", "Ask about prices", "Make purchases"],
        "vocabulary": [
            {"word": "How much", "definition": "Asking the price", "example": "How much is this shirt?", "uz": "Qancha?"},
            {"word": "Expensive", "definition": "High price", "example": "This bag is too expensive.", "uz": "Qimmat"},
            {"word": "Cheap", "definition": "Low price", "example": "I found a cheap phone.", "uz": "Arzon"},
            {"word": "Discount", "definition": "Price reduction", "example": "Is there any discount?", "uz": "Chegirma"},
            {"word": "Receipt", "definition": "Proof of purchase", "example": "Can I have a receipt?", "uz": "Chek"},
        ],
        "phrases": ["Can I try this on?", "Do you have a smaller size?", "I would like to buy this."],
        "dialogue": "A: Can I help you?\nB: Yes, I am looking for a jacket.",
        "grammar": "Comparatives: cheaper, more expensive, the cheapest",
        "exercises": [
            "Do'konda sotuvchi va xaridor dialogi tuzing.",
            "How much ___ this? (is/are)",
            "This is ___ than that one. (cheap → cheaper)",
            "Can I ___ a receipt? (have)",
        ],
        "tips": ["Narx so'rashda 'How much is this?' juda foydali.", "Kiyim uchun 'try on' iborasini yodlang."],
    },
    "travel": {
        "title": "✈️ Travel & Transport",
        "level": "A2",
        "intro": "Sayohat va transport bo'yicha eng kerakli iboralar shu darsda jamlangan.",
        "objectives": ["Learn travel vocabulary", "Ask for directions", "Book transportation"],
        "vocabulary": [
            {"word": "Airport", "definition": "Place for planes", "example": "Let's go to the airport.", "uz": "Aeroport"},
            {"word": "Ticket", "definition": "Travel pass", "example": "I need a train ticket.", "uz": "Chipta"},
            {"word": "Departure", "definition": "When you leave", "example": "The departure is at 8 AM.", "uz": "Jo'nash"},
            {"word": "Arrival", "definition": "When you arrive", "example": "Arrival time is 3 PM.", "uz": "Kelish"},
            {"word": "Luggage", "definition": "Bags and suitcases", "example": "Where is my luggage?", "uz": "Yuk/bagaj"},
        ],
        "phrases": ["Where is the station?", "I have a reservation.", "What time does it leave?"],
        "dialogue": "A: Excuse me, where is the bus stop?\nB: It is across the street.",
        "grammar": "Future tense: will + verb, going to + verb",
        "exercises": [
            "Yo'l so'rash uchun mini dialog yozing.",
            "I ___ travel to London next week. (will)",
            "When is the ___ ? (jo'nash → departure)",
            "She is ___ to visit Paris. (going)",
        ],
        "tips": ["'Excuse me' bilan boshlasangiz gap muloyim chiqadi.", "'reservation' va 'booking' ko'p ishlatiladi."],
    },
}


def get_static_lesson_pack(topic: str) -> Optional[dict]:
    """Get a static lesson pack by topic key."""
    return LESSON_PACKS.get(topic.lower().strip())


def get_available_lesson_topics() -> list[str]:
    """Get list of available lesson topic keys."""
    return list(LESSON_PACKS.keys())


# ══════════════════════════════════════════════════════════
# GRAMMAR RULES
# ══════════════════════════════════════════════════════════

GRAMMAR_RULES = {
    "tenses": "📘 <b>Ingliz tilidagi zamonlar</b>\n\n"
        "<b>1. Simple tenses</b>\n"
        "• Present Simple: odatiy ish-harakat. Misol: <i>I go to school every day.</i>\n"
        "• Past Simple: o'tgan zamondagi tugagan ish. Misol: <i>I went yesterday.</i>\n"
        "• Future Simple: kelajak reja yoki taxmin. Misol: <i>I will call you.</i>\n\n"
        "<b>2. Continuous tenses</b>\n"
        "• Davom etayotgan jarayonni bildiradi.\n"
        "• Misol: <i>She is reading now.</i>\n\n"
        "<b>3. Perfect tenses</b>\n"
        "• Natija yoki tajribani ko'rsatadi.\n"
        "• Misol: <i>They have finished the task.</i>\n\n"
        "<b>4. Perfect Continuous</b>\n"
        "• Davomiylik + natija.\n"
        "• Misol: <i>I have been learning English for two years.</i>\n\n"
        "<b>💡 Ko'p xato qilinadigan joy</b>\n"
        "• Present Simple va Present Continuous aralashib ketadi.\n"
        "• Har bir zamonda signal so'zlarni yodlang: <i>every day, now, already, for/since</i>.",

    "articles": "📘 <b>Articles: a, an, the</b>\n\n"
        "<b>a / an</b>\n"
        "• Bir dona, noaniq narsa uchun.\n"
        "• <i>a book</i>, <i>a university</i>\n"
        "• <i>an apple</i>, <i>an hour</i>\n\n"
        "<b>the</b>\n"
        "• Aniq yoki oldin tilga olingan narsa uchun.\n"
        "• <i>the sun</i>, <i>the book on the table</i>\n\n"
        "<b>Article ishlatilmaydigan holatlar</b>\n"
        "• Umumiy ko'plik: <i>Books are useful.</i>\n"
        "• Fanlar va tillar: <i>English is important.</i>\n\n"
        "<b>💡 Maslahat</b>\n"
        "• Tovushga qarab tanlang: <i>an honest man</i>, lekin <i>a European city</i>.",

    "prepositions": "📘 <b>Asosiy prepositions</b>\n\n"
        "<b>Joy</b>\n"
        "• <b>in</b> - ichida: <i>in the room</i>\n"
        "• <b>on</b> - ustida: <i>on the table</i>\n"
        "• <b>at</b> - nuqtada: <i>at school</i>\n\n"
        "<b>Vaqt</b>\n"
        "• <b>in</b> - oy, yil, uzoq davr: <i>in July</i>, <i>in 2026</i>\n"
        "• <b>on</b> - kun, sana: <i>on Monday</i>\n"
        "• <b>at</b> - aniq vaqt: <i>at 7:00</i>\n\n"
        "<b>Boshqa foydali prepositions</b>\n"
        "• <b>for</b> - davomiylik yoki maqsad\n"
        "• <b>to</b> - yo'nalish\n"
        "• <b>with</b> - bilan\n"
        "• <b>by</b> - orqali yoki yonida\n\n"
        "<b>💡 Ko'p xato</b>\n"
        "• <i>in Monday</i> emas, <i>on Monday</i>\n"
        "• <i>at night</i> lekin <i>in the morning</i>",

    "questions": "📘 <b>Savol tuzish</b>\n\n"
        "<b>Yes/No questions</b>\n"
        "• Yordamchi fe'l oldinga chiqadi.\n"
        "• <i>Do you like coffee?</i>\n"
        "• <i>Is she ready?</i>\n\n"
        "<b>Wh- questions</b>\n"
        "• <i>What, Where, When, Why, Who, How</i>\n"
        "• <i>Where do you live?</i>\n"
        "• <i>Why did he leave?</i>\n\n"
        "<b>Formula</b>\n"
        "• Wh-word + auxiliary + subject + main verb\n\n"
        "<b>💡 Ko'p xato</b>\n"
        "• <i>Where you live?</i> noto'g'ri\n"
        "• To'g'ri: <i>Where do you live?</i>",

    "conditionals": "📘 <b>Conditionals (Shart ergash gaplar)</b>\n\n"
        "<b>Zero conditional</b>\n"
        "• Umumiy haqiqat: <i>If you heat ice, it melts.</i>\n\n"
        "<b>First conditional</b>\n"
        "• Real kelajak ehtimoli: <i>If it rains, I will stay home.</i>\n\n"
        "<b>Second conditional</b>\n"
        "• Hozirgi noreal holat: <i>If I were rich, I would travel more.</i>\n\n"
        "<b>Third conditional</b>\n"
        "• O'tgan zamondagi afsus: <i>If she had studied, she would have passed.</i>\n\n"
        "<b>💡 Maslahat</b>\n"
        "• <i>if</i> qismida odatda <i>will</i> ishlatilmaydi.",

    "passive": "📘 <b>Passive Voice (Majhul nisbat)</b>\n\n"
        "<b>Formula</b>\n"
        "• <i>be</i> fe'li + V3 (Past Participle)\n"
        "• <i>The room is cleaned every day.</i>\n"
        "• <i>The homework was finished.</i>\n\n"
        "<b>Qachon ishlatiladi?</b>\n"
        "• Ishni kim qilgani muhim bo'lmasa\n"
        "• Natija muhim bo'lsa\n\n"
        "<b>Active vs Passive</b>\n"
        "• Active: <i>Ali wrote the letter.</i>\n"
        "• Passive: <i>The letter was written by Ali.</i>\n\n"
        "<b>💡 Ko'p xato</b>\n"
        "• <i>is write</i> emas\n"
        "• To'g'ri: <i>is written</i>",
}


def get_static_rule_text(rule_name: str) -> Optional[str]:
    """Get static grammar rule text by name."""
    return GRAMMAR_RULES.get(rule_name.lower().strip())


def get_available_rules() -> list[str]:
    """Get list of available grammar rule names."""
    return list(GRAMMAR_RULES.keys())


# ══════════════════════════════════════════════════════════
# MODERATION
# ══════════════════════════════════════════════════════════

# Common bad words and slurs (kept minimal, expand as needed)
_BAD_WORDS = {
    "fuck", "shit", "damn", "bitch", "ass", "dick", "pussy",
    "suka", "blyat", "pizd", "huy", "ебать", "блять",
    "sik", "qo'taq", "jo'ndi",
}

_BAD_PATTERN = re.compile(
    r'\b(' + '|'.join(re.escape(w) for w in _BAD_WORDS) + r')\b',
    re.IGNORECASE,
)


def moderation_warning(text: str) -> Optional[str]:
    """
    Check text for inappropriate content.
    Returns warning message if bad content found, None if clean.
    """
    if _BAD_PATTERN.search(text):
        return (
            "⚠️ <b>Ogohlantirish!</b>\n\n"
            "Iltimos, odob doirasidan chiqmang. "
            "Bot faqat ta'lim maqsadlarida ishlaydi."
        )
    return None
