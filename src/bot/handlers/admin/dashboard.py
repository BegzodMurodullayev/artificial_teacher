"""
Admin dashboard handler — /admin, stats, payment management, broadcast, user management.
"""

import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from src.bot.filters.role import RoleFilter
from src.bot.utils.telegram import safe_reply, safe_edit, safe_answer_callback, escape_html, fmt_num, fmt_price
from src.database.dao import user_dao, payment_dao, subscription_dao, stats_dao

logger = logging.getLogger(__name__)
router = Router(name="admin")

# Apply role filter to all handlers in this router
router.message.filter(RoleFilter("admin", "owner"))
router.callback_query.filter(RoleFilter("admin", "owner"))


@router.message(Command("admin"))
async def cmd_admin(message: Message, db_user: dict | None = None):
    """Show admin dashboard."""
    try:
        total_users = await user_dao.count_users()
        paid_users = await subscription_dao.count_paid_users()
        pending = await payment_dao.count_pending_payments()
        revenue = await payment_dao.get_total_revenue()
    except Exception as e:
        logger.error("Admin dashboard DB error: %s", e)
        await safe_reply(message, "⚠️ Server xatosi. Iltimos qayta urinib ko'ring.")
        return

    conversion = f"{(paid_users / total_users * 100):.1f}%" if total_users > 0 else "0%"

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
    # Simulate inline callback behavior or just call logic
    payments = await payment_dao.get_pending_payments()
    if not payments:
        await safe_reply(message, "✅ <b>Kutilayotgan to'lovlar yo'q.</b>")
        return
    text = f"💳 <b>Kutilayotgan to'lovlar ({len(payments)})</b>\n\n"
    buttons = []
    for p in payments[:10]:
        user = await user_dao.get_user(p["user_id"])
        name = escape_html((user or {}).get("first_name", "?"))
        text += f"#{p['id']} | {name} (ID: {p['user_id']})\n  📋 {p['plan_name'].title()} | {fmt_price(p['amount'])} | {p['duration_days']} kun\n\n"
        buttons.append([
            InlineKeyboardButton(text=f"✅ #{p['id']}", callback_data=f"admin_approve:{p['id']}"),
            InlineKeyboardButton(text=f"❌ #{p['id']}", callback_data=f"admin_reject:{p['id']}"),
        ])
    await safe_reply(message, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.message(F.text == "👥 Foydalanuvchilar")
async def _btn_adm_users(message: Message, db_user: dict | None = None):
    await safe_reply(message, "👥 <b>Foydalanuvchi qidirish</b>\n\nUser ID yoki @username yuboring.\nFormatlar:\n• <code>123456789</code>\n• <code>@username</code>")

@router.message(F.text == "📢 Broadcast")
async def _btn_adm_broadcast(message: Message, db_user: dict | None = None):
    await safe_reply(message, "📢 <b>Broadcast</b>\n\nBarcha foydalanuvchilarga xabar yuborish uchun:\n\n<code>/broadcast Xabar matni</code>")

@router.message(F.text == "📈 Statistika")
async def _btn_adm_stats(message: Message, db_user: dict | None = None):
    total_users = await user_dao.count_users()
    paid = await subscription_dao.count_paid_users()
    revenue = await payment_dao.get_total_revenue()
    admins = await user_dao.count_users_by_role("admin")
    text = f"📈 <b>Global Statistika</b>\n\n👥 Jami userlar: <b>{fmt_num(total_users)}</b>\n💎 Pulli obunalar: <b>{fmt_num(paid)}</b>\n💰 Jami tushum: <b>{fmt_price(revenue)}</b>\n🛡 Adminlar: <b>{admins}</b>\n"
    await safe_reply(message, text)

@router.message(F.text == "🔙 Asosiy Menyu")
async def _btn_adm_back(message: Message, db_user: dict | None = None):
    from src.bot.keyboards.user_menu import user_main_menu
    plan_name = await subscription_dao.get_active_plan_name(db_user["user_id"]) if db_user else "free"
    role = db_user.get("role", "user") if db_user else "user"
    await safe_reply(message, "🔙 Asosiy menyuga qaytildi.", reply_markup=user_main_menu(plan_name, role))

@router.message(F.text == "⚙️ Rejalar")
async def _btn_adm_plans(message: Message, db_user: dict | None = None):
    try:
        from src.database.dao.subscription_dao import get_all_plans
        plans = await get_all_plans() if hasattr(subscription_dao, 'get_all_plans') else []
    except Exception:
        plans = []
    
    text = "⚙️ <b>Tarif Rejalar</b>\n\n"
    if plans:
        for p in plans:
            text += f"• <b>{escape_html(p.get('display_name', p.get('name', '?')))}</b> — {fmt_price(p.get('price_monthly', 0))}/oy\n"
    else:
        text += (
            "⭐ Free — Bepul\n"
            "⭐ Standard — 29,000 so'm/oy\n"
            "💸 Pro — 59,000 so'm/oy\n"
            "👑 Premium — 99,000 so'm/oy\n"
        )
    text += "\n/admin buyrug'i bilan dashboardga qaytish."
    await safe_reply(message, text)

@router.message(F.text == "🏆 Reyting")
async def _btn_adm_leaderboard(message: Message, db_user: dict | None = None):
    try:
        from src.database.dao.stats_dao import get_leaderboard
        leaders = await stats_dao.get_leaderboard(limit=10) if hasattr(stats_dao, 'get_leaderboard') else []
    except Exception:
        leaders = []
    
    if leaders:
        text = "🏆 <b>Top 10 O'yinchilar</b>\n\n"
        for i, row in enumerate(leaders, 1):
            name = escape_html(str(row.get("first_name", row.get("user_id", "?"))))
            score = row.get("score", row.get("total_points", 0))
            text += f"{i}. {name} — <b>{fmt_num(score)}</b> ball\n"
    else:
        text = "🏆 <b>Reyting</b>\n\nHali ma'lumot yo'q."
    
    await safe_reply(message, text)

@router.callback_query(F.data == "adm:payments")
async def callback_admin_payments(callback: CallbackQuery, db_user: dict | None = None):
    """Show pending payments."""
    payments = await payment_dao.get_pending_payments()

    if not payments:
        await safe_edit(callback, "✅ <b>Kutilayotgan to'lovlar yo'q.</b>")
        await safe_answer_callback(callback)
        return

    text = f"💳 <b>Kutilayotgan to'lovlar ({len(payments)})</b>\n\n"
    buttons = []

    for p in payments[:10]:
        user = await user_dao.get_user(p["user_id"])
        name = escape_html((user or {}).get("first_name", "?"))
        text += (
            f"#{p['id']} | {name} (ID: {p['user_id']})\n"
            f"  📋 {p['plan_name'].title()} | {fmt_price(p['amount'])} | {p['duration_days']} kun\n\n"
        )
        buttons.append([
            InlineKeyboardButton(text=f"✅ #{p['id']}", callback_data=f"admin_approve:{p['id']}"),
            InlineKeyboardButton(text=f"❌ #{p['id']}", callback_data=f"admin_reject:{p['id']}"),
        ])

    buttons.append([InlineKeyboardButton(text="🔙 Dashboard", callback_data="adm:back")])
    await safe_edit(callback, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await safe_answer_callback(callback)


@router.callback_query(F.data.startswith("admin_approve:"))
async def callback_approve_payment(callback: CallbackQuery, db_user: dict | None = None):
    """Approve a payment."""
    if not db_user:
        return

    payment_id = int(callback.data.split(":")[1])
    payment = await payment_dao.get_payment(payment_id)

    if not payment or payment["status"] != "pending":
        await safe_answer_callback(callback, "❌ To'lov topilmadi yoki allaqachon ko'rib chiqilgan", show_alert=True)
        return

    admin_id = db_user["user_id"]

    # Approve payment
    await payment_dao.approve_payment(payment_id, admin_id)

    # Activate subscription
    await subscription_dao.activate_subscription(
        user_id=payment["user_id"],
        plan_name=payment["plan_name"],
        days=payment.get("duration_days", 30),
    )

    # Notify user
    from src.bot.loader import bot
    plan_display = payment["plan_name"].title()
    try:
        await bot.send_message(
            payment["user_id"],
            f"🎉 <b>To'lov tasdiqlandi!</b>\n\n"
            f"📋 Reja: <b>{plan_display}</b>\n"
            f"📅 Davomiylik: <b>{payment.get('duration_days', 30)} kun</b>\n\n"
            f"Botdan to'liq foydalanishingiz mumkin! 🚀",
        )
    except Exception as e:
        logger.warning("Failed to notify user %s about approval: %s", payment["user_id"], e)

    await safe_answer_callback(callback, f"✅ To'lov #{payment_id} tasdiqlandi!")
    await safe_edit(
        callback,
        f"✅ <b>To'lov #{payment_id} tasdiqlandi!</b>\n"
        f"User: {payment['user_id']} → {plan_display}\n"
        f"Admin: {admin_id}",
    )


@router.callback_query(F.data.startswith("admin_reject:"))
async def callback_reject_payment(callback: CallbackQuery, db_user: dict | None = None):
    """Reject a payment."""
    if not db_user:
        return

    payment_id = int(callback.data.split(":")[1])
    payment = await payment_dao.get_payment(payment_id)

    if not payment or payment["status"] != "pending":
        await safe_answer_callback(callback, "❌ To'lov topilmadi", show_alert=True)
        return

    await payment_dao.reject_payment(payment_id, db_user["user_id"], "Admin rejected")

    # Notify user
    from src.bot.loader import bot
    try:
        await bot.send_message(
            payment["user_id"],
            f"❌ <b>To'lov rad etildi</b>\n\n"
            f"To'lov #{payment_id} admin tomonidan rad etildi.\n"
            f"Muammo bo'lsa, admin bilan bog'laning.",
        )
    except Exception:
        pass

    await safe_answer_callback(callback, f"❌ To'lov #{payment_id} rad etildi")
    await safe_edit(callback, f"❌ <b>To'lov #{payment_id} rad etildi.</b>")


# ── User Management ──

@router.callback_query(F.data == "adm:users")
async def callback_admin_users(callback: CallbackQuery, db_user: dict | None = None):
    """Show user search prompt."""
    await safe_edit(
        callback,
        "👥 <b>Foydalanuvchi qidirish</b>\n\n"
        "User ID yoki @username yuboring.\n"
        "Formatlar:\n"
        "• <code>123456789</code> (ID)\n"
        "• <code>@username</code>\n\n"
        "Yoki /admin buyrug'i bilan qaytish.",
    )
    await safe_answer_callback(callback)


# ── Broadcast ──

@router.callback_query(F.data == "adm:broadcast")
async def callback_admin_broadcast(callback: CallbackQuery, db_user: dict | None = None):
    """Show broadcast instructions."""
    await safe_edit(
        callback,
        "📢 <b>Broadcast</b>\n\n"
        "Barcha foydalanuvchilarga xabar yuborish uchun:\n\n"
        "<code>/broadcast Xabar matni</code>\n\n"
        "⚠️ Bu barcha aktiv foydalanuvchilarga yuboriladi.",
    )
    await safe_answer_callback(callback)


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, db_user: dict | None = None):
    """Send broadcast message to all users."""
    if not db_user:
        return

    text = message.text.replace("/broadcast", "", 1).strip()
    if not text:
        await safe_reply(message, "⚠️ Xabar matni kerak.\n<code>/broadcast Salom!</code>")
        return

    from src.bot.loader import bot
    user_ids = await user_dao.get_all_user_ids()
    total = len(user_ids)
    sent = 0
    failed = 0

    status_msg = await safe_reply(message, f"📢 Broadcast boshlanmoqda... 0/{total}")

    for i, uid in enumerate(user_ids):
        try:
            await bot.send_message(uid, text)
            sent += 1
        except Exception:
            failed += 1

        # Update progress every 50 users
        if (i + 1) % 50 == 0 and status_msg:
            try:
                await status_msg.edit_text(
                    f"📢 Broadcast: {sent + failed}/{total}\n"
                    f"✅ Yuborildi: {sent}\n❌ Xato: {failed}"
                )
            except Exception:
                pass

    if status_msg:
        try:
            await status_msg.edit_text(
                f"📢 <b>Broadcast yakunlandi!</b>\n\n"
                f"📊 Jami: {total}\n"
                f"✅ Yuborildi: {sent}\n"
                f"❌ Xato: {failed}"
            )
        except Exception:
            pass


# ── Stats ──

@router.callback_query(F.data == "adm:stats")
async def callback_admin_stats(callback: CallbackQuery, db_user: dict | None = None):
    """Show global statistics."""
    total_users = await user_dao.count_users()
    paid = await subscription_dao.count_paid_users()
    revenue = await payment_dao.get_total_revenue()
    admins = await user_dao.count_users_by_role("admin")

    text = (
        "📈 <b>Global Statistika</b>\n\n"
        f"👥 Jami userlar: <b>{fmt_num(total_users)}</b>\n"
        f"💎 Pulli obunalar: <b>{fmt_num(paid)}</b>\n"
        f"💰 Jami tushum: <b>{fmt_price(revenue)}</b>\n"
        f"🛡 Adminlar: <b>{admins}</b>\n"
    )

    buttons = [[InlineKeyboardButton(text="🔙 Dashboard", callback_data="adm:back")]]
    await safe_edit(callback, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await safe_answer_callback(callback)


@router.callback_query(F.data == "adm:back")
async def callback_admin_back(callback: CallbackQuery, db_user: dict | None = None):
    """Go back to admin dashboard."""
    await safe_answer_callback(callback)
    if callback.message:
        await cmd_admin(callback.message, db_user)


def get_admin_router() -> Router:
    return router
