"""
Quiz handlers — /quiz, /iqtest, question flow, result display with HTML report.
DB-backed sessions replace the old in-memory dict.
"""

import asyncio
import json
import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from src.bot.utils.telegram import safe_reply, safe_edit, safe_answer_callback, escape_html
from src.services import ai_service
from src.services.level_service import auto_adjust_from_quiz, calculate_iq_score
from src.database.dao import quiz_dao, stats_dao, subscription_dao, user_dao

logger = logging.getLogger(__name__)
router = Router(name="quiz")
_QUIZ_TIMEOUT_TASKS: dict[int, asyncio.Task] = {}

# Fallback question bank
FALLBACK_QUESTIONS_EN = [
    {"question": "Choose the correct form: She ___ to school every day.", "options": {"A": "go", "B": "goes", "C": "going", "D": "gone"}, "answer": "B", "explanation": "Third person singular uses 'goes'.", "difficulty": 0.2, "key": "fb_she_goes"},
    {"question": "Which is correct?", "options": {"A": "I have went", "B": "I have gone", "C": "I have go", "D": "I have going"}, "answer": "B", "explanation": "Present perfect: have/has + past participle (gone).", "difficulty": 0.3, "key": "fb_have_gone"},
    {"question": "Fill in: If I ___ rich, I would travel.", "options": {"A": "am", "B": "was", "C": "were", "D": "be"}, "answer": "C", "explanation": "Second conditional uses 'were' for all subjects.", "difficulty": 0.5, "key": "fb_if_were"},
    {"question": "Choose: The book ___ on the table.", "options": {"A": "is", "B": "are", "C": "am", "D": "be"}, "answer": "A", "explanation": "'The book' is singular, so we use 'is'.", "difficulty": 0.1, "key": "fb_book_is"},
    {"question": "Which sentence is correct?", "options": {"A": "He don't like pizza", "B": "He doesn't likes pizza", "C": "He doesn't like pizza", "D": "He not like pizza"}, "answer": "C", "explanation": "Negative: doesn't + base form.", "difficulty": 0.3, "key": "fb_doesnt_like"},
]

FALLBACK_QUESTIONS_UZ = [
    {"question": "To'g'ri javobni tanlang: She ___ to school every day.", "options": {"A": "go", "B": "goes", "C": "going", "D": "gone"}, "answer": "B", "explanation": "Uchinchi shaxs birlik 'goes' ishlatadi.", "difficulty": 0.2, "key": "fb_uz_goes"},
    {"question": "Qaysi to'g'ri: I have ___.", "options": {"A": "went", "B": "gone", "C": "go", "D": "going"}, "answer": "B", "explanation": "Present perfect: have + V3 (gone).", "difficulty": 0.3, "key": "fb_uz_gone"},
]


def _get_display_name(user) -> str:
    """Get best display name for user."""
    if not user:
        return "Student"
    if user.username:
        return f"@{user.username}"
    return user.first_name or "Student"


def _cancel_question_timeout(session_id: int) -> None:
    task = _QUIZ_TIMEOUT_TASKS.pop(session_id, None)
    if task and not task.done():
        task.cancel()


async def _question_timeout_worker(chat_id: int, session_id: int, message_id: int, timeout: int):
    try:
        await asyncio.sleep(timeout)
    except asyncio.CancelledError:
        return

    session = await quiz_dao.get_quiz_session(session_id)
    if not session or session["status"] != "active":
        return
    if session.get("message_id") != message_id:
        return
    if session["answered"] >= session["asked"]:
        return

    question = json.loads(session.get("current_question", "{}"))
    correct_answer = question.get("answer", "")
    explanation = question.get("explanation", "")
    history = json.loads(session.get("history", "[]"))
    answered = session["answered"] + 1

    history.append({
        "question": question.get("question", ""),
        "user_answer": "skip",
        "correct_answer": correct_answer,
        "is_correct": False,
    })

    await quiz_dao.update_quiz_session(
        session_id,
        answered=answered,
        history=json.dumps(history, ensure_ascii=False),
    )

    from src.bot.loader import bot

    timeout_text = f"⏰ <b>Vaqt tugadi.</b> Javob: <b>{correct_answer}</b>"
    if explanation:
        timeout_text += f"\n💡 {escape_html(explanation)}"

    try:
        edited = await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=timeout_text,
            parse_mode="HTML",
        )
    except Exception:
        edited = None

    if answered >= session["total_questions"]:
        pivot = edited if isinstance(edited, Message) else await bot.send_message(chat_id, "🏁 Quiz yakunlanmoqda...")
        await _finish_quiz(pivot, session_id)
    else:
        pivot = edited if isinstance(edited, Message) else await bot.send_message(chat_id, "⏭ Keyingi savol...")
        await _send_next_question(pivot, session_id, session["user_id"], session["level"], session["language"])


def _schedule_question_timeout(chat_id: int, session_id: int, message_id: int, timeout: int) -> None:
    _cancel_question_timeout(session_id)
    _QUIZ_TIMEOUT_TASKS[session_id] = asyncio.create_task(
        _question_timeout_worker(chat_id, session_id, message_id, timeout)
    )


@router.message(Command("quiz"))
async def cmd_quiz(message: Message, db_user: dict | None = None):
    """Start a quiz — select question count."""
    if not db_user:
        return

    plan = await subscription_dao.get_user_plan(db_user["user_id"])
    limit = plan.get("quiz_per_day", 5)
    allowed = await stats_dao.check_limit(db_user["user_id"], "quiz", limit)
    if not allowed:
        await safe_reply(message, f"⚠️ Kunlik quiz limiti tugadi ({limit} ta).\n/subscribe — yangilash")
        return

    active = await quiz_dao.get_active_quiz_session(db_user["user_id"])
    if active:
        await safe_reply(message, "⚠️ Sizda faol quiz bor. Avval uni yakunlang.")
        return

    buttons = [
        [
            InlineKeyboardButton(text="5️⃣ 5 ta", callback_data="qpick:5"),
            InlineKeyboardButton(text="🔟 10 ta", callback_data="qpick:10"),
        ],
        [
            InlineKeyboardButton(text="1️⃣5️⃣ 15 ta", callback_data="qpick:15"),
            InlineKeyboardButton(text="2️⃣0️⃣ 20 ta", callback_data="qpick:20"),
        ],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="qpick:cancel")],
    ]
    await safe_reply(
        message,
        "🧠 <b>Quiz boshlash</b>\n\nNechta savol bo'lsin?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )


@router.callback_query(F.data.startswith("qpick:"))
async def callback_quiz_pick_count(callback: CallbackQuery, db_user: dict | None = None):
    """Handle question count selection."""
    value = callback.data.split(":")[1]
    if value == "cancel":
        await safe_answer_callback(callback)
        await safe_edit(callback, "❌ Quiz bekor qilindi.")
        return

    count = int(value)
    buttons = [
        [
            InlineKeyboardButton(text="⏱ 30s", callback_data=f"qtime:{count}:30"),
            InlineKeyboardButton(text="⏱ 45s", callback_data=f"qtime:{count}:45"),
        ],
        [
            InlineKeyboardButton(text="⏱ 60s", callback_data=f"qtime:{count}:60"),
            InlineKeyboardButton(text="⏱ 90s", callback_data=f"qtime:{count}:90"),
        ],
    ]
    await safe_edit(
        callback,
        f"🧠 <b>Quiz — {count} savol</b>\n\nHar bir savol uchun vaqt?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await safe_answer_callback(callback)


@router.callback_query(F.data.startswith("qtime:"))
async def callback_quiz_pick_time(callback: CallbackQuery, db_user: dict | None = None):
    """Handle time selection → select language → start quiz."""
    parts = callback.data.split(":")
    count = int(parts[1])
    timeout = int(parts[2])

    buttons = [
        [
            InlineKeyboardButton(text="🇬🇧 English", callback_data=f"qlang:{count}:{timeout}:en"),
            InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data=f"qlang:{count}:{timeout}:uz"),
        ],
    ]
    await safe_edit(
        callback,
        f"🧠 <b>Quiz — {count} savol, {timeout}s</b>\n\nSavollar tilini tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await safe_answer_callback(callback)


@router.callback_query(F.data.startswith("qlang:"))
async def callback_quiz_start(callback: CallbackQuery, db_user: dict | None = None):
    """Start the quiz session."""
    if not db_user:
        return

    parts = callback.data.split(":")
    count = int(parts[1])
    timeout = int(parts[2])
    lang = parts[3]
    user_id = db_user["user_id"]
    level = db_user.get("level", "A1")

    await stats_dao.inc_usage(user_id, "quiz")

    session_id = await quiz_dao.create_quiz_session(
        user_id=user_id,
        qtype="quiz",
        level=level,
        language=lang,
        total_questions=count,
        question_timeout=timeout,
        chat_id=callback.message.chat.id if callback.message else 0,
    )

    await safe_edit(callback, f"🧠 <b>Quiz #{session_id} boshlandi!</b>\n\n⏳ Birinchi savol tayyorlanmoqda...")
    await safe_answer_callback(callback)
    await _send_next_question(callback.message, session_id, user_id, level, lang)


async def _generate_question(level: str, lang: str, avoid_keys: list[str]) -> dict | None:
    """Generate a quiz question using AI with fallback."""
    mode = "quiz_generate"
    prompt = f"Level: {level}. Language: {'Uzbek' if lang == 'uz' else 'English'}. Generate a question."
    if avoid_keys:
        prompt += f" Avoid keys: {', '.join(avoid_keys[-20:])}"

    result = await ai_service.ask_json(prompt, mode=mode, level=level)

    if result and all(k in result for k in ("question", "options", "answer")):
        opts = result.get("options", {})
        if isinstance(opts, dict) and len(opts) >= 4 and result["answer"] in opts:
            return result

    bank = FALLBACK_QUESTIONS_UZ if lang == "uz" else FALLBACK_QUESTIONS_EN
    for q in bank:
        if q["key"] not in avoid_keys:
            return q.copy()

    return bank[0].copy() if bank else None


async def _send_next_question(message: Message, session_id: int, user_id: int, level: str, lang: str):
    """Generate and send the next question."""
    session = await quiz_dao.get_quiz_session(session_id)
    if not session or session["status"] != "active":
        return

    asked = session["asked"]
    total = session["total_questions"]

    if asked >= total:
        await _finish_quiz(message, session_id)
        return

    used_keys = json.loads(session.get("used_keys", "[]"))
    question = await _generate_question(level, lang, used_keys)
    if not question:
        await safe_reply(message, "❌ Savol generatsiya qilib bo'lmadi.")
        await _finish_quiz(message, session_id)
        return

    key = question.get("key", f"q_{asked}")
    used_keys.append(key)
    await quiz_dao.update_quiz_session(
        session_id,
        asked=asked + 1,
        current_question=json.dumps(question, ensure_ascii=False),
        used_keys=json.dumps(used_keys, ensure_ascii=False),
    )

    q_text = escape_html(question["question"])
    options = question.get("options", {})
    timeout = session["question_timeout"]

    text = (
        f"🧠 <b>Savol {asked + 1}/{total}</b>\n\n"
        f"{q_text}\n\n"
    )
    for letter, opt in sorted(options.items()):
        text += f"  <b>{letter}.</b> {escape_html(opt)}\n"
    text += f"\n⏱ Vaqt: {timeout} soniya"

    buttons = []
    row = []
    for letter in sorted(options.keys()):
        row.append(InlineKeyboardButton(text=letter, callback_data=f"qans:{session_id}:{letter}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="⏭ O'tkazish", callback_data=f"qans:{session_id}:skip")])

    sent = await safe_reply(message, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    if sent:
        await quiz_dao.update_quiz_session(session_id, message_id=sent.message_id)
        _schedule_question_timeout(sent.chat.id, session_id, sent.message_id, timeout)


@router.callback_query(F.data.startswith("qans:"))
async def callback_quiz_answer(callback: CallbackQuery, db_user: dict | None = None):
    """Handle quiz answer."""
    if not db_user:
        return

    parts = callback.data.split(":")
    session_id = int(parts[1])
    answer = parts[2]

    session = await quiz_dao.get_quiz_session(session_id)
    if not session or session["status"] != "active" or session["user_id"] != db_user["user_id"]:
        await safe_answer_callback(callback, "❌ Sessiya topilmadi")
        return

    question = json.loads(session.get("current_question", "{}"))
    correct_answer = question.get("answer", "")
    explanation = question.get("explanation", "")
    history = json.loads(session.get("history", "[]"))
    _cancel_question_timeout(session_id)

    answered = session["answered"] + 1
    correct = session["correct"]
    is_correct = answer == correct_answer and answer != "skip"

    if is_correct:
        correct += 1
        result_text = "✅ <b>To'g'ri!</b>"
    elif answer == "skip":
        result_text = f"⏭ <b>O'tkazildi.</b> Javob: <b>{correct_answer}</b>"
    else:
        result_text = f"❌ <b>Noto'g'ri!</b> To'g'ri javob: <b>{correct_answer}</b>"

    if explanation:
        result_text += f"\n💡 {escape_html(explanation)}"

    history.append({
        "question": question.get("question", ""),
        "user_answer": answer,
        "correct_answer": correct_answer,
        "is_correct": is_correct,
    })

    await quiz_dao.update_quiz_session(
        session_id,
        answered=answered,
        correct=correct,
        history=json.dumps(history, ensure_ascii=False),
    )

    await safe_answer_callback(callback, "✅ To'g'ri!" if is_correct else "❌ Noto'g'ri!")
    await safe_edit(callback, result_text)

    await asyncio.sleep(1.5)

    if answered >= session["total_questions"]:
        await _finish_quiz(callback.message, session_id, tg_user=callback.from_user)
    else:
        await _send_next_question(
            callback.message, session_id,
            db_user["user_id"], session["level"], session["language"],
        )


async def _finish_quiz(message: Message, session_id: int, tg_user=None):
    """Finish quiz session and show results with HTML report."""
    session = await quiz_dao.get_quiz_session(session_id)
    if not session:
        return

    _cancel_question_timeout(session_id)
    await quiz_dao.finish_quiz_session(session_id)

    user_id = session["user_id"]
    correct = session["correct"]
    total = session["total_questions"]
    answered = session["answered"]
    level = session["level"]
    accuracy = (correct / total * 100) if total > 0 else 0
    history = json.loads(session.get("history", "[]"))

    await quiz_dao.record_quiz_attempt(
        user_id=user_id,
        qtype=session["qtype"],
        total=total,
        correct=correct,
        wrong=total - correct,
        mode=session["language"],
        level_before=level,
        level_after=level,
    )

    await stats_dao.inc_stat(user_id, "quiz_played")
    await stats_dao.inc_stat(user_id, "quiz_correct", correct)

    level_result = await auto_adjust_from_quiz(user_id, correct, total, level)

    if accuracy >= 90:
        rating = "🌟 A'lo!"
        emoji = "🏆"
    elif accuracy >= 70:
        rating = "👍 Yaxshi!"
        emoji = "✅"
    elif accuracy >= 50:
        rating = "📚 O'rtacha"
        emoji = "📊"
    else:
        rating = "💪 Mashq qiling"
        emoji = "📖"

    text = (
        f"{emoji} <b>Quiz yakunlandi!</b>\n\n"
        f"📊 <b>Natija:</b>\n"
        f"  ✅ To'g'ri: <b>{correct}/{total}</b>\n"
        f"  📈 Aniqlik: <b>{accuracy:.0f}%</b>\n"
        f"  🏆 Baho: <b>{rating}</b>\n"
    )

    if level_result.get("changed"):
        text += (
            f"\n🎉 <b>Daraja o'zgardi!</b>\n"
            f"  {level_result['old']} → <b>{level_result['new']}</b>\n"
        )

    text += "\n🔄 Yana o'ynash: /quiz"

    # ── HTML report with Private/Public share ──
    username = ""
    if tg_user:
        username = tg_user.username or tg_user.first_name or ""
    elif message and message.from_user:
        username = message.from_user.username or message.from_user.first_name or ""

    kb = None
    try:
        from src.bot.utils.html_report import build_quiz_report
        from src.bot.handlers.user.check import _cache_key, _REPORT_CACHE
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

        html_content = build_quiz_report(
            correct=correct,
            total=total,
            accuracy=accuracy,
            rating=rating,
            history=history,
            level=level,
            level_changed=level_result if level_result.get("changed") else None,
            qtype=session["qtype"],
            username=username,
        )
        html_bytes = html_content.encode("utf-8")
        key = _cache_key(html_content)
        _REPORT_CACHE[key] = (html_bytes, "quiz_hisobot.html", f"🧠 Quiz Hisoboti\n👤 @{username}" if username else "🧠 Quiz Hisoboti")

        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🔒 Private", callback_data=f"rpt_prv:{key}"),
            InlineKeyboardButton(text="📢 Public",  callback_data=f"rpt_pub:{key}"),
        ]])
    except Exception as e:
        logger.warning("quiz html report error: %s", e)

    await safe_reply(message, text, reply_markup=kb)


# ── IQ Test ──

@router.message(Command("iqtest"))
async def cmd_iqtest_quiz(message: Message, db_user: dict | None = None):
    """Start IQ test (Pro+ only) — direct command handler."""
    if not db_user:
        return

    plan = await subscription_dao.get_user_plan(db_user["user_id"])
    if not plan.get("iq_test_enabled"):
        await safe_reply(
            message,
            "🧩 <b>IQ Test</b> faqat Pro va Premium foydalanuvchilar uchun.\n\n"
            "Obunangizni yangilang: /subscribe"
        )
        return

    user_id = db_user["user_id"]
    level = db_user.get("level", "A1")

    session_id = await quiz_dao.create_quiz_session(
        user_id=user_id,
        qtype="iq",
        level=level,
        language="en",
        total_questions=10,
        question_timeout=60,
        chat_id=message.chat.id,
    )

    await safe_reply(message, "🧩 <b>IQ Test boshlandi!</b>\n\n⏳ Birinchi savol tayyorlanmoqda...")
    await _send_next_question(message, session_id, user_id, level, "en")


def get_quiz_router() -> Router:
    return router
