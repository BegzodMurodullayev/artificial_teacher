"""
Inline query handler — supports @bot check: / tr: / p: / bot: queries.

Usage in any chat:
  @bot check: I goes to school yesterday
  @bot tr: Salom, qalaysiz?
  @bot p: us: pronunciation
  @bot bot: What is the difference between "since" and "for"?
"""

import hashlib
import logging

from aiogram import Router, F
from aiogram.types import (
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
    CallbackQuery,
)

from src.services import ai_service
from src.bot.utils.telegram import escape_html

logger = logging.getLogger(__name__)
router = Router(name="inline")

MAX_INLINE_TEXT = 255  # Telegram limit for inline result title


def _short(text: str, n: int = MAX_INLINE_TEXT) -> str:
    """Truncate text for inline result titles."""
    return text[:n] + ("…" if len(text) > n else "")


def _uid(text: str) -> str:
    """Generate a deterministic short ID."""
    return hashlib.md5(text.encode()).hexdigest()[:12]


# ══════════════════════════════════════════════════════════
# MAIN HANDLER
# ══════════════════════════════════════════════════════════

@router.inline_query()
async def handle_inline_query(inline_query: InlineQuery):
    """
    Route inline queries based on prefix:
      check: <text>   → Grammar correction
      tr: <text>      → UZ→EN or EN→UZ translation
      p: [us:|uk:] <word>  → Pronunciation guide
      bot: <text>     → AI conversation
      (empty or unknown) → Show help cards
    """
    raw = (inline_query.query or "").strip()
    user_id = inline_query.from_user.id
    results = []

    # ── Empty query → show help ──
    if not raw:
        results = _help_cards()
        await inline_query.answer(results, cache_time=60, is_personal=False)
        return

    # ── Route by prefix ──
    lower = raw.lower()

    if lower.startswith("check:"):
        text = raw[6:].strip()
        results = await _inline_check(text, user_id)

    elif lower.startswith("tr:"):
        text = raw[3:].strip()
        results = await _inline_translate(text, user_id)

    elif lower.startswith("p:"):
        text = raw[2:].strip()
        accent = "us"
        if text.lower().startswith("us:"):
            accent = "us"
            text = text[3:].strip()
        elif text.lower().startswith("uk:"):
            accent = "uk"
            text = text[3:].strip()
        results = await _inline_pronunciation(text, accent, user_id)

    elif lower.startswith("bot:"):
        text = raw[4:].strip()
        results = await _inline_bot(text, user_id)

    elif lower.startswith("word:"):
        text = raw[5:].strip()
        results = await _inline_word(text, user_id)

    elif lower.startswith("quiz:"):
        text = raw[5:].strip()
        results = await _inline_quiz(text, user_id)

    else:
        # Treat as grammar check by default
        results = await _inline_check(raw, user_id)

    if not results:
        results = [_error_card("❌ Natija topilmadi. Qayta urinib ko'ring.")]

    await inline_query.answer(results, cache_time=30, is_personal=True)


# ══════════════════════════════════════════════════════════
# CHECK
# ══════════════════════════════════════════════════════════

async def _inline_check(text: str, user_id: int) -> list:
    if not text or len(text) < 2:
        return [_error_card("✏️ Kamida 2 ta harf kiriting: check: I goes to school")]

    result = await ai_service.ask_json(text, mode="check", user_id=user_id)
    if not result:
        return [_error_card("❌ AI javob bermadi. Qayta urinib ko'ring.")]

    corrected = escape_html(result.get("corrected", text))
    original = escape_html(result.get("original", text))
    summary = escape_html(result.get("summary", ""))
    analysis = result.get("analysis", [])
    level = result.get("level", "")

    # Build message
    lines = [f"✅ <b>Grammatika tekshiruvi</b>\n"]

    if analysis:
        lines.append(f"📝 <b>Asl matn:</b> <i>{original}</i>")
        lines.append(f"✏️ <b>To'g'ri variant:</b> <b>{corrected}</b>\n")
        lines.append(f"🔍 <b>Xatolar ({len(analysis)}):</b>")
        for err in analysis[:5]:
            e = escape_html(err.get("error", ""))
            c = escape_html(err.get("correction", ""))
            ex = escape_html(err.get("explanation", ""))
            lines.append(f"  • ❌ <s>{e}</s> → ✅ <b>{c}</b>\n    💡 {ex}")
    else:
        lines.append(f"📝 <i>{original}</i>")
        lines.append("✅ <b>Xato topilmadi!</b>")

    if summary:
        lines.append(f"\n📊 {summary}")
    if level:
        lines.append(f"🎯 Daraja: <b>{level}</b>")

    message = "\n".join(lines)
    title = f"✅ {_short(corrected or text, 60)}"
    desc = summary or "Grammatika natijasi"

    return [InlineQueryResultArticle(
        id=_uid(f"check:{text}"),
        title=title,
        description=_short(desc, 80),
        input_message_content=InputTextMessageContent(
            message_text=message,
            parse_mode="HTML",
        ),
        thumbnail_url="https://img.icons8.com/fluency/48/checkmark.png",
    )]


# ══════════════════════════════════════════════════════════
# TRANSLATE
# ══════════════════════════════════════════════════════════

async def _inline_translate(text: str, user_id: int) -> list:
    if not text or len(text) < 2:
        return [_error_card("🌐 Tarjima qilish uchun matn kiriting: tr: Salom")]

    import re
    is_latin = bool(re.search(r'[a-zA-Z]', text))
    is_cyrillic = bool(re.search(r'[а-яА-Я]', text))
    direction = "en_to_uz" if is_latin and not is_cyrillic else "uz_to_en"
    mode = f"translate_{direction}"  # → translate_uz_to_en or translate_en_to_uz

    result = await ai_service.ask_json(text, mode=mode, user_id=user_id)
    if not result:
        return [_error_card("❌ Tarjima bajarilmadi.")]

    original = escape_html(result.get("original", text))
    translation = escape_html(result.get("translation", ""))
    notes = escape_html(result.get("notes", ""))

    if direction == "uz_to_en":
        flag_from, flag_to = "🇺🇿", "🇬🇧"
        header = "UZ → EN Tarjima"
    else:
        flag_from, flag_to = "🇬🇧", "🇺🇿"
        header = "EN → UZ Tarjima"

    lines = [
        f"🌐 <b>{header}</b>\n",
        f"{flag_from} <i>{original}</i>",
        f"{flag_to} <b>{translation}</b>",
    ]
    if notes:
        lines.append(f"\n📌 <i>{notes}</i>")

    return [InlineQueryResultArticle(
        id=_uid(f"tr:{text}"),
        title=f"🌐 {_short(translation, 60)}",
        description=f"{flag_from} {_short(original, 60)}",
        input_message_content=InputTextMessageContent(
            message_text="\n".join(lines),
            parse_mode="HTML",
        ),
        thumbnail_url="https://img.icons8.com/fluency/48/translate.png",
    )]


# ══════════════════════════════════════════════════════════
# PRONUNCIATION
# ══════════════════════════════════════════════════════════

async def _inline_pronunciation(text: str, accent: str, user_id: int) -> list:
    if not text:
        return [_error_card("🔊 So'z kiriting: p: hello yoki p: us: pronunciation")]

    result = await ai_service.ask_json(text, mode="pronunciation", user_id=user_id)
    if not result:
        return [_error_card("❌ Talaffuz ma'lumoti olinmadi.")]

    word = escape_html(result.get("word", text))
    ipa_us = escape_html(result.get("ipa_us", ""))
    ipa_uk = escape_html(result.get("ipa_uk", ""))
    syllables = escape_html(result.get("syllables", ""))
    tips = result.get("tips", [])
    examples = result.get("example_sentences", [])

    lines = [f"🔊 <b>Talaffuz qo'llanmasi</b>\n", f"📝 So'z: <b>{word}</b>"]
    if ipa_us:
        lines.append(f"🇺🇸 US: <code>{ipa_us}</code>")
    if ipa_uk:
        lines.append(f"🇬🇧 UK: <code>{ipa_uk}</code>")
    if syllables:
        lines.append(f"📊 Bo'g'inlar: <code>{syllables}</code>")
    if tips:
        lines.append("\n💡 <b>Maslahatlar:</b>")
        for tip in tips[:3]:
            lines.append(f"  • {escape_html(tip)}")
    if examples:
        lines.append("\n📋 <b>Misollar:</b>")
        for ex in examples[:2]:
            lines.append(f"  • <i>{escape_html(ex)}</i>")

    return [InlineQueryResultArticle(
        id=_uid(f"p:{text}:{accent}"),
        title=f"🔊 {word}  {ipa_us or ipa_uk}",
        description=f"Talaffuz ({accent.upper()}) | {syllables}",
        input_message_content=InputTextMessageContent(
            message_text="\n".join(lines),
            parse_mode="HTML",
        ),
        thumbnail_url="https://img.icons8.com/fluency/48/speaker.png",
    )]


# ══════════════════════════════════════════════════════════
# BOT CHAT
# ══════════════════════════════════════════════════════════

async def _inline_bot(text: str, user_id: int) -> list:
    if not text:
        return [_error_card("🤖 Savol yozing: bot: What is present perfect?")]

    response = await ai_service.ask_ai(text, mode="bot", user_id=user_id)
    if not response:
        return [_error_card("❌ AI javob bermadi.")]

    return [InlineQueryResultArticle(
        id=_uid(f"bot:{text}"),
        title=f"🤖 {_short(text, 60)}",
        description=_short(response, 100),
        input_message_content=InputTextMessageContent(
            message_text=f"🤖 <b>AI O'qituvchi</b>\n\n"
                         f"❓ <i>{escape_html(text)}</i>\n\n"
                         f"{escape_html(response)}",
            parse_mode="HTML",
        ),
        thumbnail_url="https://img.icons8.com/fluency/48/bot.png",
    )]


# ══════════════════════════════════════════════════════════
# WORD CARD
# ══════════════════════════════════════════════════════════

async def _inline_word(text: str, user_id: int) -> list:
    if not text:
        return [_error_card("🔤 So'z kiriting: word: serendipity")]

    result = await ai_service.ask_json(text, mode="word_card", user_id=user_id)
    if not result:
        return [_error_card("❌ So'z ma'lumoti olinmadi.")]

    word = escape_html(result.get("word", text))
    translation = escape_html(result.get("translation", ""))
    ipa = escape_html(result.get("ipa", ""))
    pos = escape_html(result.get("part_of_speech", ""))
    definition = escape_html(result.get("definition", ""))
    example = escape_html(result.get("example", ""))
    example_translation = escape_html(result.get("example_translation", ""))

    lines = [
        f"🇺🇸 <b>{word.capitalize()}</b> <code>[{ipa}]</code> - <i>{pos}</i>",
        f"🇺🇿 <b>{translation}</b>",
        "",
        f"📖 <b>Ma'nosi:</b> {definition}",
        "",
        f"🗣 <b>Misol:</b> <i>{example}</i>",
        f"💡 <b>Tarjimasi:</b> <i>{example_translation}</i>"
    ]

    return [InlineQueryResultArticle(
        id=_uid(f"word:{text}"),
        title=f"🔤 {word.capitalize()} — {translation}",
        description=definition,
        input_message_content=InputTextMessageContent(
            message_text="\n".join(lines),
            parse_mode="HTML",
        ),
        thumbnail_url="https://img.icons8.com/fluency/48/dictionary.png",
    )]


# ══════════════════════════════════════════════════════════
# QUIZ SHARE
# ══════════════════════════════════════════════════════════

async def _inline_quiz(text: str, user_id: int) -> list:
    topic = text if text else "random general english"
    
    result = await ai_service.ask_json(topic, mode="quiz_generate", user_id=user_id)
    if not result:
        return [_error_card("❌ Quiz yaratilmadi.")]

    question = escape_html(result.get("question", ""))
    options = result.get("options", {})
    answer = result.get("answer", "A")

    lines = [
        f"🎯 <b>Tezkor Quiz</b>",
        f"<i>Mavzu: {escape_html(topic).title()}</i>",
        "",
        f"❓ <b>{question}</b>",
    ]
    
    for k, v in options.items():
        lines.append(f"<b>{k})</b> {escape_html(v)}")

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    # Create simple callback buttons: "inl_q:<correct_ans>:<selected_ans>"
    # Ex: inl_q:A:A
    buttons = []
    for k in options.keys():
        buttons.append(InlineKeyboardButton(text=k, callback_data=f"inl_q:{answer}:{k}"))
        
    kb = InlineKeyboardMarkup(inline_keyboard=[buttons])

    return [InlineQueryResultArticle(
        id=_uid(f"quiz:{topic}:{question}"),
        title=f"🎯 Quiz ulashish: {topic.capitalize()}",
        description=question,
        reply_markup=kb,
        input_message_content=InputTextMessageContent(
            message_text="\n".join(lines),
            parse_mode="HTML",
        ),
        thumbnail_url="https://img.icons8.com/fluency/48/quiz.png",
    )]


# ══════════════════════════════════════════════════════════
# HELP CARDS (empty query)
# ══════════════════════════════════════════════════════════

def _help_cards() -> list:
    cards = [
        ("✅ Grammatika tekshiruv", "check: I goes to school", "check: matn yozing",
         "check: I goes to school yesterday",
         "https://img.icons8.com/fluency/48/checkmark.png"),
        ("🌐 Tarjima", "tr: matn yozing", "UZ→EN va EN→UZ avtomatik",
         "tr: Salom, qalaysiz?",
         "https://img.icons8.com/fluency/48/translate.png"),
        ("🔊 Talaffuz", "p: so'z yozing", "IPA transkripsiya + misollar",
         "p: pronunciation | p: uk: schedule",
         "https://img.icons8.com/fluency/48/speaker.png"),
        ("🤖 AI Suhbat", "bot: savol yozing", "Ingliz tili bo'yicha savol bering",
         "bot: What is the difference between since and for?",
         "https://img.icons8.com/fluency/48/bot.png"),
        ("🔤 So'z kartochkasi", "word: so'z", "Chiroyli so'z yodlash kartochkasi",
         "word: serendipity",
         "https://img.icons8.com/fluency/48/dictionary.png"),
        ("🎯 Quiz ulashish", "quiz: mavzu", "Guruhlarga tezkor test yuborish",
         "quiz: present perfect",
         "https://img.icons8.com/fluency/48/quiz.png"),
    ]
    results = []
    for i, (title, desc, tip, example, thumb) in enumerate(cards):
        results.append(InlineQueryResultArticle(
            id=f"help_{i}",
            title=title,
            description=f"{desc} | {tip}",
            input_message_content=InputTextMessageContent(
                message_text=(
                    f"<b>{title}</b>\n\n"
                    f"📌 Ishlatish:\n<code>@Artificial_teacher_bot {example}</code>\n\n"
                    f"💡 {tip}"
                ),
                parse_mode="HTML",
            ),
            thumbnail_url=thumb,
        ))
    return results

def _error_card(msg: str) -> InlineQueryResultArticle:
    return InlineQueryResultArticle(
        id=_uid(msg),
        title="⚠️ Xato",
        description=msg,
        input_message_content=InputTextMessageContent(
            message_text=msg,
        ),
    )

# ══════════════════════════════════════════════════════════
# INLINE CALLBACK HANDLERS
# ══════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("inl_q:"))
async def handle_inline_quiz_callback(callback: CallbackQuery):
    """Handle answer button clicks from inline quizzes."""
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Xato ma'lumot.", show_alert=True)
        return
        
    correct_ans = parts[1]
    selected_ans = parts[2]
    
    if selected_ans == correct_ans:
        await callback.answer("✅ To'g'ri javob topdingiz! Barakalla!", show_alert=True)
    else:
        await callback.answer(f"❌ Noto'g'ri.\nTo'g'ri javob: {correct_ans}", show_alert=True)
