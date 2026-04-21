"""
Subscription handlers — plan listing, payment flow, receipt handling.
"""

import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from src.bot.utils.telegram import safe_reply, safe_edit, safe_answer_callback, escape_html, fmt_price
from src.bot.keyboards.user_menu import subscription_plans_keyboard
from src.database.dao import subscription_dao, payment_dao, reward_dao

logger = logging.getLogger(__name__)
router = Router(name="subscription")


@router.message(Command("subscribe"))
async def cmd_subscribe(message: Message, db_user: dict | None = None):
    """Show subscription plans."""
    if not db_user:
        return
    await _show_plans(message, db_user)


async def _show_plans(message: Message, db_user: dict):
    """Display plan comparison."""
    user_id = db_user["user_id"]
    current = await subscription_dao.get_active_plan_name(user_id)
    remaining = await subscription_dao.remaining_days(user_id)
    plans = await subscription_dao.get_all_plans()

    text = "⭐ <b>Obuna Rejalari</b>\n\n"

    for plan in plans:
        name = plan["name"]
        display = plan.get("display_name", name.title())
        price = plan.get("price_monthly", 0)
        is_current = name == current

        # Marker for current plan
        marker = " ✅ (joriy)" if is_current else ""

        text += f"<b>{display}</b>{marker}\n"
        if price > 0:
            text += f"  💰 {fmt_price(price)}/oy\n"
        text += (
            f"  ✅ Tekshiruv: {plan.get('checks_per_day', 0)}/kun\n"
            f"  🧠 Quiz: {plan.get('quiz_per_day', 0)}/kun\n"
            f"  💬 AI xabar: {plan.get('ai_messages_day', 0)}/kun\n"
            f"  🔊 Talaffuz: {plan.get('pron_audio_per_day', 0)}/kun\n"
        )
        if plan.get("voice_enabled"):
            text += "  🎤 Ovozli xabar: ✅\n"
        if plan.get("inline_enabled"):
            text += "  ⚡ Inline rejim: ✅\n"
        if plan.get("iq_test_enabled"):
            text += "  🧩 IQ test: ✅\n"
        text += "\n"

    if current != "free" and remaining > 0:
        text += f"📅 <i>Obunangiz tugashiga {remaining} kun qoldi.</i>\n"

    await safe_reply(message, text, reply_markup=subscription_plans_keyboard())


@router.callback_query(F.data.startswith("plan:"))
async def callback_plan_select(callback: CallbackQuery, db_user: dict | None = None):
    """Handle plan selection."""
    if not db_user:
        return

    action = callback.data.split(":")[1]

    if action == "compare":
        await safe_answer_callback(callback)
        # Show comparison already in _show_plans
        return

    plan_name = action
    plan = await subscription_dao.get_plan(plan_name)
    if not plan:
        await safe_answer_callback(callback, "❌ Reja topilmadi", show_alert=True)
        return

    user_id = db_user["user_id"]
    display = plan.get("display_name", plan_name.title())

    # Duration selection
    monthly_price = plan.get("price_monthly", 0)
    yearly_price = plan.get("price_yearly", 0)

    buttons = [
        [InlineKeyboardButton(
            text=f"📅 1 oy — {fmt_price(monthly_price)}",
            callback_data=f"buy:{plan_name}:30",
        )],
        [InlineKeyboardButton(
            text=f"📅 1 yil — {fmt_price(yearly_price)} (-17%)",
            callback_data=f"buy:{plan_name}:365",
        )],
        [InlineKeyboardButton(text="🔙 Ortga", callback_data="back:plans")],
    ]

    text = (
        f"⭐ <b>{display}</b>\n\n"
        f"Davomiylikni tanlang:"
    )

    await safe_edit(callback, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await safe_answer_callback(callback)


@router.callback_query(F.data.startswith("buy:"))
async def callback_buy(callback: CallbackQuery, db_user: dict | None = None):
    """Handle purchase initiation."""
    if not db_user:
        return

    parts = callback.data.split(":")
    plan_name = parts[1]
    days = int(parts[2])

    plan = await subscription_dao.get_plan(plan_name)
    if not plan:
        await safe_answer_callback(callback, "❌ Reja topilmadi", show_alert=True)
        return

    user_id = db_user["user_id"]
    price = plan["price_monthly"] if days <= 30 else plan["price_yearly"]

    # Check for existing active subscription (upgrade credit)
    current_plan = await subscription_dao.get_active_plan_name(user_id)
    remaining = await subscription_dao.remaining_days(user_id)

    credit_text = ""
    if current_plan != "free" and remaining > 0:
        current_plan_data = await subscription_dao.get_plan(current_plan)
        if current_plan_data:
            daily_rate = current_plan_data["price_monthly"] / 30
            credit = daily_rate * remaining
            price = max(0, price - credit)
            credit_text = f"\n💳 Kredit (qolgan {remaining} kun): -{fmt_price(credit)}"

    # Get payment config
    from src.database.dao.reward_dao import get_config
    card_number = await get_config("payment_config", "card_number", "")
    card_holder = await get_config("payment_config", "card_holder", "")

    # Create pending payment
    payment_id = await payment_dao.create_payment(
        user_id=user_id,
        plan_name=plan_name,
        amount=price,
        duration_days=days,
        method="manual",
    )

    display = plan.get("display_name", plan_name.title())
    text = (
        f"💳 <b>To'lov #{payment_id}</b>\n\n"
        f"📋 Reja: <b>{display}</b>\n"
        f"📅 Davomiylik: <b>{days} kun</b>\n"
        f"💰 Summa: <b>{fmt_price(price)}</b>"
        f"{credit_text}\n\n"
    )

    if card_number:
        text += (
            f"💳 <b>To'lov ma'lumotlari:</b>\n"
            f"Karta: <code>{card_number}</code>\n"
        )
        if card_holder:
            text += f"Egasi: {escape_html(card_holder)}\n"
        text += (
            f"\n📸 <b>To'lov qilgach, chek rasmini shu yerga yuboring.</b>\n"
            f"Admin tez orada tasdiqlaydi."
        )
    else:
        text += "⚠️ To'lov ma'lumotlari hali sozlanmagan. Admin bilan bog'laning."

    buttons = [[InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"cancel_pay:{payment_id}")]]
    await safe_edit(callback, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await safe_answer_callback(callback)


@router.callback_query(F.data.startswith("cancel_pay:"))
async def callback_cancel_payment(callback: CallbackQuery, db_user: dict | None = None):
    """Cancel a pending payment."""
    payment_id = int(callback.data.split(":")[1])
    payment = await payment_dao.get_payment(payment_id)

    if payment and payment["status"] == "pending" and payment["user_id"] == db_user["user_id"]:
        await payment_dao.reject_payment(payment_id, admin_id=0, note="User cancelled")
        await safe_answer_callback(callback, "❌ To'lov bekor qilindi")
        await safe_edit(callback, "❌ <b>To'lov bekor qilindi.</b>")
    else:
        await safe_answer_callback(callback, "❌ To'lov topilmadi", show_alert=True)


@router.callback_query(F.data == "back:plans")
async def callback_back_plans(callback: CallbackQuery, db_user: dict | None = None):
    """Go back to plan listing."""
    await safe_answer_callback(callback)
    if db_user and callback.message:
        await _show_plans(callback.message, db_user)


@router.message(F.photo)
async def receipt_handler(message: Message, db_user: dict | None = None):
    """Handle receipt photo upload for pending payments."""
    if not db_user or not message.photo:
        return

    user_id = db_user["user_id"]

    # Find user's latest pending payment
    payments = await payment_dao.get_user_payments(user_id, limit=5)
    pending = next((p for p in payments if p["status"] == "pending"), None)

    if not pending:
        # No pending payment — might be a regular photo
        return

    # Save receipt file_id
    file_id = message.photo[-1].file_id
    await payment_dao.update_receipt(pending["id"], file_id)

    await safe_reply(
        message,
        f"📸 <b>Chek qabul qilindi!</b>\n\n"
        f"💳 To'lov #{pending['id']}\n"
        f"📋 Reja: {pending['plan_name'].title()}\n"
        f"💰 Summa: {fmt_price(pending['amount'])}\n\n"
        f"⏳ Admin tez orada tasdiqlaydi. Biroz kuting..."
    )

    # Notify admins
    from src.bot.loader import bot
    from src.database.dao.user_dao import get_admins
    admins = await get_admins()
    name = escape_html(db_user.get("first_name", ""))

    for admin in admins:
        try:
            await bot.send_photo(
                admin["user_id"],
                photo=file_id,
                caption=(
                    f"💳 <b>Yangi to'lov cheki!</b>\n\n"
                    f"👤 {name} (ID: {user_id})\n"
                    f"📋 Reja: {pending['plan_name'].title()}\n"
                    f"💰 Summa: {fmt_price(pending['amount'])}\n"
                    f"📅 Kun: {pending.get('duration_days', 30)}\n\n"
                    f"#payment_{pending['id']}"
                ),
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"admin_approve:{pending['id']}"),
                        InlineKeyboardButton(text="❌ Rad etish", callback_data=f"admin_reject:{pending['id']}"),
                    ]
                ]),
            )
        except Exception as e:
            logger.warning("Failed to notify admin %s: %s", admin["user_id"], e)


@router.message(Command("mypayments"))
async def cmd_mypayments(message: Message, db_user: dict | None = None):
    """Show user's payment history."""
    if not db_user:
        return

    payments = await payment_dao.get_user_payments(db_user["user_id"], limit=10)
    if not payments:
        await safe_reply(message, "📋 <b>To'lovlar tarixi bo'sh.</b>")
        return

    status_icons = {"pending": "⏳", "approved": "✅", "rejected": "❌", "expired": "⌛"}
    lines = ["💳 <b>To'lovlar tarixi</b>\n"]

    for p in payments:
        icon = status_icons.get(p["status"], "❓")
        lines.append(
            f"{icon} #{p['id']} | {p['plan_name'].title()} | "
            f"{fmt_price(p['amount'])} | {p['status']}"
        )

    await safe_reply(message, "\n".join(lines))


def get_subscription_router() -> Router:
    """Return the subscription router."""
    return router
