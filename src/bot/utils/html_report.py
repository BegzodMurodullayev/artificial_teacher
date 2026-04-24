"""
HTML Report Generator — chiroyli hisobot fayllar yaratish.
Inline va private/group rejimlarda ishlaydi.
Hisobotlar INLINE_HTML_CHANNEL ga yuklanib, file_id qayta ishlatiladi.
"""

import logging
import html
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════
# HTML TEMPLATE
# ══════════════════════════════════════════════════════════

_BASE_STYLE = """
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
    min-height: 100vh;
    padding: 20px;
    color: #e0e0ff;
  }
  .card {
    background: rgba(255,255,255,0.07);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 18px;
    padding: 28px;
    max-width: 680px;
    margin: 0 auto;
    box-shadow: 0 8px 32px rgba(0,0,0,0.4);
  }
  .header {
    display: flex;
    align-items: center;
    gap: 14px;
    margin-bottom: 24px;
    padding-bottom: 18px;
    border-bottom: 1px solid rgba(255,255,255,0.12);
  }
  .header-icon { font-size: 2.4rem; }
  .header-title { font-size: 1.35rem; font-weight: 700; color: #fff; }
  .header-sub { font-size: 0.8rem; color: rgba(255,255,255,0.5); margin-top: 2px; }
  .badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 99px;
    font-size: 0.72rem;
    font-weight: 600;
    margin-left: 8px;
  }
  .badge-green  { background: rgba(52,211,153,0.2); color: #34d399; border: 1px solid rgba(52,211,153,0.35); }
  .badge-red    { background: rgba(248,113,113,0.2); color: #f87171; border: 1px solid rgba(248,113,113,0.35); }
  .badge-blue   { background: rgba(96,165,250,0.2);  color: #60a5fa; border: 1px solid rgba(96,165,250,0.35); }
  .badge-purple { background: rgba(167,139,250,0.2); color: #a78bfa; border: 1px solid rgba(167,139,250,0.35); }
  .badge-yellow { background: rgba(251,191,36,0.2);  color: #fbbf24; border: 1px solid rgba(251,191,36,0.35); }
  .section { margin-bottom: 20px; }
  .section-title {
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: rgba(255,255,255,0.45);
    margin-bottom: 12px;
  }
  .text-block {
    background: rgba(0,0,0,0.25);
    border-radius: 10px;
    padding: 14px 16px;
    font-size: 0.97rem;
    line-height: 1.6;
    color: #c7d2fe;
    word-break: break-word;
  }
  .corrected {
    background: rgba(52,211,153,0.1);
    border: 1px solid rgba(52,211,153,0.25);
    border-radius: 10px;
    padding: 14px 16px;
    font-size: 1rem;
    line-height: 1.6;
    color: #6ee7b7;
    font-weight: 500;
  }
  .error-item {
    background: rgba(255,255,255,0.04);
    border-left: 3px solid #f87171;
    border-radius: 0 10px 10px 0;
    padding: 10px 14px;
    margin-bottom: 10px;
  }
  .error-item:last-child { margin-bottom: 0; }
  .error-wrong { color: #f87171; text-decoration: line-through; font-size: 0.93rem; }
  .error-right { color: #34d399; font-weight: 600; font-size: 0.93rem; }
  .error-exp   { color: rgba(255,255,255,0.55); font-size: 0.82rem; margin-top: 4px; }
  .arrow { color: rgba(255,255,255,0.4); margin: 0 6px; }
  .stat-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 0;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    font-size: 0.92rem;
  }
  .stat-row:last-child { border-bottom: none; }
  .stat-label { color: rgba(255,255,255,0.55); }
  .stat-value { font-weight: 600; color: #e0e0ff; }
  .progress-bar {
    height: 8px;
    background: rgba(255,255,255,0.08);
    border-radius: 99px;
    overflow: hidden;
    margin-top: 8px;
  }
  .progress-fill {
    height: 100%;
    border-radius: 99px;
    background: linear-gradient(90deg, #7c3aed, #4f46e5, #06b6d4);
    transition: width 0.5s ease;
  }
  .footer {
    margin-top: 24px;
    padding-top: 16px;
    border-top: 1px solid rgba(255,255,255,0.08);
    text-align: center;
    font-size: 0.73rem;
    color: rgba(255,255,255,0.28);
  }
  .no-errors {
    text-align: center;
    padding: 20px;
    color: #34d399;
    font-size: 1.1rem;
    font-weight: 600;
  }
  .quiz-q {
    padding: 10px 0;
    border-bottom: 1px solid rgba(255,255,255,0.07);
    font-size: 0.9rem;
  }
  .quiz-q:last-child { border-bottom: none; }
  .quiz-correct { color: #34d399; }
  .quiz-wrong   { color: #f87171; }
  .pron-ipa {
    font-family: monospace;
    background: rgba(0,0,0,0.3);
    padding: 3px 8px;
    border-radius: 6px;
    font-size: 1rem;
    color: #c084fc;
  }
</style>
"""


def _h(text: str) -> str:
    """HTML escape."""
    return html.escape(str(text or ""))


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


# ══════════════════════════════════════════════════════════
# GRAMMAR CHECK REPORT
# ══════════════════════════════════════════════════════════

def build_check_report(
    original: str,
    corrected: str,
    analysis: list,
    summary: str = "",
    level: str = "",
    username: str = "",
) -> str:
    """Build HTML report for grammar check result."""
    has_errors = bool(analysis)
    error_count = len(analysis)
    status_badge = (
        f'<span class="badge badge-red">❌ {error_count} xato</span>'
        if has_errors
        else '<span class="badge badge-green">✅ Xato yo\'q</span>'
    )
    level_badge = f'<span class="badge badge-purple">🎯 {_h(level)}</span>' if level else ""
    user_line = f"👤 {_h(username)}" if username else "Artificial Teacher Bot"

    errors_html = ""
    if has_errors:
        errors_html = '<div class="section"><div class="section-title">🔍 Topilgan xatolar</div>'
        for err in analysis[:10]:
            e = _h(err.get("error", ""))
            c = _h(err.get("correction", ""))
            ex = _h(err.get("explanation", ""))
            errors_html += f"""
            <div class="error-item">
              <div><span class="error-wrong">{e}</span>
              <span class="arrow">→</span>
              <span class="error-right">{c}</span></div>
              {'<div class="error-exp">💡 ' + ex + '</div>' if ex else ''}
            </div>"""
        errors_html += "</div>"
    else:
        errors_html = '<div class="no-errors">✅ Matnda xato topilmadi! Ajoyib!</div>'

    corrected_section = ""
    if has_errors:
        corrected_section = f"""
        <div class="section">
          <div class="section-title">✏️ To'g'ri variant</div>
          <div class="corrected">{_h(corrected)}</div>
        </div>"""

    summary_html = ""
    if summary:
        summary_html = f"""
        <div class="section">
          <div class="section-title">📊 Xulosa</div>
          <div class="text-block">{_h(summary)}</div>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="uz">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Grammatika Tekshiruvi — Artificial Teacher</title>
{_BASE_STYLE}
</head>
<body>
<div class="card">
  <div class="header">
    <div class="header-icon">📝</div>
    <div>
      <div class="header-title">Grammatika Tekshiruvi {status_badge} {level_badge}</div>
      <div class="header-sub">{user_line} · {_now_str()}</div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">📋 Asl matn</div>
    <div class="text-block">{_h(original)}</div>
  </div>

  {errors_html}
  {corrected_section}
  {summary_html}

  <div class="footer">
    🤖 Artificial Teacher Bot · @Artificial_teacher_bot
  </div>
</div>
</body>
</html>"""


# ══════════════════════════════════════════════════════════
# QUIZ RESULT REPORT
# ══════════════════════════════════════════════════════════

def build_quiz_report(
    correct: int,
    total: int,
    accuracy: float,
    rating: str,
    history: list,
    level: str = "",
    level_changed: dict | None = None,
    qtype: str = "quiz",
    username: str = "",
) -> str:
    """Build HTML report for quiz result."""
    pct = int(accuracy)
    bar_color = (
        "linear-gradient(90deg,#34d399,#059669)" if pct >= 70
        else "linear-gradient(90deg,#fbbf24,#d97706)" if pct >= 40
        else "linear-gradient(90deg,#f87171,#dc2626)"
    )
    title = "🧩 IQ Test Natijasi" if qtype == "iq" else "🧠 Quiz Natijasi"
    user_line = f"👤 {_h(username)}" if username else "Artificial Teacher Bot"

    level_html = ""
    if level_changed and level_changed.get("changed"):
        level_html = f"""
        <div class="section">
          <div class="section-title">🎉 Daraja o'zgardi!</div>
          <div class="text-block" style="color:#fbbf24;font-weight:600;font-size:1.1rem;text-align:center;">
            {_h(level_changed['old'])} → {_h(level_changed['new'])}
          </div>
        </div>"""

    history_html = ""
    if history:
        history_html = '<div class="section"><div class="section-title">📋 Savollar tarixi</div>'
        for i, item in enumerate(history[:20], 1):
            q = _h(item.get("question", ""))
            ua = _h(item.get("user_answer", ""))
            ca = _h(item.get("correct_answer", ""))
            ok = item.get("is_correct", False)
            cls = "quiz-correct" if ok else "quiz-wrong"
            icon = "✅" if ok else "❌"
            history_html += f"""
            <div class="quiz-q">
              <div style="color:rgba(255,255,255,0.7);margin-bottom:4px;">{i}. {q}</div>
              <div class="{cls}">{icon} Siz: <b>{ua}</b> · To'g'ri: <b>{ca}</b></div>
            </div>"""
        history_html += "</div>"

    return f"""<!DOCTYPE html>
<html lang="uz">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — Artificial Teacher</title>
{_BASE_STYLE}
</head>
<body>
<div class="card">
  <div class="header">
    <div class="header-icon">{'🧩' if qtype == 'iq' else '🧠'}</div>
    <div>
      <div class="header-title">{title}</div>
      <div class="header-sub">{user_line} · {_now_str()}</div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">📊 Natija</div>
    <div class="stat-row">
      <span class="stat-label">✅ To'g'ri javoblar</span>
      <span class="stat-value">{correct} / {total}</span>
    </div>
    <div class="stat-row">
      <span class="stat-label">📈 Aniqlik</span>
      <span class="stat-value">{pct}%</span>
    </div>
    <div class="stat-row">
      <span class="stat-label">🏆 Baho</span>
      <span class="stat-value">{_h(rating)}</span>
    </div>
    {'<div class="stat-row"><span class="stat-label">🎯 Daraja</span><span class="stat-value">' + _h(level) + '</span></div>' if level else ''}
    <div class="progress-bar" style="margin-top:14px;">
      <div class="progress-fill" style="width:{pct}%;background:{bar_color};"></div>
    </div>
  </div>

  {level_html}
  {history_html}

  <div class="footer">
    🤖 Artificial Teacher Bot · @Artificial_teacher_bot
  </div>
</div>
</body>
</html>"""


# ══════════════════════════════════════════════════════════
# TRANSLATION REPORT
# ══════════════════════════════════════════════════════════

def build_translate_report(
    original: str,
    translation: str,
    direction: str = "uz_to_en",
    notes: str = "",
    username: str = "",
) -> str:
    """Build HTML report for translation result."""
    direction_map = {
        "uz_to_en": ("🇺🇿", "🇬🇧", "UZ → EN Tarjima"),
        "en_to_uz": ("🇬🇧", "🇺🇿", "EN → UZ Tarjima"),
        "ru_to_en": ("🇷🇺", "🇬🇧", "RU → EN Tarjima"),
        "en_to_ru": ("🇬🇧", "🇷🇺", "EN → RU Tarjima"),
    }
    f_flag, t_flag, title = direction_map.get(direction, ("📝", "📝", "Tarjima"))
    user_line = f"👤 {_h(username)}" if username else "Artificial Teacher Bot"
    notes_html = ""
    if notes:
        notes_html = f"""
        <div class="section">
          <div class="section-title">📌 Izohlar</div>
          <div class="text-block">{_h(notes)}</div>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="uz">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — Artificial Teacher</title>
{_BASE_STYLE}
</head>
<body>
<div class="card">
  <div class="header">
    <div class="header-icon">🌐</div>
    <div>
      <div class="header-title">{title}</div>
      <div class="header-sub">{user_line} · {_now_str()}</div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">{f_flag} Asl matn</div>
    <div class="text-block">{_h(original)}</div>
  </div>

  <div class="section">
    <div class="section-title">{t_flag} Tarjima</div>
    <div class="corrected">{_h(translation)}</div>
  </div>

  {notes_html}

  <div class="footer">
    🤖 Artificial Teacher Bot · @Artificial_teacher_bot
  </div>
</div>
</body>
</html>"""


# ══════════════════════════════════════════════════════════
# PRONUNCIATION REPORT
# ══════════════════════════════════════════════════════════

def build_pronunciation_report(
    word: str,
    ipa_us: str = "",
    ipa_uk: str = "",
    syllables: str = "",
    tips: list = None,
    examples: list = None,
    mistakes: list = None,
    username: str = "",
) -> str:
    """Build HTML report for pronunciation guide."""
    tips = tips or []
    examples = examples or []
    mistakes = mistakes or []
    user_line = f"👤 {_h(username)}" if username else "Artificial Teacher Bot"

    tips_html = ""
    if tips:
        tips_html = '<div class="section"><div class="section-title">💡 Maslahatlar</div>'
        for tip in tips[:5]:
            tips_html += f'<div class="quiz-q" style="border-left:3px solid #a78bfa;padding-left:10px;">{_h(tip)}</div>'
        tips_html += "</div>"

    examples_html = ""
    if examples:
        examples_html = '<div class="section"><div class="section-title">📋 Misollar</div>'
        for ex in examples[:3]:
            examples_html += f'<div class="quiz-q"><i style="color:#c7d2fe;">{_h(ex)}</i></div>'
        examples_html += "</div>"

    mistakes_html = ""
    if mistakes:
        mistakes_html = '<div class="section"><div class="section-title">⚠️ Keng tarqalgan xatolar</div>'
        for m in mistakes[:3]:
            mistakes_html += f'<div class="quiz-q" style="color:#f87171;">{_h(m)}</div>'
        mistakes_html += "</div>"

    return f"""<!DOCTYPE html>
<html lang="uz">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Talaffuz — {_h(word)} — Artificial Teacher</title>
{_BASE_STYLE}
</head>
<body>
<div class="card">
  <div class="header">
    <div class="header-icon">🔊</div>
    <div>
      <div class="header-title">Talaffuz Qo'llanmasi</div>
      <div class="header-sub">{user_line} · {_now_str()}</div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">📝 So'z</div>
    <div class="text-block" style="font-size:1.4rem;font-weight:700;color:#fff;">{_h(word)}</div>
  </div>

  <div class="section">
    <div class="section-title">🔤 IPA Transkripsiya</div>
    {'<div class="stat-row"><span class="stat-label">🇺🇸 US</span><span class="pron-ipa">' + _h(ipa_us) + '</span></div>' if ipa_us else ''}
    {'<div class="stat-row"><span class="stat-label">🇬🇧 UK</span><span class="pron-ipa">' + _h(ipa_uk) + '</span></div>' if ipa_uk else ''}
    {'<div class="stat-row"><span class="stat-label">📊 Bo\'g\'inlar</span><span class="pron-ipa">' + _h(syllables) + '</span></div>' if syllables else ''}
  </div>

  {tips_html}
  {examples_html}
  {mistakes_html}

  <div class="footer">
    🤖 Artificial Teacher Bot · @Artificial_teacher_bot
  </div>
</div>
</body>
</html>"""


# ══════════════════════════════════════════════════════════
# SEND TO CHANNEL & GET FILE_ID
# ══════════════════════════════════════════════════════════

async def send_html_to_channel(
    bot,
    html_content: str,
    filename: str,
    channel_id,
    caption: str = "📄 HTML Hisobot",
) -> Optional[str]:
    """
    Send HTML file to channel, return file_id.
    Returns None if channel not configured or send fails.
    """
    if not channel_id or channel_id in (0, "0", ""):
        return None

    try:
        from aiogram.types import BufferedInputFile
        file_bytes = html_content.encode("utf-8")
        doc = BufferedInputFile(file_bytes, filename=filename)
        msg = await bot.send_document(
            chat_id=channel_id,
            document=doc,
            caption=caption,
        )
        if msg and msg.document:
            return msg.document.file_id
    except Exception as e:
        logger.warning("send_html_to_channel failed: %s", e)
    return None


async def send_audio_to_channel(
    bot,
    audio_bytes: bytes,
    filename: str,
    channel_id,
    caption: str = "🔊 Audio",
) -> Optional[str]:
    """
    Send audio file to channel, return file_id.
    Returns None if channel not configured or send fails.
    """
    if not channel_id or channel_id in (0, "0", ""):
        return None

    try:
        from aiogram.types import BufferedInputFile
        doc = BufferedInputFile(audio_bytes, filename=filename)
        msg = await bot.send_voice(
            chat_id=channel_id,
            voice=doc,
            caption=caption,
        )
        if msg and msg.voice:
            return msg.voice.file_id
    except Exception as e:
        logger.warning("send_audio_to_channel failed: %s", e)
    return None


def build_admin_stats_report(
    summary: dict,
    growth: list[dict],
    top_users: list[dict],
    generated_by: str = "",
) -> str:
    """Build HTML report for admin dashboard snapshot."""
    user_line = f"ðŸ‘¤ {_h(generated_by)}" if generated_by else "Artificial Teacher Admin"

    growth_html = ""
    if growth:
        growth_html = '<div class="section"><div class="section-title">ðŸ“ˆ Oxirgi 7 kunlik user qo\'shilishi</div>'
        peak = max((int(item.get("count", 0)) for item in growth), default=1) or 1
        for item in growth:
            day = _h(item.get("day", ""))
            count = int(item.get("count", 0))
            pct = int((count / peak) * 100) if peak else 0
            growth_html += f"""
            <div class="stat-row">
              <span class="stat-label">{day}</span>
              <span class="stat-value">{count}</span>
            </div>
            <div class="progress-bar" style="margin:6px 0 10px 0;">
              <div class="progress-fill" style="width:{pct}%"></div>
            </div>
            """
        growth_html += "</div>"

    top_users_html = ""
    if top_users:
        top_users_html = '<div class="section"><div class="section-title">ðŸ† Top faol userlar</div>'
        for index, item in enumerate(top_users[:20], 1):
            name = _h(item.get("name", "-"))
            uid = _h(item.get("user_id", ""))
            xp = int(item.get("xp", 0) or 0)
            checks = int(item.get("checks_total", 0) or 0)
            quiz = int(item.get("quiz_played", 0) or 0)
            top_users_html += f"""
            <div class="quiz-q">
              <div><b>{index}.</b> {name} <span style="color:rgba(255,255,255,0.5)">#{uid}</span></div>
              <div style="color:rgba(255,255,255,0.65);font-size:0.82rem;">
                XP: <b>{xp}</b> Â· Checks: <b>{checks}</b> Â· Quiz: <b>{quiz}</b>
              </div>
            </div>
            """
        top_users_html += "</div>"

    return f"""<!DOCTYPE html>
<html lang="uz">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Admin Statistika â€” Artificial Teacher</title>
{_BASE_STYLE}
</head>
<body>
<div class="card">
  <div class="header">
    <div class="header-icon">ðŸ›¡</div>
    <div>
      <div class="header-title">Admin Statistika Snapshot</div>
      <div class="header-sub">{user_line} Â· {_now_str()}</div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">ðŸ“Š Umumiy ko'rsatkichlar</div>
    <div class="stat-row"><span class="stat-label">Jami userlar</span><span class="stat-value">{int(summary.get("total_users", 0))}</span></div>
    <div class="stat-row"><span class="stat-label">Pulli userlar</span><span class="stat-value">{int(summary.get("paid_users", 0))}</span></div>
    <div class="stat-row"><span class="stat-label">Konversiya</span><span class="stat-value">{_h(summary.get("conversion", "0%"))}</span></div>
    <div class="stat-row"><span class="stat-label">Kutilayotgan to'lovlar</span><span class="stat-value">{int(summary.get("pending_payments", 0))}</span></div>
    <div class="stat-row"><span class="stat-label">Jami tushum</span><span class="stat-value">{_h(summary.get("revenue", "0"))}</span></div>
  </div>

  {growth_html}
  {top_users_html}

  <div class="footer">
    ðŸ¤– Artificial Teacher Bot Â· @Artificial_teacher_bot
  </div>
</div>
</body>
</html>"""


def build_admin_user_report(
    user: dict,
    stats: dict,
    plan_name: str,
    remaining_days: int,
    usage_today: dict | None = None,
    generated_by: str = "",
) -> str:
    """Build HTML report for a single user profile in admin panel."""
    usage_today = usage_today or {}
    user_line = f"ðŸ‘¤ {_h(generated_by)}" if generated_by else "Artificial Teacher Admin"

    name = _h(user.get("first_name") or "-")
    username = _h(user.get("username") or "-")
    uid = _h(user.get("user_id") or "-")
    role = _h(user.get("role") or "user")
    level = _h(user.get("level") or "A1")
    joined = _h(str(user.get("joined_at", ""))[:19] or "-")
    status = "BAN" if user.get("is_banned") else "ACTIVE"

    return f"""<!DOCTYPE html>
<html lang="uz">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>User Hisoboti â€” #{uid}</title>
{_BASE_STYLE}
</head>
<body>
<div class="card">
  <div class="header">
    <div class="header-icon">ðŸ‘¤</div>
    <div>
      <div class="header-title">Foydalanuvchi Hisoboti <span class="badge {'badge-red' if status == 'BAN' else 'badge-green'}">{status}</span></div>
      <div class="header-sub">{user_line} Â· {_now_str()}</div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">Asosiy ma'lumotlar</div>
    <div class="stat-row"><span class="stat-label">User ID</span><span class="stat-value">#{uid}</span></div>
    <div class="stat-row"><span class="stat-label">Ism</span><span class="stat-value">{name}</span></div>
    <div class="stat-row"><span class="stat-label">Username</span><span class="stat-value">@{username}</span></div>
    <div class="stat-row"><span class="stat-label">Role</span><span class="stat-value">{role}</span></div>
    <div class="stat-row"><span class="stat-label">Daraja</span><span class="stat-value">{level}</span></div>
    <div class="stat-row"><span class="stat-label">Qo'shilgan</span><span class="stat-value">{joined}</span></div>
  </div>

  <div class="section">
    <div class="section-title">Obuna</div>
    <div class="stat-row"><span class="stat-label">Reja</span><span class="stat-value">{_h(plan_name)}</span></div>
    <div class="stat-row"><span class="stat-label">Qolgan kun</span><span class="stat-value">{remaining_days}</span></div>
  </div>

  <div class="section">
    <div class="section-title">Umumiy faollik</div>
    <div class="stat-row"><span class="stat-label">Checks</span><span class="stat-value">{int(stats.get("checks_total", 0))}</span></div>
    <div class="stat-row"><span class="stat-label">Translations</span><span class="stat-value">{int(stats.get("translations_total", 0))}</span></div>
    <div class="stat-row"><span class="stat-label">Pronunciation</span><span class="stat-value">{int(stats.get("pron_total", 0))}</span></div>
    <div class="stat-row"><span class="stat-label">Messages</span><span class="stat-value">{int(stats.get("messages_total", 0))}</span></div>
    <div class="stat-row"><span class="stat-label">Voice</span><span class="stat-value">{int(stats.get("voice_total", 0))}</span></div>
    <div class="stat-row"><span class="stat-label">Quiz played</span><span class="stat-value">{int(stats.get("quiz_played", 0))}</span></div>
    <div class="stat-row"><span class="stat-label">Quiz correct</span><span class="stat-value">{int(stats.get("quiz_correct", 0))}</span></div>
    <div class="stat-row"><span class="stat-label">Streak</span><span class="stat-value">{int(stats.get("streak_days", 0))} kun</span></div>
  </div>

  <div class="section">
    <div class="section-title">Bugungi limitlardan foydalanish</div>
    <div class="stat-row"><span class="stat-label">Checks</span><span class="stat-value">{int(usage_today.get("checks", 0))}</span></div>
    <div class="stat-row"><span class="stat-label">Quiz</span><span class="stat-value">{int(usage_today.get("quiz", 0))}</span></div>
    <div class="stat-row"><span class="stat-label">Lessons</span><span class="stat-value">{int(usage_today.get("lessons", 0))}</span></div>
    <div class="stat-row"><span class="stat-label">AI messages</span><span class="stat-value">{int(usage_today.get("ai_messages", 0))}</span></div>
    <div class="stat-row"><span class="stat-label">Pron audio</span><span class="stat-value">{int(usage_today.get("pron_audio", 0))}</span></div>
  </div>

  <div class="footer">
    ðŸ¤– Artificial Teacher Bot Â· @Artificial_teacher_bot
  </div>
</div>
</body>
</html>"""
