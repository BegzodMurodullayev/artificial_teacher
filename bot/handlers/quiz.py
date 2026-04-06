"""handlers/quiz.py - Quiz and IQ flows."""
import html
import random
import re
import time
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils.ai import ask_json
from html_maker import render_html_document, html_open_guide
from database.db import (
    get_user,
    inc_stat,
    upsert_user,
    check_limit,
    inc_usage,
    get_user_plan,
    add_quiz_attempt,
    auto_adjust_level_from_quiz,
    set_iq_score,
    remember_question_key,
    get_recent_question_keys,
    add_points,
    get_reward_setting,
)

active_sessions = {}

PLAN_ICONS = {"free": "\U0001F193", "standard": "\u2B50", "pro": "\U0001F48E", "premium": "\U0001F451"}
QUIZ_COUNT_OPTIONS = [5, 10, 15, 20]
IQ_COUNT_OPTIONS = [10, 15, 20]
QUESTION_TIMEOUT_SECONDS = 45
QUESTION_TIMEOUT_OPTIONS = [30, 45, 60]
COUNTDOWN_TICK_SECONDS = 5

_BAD_CYRILLIC = re.compile(r"[\u0400-\u04FF]")
_UZ_WORDS = {
    "qaysi", "tog'ri", "to'g'ri", "yozilgan", "kitob", "kitoblar",
    "kitobni", "kitobda", "savol", "javob", "o'zbek", "ingliz",
    "test", "tugatish", "daraja", "misol", "tushuntir",
}

_FALLBACK_QUIZ = {
    "A1": [
        {"question": "Choose the correct form: She ___ a student.", "options": ["A) am", "B) is", "C) are", "D) be"], "answer": "B", "explanation": "She bilan is ishlatiladi."},
        {"question": "Choose the correct word: I ___ to school every day.", "options": ["A) go", "B) goes", "C) going", "D) went"], "answer": "A", "explanation": "I bilan go ishlatiladi."},
        {"question": "Choose the correct sentence.", "options": ["A) He have a car.", "B) He has a car.", "C) He having a car.", "D) He has car."], "answer": "B", "explanation": "He bilan has ishlatiladi."},
        {"question": "Choose the correct article: It is ___ apple.", "options": ["A) a", "B) an", "C) the", "D) no article"], "answer": "B", "explanation": "Apple unli tovush bilan boshlanadi, an ishlatiladi."},
        {"question": "Choose the correct pronoun: ___ are my friends.", "options": ["A) He", "B) She", "C) They", "D) It"], "answer": "C", "explanation": "Friends ko'plik, ular - they."},
    ],
    "A2": [
        {"question": "Choose the correct past form: Yesterday we ___ football.", "options": ["A) play", "B) played", "C) playing", "D) plays"], "answer": "B", "explanation": "Yesterday bilan Past Simple ishlatiladi."},
        {"question": "Choose the correct preposition: She is good ___ English.", "options": ["A) at", "B) in", "C) on", "D) for"], "answer": "A", "explanation": "good at iborasi ishlatiladi."},
        {"question": "Choose the correct form: There ___ two books on the table.", "options": ["A) is", "B) are", "C) was", "D) be"], "answer": "B", "explanation": "Two books ko'plik, shuning uchun are."},
        {"question": "Choose the correct sentence.", "options": ["A) I have visited London last year.", "B) I visited London last year.", "C) I visit London last year.", "D) I had visit London last year."], "answer": "B", "explanation": "Last year bilan Past Simple ishlatiladi."},
        {"question": "Choose the correct word: He is interested ___ music.", "options": ["A) on", "B) in", "C) at", "D) for"], "answer": "B", "explanation": "interested in iborasi to'g'ri."},
    ],
    "B1": [
        {"question": "Choose the correct form: If it rains, we ___ at home.", "options": ["A) stay", "B) stayed", "C) will stay", "D) would stay"], "answer": "C", "explanation": "First conditional: If + Present, will + V1."},
        {"question": "Choose the correct word: I look forward ___ from you.", "options": ["A) to hearing", "B) hear", "C) to hear", "D) hearing"], "answer": "A", "explanation": "look forward to + V-ing bo'ladi."},
        {"question": "Choose the correct sentence.", "options": ["A) I have been to Paris last year.", "B) I went to Paris last year.", "C) I have gone to Paris last year.", "D) I was gone to Paris last year."], "answer": "B", "explanation": "Aniq o'tgan vaqt bilan Past Simple ishlatiladi."},
        {"question": "Choose the correct form: By the time we arrived, the film ___.", "options": ["A) started", "B) has started", "C) had started", "D) was starting"], "answer": "C", "explanation": "Oldinroq bo'lgan ish uchun Past Perfect ishlatiladi."},
        {"question": "Choose the correct word: She apologized ___ being late.", "options": ["A) for", "B) to", "C) on", "D) with"], "answer": "A", "explanation": "apologize for iborasi ishlatiladi."},
    ],
    "B2": [
        {"question": "Choose the correct form: She would have passed if she ___ harder.", "options": ["A) studied", "B) studies", "C) had studied", "D) has studied"], "answer": "C", "explanation": "Third conditional ishlatilgan."},
        {"question": "Choose the correct word: The meeting was ___ due to rain.", "options": ["A) put off", "B) put on", "C) put up", "D) put out"], "answer": "A", "explanation": "put off = kechiktirmoq."},
        {"question": "Choose the correct sentence.", "options": ["A) Hardly had I arrived when he called.", "B) Hardly I had arrived when he called.", "C) Hardly had arrived I when he called.", "D) Hardly I arrived when he called."], "answer": "A", "explanation": "Hardly bilan inversion ishlatiladi."},
        {"question": "Choose the correct word: Her argument was highly ___.", "options": ["A) persuasive", "B) persuading", "C) persuade", "D) persuasion"], "answer": "A", "explanation": "was dan keyin sifat kerak: persuasive."},
        {"question": "Choose the correct sentence.", "options": ["A) No sooner I had sat down than the phone rang.", "B) No sooner had I sat down than the phone rang.", "C) No sooner had sat I down than the phone rang.", "D) No sooner I sat down than the phone rang."], "answer": "B", "explanation": "No sooner bilan inversion bo'ladi."},
    ],
    "C1": [
        {"question": "Choose the best option: His explanation was so ___ that everyone understood immediately.", "options": ["A) lucid", "B) vague", "C) scarce", "D) shallow"], "answer": "A", "explanation": "lucid - ravshan, aniq ma'nosini beradi."},
        {"question": "Choose the correct sentence.", "options": ["A) Rarely I have seen such discipline.", "B) Rarely have I seen such discipline.", "C) Rarely have seen I such discipline.", "D) Rarely I saw such discipline."], "answer": "B", "explanation": "Rarely bilan inversion ishlatiladi."},
        {"question": "Choose the best option: The plan was ___ because it balanced risk and opportunity.", "options": ["A) judicious", "B) accidental", "C) fragile", "D) implicit"], "answer": "A", "explanation": "judicious - oqilona, puxta o'ylangan."},
    ],
    "C2": [
        {"question": "Choose the best option: The policy was introduced to ___ the impact of inflation.", "options": ["A) mitigate", "B) provoke", "C) dismantle", "D) conceal"], "answer": "A", "explanation": "mitigate - yumshatmoq."},
        {"question": "Choose the correct sentence.", "options": ["A) Seldom had they encountered such resistance.", "B) Seldom they had encountered such resistance.", "C) Seldom had encountered they such resistance.", "D) Seldom they encountered such resistance."], "answer": "A", "explanation": "Seldom bilan inversion ishlatiladi."},
        {"question": "Choose the best option: Her comments were so ___ that the board postponed the vote.", "options": ["A) incisive", "B) decorative", "C) passive", "D) casual"], "answer": "A", "explanation": "incisive - o'tkir, chuqur va aniq fikr."},
    ],
}

_FALLBACK_IQ = [
    {"question": "Which pair follows the same relationship as Book : Read?", "options": ["A) Song : Listen", "B) Chair : Sit", "C) Pen : Write", "D) Road : Walk"], "answer": "C", "explanation": "Book bilan read bevosita asosiy harakat; pen bilan write ham shunday juftlik."},
    {"question": "A clock shows 3:15. What is the angle between the hour hand and the minute hand?", "options": ["A) 0 degrees", "B) 7.5 degrees", "C) 15 degrees", "D) 22.5 degrees"], "answer": "B", "explanation": "Minute hand 90 gradusda, hour hand esa 97.5 gradusda bo'ladi. Farq 7.5 gradus."},
    {"question": "If all flims are drokes and some drokes are plins, which statement must be true?", "options": ["A) All plins are flims", "B) Some plins are flims", "C) Some drokes may be flims", "D) All drokes are flims"], "answer": "C", "explanation": "Berilgan ma'lumotdan flims drokes ichida ekanini bilamiz, lekin plins bilan to'liq kesishma majburiy emas."},
    {"question": "Which number should replace the question mark? 5, 9, 17, 33, ?", "options": ["A) 49", "B) 57", "C) 65", "D) 71"], "answer": "C", "explanation": "Farqlar 4, 8, 16 bo'lib boryapti. Keyingisi 32. 33 + 32 = 65."},
    {"question": "Choose the odd one out.", "options": ["A) Violin", "B) Cello", "C) Flute", "D) Harp"], "answer": "C", "explanation": "Flute puflab chalinadi, qolganlari torli cholg'ular."},
    {"question": "If yesterday was two days before Thursday, what day is tomorrow?", "options": ["A) Wednesday", "B) Thursday", "C) Friday", "D) Saturday"], "answer": "A", "explanation": "Ikki kun oldin Thursday bo'lsa, yesterday Tuesday bo'ladi. Demak, tomorrow Wednesday."},
    {"question": "Which figure best completes the pattern? Circle, triangle, circle, triangle, ?", "options": ["A) Square", "B) Circle", "C) Triangle", "D) Pentagon"], "answer": "B", "explanation": "Ketma-ketlik navbat bilan circle va triangle bo'lib ketyapti."},
    {"question": "A train travels 60 km in 45 minutes. At the same speed, how far does it travel in 2 hours?", "options": ["A) 120 km", "B) 150 km", "C) 160 km", "D) 180 km"], "answer": "C", "explanation": "45 daqiqada 60 km bo'lsa, 1 soatda 80 km. 2 soatda 160 km."},
]

_FALLBACK_IQ_UZ = [
    {"question": "Book : Read munosabatiga eng yaqin juftlik qaysi?", "options": ["A) Song : Listen", "B) Chair : Sit", "C) Pen : Write", "D) Road : Walk"], "answer": "C", "explanation": "Book bilan read kabi, pen bilan write ham asbob va asosiy harakat munosabatida."},
    {"question": "Soat 3:15 ni ko'rsatmoqda. Soat mili bilan minut mili orasidagi burchak necha gradus?", "options": ["A) 0 gradus", "B) 7.5 gradus", "C) 15 gradus", "D) 22.5 gradus"], "answer": "B", "explanation": "Minute hand 90 gradusda, hour hand 97.5 gradusda bo'ladi. Farq 7.5 gradus."},
    {"question": "Barcha flimslar droke bo'lsa, va ba'zi drokeler plin bo'lsa, qaysi fikr albatta to'g'ri?", "options": ["A) Barcha plinlar flim", "B) Ba'zi plinlar flim", "C) Ba'zi drokeler flim bo'lishi mumkin", "D) Barcha drokeler flim"], "answer": "C", "explanation": "Berilgan ma'lumot faqat flimslar droke ekanini aniq beradi; qolganlari majburiy xulosa emas."},
    {"question": "Qaysi son o'rniga keladi? 5, 9, 17, 33, ?", "options": ["A) 49", "B) 57", "C) 65", "D) 71"], "answer": "C", "explanation": "Farqlar 4, 8, 16 bo'lib ketyapti. Keyingisi 32. 33 + 32 = 65."},
    {"question": "Qaysi biri boshqalariga o'xshamaydi?", "options": ["A) Violin", "B) Cello", "C) Flute", "D) Harp"], "answer": "C", "explanation": "Flute puflab chalinadi, qolganlari torli cholg'ular."},
    {"question": "Agar kecha payshanbadan ikki kun oldin bo'lgan bo'lsa, ertaga qaysi kun bo'ladi?", "options": ["A) Chorshanba", "B) Payshanba", "C) Juma", "D) Shanba"], "answer": "A", "explanation": "Kecha seshanba bo'ladi, demak ertaga chorshanba."},
]


def _escape_html(text: str) -> str:
    return html.escape(str(text or ""))


def _looks_uzbek(text: str) -> bool:
    if not text:
        return False
    if _BAD_CYRILLIC.search(text):
        return True
    low = text.lower()
    return any(word in low for word in _UZ_WORDS)


def _normalize_options(options):
    if not isinstance(options, list) or len(options) != 4:
        return None
    letters = ["A", "B", "C", "D"]
    result = []
    for i, option in enumerate(options):
        if not isinstance(option, str):
            return None
        clean = re.sub(r"^[A-D]\)?\s*", "", option.strip())
        clean = re.sub(r"\\([.,!?;:])", r"\1", clean)
        result.append(f"{letters[i]}) {clean}")
    return result


def _question_key(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def _validate_quiz_data(data: dict, qtype: str, language: str = "en"):
    if not isinstance(data, dict):
        return None
    question = re.sub(r"\\([.,!?;:])", r"\1", str(data.get("question", "")).strip())
    options = _normalize_options(data.get("options", []))
    answer = str(data.get("answer", "")).strip().upper()[:1]
    explanation = re.sub(r"\\([.,!?;:])", r"\1", str(data.get("explanation", "")).strip())
    if not question or not options or answer not in ("A", "B", "C", "D"):
        return None
    if language == "en" and (_looks_uzbek(question) or any(_looks_uzbek(opt) for opt in options)):
        return None
    if qtype == "iq" and _is_trivial_iq_question(question):
        return None
    return {"question": question, "options": options, "answer": answer, "explanation": explanation}



def _build_count_markup(qtype: str):
    counts = IQ_COUNT_OPTIONS if qtype == "iq" else QUIZ_COUNT_OPTIONS
    rows = [[InlineKeyboardButton(f"{count} ta savol", callback_data=f"qpick_{qtype}_{count}")] for count in counts]
    rows.append([InlineKeyboardButton("\U0001F519 Menyu", callback_data="menu_back")])
    return InlineKeyboardMarkup(rows)


def _build_timeout_markup(qtype: str, total_questions: int):
    rows = [[InlineKeyboardButton(f"{seconds} soniya", callback_data=f"qtime_{qtype}_{total_questions}_{seconds}")] for seconds in QUESTION_TIMEOUT_OPTIONS]
    rows.append([InlineKeyboardButton("\U0001F519 Menyu", callback_data="menu_back")])
    return InlineKeyboardMarkup(rows)


def _build_language_markup(qtype: str, total_questions: int, timeout_seconds: int):
    rows = [
        [InlineKeyboardButton("English", callback_data=f"qlang_{qtype}_{total_questions}_{timeout_seconds}_en")],
        [InlineKeyboardButton("O'zbekcha", callback_data=f"qlang_{qtype}_{total_questions}_{timeout_seconds}_uz")],
        [InlineKeyboardButton("🔙 Menyu", callback_data="menu_back")],
    ]
    return InlineKeyboardMarkup(rows)


def _build_iq_language_markup(total_questions: int, timeout_seconds: int):
    return _build_language_markup("iq", total_questions, timeout_seconds)


def _is_trivial_iq_question(question: str) -> bool:
    low = (question or "").lower()
    bad_patterns = [
        r"2\s*,\s*4\s*,\s*8\s*,\s*16",
        r"1\s*,\s*1\s*,\s*2\s*,\s*3\s*,\s*5",
        r"what comes next in the sequence",
        r"which number comes next",
        r"what number comes next",
        r"which number should come next",
        r"what comes next",
        r"quyidagi raqamlar ketma",
        r"ushbu raqamlar ketma",
        r"qaysi raqam kelishi mumkin",
        r"qaysi son o'rniga",
    ]
    return any(re.search(pattern, low) for pattern in bad_patterns)


def _estimate_question_difficulty(data: dict, qtype: str) -> float:
    question = (data.get("question") or "").lower()
    score = 1.0
    if qtype == "iq":
        if any(token in question for token in ("angle", "clock", "relationship", "must be true", "analogy", "if all", "spatial", "figure")):
            score += 0.6
        if any(token in question for token in ("train", "minutes", "hours", "distance", "probability", "order")):
            score += 0.4
        if any(char.isdigit() for char in question):
            score += 0.15
        if _is_trivial_iq_question(question):
            score -= 0.5
    else:
        if any(token in question for token in ("conditional", "reported", "passive", "perfect", "inversion", "article")):
            score += 0.4
    return max(0.7, min(2.0, round(score, 2)))


def _localize_quiz_fallback_row(row: dict, language: str) -> dict:
    if language != "uz":
        return dict(row)
    question = row.get("question", "")
    replacements = {
        "Choose the correct form:": "To'g'ri shaklni tanlang:",
        "Choose the correct word:": "To'g'ri variantni tanlang:",
        "Choose the correct sentence.": "To'g'ri gapni tanlang.",
        "Choose the correct article:": "To'g'ri artiklni tanlang:",
        "Choose the correct pronoun:": "To'g'ri olmoshni tanlang:",
        "Choose the best option:": "Eng to'g'ri variantni tanlang:",
    }
    for src, dst in replacements.items():
        if question.startswith(src):
            question = question.replace(src, dst, 1)
            break
    cloned = dict(row)
    cloned["question"] = question
    return cloned


async def _safe_edit_or_send(context, chat_id: int, message_id: int | None, text: str, reply_markup=None, parse_mode="HTML"):
    if message_id:
        try:
            await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)
            return {"chat_id": chat_id, "message_id": message_id}
        except Exception:
            pass
    sent = await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)
    return {"chat_id": sent.chat_id, "message_id": sent.message_id}



def _build_question_markup(user_id: int, qtype: str, options):
    rows = [[InlineKeyboardButton(option, callback_data=f"qans_{user_id}_{option[0]}_{qtype}")] for option in options]
    rows.append([InlineKeyboardButton("\U0001F6D1 Tugatish", callback_data=f"qans_{user_id}_stop_{qtype}")])
    return InlineKeyboardMarkup(rows)


async def _reply_or_edit_message(target, text, reply_markup=None, parse_mode="HTML"):
    try:
        return await target.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception:
        return await target.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)


async def _cancel_timeout_job(context, user_id: int):
    if not getattr(context, "job_queue", None):
        return
    for job in context.job_queue.get_jobs_by_name(f"quiz_timeout_{user_id}"):
        try:
            job.schedule_removal()
        except Exception:
            pass


async def _cancel_countdown_job(context, user_id: int):
    if not getattr(context, "job_queue", None):
        return
    for job in context.job_queue.get_jobs_by_name(f"quiz_countdown_{user_id}"):
        try:
            job.schedule_removal()
        except Exception:
            pass


async def _limit_check(update_or_query, user_id, field):
    allowed, used, limit = check_limit(user_id, field)
    if allowed:
        return True
    plan = get_user_plan(user_id)
    icon = PLAN_ICONS.get(plan.get("plan_name", "free"), "\U0001F193")
    limit_text = f"{limit}" if limit != -1 else "\u221e"
    text = (
        f"\u26A0\ufe0f *Kunlik limit tugadi!*\n\n"
        f"Sizning rejangiz: {icon} {plan.get('display_name', 'Free')}\n"
        f"Limit: {limit_text}/kun | Ishlatilgan: {used}\n\n"
        "Limitni oshirish uchun obuna oling."
    )
    markup = InlineKeyboardMarkup([[InlineKeyboardButton("\U0001F48E Pro obuna olish", callback_data="sub_choose_pro")]])
    if isinstance(update_or_query, Update) and update_or_query.message:
        await update_or_query.message.reply_text(text, reply_markup=markup, parse_mode="Markdown")
    else:
        await update_or_query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")
    return False


async def _generate_ai_question(level: str, qtype: str, language: str = "en", recent_keys: set[str] | None = None):
    if qtype == "iq" and language == "uz":
        mode = "iq_question_uz"
        strict_mode = "iq_question_uz_strict"
    elif qtype == "quiz" and language == "uz":
        mode = "quiz_generate_uz"
        strict_mode = "quiz_generate_uz_strict"
    else:
        mode = "iq_question" if qtype == "iq" else "quiz_generate"
        strict_mode = "iq_question_strict" if qtype == "iq" else "quiz_generate_strict"
    avoid_text = ""
    if recent_keys:
        sample = "; ".join(sorted(list(recent_keys))[:8])
        avoid_text = f"\nOldin ishlatilgan savollarga o'xshatma: {sample}"
    prompt = f"Savol yarat.{avoid_text}"
    data = await ask_json(prompt, mode=mode, level=level)
    data = _validate_quiz_data(data, qtype, language=language)
    if data:
        return data
    data = await ask_json(prompt, mode=strict_mode, level=level)
    return _validate_quiz_data(data, qtype, language=language)


async def _generate_unique_question(level: str, qtype: str, used_questions: set[str], language: str = "en"):
    for _ in range(6):
        data = await _generate_ai_question(level, qtype, language=language, recent_keys=used_questions)
        if data and _question_key(data["question"]) not in used_questions:
            data["difficulty"] = _estimate_question_difficulty(data, qtype)
            return data

    if qtype == "iq":
        pool = _FALLBACK_IQ_UZ if language == "uz" else _FALLBACK_IQ
    else:
        pool = [_localize_quiz_fallback_row(row, language) for row in _FALLBACK_QUIZ.get(level, _FALLBACK_QUIZ["B1"])]
    unused = [row for row in pool if _question_key(row["question"]) not in used_questions and (qtype != "iq" or not _is_trivial_iq_question(row["question"]))]
    picked = random.choice(unused or pool)
    picked = dict(picked)
    picked["difficulty"] = _estimate_question_difficulty(picked, qtype)
    return picked



def _format_countdown_line(remaining: int, total: int) -> str:
    total = max(total, 1)
    remaining = max(0, remaining)
    ratio = remaining / total
    filled = max(0, min(8, round(ratio * 8)))
    bar = "█" * filled + "░" * (8 - filled)
    return f"<i>\u23F1 {remaining}s qoldi</i>\n<code>{bar}</code>"


def _build_question_text(session) -> str:
    total = session["total_questions"]
    question_no = session["asked"]
    timeout_seconds = int(session.get("question_timeout", QUESTION_TIMEOUT_SECONDS))
    remaining = int(max(0, round(session.get("timeout_at", 0) - time.monotonic())))
    title = f"\U0001F9E0 <b>IQ savol {question_no}/{total}</b>" if session["type"] == "iq" else f"\U0001F3AF <b>Quiz savol {question_no}/{total}</b>"
    return (
        f"{title}\n\n"
        f"{_escape_html(session.get('question_text', ''))}\n\n"
        f"{_format_countdown_line(remaining, timeout_seconds)}"
    )


async def _prefetch_next_question(user_id: int):
    session = active_sessions.get(user_id)
    if not session:
        return
    try:
        data = await _generate_unique_question(
            session["level"],
            session["type"],
            set(session["used_questions"]),
            language=session.get("language", "en"),
        )
        live = active_sessions.get(user_id)
        if live:
            live["prefetched_question"] = data
            active_sessions[user_id] = live
    except Exception:
        return


def _queue_prefetch(user_id: int):
    session = active_sessions.get(user_id)
    if not session:
        return
    if session["asked"] >= session["total_questions"]:
        return
    try:
        session["prefetch_task"] = asyncio.create_task(_prefetch_next_question(user_id))
    except Exception:
        session["prefetch_task"] = None
    active_sessions[user_id] = session


def _quiz_summary_html(session, level_result):
    correct = session["correct"]
    total = max(session["answered"], 1)
    accuracy = round((correct / total) * 100)
    summary = (
        "<b>Quiz yakunlandi!</b>\n\n"
        f"Natija: <b>{correct}/{total}</b>\n"
        f"Aniqlik: <b>{accuracy}%</b>\n"
        f"Boshlang'ich daraja: <b>{_escape_html(level_result['old_level'])}</b>\n"
        f"Yangi daraja: <b>{_escape_html(level_result['new_level'])}</b>\n\n"
    )
    if level_result["changed"]:
        summary += f"\U0001F4C8 {_escape_html(level_result['reason'])}\n"
    else:
        summary += "\U0001F4CC Daraja hozircha o'zgarmadi.\n"
    return summary


def _iq_summary_html(session, iq_score):
    correct = session["correct"]
    total = max(session["answered"], 1)
    accuracy = round((correct / total) * 100)
    return (
        "<b>IQ testi yakunlandi!</b>\n\n"
        f"Natija: <b>{correct}/{total}</b>\n"
        f"Aniqlik: <b>{accuracy}%</b>\n"
        f"Taxminiy IQ: <b>{iq_score}</b>\n\n"
        "Bu qiymat bot ichidagi mantiqiy test uchun yumshatilgan taxminiy ko'rsatkich."
    )


def _estimate_iq_score(correct: int, total: int, avg_difficulty: float = 1.0) -> int:
    if total <= 0:
        return 92
    accuracy = correct / total
    weighted = max(0.85, min(1.35, avg_difficulty))
    score = 86 + (accuracy * 17) + (min(total, 20) * 0.35) + ((weighted - 1.0) * 10)
    return max(84, min(116, round(score)))


async def _send_quiz_question(chat_id, user_id, context, target_message=None):
    session = active_sessions.get(user_id)
    if not session:
        return
    if session.get("answered", 0) >= session.get("total_questions", 0):
        await _show_result_button(context, user_id, session)
        return
    if session.get("asked", 0) >= session.get("total_questions", 0):
        session["answered"] = max(session.get("answered", 0), session.get("total_questions", 0))
        active_sessions[user_id] = session
        await _show_result_button(context, user_id, session)
        return

    data = session.pop("prefetched_question", None)
    if not data or _question_key(data["question"]) in session["used_questions"]:
        data = await _generate_unique_question(
            session["level"],
            session["type"],
            session["used_questions"],
            language=session.get("language", "en"),
        )
    question_key = _question_key(data["question"])
    session["used_questions"].add(question_key)
    remember_question_key(user_id, session["type"], question_key)
    question_no = min(session["asked"] + 1, session["total_questions"])
    timeout_seconds = int(session.get("question_timeout", QUESTION_TIMEOUT_SECONDS))

    session["answer"] = data["answer"]
    session["explanation"] = data["explanation"]
    session["asked"] = question_no
    session["question_text"] = data["question"]
    session["options"] = data["options"]
    session["timeout_at"] = time.monotonic() + timeout_seconds
    session["current_question_key"] = question_key
    session["current_difficulty"] = float(data.get("difficulty", 1.0) or 1.0)
    active_sessions[user_id] = session
    text = _build_question_text(session)
    markup = _build_question_markup(user_id, session["type"], data["options"])

    if target_message is not None:
        try:
            sent = await target_message.edit_text(text, reply_markup=markup, parse_mode="HTML")
        except Exception:
            sent = await context.bot.send_message(chat_id, text, reply_markup=markup, parse_mode="HTML")
    else:
        sent = await context.bot.send_message(chat_id, text, reply_markup=markup, parse_mode="HTML")

    session["message_id"] = sent.message_id
    session["chat_id"] = sent.chat_id
    active_sessions[user_id] = session

    await _cancel_timeout_job(context, user_id)
    await _cancel_countdown_job(context, user_id)
    if getattr(context, "job_queue", None):
        context.job_queue.run_once(
            _question_timeout_job,
            when=timeout_seconds,
            name=f"quiz_timeout_{user_id}",
            data={"user_id": user_id, "message_id": sent.message_id, "chat_id": sent.chat_id},
        )
        context.job_queue.run_repeating(
            _countdown_job,
            interval=COUNTDOWN_TICK_SECONDS,
            first=COUNTDOWN_TICK_SECONDS,
            name=f"quiz_countdown_{user_id}",
            data={"user_id": user_id, "message_id": sent.message_id, "chat_id": sent.chat_id},
        )
    _queue_prefetch(user_id)



async def _show_result_button(context, user_id: int, session):
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("\U0001F4CA Natijani ko'rish", callback_data=f"qresult_{user_id}_{session['type']}")],
    ])
    message_ref = await _safe_edit_or_send(
        context,
        session["chat_id"],
        session.get("message_id"),
        session.get("last_feedback", "Natija tayyor."),
        reply_markup=markup,
        parse_mode="HTML",
    )
    session["chat_id"] = message_ref["chat_id"]
    session["message_id"] = message_ref["message_id"]
    active_sessions[user_id] = session


async def _finish_session_by_message(context, user_id, chat_id, message_id, qtype, stopped=False):
    await _cancel_timeout_job(context, user_id)
    await _cancel_countdown_job(context, user_id)
    session = active_sessions.pop(user_id, None) or {}
    answered = int(session.get("answered", 0) or 0)
    correct = int(session.get("correct", 0) or 0)
    level_before = session.get("level", "A1")

    if answered == 0:
        text = "\U0001F6D1 <b>Test to'xtatildi.</b>\n\nHech qanday savol ishlanmadi."
        summary_text = "Test savollari ishlanmagan."
        iq_score = None
    elif qtype == "iq":
        rows = session.get("history", [])
        avg_difficulty = 1.0
        if rows:
            diff_values = [float(row.get("difficulty", 1.0) or 1.0) for row in rows]
            avg_difficulty = sum(diff_values) / max(len(diff_values), 1)
        iq_score = _estimate_iq_score(correct, answered, avg_difficulty=avg_difficulty)
        add_quiz_attempt(user_id, "iq", level_before, level_before, correct, answered, iq_score=iq_score)
        set_iq_score(user_id, iq_score)
        text = _iq_summary_html(session, iq_score)
        summary_text = f"IQ test natijasi: {correct}/{answered}, aniqlik {round((correct / max(answered, 1)) * 100)}%, taxminiy IQ {iq_score}."
    else:
        level_result = auto_adjust_level_from_quiz(user_id, level_before, correct, answered)
        add_quiz_attempt(user_id, "quiz", level_before, level_result["new_level"], correct, answered, iq_score=0)
        text = _quiz_summary_html(session, level_result)
        summary_text = (
            f"Quiz natijasi: {correct}/{answered}, aniqlik {round((correct / max(answered, 1)) * 100)}%."
            f" Daraja: {level_result['old_level']} -> {level_result['new_level']}."
        )
        iq_score = None

    feedback = session.get("last_feedback")
    if feedback and not stopped:
        text = f"{feedback}\n\n\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n{text}"

    await _safe_edit_or_send(
        context,
        chat_id,
        message_id,
        text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001F3E0 Menyu", callback_data="menu_back")]]),
        parse_mode="HTML",
    )
    try:
        doc = render_html_document(
            "quiz_result.html",
            {
                "title": "IQ Result" if qtype == "iq" else "Quiz Result",
                "user_name": session.get("user_name", str(user_id)),
                "qtype": "IQ" if qtype == "iq" else "Quiz",
                "level": session.get("level", "A1"),
                "correct": correct,
                "total": answered,
                "iq_score": iq_score,
                "summary": summary_text,
                "rows": session.get("history", []),
                "theme_seed": f"{qtype}:{user_id}:{level_before}:{correct}:{answered}",
            },
            f"{qtype}_result_{user_id}.html",
        )
        await context.bot.send_document(chat_id, doc, filename=doc.name, caption=html_open_guide())
    except Exception:
        try:
            await context.bot.send_message(chat_id, "Quiz HTML faylini yuborishda muammo chiqdi, lekin natija tayyor.")
        except Exception:
            pass


async def _question_timeout_job(context: ContextTypes.DEFAULT_TYPE):
    data = context.job.data or {}
    user_id = data.get("user_id")
    session = active_sessions.get(user_id)
    if not session:
        return
    if session.get("message_id") != data.get("message_id"):
        return

    await _cancel_countdown_job(context, user_id)
    session["answered"] += 1
    explanation = _escape_html(session.get("explanation", ""))
    session["last_feedback"] = (
        f"\u23F1 <b>Vaqt tugadi.</b>\n\n"
        f"To'g'ri javob: <b>{_escape_html(session.get('answer', 'A'))}</b>\n"
        f"\U0001F4A1 {explanation}"
    )
    session.setdefault("history", []).append({
        "question": session.get("question_text", ""),
        "options": list(session.get("options", [])),
        "user_answer": "Vaqt tugadi",
        "correct_answer": session.get("answer", "A"),
        "is_correct": False,
        "explanation": session.get("explanation", ""),
        "difficulty": float(session.get("current_difficulty", 1.0) or 1.0),
    })
    active_sessions[user_id] = session

    if session["answered"] >= session["total_questions"]:
        await _show_result_button(context, user_id, session)
        return

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("\u27A1\ufe0f Keyingi savol", callback_data=f"qnext_{user_id}_{session['type']}")],
        [InlineKeyboardButton("\U0001F6D1 Tugatish", callback_data=f"qans_{user_id}_stop_{session['type']}")],
    ])
    message_ref = await _safe_edit_or_send(
        context,
        session["chat_id"],
        session.get("message_id"),
        session["last_feedback"],
        reply_markup=markup,
        parse_mode="HTML",
    )
    session["chat_id"] = message_ref["chat_id"]
    session["message_id"] = message_ref["message_id"]
    active_sessions[user_id] = session


async def _countdown_job(context: ContextTypes.DEFAULT_TYPE):
    data = context.job.data or {}
    user_id = data.get("user_id")
    session = active_sessions.get(user_id)
    if not session:
        try:
            context.job.schedule_removal()
        except Exception:
            pass
        return
    if session.get("message_id") != data.get("message_id"):
        try:
            context.job.schedule_removal()
        except Exception:
            pass
        return
    remaining = int(max(0, round(session.get("timeout_at", 0) - time.monotonic())))
    if remaining <= 0:
        try:
            context.job.schedule_removal()
        except Exception:
            pass
        return
    try:
        await context.bot.edit_message_text(
            chat_id=session["chat_id"],
            message_id=session["message_id"],
            text=_build_question_text(session),
            reply_markup=_build_question_markup(user_id, session["type"], session.get("options", [])),
            parse_mode="HTML",
        )
    except Exception:
        try:
            context.job.schedule_removal()
        except Exception:
            pass


async def _start_session(user, chat_id, context, qtype: str, total_questions: int, question_timeout: int, target_message=None, language: str = "en"):
    db_user = get_user(user.id)
    level = (db_user or {}).get("level", "A1")
    if qtype == "iq":
        level = "B1"
    recent_question_keys = set(get_recent_question_keys(user.id, qtype, limit=60))

    active_sessions[user.id] = {
        "type": qtype,
        "user_name": user.first_name or str(user.id),
        "level": level,
        "answer": "A",
        "explanation": "",
        "correct": 0,
        "asked": 0,
        "answered": 0,
        "total_questions": total_questions,
        "used_questions": recent_question_keys,
        "question_timeout": max(15, int(question_timeout or QUESTION_TIMEOUT_SECONDS)),
        "language": language,
        "timeout_at": 0,
        "chat_id": chat_id,
        "message_id": None,
        "last_feedback": "",
        "history": [],
        "prefetched_question": None,
        "prefetch_task": None,
    }
    inc_usage(user.id, "quiz")
    await _send_quiz_question(chat_id, user.id, context, target_message=target_message)


async def quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    upsert_user(user.id, user.username, user.first_name)
    if not await _limit_check(update, user.id, "quiz"):
        return
    await update.message.reply_text(
        "\U0001F3AF <b>Quiz</b>\n\nNechta savol ishlamoqchisiz?",
        reply_markup=_build_count_markup("quiz"),
        parse_mode="HTML",
    )


async def iq_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    upsert_user(user.id, user.username, user.first_name)
    plan = get_user_plan(user.id)
    if not plan.get("iq_test_enabled"):
        await update.message.reply_text(
            "\U0001F9E0 *IQ testi faqat Pro va Premium foydalanuvchilar uchun!*",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001F48E Pro olish", callback_data="sub_choose_pro")]]),
            parse_mode="Markdown",
        )
        return
    if not await _limit_check(update, user.id, "quiz"):
        return
    await update.message.reply_text(
        "\U0001F9E0 <b>IQ testi</b>\n\nNechta savol ishlamoqchisiz?",
        reply_markup=_build_count_markup("iq"),
        parse_mode="HTML",
    )


async def start_quiz_from_callback(query, context, qtype="quiz"):
    user = query.from_user
    upsert_user(user.id, user.username, user.first_name)
    if qtype == "iq":
        plan = get_user_plan(user.id)
        if not plan.get("iq_test_enabled"):
            await query.edit_message_text(
                "\U0001F9E0 *IQ testi faqat Pro va Premium foydalanuvchilar uchun!*",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001F48E Pro olish", callback_data="sub_choose_pro")]]),
                parse_mode="Markdown",
            )
            return
    if not await _limit_check(query, user.id, "quiz"):
        return
    await query.edit_message_text(
        ("\U0001F9E0 <b>IQ testi</b>\n\nNechta savol ishlamoqchisiz?" if qtype == "iq" else "\U0001F3AF <b>Quiz</b>\n\nNechta savol ishlamoqchisiz?"),
        reply_markup=_build_count_markup(qtype),
        parse_mode="HTML",
    )


async def quiz_picker_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, qtype, count_raw = query.data.split("_", 2)
    total_questions = int(count_raw)
    user = query.from_user
    if not await _limit_check(query, user.id, "quiz"):
        return
    await query.edit_message_text(
        ("\U0001F9E0 <b>IQ testi</b>\n\nHar savol uchun vaqtni tanlang." if qtype == "iq" else "\U0001F3AF <b>Quiz</b>\n\nHar savol uchun vaqtni tanlang."),
        reply_markup=_build_timeout_markup(qtype, total_questions),
        parse_mode="HTML",
    )


async def quiz_time_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, qtype, count_raw, timeout_raw = query.data.split("_", 3)
    total_questions = int(count_raw)
    timeout_seconds = int(timeout_raw)
    user = query.from_user
    if not await _limit_check(query, user.id, "quiz"):
        return
    await query.edit_message_text(
        ("\U0001F9E0 <b>IQ testi</b>\n\nSavollar qaysi tilda bo'lsin?" if qtype == "iq" else "\U0001F3AF <b>Quiz</b>\n\nSavollar qaysi tilda bo'lsin?"),
        reply_markup=_build_language_markup(qtype, total_questions, timeout_seconds),
        parse_mode="HTML",
    )


async def quiz_language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, qtype, count_raw, timeout_raw, language = query.data.split("_", 4)
    total_questions = int(count_raw)
    timeout_seconds = int(timeout_raw)
    user = query.from_user
    if not await _limit_check(query, user.id, "quiz"):
        return
    start_text = "\U0001F9E0 <b>IQ testi boshlanmoqda...</b>" if qtype == "iq" else "\U0001F3AF <b>Quiz boshlanmoqda...</b>"
    await query.edit_message_text(start_text, parse_mode="HTML")
    await _start_session(
        user,
        query.message.chat_id,
        context,
        qtype=qtype,
        total_questions=total_questions,
        question_timeout=timeout_seconds,
        target_message=query.message,
        language=language,
    )


async def quiz_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    _, owner_raw, choice, qtype = query.data.split("_", 3)
    owner_id = int(owner_raw)

    if query.from_user.id != owner_id:
        await query.answer("Bu sizning testingiz emas!", show_alert=True)
        return
    await query.answer()

    session = active_sessions.get(owner_id)
    if not session:
        await _safe_edit_or_send(context, query.message.chat_id, getattr(query.message, "message_id", None), "Sessiya tugagan. Yangi quiz boshlang.", parse_mode="HTML")
        return
    if query.message and session.get("message_id") and query.message.message_id != session.get("message_id"):
        await query.answer("Bu eski savol tugmasi. Yangisidan foydalaning.", show_alert=True)
        return

    if choice == "stop":
        await _finish_session_by_message(context, owner_id, session["chat_id"], session["message_id"], qtype, stopped=True)
        return

    if time.monotonic() > session.get("timeout_at", 0):
        await query.answer("Bu savol vaqti tugagan.", show_alert=True)
        return

    await _cancel_timeout_job(context, owner_id)
    await _cancel_countdown_job(context, owner_id)
    session["answered"] += 1
    inc_stat(owner_id, "quiz_played")

    correct_answer = session.get("answer", "A")
    explanation = _escape_html(session.get("explanation", ""))
    is_correct = choice == correct_answer
    if is_correct:
        session["correct"] += 1
        inc_stat(owner_id, "quiz_correct")
        add_points(owner_id, get_reward_setting("quiz_correct_points", 0.5))
        session["last_feedback"] = f"\u2705 <b>To'g'ri!</b>\n\n\U0001F4A1 {explanation}"
    else:
        session["last_feedback"] = (
            f"\u274C <b>Noto'g'ri.</b>\n\n"
            f"To'g'ri javob: <b>{_escape_html(correct_answer)}</b>\n"
            f"\U0001F4A1 {explanation}"
        )

    session.setdefault("history", []).append({
        "question": session.get("question_text", ""),
        "options": list(session.get("options", [])),
        "user_answer": choice,
        "correct_answer": correct_answer,
        "is_correct": is_correct,
        "explanation": session.get("explanation", ""),
        "difficulty": float(session.get("current_difficulty", 1.0) or 1.0),
    })
    active_sessions[owner_id] = session

    if session["answered"] >= session["total_questions"]:
        await _show_result_button(context, owner_id, session)
        return

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("\u27A1\ufe0f Keyingi savol", callback_data=f"qnext_{owner_id}_{qtype}")],
        [InlineKeyboardButton("\U0001F6D1 Tugatish", callback_data=f"qans_{owner_id}_stop_{qtype}")],
    ])
    message_ref = await _safe_edit_or_send(
        context,
        session["chat_id"],
        session.get("message_id"),
        session["last_feedback"],
        reply_markup=markup,
        parse_mode="HTML",
    )
    session["chat_id"] = message_ref["chat_id"]
    session["message_id"] = message_ref["message_id"]
    active_sessions[owner_id] = session


async def quiz_next_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    parts = query.data.split("_")
    owner_id = int(parts[1])
    qtype = parts[2] if len(parts) > 2 else "quiz"

    if query.from_user.id != owner_id:
        await query.answer("Bu sizning testingiz emas!", show_alert=True)
        return
    await query.answer()

    session = active_sessions.get(owner_id)
    if not session:
        await _safe_edit_or_send(context, query.message.chat_id, getattr(query.message, "message_id", None), "Sessiya tugagan. Yangi quiz boshlang.", parse_mode="HTML")
        return
    if query.message and session.get("message_id") and query.message.message_id != session.get("message_id"):
        await query.answer("Bu eski savol tugmasi. Yangisidan foydalaning.", show_alert=True)
        return
    if session.get("answered", 0) >= session.get("total_questions", 0):
        await _show_result_button(context, owner_id, session)
        return

    await _send_quiz_question(query.message.chat_id, owner_id, context, target_message=query.message)


async def quiz_result_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    _, owner_raw, qtype = query.data.split("_", 2)
    owner_id = int(owner_raw)
    if query.from_user.id != owner_id:
        await query.answer("Bu sizning testingiz emas!", show_alert=True)
        return
    await query.answer()
    session = active_sessions.get(owner_id)
    if not session:
        await _safe_edit_or_send(context, query.message.chat_id, getattr(query.message, "message_id", None), "Sessiya tugagan. Yangi test boshlang.", parse_mode="HTML")
        return
    await _finish_session_by_message(context, owner_id, session["chat_id"], session["message_id"], qtype)
