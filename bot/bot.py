"""
bot.py - English Teacher Bot - To'liq versiya
Python 3.14 | asyncio.run() | Inline tugmalar bevosita ishlaydi
"""
import logging, os, asyncio, re, html, traceback, json, time, uuid, atexit
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode
from dotenv import load_dotenv
try:
    import msvcrt  # Windows
except ImportError:
    msvcrt = None

try:
    import fcntl  # Unix/Linux
except ImportError:
    fcntl = None
load_dotenv()

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand,
    InlineQueryResultArticle, InputTextMessageContent, ReplyKeyboardMarkup, ReplyKeyboardRemove,
    KeyboardButton, WebAppInfo, BotCommandScopeChat
)
from telegram.error import BadRequest
from telegram.request import HTTPXRequest
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    InlineQueryHandler, ChosenInlineResultHandler, ContextTypes, filters
)

from handlers.quiz import (
    quiz_command,
    iq_command,
    quiz_callback,
    quiz_next_callback,
    quiz_picker_callback,
    quiz_time_callback,
    quiz_language_callback,
    quiz_result_callback,
    start_quiz_from_callback,
)
from handlers.subscription import (
    subscription_command, subscription_command_from_callback,
    sub_callback, receipt_handler, my_payments_command
)
from handlers.admin import (
    admin_command, admin_callback, admin_text_handler, admin_media_handler,
    group_admin_command, group_admin_callback, is_owner, OWNER_ID
)
from utils.ai import ask_ai, ask_json
from utils.tts import synthesize_pronunciation, make_audio_file
from html_maker import render_html_document, html_open_guide
from database.db import (
    init_db, upsert_user, get_user, set_level,
    inc_stat, inc_usage, check_limit,
    get_stats, get_user_plan, clear_history,
    get_group, get_daily_groups, get_sponsor_channels,
    record_level_signal, auto_adjust_level_from_signals,
    get_admin_ids, get_points, get_cash_balance, get_reward_wallet, apply_referral_code, redeem_promo_code,
    add_webapp_progress, set_webapp_progress_snapshot, get_user_rank_snapshot, get_leaderboard, get_webapp_totals,
    record_service_hit, get_service_hit_summary,
)

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN    = os.getenv("BOT_TOKEN", "")
WEBHOOK_URL  = os.getenv("WEBHOOK_URL", "")
WEBHOOK_PORT = int(os.getenv("PORT", os.getenv("WEBHOOK_PORT", "8443")))
USE_WEBHOOK  = bool(WEBHOOK_URL)
BOT_NAME = "Artificial Teacher"
BOT_USERNAME = (os.getenv("BOT_USERNAME", "@Artificial_teacher_bot") or "@Artificial_teacher_bot").strip()
BOT_BIO = "🦉 AI ingliz tili o'qituvchisi: grammatika, tarjima, quiz, darslar. O'zbekcha. 24/7 📚✨"
DEVELOPER    = "@murodullayev_web"
SUPPORT_URL = os.getenv("SUPPORT_URL", "")
WEBSITE_URL = os.getenv("WEBSITE_URL", "")
TELEGRAM_CHANNEL_URL = os.getenv("TELEGRAM_CHANNEL_URL", "")
INSTAGRAM_URL = os.getenv("INSTAGRAM_URL", "")
WEB_APP_URL = os.getenv("WEB_APP_URL", "").strip()
INLINE_HTML_CHANNEL = os.getenv("INLINE_HTML_CHANNEL", "").strip().strip('"').strip("'")
INLINE_AUDIO_CHANNEL = os.getenv("INLINE_AUDIO_CHANNEL", "").strip().strip('"').strip("'")
UPDATE_CONCURRENCY = int(os.getenv("UPDATE_CONCURRENCY", "64"))
TG_CONNECTION_POOL = int(os.getenv("TG_CONNECTION_POOL", "128"))
TG_POOL_TIMEOUT = float(os.getenv("TG_POOL_TIMEOUT", "20"))
SPONSOR_CACHE_SEC = int(os.getenv("SPONSOR_CACHE_SEC", "300"))
HTML_SEND_CONCURRENCY = int(os.getenv("HTML_SEND_CONCURRENCY", "8"))
HTML_SEND_WAIT_SEC = float(os.getenv("HTML_SEND_WAIT_SEC", "10"))
_HTML_SEND_SEMAPHORE = asyncio.Semaphore(max(1, HTML_SEND_CONCURRENCY))
INLINE_CACHE_LIMIT = 256
_SPONSOR_ACCESS_CACHE = {}
_INSTANCE_LOCK_HANDLE = None
_INSTANCE_LOCK_PATH = Path(
    os.getenv("INSTANCE_LOCK_FILE", str(Path(__file__).with_name("bot.instance.lock")))
)

PLAN_ICONS = {"free": "\U0001F193", "standard": "\u2B50", "pro": "\U0001F48E", "premium": "\U0001F451"}
LEVELS = ["A1","A2","B1","B2","C1","C2"]
LEVEL_GUESS_RE = re.compile(r"daraja\s+taxmini\s*:\s*(A1|A2|B1|B2|C1|C2)", re.IGNORECASE)
LESSON_TOPICS = {
    "A1": ["greetings", "family", "food", "colors", "numbers", "daily routine", "school", "home", "weather", "shopping"],
    "A2": ["travel", "health", "jobs", "hobbies", "technology", "city life", "transport", "friends", "weekend plans", "restaurants"],
    "B1": ["work", "education", "communication", "environment", "sports", "culture", "money", "media", "problem solving", "habits"],
    "B2": ["leadership", "productivity", "career growth", "innovation", "relationships", "public speaking", "global issues", "business meetings", "negotiation", "research"],
    "C1": ["critical thinking", "psychology", "strategy", "branding", "economics", "ethics", "policy", "analysis", "academic writing", "debate"],
    "C2": ["philosophy", "geopolitics", "advanced rhetoric", "linguistics", "entrepreneurship", "systems thinking", "market dynamics", "creative direction", "social theory", "innovation labs"],
}


def acquire_instance_lock() -> bool:
    """Prevent multiple polling processes of the same bot on one host."""
    global _INSTANCE_LOCK_HANDLE
    try:
        _INSTANCE_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
        lock_file = open(_INSTANCE_LOCK_PATH, "a+", encoding="utf-8")
    except OSError as e:
        logger.warning("Instance lock faylini ochib bo'lmadi: %s", e)
        return True

    try:
        lock_file.seek(0)
        if msvcrt:
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
        elif fcntl:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        else:
            logger.warning("File lock backend topilmadi. Lock checksiz davom etyapti.")
    except OSError:
        try:
            lock_file.close()
        except Exception:
            pass
        logger.error("Boshqa bot instance ishlayapti. Iltimos, dublikat processni to'xtating.")
        return False

    lock_file.seek(0)
    lock_file.truncate(0)
    lock_file.write(str(os.getpid()))
    lock_file.flush()
    _INSTANCE_LOCK_HANDLE = lock_file
    return True


def release_instance_lock() -> None:
    global _INSTANCE_LOCK_HANDLE
    if not _INSTANCE_LOCK_HANDLE:
        return
    try:
        if msvcrt:
            _INSTANCE_LOCK_HANDLE.seek(0)
            msvcrt.locking(_INSTANCE_LOCK_HANDLE.fileno(), msvcrt.LK_UNLCK, 1)
        elif fcntl:
            fcntl.flock(_INSTANCE_LOCK_HANDLE.fileno(), fcntl.LOCK_UN)
    except OSError:
        pass
    finally:
        try:
            _INSTANCE_LOCK_HANDLE.close()
        except Exception:
            pass
        _INSTANCE_LOCK_HANDLE = None


atexit.register(release_instance_lock)

async def start_health_server() -> Optional[asyncio.AbstractServer]:
    """Render free web service uchun oddiy site + health endpoint."""
    port_raw = os.getenv("PORT", "").strip()
    if not port_raw:
        return None
    try:
        port = int(port_raw)
    except ValueError:
        logger.warning("PORT noto'g'ri: %s", port_raw)
        return None

    def _resp(status: str, body: bytes, content_type: str = "text/plain; charset=utf-8") -> bytes:
        header = (
            f"HTTP/1.1 {status}\\r\\n"
            f"Content-Type: {content_type}\\r\\n"
            f"Content-Length: {len(body)}\\r\\n"
            "Connection: close\\r\\n\\r\\n"
        ).encode("utf-8")
        return header + body

    def _site_html() -> bytes:
        s = get_service_hit_summary(limit=5)
        return render_awake_site(s)

    async def _handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        path = "/"
        ip = ""
        ua = ""
        try:
            req = (await reader.read(4096)).decode("utf-8", errors="ignore")
            first = req.splitlines()[0] if req else ""
            parts = first.split()
            if len(parts) >= 2:
                path = parts[1].split("?", 1)[0]
            for h in req.splitlines()[1:40]:
                if h.lower().startswith("user-agent:"):
                    ua = h.split(":", 1)[1].strip()
                    break
            peer = writer.get_extra_info("peername")
            if isinstance(peer, tuple) and peer:
                ip = str(peer[0])
            record_service_hit(path=path, ip=ip, user_agent=ua)
            if path in ("/", "/index.html", "/status"):
                writer.write(_resp("200 OK", _site_html(), "text/html; charset=utf-8"))
            elif path in ("/health", "/ping"):
                writer.write(_resp("200 OK", b"ok"))
            else:
                writer.write(_resp("404 Not Found", b"not found"))
            await writer.drain()
        except Exception:
            pass
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    try:
        server = await asyncio.start_server(_handle, host="0.0.0.0", port=port)
        logger.info("Health/site server ishlamoqda: 0.0.0.0:%s", port)
        return server
    except Exception as e:
        logger.warning("Health/site serverni ishga tushirib bo'lmadi: %s", e)
        return None


def render_awake_site(stats: dict) -> bytes:
    template_path = Path(__file__).with_name("site") / "index.html"
    try:
        html_text = template_path.read_text(encoding="utf-8")
    except Exception:
        html_text = "<!doctype html><html><body>Service running</body></html>"
    payload = json.dumps({
        "total": stats.get("total", 0),
        "last_at": stats.get("last_at") or "-",
        "last_1h": stats.get("last_1h", 0),
        "last_24h": stats.get("last_24h", 0),
    })
    html_text = html_text.replace("{{total}}", str(stats.get("total", 0)))
    html_text = html_text.replace("{{last_at}}", str(stats.get("last_at") or "-"))
    html_text = html_text.replace("{{last_1h}}", str(stats.get("last_1h", 0)))
    html_text = html_text.replace("{{last_24h}}", str(stats.get("last_24h", 0)))
    html_text = html_text.replace("{{stats_json}}", payload)
    return html_text.encode("utf-8")
def plan_display_name(plan: dict, with_icon: bool = False) -> str:
    plan_name = str(plan.get("plan_name", "free")).lower()
    fallback = {
        "free": "Free",
        "standard": "Standard",
        "pro": "Pro",
        "premium": "Premium",
    }.get(plan_name, "Free")

    raw = str(plan.get("display_name", fallback) or fallback)
    cleaned = raw
    for token in ("\U0001F193", "\u2B50", "\U0001F48E", "\U0001F451", "[FREE]", "[STD]", "[PRO]", "[PREM]"):
        cleaned = cleaned.replace(token, " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -")

    words = cleaned.split()
    if len(words) >= 2 and words[0].lower() == words[1].lower():
        cleaned = " ".join(words[1:])
    if cleaned.lower() in ("free", "standard", "pro", "premium"):
        cleaned = cleaned.title()
    if not cleaned:
        cleaned = fallback

    if with_icon:
        return f"{PLAN_ICONS.get(plan_name, '')} {cleaned}".strip()
    return cleaned


def normalize_quick_menu_text(text: str) -> str:
    source = (text or "").strip().lower()
    for token in ("’", "`", "ʻ", "ʼ", "´"):
        source = source.replace(token, "'")
    source = source.replace("—", "-").replace("–", "-")
    cleaned = re.sub(r"^[^a-z0-9']+\s*", "", source)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    aliases = {
        "tekshirish": "tekshiruv",
        "tekshiruv": "tekshiruv",
        "progress": "progress",
        "statistika": "progress",
        "darajam": "progress",
        "reyting": "progress",
        "darajam / reyting": "progress",
        "darajam/reyting": "progress",
        "bonus": "bonuslar",
        "bonuslar": "bonuslar",
        "promo": "bonuslar",
        "tolovlar": "to'lovlar",
        "to'lovlar": "to'lovlar",
        "payments": "to'lovlar",
        "obuna": "tariflar",
        "tariflar": "tariflar",
        "grammatika": "grammatika",
        "grammar": "grammatika",
        "kunlik so'z": "kunlik so'z",
        "kunlik soz": "kunlik so'z",
        "daily word": "kunlik so'z",
        "dailyword": "kunlik so'z",
        "bosh sahifa": "menyu",
        "home": "menyu",
        "iq testi": "iq test",
    }
    return aliases.get(cleaned, cleaned)


def extract_level_guess(text: str) -> str | None:
    if not text:
        return None
    match = LEVEL_GUESS_RE.search(text)
    if not match:
        return None
    level = match.group(1).upper()
    return level if level in LEVELS else None


def extract_mention_payload(text: str) -> str | None:
    if not text:
        return None
    stripped = text.strip()
    uname = BOT_USERNAME.lower()
    low = stripped.lower()

    if low == uname:
        return ""
    if low.startswith(uname + " "):
        return stripped[len(BOT_USERNAME):].strip()

    pattern = re.escape(BOT_USERNAME) + r"[,:]?\s*(.*)"
    m = re.search(pattern, stripped, flags=re.IGNORECASE)
    if not m:
        return None
    return (m.group(1) or "").strip()


def detect_translation_mode(text: str) -> str:
    content = (text or "").strip().lower()
    if not content:
        return "uz_to_en"
    uz_signals = [" men ", " sen ", " siz ", " biz ", " yoki ", " uchun ", " bilan ", " kerak ", " emas ", " qachon ", " qayer ", " nima ", " bugun ", " ertaga ", " o'", " g'", " sh ", " ch "]
    en_signals = [" the ", " and ", " is ", " are ", " was ", " were ", " have ", " has ", " i ", " you ", " we ", " they ", " this ", " that ", " from ", " with ", " open ", " send "]
    padded = f" {content} "
    uz_score = sum(1 for token in uz_signals if token in padded)
    en_score = sum(1 for token in en_signals if token in padded)
    if re.search(r"\b(the|is|are|was|were|have|has|open|from|send|saved messages)\b", content):
        en_score += 2
    return "en_to_uz" if en_score > uz_score else "uz_to_en"


def parse_request_mode(content: str) -> tuple[str, str]:
    raw = (content or "").strip()
    low = raw.lower()
    if low.startswith("tr uz:") or low.startswith("tr uz ") or low.startswith("tr uzbek:"):
        return "uz_to_en", raw.split(":", 1)[1].strip() if ":" in raw else raw[6:].strip()
    if low.startswith("tr en:") or low.startswith("tr en ") or low.startswith("tr eng:") or low.startswith("tr english:"):
        return "en_to_uz", raw.split(":", 1)[1].strip() if ":" in raw else raw[6:].strip()
    if low.startswith("tr:"):
        payload = raw[3:].strip()
        return detect_translation_mode(payload), payload
    if low.startswith("p:"):
        return "pronunciation", raw[2:].strip()
    for prefix in ("p us:", "p uk:", "p british:", "p american:", "p us ", "p uk "):
        if low.startswith(prefix):
            return "pronunciation", raw[2:].strip()
    if low.startswith("check:"):
        return "check", raw[6:].strip()
    if low.startswith("ai:"):
        return "general", raw[3:].strip()
    return "check", raw


def parse_pronunciation_target(content: str, default_accent: str = "us") -> tuple[str, str]:
    raw = (content or "").strip()
    low = raw.lower()
    prefixes = (
        ("uk:", "uk"),
        ("us:", "us"),
        ("british:", "uk"),
        ("american:", "us"),
        ("uk ", "uk"),
        ("us ", "us"),
    )
    for prefix, accent in prefixes:
        if low.startswith(prefix):
            return accent, raw[len(prefix):].strip()
    return default_accent, raw


def format_points(value) -> str:
    try:
        amount = float(value or 0)
    except Exception:
        amount = 0.0
    if abs(amount - round(amount)) < 0.00001:
        return str(int(round(amount)))
    return f"{amount:.2f}".rstrip("0").rstrip(".")


def parse_translation_response(response: str) -> dict:
    payload = {
        "translated_text": (response or "").strip(),
        "alternatives": [],
        "notes": [],
        "raw_text": (response or "").strip(),
    }
    if not response:
        return payload
    trans_match = re.search(r"Tarjima:\s*(.*?)(?:Muqobil variantlar:|Qisqa izoh:|$)", response, re.S | re.I)
    alt_match = re.search(r"Muqobil variantlar:\s*(.*?)(?:Qisqa izoh:|$)", response, re.S | re.I)
    note_match = re.search(r"Qisqa izoh:\s*(.*)$", response, re.S | re.I)
    if trans_match:
        payload["translated_text"] = trans_match.group(1).strip()
    if alt_match:
        payload["alternatives"] = [line.strip(" -\n\r\t") for line in alt_match.group(1).splitlines() if line.strip()]
    if note_match:
        payload["notes"] = [line.strip(" -\n\r\t") for line in note_match.group(1).splitlines() if line.strip()]
    if not payload["notes"] and payload["alternatives"]:
        payload["notes"] = payload["alternatives"]
    if not payload["notes"]:
        payload["notes"] = [payload["translated_text"]]
    return payload


def build_translation_direction_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🇺🇿 UZ → EN", callback_data="trdir__uz_to_en"),
            InlineKeyboardButton("🇬🇧 EN → UZ", callback_data="trdir__en_to_uz"),
        ],
        [InlineKeyboardButton("🏠 Menyu", callback_data="menu_back")],
    ])


def build_rules_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📖 Tenses", callback_data="rule__tenses"), InlineKeyboardButton("📖 Articles", callback_data="rule__articles")],
        [InlineKeyboardButton("📖 Prepositions", callback_data="rule__prepositions"), InlineKeyboardButton("❓ Questions", callback_data="rule__questions")],
        [InlineKeyboardButton("📖 Conditionals", callback_data="rule__conditionals"), InlineKeyboardButton("📖 Passive Voice", callback_data="rule__passive")],
        [InlineKeyboardButton("✍️ O'z mavzum", callback_data="rule__custom")],
        [InlineKeyboardButton("🏠 Menyu", callback_data="menu_back")],
    ])


def build_translation_html_doc(source_text: str, response: str, direction: str, user_name: str, user_id: int):
    parsed = parse_translation_response(response)
    direction_label = "O'zbekcha ? Inglizcha" if direction == "uz_to_en" else "English ? O'zbekcha"
    return render_html_document(
        "translation_report.html",
        {
            "title": "Translation Report",
            "subtitle": direction_label,
            "user_name": user_name or "User",
            "source_text": source_text,
            "translated_text": parsed["translated_text"],
            "notes": parsed["notes"],
            "direction_label": direction_label,
            "raw_text": response,
            "theme_seed": f"{direction}:{source_text[:80]}",
        },
        f"translation_{direction}_{user_id}.html",
    )



def build_study_note_doc(title: str, subtitle: str, raw_text: str, user_name: str, user_id: int, section: str = "Guide", file_prefix: str = "study_note"):
    clean_text = (raw_text or "").strip()
    lines = [re.sub(r"^[\-?\d.)\s]+", "", line.strip()) for line in clean_text.splitlines() if line.strip()]
    summary = lines[0] if lines else clean_text[:180]
    key_points = lines[:10] if lines else [clean_text[:200]]
    return render_html_document(
        "study_note.html",
        {
            "title": title,
            "subtitle": subtitle,
            "section": section,
            "user_name": user_name or "User",
            "summary": summary,
            "key_points": key_points,
            "raw_text": clean_text or "Ma'lumot topilmadi.",
            "theme_seed": f"{file_prefix}:{title}:{subtitle}:{user_id}",
        },
        f"{file_prefix}_{user_id}.html",
    )


def build_referral_link(user_id: int) -> str:
    wallet = get_reward_wallet(user_id)
    code = str(wallet.get("referral_code", f"AT{user_id}"))
    return f"https://t.me/{BOT_USERNAME.lstrip('@')}?start={code}"


def build_web_app_url(user_id: Optional[int] = None) -> str | None:
    if not WEB_APP_URL:
        return None
    if user_id is None:
        return WEB_APP_URL
    try:
        plan = get_user_plan(user_id)
        rank = get_user_rank_snapshot(user_id) or {}
        plan_name = plan.get("plan_name", "free")
        level = (get_user(user_id) or {}).get("level", "A1")
        score = int(rank.get("learning_score", 0) or 0)
        user_rank = int(rank.get("rank", 0) or 0)
    except Exception:
        plan_name = "free"
        level = "A1"
        score = 0
        user_rank = 0
    params = urlencode({"uid": user_id, "plan": plan_name, "level": level, "score": score, "rank": user_rank})
    sep = "&" if "?" in WEB_APP_URL else "?"
    return f"{WEB_APP_URL}{sep}{params}"

def build_web_app_markup(user_id: int, include_back: bool = True):
    url = build_web_app_url(user_id)
    if not url:
        return None
    rows = [[InlineKeyboardButton("\U0001F4F1 Web App ochish", web_app=WebAppInfo(url=url))]]
    if include_back:
        rows.append([InlineKeyboardButton("\U0001F519 Menyu", callback_data="menu_back")])
    return InlineKeyboardMarkup(rows)


def quick_menu_kb(role: str = "user", user_id: Optional[int] = None):
    rows = [
        ["\u2705 Tekshiruv", "\U0001F501 Tarjima", "\U0001F50A Talaffuz"],
        ["\U0001F3AF Quiz", "\U0001F9E0 IQ test", "\U0001F4DA Dars"],
        ["\U0001F4D6 Grammatika", "\U0001F4C5 Kunlik so'z", "\U0001F4C8 Darajam / Reyting"],
        ["\U0001F381 Bonuslar", "\U0001F4B3 Tariflar", "\u2139\ufe0f Aloqa"],
    ]
    web_url = build_web_app_url(user_id)
    if web_url:
        rows.append([KeyboardButton("\U0001F4F1 Web App", web_app=WebAppInfo(url=web_url))])
    else:
        rows.append(["\U0001F4F1 Web App"])
    if role in ("admin", "owner"):
        rows.append(["\U0001F6E1 Admin panel"])
    return ReplyKeyboardMarkup(
        rows,
        resize_keyboard=True,
        input_field_placeholder="Kerakli bo'limni tanlang yoki savolingizni yozing...",
    )


def build_main_menu_hint() -> str:
    return (
        "\U0001F3E0 *Asosiy boshqaruv klaviaturada tayyor.*\n\n"
        "Kerakli bo'limni pastdagi keyboarddan tanlang."
    )


def escape_md(text: str) -> str:
    if text is None:
        return ""
    # Basic Markdown v1 escaping for dynamic content
    return re.sub(r"([_*\[\]()~`>#+=|{}.!-])", r"\\\1", str(text))


async def safe_reply(message, text, reply_markup=None, parse_mode=None):
    if message is None:
        return
    try:
        return await message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except BadRequest:
        if parse_mode:
            try:
                return await message.reply_text(text, reply_markup=reply_markup)
            except Exception:
                pass
    except Exception:
        pass
    return None


async def safe_edit(query, text, reply_markup=None, parse_mode=None):
    if query is None:
        return
    try:
        if query.message and query.message.text is not None:
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
            return
        if query.message and query.message.caption is not None:
            await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
            return
    except BadRequest:
        if parse_mode:
            try:
                if query.message and query.message.text is not None:
                    await query.edit_message_text(text, reply_markup=reply_markup)
                    return
                if query.message and query.message.caption is not None:
                    await query.edit_message_caption(caption=text, reply_markup=reply_markup)
                    return
            except BadRequest:
                pass
    try:
        if query.message:
            await safe_reply(query.message, text, reply_markup=reply_markup, parse_mode=parse_mode)
            return
    except Exception:
        pass
    try:
        await query.bot.send_message(chat_id=query.message.chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception:
        pass


async def safe_delete(message):
    if message is None:
        return
    try:
        await message.delete()
    except Exception:
        pass


def build_sponsor_keyboard(channels):
    rows = []
    for row in channels[:8]:
        label = row.get("title") or row.get("chat_ref") or "Kanal"
        url = row.get("join_url") or ""
        if url:
            rows.append([InlineKeyboardButton(f"\U0001F4E2 {label}", url=url)])
    rows.append([InlineKeyboardButton("Tekshirdim", callback_data="sponsor_recheck")])
    return InlineKeyboardMarkup(rows)


async def ensure_sponsor_access(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    if not user:
        return True
    db_user = get_user(user.id)
    if db_user and db_user.get("role") in ("admin", "owner"):
        return True

    channels = get_sponsor_channels(active_only=True)
    if not channels:
        return True

    now_ts = time.time()
    if len(_SPONSOR_ACCESS_CACHE) > 50000:
        stale = [key for key, value in _SPONSOR_ACCESS_CACHE.items() if value.get("expires", 0) <= now_ts]
        for key in stale[:10000]:
            _SPONSOR_ACCESS_CACHE.pop(key, None)

    missing = []
    for row in channels:
        cache_key = (str(row["chat_ref"]), int(user.id))
        cached = _SPONSOR_ACCESS_CACHE.get(cache_key)
        if cached and cached.get("expires", 0) > now_ts:
            if not cached.get("ok", False):
                missing.append(row)
            continue
        try:
            member = await context.bot.get_chat_member(row["chat_ref"], user.id)
            is_joined = member.status in ("member", "administrator", "creator")
        except Exception:
            is_joined = False
        _SPONSOR_ACCESS_CACHE[cache_key] = {"ok": is_joined, "expires": now_ts + SPONSOR_CACHE_SEC}
        if not is_joined:
            missing.append(row)

    if not missing:
        return True

    missing_lines = "\n".join([f"- {row.get('title') or row.get('chat_ref')}" for row in missing])
    text = (
        "*Siz quyidagi kanallarga obuna bo'lmagansiz:*\n\n"
        f"{missing_lines}\n\n"
        "*Botdan foydalanish uchun shu kanallarga qo'shiling.*\n\n"
        "Obuna bo'lgach, `Tekshirdim` tugmasini bosing."
    )
    if update.callback_query:
        await safe_edit(update.callback_query, text, reply_markup=build_sponsor_keyboard(missing), parse_mode="Markdown")
    elif update.effective_message:
        await safe_reply(update.effective_message, text, reply_markup=build_sponsor_keyboard(missing), parse_mode="Markdown")
    return False


def build_daily_word_text(data: dict) -> str:
    word = escape_md(data.get("word", ""))
    pos = escape_md(data.get("pos", ""))
    translation = escape_md(data.get("translation", ""))
    example = escape_md(data.get("example", ""))
    example_uz = escape_md(data.get("example_uz", ""))
    tip = escape_md(data.get("tip", ""))

    pos_txt = f" - _{pos}_" if pos else ""
    text = (
        "\U0001F338 *Kunlik so'z*\n\n"
        f"\U0001F497 *{word}*{pos_txt}\n"
        f"\U0001F1FA\U0001F1FF {translation}\n\n"
        f"\U0001F4D6 _{example}_\n"
        f"\U0001F1FA\U0001F1FF {example_uz}\n\n"
        f"\U0001F4A1 {tip}"
    )
    return text


def parse_check_response(response: str) -> dict:
    data = {
        "analysis_items": [],
        "corrected_text": response.strip(),
        "level_guess": "-",
        "rule_text": "",
    }
    if not response:
        return data

    analysis_match = re.search(r"Tahlil:\s*(.*?)(?:To'g'ri variant:|$)", response, re.S | re.I)
    correct_match = re.search(r"To'g'ri variant:\s*(.*?)(?:Daraja taxmini:|Asosiy qoida:|$)", response, re.S | re.I)
    level_match = re.search(r"Daraja taxmini:\s*(A1|A2|B1|B2|C1|C2)", response, re.I)
    rule_match = re.search(r"Asosiy qoida:\s*(.*)$", response, re.S | re.I)

    analysis_text = (analysis_match.group(1).strip() if analysis_match else "").strip()
    if analysis_text:
        items = [line.strip(" -\n\r\t") for line in analysis_text.splitlines() if line.strip()]
        data["analysis_items"] = items or [analysis_text]
    corrected = (correct_match.group(1).strip() if correct_match else "").strip()
    if corrected:
        data["corrected_text"] = corrected
    if level_match:
        data["level_guess"] = level_match.group(1).upper()
    if rule_match:
        data["rule_text"] = rule_match.group(1).strip()
    return data


async def send_html_export(chat_id: int, context: ContextTypes.DEFAULT_TYPE, document, filename: str, caption: Optional[str] = None):
    try:
        document.name = filename
        await asyncio.wait_for(_HTML_SEND_SEMAPHORE.acquire(), timeout=HTML_SEND_WAIT_SEC)
        try:
            await context.bot.send_document(chat_id=chat_id, document=document, filename=filename, caption=caption or html_open_guide())
        finally:
            _HTML_SEND_SEMAPHORE.release()
        return True
    except TimeoutError:
        try:
            await context.bot.send_message(chat_id, "HTML navbati band. Asosiy natija yuborildi, HTML keyinroq qayta urinib ko'ring.")
        except Exception:
            pass
        return False
    except Exception:
        try:
            await context.bot.send_message(chat_id, "HTML faylni yuborishda muammo chiqdi, lekin asosiy natija tayyor.")
        except Exception:
            pass
        return False

def remember_inline_result(context: ContextTypes.DEFAULT_TYPE, result_id: str, mode: str, content: str, answer: str, export_mode: str = "private"):
    cache = context.application.bot_data.setdefault("inline_result_cache", {})
    cache[result_id] = {
        "mode": mode,
        "content": content,
        "answer": answer,
        "export_mode": export_mode,
        "ts": time.time(),
    }
    if len(cache) > INLINE_CACHE_LIMIT:
        stale_keys = sorted(cache, key=lambda key: cache[key].get("ts", 0))[:-INLINE_CACHE_LIMIT]
        for key in stale_keys:
            cache.pop(key, None)


def pop_inline_result(context: ContextTypes.DEFAULT_TYPE, result_id: str) -> dict:
    cache = context.application.bot_data.setdefault("inline_result_cache", {})
    data = cache.pop(result_id, {})
    return data if isinstance(data, dict) else {}


def build_export_id(prefix: str) -> str:
    return f"AT{prefix}-{uuid.uuid4().hex[:6].upper()}"


def build_channel_post_link(channel_ref: str, message_id: int) -> str | None:
    ref = (channel_ref or "").strip()
    if not ref:
        return None
    if ref.startswith("https://t.me/"):
        slug = ref.rstrip("/").split("/")[-1]
        return f"https://t.me/{slug}/{message_id}" if slug else None
    if ref.startswith("@"):
        return f"https://t.me/{ref[1:]}/{message_id}"
    if re.fullmatch(r"[A-Za-z0-9_]{5,32}", ref):
        return f"https://t.me/{ref}/{message_id}"
    return None


def build_inline_delivery_note(label: str, export_mode: str) -> str:
    if export_mode == "channel":
        return f"{label} arxiv kanalga yuboriladi."
    return f"{label} bot private chatiga yuboriladi."

def build_inline_pending_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("Qo'shimcha fayl tayyorlanmoqda", url=f"https://t.me/{BOT_USERNAME.lstrip('@')}")]]
    )


def build_inline_export_markup(links: list[tuple[str, str | None]] | None = None) -> InlineKeyboardMarkup | None:
    rows = []
    for title, link in links or []:
        if link:
            rows.append([InlineKeyboardButton(title, url=link)])
    return InlineKeyboardMarkup(rows) if rows else None

async def update_inline_text_result(context: ContextTypes.DEFAULT_TYPE, chosen, user_id: int, text: str):
    inline_message_id = getattr(chosen, "inline_message_id", None)
    if inline_message_id:
        try:
            await context.bot.edit_message_text(
                inline_message_id=inline_message_id,
                text=(text or "").strip()[:4096],
            )
            return True
        except Exception as e:
            logger.warning("Inline natijani yangilab bo'lmadi: %s", e)
    try:
        await context.bot.send_message(user_id, (text or "").strip()[:4096])
        return True
    except Exception as e:
        logger.warning("Inline natijani DM yuborib bo'lmadi: %s", e)
    return False


async def attach_inline_export_info(
    context: ContextTypes.DEFAULT_TYPE,
    chosen,
    user_id: int,
    answer: str,
    export_id: str,
    label: str,
    links: list[tuple[str, str | None]] | None = None,
):
    extra_lines = [f"{label} ID: {export_id}"]
    if links:
        for title, link in links:
            if link:
                extra_lines.append(f"{title}: {link}")
    if len(extra_lines) == 1:
        extra_lines.append("Qo'shimcha fayl kanalga yuklandi.")
    extra = "\n\n" + "\n".join(extra_lines)
    inline_message_id = getattr(chosen, "inline_message_id", None)
    if inline_message_id:
        try:
            await context.bot.edit_message_text(
                inline_message_id=inline_message_id,
                text=(answer.strip() + extra)[:4096],
                reply_markup=build_inline_export_markup(links),
            )
            return
        except Exception as e:
            logger.warning("Inline xabarni yangilab bo'lmadi: %s", e)
    try:
        await context.bot.send_message(user_id, extra.strip())
    except Exception as e:
        logger.warning("Inline export DM yuborilmadi: %s", e)


def get_lesson_topics_for_level(level: str) -> list[str]:
    if level in LESSON_TOPICS:
        return LESSON_TOPICS[level]
    return LESSON_TOPICS["A1"]


def render_lesson_html(topic: str, level: str, pack: dict) -> str:
    words_html = "".join(
        f"<li><strong>{html.escape(item.get('word', ''))}</strong> - {html.escape(item.get('meaning', ''))}<br><em>{html.escape(item.get('example', ''))}</em></li>"
        for item in pack.get("words", [])
    )
    phrases_html = "".join(f"<li>{html.escape(item)}</li>" for item in pack.get("phrases", []))
    exercises_html = "".join(f"<li>{html.escape(item)}</li>" for item in pack.get("exercises", []))
    tips_html = "".join(f"<li>{html.escape(item)}</li>" for item in pack.get("tips", []))
    title = html.escape(pack.get("title", topic.title()))
    intro = html.escape(pack.get("intro", ""))
    dialogue = html.escape(pack.get("dialogue", ""))
    return f"""<!DOCTYPE html>
<html lang="uz">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>
    :root {{
      --bg: #f6efe4;
      --paper: #fffaf2;
      --ink: #1f2a37;
      --accent: #bf6c2c;
      --muted: #6b7280;
      --line: #ead8bf;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      background:
        radial-gradient(circle at top right, rgba(191,108,44,0.16), transparent 30%),
        linear-gradient(180deg, #f7f1e8 0%, #efe4d1 100%);
      color: var(--ink);
      padding: 28px;
    }}
    .sheet {{
      max-width: 980px;
      margin: 0 auto;
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 24px;
      padding: 28px;
      box-shadow: 0 18px 45px rgba(68, 41, 18, 0.12);
    }}
    .hero {{
      border-bottom: 1px solid var(--line);
      padding-bottom: 18px;
      margin-bottom: 22px;
    }}
    .eyebrow {{
      text-transform: uppercase;
      letter-spacing: 0.14em;
      color: var(--accent);
      font-size: 12px;
    }}
    h1, h2 {{ margin: 0 0 12px; }}
    h1 {{ font-size: 38px; }}
    h2 {{ font-size: 24px; margin-top: 26px; }}
    p, li {{ line-height: 1.7; }}
    .meta {{
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      color: var(--muted);
      font-size: 14px;
    }}
    .card {{
      background: #fff;
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 18px;
      margin-top: 16px;
    }}
    ul {{ padding-left: 22px; }}
    @media (max-width: 720px) {{
      body {{ padding: 14px; }}
      .sheet {{ padding: 18px; border-radius: 16px; }}
      h1 {{ font-size: 30px; }}
    }}
  </style>
</head>
<body>
  <main class="sheet">
    <section class="hero">
      <div class="eyebrow">English Teacher Bot lesson</div>
      <h1>{title}</h1>
      <div class="meta">
        <span>Mavzu: {html.escape(topic.title())}</span>
        <span>Daraja: {html.escape(level)}</span>
      </div>
      <p>{intro}</p>
    </section>

    <section class="card">
      <h2>So'zlar</h2>
      <ul>{words_html}</ul>
    </section>

    <section class="card">
      <h2>Foydali iboralar</h2>
      <ul>{phrases_html}</ul>
    </section>

    <section class="card">
      <h2>Mini dialogue</h2>
      <p>{dialogue}</p>
    </section>

    <section class="card">
      <h2>Mashqlar</h2>
      <ul>{exercises_html}</ul>
    </section>

    <section class="card">
      <h2>Maslahatlar</h2>
      <ul>{tips_html}</ul>
    </section>
  </main>
</body>
</html>"""


async def build_lesson_outputs(user_id: int, topic: str, level: str):
    pack = await ask_json(topic, mode="lesson_pack", level=level)
    if not isinstance(pack, dict):
        return None, None, None

    words = pack.get("words", [])[:8]
    preview_lines = [
        f"\U0001F4D8 *{escape_md(pack.get('title', topic.title()))}*",
        f"Daraja: *{escape_md(level)}*",
        "",
        escape_md(pack.get("intro", "")),
        "",
        "*Asosiy so'zlar:*",
    ]
    for item in words:
        word = escape_md(item.get("word", ""))
        meaning = escape_md(item.get("meaning", ""))
        preview_lines.append(f"- {word}: {meaning}")
    preview_lines.append("")
    preview_lines.append("To'liq dars HTML fayl sifatida ham yuborildi.")

    file_name = f"lesson_{user_id}_{re.sub(r'[^a-z0-9]+', '_', topic.lower())}.html"
    document = render_html_document(
        "lesson_pack.html",
        {
            "title": pack.get("title", topic.title()),
            "topic": topic.title(),
            "level": level,
            "intro": pack.get("intro", ""),
            "words": pack.get("words", []),
            "phrases": pack.get("phrases", []),
            "dialogue": pack.get("dialogue", ""),
            "exercises": pack.get("exercises", []),
            "tips": pack.get("tips", []),
        },
        file_name,
    )
    return "\n".join(preview_lines), document, pack


async def limit_check(update, user_id, field) -> bool:
    allowed, used, limit = check_limit(user_id, field)
    if not allowed:
        plan = get_user_plan(user_id)
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("\U0001F4B3 Obuna olish", callback_data="menu_subscribe")
        ]])
        target_message = update.effective_message
        if not target_message:
            return False
        await target_message.reply_text(
            f"\u26A0\ufe0f *Kunlik limit tugadi!*\n\n"
            f"Sizning rejangiz: {plan_display_name(plan, with_icon=True)}\n"
            f"Limit: {limit}/kun\n\n"
            "Limitni oshirish uchun obuna oling \U0001F4AA",
            reply_markup=kb, parse_mode="Markdown"
        )
        return False
    return True


def build_user_stats_text(user_id: int, first_name: str) -> str | None:
    s = get_stats(user_id)
    db_user = get_user(user_id)
    plan = get_user_plan(user_id)
    wallet = get_reward_wallet(user_id)
    rank = get_user_rank_snapshot(user_id) or {}
    web = get_webapp_totals(user_id, days=30)
    if not s:
        return None
    quiz_acc = round(s["quiz_correct"] / s["quiz_played"] * 100) if s["quiz_played"] else 0
    expires = plan.get("expires_at", "")
    exp_txt = f"\nMuddati: {expires[:10]}" if expires else ""
    first_safe = escape_md(first_name)
    rank_text = f"#{rank.get('rank', '-')} / {rank.get('total_users', '-')}" if rank else "Hisoblanmoqda"
    score = int(rank.get("learning_score", 0) or 0)
    level = db_user.get('level', 'A1') if db_user else 'A1'
    points_text = format_points(wallet.get("points", 0))
    cash_text = format_points(get_cash_balance(user_id))
    ref_code = wallet.get("referral_code", f"AT{user_id}")
    return (
        f"\U0001F4C8 *Progress va reyting*\n\n"
        f"Foydalanuvchi: *{first_safe}*\n"
        f"Obuna: {plan_display_name(plan, with_icon=True)}{exp_txt}\n"
        f"Daraja: *{escape_md(level)}*\n"
        f"Reyting: *{escape_md(rank_text)}*\n"
        f"O'quv balli: *{score}*\n"
        f"Referral ballar: *{points_text}*\n"
        f"Referral cashback: *{cash_text} UZS*\n"
        f"Referral kod: `{ref_code}`\n"
        f"Streak: *{s.get('streak_days', 0)} kun*\n\n"
        f"*Bot statistikasi:*\n"
        f"- Tekshiruvlar: {s['checks_total']}\n"
        f"- Quiz: {s['quiz_correct']} to'g'ri / {s['quiz_played']} savol ({quiz_acc}%)\n"
        f"- IQ ko'rsatkichi: {s.get('iq_score', 0)}\n"
        f"- AI xabarlar: {s['messages_total']}\n\n"
        f"*Web App / tracker (30 kun):*\n"
        f"- Focus: {web.get('focus_minutes', 0)} min\n"
        f"- So'zlar: {web.get('words_learned', 0)}\n"
        f"- Quiz session: {web.get('quiz_completed', 0)}\n"
        f"- Darslar: {web.get('lessons_completed', 0)}\n"
        f"- Tracker ballari: {web.get('points_earned', 0)}"
    )


def build_leaderboard_text(limit: int = 5) -> str:
    rows = get_leaderboard(limit)
    if not rows:
        return "\U0001F3C6 Reyting hozircha bo'sh."
    lines = ["\U0001F3C6 *Top foydalanuvchilar*"]
    medals = {1: "\U0001F947", 2: "\U0001F948", 3: "\U0001F949"}
    for row in rows:
        rank = int(row.get("rank", 0) or 0)
        prefix = medals.get(rank, f"{rank}.")
        name = escape_md(row.get("first_name") or row.get("username") or f"User {row.get('user_id')}")
        level = escape_md(str(row.get("level", "A1")))
        score = int(row.get("learning_score", 0) or 0)
        lines.append(f"{prefix} *{name}* | {level} | {score} ball")
    return "\n".join(lines)


def build_progress_panel_text(user_id: int, first_name: str, leaderboard_limit: int = 5) -> str | None:
    stats_text = build_user_stats_text(user_id, first_name)
    if not stats_text:
        return None
    leaderboard = build_leaderboard_text(limit=leaderboard_limit)
    return f"{stats_text}\n\n{leaderboard}"


def build_progress_action_markup(user_id: int):
    rows = [
        [
            InlineKeyboardButton("\U0001F4C4 HTML hisobot", callback_data="menu_progress_html"),
            InlineKeyboardButton("\U0001F3C6 Top reyting", callback_data="menu_leaderboard"),
        ],
        [
            InlineKeyboardButton("\U0001F381 Bonuslar", callback_data="menu_bonus_center"),
            InlineKeyboardButton("\U0001F4B3 To'lovlar", callback_data="menu_mypayments"),
        ],
        [InlineKeyboardButton("\U0001F4E6 Tariflar", callback_data="menu_subscribe")],
    ]
    web_url = build_web_app_url(user_id)
    if web_url:
        rows.append([InlineKeyboardButton("\U0001F4F1 Web App", web_app=WebAppInfo(url=web_url))])
    rows.append([InlineKeyboardButton("\U0001F3E0 Menyu", callback_data="menu_back")])
    return InlineKeyboardMarkup(rows)


def build_bonus_center_text(user_id: int, first_name: str) -> str:
    wallet = get_reward_wallet(user_id)
    plan = get_user_plan(user_id)
    rank = get_user_rank_snapshot(user_id) or {}
    rank_text = f"#{rank.get('rank', '-')} / {rank.get('total_users', '-')}" if rank else "Hisoblanmoqda"
    referral_link = build_referral_link(user_id)
    return (
        "\U0001F381 *Bonus va to'lov markazi*\n\n"
        f"Foydalanuvchi: *{escape_md(first_name)}*\n"
        f"Reja: {plan_display_name(plan, with_icon=True)}\n"
        f"Referral ballar: *{format_points(wallet.get('points', 0))}*\n"
        f"Referral cashback: *{format_points(get_cash_balance(user_id))} UZS*\n"
        f"Referral kod: `{wallet.get('referral_code', f'AT{user_id}')}`\n"
        f"Referral havola: `{referral_link}`\n"
        f"Platform reytingi: *{escape_md(rank_text)}*\n\n"
        "Bu bo'limda promo kod, referral, to'lovlar tarixi, tariflar va progress jamlangan."
    )



def build_referral_panel_text(user_id: int, first_name: str) -> str:
    wallet = get_reward_wallet(user_id)
    referral_link = build_referral_link(user_id)
    total_refs = int(wallet.get("total_referrals", 0) or 0)
    points = format_points(wallet.get("points", 0))
    cash = format_points(get_cash_balance(user_id))
    code = wallet.get("referral_code", f"AT{user_id}")
    return (
        "\U0001F517 *Referral bo'limi*\n\n"
        f"Foydalanuvchi: *{escape_md(first_name)}*\n"
        f"Olib kirgan odamlar: *{total_refs}*\n"
        f"Yig'ilgan ballar: *{points}*\n"
        f"Referral cashback: *{cash} UZS*\n"
        f"Referral kod: `{code}`\n"
        f"Referral havola: `{referral_link}`\n\n"
        "*Nima qilish mumkin:*\n"
        "- Havolani do'stlarga yuborib user olib kirish\n"
        "- Referral ballar yig'ish\n"
        "- Ballarni bonus/promo packlarda ishlatish\n"
        "- To'lovlardan cashback olish"
    )


def build_referral_panel_markup(user_id: int):
    referral_link = build_referral_link(user_id)
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("\U0001F4E4 Havolani ochish", url=referral_link)],
        [
            InlineKeyboardButton("\U0001F381 Bonus markazi", callback_data="menu_bonus_center"),
            InlineKeyboardButton("\U0001F519 Orqaga", callback_data="menu_bonus_center"),
        ],
    ])

def build_bonus_center_markup(user_id: int):
    rows = [
        [
            InlineKeyboardButton("\U0001F3AB Promo kod", callback_data="menu_enter_promo"),
            InlineKeyboardButton("\U0001F4B3 To'lovlar", callback_data="menu_mypayments"),
        ],
        [
            InlineKeyboardButton("\U0001F4E6 Tariflar", callback_data="menu_subscribe"),
            InlineKeyboardButton("\U0001F4C8 Darajam / Reyting", callback_data="menu_progress_panel"),
        ],
        [
            InlineKeyboardButton("\U0001F517 Referral bo'limi", callback_data="menu_referral_panel"),
        ],
    ]
    web_url = build_web_app_url(user_id)
    if web_url:
        rows.append([InlineKeyboardButton("\U0001F4F1 Web App", web_app=WebAppInfo(url=web_url))])
    rows.append([InlineKeyboardButton("\U0001F3E0 Menyu", callback_data="menu_back")])
    return InlineKeyboardMarkup(rows)


def build_progress_report_doc(user_id: int, first_name: str):
    stats = get_stats(user_id)
    if not stats:
        return None
    db_user = get_user(user_id) or {}
    plan = get_user_plan(user_id)
    wallet = get_reward_wallet(user_id)
    rank = get_user_rank_snapshot(user_id) or {}
    web = get_webapp_totals(user_id, days=30)
    quiz_played = int(stats.get("quiz_played", 0) or 0)
    quiz_correct = int(stats.get("quiz_correct", 0) or 0)
    quiz_accuracy = round((quiz_correct / max(quiz_played, 1)) * 100) if quiz_played else 0
    leaders = []
    for row in get_leaderboard(10):
        leaders.append({
            "rank": int(row.get("rank", 0) or 0),
            "name": row.get("first_name") or row.get("username") or f"User {row.get('user_id')}",
            "level": row.get("level", "A1"),
            "score": int(row.get("learning_score", 0) or 0),
        })
    return render_html_document(
        "progress_report.html",
        {
            "title": "Progress Report",
            "user_name": first_name or "Foydalanuvchi",
            "plan_name": plan_display_name(plan, with_icon=False),
            "level": db_user.get("level", "A1"),
            "rank": rank.get("rank", "-"),
            "total_users": rank.get("total_users", "-"),
            "score": int(rank.get("learning_score", 0) or 0),
            "streak_days": int(stats.get("streak_days", 0) or 0),
            "checks_total": int(stats.get("checks_total", 0) or 0),
            "quiz_played": quiz_played,
            "quiz_correct": quiz_correct,
            "quiz_accuracy": quiz_accuracy,
            "iq_score": int(stats.get("iq_score", 0) or 0),
            "messages_total": int(stats.get("messages_total", 0) or 0),
            "referral_points": float(wallet.get("points", 0) or 0),
            "referral_code": wallet.get("referral_code", f"AT{user_id}"),
            "referral_link": build_referral_link(user_id),
            "cash_balance": float(get_cash_balance(user_id) or 0),
            "focus_minutes": int(web.get("focus_minutes", 0) or 0),
            "words_learned": int(web.get("words_learned", 0) or 0),
            "quiz_completed": int(web.get("quiz_completed", 0) or 0),
            "lessons_completed": int(web.get("lessons_completed", 0) or 0),
            "tracker_points": int(web.get("points_earned", 0) or 0),
            "leaders": leaders,
            "theme_seed": f"progress:{user_id}:{rank.get('learning_score', 0)}",
        },
        f"progress_report_{user_id}.html",
    )


def reset_user_session_state(context: ContextTypes.DEFAULT_TYPE, keep_pron_accent: bool = True):
    """Clear temporary interaction states so users don't get stuck in old mode."""
    accent = context.user_data.get("pron_accent", "us") if keep_pron_accent else None
    for key in (
        "mode",
        "awaiting_receipt",
        "awaiting_promo_code",
        "awaiting_level_test",
        "awaiting_custom_rule",
    ):
        context.user_data.pop(key, None)
    if accent in ("us", "uk"):
        context.user_data["pron_accent"] = accent

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    reset_user_session_state(context, keep_pron_accent=True)
    existing_user = get_user(user.id)
    upsert_user(user.id, user.username, user.first_name)
    db_user = get_user(user.id)
    if not existing_user and getattr(context, "args", None):
        result = apply_referral_code(user.id, context.args[0])
        if result.get("applied"):
            try:
                await context.bot.send_message(
                    result["referrer_id"],
                    f"\U0001F381 Referral bonusi berildi: +{result['bonus']} ball",
                )
            except Exception:
                pass
    if not await ensure_sponsor_access(update, context):
        return
    plan = get_user_plan(user.id)
    name = user.first_name or "Do'st"
    name_safe = escape_md(name)

    text = (
        f"Salom, *{name_safe}*!\n\n"
        f"*{BOT_NAME}* - ingliz tilini o'zbekcha o'rgatadigan AI yordamchi.\n\n"
        f"Sizning rejangiz: *{plan_display_name(plan, with_icon=True)}*\n\n"
        "Asosiy bo'limlar pastdagi klaviaturada."
    )
    cleanup_msg = await safe_reply(update.message, "\u2063", reply_markup=ReplyKeyboardRemove())
    await safe_delete(cleanup_msg)
    await safe_reply(update.message, text, reply_markup=quick_menu_kb((db_user or {}).get("role", "user"), user_id=user.id), parse_mode="Markdown")


def build_topic_keyboard(topics):
    buttons = [InlineKeyboardButton(t.capitalize(), callback_data=f"lesson__{t}") for t in topics]
    rows = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
    rows.append([InlineKeyboardButton("\U0001F519 Menyu", callback_data="menu_back")])
    return InlineKeyboardMarkup(rows)

def build_pronunciation_keyboard(accent: str = "us"):
    accent = "uk" if accent == "uk" else "us"
    us_label = "\U0001F1FA\U0001F1F8 US" + (" \u2705" if accent == "us" else "")
    uk_label = "\U0001F1EC\U0001F1E7 UK" + (" \u2705" if accent == "uk" else "")
    rows = [
        [
            InlineKeyboardButton(us_label, callback_data="pronaccent__us"),
            InlineKeyboardButton(uk_label, callback_data="pronaccent__uk"),
        ],
        [InlineKeyboardButton("\U0001F519 Menyu", callback_data="menu_back")],
    ]
    return InlineKeyboardMarkup(rows)

def build_pronunciation_caption(term: str, analysis: str, accent: str) -> str:
    accent_label = "UK" if accent == "uk" else "US"
    compact = re.sub(r"[*_`#>]+", "", analysis or "")
    compact = re.sub(r"\n{3,}", "\n\n", compact).strip()
    caption = f"Talaffuz audio\nSo'z: {term}\nAksent: {accent_label}"
    if compact:
        room = 1024 - len(caption) - 4
        if room > 0:
            compact = compact[:room].rstrip()
            caption += f"\n\n{compact}"
    return caption[:1024]


def build_pronunciation_html_doc(term: str, accent: str, analysis: str, user_name: str, user_id: int):
    accent_label = "UK" if accent == "uk" else "US"
    sections = [line.strip(" -	") for line in (analysis or "").splitlines() if line.strip()]
    if not sections:
        sections = [analysis or "Tahlil mavjud emas."]
    return render_html_document(
        "pronunciation_guide.html",
        {
            "title": "Pronunciation Guide",
            "user_name": user_name or "User",
            "term": term,
            "accent": accent_label,
            "analysis_items": sections,
            "full_text": analysis or "Tahlil mavjud emas.",
        },
        f"pronunciation_guide_{user_id}.html",
    )


async def send_pronunciation_audio(
    chat_id: int,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    accent: str,
    caption: Optional[str] = None,
):
    result = await synthesize_pronunciation(text, accent=accent)
    if not result.get("ok"):
        err = result.get("error", "unknown")
        msg = {
            "missing_api_key": "Talaffuz audio API kaliti topilmadi. `TOPMEDIAI_API_KEY` ni sozlang.",
            "empty_text": "Matn bo'sh.",
            "busy": "Talaffuz serveri band. 10-20 soniyadan keyin qayta urinib ko'ring.",
            "speaker_not_found": "US/UK ovoz topilmadi. Speaker IDlarni sozlash kerak.",
            "http_401": "Talaffuz API kaliti xato (401).",
            "http_429": "Talaffuz limiti oshdi (429). Biroz kuting.",
            "no_audio_url": "Audio havolasi topilmadi. Keyinroq qayta urinib ko'ring.",
            "request": "Talaffuz xizmati bilan aloqa xatosi.",
            "unknown": "Talaffuz audio yaratishda texnik xatolik.",
        }.get(err, "Talaffuz audio yaratib bo'lmadi.")
        return False, msg
    ext = "mp3"
    accent_label = "UK" if accent == "uk" else "US"
    audio_file = make_audio_file(result["audio"], f"pronunciation_{accent_label.lower()}.{ext}")
    await context.bot.send_audio(
        chat_id=chat_id,
        audio=audio_file,
        filename=audio_file.name,
        caption=(caption or f"Talaffuz audio tayyor ({accent_label}).")[:1024],
    )
    return True, ""

def build_about_text() -> str:
    return (
        f"\u2139\ufe0f *{BOT_NAME}*\n\n"
        f"{BOT_BIO}\n\n"
        f"Bot useri: {BOT_USERNAME}\n\n"
        "*Asosiy yo'nalishlar:*\n"
        "- grammatik tekshiruv\n"
        "- tarjima va talaffuz\n"
        "- darajaga mos quiz va darslar\n"
        "- statistika va rivojlanish kuzatuvi\n\n"
        "*Aloqa va loyiha:*\n"
        f"- Dasturchi: {DEVELOPER}\n"
        "- Hamkorlik, reklama va fikr-mulohaza uchun pastdagi tugmalardan foydalaning.\n\n"
        "*Inline rejim:*\n"
        f"{BOT_USERNAME} your text - tekshiruv\n"
        f"{BOT_USERNAME} tr: matn - tarjima\n"
        f"{BOT_USERNAME} p: us: word - talaffuz\n"
        f"{BOT_USERNAME} p: uk: word - britancha talaffuz"
    )


def build_about_buttons():
    buttons = [
        [InlineKeyboardButton("\U0001F4B3 Obuna", callback_data="menu_subscribe")],
        [InlineKeyboardButton("\U0001F519 Menyu", callback_data="menu_back")],
    ]
    if SUPPORT_URL:
        buttons.append([InlineKeyboardButton("\U0001F4AC Aloqa", url=SUPPORT_URL)])
    if TELEGRAM_CHANNEL_URL:
        buttons.append([InlineKeyboardButton("\U0001F4E2 Telegram kanal", url=TELEGRAM_CHANNEL_URL)])
    if INSTAGRAM_URL:
        buttons.append([InlineKeyboardButton("\U0001F4F8 Instagram", url=INSTAGRAM_URL)])
    if WEBSITE_URL:
        buttons.append([InlineKeyboardButton("\U0001F310 Sayt", url=WEBSITE_URL)])
    if WEB_APP_URL:
        buttons.append([InlineKeyboardButton("\U0001F4F1 Web App", web_app=WebAppInfo(url=WEB_APP_URL))])
    buttons.append([InlineKeyboardButton("\U0001F4DE Dasturchi", url="https://t.me/murodullayev_web")])
    return InlineKeyboardMarkup(buttons)


def build_webapp_intro_text(user_id: int) -> str:
    plan = get_user_plan(user_id)
    plan_name = str(plan.get("plan_name", "free")).lower()
    feature_block = (
        "- Pomodoro fokus taymeri\n"
        "- Rivojlanish tracker (quiz, dars, so'z)\n"
        "- Haftalik progress ko'rinishi"
    )
    if plan_name == "free":
        premium_block = (
            "*Free:* bazaviy tracker + oddiy pomodoro\n"
            "*Pro/Premium:* kengaytirilgan analytics, export va chuqur statistika"
        )
    else:
        premium_block = (
            f"*Sizning rejangiz:* {plan_display_name(plan, with_icon=True)}\n"
            "Kengaytirilgan tracker va premium bloklar ochiq."
        )
    return (
        "\U0001F4F1 *Telegram Web App*\n\n"
        "Botga ulangan mini-ilova tayyor. Bu yerda quyidagilar bo'ladi:\n"
        f"{feature_block}\n\n"
        f"{premium_block}"
    )


async def app_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_sponsor_access(update, context):
        return
    user_id = update.effective_user.id
    markup = build_web_app_markup(user_id, include_back=False)
    if not markup:
        await safe_reply(
            update.effective_message,
            "Web App URL hozircha sozlanmagan. `.env` ichida `WEB_APP_URL` ni kiriting.",
            parse_mode="Markdown",
        )
        return
    await safe_reply(
        update.effective_message,
        build_webapp_intro_text(user_id),
        reply_markup=markup,
        parse_mode="Markdown",
    )


async def main_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    upsert_user(user.id, user.username, user.first_name)
    data = query.data

    if data == "sponsor_recheck":
        if await ensure_sponsor_access(update, context):
            await safe_edit(query, build_main_menu_hint(), parse_mode="Markdown")
        return

    if not await ensure_sponsor_access(update, context):
        return

    if data == "do_check":
        context.user_data["mode"] = "check"
        await safe_edit(
            query,
            "\u2705 *Matn tekshirish rejimi*\n\n"
            "Inglizcha matnni yozing - men grammatik xatolarni topib tuzataman.\n\n"
            "_Misol: I went to school yesterday_",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001F3E0 Menyu", callback_data="menu_back")]]),
            parse_mode="Markdown",
        )
        return

    if data == "do_translate":
        await safe_edit(
            query,
            "🔁 *Tarjima bo'limi*\n\nQaysi yo'nalishda ishlamoqchisiz?",
            reply_markup=build_translation_direction_markup(),
            parse_mode="Markdown",
        )
        return

    if data.startswith("trdir__"):
        direction = data.split("__", 1)[1]
        context.user_data["mode"] = direction
        if direction == "en_to_uz":
            text_out = (
                "🔁 *English -> O'zbekcha tarjima*\n\n"
                "Endi inglizcha matn yuboring, men uni tabiiy o'zbekchaga o'giraman.\n\n"
                "_Misol: I have already finished my work_"
            )
        else:
            text_out = (
                "🔁 *O'zbekcha -> Inglizcha tarjima*\n\n"
                "Endi o'zbekcha matn yuboring, men uni tabiiy inglizchaga o'giraman.\n\n"
                "_Misol: Men har kuni maktabga boraman_"
            )
        await safe_edit(query, text_out, reply_markup=build_translation_direction_markup(), parse_mode="Markdown")
        return


    if data == "do_quiz":
        await start_quiz_from_callback(query, context, qtype="quiz")
        return

    if data == "do_iq":
        await start_quiz_from_callback(query, context, qtype="iq")
        return

    if data == "do_daily":
        await safe_edit(query, "\U0001F4C5 Kunlik so'z tayyorlanmoqda...")
        data_json = await ask_json("So'z", mode="daily_word")
        if data_json:
            daily_text = build_daily_word_text(data_json)
            kb = [[
                InlineKeyboardButton("\U0001F50A Talaffuz", callback_data=f"pron__{data_json.get('word', '')}"),
                InlineKeyboardButton("\U0001F3E0 Menyu", callback_data="menu_back"),
            ]]
            await safe_edit(query, daily_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return

    if data == "do_lesson":
        allowed, used, limit = check_limit(user.id, "lessons")
        if not allowed:
            kb = [[InlineKeyboardButton("\U0001F4B3 Obuna", callback_data="menu_subscribe")]]
            await safe_edit(query, f"\u26A0\ufe0f Kunlik dars limiti tugadi ({limit}/kun).", reply_markup=InlineKeyboardMarkup(kb))
            return
        db_user = get_user(user.id)
        level = (db_user or {}).get("level", "A1")
        topics = get_lesson_topics_for_level(level)
        await safe_edit(
            query,
            f"\U0001F4DA *Mavzu tanlang*\n\nDaraja: *{escape_md(level)}*",
            reply_markup=build_topic_keyboard(topics),
            parse_mode="Markdown",
        )
        return

    if data.startswith("lesson__"):
        topic = data.split("__", 1)[1]
        topic_safe = escape_md(topic.capitalize())
        await safe_edit(query, f"\U0001F4DA *{topic_safe}* mavzusida dars tayyorlanmoqda...", parse_mode="Markdown")
        db_user = get_user(user.id)
        level = (db_user or {}).get("level", "A1")
        response, html_doc, _ = await build_lesson_outputs(user.id, topic, level)
        inc_usage(user.id, "lessons")
        kb = [[InlineKeyboardButton("\U0001F3E0 Menyu", callback_data="menu_back")]]
        if response:
            await safe_edit(query, response, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
            if html_doc:
                await send_html_export(query.message.chat_id, context, html_doc, getattr(html_doc, "name", "lesson.html"))
        else:
            fallback = await ask_ai(topic, mode="lesson", user_id=user.id)
            await safe_edit(query, fallback, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return

    if data == "do_pron":
        context.user_data["mode"] = "pronunciation"
        accent = context.user_data.get("pron_accent", "us")
        accent_label = "UK" if accent == "uk" else "US"
        await safe_edit(
            query,
            "\U0001F50A *Talaffuz rejimi*\n\n"
            f"Hozirgi sheva: *{accent_label}*\n"
            "So'z yoki gap yuboring, audio talaffuz qaytaraman.",
            reply_markup=build_pronunciation_keyboard(accent),
            parse_mode="Markdown",
        )
        return

    if data.startswith("pronaccent__"):
        accent = "uk" if data.endswith("__uk") else "us"
        context.user_data["pron_accent"] = accent
        context.user_data["mode"] = "pronunciation"
        accent_label = "UK" if accent == "uk" else "US"
        await safe_edit(
            query,
            "\U0001F50A *Talaffuz rejimi*\n\n"
            f"Sheva yangilandi: *{accent_label}*\n"
            "So'z yoki gap yuboring, audio talaffuz qaytaraman.",
            reply_markup=build_pronunciation_keyboard(accent),
            parse_mode="Markdown",
        )
        return

    if data.startswith("pron__"):
        word = data.split("__", 1)[1]
        word_safe = escape_md(word)
        if not await limit_check(update, user.id, "pron_audio"):
            return
        accent = context.user_data.get("pron_accent", "us")
        accent_label = "UK" if accent == "uk" else "US"
        await safe_edit(query, f"\U0001F50A *{word_safe}* talaffuzi ({accent_label}) tayyorlanmoqda...", parse_mode="Markdown")
        analysis = await ask_ai(word, mode="pronunciation", user_id=user.id)
        caption = build_pronunciation_caption(word, analysis, accent)
        ok, err = await send_pronunciation_audio(query.message.chat_id, context, word, accent, caption=caption)
        if ok:
            inc_usage(user.id, "pron_audio")
            inc_stat(user.id, "messages_total")
            await safe_edit(query, analysis, reply_markup=build_pronunciation_keyboard(accent), parse_mode="Markdown")
            doc = build_pronunciation_html_doc(word, accent, analysis, user.first_name or "User", user.id)
            await send_html_export(query.message.chat_id, context, doc, doc.name, caption="Talaffuz qo'llanmasi")
        else:
            await safe_edit(query, err, reply_markup=build_pronunciation_keyboard(accent), parse_mode="Markdown")
        return

    if data == "do_rules":
        await safe_edit(query, "📖 *Grammatika qoidalari*\n\nMavzuni tanlang:", reply_markup=build_rules_markup(), parse_mode="Markdown")
        return


    if data.startswith("rule__"):
        rule = data.split("__", 1)[1]
        if rule == "custom":
            context.user_data["awaiting_custom_rule"] = True
            await safe_edit(
                query,
                "\u270D\ufe0f *Qaysi grammatika mavzusini xohlaysiz?*\n\nMasalan: reported speech, modal verbs, phrasal verbs.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001F519 Orqaga", callback_data="do_rules")]]),
                parse_mode="Markdown",
            )
            return
        prompts = {
            "tenses": "Ingliz tilidagi barcha zamonlar: Simple, Continuous, Perfect, Perfect Continuous - batafsil o'zbekcha tushuntir, misollar bilan.",
            "articles": "a, an, the articlelar qachon ishlatilishi - batafsil o'zbekcha tushuntir, misollar bilan.",
            "prepositions": "in, on, at, for, to, with, by asosiy prepositionlar - o'zbekcha tushuntir.",
            "questions": "Yes/No va Wh- savollar tuzish qoidalari - o'zbekcha, misollar bilan.",
            "conditionals": "0, 1, 2, 3-type Conditional - har birini o'zbekcha misol bilan.",
            "passive": "Passive Voice barcha zamonlarda - Active va Passive farqini misol bilan.",
        }
        await safe_edit(query, "\u23F3 Tayyorlanmoqda...")
        response = await ask_ai(prompts.get(rule, rule), mode="rule", user_id=user.id)
        kb = [[InlineKeyboardButton("\U0001F519 Grammatika", callback_data="do_rules")]]
        await safe_edit(query, response, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return

    if data == "do_stats":
        stats_text = build_user_stats_text(user.id, user.first_name or "Foydalanuvchi")
        if not stats_text:
            await safe_edit(query, "Statistika hali yo'q.")
            return
        await safe_edit(query, stats_text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001F3E0 Menyu", callback_data="menu_back")]]), parse_mode="Markdown")
        return

    if data == "do_level":
        db_user = get_user(user.id)
        current = db_user["level"] if db_user else "A1"
        kb = []
        row = []
        for lvl in LEVELS:
            mark = "\u2705 " if lvl == current else ""
            row.append(InlineKeyboardButton(f"{mark}{lvl}", callback_data=f"setlvl__{lvl}"))
            if len(row) == 3:
                kb.append(row)
                row = []
        if row:
            kb.append(row)
        kb.append([InlineKeyboardButton("\U0001F3E0 Menyu", callback_data="menu_back")])
        await safe_edit(
            query,
            f"\U0001F3AF *Daraja tanlash*\n\nHozirgi: *{current}*\n\nQuiz natijalari va yozuvlaringiz asosida daraja avtomatik yangilanadi.",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="Markdown",
        )
        return

    if data.startswith("setlvl__"):
        level = data.split("__", 1)[1]
        set_level(user.id, level)
        await safe_edit(query, f"\u2705 Darajangiz *{level}* ga o'rnatildi!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001F3E0 Menyu", callback_data="menu_back")]]), parse_mode="Markdown")
        return

    if data == "do_level_auto":
        await safe_edit(query, "\U0001F50D *Auto daraja faollashtirilgan.*\n\nQuiz, test va yozgan inglizcha matnlaringiz asosida daraja avtomatik yangilanadi.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001F3E0 Menyu", callback_data="menu_back")]]), parse_mode="Markdown")
        return

    if data == "do_about":
        await safe_edit(query, build_about_text(), reply_markup=build_about_buttons(), parse_mode="Markdown")
        return

    if data == "do_webapp":
        markup = build_web_app_markup(user.id)
        if not markup:
            await safe_edit(query, "Web App URL hozircha sozlanmagan. Admin `.env` ichida `WEB_APP_URL` ni kiritishi kerak.", parse_mode="Markdown")
            return
        await safe_edit(query, build_webapp_intro_text(user.id), reply_markup=markup, parse_mode="Markdown")
        return

    if data == "menu_subscribe":
        await subscription_command_from_callback(query, context)
        return

    if data == "menu_mypayments":
        await my_payments_command(update, context)
        return

    if data == "menu_enter_promo":
        context.user_data["awaiting_promo_code"] = True
        await safe_edit(query, "\U0001F3AB *Promo kodni yuboring*\n\nMasalan: `SPRING2026`", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001F3E0 Menyu", callback_data="menu_back")]]), parse_mode="Markdown")
        return

    if data == "menu_bonus_center":
        await safe_edit(query, build_bonus_center_text(user.id, user.first_name or "Foydalanuvchi"), reply_markup=build_bonus_center_markup(user.id), parse_mode="Markdown")
        return
    if data == "menu_referral_panel":
        await safe_edit(
            query,
            build_referral_panel_text(user.id, user.first_name or "Foydalanuvchi"),
            reply_markup=build_referral_panel_markup(user.id),
            parse_mode="Markdown",
        )
        return


    if data == "menu_progress_panel":
        progress_text = build_progress_panel_text(user.id, user.first_name or "Foydalanuvchi", leaderboard_limit=5)
        if not progress_text:
            await safe_edit(query, "Statistika hozircha yo'q.")
            return
        await safe_edit(query, progress_text, reply_markup=build_progress_action_markup(user.id), parse_mode="Markdown")
        return

    if data == "menu_progress_html":
        doc = build_progress_report_doc(user.id, user.first_name or "Foydalanuvchi")
        if not doc:
            await safe_edit(query, "Statistika hozircha yo'q.", reply_markup=build_progress_action_markup(user.id))
            return
        await send_html_export(query.message.chat_id, context, doc, doc.name, caption="Progress report HTML")
        await safe_edit(query, "\u2705 HTML hisobot yuborildi.", reply_markup=build_progress_action_markup(user.id))
        return

    if data == "menu_leaderboard":
        await safe_edit(query, build_leaderboard_text(limit=10), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001F4C8 Darajam / Reyting", callback_data="menu_progress_panel")], [InlineKeyboardButton("\U0001F3E0 Menyu", callback_data="menu_back")]]), parse_mode="Markdown")
        return

    if data == "menu_back":
        await safe_edit(query, build_main_menu_hint(), parse_mode="Markdown")
        return


async def private_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.text:
        return
    user = message.from_user
    text = message.text.strip()
    upsert_user(user.id, user.username, user.first_name)
    db_user = get_user(user.id)

    if await admin_text_handler(update, context):
        return

    if context.user_data.get("awaiting_receipt"):
        await receipt_handler(update, context)
        return

    if not await ensure_sponsor_access(update, context):
        return

    if context.user_data.get("awaiting_promo_code"):
        context.user_data.pop("awaiting_promo_code", None)
        result = redeem_promo_code(user.id, text)
        if not result.get("ok"):
            reason = result.get("reason")
            fail_text = {
                "not_found": "Promo kod topilmadi yoki aktiv emas.",
                "already_used": "Siz bu promo kodni avval ishlatgansiz.",
                "limit": "Promo kod limiti tugagan.",
            }.get(reason, "Promo kodni qo'llab bo'lmadi.")
            await safe_reply(message, fail_text, reply_markup=build_bonus_center_markup(user.id))
            return
        await safe_reply(message, f"\u2705 Promo kod qabul qilindi. +{result['points']} ball qo'shildi.", reply_markup=build_bonus_center_markup(user.id))
        return

    menu_text = normalize_quick_menu_text(text)
    if menu_text == "menyu":
        await start(update, context)
        return
    if menu_text in ("obuna", "tariflar"):
        await subscription_command(update, context)
        return
    if menu_text == "bonuslar":
        await safe_reply(message, build_bonus_center_text(user.id, user.first_name or "Foydalanuvchi"), reply_markup=build_bonus_center_markup(user.id), parse_mode="Markdown")
        return
    if menu_text == "to'lovlar":
        await my_payments_command(update, context)
        return
    if menu_text in ("web app", "webapp", "app"):
        markup = build_web_app_markup(user.id, include_back=False)
        if not markup:
            await safe_reply(message, "Web App URL hozircha sozlanmagan. Admin `WEB_APP_URL` ni kiritishi kerak.")
            return
        await safe_reply(message, build_webapp_intro_text(user.id), reply_markup=markup, parse_mode="Markdown")
        return
    if menu_text == "aloqa":
        await safe_reply(message, build_about_text(), reply_markup=build_about_buttons(), parse_mode="Markdown")
        return
    if menu_text == "progress":
        progress_text = build_progress_panel_text(user.id, user.first_name or "Foydalanuvchi", leaderboard_limit=5)
        if not progress_text:
            await safe_reply(message, "Statistika hozircha yo'q.")
        else:
            await safe_reply(message, progress_text, reply_markup=build_progress_action_markup(user.id), parse_mode="Markdown")
        return
    if menu_text == "tekshiruv":
        context.user_data["mode"] = "check"
        await safe_reply(message, "\u2705 Tekshiruv rejimi yoqildi. Inglizcha matn yuboring.")
        return
    if menu_text == "tarjima":
        await safe_reply(
            message,
            "🔁 Tarjima bo'limi\n\nQaysi yo'nalishda ishlamoqchisiz?",
            reply_markup=build_translation_direction_markup(),
            parse_mode="Markdown",
        )
        return
    if menu_text == "talaffuz":
        context.user_data["mode"] = "pronunciation"
        accent = context.user_data.get("pron_accent", "us")
        accent_label = "UK" if accent == "uk" else "US"
        await safe_reply(message, "🔊 Talaffuz rejimi yoqildi.\n" f"Hozirgi sheva: {accent_label}\n" "So'z yoki gap yuboring.", reply_markup=build_pronunciation_keyboard(accent))
        return
    if menu_text == "quiz":
        await quiz_command(update, context)
        return
    if menu_text in ("iq test", "iqtest"):
        await iq_command(update, context)
        return
    if menu_text == "dars":
        allowed, used, limit = check_limit(user.id, "lessons")
        if not allowed:
            await safe_reply(message, f"Kunlik dars limiti tugadi ({limit}/kun). Obuna bo'limini oching.")
            return
        db_user = get_user(user.id)
        level = (db_user or {}).get("level", "A1")
        topics = get_lesson_topics_for_level(level)
        await safe_reply(message, f"Darajangiz: {level}\nMavzu tanlang:", reply_markup=build_topic_keyboard(topics))
        return
    if menu_text == "grammatika":
        await safe_reply(message, "📖 *Grammatika qoidalari*\n\nMavzuni tanlang:", reply_markup=build_rules_markup(), parse_mode="Markdown")
        return
    if menu_text == "kunlik so'z":
        status_msg = await safe_reply(message, "📅 Kunlik so'z tayyorlanmoqda...")
        data_json = await ask_json("So'z", mode="daily_word")
        await safe_delete(status_msg)
        if data_json:
            daily_text = build_daily_word_text(data_json)
            kb = [[InlineKeyboardButton("🔊 Talaffuz", callback_data=f"pron__{data_json.get('word', '')}"), InlineKeyboardButton("🏠 Menyu", callback_data="menu_back")]]
            await safe_reply(message, daily_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return

    if context.user_data.get("awaiting_level_test"):
        context.user_data.pop("awaiting_level_test")
        status_msg = await safe_reply(message, "\U0001F9ED Darajangiz aniqlanmoqda...")
        result = await ask_json(text, mode="level_test")
        await safe_delete(status_msg)
        if result:
            level = result.get("level", "A1")
            set_level(user.id, level)
            await safe_reply(message, f"\u2705 *Darajangiz: {escape_md(level)}*\n\n{result.get('reason', '')}\n\nBot endi shunga mos tushuntiradi!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001F3E0 Menyu", callback_data="menu_back")]]), parse_mode="Markdown")
        return

    mode = context.user_data.get("mode", "auto")

    if mode == "pronunciation":
        if text.strip().lower() in {"bekor", "cancel", "stop", "exit", "chiqish", "orqaga", "ortga"}:
            context.user_data.pop("mode", None)
            await safe_reply(
                message,
                "✅ Talaffuz rejimi o'chirildi. Endi odatiy rejimdasiz.",
                reply_markup=quick_menu_kb((db_user or {}).get("role", "user"), user_id=user.id),
            )
            return
        if not await limit_check(update, user.id, "pron_audio"):
            return
        accent = context.user_data.get("pron_accent", "us")
        accent_label = "UK" if accent == "uk" else "US"
        status_msg = await safe_reply(message, f"\U0001F50A Talaffuz ({accent_label}) tayyorlanmoqda...")
        analysis = await ask_ai(text, mode="pronunciation", user_id=user.id)
        ok, err = await send_pronunciation_audio(message.chat_id, context, text, accent, caption=build_pronunciation_caption(text, analysis, accent))
        await safe_delete(status_msg)
        if ok:
            inc_usage(user.id, "pron_audio")
            inc_stat(user.id, "messages_total")
            await safe_reply(message, analysis, reply_markup=build_pronunciation_keyboard(accent), parse_mode="Markdown")
            doc = build_pronunciation_html_doc(text, accent, analysis, user.first_name or "User", user.id)
            await send_html_export(message.chat_id, context, doc, doc.name, caption="Talaffuz qo'llanmasi")
        else:
            await safe_reply(message, err, reply_markup=build_pronunciation_keyboard(accent))
        return

    field_map = {"check": "checks", "uz_to_en": "checks", "en_to_uz": "checks", "auto": "ai_messages"}
    field = field_map.get(mode, "ai_messages")
    if not await limit_check(update, user.id, field):
        return

    if context.user_data.get("awaiting_custom_rule"):
        context.user_data.pop("awaiting_custom_rule")
        status_msg = await safe_reply(message, "\u23F3 Grammatika mavzusi tayyorlanmoqda...")
        response = await ask_ai(f"{text} mavzusini batafsil va uzunroq tushuntir, misollar, xatolar va mini mashqlar bilan.", mode="rule", user_id=user.id)
        await safe_delete(status_msg)
        await safe_reply(message, response, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001F3E0 Menyu", callback_data="menu_back")]]), parse_mode="Markdown")
        return

    status_msg = await safe_reply(message, "\u23F3 Tayyorlanmoqda...")
    response = await ask_ai(text, mode=mode, user_id=user.id, use_history=(mode == "auto"))
    await safe_delete(status_msg)
    inc_usage(user.id, field)
    inc_stat(user.id, "messages_total")
    if mode == "check":
        inc_stat(user.id, "checks_total")

    level_guess = extract_level_guess(response) if mode in ("check", "auto") else None
    if level_guess:
        record_level_signal(user.id, mode, level_guess)
        level_result = auto_adjust_level_from_signals(user.id)
        if level_result["changed"]:
            response += f"\n\n\U0001F393 *Daraja yangilandi:* *{escape_md(level_result['old_level'])}* -> *{escape_md(level_result['new_level'])}*\n{escape_md(level_result['reason'])}"

    kb = [[InlineKeyboardButton("\U0001F3E0 Menyu", callback_data="menu_back")]]
    await safe_reply(message, response, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    if mode == "check":
        parsed = parse_check_response(response)
        document = render_html_document(
            "grammar_analysis.html",
            {
                "title": "Grammar Analysis",
                "user_name": user.first_name or "User",
                "analysis_items": parsed["analysis_items"] or ["Tahlil mavjud emas."],
                "corrected_text": parsed["corrected_text"],
                "level_guess": parsed["level_guess"],
                "rule_text": parsed["rule_text"] or "Asosiy qoida ajratilmadi.",
                "theme_seed": f"grammar:{text[:80]}",
            },
            f"grammar_analysis_{user.id}.html",
        )
        await send_html_export(message.chat_id, context, document, document.name)
    elif mode in ("uz_to_en", "en_to_uz"):
        document = build_translation_html_doc(text, response, mode, user.first_name or "User", user.id)
        await send_html_export(message.chat_id, context, document, document.name, caption="Tarjima HTML qo'llanmasi")


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await admin_media_handler(update, context):
        return
    if context.user_data.get("awaiting_receipt"):
        await receipt_handler(update, context)


async def web_app_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user
    if not message or not user or not getattr(message, "web_app_data", None):
        return

    upsert_user(user.id, user.username, user.first_name)
    raw = message.web_app_data.data or ""
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            data = {}
    except Exception:
        data = {}

    def apply_payload(payload: dict):
        action = str(payload.get("action", "")).strip().lower()
        if action == "pomodoro_done":
            minutes = max(1, min(int(payload.get("minutes", 25) or 25), 180))
            points = max(1, min(int(payload.get("points", max(1, minutes // 5)) or max(1, minutes // 5)), 100))
            add_webapp_progress(user.id, focus_minutes=minutes, points_earned=points)
            return

        if action == "tracker_sync":
            words = max(0, min(int(payload.get("words", 0) or 0), 1000))
            quizzes = max(0, min(int(payload.get("quizzes", 0) or 0), 300))
            lessons = max(0, min(int(payload.get("lessons", 0) or 0), 300))
            points = max(0, min(int(payload.get("points", 0) or 0), 10000))
            set_webapp_progress_snapshot(
                user.id,
                words_learned=words,
                quiz_completed=quizzes,
                lessons_completed=lessons,
                points_earned=points,
            )
            return

        if action == "settings_sync":
            return

    action = str(data.get("action", "")).strip().lower()
    if action == "bulk_sync":
        items = data.get("items") or []
        if isinstance(items, list):
            for item in items[:25]:
                if isinstance(item, dict):
                    apply_payload(item)
        return

    apply_payload(data)


# Guruh xabarlari

# Guruh xabarlari
async def group_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.text:
        return
    user = message.from_user
    text = message.text.strip()
    text_lower = text.lower()
    chat_id = message.chat_id
    upsert_user(user.id, user.username, user.first_name)
    settings = get_group(chat_id)
    inc_stat(user.id, "messages_total")

    mention_payload = extract_mention_payload(text)
    if mention_payload is not None and settings["bot_enabled"]:
        mode, content = parse_request_mode(mention_payload)
        content = (content or "").strip()
        if not content:
            await safe_reply(
                message,
                f"Foydalanish:\n{BOT_USERNAME} your text\n{BOT_USERNAME} tr: matn\n{BOT_USERNAME} p: word",
            )
            return

        if mode == "check":
            if not settings["check_enabled"]:
                await safe_reply(message, "Bu guruhda tekshiruv o'chirilgan.")
                return
            allowed, _, limit = check_limit(user.id, "checks")
            if not allowed:
                await safe_reply(message, f"Kunlik limit: {limit}/kun. /subscribe")
                return
            status_msg = await safe_reply(message, "Tekshirilmoqda...")
            r = await ask_ai(content, mode="check", user_id=user.id)
            await safe_delete(status_msg)
            inc_usage(user.id, "checks")
            inc_stat(user.id, "checks_total")
            level_guess = extract_level_guess(r)
            if level_guess:
                record_level_signal(user.id, "group_check", level_guess)
                level_result = auto_adjust_level_from_signals(user.id)
                if level_result["changed"]:
                    r += (
                        f"\n\n*Daraja yangilandi:* "
                        f"*{escape_md(level_result['old_level'])}* -> *{escape_md(level_result['new_level'])}*"
                    )
            kb = [[InlineKeyboardButton("Yana tekshirish", switch_inline_query_current_chat=content)]]
            await safe_reply(message, r, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
            parsed = parse_check_response(r)
            document = render_html_document(
                "grammar_analysis.html",
                {
                    "title": "Grammar Analysis",
                    "user_name": user.first_name or "User",
                    "analysis_items": parsed["analysis_items"] or ["Tahlil mavjud emas."],
                    "corrected_text": parsed["corrected_text"],
                    "level_guess": parsed["level_guess"],
                    "rule_text": parsed["rule_text"] or "Asosiy qoida ajratilmadi.",
                    "theme_seed": f"grammar:{content[:80]}",
                },
                f"grammar_analysis_{user.id}.html",
            )
            await send_html_export(message.chat_id, context, document, document.name)
            return

        if mode == "general":
            allowed, _, limit = check_limit(user.id, "ai_messages")
            if not allowed:
                await safe_reply(message, f"Kunlik AI limit: {limit}/kun.")
                return
            status_msg = await safe_reply(message, "Javob tayyorlanmoqda...")
            r = await ask_ai(content, mode="general", user_id=user.id)
            await safe_delete(status_msg)
            inc_usage(user.id, "ai_messages")
            await safe_reply(message, r, parse_mode="Markdown")
            return

        if mode in ("uz_to_en", "en_to_uz"):
            if not settings.get("translate_enabled", 1):
                await safe_reply(message, "Bu guruhda tarjima o'chirilgan.")
                return
            status_msg = await safe_reply(message, "Tarjima qilinmoqda...")
            r = await ask_ai(content, mode=mode, user_id=user.id)
            await safe_delete(status_msg)
            await safe_reply(message, r, parse_mode="Markdown")
            document = build_translation_html_doc(content, r, mode, user.first_name or "User", user.id)
            await send_html_export(message.chat_id, context, document, document.name, caption="Tarjima HTML qo'llanmasi")
            return


        if mode == "pronunciation":
            if not settings.get("pronunciation_enabled", 1):
                await safe_reply(message, "Bu guruhda talaffuz o'chirilgan.")
                return
            if not await limit_check(update, user.id, "pron_audio"):
                return
            accent, term = parse_pronunciation_target(content)
            if not term:
                await safe_reply(message, "Format: `p us: word` yoki `p uk: word`", parse_mode="Markdown")
                return
            status_msg = await safe_reply(message, f"Talaffuz ({accent.upper()}) tayyorlanmoqda...")
            r = await ask_ai(term, mode="pronunciation", user_id=user.id)
            await safe_delete(status_msg)
            caption = build_pronunciation_caption(term, r, accent)
            ok, audio_error = await send_pronunciation_audio(
                message.chat_id,
                context,
                term,
                accent=accent,
                caption=caption,
            )
            await safe_reply(message, r, parse_mode="Markdown")
            if not ok:
                await safe_reply(message, audio_error)
            else:
                inc_usage(user.id, "pron_audio")
                doc = build_pronunciation_html_doc(term, accent, r, user.first_name or "User", user.id)
                await send_html_export(message.chat_id, context, doc, doc.name, caption="Talaffuz qo'llanmasi")
            return

    if "#check" in text_lower and settings["check_enabled"]:
        content = re.sub(r"#check", "", text, flags=re.IGNORECASE).strip()
        if not content:
            await safe_reply(message, "\u274C matn #check", parse_mode="Markdown")
            return
        allowed, used, limit = check_limit(user.id, "checks")
        if not allowed:
            await safe_reply(message, f"\u26A0\ufe0f Kunlik limit: {limit}/kun.")
            return
        status_msg = await safe_reply(message, "\u23F3 Tekshirilmoqda...")
        r = await ask_ai(content, mode="check", user_id=user.id)
        await safe_delete(status_msg)
        inc_usage(user.id, "checks")
        inc_stat(user.id, "checks_total")
        await safe_reply(message, r, parse_mode="Markdown")
        parsed = parse_check_response(r)
        document = render_html_document(
            "grammar_analysis.html",
            {
                "title": "Grammar Analysis",
                "user_name": user.first_name or "User",
                "analysis_items": parsed["analysis_items"] or ["Tahlil mavjud emas."],
                "corrected_text": parsed["corrected_text"],
                "level_guess": parsed["level_guess"],
                "rule_text": parsed["rule_text"] or "Asosiy qoida ajratilmadi.",
                "theme_seed": f"grammar:{content[:80]}",
            },
            f"grammar_analysis_{user.id}.html",
        )
        await send_html_export(message.chat_id, context, document, document.name)

    elif "#bot" in text_lower and settings["bot_enabled"]:
        content = re.sub(r"#bot", "", text, flags=re.IGNORECASE).strip()
        if not content:
            await safe_reply(message, "\u274C #bot savol", parse_mode="Markdown")
            return
        allowed, _, limit = check_limit(user.id, "ai_messages")
        if not allowed:
            await safe_reply(message, f"\u26A0\ufe0f Kunlik AI limit: {limit}/kun.")
            return
        status_msg = await safe_reply(message, "⏳ Javob tayyorlanmoqda...")
        r = await ask_ai(content, mode="general", user_id=user.id)
        await safe_delete(status_msg)
        inc_usage(user.id, "ai_messages")
        await safe_reply(message, r, parse_mode="Markdown")

    elif re.search(r"\B#t\b", text, re.IGNORECASE):
        if not settings.get("translate_enabled", 1):
            await safe_reply(message, "Bu guruhda tarjima o'chirilgan.")
            return
        content = re.sub(r"\B#t\b", "", text, flags=re.IGNORECASE).strip()
        if not content:
            await safe_reply(message, "❌ #t matn", parse_mode="Markdown")
            return
        translate_mode = detect_translation_mode(content)
        status_msg = await safe_reply(message, "🔁 Tarjima qilinmoqda...")
        r = await ask_ai(content, mode=translate_mode, user_id=user.id)
        await safe_delete(status_msg)
        await safe_reply(message, r, parse_mode="Markdown")
        document = build_translation_html_doc(content, r, translate_mode, user.first_name or "User", user.id)
        await send_html_export(message.chat_id, context, document, document.name, caption="Tarjima HTML qo'llanmasi")

    elif re.search(r"\B#p\b", text, re.IGNORECASE):
        if not settings.get("pronunciation_enabled", 1):
            await safe_reply(message, "Bu guruhda talaffuz o'chirilgan.")
            return
        content = re.sub(r"\B#p\b", "", text, flags=re.IGNORECASE).strip()
        if not content:
            await safe_reply(message, "Format: `#p so'z` yoki `#p us: word`", parse_mode="Markdown")
            return
        if not await limit_check(update, user.id, "pron_audio"):
            return
        accent, term = parse_pronunciation_target(content)
        if not term:
            await safe_reply(message, "Format: `#p us: word` yoki `#p uk: word`", parse_mode="Markdown")
            return
        status_msg = await safe_reply(message, f"Talaffuz ({accent.upper()}) tayyorlanmoqda...")
        r = await ask_ai(term, mode="pronunciation", user_id=user.id)
        await safe_delete(status_msg)
        caption = build_pronunciation_caption(term, r, accent)
        ok, audio_error = await send_pronunciation_audio(
            message.chat_id,
            context,
            term,
            accent=accent,
            caption=caption,
        )
        await safe_reply(message, r, parse_mode="Markdown")
        if not ok:
            await safe_reply(message, audio_error)
        else:
            inc_usage(user.id, "pron_audio")
            doc = build_pronunciation_html_doc(term, accent, r, user.first_name or "User", user.id)
            await send_html_export(message.chat_id, context, doc, doc.name, caption="Talaffuz qo'llanmasi")


async def inline_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query
    if not query:
        return

    text = (query.query or "").strip()
    results = []

    if not text:
        examples = [
            InlineQueryResultArticle(
                id=str(uuid.uuid4()),
                title=f"Check: {BOT_USERNAME} your text",
                description="Tekshiruv va HTML variantlari chiqadi.",
                input_message_content=InputTextMessageContent(
                    f"Inline Check\n\nMatn yozing: {BOT_USERNAME} your sentence"
                ),
            ),
            InlineQueryResultArticle(
                id=str(uuid.uuid4()),
                title=f"Translate: {BOT_USERNAME} tr: ...",
                description="O'zbek -> Ingliz",
                input_message_content=InputTextMessageContent(
                    f"Inline Translate\n\n{BOT_USERNAME} tr: men bugun ishlayman"
                ),
            ),
            InlineQueryResultArticle(
                id=str(uuid.uuid4()),
                title=f"Pronunciation: {BOT_USERNAME} p: ...",
                description="Audio va qo'shimcha qo'llanma variantlari chiqadi.",
                input_message_content=InputTextMessageContent(
                    f"Inline Pronunciation\n\n{BOT_USERNAME} p: us: serendipity"
                ),
            ),
        ]
        await query.answer(examples, cache_time=10, is_personal=True)
        return

    mode, content = parse_request_mode(text)
    content = content.strip()
    if not content:
        await query.answer([], cache_time=5, is_personal=True)
        return

    if mode == "pronunciation":
        accent, term = parse_pronunciation_target(content)
        preview = term or content
        private_id = f"pri_{uuid.uuid4().hex}"
        remember_inline_result(context, private_id, mode, content, "", export_mode="private")
        results.append(
            InlineQueryResultArticle(
                id=private_id,
                title=f"Talaffuz {accent.upper()} maxfiy: {preview[:32]}",
                description=build_inline_delivery_note("Audio va HTML", "private"),
                input_message_content=InputTextMessageContent("Talaffuz tayyorlanmoqda..."),
                reply_markup=build_inline_pending_markup(),
            )
        )
        if INLINE_AUDIO_CHANNEL:
            public_id = f"pub_{uuid.uuid4().hex}"
            remember_inline_result(context, public_id, mode, content, "", export_mode="channel")
            results.append(
                InlineQueryResultArticle(
                    id=public_id,
                    title=f"Talaffuz {accent.upper()} ochiq: {preview[:32]}",
                    description=build_inline_delivery_note("Audio va HTML", "channel"),
                    input_message_content=InputTextMessageContent("Talaffuz tayyorlanmoqda..."),
                    reply_markup=build_inline_pending_markup(),
                )
            )
        await query.answer(results, cache_time=8, is_personal=True)
        return

    if mode == "check":
        private_id = f"pri_{uuid.uuid4().hex}"
        remember_inline_result(context, private_id, mode, content, "", export_mode="private")
        results.append(
            InlineQueryResultArticle(
                id=private_id,
                title=f"Tekshiruv maxfiy: {content[:34]}",
                description=build_inline_delivery_note("HTML qo'llanma", "private"),
                input_message_content=InputTextMessageContent("Tekshiruv tayyorlanmoqda..."),
                reply_markup=build_inline_pending_markup(),
            )
        )
        if INLINE_HTML_CHANNEL:
            public_id = f"pub_{uuid.uuid4().hex}"
            remember_inline_result(context, public_id, mode, content, "", export_mode="channel")
            results.append(
                InlineQueryResultArticle(
                    id=public_id,
                    title=f"Tekshiruv ochiq: {content[:34]}",
                    description=build_inline_delivery_note("HTML qo'llanma", "channel"),
                    input_message_content=InputTextMessageContent("Tekshiruv tayyorlanmoqda..."),
                    reply_markup=build_inline_pending_markup(),
                )
            )
        await query.answer(results, cache_time=8, is_personal=True)
        return

    translate_label = "O'zbek -> Ingliz" if mode == "uz_to_en" else "Ingliz -> O'zbek" if mode == "en_to_uz" else "Ingliz bo'yicha yordam"
    result_id = f"pri_{uuid.uuid4().hex}"
    title = f"Tarjima maxfiy: {content[:40]}" if mode in ("uz_to_en", "en_to_uz") else f"AI javob: {content[:40]}"
    remember_inline_result(context, result_id, mode, content, "", export_mode="private")
    results.append(
        InlineQueryResultArticle(
            id=result_id,
            title=title,
            description=build_inline_delivery_note("HTML qo'llanma", "private") if mode in ("uz_to_en", "en_to_uz") else translate_label,
            input_message_content=InputTextMessageContent("Natija tayyorlanmoqda..."),
            reply_markup=build_inline_pending_markup(),
        )
    )
    if mode in ("uz_to_en", "en_to_uz") and INLINE_HTML_CHANNEL:
        public_id = f"pub_{uuid.uuid4().hex}"
        remember_inline_result(context, public_id, mode, content, "", export_mode="channel")
        results.append(
            InlineQueryResultArticle(
                id=public_id,
                title=f"Tarjima ochiq: {content[:40]}",
                description=build_inline_delivery_note("HTML qo'llanma", "channel"),
                input_message_content=InputTextMessageContent("Natija tayyorlanmoqda..."),
                reply_markup=build_inline_pending_markup(),
            )
        )
    await query.answer(results, cache_time=8, is_personal=True)



async def chosen_inline_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chosen = update.chosen_inline_result
    if not chosen:
        return

    user = chosen.from_user
    if not user:
        return

    upsert_user(user.id, user.username, user.first_name)
    cached = pop_inline_result(context, chosen.result_id)
    mode, content = parse_request_mode((chosen.query or "").strip())
    answer = ""
    rid = str(chosen.result_id or "")
    export_mode = "channel" if rid.startswith("pub_") else "private"

    if cached:
        mode = str(cached.get("mode") or mode)
        content = str(cached.get("content") or content)
        answer = str(cached.get("answer") or "")
        export_mode = str(cached.get("export_mode") or export_mode)

    content = (content or "").strip()
    if not content:
        return

    try:
        if mode == "pronunciation":
            allowed, _, limit = check_limit(user.id, "pron_audio")
            if not allowed:
                await update_inline_text_result(context, chosen, user.id, f"Inline talaffuz limiti tugadi. Limit: {limit}/kun.")
                return
            accent, term = parse_pronunciation_target(content)
            if not term:
                await update_inline_text_result(context, chosen, user.id, "Format: p us: word yoki p uk: word")
                return
            if not answer:
                answer = await ask_ai(term, mode="pronunciation", user_id=user.id)

            if export_mode == "channel" and INLINE_AUDIO_CHANNEL:
                export_id = build_export_id("A")
                tts_result = await synthesize_pronunciation(term, accent=accent)
                if not tts_result.get("ok"):
                    await update_inline_text_result(context, chosen, user.id, "Audio yaratishda muammo chiqdi.")
                    return
                ext = "mp3"
                audio_file = make_audio_file(tts_result["audio"], f"inline_audio_{export_id}.{ext}")
                caption = (build_pronunciation_caption(term, answer, accent) + f"\n\nID: {export_id}")[:1024]
                sent = await context.bot.send_audio(
                    chat_id=INLINE_AUDIO_CHANNEL,
                    audio=audio_file,
                    filename=audio_file.name,
                    caption=caption,
                )
                inc_usage(user.id, "pron_audio")
                html_channel = INLINE_HTML_CHANNEL or INLINE_AUDIO_CHANNEL
                doc = build_pronunciation_html_doc(term, accent, answer, user.first_name or "User", user.id)
                html_sent = await context.bot.send_document(
                    chat_id=html_channel,
                    document=doc,
                    filename=doc.name,
                    caption=(f"Inline talaffuz qo'llanmasi\nID: {export_id}")[:1024],
                )
                audio_link = build_channel_post_link(INLINE_AUDIO_CHANNEL, sent.message_id)
                html_link = build_channel_post_link(html_channel, html_sent.message_id)
                await attach_inline_export_info(
                    context,
                    chosen,
                    user.id,
                    answer,
                    export_id,
                    "Audio/HTML",
                    links=[("Audio havola", audio_link), ("HTML havola", html_link)],
                )
                return

            caption = build_pronunciation_caption(term, answer, accent)
            ok, msg = await send_pronunciation_audio(user.id, context, term, accent=accent, caption=caption)
            if not ok:
                await update_inline_text_result(context, chosen, user.id, msg)
                return
            inc_usage(user.id, "pron_audio")
            doc = build_pronunciation_html_doc(term, accent, answer, user.first_name or "User", user.id)
            await send_html_export(user.id, context, doc, doc.name, caption="Inline talaffuz qo'llanmasi")
            await update_inline_text_result(context, chosen, user.id, answer)
            return

        if mode == "check":
            allowed, _, limit = check_limit(user.id, "checks")
            if not allowed:
                await update_inline_text_result(context, chosen, user.id, f"Inline tekshiruv limiti tugadi. Limit: {limit}/kun.")
                return
            if not answer:
                answer = await ask_ai(content, mode="check", user_id=user.id)
            inc_usage(user.id, "checks")
            parsed = parse_check_response(answer)
            document = render_html_document(
                "grammar_analysis.html",
                {
                    "title": "Inline Grammar Analysis",
                    "user_name": user.first_name or "User",
                    "analysis_items": parsed["analysis_items"] or ["Tahlil mavjud emas."],
                    "corrected_text": parsed["corrected_text"],
                    "level_guess": parsed["level_guess"],
                    "rule_text": parsed["rule_text"] or "Asosiy qoida ajratilmadi.",
                    "theme_seed": f"inline-grammar:{content[:80]}",
                },
                f"inline_grammar_{user.id}.html",
            )
            if export_mode == "channel" and INLINE_HTML_CHANNEL:
                export_id = build_export_id("H")
                sent = await context.bot.send_document(
                    chat_id=INLINE_HTML_CHANNEL,
                    document=document,
                    filename=document.name,
                    caption=(f"Inline tekshiruv HTML qo'llanmasi\nID: {export_id}")[:1024],
                )
                html_link = build_channel_post_link(INLINE_HTML_CHANNEL, sent.message_id)
                await attach_inline_export_info(
                    context,
                    chosen,
                    user.id,
                    answer,
                    export_id,
                    "HTML",
                    links=[("HTML havola", html_link)],
                )
                return
            await send_html_export(
                user.id,
                context,
                document,
                document.name,
                caption="Inline tekshiruv HTML qo'llanmasi",
            )
            await update_inline_text_result(context, chosen, user.id, answer)
            return

        if mode in ("uz_to_en", "en_to_uz", "general"):
            allowed, _, limit = check_limit(user.id, "ai_messages")
            if not allowed:
                await update_inline_text_result(context, chosen, user.id, f"Inline AI limiti tugadi. Limit: {limit}/kun.")
                return
            if not answer:
                answer = await ask_ai(content, mode=mode, user_id=user.id)
            inc_usage(user.id, "ai_messages")
            if mode in ("uz_to_en", "en_to_uz"):
                document = build_translation_html_doc(content, answer, mode, user.first_name or "User", user.id)
                if export_mode == "channel" and INLINE_HTML_CHANNEL:
                    export_id = build_export_id("T")
                    sent = await context.bot.send_document(
                        chat_id=INLINE_HTML_CHANNEL,
                        document=document,
                        filename=document.name,
                        caption=(f"Inline tarjima HTML qo'llanmasi\nID: {export_id}")[:1024],
                    )
                    html_link = build_channel_post_link(INLINE_HTML_CHANNEL, sent.message_id)
                    await attach_inline_export_info(
                        context,
                        chosen,
                        user.id,
                        answer,
                        export_id,
                        "HTML",
                        links=[("HTML havola", html_link)],
                    )
                    return
                await send_html_export(user.id, context, document, document.name, caption="Inline tarjima HTML qo'llanmasi")
            await update_inline_text_result(context, chosen, user.id, answer)
            return
    except Exception as e:
        logger.warning("Inline follow-up yuborilmadi: %s", e)


async def joined_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for m in update.message.new_chat_members:
        if m.id == context.bot.id:
            await safe_reply(
                update.message,
                "\U0001F44B *English Teacher Bot* guruhga qo'shildi!\n\n"
                "#check [matn] - tekshiruv\n"
                "#bot [savol] - AI savol\n"
                "#t [matn] - tarjima\n"
                "#p [so'z] - talaffuz\n\n"
                f"Mention bilan ham ishlaydi: {BOT_USERNAME} your text\n\n"
                "/admin - guruh sozlamalari\n/help - batafsil yordam",
                parse_mode="Markdown",
            )


async def daily_job(context):
    groups = get_daily_groups()
    for g in groups:
        data = await ask_json("So'z", mode="daily_word")
        if data:
            text = build_daily_word_text(data)
            try:
                await context.bot.send_message(g["chat_id"], text, parse_mode="Markdown")
            except BadRequest:
                try:
                    await context.bot.send_message(g["chat_id"], text)
                except Exception as e:
                    logger.warning(f"Daily job: {e}")
            except Exception as e:
                logger.warning(f"Daily job: {e}")




# Buyruqlar
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db_user = get_user(user.id) or {}
    role = str(db_user.get("role", "user")).lower()
    extra = "/awake - Service awake monitor (admin)\\n" if role in ("owner", "admin") else ""
    await safe_reply(
        update.message,
        "\U0001F4D6 *Buyruqlar*\n\n"
        "/start - Bosh menyu\n"
        "/subscribe - Obuna rejalari\n"
        "/mypayments - To'lovlar tarixi\n"
        "/mystats - Darajam va reyting\n"
        f"{extra}"
        "/promo - Promo kod ishlatish\n"
        "/clear - Suhbat tarixini tozalash\n"
        "/quiz - Quiz boshlash\n"
        "/iqtest - IQ test boshlash\n"
        "/app - Telegram Web App\n"
        "/admin - Admin panel\n\n"
        "*Guruhda:*\n"
        "#check [matn] - tekshiruv\n"
        "#bot [savol] - AI savol\n"
        "#t [matn] - tarjima\n"
        "#p [so'z] - talaffuz\n\n"
        "*Inline:*\n"
        f"{BOT_USERNAME} your text - tekshiruv\n"
        f"{BOT_USERNAME} tr: matn - tarjima\n"
        f"{BOT_USERNAME} p: us: word - talaffuz\n\n"
        "Asosiy boshqaruv keyboard orqali ishlaydi.",
        parse_mode="Markdown",
    )


async def subscribe_command_guarded(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_sponsor_access(update, context):
        return
    await subscription_command(update, context)


async def mypayments_command_guarded(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_sponsor_access(update, context):
        return
    await my_payments_command(update, context)


async def quiz_command_guarded(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_sponsor_access(update, context):
        return
    await quiz_command(update, context)


async def iq_command_guarded(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_sponsor_access(update, context):
        return
    await iq_command(update, context)


async def mystats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_sponsor_access(update, context):
        return
    progress_text = build_progress_panel_text(update.effective_user.id, update.effective_user.first_name or "Foydalanuvchi", leaderboard_limit=5)
    if not progress_text:
        await safe_reply(update.message, "Statistika hozircha yo'q.")
        return
    await safe_reply(
        update.message,
        progress_text,
        reply_markup=build_progress_action_markup(update.effective_user.id),
        parse_mode="Markdown",
    )


async def awake_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db_user = get_user(user.id) or {}
    role = str(db_user.get("role", "user")).lower()
    if role not in ("owner", "admin"):
        await safe_reply(update.effective_message, "Bu bo'lim faqat admin/owner uchun.")
        return

    stats = get_service_hit_summary(limit=12)
    last_at = stats.get("last_at") or "-"
    total = int(stats.get("total", 0) or 0)
    h1 = int(stats.get("last_1h", 0) or 0)
    h24 = int(stats.get("last_24h", 0) or 0)

    rows = []
    for i, r in enumerate(stats.get("recent", []), start=1):
        ts = r.get("created_at", "-")
        path = r.get("path", "-")
        ip = r.get("ip", "-")
        ua = (r.get("user_agent") or "-")[:30]
        rows.append(f"{i}. {ts} | {path} | {ip} | {ua}")

    history = "\n".join(rows) if rows else "Hozircha kirishlar yo'q."
    text = (
        "🌐 Service Awake Monitor\n\n"
        f"So'nggi kirish: {last_at}\n"
        f"Jami kirish: {total}\n"
        f"1 soat: {h1}\n"
        f"24 soat: {h24}\n\n"
        "Oxirgi kirishlar:\n"
        f"{history}"
    )
    await safe_reply(update.effective_message, text)

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_history(update.effective_user.id)
    context.user_data.pop("mode", None)
    await safe_reply(update.message, "\U0001F5D1 Tarix tozalandi! Rejim: avtomatik.")


async def promo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_sponsor_access(update, context):
        return
    if not context.args:
        await safe_reply(update.message, "Promo kodni kiriting: `/promo KOD`", parse_mode="Markdown")
        return
    result = redeem_promo_code(update.effective_user.id, context.args[0])
    if not result.get("ok"):
        reason = result.get("reason")
        text = {
            "not_found": "Promo kod topilmadi yoki aktiv emas.",
            "already_used": "Siz bu promo kodni avval ishlatgansiz.",
            "limit": "Promo kod limiti tugagan.",
        }.get(reason, "Promo kodni qo'llab bo'lmadi.")
        await safe_reply(update.message, text)
        return
    await safe_reply(update.message, f"\u2705 Promo kod qabul qilindi. +{result['points']} ball qo'shildi.")
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.exception("Unhandled exception while processing update", exc_info=context.error)
    try:
        if isinstance(update, Update) and update.effective_message:
            await safe_reply(update.effective_message, 
                "Texnik xatolik yuz berdi. Iltimos, qayta urinib ko'ring yoki /start ni bosing."
            )
    except Exception:
        pass
    try:
        tb = "".join(traceback.format_exception_only(type(context.error), context.error)).strip()
        location = ""
        if isinstance(update, Update):
            user = update.effective_user
            chat = update.effective_chat
            location = f"user={getattr(user, 'id', '-')}, chat={getattr(chat, 'id', '-')}"
        text = f"Tizim xatoligi\n{location}\n{tb[:3200]}"
        for admin_id in get_admin_ids(include_owner=True):
            try:
                await context.bot.send_message(admin_id, text)
            except Exception:
                pass
    except Exception:
        pass


async def main():
    if not acquire_instance_lock():
        return

    init_db()

    # Owner ni DB ga qo'shish
    if OWNER_ID:
        from database.db import upsert_user as ups, set_role
        ups(OWNER_ID, "owner", "Owner")
        set_role(OWNER_ID, "owner")

    request = HTTPXRequest(connection_pool_size=TG_CONNECTION_POOL, connect_timeout=15.0, read_timeout=40.0, write_timeout=40.0, pool_timeout=TG_POOL_TIMEOUT)
    get_updates_request = HTTPXRequest(connection_pool_size=TG_CONNECTION_POOL, connect_timeout=15.0, read_timeout=70.0, write_timeout=40.0, pool_timeout=TG_POOL_TIMEOUT)
    app = Application.builder().token(BOT_TOKEN).request(request).get_updates_request(get_updates_request).concurrent_updates(UPDATE_CONCURRENCY).build()

    # Buyruqlar
    app.add_handler(CommandHandler("start",       start))
    app.add_handler(CommandHandler("help",        help_command))
    app.add_handler(CommandHandler("subscribe",   subscribe_command_guarded))
    app.add_handler(CommandHandler("mypayments",  mypayments_command_guarded))
    app.add_handler(CommandHandler("mystats",     mystats_command))
    app.add_handler(CommandHandler("awake",       awake_command))
    app.add_handler(CommandHandler("clear",       clear_command))
    app.add_handler(CommandHandler("promo",       promo_command))
    app.add_handler(CommandHandler("admin",       group_admin_command))
    app.add_handler(CommandHandler("quiz",        quiz_command_guarded))
    app.add_handler(CommandHandler("iqtest",      iq_command_guarded))
    app.add_handler(CommandHandler("app",         app_command))

    # Quiz callbacklar
    app.add_handler(CallbackQueryHandler(quiz_callback,      pattern=r"^qans_\d+_[A-D]_(quiz|iq)$"))
    app.add_handler(CallbackQueryHandler(quiz_callback,      pattern=r"^qans_\d+_stop_(quiz|iq)$"))
    app.add_handler(CallbackQueryHandler(quiz_picker_callback, pattern=r"^qpick_(quiz|iq)_\d+$"))
    app.add_handler(CallbackQueryHandler(quiz_time_callback, pattern=r"^qtime_(quiz|iq)_\d+_\d+$"))
    app.add_handler(CallbackQueryHandler(quiz_language_callback, pattern=r"^qlang_(quiz|iq)_\d+_\d+_(en|uz)$"))
    app.add_handler(CallbackQueryHandler(quiz_result_callback, pattern=r"^qresult_\d+_(quiz|iq)$"))
    app.add_handler(CallbackQueryHandler(quiz_next_callback, pattern=r"^qnext_"))

    # Obuna callbacklar
    app.add_handler(CallbackQueryHandler(sub_callback, pattern=r"^sub_"))

    # Admin callbacklar
    app.add_handler(CallbackQueryHandler(admin_callback,       pattern=r"^(adm_|pay_|paycfg_|plan_|grant_)"))
    app.add_handler(CallbackQueryHandler(group_admin_callback, pattern=r"^gadm_"))

    # Asosiy menu callbacklar (hammasi)
    app.add_handler(CallbackQueryHandler(main_callback))

    # Inline
    app.add_handler(InlineQueryHandler(inline_handler))
    app.add_handler(ChosenInlineResultHandler(chosen_inline_handler))

    # Ovozli
    from handlers.voice import voice_handler
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, voice_handler))

    # Guruhga qo'shilish
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, joined_group))

    # Guruh xabarlari
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS,
        group_handler
    ))

    app.add_handler(MessageHandler(
        (filters.PHOTO | filters.Document.ALL | filters.VIDEO) & filters.ChatType.PRIVATE,
        photo_handler
    ))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data_handler))

    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
        private_handler
    ))

    app.add_error_handler(error_handler)

    if app.job_queue:
        from datetime import time as dtime
        app.job_queue.run_daily(daily_job, time=dtime(3, 0, 0))

    async with app:
        await app.bot.set_my_commands([
            BotCommand("start",      "Bosh menyu"),
            BotCommand("subscribe",  "Obuna rejalari"),
            BotCommand("mypayments", "To'lovlar tarixi"),
            BotCommand("mystats",    "Statistika"),
            BotCommand("clear",      "Tarixni tozalash"),
            BotCommand("promo",      "Promo kod"),
            BotCommand("help",       "Yordam"),
            BotCommand("admin",      "Admin panel"),
            BotCommand("quiz",       "Quiz"),
            BotCommand("iqtest",     "IQ test"),
            BotCommand("app",        "Web App"),
        ])

        admin_commands = [
            BotCommand("start",      "Bosh menyu"),
            BotCommand("subscribe",  "Obuna rejalari"),
            BotCommand("mypayments", "To'lovlar tarixi"),
            BotCommand("mystats",    "Statistika"),
            BotCommand("awake",      "Service awake monitor"),
            BotCommand("clear",      "Tarixni tozalash"),
            BotCommand("promo",      "Promo kod"),
            BotCommand("help",       "Yordam"),
            BotCommand("admin",      "Admin panel"),
            BotCommand("quiz",       "Quiz"),
            BotCommand("iqtest",     "IQ test"),
            BotCommand("app",        "Web App"),
        ]
        for admin_id in get_admin_ids(include_owner=True):
            try:
                await app.bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(admin_id))
            except Exception:
                pass
        await app.start()
        health_server = None
        try:
            if USE_WEBHOOK and WEBHOOK_URL:
                await app.updater.start_webhook(
                    listen="0.0.0.0", port=WEBHOOK_PORT,
                    url_path=BOT_TOKEN,
                    webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
                )
            else:
                health_server = await start_health_server()
                await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)

            logger.info("Bot ishlamoqda!")
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                pass
        finally:
            try:
                if health_server:
                    health_server.close()
                    await health_server.wait_closed()
            except Exception:
                pass
            try:
                if app.updater.running:
                    await app.updater.stop()
            except Exception:
                pass
            try:
                if app.running:
                    await app.stop()
            except Exception:
                pass
            release_instance_lock()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Bot to'xtatildi.")
    except RuntimeError as e:
        if "Application is still running" in str(e):
            logger.info("Bot to'xtatildi.")
        else:
            raise





































































