"""
Admin dashboard handler.
Inline-first panel for payments, users, broadcast, stats, plans and leaderboard.
"""

import csv
import io
import logging
from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from src.bot.filters.role import RoleFilter
from src.bot.utils.html_report import build_admin_stats_report, build_admin_user_report
from src.bot.utils.telegram import (
    escape_html,
    fmt_num,
    fmt_price,
    safe_answer_callback,
    safe_edit,
    safe_reply,
)
from src.database.connection import get_db
from src.database.dao import leaderboard_dao, payment_dao, stats_dao, subscription_dao, user_dao

logger = logging.getLogger(__name__)
router = Router(name="admin")

router.message.filter(RoleFilter("admin", "owner"))
router.callback_query.filter(RoleFilter("admin", "owner"))

BROADCAST_STATE = "ADMIN_BROADCAST_WAIT"
USER_SEARCH_STATE = "ADMIN_USER_SEARCH_WAIT"
PLAN_EDIT_STATE = "ADMIN_EDIT_PLAN_PRICE"


def _extract_broadcast_text(raw_text: str | None) -> str:
    if not raw_text:
        return ""
    parts = raw_text.strip().split(maxsplit=1)
    if not parts:
        return ""
    cmd = parts[0].split("@", 1)[0].lower()
    if cmd != "/broadcast":
        return ""
    return parts[1].strip() if len(parts) > 1 else ""





async def _growth_data_last_days(days: int = 7) -> list[dict]:
    db = await get_db()
    start_day = (datetime.utcnow().date() - timedelta(days=days - 1)).isoformat()
    cursor = await db.execute(
        """
        SELECT substr(joined_at, 1, 10) AS day, COUNT(*) AS cnt
        FROM users
        WHERE joined_at IS NOT NULL AND substr(joined_at, 1, 10) >= ?
        GROUP BY substr(joined_at, 1, 10)
        ORDER BY day ASC
        """,
        (start_day,),
    )
    rows = await cursor.fetchall()
    counts = {str(row["day"] if isinstance(row, dict) else row[0]): int(row["cnt"] if isinstance(row, dict) else row[1]) for row in rows}

    result: list[dict] = []
    for offset in range(days - 1, -1, -1):
        day = (datetime.utcnow().date() - timedelta(days=offset))
        day_iso = day.isoformat()
        result.append({"day": day.strftime("%m-%d"), "count": counts.get(day_iso, 0)})
    return result


def _growth_chart_text(growth: list[dict]) -> str:
    if not growth:
        return "<i>Ma'lumot yo'q</i>"
    max_count = max((item["count"] for item in growth), default=1) or 1
    lines = []
    for item in growth:
        count = item["count"]
        filled = int((count / max_count) * 10) if max_count else 0
        bar = "█" * filled + "░" * (10 - filled)
        lines.append(f"<code>{item['day']}</code> | {bar} <b>{count}</b>")
    return "\n".join(lines)


async def _get_admin_overview() -> tuple[int, int, int, float]:
    total_users = await user_dao.count_users()
    paid_users = await subscription_dao.count_paid_users()
    pending = await payment_dao.count_pending_payments()
    revenue = await payment_dao.get_total_revenue()
    return total_users, paid_users, pending, revenue


async def _get_top_users(limit: int = 20) -> list[dict]:
    db = await get_db()
    cursor = await db.execute(
        """
        SELECT
            u.user_id,
            u.first_name,
            u.username,
            COALESCE(s.checks_total, 0) AS checks_total,
            COALESCE(s.quiz_played, 0) AS quiz_played,
            COALESCE(x.total_xp, 0) AS xp
        FROM users u
        LEFT JOIN stats s ON s.user_id = u.user_id
        LEFT JOIN user_xp x ON x.user_id = u.user_id
        WHERE u.is_banned = 0
        ORDER BY COALESCE(x.total_xp, 0) DESC, COALESCE(s.checks_total, 0) DESC, COALESCE(s.quiz_played, 0) DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = await cursor.fetchall()
    result: list[dict] = []
    for row in rows:
        item = dict(row)
        name = item.get("first_name") or item.get("username") or str(item.get("user_id"))
        result.append(
            {
                "user_id": item.get("user_id"),
                "name": name,
                "xp": item.get("xp", 0),
                "checks_total": item.get("checks_total", 0),
                "quiz_played": item.get("quiz_played", 0),
            }
        )
    return result


async def _render_dashboard(target: Message | CallbackQuery) -> None:
    try:
        total_users, paid_users, pending, revenue = await _get_admin_overview()
    except Exception as exc:
        logger.error("Admin dashboard DB error: %s", exc)
        if isinstance(target, CallbackQuery):
            await safe_answer_callback(target, "⚠️ Server xatosi", show_alert=True)
        else:
            await safe_reply(target, "⚠️ Server xatosi. Iltimos, qayta urinib ko'ring.")
        return

    conversion = f"{(paid_users / total_users * 100):.1f}%" if total_users else "0%"
    text = (
        "🛡 <b>Admin Dashboard</b>\n\n"
        f"👥 Jami foydalanuvchilar: <b>{fmt_num(total_users)}</b>\n"
        f"💎 Pulli obunalar: <b>{fmt_num(paid_users)}</b>\n"
        f"📊 Konversiya: <b>{conversion}</b>\n"
        f"💰 Umumiy tushum: <b>{fmt_price(revenue)}</b>\n"
        f"⏳ Kutilayotgan to'lovlar: <b>{pending}</b>\n\n"
        "Pastdagi tugmalardan bo'limni tanlang."
    )

    if isinstance(target, CallbackQuery):
        await safe_edit(target, text, reply_markup=None)
        await safe_answer_callback(target)
    else:
        await safe_reply(target, text)


async def _ensure_admin_reply_menu(message: Message) -> None:
    """Enable admin reply keyboard so command-less flow works from buttons."""
    from src.bot.keyboards.user_menu import admin_main_menu

    await safe_reply(
        message,
        "🛡 Admin rejimi yoqildi. Bo'limlarni pastdagi tugmalardan tanlang.",
        reply_markup=admin_main_menu(),
    )


async def _render_payments(target: Message | CallbackQuery) -> None:
    payments = await payment_dao.get_pending_payments()
    if not payments:
        text = "✅ <b>Kutilayotgan to'lovlar yo'q.</b>"
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Dashboard", callback_data="adm:back")]])
    else:
        lines = [f"💳 <b>Kutilayotgan to'lovlar ({len(payments)})</b>", ""]
        buttons: list[list[InlineKeyboardButton]] = []
        for payment in payments[:12]:
            user = await user_dao.get_user(payment["user_id"])
            name = escape_html((user or {}).get("first_name", "?"))
            lines.append(
                f"#{payment['id']} | {name} (ID: {payment['user_id']})\n"
                f"📋 {payment['plan_name'].title()} | {fmt_price(payment['amount'])} | {payment['duration_days']} kun\n"
            )
            buttons.append(
                [
                    InlineKeyboardButton(text=f"✅ #{payment['id']}", callback_data=f"admin_approve:{payment['id']}"),
                    InlineKeyboardButton(text=f"❌ #{payment['id']}", callback_data=f"admin_reject:{payment['id']}"),
                ]
            )
        buttons.append([InlineKeyboardButton(text="🔙 Dashboard", callback_data="adm:back")])
        text = "\n".join(lines)
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    if isinstance(target, CallbackQuery):
        await safe_edit(target, text, reply_markup=kb)
        await safe_answer_callback(target)
    else:
        await safe_reply(target, text, reply_markup=kb)


def _users_home_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔎 User qidirish", callback_data="adm:users_search"),
                InlineKeyboardButton(text="📋 Oxirgi userlar", callback_data="adm:users_list:0"),
            ],
            [
                InlineKeyboardButton(text="📥 CSV export", callback_data="adm:export_users"),
            ],
            [InlineKeyboardButton(text="🔙 Dashboard", callback_data="adm:back")],
        ]
    )


async def _render_users_home(target: Message | CallbackQuery) -> None:
    text = (
        "👥 <b>Foydalanuvchilar paneli</b>\n\n"
        "User bilan ishlash uchun tugmalarni ishlating:\n"
        "• Qidirish: ID yoki @username\n"
        "• Oxirgi userlar ro'yxati\n"
        "• CSV export\n"
    )
    if isinstance(target, CallbackQuery):
        await safe_edit(target, text, reply_markup=_users_home_keyboard())
        await safe_answer_callback(target)
    else:
        await safe_reply(target, text, reply_markup=_users_home_keyboard())


async def _render_users_list(callback: CallbackQuery, offset: int = 0, limit: int = 12) -> None:
    users = await user_dao.get_users_page(offset=offset, limit=limit)
    lines = [f"👥 <b>Userlar ro'yxati</b> (offset {offset})", ""]
    buttons: list[list[InlineKeyboardButton]] = []

    if users:
        for item in users:
            user_id = int(item["user_id"])
            first_name = escape_html(item.get("first_name", "") or "-")
            username = escape_html(item.get("username", "") or "-")
            lines.append(f"<code>{user_id}</code> | {first_name} | @{username}")
            buttons.append(
                [
                    InlineKeyboardButton(
                        text=f"👤 {first_name[:12]} ({user_id})",
                        callback_data=f"adm:user:{user_id}",
                    )
                ]
            )
    else:
        lines.append("<i>User topilmadi.</i>")

    nav_row: list[InlineKeyboardButton] = []
    if offset > 0:
        prev_offset = max(0, offset - limit)
        nav_row.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"adm:users_list:{prev_offset}"))
    if users and len(users) == limit:
        nav_row.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"adm:users_list:{offset + limit}"))
    if nav_row:
        buttons.append(nav_row)

    buttons.append([InlineKeyboardButton(text="🔙 Userlar paneli", callback_data="adm:users")])
    await safe_edit(callback, "\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await safe_answer_callback(callback)


def _user_card_keyboard(user: dict) -> InlineKeyboardMarkup:
    user_id = int(user["user_id"])
    ban_action = "unban" if user.get("is_banned") else "ban"
    ban_text = "✅ Bandan olish" if user.get("is_banned") else "🚫 Ban qilish"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=ban_text, callback_data=f"adm_user:{ban_action}:{user_id}")],
            [
                InlineKeyboardButton(text="⭐ Free", callback_data=f"adm_user:free:{user_id}"),
                InlineKeyboardButton(text="💎 Pro", callback_data=f"adm_user:pro:{user_id}"),
                InlineKeyboardButton(text="👑 Premium", callback_data=f"adm_user:premium:{user_id}"),
            ],
            [InlineKeyboardButton(text="📄 HTML hisobot", callback_data=f"adm:userhtml:{user_id}")],
            [InlineKeyboardButton(text="🔙 Userlar paneli", callback_data="adm:users")],
        ]
    )


async def _render_user_card(target: Message | CallbackQuery, user_id: int) -> None:
    user = await user_dao.get_user(user_id)
    if not user:
        if isinstance(target, CallbackQuery):
            await safe_answer_callback(target, "❌ User topilmadi.", show_alert=True)
        else:
            await safe_reply(target, "❌ User topilmadi.")
        return

    plan = await subscription_dao.get_active_plan_name(user_id)
    remain = await subscription_dao.remaining_days(user_id)
    stats = await stats_dao.get_stats(user_id)
    usage = await stats_dao.get_usage_today(user_id)

    text = (
        "👤 <b>Foydalanuvchi profil</b>\n\n"
        f"ID: <code>{user['user_id']}</code>\n"
        f"Ism: {escape_html(user.get('first_name', '') or '-')}\n"
        f"Username: @{escape_html(user.get('username', '') or '-')}\n"
        f"Daraja: <b>{escape_html(user.get('level', 'A1'))}</b>\n"
        f"Rol: <b>{escape_html(user.get('role', 'user'))}</b>\n"
        f"Obuna: <b>{escape_html(plan)}</b> ({remain} kun)\n"
        f"Qo'shilgan: {escape_html(str(user.get('joined_at', ''))[:19])}\n"
        f"Holat: {'🚫 <b>Ban qilingan</b>' if user.get('is_banned') else '✅ <b>Aktiv</b>'}\n\n"
        "📊 <b>Qisqa statistika</b>\n"
        f"• Checks: <b>{fmt_num(stats.get('checks_total', 0))}</b>\n"
        f"• Quiz: <b>{fmt_num(stats.get('quiz_played', 0))}</b> / ✅ {fmt_num(stats.get('quiz_correct', 0))}\n"
        f"• Messages: <b>{fmt_num(stats.get('messages_total', 0))}</b>\n"
        f"• Bugungi AI xabar: <b>{fmt_num(usage.get('ai_messages', 0))}</b>"
    )
    kb = _user_card_keyboard(user)

    if isinstance(target, CallbackQuery):
        await safe_edit(target, text, reply_markup=kb)
        await safe_answer_callback(target)
    else:
        await safe_reply(target, text, reply_markup=kb)


async def _run_broadcast(
    message: Message,
    *,
    text: str = "",
    source_message: Message | None = None,
) -> None:
    from src.services.broadcast_service import send_broadcast

    status_msg = await safe_reply(message, "📢 Broadcast boshlanmoqda...")

    async def _progress(done: int, total: int, sent: int, failed: int) -> None:
        if not status_msg:
            return
        try:
            await status_msg.edit_text(
                "📢 Broadcast davom etmoqda...\n\n"
                f"Jarayon: {done}/{total}\n"
                f"✅ Yuborildi: {sent}\n"
                f"❌ Xato: {failed}"
            )
        except Exception:
            pass

    result = await send_broadcast(text=text, progress_callback=_progress, source_message=source_message)
    if status_msg:
        try:
            await status_msg.edit_text(
                "📢 <b>Broadcast yakunlandi!</b>\n\n"
                f"📊 Jami: {result['total']}\n"
                f"✅ Yuborildi: {result['sent']}\n"
                f"❌ Xato: {result['failed']}"
            )
        except Exception:
            pass


async def _render_stats(target: Message | CallbackQuery, generated_by: str = "") -> None:
    total_users, paid, pending, revenue = await _get_admin_overview()
    conversion = f"{(paid / total_users * 100):.1f}%" if total_users else "0%"
    admins = await user_dao.count_users_by_role("admin")
    growth = await _growth_data_last_days(7)
    chart = _growth_chart_text(growth)

    text = (
        "📈 <b>Kengaytirilgan statistika</b>\n\n"
        f"👥 Jami userlar: <b>{fmt_num(total_users)}</b>\n"
        f"💎 Pulli obunalar: <b>{fmt_num(paid)}</b>\n"
        f"📊 Konversiya: <b>{conversion}</b>\n"
        f"💰 Jami tushum: <b>{fmt_price(revenue)}</b>\n"
        f"⏳ Pending to'lov: <b>{pending}</b>\n"
        f"🛡 Adminlar: <b>{admins}</b>\n\n"
        f"📈 <b>Oxirgi 7 kunlik o'sish:</b>\n{chart}"
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📥 Userlar CSV", callback_data="adm:export_users"),
                InlineKeyboardButton(text="📄 HTML hisobot", callback_data="adm:stats_html"),
            ],
            [InlineKeyboardButton(text="🔙 Dashboard", callback_data="adm:back")],
        ]
    )

    if isinstance(target, CallbackQuery):
        await safe_edit(target, text, reply_markup=kb)
        await safe_answer_callback(target)
    else:
        await safe_reply(target, text, reply_markup=kb)


async def _send_stats_html(callback: CallbackQuery, db_user: dict | None = None) -> None:
    total_users, paid, pending, revenue = await _get_admin_overview()
    conversion = f"{(paid / total_users * 100):.1f}%" if total_users else "0%"
    growth = await _growth_data_last_days(7)
    top_users = await _get_top_users(20)
    html = build_admin_stats_report(
        summary={
            "total_users": total_users,
            "paid_users": paid,
            "pending_payments": pending,
            "revenue": fmt_price(revenue),
            "conversion": conversion,
        },
        growth=growth,
        top_users=top_users,
        generated_by=(db_user or {}).get("first_name", ""),
    )
    document = BufferedInputFile(html.encode("utf-8"), filename="admin_stats_report.html")
    await callback.bot.send_document(
        chat_id=callback.from_user.id,
        document=document,
        caption="📄 Admin statistika HTML hisobot",
    )


async def _send_user_html(callback: CallbackQuery, target_user_id: int, db_user: dict | None = None) -> None:
    user = await user_dao.get_user(target_user_id)
    if not user:
        await safe_answer_callback(callback, "❌ User topilmadi.", show_alert=True)
        return
    stats = await stats_dao.get_stats(target_user_id)
    usage = await stats_dao.get_usage_today(target_user_id)
    plan = await subscription_dao.get_active_plan_name(target_user_id)
    remain = await subscription_dao.remaining_days(target_user_id)

    html = build_admin_user_report(
        user=user,
        stats=stats,
        plan_name=plan,
        remaining_days=remain,
        usage_today=usage,
        generated_by=(db_user or {}).get("first_name", ""),
    )
    document = BufferedInputFile(html.encode("utf-8"), filename=f"user_{target_user_id}_report.html")
    await callback.bot.send_document(
        chat_id=callback.from_user.id,
        document=document,
        caption=f"📄 User #{target_user_id} HTML hisobot",
    )


async def _render_plans(target: Message | CallbackQuery) -> None:
    try:
        plans = await subscription_dao.get_all_plans()
    except Exception:
        plans = []

    text_lines = ["⚙️ <b>Tarif rejalar</b>", ""]
    buttons: list[list[InlineKeyboardButton]] = []
    if plans:
        for plan in plans:
            name = plan.get("name", "?")
            text_lines.append(
                f"• <b>{escape_html(plan.get('display_name', name))}</b> — {fmt_price(plan.get('price_monthly', 0))}/oy"
            )
            buttons.append([InlineKeyboardButton(text=f"✏️ {name.title()} narxini tahrirlash", callback_data=f"adm_edit_plan:{name}")])
    else:
        text_lines.append("<i>Rejalar topilmadi.</i>")

    buttons.append([InlineKeyboardButton(text="🔙 Dashboard", callback_data="adm:back")])
    text = "\n".join(text_lines)
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    if isinstance(target, CallbackQuery):
        await safe_edit(target, text, reply_markup=kb)
        await safe_answer_callback(target)
    else:
        await safe_reply(target, text, reply_markup=kb)


async def _render_leaderboard(target: Message | CallbackQuery) -> None:
    leaders = await leaderboard_dao.get_global_leaderboard(limit=15)
    if not leaders:
        text = "🏆 <b>Reyting</b>\n\nHali ma'lumot yo'q."
    else:
        lines = ["🏆 <b>Global reyting (Top 15)</b>", ""]
        for index, row in enumerate(leaders, 1):
            name = escape_html(str(row.get("first_name") or row.get("username") or row.get("user_id")))
            score = int(row.get("learning_score", 0) or 0)
            xp = int(row.get("total_xp", 0) or 0)
            lines.append(f"{index}. {name} — <b>{fmt_num(score)}</b> LS | XP: <b>{fmt_num(xp)}</b>")
        text = "\n".join(lines)

    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Dashboard", callback_data="adm:back")]])
    if isinstance(target, CallbackQuery):
        await safe_edit(target, text, reply_markup=kb)
        await safe_answer_callback(target)
    else:
        await safe_reply(target, text, reply_markup=kb)


@router.message(Command("admin"))
@router.message(F.text == "🛡 Admin Panel")
async def cmd_admin(message: Message, db_user: dict | None = None):
    await _ensure_admin_reply_menu(message)
    await _render_dashboard(message)


@router.message(F.text == "💳 To'lovlar")
async def _btn_adm_payments(message: Message, db_user: dict | None = None):
    await _render_payments(message)


@router.message(F.text == "👥 Foydalanuvchilar")
async def _btn_adm_users(message: Message, db_user: dict | None = None):
    await _render_users_home(message)


@router.message(F.text == "📢 Broadcast")
async def _btn_adm_broadcast(message: Message, db_user: dict | None = None, state: FSMContext | None = None):
    if state:
        await state.set_state(BROADCAST_STATE)
    await safe_reply(
        message,
        "📢 <b>Broadcast rejimi</b>\n\n"
        "Xabar matnini kiriting yoki tayyor postni <b>forward</b> qiling.\n"
        "Bekor qilish: <code>bekor</code>",
    )


@router.message(F.text == "📈 Statistika")
async def _btn_adm_stats(message: Message, db_user: dict | None = None):
    await _render_stats(message, generated_by=(db_user or {}).get("first_name", ""))


@router.message(F.text == "⚙️ Rejalar")
async def _btn_adm_plans(message: Message, db_user: dict | None = None):
    await _render_plans(message)


@router.message(F.text == "🏆 Reyting")
async def _btn_adm_leaderboard(message: Message, db_user: dict | None = None):
    await _render_leaderboard(message)


@router.message(F.text == "🔙 Asosiy Menyu")
async def _btn_adm_back(message: Message, db_user: dict | None = None):
    from src.bot.keyboards.user_menu import user_main_menu

    plan_name = await subscription_dao.get_active_plan_name(db_user["user_id"]) if db_user else "free"
    role = db_user.get("role", "user") if db_user else "user"
    await safe_reply(message, "🔙 Asosiy menyuga qaytildi.", reply_markup=user_main_menu(plan_name, role))


@router.callback_query(F.data == "adm:payments")
async def callback_admin_payments(callback: CallbackQuery, db_user: dict | None = None):
    await _render_payments(callback)


@router.callback_query(F.data == "adm:users")
async def callback_admin_users(callback: CallbackQuery, db_user: dict | None = None):
    await _render_users_home(callback)


@router.callback_query(F.data == "adm:users_search")
async def callback_users_search(callback: CallbackQuery, state: FSMContext):
    await state.set_state(USER_SEARCH_STATE)
    await safe_edit(
        callback,
        "🔎 <b>User qidirish</b>\n\n"
        "ID yoki @username yuboring.\n"
        "Bekor qilish: <code>bekor</code>",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="❌ Bekor", callback_data="adm:users")]]
        ),
    )
    await safe_answer_callback(callback)


@router.callback_query(F.data.startswith("adm:users_list:"))
async def callback_users_list(callback: CallbackQuery, db_user: dict | None = None):
    try:
        offset = int((callback.data or "0").split(":")[-1])
    except ValueError:
        offset = 0
    await _render_users_list(callback, offset=offset)


@router.callback_query(F.data.startswith("adm:user:"))
async def callback_user_card(callback: CallbackQuery, db_user: dict | None = None):
    try:
        target_user_id = int((callback.data or "").split(":")[-1])
    except ValueError:
        await safe_answer_callback(callback, "❌ Noto'g'ri user ID.", show_alert=True)
        return
    await _render_user_card(callback, target_user_id)


@router.callback_query(F.data.startswith("adm:userhtml:"))
async def callback_user_html(callback: CallbackQuery, db_user: dict | None = None):
    try:
        target_user_id = int((callback.data or "").split(":")[-1])
    except ValueError:
        await safe_answer_callback(callback, "❌ Noto'g'ri user ID.", show_alert=True)
        return
    await safe_answer_callback(callback, "📄 HTML hisobot tayyorlanmoqda...")
    await _send_user_html(callback, target_user_id, db_user=db_user)


@router.message(StateFilter(USER_SEARCH_STATE), F.text.regexp(r"(?i)^(bekor|cancel)$"))
async def message_user_search_cancel(message: Message, state: FSMContext):
    await state.clear()
    await safe_reply(message, "❌ Qidiruv bekor qilindi.")


@router.message(StateFilter(USER_SEARCH_STATE), F.text)
async def message_user_search_apply(message: Message, state: FSMContext):
    query = message.text.strip()
    user = await user_dao.find_user_by_username(query[1:]) if query.startswith("@") else (await user_dao.get_user(int(query)) if query.isdigit() else None)
    if not user:
        await safe_reply(message, "❌ User topilmadi. ID yoki @username yuboring.")
        return
    await state.clear()
    await _render_user_card(message, int(user["user_id"]))


@router.callback_query(F.data == "adm:broadcast")
async def callback_admin_broadcast(callback: CallbackQuery, state: FSMContext | None = None, db_user: dict | None = None):
    if state:
        await state.set_state(BROADCAST_STATE)
    await safe_edit(
        callback,
        "📢 <b>Broadcast rejimi</b>\n\n"
        "Xabar matnini kiriting yoki tayyor postni <b>forward</b> qiling.\n"
        "Bekor qilish: <code>bekor</code>",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🔙 Dashboard", callback_data="adm:back")]]
        ),
    )
    await safe_answer_callback(callback)


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, state: FSMContext, db_user: dict | None = None):
    if not db_user:
        return
    text = _extract_broadcast_text(message.text)
    if not text:
        await state.set_state(BROADCAST_STATE)
        await safe_reply(
            message,
            "📢 <b>Broadcast rejimi yoqildi.</b>\n\n"
            "Xabar matnini yuboring yoki postni <b>forward</b> qiling.\n"
            "Bekor qilish: <code>bekor</code>",
        )
        return
    await state.clear()
    await _run_broadcast(message, text=text)


@router.message(StateFilter(BROADCAST_STATE), F.text.regexp(r"(?i)^(bekor|cancel)$"))
async def _cancel_broadcast_input(message: Message, state: FSMContext, db_user: dict | None = None):
    await state.clear()
    await safe_reply(message, "❌ Broadcast bekor qilindi.")


@router.message(StateFilter(BROADCAST_STATE))
async def _handle_broadcast_input(message: Message, state: FSMContext, db_user: dict | None = None):
    if message.text and message.text.startswith("/"):
        await safe_reply(
            message,
            "⚠️ Xabar matnini kiriting yoki tayyor postni forward qiling.\n"
            "Bekor qilish: <code>bekor</code>",
        )
        return
    await state.clear()
    await _run_broadcast(message, source_message=message)


@router.callback_query(F.data == "adm:stats")
async def callback_admin_stats(callback: CallbackQuery, db_user: dict | None = None):
    await _render_stats(callback, generated_by=(db_user or {}).get("first_name", ""))


@router.callback_query(F.data == "adm:stats_html")
async def callback_admin_stats_html(callback: CallbackQuery, db_user: dict | None = None):
    await safe_answer_callback(callback, "📄 HTML hisobot tayyorlanmoqda...")
    await _send_stats_html(callback, db_user=db_user)


@router.callback_query(F.data == "adm:plans")
async def callback_admin_plans(callback: CallbackQuery, db_user: dict | None = None):
    await _render_plans(callback)


@router.callback_query(F.data.startswith("adm_edit_plan:"))
async def callback_adm_edit_plan(callback: CallbackQuery, state: FSMContext, db_user: dict | None = None):
    plan_name = callback.data.split(":")[1]
    await state.set_state(PLAN_EDIT_STATE)
    await state.update_data(edit_plan_name=plan_name)
    await safe_edit(
        callback,
        f"✏️ <b>{plan_name.title()}</b> rejasini tahrirlash.\n\n"
        "Yangi oylik narxni kiriting.\n"
        "<i>Bekor qilish uchun 'bekor' deb yozing.</i>",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🔙 Rejalar", callback_data="adm:plans")]]
        ),
    )
    await safe_answer_callback(callback)


@router.message(StateFilter(PLAN_EDIT_STATE), F.text.regexp(r"(?i)^(bekor|\d+(\.\d+)?)$"))
async def _handle_admin_edit_plan_price(message: Message, state: FSMContext, db_user: dict | None = None):
    if message.text.lower() == "bekor":
        await state.clear()
        await safe_reply(message, "❌ Tahrirlash bekor qilindi.")
        return

    try:
        new_price = float(message.text.strip())
        if new_price < 0:
            raise ValueError
    except ValueError:
        await safe_reply(message, "❌ Faqat musbat son kiriting. Masalan: 59000")
        return

    data = await state.get_data()
    plan_name = data.get("edit_plan_name")
    if not plan_name:
        await state.clear()
        return

    await subscription_dao.update_plan_field(plan_name, "price_monthly", new_price)
    await subscription_dao.update_plan_field(plan_name, "price_yearly", new_price * 10)
    await state.clear()
    await safe_reply(message, f"✅ <b>{plan_name.title()}</b> narxi {fmt_price(new_price)}/oy etib belgilandi.")


@router.callback_query(F.data == "adm:leaderboard")
async def callback_admin_leaderboard(callback: CallbackQuery, db_user: dict | None = None):
    await _render_leaderboard(callback)


@router.callback_query(F.data == "adm:admins")
async def callback_admin_admins(callback: CallbackQuery, db_user: dict | None = None):
    from src.bot.handlers.admin.management import _render_admins_panel

    await _render_admins_panel(callback, current_admin_id=(db_user or {}).get("user_id"))


@router.callback_query(F.data == "adm:payment_settings")
async def callback_admin_payment_settings(callback: CallbackQuery, db_user: dict | None = None):
    from src.bot.handlers.admin.management import _render_payment_config_panel

    await _render_payment_config_panel(callback)


@router.callback_query(F.data == "adm:sponsors")
async def callback_admin_sponsors(callback: CallbackQuery, db_user: dict | None = None):
    from src.bot.handlers.admin.management import _render_sponsors_panel

    await _render_sponsors_panel(callback)


@router.callback_query(F.data.startswith("admin_approve:"))
async def callback_approve_payment(callback: CallbackQuery, db_user: dict | None = None):
    if not db_user:
        return

    payment_id = int(callback.data.split(":")[1])
    payment = await payment_dao.get_payment(payment_id)
    if not payment or payment["status"] != "pending":
        await safe_answer_callback(callback, "❌ To'lov topilmadi yoki allaqachon ko'rib chiqilgan", show_alert=True)
        return

    await payment_dao.approve_payment(payment_id, db_user["user_id"])
    await subscription_dao.activate_subscription(
        user_id=payment["user_id"],
        plan_name=payment["plan_name"],
        days=payment.get("duration_days", 30),
    )

    from src.bot.loader import bot

    try:
        await bot.send_message(
            payment["user_id"],
            "🎉 <b>To'lov tasdiqlandi!</b>\n\n"
            f"📋 Reja: <b>{payment['plan_name'].title()}</b>\n"
            f"📅 Davomiylik: <b>{payment.get('duration_days', 30)} kun</b>\n\n"
            "Botdan to'liq foydalanishingiz mumkin.",
        )
    except Exception as exc:
        logger.warning("Failed to notify user %s: %s", payment["user_id"], exc)

    await safe_answer_callback(callback, f"✅ To'lov #{payment_id} tasdiqlandi!")
    await _render_payments(callback)


@router.callback_query(F.data.startswith("admin_reject:"))
async def callback_reject_payment(callback: CallbackQuery, db_user: dict | None = None):
    if not db_user:
        return

    payment_id = int(callback.data.split(":")[1])
    payment = await payment_dao.get_payment(payment_id)
    if not payment or payment["status"] != "pending":
        await safe_answer_callback(callback, "❌ To'lov topilmadi", show_alert=True)
        return

    await payment_dao.reject_payment(payment_id, db_user["user_id"], "Admin rejected")

    from src.bot.loader import bot

    try:
        await bot.send_message(
            payment["user_id"],
            "❌ <b>To'lov rad etildi</b>\n\n"
            f"To'lov #{payment_id} admin tomonidan rad etildi.\n"
            "Muammo bo'lsa, admin bilan bog'laning.",
        )
    except Exception:
        pass

    await safe_answer_callback(callback, f"❌ To'lov #{payment_id} rad etildi")
    await _render_payments(callback)


@router.callback_query(F.data.startswith("adm_user:"))
async def callback_adm_user_action(callback: CallbackQuery, db_user: dict | None = None):
    _, action, target_id_raw = callback.data.split(":")
    target_id = int(target_id_raw)

    if action == "ban":
        await user_dao.ban_user(target_id, 1)
        await safe_answer_callback(callback, "🚫 User ban qilindi")
    elif action == "unban":
        await user_dao.ban_user(target_id, 0)
        await safe_answer_callback(callback, "✅ User bandan olindi")
    elif action in {"free", "pro", "premium"}:
        days = 30 if action in {"pro", "premium"} else 0
        await subscription_dao.activate_subscription(target_id, action, days)
        await safe_answer_callback(callback, f"⭐ {action.title()} obunasi berildi")
    else:
        await safe_answer_callback(callback, "❌ Noma'lum amal", show_alert=True)
        return

    await _render_user_card(callback, target_id)


@router.callback_query(F.data == "adm:export_users")
async def callback_export_users(callback: CallbackQuery, db_user: dict | None = None):
    await safe_answer_callback(callback, "CSV tayyorlanmoqda...")
    db = await get_db()
    cursor = await db.execute("SELECT * FROM users")
    users = await cursor.fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    if users:
        first = dict(users[0])
        writer.writerow(first.keys())
        for row in users:
            writer.writerow(dict(row).values())

    document = BufferedInputFile(output.getvalue().encode("utf-8"), filename="users_export.csv")
    await callback.bot.send_document(
        chat_id=callback.from_user.id,
        document=document,
        caption="📊 Foydalanuvchilar ro'yxati (CSV)",
    )


@router.callback_query(F.data == "adm:back")
@router.callback_query(F.data == "adm:home")
async def callback_admin_back(callback: CallbackQuery, db_user: dict | None = None):
    await _render_dashboard(callback)


@router.callback_query(F.data.startswith("admin:"))
async def callback_admin_legacy(callback: CallbackQuery, state: FSMContext | None = None, db_user: dict | None = None):
    data = callback.data or ""
    mapping = {
        "admin:payments": callback_admin_payments,
        "admin:users": callback_admin_users,
        "admin:broadcast": callback_admin_broadcast,
        "admin:stats": callback_admin_stats,
        "admin:plans": callback_admin_plans,
        "admin:leaderboard": callback_admin_leaderboard,
        "admin:admins": callback_admin_admins,
        "admin:payment_settings": callback_admin_payment_settings,
        "admin:sponsors": callback_admin_sponsors,
        "admin:back": callback_admin_back,
    }
    handler = mapping.get(data)
    if not handler:
        await safe_answer_callback(callback, "⚠️ Eski tugma. /admin ni qayta bosing.", show_alert=True)
        return
    if handler is callback_admin_broadcast:
        await handler(callback, state=state, db_user=db_user)
    else:
        await handler(callback, db_user=db_user)


@router.callback_query(F.data.startswith("adm:"))
async def callback_admin_unknown_adm(callback: CallbackQuery, db_user: dict | None = None):
    """Catch stale inline buttons and recover to dashboard instead of doing nothing."""
    await safe_answer_callback(callback, "⚠️ Tugma eskirgan. Dashboard yangilandi.")
    await _render_dashboard(callback)


@router.callback_query(F.data.startswith("admin_"))
async def callback_admin_unknown_legacy_inline(callback: CallbackQuery, db_user: dict | None = None):
    """Catch stale legacy inline buttons (except known approve/reject handlers)."""
    await safe_answer_callback(callback, "⚠️ Tugma eskirgan. Dashboard yangilandi.")
    await _render_dashboard(callback)


def get_admin_router() -> Router:
    return router
