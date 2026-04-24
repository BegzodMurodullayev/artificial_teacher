"""
Admin dashboard handler: admin menu, payments, users, broadcast, stats, and exports.
"""

import csv
import io
import logging
from collections import Counter
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
from src.bot.utils.telegram import (
    escape_html,
    fmt_num,
    fmt_price,
    safe_answer_callback,
    safe_edit,
    safe_reply,
)
from src.database.dao import payment_dao, stats_dao, subscription_dao, user_dao

logger = logging.getLogger(__name__)
router = Router(name="admin")

router.message.filter(RoleFilter("admin", "owner"))
router.callback_query.filter(RoleFilter("admin", "owner"))


async def _build_growth_chart() -> str:
    from src.database.connection import get_db

    db = await get_db()
    cursor = await db.execute("SELECT joined_at FROM users WHERE joined_at IS NOT NULL")
    rows = await cursor.fetchall()

    today = datetime.utcnow().date()
    last_7 = [today - timedelta(days=offset) for offset in range(6, -1, -1)]
    counts = Counter()

    for row in rows:
        value = row[0] if not isinstance(row, dict) else row.get("joined_at")
        if not value:
            continue
        try:
            joined = datetime.fromisoformat(str(value)[:19]).date()
        except ValueError:
            continue
        if joined in last_7:
            counts[joined] += 1

    max_count = max(counts.values(), default=1)
    lines = []
    for day in last_7:
        count = counts.get(day, 0)
        filled = int((count / max_count) * 10) if max_count else 0
        bar = "█" * filled + "░" * (10 - filled)
        lines.append(f"<code>{day.strftime('%m-%d')}</code> | {bar} <b>{count}</b>")
    return "\n".join(lines) if lines else "<i>Ma'lumot yo'q</i>"


async def _get_admin_overview() -> tuple[int, int, int, float]:
    total_users = await user_dao.count_users()
    paid_users = await subscription_dao.count_paid_users()
    pending = await payment_dao.count_pending_payments()
    revenue = await payment_dao.get_total_revenue()
    return total_users, paid_users, pending, revenue


@router.message(Command("admin"))
@router.message(F.text == "🛡 Admin Panel")
async def cmd_admin(message: Message, db_user: dict | None = None):
    """Show admin dashboard."""
    try:
        total_users, paid_users, pending, revenue = await _get_admin_overview()
    except Exception as exc:
        logger.error("Admin dashboard DB error: %s", exc)
        await safe_reply(message, "⚠️ Server xatosi. Iltimos, qayta urinib ko'ring.")
        return

    conversion = f"{(paid_users / total_users * 100):.1f}%" if total_users else "0%"
    text = (
        "🛡 <b>Admin Dashboard</b>\n\n"
        f"👥 Jami foydalanuvchilar: <b>{fmt_num(total_users)}</b>\n"
        f"💎 Pulli obunalar: <b>{fmt_num(paid_users)}</b>\n"
        f"📊 Konversiya: <b>{conversion}</b>\n"
        f"💰 Umumiy tushum: <b>{fmt_price(revenue)}</b>\n"
        f"⏳ Kutilayotgan to'lovlar: <b>{pending}</b>\n"
    )

    from src.bot.keyboards.user_menu import admin_main_menu

    await safe_reply(message, text, reply_markup=admin_main_menu())


@router.message(F.text == "💳 To'lovlar")
async def _btn_adm_payments(message: Message, db_user: dict | None = None):
    payments = await payment_dao.get_pending_payments()
    if not payments:
        await safe_reply(message, "✅ <b>Kutilayotgan to'lovlar yo'q.</b>")
        return

    text = [f"💳 <b>Kutilayotgan to'lovlar ({len(payments)})</b>", ""]
    buttons: list[list[InlineKeyboardButton]] = []
    for payment in payments[:10]:
        user = await user_dao.get_user(payment["user_id"])
        name = escape_html((user or {}).get("first_name", "?"))
        text.append(
            f"#{payment['id']} | {name} (ID: {payment['user_id']})\n"
            f"📋 {payment['plan_name'].title()} | {fmt_price(payment['amount'])} | {payment['duration_days']} kun\n"
        )
        buttons.append(
            [
                InlineKeyboardButton(text=f"✅ #{payment['id']}", callback_data=f"admin_approve:{payment['id']}"),
                InlineKeyboardButton(text=f"❌ #{payment['id']}", callback_data=f"admin_reject:{payment['id']}"),
            ]
        )

    await safe_reply(message, "\n".join(text), reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.message(F.text == "👥 Foydalanuvchilar")
async def _btn_adm_users(message: Message, db_user: dict | None = None):
    await safe_reply(
        message,
        "👥 <b>Foydalanuvchi qidirish</b>\n\n"
        "User ID yoki @username yuboring.\n"
        "Formatlar:\n"
        "• <code>123456789</code>\n"
        "• <code>@username</code>",
    )


@router.message(F.text == "📢 Broadcast")
async def _btn_adm_broadcast(message: Message, db_user: dict | None = None):
    await safe_reply(
        message,
        "📢 <b>Broadcast</b>\n\n"
        "Barcha foydalanuvchilarga xabar yuborish uchun:\n"
        "<code>/broadcast Xabar matni</code>",
    )


@router.message(F.text == "📈 Statistika")
async def _btn_adm_stats(message: Message, db_user: dict | None = None):
    total_users = await user_dao.count_users()
    paid = await subscription_dao.count_paid_users()
    revenue = await payment_dao.get_total_revenue()
    admins = await user_dao.count_users_by_role("admin")
    chart = await _build_growth_chart()

    text = (
        "📊 <b>Kengaytirilgan statistika</b>\n\n"
        f"👥 Jami userlar: <b>{fmt_num(total_users)}</b>\n"
        f"💎 Pulli obunalar: <b>{fmt_num(paid)}</b>\n"
        f"💰 Jami tushum: <b>{fmt_price(revenue)}</b>\n"
        f"🛡 Adminlar: <b>{admins}</b>\n\n"
        f"📈 <b>Oxirgi 7 kunlik o'sish:</b>\n{chart}"
    )

    buttons = [[InlineKeyboardButton(text="📥 Userlarni CSV export", callback_data="adm:export_users")]]
    await safe_reply(message, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.message(F.text == "🔙 Asosiy Menyu")
async def _btn_adm_back(message: Message, db_user: dict | None = None):
    from src.bot.keyboards.user_menu import user_main_menu

    plan_name = await subscription_dao.get_active_plan_name(db_user["user_id"]) if db_user else "free"
    role = db_user.get("role", "user") if db_user else "user"
    await safe_reply(message, "🔙 Asosiy menyuga qaytildi.", reply_markup=user_main_menu(plan_name, role))


@router.message(F.text == "⚙️ Rejalar")
async def _btn_adm_plans(message: Message, db_user: dict | None = None):
    try:
        plans = await subscription_dao.get_all_plans()
    except Exception:
        plans = []

    text = ["⚙️ <b>Tarif rejalar</b>", ""]
    buttons: list[list[InlineKeyboardButton]] = []
    if plans:
        for plan in plans:
            name = plan.get("name", "?")
            text.append(
                f"• <b>{escape_html(plan.get('display_name', name))}</b> — {fmt_price(plan.get('price_monthly', 0))}/oy"
            )
            buttons.append(
                [
                    InlineKeyboardButton(
                        text=f"✏️ {name.title()} narxini tahrirlash",
                        callback_data=f"adm_edit_plan:{name}",
                    )
                ]
            )
    else:
        text.extend(
            [
                "⭐ Free — Bepul",
                "⭐ Standard — 29,000 so'm/oy",
                "💎 Pro — 59,000 so'm/oy",
                "👑 Premium — 99,000 so'm/oy",
            ]
        )

    buttons.append([InlineKeyboardButton(text="🔙 Dashboard", callback_data="adm:back")])
    await safe_reply(message, "\n".join(text), reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("adm_edit_plan:"))
async def callback_adm_edit_plan(callback: CallbackQuery, state: FSMContext, db_user: dict | None = None):
    plan_name = callback.data.split(":")[1]
    await state.set_state("ADMIN_EDIT_PLAN_PRICE")
    await state.update_data(edit_plan_name=plan_name)
    await safe_edit(
        callback,
        f"✏️ <b>{plan_name.title()}</b> rejasini tahrirlash.\n\n"
        "Yangi oylik narxni kiriting.\n"
        "<i>Bekor qilish uchun 'bekor' deb yozing.</i>",
    )
    await safe_answer_callback(callback)


@router.message(StateFilter("ADMIN_EDIT_PLAN_PRICE"), F.text.regexp(r"^(bekor|\d+(\.\d+)?)$"))
async def _handle_admin_edit_plan_price(message: Message, state: FSMContext, db_user: dict | None = None):
    if message.text.lower() == "bekor":
        await state.clear()
        await safe_reply(message, "❌ Tahrirlash bekor qilindi.")
        await cmd_admin(message, db_user)
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
    await safe_reply(
        message,
        f"✅ <b>{plan_name.title()}</b> rejasining narxi {fmt_price(new_price)}/oy etib belgilandi.",
    )
    await cmd_admin(message, db_user)


@router.message(F.text == "🏆 Reyting")
async def _btn_adm_leaderboard(message: Message, db_user: dict | None = None):
    try:
        leaders = await stats_dao.get_leaderboard(limit=10) if hasattr(stats_dao, "get_leaderboard") else []
    except Exception:
        leaders = []

    if leaders:
        lines = ["🏆 <b>Top 10 o'yinchi</b>", ""]
        for index, row in enumerate(leaders, 1):
            name = escape_html(str(row.get("first_name", row.get("user_id", "?"))))
            score = row.get("score", row.get("total_points", 0))
            lines.append(f"{index}. {name} — <b>{fmt_num(score)}</b> ball")
        await safe_reply(message, "\n".join(lines))
        return

    await safe_reply(message, "🏆 <b>Reyting</b>\n\nHali ma'lumot yo'q.")


@router.callback_query(F.data == "adm:payments")
async def callback_admin_payments(callback: CallbackQuery, db_user: dict | None = None):
    payments = await payment_dao.get_pending_payments()
    if not payments:
        await safe_edit(callback, "✅ <b>Kutilayotgan to'lovlar yo'q.</b>")
        await safe_answer_callback(callback)
        return

    lines = [f"💳 <b>Kutilayotgan to'lovlar ({len(payments)})</b>", ""]
    buttons: list[list[InlineKeyboardButton]] = []
    for payment in payments[:10]:
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
    await safe_edit(callback, "\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await safe_answer_callback(callback)


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
    await safe_edit(
        callback,
        f"✅ <b>To'lov #{payment_id} tasdiqlandi!</b>\n"
        f"User: {payment['user_id']} → {payment['plan_name'].title()}\n"
        f"Admin: {db_user['user_id']}",
    )


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
    await safe_edit(callback, f"❌ <b>To'lov #{payment_id} rad etildi.</b>")


@router.callback_query(F.data == "adm:users")
async def callback_admin_users(callback: CallbackQuery, db_user: dict | None = None):
    await safe_edit(
        callback,
        "👥 <b>Foydalanuvchi qidirish</b>\n\n"
        "User ID yoki @username yuboring.\n"
        "Formatlar:\n"
        "• <code>123456789</code>\n"
        "• <code>@username</code>\n\n"
        "Yoki /admin buyrug'i bilan qayting.",
    )
    await safe_answer_callback(callback)


@router.message(F.text.regexp(r"^@[\w_]+$") | F.text.regexp(r"^\d{5,15}$"))
async def _search_user_admin(message: Message, db_user: dict | None = None):
    query = message.text.strip()
    user = await user_dao.find_user_by_username(query[1:]) if query.startswith("@") else await user_dao.get_user(int(query))
    if not user:
        await safe_reply(message, "❌ <b>Foydalanuvchi topilmadi.</b>")
        return

    plan = await subscription_dao.get_active_plan_name(user["user_id"])
    text = (
        "👤 <b>Foydalanuvchi profil</b>\n\n"
        f"ID: <code>{user['user_id']}</code>\n"
        f"Ism: {escape_html(user.get('first_name', '') or '-')}\n"
        f"Username: @{escape_html(user.get('username', '') or '-')}\n"
        f"Daraja: {escape_html(user.get('level', 'A1'))}\n"
        f"Rol: {escape_html(user.get('role', 'user'))}\n"
        f"Obuna: <b>{escape_html(plan)}</b>\n"
        f"Qo'shilgan: {escape_html(str(user.get('joined_at', ''))[:19])}\n"
        f"Holat: {'🚫 <b>Ban qilingan</b>' if user.get('is_banned') else '✅ <b>Aktiv</b>'}"
    )

    ban_action = "unban" if user.get("is_banned") else "ban"
    ban_text = "✅ Bandan olish" if user.get("is_banned") else "🚫 Ban qilish"
    buttons = [
        [InlineKeyboardButton(text=ban_text, callback_data=f"adm_user:{ban_action}:{user['user_id']}")],
        [InlineKeyboardButton(text="⭐ Free berish", callback_data=f"adm_user:free:{user['user_id']}")],
        [InlineKeyboardButton(text="💎 Pro berish (30 kun)", callback_data=f"adm_user:pro:{user['user_id']}")],
    ]
    await safe_reply(message, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


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
    elif action in {"free", "pro"}:
        days = 30 if action == "pro" else 0
        await subscription_dao.activate_subscription(target_id, action, days)
        await safe_answer_callback(callback, f"⭐ {action.title()} obunasi berildi")
    else:
        await safe_answer_callback(callback, "❌ Noma'lum amal", show_alert=True)
        return

    await safe_edit(callback, f"✅ Harakat bajarildi: <code>{target_id}</code> ({action})")


@router.callback_query(F.data == "adm:broadcast")
async def callback_admin_broadcast(callback: CallbackQuery, db_user: dict | None = None):
    await safe_edit(
        callback,
        "📢 <b>Broadcast</b>\n\n"
        "Barcha foydalanuvchilarga xabar yuborish uchun:\n"
        "<code>/broadcast Xabar matni</code>\n\n"
        "⚠️ Bu barcha aktiv foydalanuvchilarga yuboriladi.",
    )
    await safe_answer_callback(callback)


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, db_user: dict | None = None):
    if not db_user:
        return

    text = (message.text or "").replace("/broadcast", "", 1).strip()
    if not text:
        await safe_reply(message, "⚠️ Xabar matni kerak.\n<code>/broadcast Salom!</code>")
        return

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

    result = await send_broadcast(text, progress_callback=_progress)

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


@router.callback_query(F.data == "adm:stats")
async def callback_admin_stats(callback: CallbackQuery, db_user: dict | None = None):
    total_users = await user_dao.count_users()
    paid = await subscription_dao.count_paid_users()
    revenue = await payment_dao.get_total_revenue()
    admins = await user_dao.count_users_by_role("admin")
    chart = await _build_growth_chart()

    text = (
        "📊 <b>Kengaytirilgan statistika</b>\n\n"
        f"👥 Jami userlar: <b>{fmt_num(total_users)}</b>\n"
        f"💎 Pulli obunalar: <b>{fmt_num(paid)}</b>\n"
        f"💰 Jami tushum: <b>{fmt_price(revenue)}</b>\n"
        f"🛡 Adminlar: <b>{admins}</b>\n\n"
        f"📈 <b>Oxirgi 7 kunlik o'sish:</b>\n{chart}"
    )

    buttons = [
        [InlineKeyboardButton(text="📥 Userlarni CSV export", callback_data="adm:export_users")],
        [InlineKeyboardButton(text="🔙 Dashboard", callback_data="adm:back")],
    ]
    await safe_edit(callback, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await safe_answer_callback(callback)


@router.callback_query(F.data == "adm:export_users")
async def callback_export_users(callback: CallbackQuery, db_user: dict | None = None):
    await safe_answer_callback(callback, "CSV tayyorlanmoqda...")

    from src.database.connection import get_db
    from src.bot.loader import bot

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
    await bot.send_document(
        chat_id=callback.from_user.id,
        document=document,
        caption="📊 Foydalanuvchilar ro'yxati (CSV)",
    )


@router.callback_query(F.data == "adm:back")
async def callback_admin_back(callback: CallbackQuery, db_user: dict | None = None):
    await safe_answer_callback(callback)
    if callback.message:
        await cmd_admin(callback.message, db_user)


def get_admin_router() -> Router:
    return router
