import asyncio
"""handlers/admin.py - Admin and owner panel."""
import io
import os
import re
import html as pyhtml
import tempfile
from pathlib import Path
from urllib.parse import urlencode
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from telegram.error import BadRequest
from telegram.ext import ContextTypes
from html_maker import render_html_document, html_open_guide
from database.db import (
    get_user,
    set_role,
    ban_user,
    get_all_users,
    find_user_by_username,
    iter_broadcast_user_ids,
    get_users_with_active_plans,
    iter_users_with_active_plans,
    get_global_stats,
    get_sales_funnel_stats,
    get_pending_payments,
    has_pending_payment,
    approve_payment,
    reject_payment,
    get_all_pay_config,
    set_pay_config,
    get_all_plans,
    update_plan,
    set_subscription,
    get_active_subscription,
    get_payment,
    get_group,
    set_group,
    get_sponsor_channels,
    add_sponsor_channel,
    remove_sponsor_channel,
    get_all_reward_settings,
    set_reward_setting,
    get_promo_packs,
    add_promo_pack,
    remove_promo_pack,
    add_promo_code,
    get_user_plan,
    get_leaderboard,
    get_user_rank_snapshot,
)


OWNER_ID = int(os.getenv("OWNER_ID", "0"))
WEB_APP_URL = os.getenv("WEB_APP_URL", "").strip()
PLAN_ICONS = {"free": "\U0001F193", "standard": "\u2B50", "pro": "\U0001F48E", "premium": "\U0001F451"}
BROADCAST_CHUNK_SIZE = max(1, int(os.getenv("BROADCAST_CHUNK_SIZE", "20")))
BROADCAST_PAUSE_SEC = float(os.getenv("BROADCAST_PAUSE_SEC", "0.25"))


def escape_md(text: str) -> str:
    if text is None:
        return ""
    return re.sub(r"([_*\[\]()~`>#+=|{}.!-])", r"\\\1", str(text))


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
            await query.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception:
        pass


async def safe_send(context, chat_id, text, reply_markup=None, parse_mode=None):
    try:
        await context.bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)
        return
    except BadRequest:
        pass
    try:
        await context.bot.send_message(chat_id, text, reply_markup=reply_markup)
    except Exception:
        pass


async def _broadcast_text_one(context, user_id, text):
    try:
        await context.bot.send_message(user_id, text, parse_mode="Markdown")
        return True
    except BadRequest:
        try:
            await context.bot.send_message(user_id, text)
            return True
        except Exception:
            return False
    except Exception:
        return False


async def _broadcast_copy_one(context, chat_id, from_chat_id, message_id):
    try:
        await context.bot.copy_message(chat_id=chat_id, from_chat_id=from_chat_id, message_id=message_id)
        return True
    except Exception:
        return False


async def _broadcast_in_chunks(items, worker):
    success, fail = 0, 0
    for idx in range(0, len(items), BROADCAST_CHUNK_SIZE):
        batch = items[idx:idx + BROADCAST_CHUNK_SIZE]
        results = await asyncio.gather(*(worker(item) for item in batch), return_exceptions=True)
        for result in results:
            if result is True:
                success += 1
            else:
                fail += 1
        if idx + BROADCAST_CHUNK_SIZE < len(items):
            await asyncio.sleep(BROADCAST_PAUSE_SEC)
    return success, fail


async def _broadcast_user_id_batches(worker):
    success, fail = 0, 0
    for batch in iter_broadcast_user_ids(BROADCAST_CHUNK_SIZE):
        results = await asyncio.gather(*(worker(user_id) for user_id in batch), return_exceptions=True)
        for result in results:
            if result is True:
                success += 1
            else:
                fail += 1
        if len(batch) >= BROADCAST_CHUNK_SIZE:
            await asyncio.sleep(BROADCAST_PAUSE_SEC)
    return success, fail


def is_owner(user_id):
    return user_id == OWNER_ID


def is_admin(user):
    return user and (user.get("role") in ("admin", "owner") or user.get("user_id") == OWNER_ID)


def normalize_admin_text(text: str) -> str:
    cleaned = re.sub(r"^[^A-Za-z0-9'`]+", "", (text or "").strip()).lower()
    aliases = {
        "admin": "admin panel",
        "boshqaruv": "admin panel",
        "orqaga": "admin panel",
        "payments": "to'lovlar",
        "users": "userlar",
        "foydalanuvchilar": "userlar",
        "analytics": "analitika",
        "analitika": "analitika",
        "stats": "statistika",
        "global statistika": "statistika",
        "export": "export",
        "user eksport": "export users",
        "foydalanuvchilar eksporti": "export users",
        "foydalanuvchi eksporti": "export users",
        "html hisobot": "html hisobotlar",
        "html hisobotlar": "html hisobotlar",
        "sotuv funnel": "funnel",
        "konversiya": "funnel",
        "plans": "rejalar",
        "sponsors": "homiy kanallar",
        "ads": "reklama",
        "owner": "adminlar",
        "back": "admin panel",
    }
    return aliases.get(cleaned, cleaned)
def is_owner_only_callback(data: str) -> bool:
    owner_only_exact = {
        "adm_pay_config",
        "adm_admins",
        "adm_marketing",
        "adm_pack_add",
        "adm_code_add",
        "adm_cancel_admin",
    }
    owner_only_prefixes = (
        "paycfg_",
        "adm_reward_",
        "adm_pack_del_",
        "adm_confirm_admin_",
    )
    return data in owner_only_exact or any(data.startswith(prefix) for prefix in owner_only_prefixes)


def admin_reply_kb(user_id: int):
    rows = [
        ["📊 Dashboard", "💳 To'lovlar", "👥 Userlar"],
        ["📊 Statistika", "📈 Funnel", "📄 HTML hisobotlar"],
        ["🏆 Reyting", "📄 User eksport", "📢 Homiy kanallar"],
        ["📦 Rejalar", "📣 Reklama"],
    ]
    if is_owner(user_id):
        rows.append(["⚙️ To'lov sozlamalari", "🎁 Marketing", "👮 Adminlar"])
    rows.append(["👤 User panel"])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, input_field_placeholder="Admin bo'limini tanlang...")


def _build_html_reports_markup(back_callback: str = "adm_back"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Global statistika HTML", callback_data="adm_stats_html")],
        [InlineKeyboardButton("📈 Sotuv funnel HTML", callback_data="adm_funnel_html")],
        [InlineKeyboardButton("📄 User eksport HTML", callback_data="adm_export_users")],
        [InlineKeyboardButton("🔙 Orqaga", callback_data=back_callback)],
    ])
def _build_web_app_url(user_id: int) -> str | None:
    if not WEB_APP_URL:
        return None
    try:
        plan_name = get_user_plan(user_id).get("plan_name", "free")
        rank = get_user_rank_snapshot(user_id) or {}
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


def user_reply_kb(user_id: int):
    rows = [
        ["\u2705 Tekshiruv", "\U0001F501 Tarjima", "\U0001F50A Talaffuz"],
        ["\U0001F3AF Quiz", "\U0001F9E0 IQ test", "\U0001F4DA Dars"],
        ["\U0001F4D6 Grammatika", "\U0001F4C5 Kunlik so'z", "\U0001F4C8 Darajam / Reyting"],
        ["\U0001F381 Bonuslar", "\U0001F4B3 Tariflar", "\u2139\ufe0f Aloqa"],
    ]
    web_url = _build_web_app_url(user_id)
    if web_url:
        rows.append([KeyboardButton("\U0001F4F1 Web App", web_app=WebAppInfo(url=web_url))])
    else:
        rows.append(["\U0001F4F1 Web App"])
    if is_admin(get_user(user_id)):
        rows.append(["\U0001F6E1 Admin panel"])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, input_field_placeholder="Bo'limni tanlang...")


def build_admin_summary_text():
    gs = get_global_stats()
    funnel = get_sales_funnel_stats()
    approved_amount = int(funnel.get("approved_amount_30d", 0) or 0)
    return (
        "🛡️ *Admin dashboard*\n\n"
        f"👥 Foydalanuvchilar: *{gs['total_users']}*\n"
        f"💎 Pullik userlar: *{gs['paid_users']}*\n"
        f"🆓 Free userlar: *{gs.get('free_users', 0)}*\n"
        f"🎯 Konversiya: *{gs.get('conversion_rate', 0)}%*\n"
        f"⏳ Kutayotgan to'lovlar: *{gs['pending_payments']}*\n"
        f"✅ Tekshiruvlar: *{gs['total_checks']}*\n"
        f"🧠 Quiz savollar: *{gs['total_quiz']}*\n"
        f"💰 30 kunlik tushum: *{approved_amount:,} UZS*\n\n"
        "Keyboarddan kerakli bo'limni tanlang."
    )


def _payment_mode(cfg: dict) -> str:
    mode = str(cfg.get("payment_mode") or cfg.get("payment_method") or "manual").strip().lower()
    return mode if mode in {"manual", "hybrid", "auto"} else "manual"


def _mask_secret(value: str, keep: int = 4) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "yo'q"
    if len(raw) <= keep:
        return "*" * len(raw)
    return f"{'*' * max(4, len(raw) - keep)}{raw[-keep:]}"


def _build_payment_config_text(cfg: dict) -> str:
    mode = _payment_mode(cfg)
    provider = str(cfg.get("payment_provider") or "manual").strip().lower() or "manual"
    review = "ha" if str(cfg.get("manual_review_enabled", "1")) != "0" else "yo'q"
    checkout_url = str(cfg.get("checkout_url_template", "")).strip()
    checkout_ready = "ha" if checkout_url else "yo'q"
    checkout_label = cfg.get("checkout_button_label", "Auto to'lovni ochish")
    token_mask = _mask_secret(cfg.get("provider_token", ""))
    secret_mask = _mask_secret(cfg.get("provider_secret", ""))
    lines = [
        "💳 *To'lov sozlamalari*",
        "",
        f"Rejim: *{escape_md(mode)}*",
        f"Provider: *{escape_md(provider)}*",
        f"Manual review: *{review}*",
        f"Checkout URL tayyor: *{checkout_ready}*",
        f"Checkout tugma nomi: *{escape_md(checkout_label)}*",
        f"Provider token: `{escape_md(token_mask)}`",
        f"Provider secret: `{escape_md(secret_mask)}`",
        f"Karta nomi: *{escape_md(cfg.get('card_label', 'Karta'))}*",
        f"Karta: `{escape_md(cfg.get('card_number', '-'))}`",
        f"Karta egasi: *{escape_md(cfg.get('card_holder', '-'))}*",
        f"Manual izoh: {escape_md((cfg.get('payment_note', '-') or '-')[:140])}",
        f"Auto izoh: {escape_md((cfg.get('auto_payment_note', '-') or '-')[:140])}",
    ]
    return "\n".join(lines)


def _build_payment_config_keyboard(cfg: dict):
    mode = _payment_mode(cfg)
    review = str(cfg.get("manual_review_enabled", "1")) != "0"

    def mark(target: str) -> str:
        return "\u2705 " if mode == target else ""

    review_label = "\u2705 Manual review" if review else "\u274C Manual review"
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"{mark('manual')}Manual", callback_data="paycfg_mode_manual"),
            InlineKeyboardButton(f"{mark('hybrid')}Hybrid", callback_data="paycfg_mode_hybrid"),
            InlineKeyboardButton(f"{mark('auto')}Auto", callback_data="paycfg_mode_auto"),
        ],
        [InlineKeyboardButton(review_label, callback_data="paycfg_manual_review_toggle")],
        [InlineKeyboardButton("Provider", callback_data="paycfg_payment_provider"), InlineKeyboardButton("Checkout URL", callback_data="paycfg_checkout_url_template")],
        [InlineKeyboardButton("Checkout label", callback_data="paycfg_checkout_button_label"), InlineKeyboardButton("Provider token", callback_data="paycfg_provider_token")],
        [InlineKeyboardButton("Provider secret", callback_data="paycfg_provider_secret")],
        [InlineKeyboardButton("Karta nomi", callback_data="paycfg_card_label"), InlineKeyboardButton("Karta raqami", callback_data="paycfg_card_number")],
        [InlineKeyboardButton("Karta egasi", callback_data="paycfg_card_holder")],
        [InlineKeyboardButton("Manual izoh", callback_data="paycfg_payment_note"), InlineKeyboardButton("Auto izoh", callback_data="paycfg_auto_payment_note")],
        [InlineKeyboardButton("\U0001F519 Orqaga", callback_data="adm_back")],
    ])


def _build_leaderboard_admin_text(limit: int = 10) -> str:
    rows = get_leaderboard(limit)
    if not rows:
        return "🏆 Reyting hozircha bo'sh."
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    lines = ["🏆 *Platform reytingi*\n"]
    for row in rows:
        prefix = medals.get(int(row.get("rank", 0)), f"{row.get('rank', '?')}.")
        name = escape_md(row.get("first_name") or row.get("username") or f"User {row.get('user_id')}")
        lines.append(f"{prefix} *{name}* | {escape_md(str(row.get('level', 'A1')))} | {int(row.get('learning_score', 0) or 0)} ball")
    return "\n".join(lines)




def _fmt_num(value) -> str:
    try:
        return f"{int(value or 0):,}".replace(",", " ")
    except Exception:
        return "0"


def _input_back_markup(callback_data: str):
    return InlineKeyboardMarkup([[InlineKeyboardButton("\U0001F519 Orqaga", callback_data=callback_data)]])


async def _send_html_buffer(context, chat_id, document, filename: str, caption: str | None = None):
    document.name = filename
    await context.bot.send_document(chat_id, document, filename=filename, caption=caption or html_open_guide())


async def _send_temp_html_file(context, chat_id, file_path: Path, filename: str, caption: str | None = None):
    try:
        with file_path.open("rb") as f:
            await context.bot.send_document(chat_id, f, filename=filename, caption=caption or html_open_guide())
    finally:
        try:
            file_path.unlink(missing_ok=True)
        except Exception:
            pass


def _build_stats_html_doc(gs: dict):
    total = max(int(gs.get("total_users", 0) or 0), 1)
    free_users = int(gs.get("free_users", 0) or 0)
    paid_users = int(gs.get("paid_users", 0) or 0)
    pending = int(gs.get("pending_payments", 0) or 0)
    leaders = [
        {
            "rank": int(row.get("rank", 0) or 0),
            "name": row.get("first_name") or row.get("username") or f"User {row.get('user_id')}",
            "level": row.get("level", "A1"),
            "score": _fmt_num(row.get("learning_score", 0)),
        }
        for row in get_leaderboard(10)
    ]
    return render_html_document(
        "admin_stats_report.html",
        {
            "title": "Global Statistika",
            "total_users": _fmt_num(total),
            "free_users": _fmt_num(free_users),
            "paid_users": _fmt_num(paid_users),
            "pending_payments": _fmt_num(pending),
            "total_checks": _fmt_num(gs.get("total_checks", 0)),
            "total_quiz": _fmt_num(gs.get("total_quiz", 0)),
            "conversion_rate": gs.get("conversion_rate", 0),
            "free_rate": round((free_users / total) * 100, 2),
            "pending_rate": round((pending / total) * 100, 2),
            "leaders": leaders,
        },
        "global_stats_report.html",
    )


def _build_funnel_html_doc(funnel: dict):
    total = max(int(funnel.get("total_users", 0) or 0), 1)
    plans = funnel.get("plan_counts", {}) or {}
    plan_rows = []
    for name in ("free", "standard", "pro", "premium"):
        count = int(plans.get(name, 0) or 0)
        if name == "free" and count == 0:
            count = int(funnel.get("free_users", 0) or 0)
        plan_rows.append({
            "name": name.capitalize(),
            "count": _fmt_num(count),
            "rate": round((count / total) * 100, 2),
        })
    approved_count = int(funnel.get("approved_count", 0) or 0)
    pending_count = int(funnel.get("pending_count", 0) or 0)
    return render_html_document(
        "admin_funnel_report.html",
        {
            "title": "Sotuv Funnel",
            "total_users": _fmt_num(total),
            "free_users": _fmt_num(funnel.get("free_users", 0)),
            "paid_users": _fmt_num(funnel.get("paid_users", 0)),
            "conversion_rate": funnel.get("conversion_rate", 0),
            "pending_count": _fmt_num(pending_count),
            "pending_amount": _fmt_num(funnel.get("pending_amount", 0)),
            "approved_count": _fmt_num(approved_count),
            "approved_amount_30d": _fmt_num(funnel.get("approved_amount_30d", 0)),
            "rejected_count": _fmt_num(funnel.get("rejected_count", 0)),
            "new_users_7d": _fmt_num(funnel.get("new_users_7d", 0)),
            "active_users_7d": _fmt_num(funnel.get("active_users_7d", 0)),
            "pending_rate": round((pending_count / total) * 100, 2),
            "approved_rate": round((approved_count / total) * 100, 2),
            "plan_rows": plan_rows,
        },
        "sales_funnel_report.html",
    )


def _build_users_export_html_file() -> tuple[Path, int]:
    temp = tempfile.NamedTemporaryFile("w", suffix=".html", encoding="utf-8", delete=False)
    file_path = Path(temp.name)
    total = 0
    plan_counts: dict[str, int] = {}
    temp.write(
        '<!DOCTYPE html><html lang="uz"><head><meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
        '<title>Users Export</title><style>'
        'body{margin:0;padding:24px;background:#f5efe6;font-family:Georgia,serif;color:#1f2937;}'
        '.sheet{max-width:1480px;margin:0 auto;background:#fffaf4;border:1px solid #ead7c0;border-radius:24px;padding:28px;box-shadow:0 18px 42px rgba(60,36,15,.12);}'
        '.eyebrow{text-transform:uppercase;letter-spacing:.14em;font-size:12px;color:#a95517;margin-bottom:8px;}'
        '.meta{display:flex;flex-wrap:wrap;gap:10px;color:#6b7280;font-size:14px;margin-bottom:20px;}'
        '.pill{display:inline-block;padding:6px 10px;border-radius:999px;background:#f7eadc;border:1px solid #ead7c0;}'
        'table{width:100%;border-collapse:collapse;margin-top:18px;font-size:13px;}'
        'th,td{border:1px solid #ead7c0;padding:9px;text-align:left;vertical-align:top;}'
        'th{position:sticky;top:0;background:#f7efe5;}'
        'tr:nth-child(even){background:#fff;}'
        'code{background:#f6eee4;padding:2px 6px;border-radius:6px;font-size:90%;}'
        '.summary{margin-top:18px;padding:18px;border:1px solid #ead7c0;border-radius:18px;background:#fff;}'
        '</style></head><body><main class="sheet">'
    )
    temp.write(
        '<div class="eyebrow">Artificial Teacher admin export</div>'
        "<h1>Foydalanuvchilar ro'yxati</h1>"
        '<div class="meta"><span class="pill">HTML export</span>'
        "<span class=\"pill\">Jadval ko'rinishi</span>"
        '<span class="pill">Large-scale export tayyor</span></div>'
    )
    temp.write(
        "<table><thead><tr>"
        "<th>#</th><th>ID</th><th>Username</th><th>Ism</th><th>Daraja</th><th>Rol</th>"
        "<th>Tarif</th><th>Expires</th><th>Ban</th><th>Joined</th>"
        "</tr></thead><tbody>"
    )
    for batch in iter_users_with_active_plans(1000):
        for row in batch:
            total += 1
            plan = str(row.get("plan_name") or "free")
            plan_counts[plan] = plan_counts.get(plan, 0) + 1
            username = row.get("username") or "-"
            username_view = f"@{username}" if username != "-" else "-"
            temp.write("<tr>")
            temp.write(f"<td>{_fmt_num(total)}</td>")
            temp.write(f"<td><code>{pyhtml.escape(str(row.get('user_id', '')))}</code></td>")
            temp.write(f"<td>{pyhtml.escape(username_view)}</td>")
            temp.write(f"<td>{pyhtml.escape(str(row.get('first_name') or '-'))}</td>")
            temp.write(f"<td>{pyhtml.escape(str(row.get('level') or 'A1'))}</td>")
            temp.write(f"<td>{pyhtml.escape(str(row.get('role') or 'user'))}</td>")
            temp.write(f"<td>{pyhtml.escape(plan)}</td>")
            temp.write(f"<td>{pyhtml.escape(str((row.get('expires_at') or '')[:19] or '-'))}</td>")
            temp.write(f"<td>{'Ha' if row.get('is_banned') else "Yo'q"}</td>")
            temp.write(f"<td>{pyhtml.escape(str((row.get('joined_at') or '')[:19] or '-'))}</td>")
            temp.write("</tr>")
    temp.write("</tbody></table>")
    temp.write(
        f'<section class="summary"><h2 style="margin-top:0">Export summary</h2>'
        f"<p>Jami userlar: <b>{_fmt_num(total)}</b></p><ul>"
    )
    for name, count in sorted(plan_counts.items()):
        temp.write(f"<li>{pyhtml.escape(name.capitalize())}: <b>{_fmt_num(count)}</b></li>")
    temp.write("</ul></section></main></body></html>")
    temp.close()
    return file_path, total

def _build_admin_analytics_markup():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Global statistika", callback_data="adm_stats")],
        [InlineKeyboardButton("📈 Sotuv funnel", callback_data="adm_funnel")],
        [InlineKeyboardButton("🏆 Reyting", callback_data="adm_leaderboard")],
        [InlineKeyboardButton("📄 HTML hisobotlar", callback_data="adm_html_reports")],
        [InlineKeyboardButton("📄 User eksport", callback_data="adm_export_users")],
        [InlineKeyboardButton("🔙 Orqaga", callback_data="adm_back")],
    ])
def _user_detail_markup(user_row):
    ban_action = "unban" if user_row.get("is_banned") else "ban"
    ban_label = "\u2705 Blokdan chiqarish" if user_row.get("is_banned") else "\U0001F6AB Bloklash"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(ban_label, callback_data=f"adm_user_{user_row['user_id']}_{ban_action}")],
        [InlineKeyboardButton("\U0001F381 Obuna berish", callback_data=f"adm_user_{user_row['user_id']}_grant")],
        [InlineKeyboardButton("\U0001F519 Orqaga", callback_data="adm_users")],
    ])


def _clear_admin_context_flags(context):
    for key in (
        "setting_pay_config",
        "editing_plan",
        "editing_reward_setting",
        "adding_admin",
        "adding_sponsor",
        "adding_promo_pack",
        "adding_promo_code",
        "broadcasting",
        "searching_user",
        "pending_admin_id",
        "promo_code_stage",
        "promo_code_form",
    ):
        context.user_data.pop(key, None)


async def check_admin(update, context):
    user_id = update.effective_user.id
    db_user = get_user(user_id)
    if not is_admin(db_user):
        if update.message:
            await update.message.reply_text("\u274C Ruxsat yo'q.")
        return False
    return True


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update, context):
        return
    await update.effective_message.reply_text(
        build_admin_summary_text(),
        reply_markup=admin_reply_kb(update.effective_user.id),
        parse_mode="Markdown",
    )


async def show_admin_menu(user_id, context, message=None):
    text = build_admin_summary_text()
    if message:
        try:
            await message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
    await context.bot.send_message(user_id, text, reply_markup=admin_reply_kb(user_id), parse_mode="Markdown")


def _user_detail_text(user_row):
    from database.db import get_user_plan

    plan = get_user_plan(user_row["user_id"])
    plan_name = plan.get("plan_name", "free")
    icon = PLAN_ICONS.get(plan_name, "\U0001F193")
    username = user_row.get("username") or "-"
    blocked_text = "Ha" if user_row.get("is_banned") else "Yo'q"
    return (
        f"\U0001F464 *{escape_md(user_row.get('first_name') or 'User')}*\n"
        f"@{escape_md(username)} | `{user_row['user_id']}`\n"
        f"\U0001F393 Daraja: *{escape_md(user_row.get('level', 'A1'))}*\n"
        f"\U0001F4E6 Obuna: {icon} *{escape_md(plan_name.capitalize())}*\n"
        f"\U0001F6AB Bloklangan: *{blocked_text}*\n"
        f"\U0001F4C5 Qo'shilgan: *{escape_md((user_row.get('joined_at') or '')[:10])}*"
    )


async def _show_user_detail(query, user_row):
    await safe_edit(query, _user_detail_text(user_row), reply_markup=_user_detail_markup(user_row), parse_mode="Markdown")


def _sponsors_text():
    sponsors = get_sponsor_channels(active_only=False)
    lines = ["\U0001F4E3 *Homiy kanallar*\n"]
    if not sponsors:
        lines.append("Hozircha kanal qo'shilmagan.")
    else:
        for row in sponsors:
            lines.append(
                f"`{row['id']}` | *{escape_md(row['title'] or row['chat_ref'])}*\n"
                f"{escape_md(row['chat_ref'])}\n"
                f"{escape_md(row['join_url'])}\n"
            )
    lines.append("Qo'shish formati:")
    lines.append("`@username | Kanal nomi | https://t.me/username`")
    return "\n".join(lines), sponsors


async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    db_user = get_user(query.from_user.id)
    if not is_admin(db_user):
        await query.answer("\u274C Ruxsat yo'q!", show_alert=True)
        return

    data = query.data
    if is_owner_only_callback(data) and not is_owner(query.from_user.id):
        await query.answer("Faqat owner uchun.", show_alert=True)
        return

    if data == "adm_payments":
        payments = get_pending_payments()
        if not payments:
            await safe_edit(query, "\u2705 Kutayotgan to'lov yo'q.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001F519 Orqaga", callback_data="adm_back")]]))
            return
        text = [f"\u23F3 *Kutayotgan to'lovlar ({len(payments)} ta)*\n"]
        keyboard = []
        for p in payments[:15]:
            name = escape_md(p["first_name"] or p["username"] or str(p["user_id"]))
            text.append(f"#{p['id']} | {name} | {PLAN_ICONS.get(p['plan_name'], '')} {escape_md(p['plan_name'])} | {int(p['amount']):,} UZS")
            keyboard.append([InlineKeyboardButton(f"#{p['id']} Ko'rish", callback_data=f"adm_pay_view_{p['id']}")])
        keyboard.append([InlineKeyboardButton("\U0001F519 Orqaga", callback_data="adm_back")])
        await safe_edit(query, "\n".join(text), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return

    if data.startswith("adm_pay_view_"):
        pay_id = int(data.split("_")[-1])
        payment = get_payment(pay_id)
        if not payment:
            await safe_edit(query, "\u274C To'lov topilmadi.")
            return
        user_row = get_user(payment["user_id"])
        first_name = escape_md((user_row or {}).get("first_name") or str(payment["user_id"]))
        username = escape_md((user_row or {}).get("username") or "-")
        text = (
            f"\U0001F4CB *To'lov #{pay_id}*\n\n"
            f"\U0001F464 {first_name} (@{username} | `{payment['user_id']}`)\n"
            f"\U0001F4E6 Reja: {PLAN_ICONS.get(payment['plan_name'], '')} *{escape_md(payment['plan_name'])}*\n"
            f"\U0001F4B0 Miqdor: *{int(payment['amount']):,} UZS*\n"
            f"\U0001F4C5 Sana: *{escape_md(payment['created_at'][:16])}*\n"
            f"\U0001F4CC Holat: *{escape_md(payment['status'])}*"
        )
        markup = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("\u2705 Tasdiqlash", callback_data=f"pay_approve_{pay_id}"),
                InlineKeyboardButton("\u274C Rad etish", callback_data=f"pay_reject_{pay_id}"),
            ],
            [InlineKeyboardButton("\U0001F519 Orqaga", callback_data="adm_payments")],
        ])
        if payment.get("receipt_file_id"):
            try:
                await query.message.reply_photo(payment["receipt_file_id"], caption=text, reply_markup=markup, parse_mode="Markdown")
                return
            except Exception:
                try:
                    await query.message.reply_document(payment["receipt_file_id"], caption=text, reply_markup=markup, parse_mode="Markdown")
                    return
                except Exception:
                    pass
        await safe_edit(query, text, reply_markup=markup, parse_mode="Markdown")
        return

    if data.startswith("pay_approve_"):
        pay_id = int(data.split("_")[-1])
        payment = approve_payment(pay_id, query.from_user.id)
        if not payment:
            await query.answer("\u274C To'lov topilmadi.", show_alert=True)
            return
        referral_bonus = float(payment.get("referral_bonus") or 0)
        caption = (
            f"\u2705 *To'lov #{pay_id} tasdiqlandi!*\n\n"
            f"{PLAN_ICONS.get(payment['plan_name'], '')} *{escape_md(payment['plan_name'].capitalize())}* faollashtirildi.\n"
            "\u2705 Kutish ro'yxatidan o'chirildi."
        )
        if referral_bonus > 0:
            caption += f"\n\n\U0001F4B8 Referral cashback: *{referral_bonus:,.2f} UZS*"
        if query.message.photo or query.message.caption:
            try:
                await query.edit_message_caption(caption=caption, parse_mode="Markdown", reply_markup=None)
            except Exception:
                await safe_edit(query, caption, parse_mode="Markdown")
        else:
            await safe_edit(query, caption, parse_mode="Markdown")
        await safe_send(
            context,
            payment["user_id"],
            f"\U0001F389 *To'lov tasdiqlandi!*\n\nReja: {PLAN_ICONS.get(payment['plan_name'], '')} *{escape_md(payment['plan_name'].capitalize())}*\n/start",
            parse_mode="Markdown",
        )
        if referral_bonus > 0 and payment.get("referrer_id"):
            await safe_send(
                context,
                payment["referrer_id"],
                f"\U0001F381 Referral cashback tushdi!\n\nTo'langan user: `{payment['user_id']}`\nBonus: *{referral_bonus:,.2f} UZS*",
                parse_mode="Markdown",
            )
        return

    if data.startswith("pay_reject_"):
        pay_id = int(data.split("_")[-1])
        payment = get_payment(pay_id)
        reject_payment(pay_id, query.from_user.id)
        if payment:
            caption = "\u274C *To'lov rad etildi.*\n\u2705 Kutish ro'yxatidan o'chirildi."
            if query.message.photo or query.message.caption:
                try:
                    await query.edit_message_caption(caption=caption, parse_mode="Markdown", reply_markup=None)
                except Exception:
                    await safe_edit(query, caption, parse_mode="Markdown")
            else:
                await safe_edit(query, caption, parse_mode="Markdown")
            await safe_send(
                context,
                payment["user_id"],
                f"\u274C *To'lov rad etildi.*\n\nTo'lov #{pay_id}\nQayta urinib ko'rishingiz mumkin.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("\U0001F4B3 Tariflar", callback_data="menu_subscribe")],
                    [InlineKeyboardButton("\U0001F3E0 Asosiy menyu", callback_data="menu_back")],
                ]),
                parse_mode="Markdown",
            )
        return

    if data == "adm_pay_config":
        cfg = get_all_pay_config()
        await safe_edit(query, _build_payment_config_text(cfg), reply_markup=_build_payment_config_keyboard(cfg), parse_mode="Markdown")
        return

    if data.startswith("paycfg_mode_"):
        mode = data.rsplit("_", 1)[-1]
        if mode not in {"manual", "hybrid", "auto"}:
            mode = "manual"
        set_pay_config("payment_mode", mode)
        set_pay_config("payment_method", mode)
        cfg = get_all_pay_config()
        await safe_edit(query, _build_payment_config_text(cfg), reply_markup=_build_payment_config_keyboard(cfg), parse_mode="Markdown")
        return

    if data == "paycfg_manual_review_toggle":
        cfg = get_all_pay_config()
        current = str(cfg.get("manual_review_enabled", "1")) != "0"
        set_pay_config("manual_review_enabled", "0" if current else "1")
        cfg = get_all_pay_config()
        await safe_edit(query, _build_payment_config_text(cfg), reply_markup=_build_payment_config_keyboard(cfg), parse_mode="Markdown")
        return

    if data == "adm_leaderboard":
        await safe_edit(query, _build_leaderboard_admin_text(limit=10), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="adm_back")]]), parse_mode="Markdown")
        return

    if data.startswith("paycfg_"):
        field = data.split("_", 1)[1]
        labels = {
            "card_label": "Karta nomini yuboring:",
            "card_number": "Karta raqamini yuboring:",
            "card_holder": "Karta egasi ismini yuboring:",
            "payment_note": "Qo'lda to'lov uchun izoh yuboring:",
            "payment_provider": "Provider nomini yuboring (manual/click/payme/stripe/stars/external):",
            "checkout_url_template": "Checkout URL template yuboring. Misol: `https://site.uz/pay?uid={user_id}&plan={plan}&days={days}&amount={amount}`",
            "checkout_button_label": "Checkout tugma nomini yuboring:",
            "provider_token": "Provider tokenni yuboring. Tozalash uchun `clear` deb yozing:",
            "provider_secret": "Provider secretni yuboring. Tozalash uchun `clear` deb yozing:",
            "auto_payment_note": "Auto to'lov bo'limi uchun izoh yuboring:",
        }
        context.user_data["setting_pay_config"] = field
        await safe_edit(
            query,
            f"\u270F\ufe0f *{labels.get(field, field)}*",
            reply_markup=_input_back_markup("adm_pay_config"),
            parse_mode="Markdown",
        )
        return


    if data == "adm_plans":
        plans = get_all_plans()
        lines = ["\U0001F4E6 *Rejalar narxi*\n"]
        keyboard = []
        for plan in plans:
            if plan["name"] == "free":
                continue
            lines.append(
                f"{PLAN_ICONS[plan['name']]} *{escape_md(plan['display_name'])}*: {int(plan['price_monthly']):,}/oy | {int(plan['price_yearly']):,}/yil"
            )
            keyboard.append([InlineKeyboardButton(f"Narxni o'zgartirish: {plan['display_name']}", callback_data=f"plan_edit_{plan['name']}")])
        keyboard.append([InlineKeyboardButton("\U0001F519 Orqaga", callback_data="adm_back")])
        await safe_edit(query, "\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return

    if data.startswith("plan_edit_"):
        plan_name = data.split("_", 2)[2]
        context.user_data["editing_plan"] = plan_name
        await safe_edit(
            query,
            f"\u270F\ufe0f *{escape_md(plan_name.capitalize())}* oylik narxini yuboring.\nMasalan: `59000`",
            reply_markup=_input_back_markup("adm_plans"),
            parse_mode="Markdown",
        )
        return


    if data == "adm_admins":
        _clear_admin_context_flags(context)
        admins = [u for u in get_all_users() if u["role"] in ("admin", "owner")]
        lines = [f"\U0001F46E *Adminlar ({len(admins)} ta)*\n"]
        for row in admins:
            lines.append(f"{escape_md(row['first_name'])} | @{escape_md(row['username'])} | `{row['user_id']}` | *{escape_md(row['role'])}*")
        lines.append("\nAdmin qilish uchun user ID yoki @username yuboring.")
        context.user_data["adding_admin"] = True
        await safe_edit(query, "\n".join(lines), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001F519 Orqaga", callback_data="adm_back")]]), parse_mode="Markdown")
        return

    if data == "adm_broadcast":
        _clear_admin_context_flags(context)
        context.user_data["broadcasting"] = True
        await safe_edit(
            query,
            "\U0001F4E2 *Reklama yoki xabar yuborish*\n\nMatn, rasm, video yoki forward yuboring.\nBot shu xabarni barcha userlarga yuboradi.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001F519 Orqaga", callback_data="adm_back")]]),
            parse_mode="Markdown",
        )
        return

    if data == "adm_marketing":
        _clear_admin_context_flags(context)
        settings = get_all_reward_settings()
        packs = get_promo_packs(active_only=False)
        text = (
            "\U0001F381 *Marketing va bonuslar*\n\n"
            f"Referral bonusi: *{settings.get('referral_points', '25')} ball*\n"
            f"Quiz to'g'ri javob: *{settings.get('quiz_correct_points', '2')} ball*\n"
            f"Aktiv/umumiy promo pack: *{len([p for p in packs if p.get('is_active')])}/{len(packs)}*\n\n"
            "Promo pack format:\n"
            "`Nomi | plan | kun | ball`\n"
            "Misol:\n"
            "`Starter bonus | standard | 5 | 120`"
        )
        keyboard = [
            [InlineKeyboardButton("Referral bonus", callback_data="adm_reward_referral_points")],
            [InlineKeyboardButton("Quiz balli", callback_data="adm_reward_quiz_correct_points")],
            [InlineKeyboardButton("Promo pack qo'shish", callback_data="adm_pack_add")],
            [InlineKeyboardButton("Promo code qo'shish", callback_data="adm_code_add")],
        ]
        for pack in packs[:12]:
            keyboard.append([InlineKeyboardButton(f"\u274C Pack o'chirish #{pack['id']}", callback_data=f"adm_pack_del_{pack['id']}")])
        keyboard.append([InlineKeyboardButton("\U0001F519 Orqaga", callback_data="adm_back")])
        await safe_edit(query, text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return

    if data.startswith("adm_reward_"):
        field = data.replace("adm_reward_", "", 1)
        context.user_data["editing_reward_setting"] = field
        label = "Referral uchun necha ball?" if field == "referral_points" else "Quiz to'g'ri javob uchun necha ball?"
        await safe_edit(
            query,
            f"\u270F\ufe0f *{label}*\nFaqat raqam yuboring.",
            reply_markup=_input_back_markup("adm_marketing"),
            parse_mode="Markdown",
        )
        return

    if data == "adm_pack_add":
        _clear_admin_context_flags(context)
        context.user_data["adding_promo_pack"] = True
        await safe_edit(
            query,
            "Promo pack formatini yuboring:\n`Nomi | plan | kun | ball`",
            reply_markup=_input_back_markup("adm_marketing"),
            parse_mode="Markdown",
        )
        return


    if data == "adm_code_add":
        _clear_admin_context_flags(context)
        context.user_data["promo_code_stage"] = "code"
        context.user_data["promo_code_form"] = {}
        await safe_edit(
            query,
            "\U0001F39F *Promo code yaratish*\n\n1-bosqich: promo kod nomini yuboring.\nMisol: `WELCOME50`",
            reply_markup=_input_back_markup("adm_marketing"),
            parse_mode="Markdown",
        )
        return


    if data.startswith("adm_pack_del_"):
        pack_id = int(data.split("_")[-1])
        remove_promo_pack(pack_id)
        await query.answer("Promo pack o'chirildi.")
        await safe_edit(query, "Promo pack o'chirildi.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001F519 Marketing", callback_data="adm_marketing")]]))
        return

    if data == "adm_sponsors":
        _clear_admin_context_flags(context)
        text, sponsors = _sponsors_text()
        keyboard = [[InlineKeyboardButton("\u2795 Kanal qo'shish", callback_data="adm_sponsor_add")]]
        for row in sponsors[:15]:
            keyboard.append([InlineKeyboardButton(f"\u274C O'chirish #{row['id']}", callback_data=f"adm_sponsor_del_{row['id']}")])
        keyboard.append([InlineKeyboardButton("\U0001F519 Orqaga", callback_data="adm_back")])
        await safe_edit(query, text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return

    if data == "adm_sponsor_add":
        _clear_admin_context_flags(context)
        context.user_data["adding_sponsor"] = True
        await safe_edit(
            query,
            "\u2795 *Yangi homiy kanal*\n\nLink yoki @username yuboring.\n\nMisol:\n`https://t.me/kanal`\n`@kanal`\n\nXohlasangiz keyin `| Tugma nomi` ham qo'shishingiz mumkin.",
            reply_markup=_input_back_markup("adm_sponsors"),
            parse_mode="Markdown",
        )
        return

    if data.startswith("adm_confirm_admin_"):
        target_id = int(data.split("_")[-1])
        set_role(target_id, "admin")
        target_user = get_user(target_id)
        await safe_edit(
            query,
            f"\u2705 *Admin berildi*\n\n"
            f"User: *{escape_md((target_user or {}).get('first_name') or 'User')}*\n"
            f"Username: @{escape_md((target_user or {}).get('username') or '-')}\n"
            f"ID: `{target_id}`",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001F519 Orqaga", callback_data="adm_admins")]]),
            parse_mode="Markdown",
        )
        return

    if data == "adm_cancel_admin":
        context.user_data.pop("pending_admin_id", None)
        await safe_edit(
            query,
            "Admin berish bekor qilindi.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001F519 Orqaga", callback_data="adm_admins")]]),
        )
        return

    if data.startswith("adm_sponsor_del_"):
        sponsor_id = int(data.split("_")[-1])
        remove_sponsor_channel(sponsor_id)
        await query.answer("Homiy kanal o'chirildi.")
        text, sponsors = _sponsors_text()
        keyboard = [[InlineKeyboardButton("\u2795 Kanal qo'shish", callback_data="adm_sponsor_add")]]
        for row in sponsors[:15]:
            keyboard.append([InlineKeyboardButton(f"\u274C O'chirish #{row['id']}", callback_data=f"adm_sponsor_del_{row['id']}")])
        keyboard.append([InlineKeyboardButton("\U0001F519 Orqaga", callback_data="adm_back")])
        await safe_edit(query, text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return

    if data == "adm_export_users":
        file_path, total = _build_users_export_html_file()
        await _send_temp_html_file(
            context,
            query.from_user.id,
            file_path,
            "users_export.html",
            caption=f"Foydalanuvchilar eksporti\nJami userlar: {total}",
        )
        await safe_edit(
            query,
            f"?? *User eksport HTML yuborildi.*\n\nJami userlar: *{total}*\nFaylni chatdan ochishingiz mumkin.",
            reply_markup=_build_html_reports_markup(),
            parse_mode="Markdown",
        )
        return

    if data == "adm_users":
        _clear_admin_context_flags(context)
        context.user_data["searching_user"] = True
        await safe_edit(
            query,
            "?? *Foydalanuvchini topish*\n\nUser ID yoki @username yuboring.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("?? Orqaga", callback_data="adm_back")]]),
            parse_mode="Markdown",
        )
        return
    if data.startswith("adm_user_"):
        _, _, target_id_raw, action = data.split("_", 3)
        target_id = int(target_id_raw)
        user_row = get_user(target_id)
        if not user_row:
            await query.answer("Topilmadi.", show_alert=True)
            return
        if action == "ban":
            ban_user(target_id, True)
            user_row = get_user(target_id)
            await _show_user_detail(query, user_row)
            return
        if action == "unban":
            ban_user(target_id, False)
            user_row = get_user(target_id)
            await _show_user_detail(query, user_row)
            return
        if action == "grant":
            keyboard = [
                [InlineKeyboardButton("\u2B50 Standard (30 kun)", callback_data=f"grant_standard_30_{target_id}")],
                [InlineKeyboardButton("\u2B50 Standard (365 kun)", callback_data=f"grant_standard_365_{target_id}")],
                [InlineKeyboardButton("\U0001F48E Pro (30 kun)", callback_data=f"grant_pro_30_{target_id}")],
                [InlineKeyboardButton("\U0001F48E Pro (365 kun)", callback_data=f"grant_pro_365_{target_id}")],
                [InlineKeyboardButton("\U0001F451 Premium (30 kun)", callback_data=f"grant_premium_30_{target_id}")],
                [InlineKeyboardButton("\U0001F451 Premium (365 kun)", callback_data=f"grant_premium_365_{target_id}")],
                [InlineKeyboardButton("\U0001F193 Free ga qaytarish", callback_data=f"grant_free_{target_id}")],
                [InlineKeyboardButton("\U0001F519 Orqaga", callback_data="adm_users")],
            ]
            await safe_edit(
                query,
                f"\U0001F381 *{escape_md(user_row['first_name'])}* uchun obuna tanlang.",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown",
            )
            return
        await _show_user_detail(query, user_row)
        return

    if data.startswith("grant_"):
        parts = data.split("_")
        if len(parts) == 3:
            _, plan_name, target_id_raw = parts
            target_id = int(target_id_raw)
            days = 0 if plan_name == "free" else 30
        elif len(parts) == 4:
            _, plan_name, days_raw, target_id_raw = parts
            target_id = int(target_id_raw)
            days = int(days_raw)
        else:
            await query.answer("Grant formati xato.", show_alert=True)
            return
        if plan_name != "free" and has_pending_payment(target_id):
            await query.answer("Userda tekshirilayotgan to'lov bor.", show_alert=True)
            return
        active = get_active_subscription(target_id)
        if plan_name != "free" and active and active.get("plan_name") != "free":
            await query.answer("Userda aktiv pullik obuna bor.", show_alert=True)
            return
        set_subscription(target_id, plan_name, days)
        await query.answer("Obuna berildi.")
        await safe_send(
            context,
            target_id,
            f"\U0001F381 *Admin tomonidan obuna berildi!*\n\nReja: {PLAN_ICONS.get(plan_name, '')} *{escape_md(plan_name.capitalize())}*\nMuddat: *{days} kun*",
            parse_mode="Markdown",
        )
        await safe_edit(query, f"\u2705 `{target_id}` userga *{escape_md(plan_name)}* berildi. Muddat: *{days} kun*.", parse_mode="Markdown")
        return

    if data == "adm_stats":
        gs = get_global_stats()
        text = (
            "📊 *Global statistika*\n\n"
            f"👥 Jami userlar: *{gs['total_users']}*\n"
            f"🆓 Free: *{gs.get('free_users', 0)}*\n"
            f"💎 Pullik: *{gs['paid_users']}*\n"
            f"🎯 Konversiya: *{gs.get('conversion_rate', 0)}%*\n"
            f"⏳ Pending to'lovlar: *{gs['pending_payments']}*\n"
            f"✅ Tekshirishlar: *{gs['total_checks']}*\n"
            f"🎯 Quiz savollar: *{gs['total_quiz']}*"
        )
        await safe_edit(
            query,
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📄 HTML hisobot", callback_data="adm_stats_html")],
                [InlineKeyboardButton("🔙 Orqaga", callback_data="adm_back")],
            ]),
            parse_mode="Markdown",
        )
        return


    if data == "adm_funnel":
        funnel = get_sales_funnel_stats()
        plans = funnel.get("plan_counts", {})
        text = (
            "📈 *Sotuv funnel*\n\n"
            f"Jami userlar: *{funnel['total_users']}*\n"
            f"Free: *{funnel['free_users']}*\n"
            f"Paid: *{funnel['paid_users']}*\n"
            f"Konversiya: *{funnel['conversion_rate']}%*\n\n"
            f"Standard: *{plans.get('standard', 0)}*\n"
            f"Pro: *{plans.get('pro', 0)}*\n"
            f"Premium: *{plans.get('premium', 0)}*\n\n"
            f"Pending: *{funnel['pending_count']}* | *{int(funnel['pending_amount']):,} UZS*\n"
            f"Approved: *{funnel['approved_count']}* | *{int(funnel['approved_amount_30d']):,} UZS*\n"
            f"Rejected: *{funnel['rejected_count']}*\n\n"
            f"Yangi userlar (7 kun): *{funnel['new_users_7d']}*\n"
            f"Aktiv userlar (7 kun): *{funnel['active_users_7d']}*"
        )
        await safe_edit(
            query,
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📄 HTML hisobot", callback_data="adm_funnel_html")],
                [InlineKeyboardButton("🔙 Orqaga", callback_data="adm_back")],
            ]),
            parse_mode="Markdown",
        )
        return

    if data == "adm_html_reports":
        await safe_edit(
            query,
            "?? *HTML hisobotlar markazi*\n\nKerakli hisobot turini tanlang.",
            reply_markup=_build_html_reports_markup(),
            parse_mode="Markdown",
        )
        return

    if data == "adm_stats_html":
        gs = get_global_stats()
        await _send_html_buffer(
            context,
            query.from_user.id,
            _build_stats_html_doc(gs),
            "global_stats_report.html",
            caption="Global statistika HTML hisobot",
        )
        await safe_edit(
            query,
            "?? *Global statistika HTML hisobot yuborildi.*\n\nFaylni chatning o\'zidan ochishingiz mumkin.",
            reply_markup=_build_html_reports_markup(),
            parse_mode="Markdown",
        )
        return

    if data == "adm_funnel_html":
        funnel = get_sales_funnel_stats()
        await _send_html_buffer(
            context,
            query.from_user.id,
            _build_funnel_html_doc(funnel),
            "sales_funnel_report.html",
            caption="Sotuv funnel HTML hisobot",
        )
        await safe_edit(
            query,
            "?? *Sotuv funnel HTML hisobot yuborildi.*\n\nFaylni chatning o\'zidan ochishingiz mumkin.",
            reply_markup=_build_html_reports_markup(),
            parse_mode="Markdown",
        )
        return

    if data == "adm_back":
        _clear_admin_context_flags(context)
        await show_admin_menu(query.from_user.id, context, message=query.message)

async def admin_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db_user = get_user(user.id)
    if not is_admin(db_user):
        return False

    text = update.message.text.strip()
    menu_text = normalize_admin_text(text)
    owner_only_sections = {"to'lov sozlamalari", "adminlar", "marketing"}

    if menu_text in owner_only_sections and not is_owner(user.id):
        await update.message.reply_text("Bu bo'lim faqat owner uchun.")
        return True

    if menu_text in {"admin panel", "dashboard"}:
        _clear_admin_context_flags(context)
        await update.message.reply_text(
            build_admin_summary_text(),
            reply_markup=admin_reply_kb(user.id),
            parse_mode="Markdown",
        )
        return True

    if context.user_data.get("setting_pay_config"):
        if not is_owner(user.id):
            context.user_data.pop("setting_pay_config", None)
            await update.message.reply_text("Bu sozlama faqat owner uchun.", reply_markup=_input_back_markup("adm_back"))
            return True
        field = context.user_data.pop("setting_pay_config")
        value = text.strip().strip('"').strip("'")
        if value.lower() in {"clear", "none", "bo'sh", "empty", "-"}:
            value = ""
        if field == "payment_provider":
            value = value.lower().replace(" ", "_")
        set_pay_config(field, value)
        if field == "payment_mode":
            set_pay_config("payment_method", value)
        cfg = get_all_pay_config()
        await update.message.reply_text(_build_payment_config_text(cfg), reply_markup=_build_payment_config_keyboard(cfg), parse_mode="Markdown")
        return True

    if context.user_data.get("editing_plan"):
        plan_name = context.user_data.pop("editing_plan")
        try:
            amount = float(text.replace(" ", ""))
        except ValueError:
            await update.message.reply_text("\u274C Faqat raqam yuboring.")
            return True
        update_plan(plan_name, "price_monthly", amount)
        await update.message.reply_text(
            f"\u2705 *{escape_md(plan_name)}* oylik narxi: *{int(amount):,} UZS*",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001F519 Orqaga", callback_data="adm_plans")]]),
            parse_mode="Markdown",
        )
        return True

    if context.user_data.get("editing_reward_setting") and is_owner(user.id):
        field = context.user_data.pop("editing_reward_setting")
        try:
            value = int(text.replace(" ", ""))
        except ValueError:
            await update.message.reply_text("\u274C Faqat raqam yuboring.")
            return True
        set_reward_setting(field, value)
        await update.message.reply_text(
            f"\u2705 *{escape_md(field)}* yangilandi: *{value}*",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001F519 Marketing", callback_data="adm_marketing")]]),
            parse_mode="Markdown",
        )
        return True

    if context.user_data.get("adding_admin") and is_owner(user.id):
        target = text.strip()
        target_user = None
        target_id = None
        if target.isdigit():
            target_id = int(target)
            target_user = get_user(target_id)
        else:
            target_user = find_user_by_username(target)
            if target_user:
                target_id = int(target_user.get("user_id", 0) or 0)
        if not target_id or not target_user:
            await update.message.reply_text("❌ User topilmadi. ID yoki @username yuboring.", reply_markup=_input_back_markup("adm_admins"))
            return True
        context.user_data.pop("adding_admin", None)
        context.user_data["pending_admin_id"] = target_id
        await update.message.reply_text(
            f"👮 *Admin qilish tasdig'i*\n\n"
            f"User: *{escape_md(target_user.get('first_name') or 'User')}*\n"
            f"Username: @{escape_md(target_user.get('username') or '-')}\n"
            f"ID: `{target_id}`\n\nRostdan ham admin qilamizmi?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"adm_confirm_admin_{target_id}")],
                [InlineKeyboardButton("❌ Bekor qilish", callback_data="adm_cancel_admin")],
            ]),
            parse_mode="Markdown",
        )
        return True


    if context.user_data.get("adding_sponsor"):
        context.user_data.pop("adding_sponsor", None)
        parts = [part.strip() for part in text.split("|") if part.strip()]
        if not parts:
            await update.message.reply_text("Kanal linki yoki @username yuboring.", reply_markup=_input_back_markup("adm_sponsors"))
            return True
        if len(parts) == 1:
            raw = parts[0]
            join_url = raw if raw.startswith("http") else f"https://t.me/{raw.lstrip('@')}"
            if raw.startswith("@"):
                chat_ref = raw
                title = raw.lstrip("@")
            elif "t.me/" in raw:
                slug = raw.split("t.me/", 1)[1].strip("/")
                if slug.startswith("+"):
                    chat_ref = raw
                    title = "Homiy kanal"
                else:
                    chat_ref = f"@{slug}"
                    title = slug
            else:
                await update.message.reply_text("Kanal linki yoki @username yuboring.", reply_markup=_input_back_markup("adm_sponsors"))
                return True
        elif len(parts) == 2:
            raw, title = parts
            join_url = raw if raw.startswith("http") else f"https://t.me/{raw.lstrip('@')}"
            if raw.startswith("@"):
                chat_ref = raw
            elif "t.me/" in raw:
                slug = raw.split("t.me/", 1)[1].strip("/")
                chat_ref = raw if slug.startswith("+") else f"@{slug}"
            else:
                chat_ref = raw
        else:
            chat_ref, title, join_url = parts[:3]
        add_sponsor_channel(chat_ref, title, join_url)
        await update.message.reply_text("\u2705 Homiy kanal qo'shildi.")
        return True

    if context.user_data.get("adding_promo_pack") and is_owner(user.id):
        context.user_data.pop("adding_promo_pack", None)
        parts = [part.strip() for part in text.split("|")]
        if len(parts) != 4:
            await update.message.reply_text("Format: Nomi | plan | kun | ball", reply_markup=_input_back_markup("adm_marketing"))
            return True
        title, plan_name, days_raw, points_raw = parts
        try:
            days = int(days_raw)
            points = int(points_raw)
        except ValueError:
            await update.message.reply_text("Kun va ball raqam bo'lishi kerak.", reply_markup=_input_back_markup("adm_marketing"))
            return True
        add_promo_pack(title, plan_name.lower(), days, points)
        await update.message.reply_text(
            f"\u2705 Promo pack qo'shildi: *{escape_md(title)}*",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001F519 Marketing", callback_data="adm_marketing")]]),
            parse_mode="Markdown",
        )
        return True

    if context.user_data.get("promo_code_stage") and is_owner(user.id):
        stage = context.user_data.get("promo_code_stage")
        form = context.user_data.setdefault("promo_code_form", {})
        if stage == "code":
            form["code"] = text.strip().upper()
            context.user_data["promo_code_stage"] = "points"
            await update.message.reply_text("2-bosqich: nechta ball berilishini yuboring.", reply_markup=_input_back_markup("adm_marketing"))
            return True
        if stage == "points":
            try:
                form["points"] = int(text.replace(" ", ""))
            except ValueError:
                await update.message.reply_text("❌ Ball raqam bo'lishi kerak.", reply_markup=_input_back_markup("adm_marketing"))
                return True
            context.user_data["promo_code_stage"] = "limit"
            await update.message.reply_text("3-bosqich: promo code nechta user ishlata olishini yuboring.", reply_markup=_input_back_markup("adm_marketing"))
            return True
        if stage == "limit":
            try:
                limit = int(text.replace(" ", ""))
            except ValueError:
                await update.message.reply_text("❌ Limit raqam bo'lishi kerak.", reply_markup=_input_back_markup("adm_marketing"))
                return True
            add_promo_code(form.get("code", "PROMO"), int(form.get("points", 0)), limit)
            context.user_data.pop("promo_code_stage", None)
            context.user_data.pop("promo_code_form", None)
            await update.message.reply_text(
                f"✅ Promo code qo'shildi: *{escape_md(form.get('code', 'PROMO'))}*",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Marketing", callback_data="adm_marketing")]]),
                parse_mode="Markdown",
            )
            return True

    if context.user_data.get("adding_promo_code") and is_owner(user.id):
        context.user_data.pop("adding_promo_code", None)
        parts = [part.strip() for part in text.split("|")]
        if len(parts) != 3:
            await update.message.reply_text("Format: KOD | ball | limit", reply_markup=_input_back_markup("adm_marketing"))
            return True
        code, points_raw, limit_raw = parts
        try:
            points = int(points_raw)
            limit = int(limit_raw)
        except ValueError:
            await update.message.reply_text("Ball va limit raqam bo'lishi kerak.", reply_markup=_input_back_markup("adm_marketing"))
            return True
        add_promo_code(code, points, limit)
        await update.message.reply_text(
            f"✅ Promo code qo'shildi: *{escape_md(code.upper())}*",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Marketing", callback_data="adm_marketing")]]),
            parse_mode="Markdown",
        )
        return True


    if context.user_data.get("broadcasting"):
        menu_actions = {
            "user panel", "admin panel", "dashboard", "to'lovlar", "userlar", "to'lov sozlamalari",
            "statistika", "funnel", "analitika", "export", "export users", "html hisobotlar", "reklama", "homiy kanallar",
            "rejalar", "adminlar", "marketing", "reyting",
        }
        if menu_text in menu_actions:
            context.user_data.pop("broadcasting", None)
        else:
            context.user_data.pop("broadcasting")
            success, fail = await _broadcast_user_id_batches(
                lambda user_id: _broadcast_text_one(context, user_id, text),
            )
            await update.message.reply_text(f"\U0001F4E2 Yuborildi.\n\u2705 {success} ta | \u274C {fail} ta")
            return True

    if context.user_data.get("searching_user"):
        context.user_data.pop("searching_user")
        target = text.strip()
        user_row = None
        if target.isdigit():
            user_row = get_user(int(target))
        else:
            user_row = find_user_by_username(target)
        if not user_row:
            await update.message.reply_text("? Foydalanuvchi topilmadi. ID yoki @username yuboring.", reply_markup=_input_back_markup("adm_users"))
            return True
        await update.message.reply_text(
            _user_detail_text(user_row),
            reply_markup=_user_detail_markup(user_row),
            parse_mode="Markdown",
        )
        return True

    if menu_text == "user panel":
        await update.message.reply_text(
            "?? User dashboardga qaytdingiz.",
            reply_markup=user_reply_kb(user.id),
        )
        return True

    if menu_text == "to'lovlar":
        _clear_admin_context_flags(context)
        payments = get_pending_payments()
        if not payments:
            await update.message.reply_text("? Kutayotgan to'lov yo'q.", reply_markup=_input_back_markup("adm_back"))
            return True
        lines = [f"? *Kutayotgan to'lovlar ({len(payments)} ta)*\n"]
        keyboard = []
        for p in payments[:15]:
            name = escape_md(p["first_name"] or p["username"] or str(p["user_id"]))
            lines.append(f"#{p['id']} | {name} | {PLAN_ICONS.get(p['plan_name'], '')} {escape_md(p['plan_name'])} | {int(p['amount']):,} UZS")
            keyboard.append([InlineKeyboardButton(f"#{p['id']} Ko'rish", callback_data=f"adm_pay_view_{p['id']}")])
        keyboard.append([InlineKeyboardButton("?? Orqaga", callback_data="adm_back")])
        await update.message.reply_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return True

    if menu_text == "userlar":
        _clear_admin_context_flags(context)
        context.user_data["searching_user"] = True
        await update.message.reply_text("?? User ID yoki @username yuboring.", reply_markup=_input_back_markup("adm_back"))
        return True

    if menu_text == "to'lov sozlamalari":
        _clear_admin_context_flags(context)
        cfg = get_all_pay_config()
        await update.message.reply_text(_build_payment_config_text(cfg), reply_markup=_build_payment_config_keyboard(cfg), parse_mode="Markdown")
        return True

    if menu_text == "analitika":
        await update.message.reply_text(
            "?? *Analitika markazi*\n\nKerakli hisobotni tanlang.",
            reply_markup=_build_admin_analytics_markup(),
            parse_mode="Markdown",
        )
        return True

    if menu_text == "html hisobotlar":
        await update.message.reply_text(
            "?? *HTML hisobotlar markazi*\n\nKerakli hisobot turini tanlang.",
            reply_markup=_build_html_reports_markup(),
            parse_mode="Markdown",
        )
        return True

    if menu_text == "reyting":
        await update.message.reply_text(
            _build_leaderboard_admin_text(limit=10),
            reply_markup=_input_back_markup("adm_back"),
            parse_mode="Markdown",
        )
        return True

    if menu_text == "statistika":
        gs = get_global_stats()
        msg = (
            "?? *Global statistika*\n\n"
            f"?? Jami userlar: *{gs['total_users']}*\n"
            f"?? Free: *{gs.get('free_users', 0)}*\n"
            f"?? Pullik: *{gs['paid_users']}*\n"
            f"?? Konversiya: *{gs.get('conversion_rate', 0)}%*\n"
            f"? Pending to'lovlar: *{gs['pending_payments']}*\n"
            f"? Tekshirishlar: *{gs['total_checks']}*\n"
            f"?? Quiz savollar: *{gs['total_quiz']}*"
        )
        await update.message.reply_text(
            msg,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("?? HTML hisobot", callback_data="adm_stats_html")],
                [InlineKeyboardButton("?? Orqaga", callback_data="adm_back")],
            ]),
            parse_mode="Markdown",
        )
        return True

    if menu_text == "funnel":
        funnel = get_sales_funnel_stats()
        plans = funnel.get("plan_counts", {})
        msg = (
            "?? *Sotuv funnel*\n\n"
            f"Jami userlar: *{funnel['total_users']}*\n"
            f"Free: *{funnel['free_users']}*\n"
            f"Paid: *{funnel['paid_users']}*\n"
            f"Konversiya: *{funnel['conversion_rate']}%*\n\n"
            f"Standard: *{plans.get('standard', 0)}*\n"
            f"Pro: *{plans.get('pro', 0)}*\n"
            f"Premium: *{plans.get('premium', 0)}*\n\n"
            f"Pending: *{funnel['pending_count']}* | *{int(funnel['pending_amount']):,} UZS*\n"
            f"Approved: *{funnel['approved_count']}* | *{int(funnel['approved_amount_30d']):,} UZS*\n"
            f"Rejected: *{funnel['rejected_count']}*\n\n"
            f"Yangi userlar (7 kun): *{funnel['new_users_7d']}*\n"
            f"Aktiv userlar (7 kun): *{funnel['active_users_7d']}*"
        )
        await update.message.reply_text(
            msg,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("?? HTML hisobot", callback_data="adm_funnel_html")],
                [InlineKeyboardButton("?? Orqaga", callback_data="adm_back")],
            ]),
            parse_mode="Markdown",
        )
        return True

    if menu_text in {"export users", "export"}:
        file_path, total = _build_users_export_html_file()
        await _send_temp_html_file(
            context,
            user.id,
            file_path,
            "users_export.html",
            caption=f"Foydalanuvchilar eksporti\nJami userlar: {total}",
        )
        await update.message.reply_text(
            f"?? User eksport HTML yuborildi.\nJami userlar: {total}",
            reply_markup=_build_html_reports_markup(),
        )
        return True

    if menu_text == "reklama":
        _clear_admin_context_flags(context)
        context.user_data["broadcasting"] = True
        await update.message.reply_text("Reklama matni yoki media yuboring. Bot hamma userlarga jo'natadi.", reply_markup=_input_back_markup("adm_back"))
        return True

    if menu_text == "homiy kanallar":
        _clear_admin_context_flags(context)
        context.user_data.pop("adding_sponsor", None)
        text_out, sponsors = _sponsors_text()
        keyboard = [[InlineKeyboardButton("? Kanal qo'shish", callback_data="adm_sponsor_add")]]
        for row in sponsors[:15]:
            keyboard.append([InlineKeyboardButton(f"? O'chirish #{row['id']}", callback_data=f"adm_sponsor_del_{row['id']}")])
        keyboard.append([InlineKeyboardButton("?? Orqaga", callback_data="adm_back")])
        await update.message.reply_text(text_out, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return True

    if menu_text == "rejalar":
        _clear_admin_context_flags(context)
        plans = get_all_plans()
        lines = ["?? *Rejalar narxi*\n"]
        keyboard = []
        for plan in plans:
            if plan["name"] == "free":
                continue
            lines.append(f"{PLAN_ICONS[plan['name']]} *{escape_md(plan['display_name'])}*: {int(plan['price_monthly']):,}/oy | {int(plan['price_yearly']):,}/yil")
            keyboard.append([InlineKeyboardButton(f"Narxni o'zgartirish: {plan['display_name']}", callback_data=f"plan_edit_{plan['name']}")])
        keyboard.append([InlineKeyboardButton("?? Orqaga", callback_data="adm_back")])
        await update.message.reply_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return True

    if menu_text == "adminlar" and is_owner(user.id):
        _clear_admin_context_flags(context)
        admins = [u for u in get_all_users() if u["role"] in ("admin", "owner")]
        lines = [f"?? *Adminlar ({len(admins)} ta)*\n"]
        for row in admins:
            lines.append(f"{escape_md(row['first_name'])} | @{escape_md(row['username'])} | `{row['user_id']}` | *{escape_md(row['role'])}*")
        lines.append("\nAdmin qilish uchun user ID yoki @username yuboring.")
        context.user_data["adding_admin"] = True
        await update.message.reply_text("\n".join(lines), reply_markup=_input_back_markup("adm_back"), parse_mode="Markdown")
        return True

    if menu_text == "marketing" and is_owner(user.id):
        _clear_admin_context_flags(context)
        settings = get_all_reward_settings()
        packs = get_promo_packs(active_only=False)
        msg = (
            "\U0001F381 *Marketing va bonuslar*\n\n"
            f"Referral bonusi: *{settings.get('referral_points', '25')} ball*\n"
            f"Quiz to'g'ri javob: *{settings.get('quiz_correct_points', '2')} ball*\n"
            f"Aktiv/umumiy promo pack: *{len([p for p in packs if p.get('is_active')])}/{len(packs)}*\n\n"
            "Promo pack format:\n`Nomi | plan | kun | ball`"
        )
        keyboard = [
            [InlineKeyboardButton("Referral bonus", callback_data="adm_reward_referral_points")],
            [InlineKeyboardButton("Quiz balli", callback_data="adm_reward_quiz_correct_points")],
            [InlineKeyboardButton("Promo pack qo'shish", callback_data="adm_pack_add")],
            [InlineKeyboardButton("Promo code qo'shish", callback_data="adm_code_add")],
        ]
        keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="adm_back")])
        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return True

    return False


async def admin_media_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db_user = get_user(user.id)
    if not is_admin(db_user):
        return False
    if not context.user_data.get("broadcasting"):
        return False

    context.user_data.pop("broadcasting", None)
    success, fail = await _broadcast_user_id_batches(
        lambda user_id: _broadcast_copy_one(
            context,
            user_id,
            update.effective_chat.id,
            update.message.message_id,
        )
    )
    await update.message.reply_text(f"\U0001F4E2 Media reklama yuborildi.\n\u2705 {success} ta | \u274C {fail} ta")
    return True


def build_group_settings_keyboard(chat_id: int, settings: dict):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{'\u2705' if settings.get('check_enabled') else '\u274C'} #check", callback_data=f"gadm_{chat_id}_check_enabled")],
        [InlineKeyboardButton(f"{'\u2705' if settings.get('bot_enabled') else '\u274C'} #bot", callback_data=f"gadm_{chat_id}_bot_enabled")],
        [InlineKeyboardButton(f"{'\u2705' if settings.get('translate_enabled', 1) else '\u274C'} #t", callback_data=f"gadm_{chat_id}_translate_enabled")],
        [InlineKeyboardButton(f"{'\u2705' if settings.get('pronunciation_enabled', 1) else '\u274C'} #p", callback_data=f"gadm_{chat_id}_pronunciation_enabled")],
        [InlineKeyboardButton(f"{'\u2705' if settings.get('daily_enabled') else '\u274C'} Kunlik so'z", callback_data=f"gadm_{chat_id}_daily_enabled")],
    ])


async def group_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type == "private":
        await admin_command(update, context)
        return
    user = update.effective_user
    try:
        member = await context.bot.get_chat_member(chat.id, user.id)
        if member.status not in ("administrator", "creator"):
            await update.message.reply_text("\u274C Faqat guruh adminlari uchun.")
            return
    except Exception:
        return

    settings = get_group(chat.id)
    await update.message.reply_text(
        "\u2699\ufe0f *Guruh sozlamalari*",
        reply_markup=build_group_settings_keyboard(chat.id, settings),
        parse_mode="Markdown",
    )


async def group_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, chat_id_raw, field = query.data.split("_", 2)
    chat_id = int(chat_id_raw)
    settings = get_group(chat_id)
    new_val = 0 if settings.get(field) else 1
    set_group(chat_id, field, new_val)
    settings = get_group(chat_id)
    await query.edit_message_reply_markup(reply_markup=build_group_settings_keyboard(chat_id, settings))




