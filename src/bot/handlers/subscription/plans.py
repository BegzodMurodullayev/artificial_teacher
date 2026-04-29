"""
Subscription handlers: plans, payment selection, receipts, and payment history.
"""

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    ContentType,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)

from src.bot.keyboards.user_menu import subscription_plans_keyboard
from src.bot.utils.telegram import escape_html, fmt_price, safe_answer_callback, safe_edit, safe_reply
from src.database.dao import payment_dao, reward_dao, subscription_dao

logger = logging.getLogger(__name__)
router = Router(name="subscription")


async def _get_payment_config() -> dict[str, str]:
    return await reward_dao.get_all_config("payment_config")


def _is_enabled(config: dict[str, str], key: str, default: str = "1") -> bool:
    return config.get(key, default) != "0"


@router.message(Command("subscribe"))
async def cmd_subscribe(message: Message, db_user: dict | None = None):
    """Show subscription plans."""
    if not db_user:
        return
    await _show_plans(message, db_user)


async def _show_plans(message: Message, db_user: dict) -> None:
    user_id = db_user["user_id"]
    current = await subscription_dao.get_active_plan_name(user_id)
    remaining = await subscription_dao.remaining_days(user_id)
    plans = await subscription_dao.get_all_plans()

    text = "⭐ <b>Obuna rejalari</b>\n\n"
    for plan in plans:
        name = plan["name"]
        display = plan.get("display_name", name.title())
        price = plan.get("price_monthly", 0)
        marker = " ✅ (joriy)" if name == current else ""

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
        return

    plan = await subscription_dao.get_plan(action)
    if not plan:
        await safe_answer_callback(callback, "❌ Reja topilmadi", show_alert=True)
        return

    monthly_price = plan.get("price_monthly", 0)
    yearly_price = plan.get("price_yearly", 0)
    display = plan.get("display_name", action.title())

    buttons = [
        [
            InlineKeyboardButton(
                text=f"📅 1 oy — {fmt_price(monthly_price)}",
                callback_data=f"buy:{action}:30",
            )
        ],
        [
            InlineKeyboardButton(
                text=f"📅 1 yil — {fmt_price(yearly_price)}",
                callback_data=f"buy:{action}:365",
            )
        ],
        [InlineKeyboardButton(text="🔙 Ortga", callback_data="back:plans")],
    ]

    await safe_edit(
        callback,
        f"⭐ <b>{display}</b>\n\nDavomiylikni tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await safe_answer_callback(callback)


@router.callback_query(F.data.startswith("buy:"))
async def callback_buy(callback: CallbackQuery, db_user: dict | None = None):
    """Create a pending payment and offer enabled methods."""
    if not db_user:
        return

    _, plan_name, days_raw = callback.data.split(":")
    days = int(days_raw)

    plan = await subscription_dao.get_plan(plan_name)
    if not plan:
        await safe_answer_callback(callback, "❌ Reja topilmadi", show_alert=True)
        return

    price = float(plan["price_monthly"] if days <= 30 else plan["price_yearly"])
    user_id = db_user["user_id"]
    current_plan = await subscription_dao.get_active_plan_name(user_id)
    remaining = await subscription_dao.remaining_days(user_id)

    credit_text = ""
    if current_plan != "free" and remaining > 0:
        current_plan_data = await subscription_dao.get_plan(current_plan)
        if current_plan_data:
            daily_rate = float(current_plan_data["price_monthly"]) / 30
            credit = daily_rate * remaining
            price = max(0.0, price - credit)
            credit_text = f"\n💳 Kredit (qolgan {remaining} kun): -{fmt_price(credit)}"

    display = plan.get("display_name", plan_name.title())
    config = await _get_payment_config()
    manual_enabled = _is_enabled(config, "manual_enabled")
    stars_enabled = _is_enabled(config, "stars_enabled")
    provider_name = config.get("provider_name", "Karta (Click/Payme)")

    if price > 0 and not manual_enabled and not stars_enabled:
        await safe_answer_callback(
            callback,
            "❌ Hozircha to'lov usullari yoqilmagan. Adminga murojaat qiling.",
            show_alert=True,
        )
        return

    payment_id = await payment_dao.create_payment(
        user_id=user_id,
        plan_name=plan_name,
        amount=price,
        duration_days=days,
        method="pending_method",
    )

    if price <= 0:
        await payment_dao.set_payment_method(payment_id, "credit")
        await payment_dao.approve_payment(payment_id, admin_id=0)
        await subscription_dao.activate_subscription(user_id, plan_name, days)
        await safe_edit(
            callback,
            "✅ <b>Obuna faollashtirildi!</b>\n\n"
            f"📋 Reja: <b>{display}</b>\n"
            f"📅 Davomiylik: <b>{days} kun</b>\n"
            f"💰 Yakuniy summa: <b>{fmt_price(price)}</b>\n\n"
            "Mavjud kredit hisobiga to'lov yopildi.",
        )
        await safe_answer_callback(callback)
        return

    stars_amount = max(1, int(round(price / 150)))
    text = (
        "💳 <b>To'lov usulini tanlang</b>\n\n"
        f"📋 Reja: <b>{display}</b>\n"
        f"📅 Davomiylik: <b>{days} kun</b>\n"
        f"💰 Summa: <b>{fmt_price(price)}</b>"
        f"{credit_text}\n\n"
    )

    buttons: list[list[InlineKeyboardButton]] = []
    if manual_enabled:
        buttons.append(
            [InlineKeyboardButton(text=f"💳 {provider_name}", callback_data=f"pay_manual:{payment_id}")]
        )
    if stars_enabled:
        buttons.append(
            [InlineKeyboardButton(text=f"⭐ Telegram Stars ({stars_amount} XTR)", callback_data=f"pay_stars:{payment_id}")]
        )
    buttons.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"cancel_pay:{payment_id}")])

    await safe_edit(callback, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await safe_answer_callback(callback)


@router.callback_query(F.data.startswith("pay_manual:"))
async def callback_pay_manual(callback: CallbackQuery, db_user: dict | None = None):
    """Handle manual payment flow."""
    if not db_user:
        return

    payment_id = int(callback.data.split(":")[1])
    payment = await payment_dao.get_payment(payment_id)
    if not payment or payment["user_id"] != db_user["user_id"]:
        await safe_answer_callback(callback, "❌ To'lov topilmadi", show_alert=True)
        return

    config = await _get_payment_config()
    if not _is_enabled(config, "manual_enabled"):
        await safe_answer_callback(callback, "❌ Manual to'lov vaqtincha o'chirilgan", show_alert=True)
        return

    await payment_dao.set_payment_method(payment_id, "manual")

    card_number = config.get("card_number", "")
    card_holder = config.get("card_holder", "")
    provider_name = config.get("provider_name", "Karta (Click/Payme)")
    receipt_channel = config.get("receipt_channel", "")

    text = (
        f"💳 <b>To'lov #{payment_id}</b>\n\n"
        f"📋 Reja: <b>{payment['plan_name'].title()}</b>\n"
        f"💰 Summa: <b>{fmt_price(payment['amount'])}</b>\n"
        f"🏦 Usul: <b>{escape_html(provider_name)}</b>\n\n"
    )

    if card_number:
        text += f"Karta: <code>{escape_html(card_number)}</code>\n"
        if card_holder:
            text += f"Egasi: {escape_html(card_holder)}\n"

    if receipt_channel:
        text += f"Cheklar kuzatiladigan kanal: <code>{escape_html(receipt_channel)}</code>\n"

    text += (
        "\n📸 <b>To'lov qilgach, chek rasmini shu yerga yuboring.</b>\n"
        "Admin tez orada ko'rib chiqadi."
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"cancel_pay:{payment_id}")]]
    )
    await safe_edit(callback, text, reply_markup=keyboard)
    await safe_answer_callback(callback)


@router.callback_query(F.data.startswith("pay_stars:"))
async def callback_pay_stars(callback: CallbackQuery, db_user: dict | None = None):
    """Handle Telegram Stars payment flow."""
    if not db_user:
        return

    payment_id = int(callback.data.split(":")[1])
    payment = await payment_dao.get_payment(payment_id)
    if not payment or payment["user_id"] != db_user["user_id"]:
        await safe_answer_callback(callback, "❌ To'lov topilmadi", show_alert=True)
        return

    config = await _get_payment_config()
    if not _is_enabled(config, "stars_enabled"):
        await safe_answer_callback(callback, "❌ Telegram Stars vaqtincha o'chirilgan", show_alert=True)
        return

    stars_amount = int(round(payment["amount"] / 150))
    if stars_amount <= 0:
        await safe_answer_callback(callback, "❌ Stars summasi noto'g'ri", show_alert=True)
        return

    from src.bot.loader import bot

    await payment_dao.set_payment_method(payment_id, "stars")
    await safe_edit(callback, "⭐ Telegram Stars invoice tayyorlanmoqda...")
    await safe_answer_callback(callback)

    try:
        await bot.send_invoice(
            chat_id=callback.from_user.id,
            title=f"Artificial Teacher — {payment['plan_name'].title()}",
            description=f"{payment['duration_days']} kunlik premium imkoniyatlar uchun to'lov.",
            payload=f"stars_pay:{payment_id}",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label="Obuna narxi", amount=stars_amount)],
        )
    except Exception as exc:
        logger.error("Failed to send stars invoice: %s", exc)
        if callback.message:
            await callback.message.answer("❌ Stars invoice yaratishda xatolik yuz berdi.")


@router.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment_handler(message: Message, db_user: dict | None = None):
    """Auto-approve Telegram Stars payments."""
    if not db_user or not message.successful_payment:
        return

    payload = message.successful_payment.invoice_payload
    if not payload.startswith("stars_pay:"):
        return

    payment_id = int(payload.split(":")[1])
    payment = await payment_dao.get_payment(payment_id)
    if not payment or payment["status"] != "pending":
        return

    await payment_dao.approve_payment(payment_id, admin_id=0)
    await subscription_dao.activate_subscription(
        user_id=payment["user_id"],
        plan_name=payment["plan_name"],
        days=payment.get("duration_days", 30),
    )

    await safe_reply(
        message,
        "🎉 <b>To'lov muvaffaqiyatli amalga oshirildi!</b>\n\n"
        f"📋 Reja: <b>{payment['plan_name'].title()}</b>\n"
        f"📅 Davomiylik: <b>{payment.get('duration_days', 30)} kun</b>\n\n"
        "Botning premium imkoniyatlari faollashdi.",
    )


@router.callback_query(F.data.startswith("cancel_pay:"))
async def callback_cancel_payment(callback: CallbackQuery, db_user: dict | None = None):
    """Cancel a pending payment."""
    if not db_user:
        return

    payment_id = int(callback.data.split(":")[1])
    payment = await payment_dao.get_payment(payment_id)

    if payment and payment["status"] == "pending" and payment["user_id"] == db_user["user_id"]:
        await payment_dao.reject_payment(payment_id, admin_id=0, note="User cancelled")
        await safe_answer_callback(callback, "❌ To'lov bekor qilindi")
        await safe_edit(callback, "❌ <b>To'lov bekor qilindi.</b>")
        return

    await safe_answer_callback(callback, "❌ To'lov topilmadi", show_alert=True)


@router.callback_query(F.data == "back:plans")
async def callback_back_plans(callback: CallbackQuery, db_user: dict | None = None):
    """Go back to plan listing."""
    await safe_answer_callback(callback)
    if db_user and callback.message:
        await _show_plans(callback.message, db_user)


@router.message(F.photo, F.content_type == ContentType.PHOTO)
async def receipt_handler(message: Message, db_user: dict | None = None):
    """Handle receipt photo uploads for the latest pending payment."""
    if not db_user or not message.photo or message.chat.type != "private":
        return

    user_id = db_user["user_id"]
    payments = await payment_dao.get_user_payments(user_id, limit=5)
    pending = next((item for item in payments if item["status"] == "pending"), None)
    if not pending:
        return

    file_id = message.photo[-1].file_id
    await payment_dao.update_receipt(pending["id"], file_id)

    await safe_reply(
        message,
        "📸 <b>Chek qabul qilindi!</b>\n\n"
        f"💳 To'lov #{pending['id']}\n"
        f"📋 Reja: {pending['plan_name'].title()}\n"
        f"💰 Summa: {fmt_price(pending['amount'])}\n\n"
        "⏳ Admin tez orada ko'rib chiqadi.",
    )

    from src.bot.loader import bot
    from src.database.dao.user_dao import get_admins

    admins = await get_admins()
    config = await _get_payment_config()
    receipt_channel = config.get("receipt_channel", "").strip()
    user_name = escape_html(db_user.get("first_name", "") or "User")
    admin_caption = (
        "💳 <b>Yangi to'lov cheki!</b>\n\n"
        f"👤 {user_name} (ID: {user_id})\n"
        f"📋 Reja: {pending['plan_name'].title()}\n"
        f"💰 Summa: {fmt_price(pending['amount'])}\n"
        f"📅 Kun: {pending.get('duration_days', 30)}\n\n"
        f"#payment_{pending['id']}"
    )
    review_markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"admin_approve:{pending['id']}"),
                InlineKeyboardButton(text="❌ Rad etish", callback_data=f"admin_reject:{pending['id']}"),
            ]
        ]
    )

    for admin in admins:
        try:
            await bot.send_photo(
                admin["user_id"],
                photo=file_id,
                caption=admin_caption,
                reply_markup=review_markup,
            )
        except Exception as exc:
            logger.warning("Failed to notify admin %s: %s", admin["user_id"], exc)

    if receipt_channel:
        try:
            chat_ref = receipt_channel if receipt_channel.startswith("@") else int(receipt_channel)
            await bot.send_photo(
                chat_ref,
                photo=file_id,
                caption=admin_caption,
            )
        except Exception as exc:
            logger.warning("Failed to forward receipt to %s: %s", receipt_channel, exc)


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
    for payment in payments:
        lines.append(
            f"{status_icons.get(payment['status'], '❔')} "
            f"#{payment['id']} | {payment['plan_name'].title()} | "
            f"{fmt_price(payment['amount'])} | {payment['status']}"
        )

    await safe_reply(message, "\n".join(lines))


def get_subscription_router() -> Router:
    return router
