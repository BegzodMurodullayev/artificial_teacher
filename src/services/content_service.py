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
        "objectives": ["Learn basic greetings", "Introduce yourself", "Ask about someone"],
        "vocabulary": [
            {"word": "Hello", "definition": "A common greeting", "example": "Hello, how are you?", "uz": "Salom"},
            {"word": "Goodbye", "definition": "Used when leaving", "example": "Goodbye, see you later!", "uz": "Xayr"},
            {"word": "Nice to meet you", "definition": "Said when meeting someone new", "example": "Nice to meet you, I'm Ali.", "uz": "Tanishganimdan xursandman"},
            {"word": "How are you?", "definition": "Asking about wellbeing", "example": "How are you today?", "uz": "Qalaysiz?"},
            {"word": "Thank you", "definition": "Expressing gratitude", "example": "Thank you for your help.", "uz": "Rahmat"},
        ],
        "grammar": "Present tense of 'to be': I am, You are, He/She is",
        "exercises": [
            "Fill in: Hello, my name ___ Ali. (is)",
            "Translate: Tanishganimdan xursandman → ?",
            "Complete: How ___ you? I ___ fine. (are, am)",
        ],
    },
    "shopping": {
        "title": "🛍️ Shopping & Money",
        "level": "A2",
        "objectives": ["Learn shopping vocabulary", "Ask about prices", "Make purchases"],
        "vocabulary": [
            {"word": "How much", "definition": "Asking the price", "example": "How much is this shirt?", "uz": "Qancha?"},
            {"word": "Expensive", "definition": "High price", "example": "This bag is too expensive.", "uz": "Qimmat"},
            {"word": "Cheap", "definition": "Low price", "example": "I found a cheap phone.", "uz": "Arzon"},
            {"word": "Discount", "definition": "Price reduction", "example": "Is there any discount?", "uz": "Chegirma"},
            {"word": "Receipt", "definition": "Proof of purchase", "example": "Can I have a receipt?", "uz": "Chek"},
        ],
        "grammar": "Comparatives: cheaper, more expensive, the cheapest",
        "exercises": [
            "How much ___ this? (is/are)",
            "This is ___ than that one. (cheap → cheaper)",
            "Can I ___ a receipt? (have)",
        ],
    },
    "travel": {
        "title": "✈️ Travel & Transport",
        "level": "A2",
        "objectives": ["Learn travel vocabulary", "Ask for directions", "Book transportation"],
        "vocabulary": [
            {"word": "Airport", "definition": "Place for planes", "example": "Let's go to the airport.", "uz": "Aeroport"},
            {"word": "Ticket", "definition": "Travel pass", "example": "I need a train ticket.", "uz": "Chipta"},
            {"word": "Departure", "definition": "When you leave", "example": "The departure is at 8 AM.", "uz": "Jo'nash"},
            {"word": "Arrival", "definition": "When you arrive", "example": "Arrival time is 3 PM.", "uz": "Kelish"},
            {"word": "Luggage", "definition": "Bags and suitcases", "example": "Where is my luggage?", "uz": "Yuk/bagaj"},
        ],
        "grammar": "Future tense: will + verb, going to + verb",
        "exercises": [
            "I ___ travel to London next week. (will)",
            "When is the ___ ? (jo'nash → departure)",
            "She is ___ to visit Paris. (going)",
        ],
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
    "tenses": "📚 **English Tenses**\n\n"
        "1. **Present Simple**: I work / She works\n"
        "2. **Present Continuous**: I am working\n"
        "3. **Past Simple**: I worked\n"
        "4. **Past Continuous**: I was working\n"
        "5. **Present Perfect**: I have worked\n"
        "6. **Future Simple**: I will work",

    "articles": "📚 **Articles: a, an, the**\n\n"
        "• **a** — unspecific singular (a book, a cat)\n"
        "• **an** — before vowel sounds (an apple, an hour)\n"
        "• **the** — specific/known (the sun, the book on the table)\n"
        "• No article — general/uncountable (water, love, cats in general)",

    "prepositions": "📚 **Common Prepositions**\n\n"
        "• **in** — inside (in the room, in 2024)\n"
        "• **on** — surface (on the table, on Monday)\n"
        "• **at** — point (at home, at 5 PM)\n"
        "• **to** — direction (go to school)\n"
        "• **for** — purpose/duration (for you, for 3 hours)",

    "questions": "📚 **Question Formation**\n\n"
        "• **Yes/No**: Do/Does/Did + subject + verb?\n"
        "  → Do you like coffee?\n"
        "• **Wh-**: Wh-word + auxiliary + subject + verb?\n"
        "  → Where do you live?\n"
        "• **Tag**: statement + opposite tag\n"
        "  → You like tea, don't you?",

    "conditionals": "📚 **Conditional Sentences**\n\n"
        "• **Zero**: If + present, present (facts)\n"
        "  → If you heat water, it boils.\n"
        "• **First**: If + present, will + verb (possible)\n"
        "  → If it rains, I will stay home.\n"
        "• **Second**: If + past, would + verb (unlikely)\n"
        "  → If I won the lottery, I would travel.\n"
        "• **Third**: If + past perfect, would have + V3 (impossible past)\n"
        "  → If I had studied, I would have passed.",

    "passive": "📚 **Passive Voice**\n\n"
        "• Active: The cat ate the fish.\n"
        "• Passive: The fish was eaten by the cat.\n"
        "• Formula: Object + be + V3 (+ by agent)\n"
        "• Present: is/are + V3\n"
        "• Past: was/were + V3\n"
        "• Future: will be + V3",
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
