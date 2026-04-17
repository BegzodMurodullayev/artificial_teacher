import random
from typing import Dict, List


QUIZ_BANK: List[Dict[str, object]] = [
    {
        "question": "Choose the correct sentence:",
        "options": [
            "She go to school every day.",
            "She goes to school every day.",
            "She going to school every day.",
            "She gone to school every day.",
        ],
        "answer": 1,
        "explanation": "He/She/It bilan Present Simple da fe'lga -s/-es qo'shiladi.",
        "level": "A1",
    },
    {
        "question": "Fill in the blank: I ___ never been to London.",
        "options": ["am", "have", "has", "was"],
        "answer": 1,
        "explanation": "Present Perfect: I/You/We/They + have + V3.",
        "level": "A2",
    },
    {
        "question": "Choose the correct article: ___ apple a day keeps the doctor away.",
        "options": ["A", "An", "The", "No article"],
        "answer": 1,
        "explanation": "Unli tovush bilan boshlangan birlik sanoqli so'z oldida 'an' ishlatiladi.",
        "level": "A1",
    },
    {
        "question": "Which is correct?",
        "options": [
            "There is many books on the table.",
            "There are many books on the table.",
            "There many books are on the table.",
            "There are much books on the table.",
        ],
        "answer": 1,
        "explanation": "Ko'plikdagi sanaladigan ot bilan 'there are' ishlatiladi.",
        "level": "A1",
    },
    {
        "question": "Choose the best option: If it ___ tomorrow, we will stay home.",
        "options": ["rain", "rains", "will rain", "rained"],
        "answer": 1,
        "explanation": "First conditional: If + Present Simple, will + infinitive.",
        "level": "B1",
    },
    {
        "question": "Fill in the blank: I was tired, ___ I went to bed early.",
        "options": ["because", "so", "but", "if"],
        "answer": 1,
        "explanation": "'So' natijani bildiradi: charchadim, shuning uchun erta uxladim.",
        "level": "A2",
    },
    {
        "question": "Choose the correct passive form: People speak English worldwide.",
        "options": [
            "English is spoken worldwide.",
            "English spoken worldwide.",
            "English is speak worldwide.",
            "English was spoken worldwide now.",
        ],
        "answer": 0,
        "explanation": "Passive (Present Simple): am/is/are + V3.",
        "level": "B1",
    },
    {
        "question": "Which sentence is grammatically correct?",
        "options": [
            "He don't like coffee.",
            "He doesn't likes coffee.",
            "He doesn't like coffee.",
            "He not like coffee.",
        ],
        "answer": 2,
        "explanation": "3-shaxs birlik inkor: does not + verb(base form).",
        "level": "A1",
    },
    {
        "question": "Choose the correct preposition: She is good ___ math.",
        "options": ["at", "in", "on", "for"],
        "answer": 0,
        "explanation": "Yaxshi bo'lish ma'nosida: good at.",
        "level": "A2",
    },
    {
        "question": "Complete the sentence: By next year, they ___ here for a decade.",
        "options": ["will live", "will have lived", "have lived", "lived"],
        "answer": 1,
        "explanation": "Kelajakdagi ma'lum vaqtgacha davom etadigan holat: Future Perfect.",
        "level": "B2",
    },
    {
        "question": "Find the correct option: I look forward to ___ you.",
        "options": ["see", "seeing", "seen", "be seeing"],
        "answer": 1,
        "explanation": "look forward to dan keyin gerund (V-ing) keladi.",
        "level": "B1",
    },
    {
        "question": "Choose the right form: She said that she ___ busy that day.",
        "options": ["is", "was", "were", "has been"],
        "answer": 1,
        "explanation": "Reported speech da zamon bir pog'ona orqaga suriladi.",
        "level": "B1",
    },
    {
        "question": "Select the best modal verb: You ___ wear a seatbelt.",
        "options": ["must", "might", "could", "would"],
        "answer": 0,
        "explanation": "Majburiyat yoki qat'iy qoida uchun 'must'.",
        "level": "A2",
    },
    {
        "question": "Which one is correct?",
        "options": [
            "She has lived here since 5 years.",
            "She has lived here for 5 years.",
            "She lives here for 5 years.",
            "She lived here since 5 years.",
        ],
        "answer": 1,
        "explanation": "Davomiylik muddati bilan 'for', boshlanish nuqtasi bilan 'since'.",
        "level": "B1",
    },
    {
        "question": "Choose the correct relative pronoun: The man ___ called is my uncle.",
        "options": ["which", "who", "where", "when"],
        "answer": 1,
        "explanation": "Odamlar uchun who ishlatiladi.",
        "level": "A2",
    },
    {
        "question": "Pick the correct sentence:",
        "options": [
            "I wish I can fly.",
            "I wish I could fly.",
            "I wish I will fly.",
            "I wish I am flying.",
        ],
        "answer": 1,
        "explanation": "Wish + unreal present holatda past form ishlatiladi: could.",
        "level": "B2",
    },
    {
        "question": "Choose the best answer: Hardly ___ I arrived when it started raining.",
        "options": ["had", "have", "did", "was"],
        "answer": 0,
        "explanation": "Hardly/Scarcely bilan inversiya: Hardly had I ... when ...",
        "level": "C1",
    },
    {
        "question": "Select the correct form: Neither of the answers ___ correct.",
        "options": ["are", "were", "is", "be"],
        "answer": 2,
        "explanation": "Neither of + plural noun ko'pincha birlik fe'l bilan keladi: is.",
        "level": "B2",
    },
    {
        "question": "Complete: The project ___ by the time we got there.",
        "options": ["finished", "has finished", "had been finished", "was finishing"],
        "answer": 2,
        "explanation": "Pastdagi boshqa voqeagacha tugallangan passive holat: had been + V3.",
        "level": "C1",
    },
    {
        "question": "Pick the most natural sentence:",
        "options": [
            "Despite of the rain, we played.",
            "Despite the rain, we played.",
            "Although of the rain, we played.",
            "In spite the rain, we played.",
        ],
        "answer": 1,
        "explanation": "Despite + noun/gerund. 'Despite of' noto'g'ri.",
        "level": "B1",
    },
]


DAILY_WORDS: List[Dict[str, str]] = [
    {"word": "achieve", "definition": "erishmoq", "example": "You can achieve your goals with daily practice."},
    {"word": "improve", "definition": "yaxshilamoq", "example": "Reading every day will improve your vocabulary."},
    {"word": "confident", "definition": "o'ziga ishongan", "example": "She felt confident before the interview."},
    {"word": "challenge", "definition": "sinov, qiyinchilik", "example": "Learning a language is a fun challenge."},
    {"word": "habit", "definition": "odat", "example": "Make English practice a daily habit."},
    {"word": "focus", "definition": "diqqatni jamlamoq", "example": "Try to focus on one topic at a time."},
    {"word": "opportunity", "definition": "imkoniyat", "example": "This course is a great opportunity to grow."},
    {"word": "progress", "definition": "taraqqiyot", "example": "Small progress every day leads to big results."},
    {"word": "fluent", "definition": "ravon (til bilish)", "example": "He became fluent after one year of speaking practice."},
    {"word": "consistency", "definition": "barqarorlik, uzluksizlik", "example": "Consistency is more important than intensity."},
]


LEVEL_ORDER = ["A1", "A2", "B1", "B2", "C1", "C2"]


def pick_quiz_questions(count: int = 5) -> List[Dict[str, object]]:
    sample_size = min(count, len(QUIZ_BANK))
    return random.sample(QUIZ_BANK, sample_size)


def pick_daily_word() -> Dict[str, str]:
    return random.choice(DAILY_WORDS)


def score_to_level(score: float) -> str:
    if score < 0.35:
        return "A1"
    if score < 0.5:
        return "A2"
    if score < 0.65:
        return "B1"
    if score < 0.8:
        return "B2"
    if score < 0.92:
        return "C1"
    return "C2"
