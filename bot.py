
import json
import logging
import os
import re
from datetime import time as dt_time
from uuid import uuid4
from zoneinfo import ZoneInfo

import httpx
from dotenv import load_dotenv
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InputTextMessageContent,
    Update,
    WebAppInfo,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    InlineQueryHandler,
    MessageHandler,
    filters,
)

from database import (
    add_focus_session,
    add_task,
    complete_task,
    enable_daily_subscription,
    ensure_user,
    get_focus_summary,
    get_recent_context,
    get_user_level,
    get_user_stats,
    increment_stat,
    init_db,
    is_feature_enabled,
    list_daily_subscriptions,
    list_feature_states,
    list_tasks,
    log_message,
    save_quiz_result,
    save_webapp_snapshot,
    set_chat_feature,
    set_task_state_by_web_id,
    set_user_level,
)
from openrouter_client import ask_ai
from teacher_content import LEVEL_ORDER, pick_daily_word, pick_quiz_questions, score_to_level

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
DEVELOPER = os.getenv("DEVELOPER_HANDLE", "@murodullayev_web")
WEB_APP_URL = os.getenv("WEB_APP_URL", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
BOT_TIMEZONE = os.getenv("BOT_TIMEZONE", "Asia/Tashkent")
DAILY_WORD_HOUR = int(os.getenv("DAILY_WORD_HOUR", "8"))
DAILY_WORD_MINUTE = int(os.getenv("DAILY_WORD_MINUTE", "0"))

FEATURE_LABELS = {
    "check": "Matn tekshiruv",
    "bot": "AI savol-javob",
    "translate": "Tarjima",
    "quiz": "Quiz",
    "lesson": "Mavzuli dars",
    "tracker": "Pomodoro/Tracker",
}


def _ensure_user(update: Update) -> int:
    user = update.effective_user
    if not user:
        return 0
    ensure_user(user.id, user.username, user.first_name)
    return user.id


def _store_interaction(user_id: int, mode: str, user_text: str, ai_text: str) -> None:
    log_message(user_id, "user", mode, user_text[:4000])
    log_message(user_id, "assistant", mode, ai_text[:4000])


def _build_admin_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    states = list_feature_states(chat_id)
    rows = []
    for feature, title in FEATURE_LABELS.items():
        mark = "ON" if states.get(feature, True) else "OFF"
        rows.append([InlineKeyboardButton(f"{title}: {mark}", callback_data=f"adm:{feature}")])
    return InlineKeyboardMarkup(rows)


def _bar(value: int, max_value: int, width: int = 12) -> str:
    if max_value <= 0:
        return "-" * width
    filled = max(0, min(width, round((value / max_value) * width)))
    return "#" * filled + "-" * (width - filled)


def _focus_chart(rows):
    if not rows:
        return "So'nggi 7 kunda fokus sessiya topilmadi."
    peak = max(item["minutes"] for item in rows) or 1
    lines = []
    for item in rows:
        day_label = item["day"][5:]
        lines.append(f"{day_label} | {_bar(item['minutes'], peak)} {item['minutes']}m")
    return "\n".join(lines)


def _upgrade_level_if_needed(user_id: int, candidate_level: str) -> str:
    current = get_user_level(user_id)
    try:
        if LEVEL_ORDER.index(candidate_level) > LEVEL_ORDER.index(current):
            set_user_level(user_id, candidate_level)
            return candidate_level
        return current
    except ValueError:
        return current


async def _is_group_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    chat = update.effective_chat
    user = update.effective_user
    if not chat or not user:
        return False
    if chat.type == "private":
        return True
    member = await context.bot.get_chat_member(chat.id, user.id)
    return member.status in {"administrator", "creator"}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = _ensure_user(update)
    name = update.effective_user.first_name if update.effective_user else "Do'st"
    text = (
        f"Salom, {name}!\n\n"
        "Men sizning Artificial Teacher botingizman.\n"
        "AI asosida: grammatika, tarjima, quiz, dars, tracker va WebApp sinxron ishlaydi.\n\n"
        "Tezkor komandalar:\n"
        "/quiz - 5 ta test\n"
        "/lesson travel - mavzuli dars\n"
        "/mystats - shaxsiy statistika\n"
        "/tracker - fokus va task holati\n"
        "/help - barcha buyruqlar"
    )

    keyboard = [
        [
            InlineKeyboardButton("Matn tekshiruv", callback_data="info:check"),
            InlineKeyboardButton("AI savol-javob", callback_data="info:ask"),
        ],
        [
            InlineKeyboardButton("Quiz boshlash", callback_data="info:quiz"),
            InlineKeyboardButton("Kunlik soz", callback_data="info:daily"),
        ],
    ]

    if WEB_APP_URL.startswith("http://") or WEB_APP_URL.startswith("https://"):
        keyboard.append([InlineKeyboardButton("Open WebApp (Pomodoro)", web_app=WebAppInfo(url=WEB_APP_URL))])
    else:
        keyboard.append([InlineKeyboardButton("WebApp URL sozlanmagan", callback_data="info:webapp")])

    keyboard.append([InlineKeyboardButton("Dasturchi", url=f"https://t.me/{DEVELOPER.lstrip('@')}")])
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    if user_id:
        log_message(user_id, "assistant", "system", "start command")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "Asosiy buyruqlar:\n"
        "/start - bosh menu\n"
        "/help - yordam\n"
        "/quiz - grammatika testi (5 savol)\n"
        "/mystats - statistikangiz\n"
        "/mylevel - hozirgi daraja\n"
        "/setlevel A1|A2|B1|B2|C1|C2 - qo'lda daraja o'rnatish\n"
        "/lesson <mavzu> - mavzuga oid mini dars\n"
        "/uz2en <matn> - o'zbekchadan inglizchaga\n"
        "/pronounce <word> - talaffuz + IPA\n"
        "/focus <daqiqa> - qo'lda fokus sessiya qo'shish\n"
        "/task add <nom> | /task done <id> | /task list\n"
        "/tracker - fokus chart + tasklar\n"
        "/daily_on va /daily_off - kunlik so'z obunasi\n"
        "/admin - guruhda feature ON/OFF panel\n\n"
        "Guruh kalitlari:\n"
        "#check - grammatik tekshiruv\n"
        "#bot - AI savol-javob\n"
        "#t - tarjima\n\n"
        "Inline mode:\n"
        "Istalgan chatda @BotUsername so'rov yozing."
    )
    await update.message.reply_text(help_text)


async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Artificial Teacher Bot\n"
        "AI: OpenRouter\n"
        "Qo'shimcha: Quiz, Level, Tracker, WebApp sync\n"
        f"Dasturchi: {DEVELOPER}"
    )


async def contact_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Taklif va yordam uchun yozing: {DEVELOPER}")


async def webapp_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if WEB_APP_URL.startswith("http://") or WEB_APP_URL.startswith("https://"):
        keyboard = [[InlineKeyboardButton("Open WebApp", web_app=WebAppInfo(url=WEB_APP_URL))]]
        await update.message.reply_text(
            "Pomodoro + tracker mini-appni ochish uchun tugmani bosing.",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    else:
        await update.message.reply_text(
            "WEB_APP_URL sozlanmagan. .env ichiga public https URL yozing."
        )


async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("Tenses", callback_data="rule:tenses"),
            InlineKeyboardButton("Articles", callback_data="rule:articles"),
        ],
        [
            InlineKeyboardButton("Prepositions", callback_data="rule:prepositions"),
            InlineKeyboardButton("Conditionals", callback_data="rule:conditionals"),
        ],
        [InlineKeyboardButton("Passive Voice", callback_data="rule:passive")],
    ]
    await update.message.reply_text(
        "Qaysi grammatika mavzusi kerak?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def mylevel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = _ensure_user(update)
    level = get_user_level(user_id)
    await update.message.reply_text(f"Sizning hozirgi darajangiz: {level}")


async def setlevel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = _ensure_user(update)
    if not context.args:
        await update.message.reply_text("Namuna: /setlevel B1")
        return
    level = context.args[0].upper().strip()
    if level not in LEVEL_ORDER:
        await update.message.reply_text("Daraja faqat: A1, A2, B1, B2, C1, C2")
        return
    set_user_level(user_id, level)
    await update.message.reply_text(f"Daraja saqlandi: {level}")


async def quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = _ensure_user(update)
    chat_id = update.effective_chat.id if update.effective_chat else 0
    if chat_id and not is_feature_enabled(chat_id, "quiz"):
        await update.message.reply_text("Bu chatda quiz vaqtincha o'chirilgan.")
        return

    questions = pick_quiz_questions(5)
    context.user_data["quiz"] = {"questions": questions, "index": 0, "correct": 0}
    await update.message.reply_text("Quiz boshlandi! 5 ta savol bo'ladi.")
    await _send_quiz_question(update.message, context)
    increment_stat(user_id, "quizzes", 0)


async def _send_quiz_question(message_obj, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get("quiz")
    if not state:
        return
    index = state["index"]
    questions = state["questions"]
    if index >= len(questions):
        return

    q = questions[index]
    options = q["options"]
    keyboard = []
    for option_index, option in enumerate(options):
        keyboard.append(
            [InlineKeyboardButton(f"{chr(65 + option_index)}. {option}", callback_data=f"qz:{index}:{option_index}")]
        )
    text = f"Savol {index + 1}/{len(questions)}\n{q['question']}"
    await message_obj.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def _finish_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    state = context.user_data.get("quiz")
    if not state:
        return
    correct = state["correct"]
    total = len(state["questions"])
    ratio = (correct / total) if total else 0
    estimated = score_to_level(ratio)
    final_level = _upgrade_level_if_needed(user_id, estimated)
    save_quiz_result(user_id, correct, total)

    msg = (
        f"Quiz tugadi.\n"
        f"Natija: {correct}/{total} ({round(ratio * 100)}%)\n"
        f"Tavsiyaviy daraja: {estimated}\n"
        f"Sizning saqlangan darajangiz: {final_level}"
    )
    await update.effective_message.reply_text(msg)
    context.user_data.pop("quiz", None)


async def lesson_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = _ensure_user(update)
    chat_id = update.effective_chat.id if update.effective_chat else 0
    if chat_id and not is_feature_enabled(chat_id, "lesson"):
        await update.message.reply_text("Bu chatda dars funksiyasi o'chirilgan.")
        return

    if not context.args:
        await update.message.reply_text("Namuna: /lesson travel")
        return

    topic = " ".join(context.args).strip()
    level = get_user_level(user_id)
    prompt = f"Mavzu: {topic}. Foydalanuvchi darajasi: {level}. Darsni shunga mosla."
    history = get_recent_context(user_id, limit=4)
    await update.message.reply_text("Dars tayyorlanmoqda...")
    response = await ask_ai(prompt, mode="lesson", context=history, max_tokens=1400, temperature=0.45)
    await update.message.reply_text(response)
    increment_stat(user_id, "questions")
    _store_interaction(user_id, "lesson", prompt, response)


async def uz2en_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = _ensure_user(update)
    if not context.args:
        await update.message.reply_text("Namuna: /uz2en Men bugun ingliz tilini o'rganyapman")
        return
    text = " ".join(context.args).strip()
    response = await ask_ai(text, mode="uz_to_en", context=get_recent_context(user_id, 4), max_tokens=600)
    await update.message.reply_text(response)
    increment_stat(user_id, "translations")
    _store_interaction(user_id, "uz_to_en", text, response)


async def pronounce_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = _ensure_user(update)
    if not context.args:
        await update.message.reply_text("Namuna: /pronounce thought")
        return
    word = " ".join(context.args).strip()
    response = await ask_ai(word, mode="pronunciation", max_tokens=500)
    await update.message.reply_text(response)
    increment_stat(user_id, "questions")
    _store_interaction(user_id, "pronunciation", word, response)


async def mystats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = _ensure_user(update)
    stats = get_user_stats(user_id)
    focus_rows = get_focus_summary(user_id, days=7)

    total_quiz = stats["quiz_total"] or 0
    acc = round((stats["quiz_correct"] / total_quiz) * 100) if total_quiz else 0

    text = (
        "Sizning statistikangiz\n\n"
        f"Daraja: {stats['level']}\n"
        f"Tekshiruvlar: {stats['checks']}\n"
        f"AI savollar: {stats['questions']}\n"
        f"Tarjimalar: {stats['translations']}\n"
        f"Quiz: {stats['quizzes']} ta (aniqlik: {acc}%)\n"
        f"Fokus daqiqalari: {stats['focus_minutes']} min\n"
        f"Tasklar: {stats['tasks_done']}/{stats['tasks_created']} bajarilgan\n\n"
        "7 kunlik fokus diagramma:\n"
        f"{_focus_chart(focus_rows)}"
    )
    await update.message.reply_text(text)


async def focus_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = _ensure_user(update)
    if not context.args:
        await update.message.reply_text("Namuna: /focus 25")
        return
    try:
        minutes = int(context.args[0])
        if minutes <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Daqiqa musbat son bo'lishi kerak. Masalan: /focus 25")
        return

    add_focus_session(user_id, minutes, source="bot")
    await update.message.reply_text(f"Fokus sessiya saqlandi: {minutes} daqiqa.")


async def task_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = _ensure_user(update)
    if not context.args:
        await update.message.reply_text("Namuna: /task add Reading practice | /task done 3 | /task list")
        return

    action = context.args[0].lower().strip()
    if action == "add":
        title = " ".join(context.args[1:]).strip()
        if not title:
            await update.message.reply_text("Task nomini yozing. Namuna: /task add Daily listening 20 min")
            return
        task_id = add_task(user_id, title, source="bot")
        await update.message.reply_text(f"Task qo'shildi. ID: {task_id}")
        return

    if action == "done":
        if len(context.args) < 2:
            await update.message.reply_text("Namuna: /task done 3")
            return
        try:
            task_id = int(context.args[1])
        except ValueError:
            await update.message.reply_text("Task ID son bo'lishi kerak.")
            return
        ok = complete_task(user_id, task_id)
        await update.message.reply_text("Task yakunlandi." if ok else "Bunday task topilmadi.")
        return

    if action == "list":
        tasks = list_tasks(user_id, only_open=False, limit=20)
        if not tasks:
            await update.message.reply_text("Tasklar hozircha yo'q.")
            return
        lines = []
        for item in tasks:
            marker = "?" if item["status"] == "done" else "?"
            lines.append(f"{marker} #{item['id']} {item['title']}")
        await update.message.reply_text("Tasklar:\n" + "\n".join(lines))
        return

    await update.message.reply_text("Noto'g'ri format. /task add|done|list dan foydalaning.")


async def tracker_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = _ensure_user(update)
    chat_id = update.effective_chat.id if update.effective_chat else 0
    if chat_id and not is_feature_enabled(chat_id, "tracker"):
        await update.message.reply_text("Bu chatda tracker funksiyasi o'chirilgan.")
        return

    stats = get_user_stats(user_id)
    focus_rows = get_focus_summary(user_id, days=7)
    open_tasks = list_tasks(user_id, only_open=True, limit=5)
    open_task_text = "\n".join([f"- #{t['id']} {t['title']}" for t in open_tasks]) if open_tasks else "- Ochiq task yo'q"

    text = (
        "Tracker panel\n\n"
        f"Jami fokus: {stats['focus_minutes']} daqiqa\n"
        f"Bajarilgan tasklar: {stats['tasks_done']}\n\n"
        "So'nggi 7 kun fokus:\n"
        f"{_focus_chart(focus_rows)}\n\n"
        f"Ochiq tasklar:\n{open_task_text}"
    )
    await update.message.reply_text(text)

    if WEB_APP_URL.startswith("http://") or WEB_APP_URL.startswith("https://"):
        keyboard = [[InlineKeyboardButton("WebApp ochish", web_app=WebAppInfo(url=WEB_APP_URL))]]
        await update.message.reply_text("Batafsil diagramma uchun WebApp:", reply_markup=InlineKeyboardMarkup(keyboard))


async def daily_on_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private" and not await _is_group_admin(update, context):
        await update.message.reply_text("Guruhda faqat admin bu funksiyani yoqa oladi.")
        return
    enable_daily_subscription(update.effective_chat.id, True)
    await update.message.reply_text("Kunlik so'z yoqildi.")


async def daily_off_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private" and not await _is_group_admin(update, context):
        await update.message.reply_text("Guruhda faqat admin bu funksiyani o'chira oladi.")
        return
    enable_daily_subscription(update.effective_chat.id, False)
    await update.message.reply_text("Kunlik so'z o'chirildi.")


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        await update.message.reply_text("Admin panel faqat guruh chatlari uchun.")
        return
    if not await _is_group_admin(update, context):
        await update.message.reply_text("Faqat guruh admini /admin dan foydalana oladi.")
        return
    await update.message.reply_text(
        "Feature boshqaruvi (ON/OFF):",
        reply_markup=_build_admin_keyboard(update.effective_chat.id),
    )


async def transcribe_audio(audio_bytes: bytes) -> str:
    if not OPENAI_API_KEY:
        return ""
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    files = {"file": ("voice.ogg", audio_bytes, "audio/ogg")}
    data = {"model": "whisper-1", "response_format": "text"}
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers=headers,
                files=files,
                data=data,
            )
            response.raise_for_status()
            return response.text.strip()
    except Exception as exc:
        logger.error("Voice transcription error: %s", exc)
        return ""


async def voice_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.voice:
        return
    user_id = _ensure_user(update)
    if not OPENAI_API_KEY:
        await message.reply_text("OPENAI_API_KEY topilmadi. Ovozli tahlil uchun .env ga qo'shing.")
        return

    await message.reply_text("Ovoz matnga aylantirilmoqda...")
    voice_file = await context.bot.get_file(message.voice.file_id)
    voice_data = await voice_file.download_as_bytearray()
    transcript = await transcribe_audio(bytes(voice_data))
    if not transcript:
        await message.reply_text("Ovozni tahlil qilib bo'lmadi. Qayta urinib ko'ring.")
        return

    await message.reply_text(f"Transkript:\n{transcript}")
    response = await ask_ai(
        transcript,
        mode="check",
        context=get_recent_context(user_id, 6),
        max_tokens=900,
    )
    await message.reply_text(response)
    increment_stat(user_id, "checks")
    _store_interaction(user_id, "voice_check", transcript, response)


async def web_app_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.web_app_data:
        return
    user_id = _ensure_user(update)
    payload_raw = message.web_app_data.data

    try:
        payload = json.loads(payload_raw)
    except json.JSONDecodeError:
        await message.reply_text("WebApp data JSON formatda emas.")
        return

    save_webapp_snapshot(user_id, payload)
    payload_type = payload.get("type", "unknown")

    if payload_type == "focus_session":
        minutes = int(payload.get("minutes", 0) or 0)
        if minutes > 0:
            add_focus_session(user_id, minutes, source="webapp")
            await message.reply_text(f"WebApp fokus sessiya saqlandi: {minutes} daqiqa.")
        return

    if payload_type == "task_add":
        title = str(payload.get("title", "")).strip()
        web_id = str(payload.get("task_id", "")).strip() or None
        if title:
            task_id = add_task(user_id, title, source="webapp", web_id=web_id)
            await message.reply_text(f"WebApp task qo'shildi: #{task_id}")
        return

    if payload_type == "task_toggle":
        web_id = str(payload.get("task_id", "")).strip()
        title = str(payload.get("title", "")).strip() or "Web task"
        done = bool(payload.get("done", False))
        if web_id:
            set_task_state_by_web_id(user_id, web_id, title, done)
            await message.reply_text("WebApp task holati yangilandi.")
        return

    if payload_type == "sync_state":
        tasks = payload.get("tasks", [])
        applied = 0
        if isinstance(tasks, list):
            for item in tasks:
                if not isinstance(item, dict):
                    continue
                task_id = str(item.get("id", "")).strip()
                title = str(item.get("title", "")).strip()
                if not task_id or not title:
                    continue
                set_task_state_by_web_id(user_id, task_id, title, bool(item.get("done", False)))
                applied += 1
        await message.reply_text(f"WebApp state qabul qilindi. Tasklar: {applied}")
        return

    await message.reply_text("WebApp data qabul qilindi.")


async def group_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.text:
        return

    text = message.text.strip()
    text_lower = text.lower()
    user_id = _ensure_user(update)
    chat_id = message.chat.id

    if "#check" in text_lower:
        if not is_feature_enabled(chat_id, "check"):
            return
        content = re.sub(r"#check", "", text, flags=re.IGNORECASE).strip()
        if not content:
            await message.reply_text("Namuna: I goes to school #check")
            return
        await message.reply_text("Tekshirilmoqda...")
        ai = await ask_ai(content, mode="check", context=get_recent_context(user_id, 6))
        await message.reply_text(ai)
        increment_stat(user_id, "checks")
        _store_interaction(user_id, "check", content, ai)
        return

    if "#bot" in text_lower:
        if not is_feature_enabled(chat_id, "bot"):
            return
        content = re.sub(r"#bot", "", text, flags=re.IGNORECASE).strip()
        if not content:
            await message.reply_text("Namuna: #bot Present Perfect haqida tushuntir")
            return
        await message.reply_text("AI javob tayyorlamoqda...")
        ai = await ask_ai(content, mode="general", context=get_recent_context(user_id, 6))
        await message.reply_text(ai)
        increment_stat(user_id, "questions")
        _store_interaction(user_id, "general", content, ai)
        return

    if re.search(r"\B#t\b", text, re.IGNORECASE):
        if not is_feature_enabled(chat_id, "translate"):
            return
        content = re.sub(r"\B#t\b", "", text, flags=re.IGNORECASE).strip()
        if not content:
            await message.reply_text("Namuna: #t although")
            return
        await message.reply_text("Tarjima qilinmoqda...")
        ai = await ask_ai(content, mode="translate", context=get_recent_context(user_id, 6))
        await message.reply_text(ai)
        increment_stat(user_id, "translations")
        _store_interaction(user_id, "translate", content, ai)


async def private_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.text:
        return

    text = message.text.strip()
    if text.startswith("/"):
        return

    user_id = _ensure_user(update)
    history = get_recent_context(user_id, 8)

    if text.lower().startswith("uz:"):
        payload = text[3:].strip()
        if not payload:
            await message.reply_text("Namuna: uz: men bugun dars qilaman")
            return
        await message.reply_text("Tarjima qilinmoqda...")
        ai = await ask_ai(payload, mode="uz_to_en", context=history, max_tokens=700)
        await message.reply_text(ai)
        increment_stat(user_id, "translations")
        _store_interaction(user_id, "uz_to_en", payload, ai)
        return

    await message.reply_text("Tahlil qilinmoqda...")
    ai = await ask_ai(text, mode="auto", context=history)
    await message.reply_text(ai)
    increment_stat(user_id, "questions")
    _store_interaction(user_id, "auto", text, ai)


async def inline_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    inline_query = update.inline_query
    if not inline_query:
        return
    query = inline_query.query.strip()

    if not query:
        await inline_query.answer(
            [
                InlineQueryResultArticle(
                    id=str(uuid4()),
                    title="Artificial Teacher yordam",
                    description="Masalan: check I goes to school yoki t although",
                    input_message_content=InputTextMessageContent(
                        "Inline mode ishlatish:\n"
                        "check <matn> - grammatik tekshiruv\n"
                        "t <so'z/yoki ibora> - tarjima\n"
                        "savol yozing - AI javob"
                    ),
                )
            ],
            is_personal=True,
            cache_time=0,
        )
        return

    mode = "general"
    payload = query
    lower = query.lower()
    if lower.startswith("check "):
        mode = "check"
        payload = query[6:].strip()
    elif lower.startswith("t "):
        mode = "translate"
        payload = query[2:].strip()
    elif lower.startswith("uz "):
        mode = "uz_to_en"
        payload = query[3:].strip()

    if not payload:
        payload = query
    ai = await ask_ai(payload, mode=mode, max_tokens=350, temperature=0.2)
    description = ai.replace("\n", " ")
    if len(description) > 180:
        description = description[:177] + "..."

    result = InlineQueryResultArticle(
        id=str(uuid4()),
        title="Artificial Teacher javobi",
        description=description,
        input_message_content=InputTextMessageContent(ai),
    )
    await inline_query.answer([result], is_personal=True, cache_time=0)


async def daily_word_job(context: ContextTypes.DEFAULT_TYPE):
    word = pick_daily_word()
    text = (
        "Daily Word\n\n"
        f"{word['word']} - {word['definition']}\n"
        f"Example: {word['example']}\n\n"
        "Bugun shu so'z bilan 2 ta gap tuzib ko'ring."
    )
    for chat_id in list_daily_subscriptions():
        try:
            await context.bot.send_message(chat_id=chat_id, text=text)
        except Exception as exc:
            logger.warning("Daily word sending failed to %s: %s", chat_id, exc)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    await query.answer()
    data = query.data or ""
    user_id = query.from_user.id
    ensure_user(user_id, query.from_user.username, query.from_user.first_name)

    if data.startswith("info:"):
        key = data.split(":", 1)[1]
        info_texts = {
            "check": "Matn tekshiruv: guruhda #check yoki private chatga oddiy matn yuboring.",
            "ask": "AI savol-javob: guruhda #bot yoki private chatda savol yozing.",
            "quiz": "Quiz boshlash uchun /quiz buyrug'ini yuboring.",
            "daily": "Kunlik so'z yoqish: /daily_on, o'chirish: /daily_off",
            "webapp": "WEB_APP_URL hali .env da sozlanmagan.",
        }
        await query.message.reply_text(info_texts.get(key, "Ma'lumot topilmadi."))
        return

    if data.startswith("rule:"):
        topic = data.split(":", 1)[1]
        prompts = {
            "tenses": "Ingliz tilidagi asosiy zamonlarni oddiy jadval va misollar bilan tushuntir.",
            "articles": "a/an/the article qoidalarini misollar bilan tushuntir.",
            "prepositions": "in/on/at/for/to/with prepositionlarini oson usulda tushuntir.",
            "conditionals": "0, 1, 2, 3 conditionals farqi va misollar.",
            "passive": "Passive Voice qachon ishlatiladi, Active vs Passive misollari bilan.",
        }
        prompt = prompts.get(topic, topic)
        await query.message.reply_text("Qoida tayyorlanmoqda...")
        answer = await ask_ai(prompt, mode="rule", context=get_recent_context(user_id, 4))
        await query.message.reply_text(answer)
        increment_stat(user_id, "questions")
        _store_interaction(user_id, "rule", prompt, answer)
        return

    if data.startswith("qz:"):
        state = context.user_data.get("quiz")
        if not state:
            await query.message.reply_text("Quiz sessiyasi tugagan. /quiz bilan qayta boshlang.")
            return

        parts = data.split(":")
        if len(parts) != 3:
            return
        try:
            incoming_index = int(parts[1])
            picked = int(parts[2])
        except ValueError:
            return

        current_index = state["index"]
        if incoming_index != current_index:
            await query.answer("Bu savol eskirgan.", show_alert=False)
            return

        question = state["questions"][current_index]
        correct_option = int(question["answer"])
        is_correct = picked == correct_option
        if is_correct:
            state["correct"] += 1

        verdict = "To'g'ri!" if is_correct else "Noto'g'ri."
        explain = question["explanation"]
        correct_text = question["options"][correct_option]
        await query.edit_message_text(
            f"{verdict}\nTo'g'ri javob: {correct_text}\nIzoh: {explain}"
        )

        state["index"] += 1
        if state["index"] >= len(state["questions"]):
            await _finish_quiz(update, context, user_id)
        else:
            await _send_quiz_question(query.message, context)
        return

    if data.startswith("adm:"):
        if query.message.chat.type == "private":
            await query.message.reply_text("Admin panel faqat guruhda ishlaydi.")
            return
        member = await context.bot.get_chat_member(query.message.chat.id, query.from_user.id)
        if member.status not in {"administrator", "creator"}:
            await query.message.reply_text("Faqat admin sozlamani o'zgartira oladi.")
            return

        feature = data.split(":", 1)[1]
        states = list_feature_states(query.message.chat.id)
        current = states.get(feature, True)
        set_chat_feature(query.message.chat.id, feature, not current)
        await query.edit_message_reply_markup(reply_markup=_build_admin_keyboard(query.message.chat.id))
        await query.message.reply_text(f"{FEATURE_LABELS.get(feature, feature)}: {'ON' if not current else 'OFF'}")


async def bot_added_to_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return
    for member in message.new_chat_members:
        if member.id == context.bot.id:
            await message.reply_text(
                "Salom! Artificial Teacher bot guruhga qo'shildi.\n"
                "Ishlatish:\n"
                "#check - grammatik tekshiruv\n"
                "#bot - AI savol\n"
                "#t - tarjima\n"
                "/admin - feature ON/OFF"
            )


def main():
    if not BOT_TOKEN or "YOUR_BOT_TOKEN_HERE" in BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN .env da sozlanmagan.")

    init_db()
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("rules", rules_command))
    application.add_handler(CommandHandler("about", about_command))
    application.add_handler(CommandHandler("contact", contact_command))
    application.add_handler(CommandHandler("quiz", quiz_command))
    application.add_handler(CommandHandler("lesson", lesson_command))
    application.add_handler(CommandHandler("mystats", mystats_command))
    application.add_handler(CommandHandler("mylevel", mylevel_command))
    application.add_handler(CommandHandler("setlevel", setlevel_command))
    application.add_handler(CommandHandler("uz2en", uz2en_command))
    application.add_handler(CommandHandler("pronounce", pronounce_command))
    application.add_handler(CommandHandler("tracker", tracker_command))
    application.add_handler(CommandHandler("focus", focus_command))
    application.add_handler(CommandHandler("task", task_command))
    application.add_handler(CommandHandler("daily_on", daily_on_command))
    application.add_handler(CommandHandler("daily_off", daily_off_command))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("webapp", webapp_command))

    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(InlineQueryHandler(inline_query_handler))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, bot_added_to_group))
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data_handler))
    application.add_handler(MessageHandler(filters.VOICE, voice_message_handler))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS, group_message_handler)
    )
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, private_message_handler)
    )

    if application.job_queue:
        tz = ZoneInfo(BOT_TIMEZONE)
        application.job_queue.run_daily(
            daily_word_job,
            time=dt_time(hour=DAILY_WORD_HOUR, minute=DAILY_WORD_MINUTE, tzinfo=tz),
            name="daily_word",
        )

    webhook_url = os.getenv("WEBHOOK_URL", "").strip()
    logger.info("Bot ishga tushmoqda...")

    if webhook_url:
        path = os.getenv("WEBHOOK_PATH", "telegram-webhook").lstrip("/")
        port = int(os.getenv("PORT", "8080"))
        application.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=path,
            webhook_url=f"{webhook_url.rstrip('/')}/{path}",
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
        )
    else:
        application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
