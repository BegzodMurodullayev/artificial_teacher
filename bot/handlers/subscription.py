"""handlers/subscription.py - Subscription and payment flow."""
import os
import re
from urllib.parse import quote_plus
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest, TimedOut
from telegram.ext import ContextTypes
from database.db import (
    get_user_plan,
    get_all_plans,
    get_plan,
    create_payment,
    get_user_payments,
    get_pending_payment_for_user,
    get_active_subscription,
    get_all_pay_config,
    upsert_user,
    get_admin_ids,
    calculate_plan_quote,
    get_points,
    get_promo_packs,
    redeem_promo_pack,
    get_reward_wallet,
)

PLAN_ICONS = {
    "free": "\U0001F193",
    "standard": "\u2B50",
    "pro": "\U0001F48E",
    "premium": "\U0001F451",
}


def fmt_price(amount):
    if amount == 0:
        return "Bepul"
    return f"{round(amount):,} UZS".replace(",", " ")


def payment_mode(cfg: dict) -> str:
    mode = str(cfg.get("payment_mode") or cfg.get("payment_method") or "manual").strip().lower()
    return mode if mode in {"manual", "hybrid", "auto"} else "manual"


def checkout_ready(cfg: dict) -> bool:
    return bool(str(cfg.get("checkout_url_template", "")).strip())


def build_checkout_url(cfg: dict, user_id: int, plan_name: str, days: int, amount: float) -> str:
    template = str(cfg.get("checkout_url_template", "")).strip()
    if not template:
        return ""
    replacements = {
        "user_id": str(user_id),
        "plan": quote_plus(str(plan_name)),
        "days": str(days),
        "amount": str(int(round(amount or 0))),
        "plan_label": quote_plus(format_plan_title(plan_name)),
    }
    url = template
    for key, value in replacements.items():
        url = url.replace("{" + key + "}", value)
    return url


def build_payment_choice_keyboard(plan_name: str, monthly_quote: dict, yearly_quote: dict, cfg: dict):
    rows = []
    mode = payment_mode(cfg)
    auto_ready = checkout_ready(cfg)
    auto_enabled = auto_ready and mode in {"auto", "hybrid"}
    manual_enabled = mode in {"manual", "hybrid"} or not auto_ready

    if auto_enabled:
        rows.append([InlineKeyboardButton(f"⚡ Auto 1 oy - {fmt_price(monthly_quote['final_amount'])}", callback_data=f"sub_auto_{plan_name}_30")])
        rows.append([InlineKeyboardButton(f"⚡ Auto 1 yil - {fmt_price(yearly_quote['final_amount'])}", callback_data=f"sub_auto_{plan_name}_365")])
    if manual_enabled:
        rows.append([InlineKeyboardButton(f"🧾 Qo'lda 1 oy - {fmt_price(monthly_quote['final_amount'])}", callback_data=f"sub_pay_{plan_name}_30")])
        rows.append([InlineKeyboardButton(f"🧾 Qo'lda 1 yil - {fmt_price(yearly_quote['final_amount'])}", callback_data=f"sub_pay_{plan_name}_365")])

    rows.append([InlineKeyboardButton("🔙 Orqaga", callback_data="sub_back")])
    return InlineKeyboardMarkup(rows)


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


async def safe_reply(message, text, reply_markup=None, parse_mode=None):
    if message is None:
        return
    try:
        await message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        return
    except BadRequest:
        if parse_mode:
            try:
                await message.reply_text(text, reply_markup=reply_markup)
                return
            except Exception:
                pass
    except TimedOut:
        return
    except Exception:
        pass


def format_plan_title(plan_name: str, display_name: str | None = None) -> str:
    fallback = {
        "free": "Free",
        "standard": "Standard",
        "pro": "Pro",
        "premium": "Premium",
    }.get(plan_name, plan_name.capitalize())

    raw = (display_name or fallback).strip()
    cleaned = raw
    for token in ("\U0001F193", "\u2B50", "\U0001F48E", "\U0001F451", "[FREE]", "[STD]", "[PRO]", "[PREM]"):
        cleaned = cleaned.replace(token, " ")
    cleaned = " ".join(cleaned.split()).strip(" -")

    parts = cleaned.split()
    if len(parts) >= 2 and parts[0].lower() == parts[1].lower():
        cleaned = " ".join(parts[1:])
    if cleaned.lower() in ("free", "standard", "pro", "premium"):
        cleaned = cleaned.title()
    return cleaned or fallback


def escape_md(text: str) -> str:
    if text is None:
        return ""
    return re.sub(r"([_*\[\]()~`>#+=|{}.!-])", r"\\\1", str(text))


def plan_keyboard(current_plan="free"):
    plans = get_all_plans()
    rows = []
    for p in plans:
        if p["name"] == "free":
            continue
        mark = " [ACTIVE]" if p["name"] == current_plan else ""
        rows.append([
            InlineKeyboardButton(
                f"{PLAN_ICONS.get(p['name'], '')} {format_plan_title(p['name'], p.get('display_name'))} - {fmt_price(p['price_monthly'])}/oy{mark}",
                callback_data=f"sub_choose_{p['name']}",
            )
        ])
    rows.append([InlineKeyboardButton("\U0001F381 Ball bilan paketlar", callback_data="sub_points_packs")])
    rows.append([InlineKeyboardButton("\U0001F519 Menyu", callback_data="menu_back")])
    return InlineKeyboardMarkup(rows)


def payment_action_keyboard(plan_name: str, card_label: str):
    rows = []
    if card_label:
        rows.append([InlineKeyboardButton(f"\U0001F4B3 {card_label}", callback_data="sub_card_info")])
    rows.append([InlineKeyboardButton("\U0001F9FE Chek yuborish", callback_data="sub_send_receipt")])
    rows.append([InlineKeyboardButton("\U0001F519 Orqaga", callback_data=f"sub_choose_{plan_name}")])
    return InlineKeyboardMarkup(rows)


def build_subscription_text(user_id: int) -> tuple[str, str]:
    plan = get_user_plan(user_id)
    wallet = get_reward_wallet(user_id)
    plan_name = plan.get("plan_name", "free")
    icon = PLAN_ICONS.get(plan_name, "🆓")
    expires = plan.get("expires_at", "")
    exp_text = f"\nMuddati: `{expires[:10]}`" if expires else ""

    plans = get_all_plans()
    text = (
        f"*Obuna tizimi*\n\n"
        f"Sizning rejangiz: {icon} *{format_plan_title(plan_name, plan.get('display_name'))}*{exp_text}\n\n"
        f"*Ballaringiz:* {wallet.get('points', 0)} | Referral kod: `{wallet.get('referral_code', f'AT{user_id}')}`\n\n"
        "*Muhim:* Pul bo'lmasa ham Free rejim ishlaydi.\n"
        "Pullik rejalar ko'p ishlatadiganlar uchun: limit yuqori va tezroq natija.\n\n"
        "*Nega pullik reja bor?*\n"
        "- server va AI xarajatlarini qoplash\n"
        "- yuqori yuklamada barqaror ishlash\n"
        "- Free rejimni uzoq muddat bepul saqlash\n\n"
        "*Rejalar taqqoslash:*\n\n"
    )

    for p in plans:
        ic = PLAN_ICONS.get(p["name"], "")
        checks = "cheksiz" if p["checks_per_day"] == -1 else str(p["checks_per_day"])
        ai = "cheksiz" if p["ai_messages_day"] == -1 else str(p["ai_messages_day"])
        pron_audio = "cheksiz" if p.get("pron_audio_per_day", 0) == -1 else str(p.get("pron_audio_per_day", 0))
        voice = "ha" if p["voice_enabled"] else "yo'q"
        inline = "ha" if p["inline_enabled"] else "yo'q"
        text += (
            f"{ic} *{format_plan_title(p['name'], p.get('display_name'))}* - {fmt_price(p['price_monthly'])}/oy\n"
            f"  Tekshirish: {checks}/kun | AI: {ai}/kun | Talaffuz audio: {pron_audio}/kun | Ovoz: {voice} | Inline: {inline}\n\n"
        )

    return text, plan_name


async def subscription_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    upsert_user(user.id, user.username, user.first_name)
    text, plan_name = build_subscription_text(user.id)

    if update.callback_query:
        await safe_edit(
            update.callback_query,
            text,
            reply_markup=plan_keyboard(plan_name),
            parse_mode="Markdown",
        )
        return

    target = update.effective_message
    if target:
        await target.reply_text(
            text,
            reply_markup=plan_keyboard(plan_name),
            parse_mode="Markdown",
        )


async def sub_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("sub_choose_"):
        plan_name = data.split("_", 2)[2]
        plan = get_plan(plan_name)
        if not plan:
            return

        current_plan = get_user_plan(query.from_user.id)
        if current_plan and current_plan.get("plan_name") != "free":
            if plan.get("price_monthly", 0) < current_plan.get("price_monthly", 0):
                await safe_edit(query, "Sizda yuqori reja aktiv. Pastroq reja uchun to'lov mumkin emas.", parse_mode="Markdown")
                return

        cfg = get_all_pay_config()
        icon = PLAN_ICONS.get(plan_name, "")
        chk = "Cheksiz" if plan["checks_per_day"] == -1 else f"{plan['checks_per_day']}/kun"
        ai = "Cheksiz" if plan["ai_messages_day"] == -1 else f"{plan['ai_messages_day']}/kun"
        voice_label = "ha" if plan["voice_enabled"] else "yo'q"
        pron_audio_label = "Cheksiz" if plan.get("pron_audio_per_day", 0) == -1 else f"{plan.get('pron_audio_per_day', 0)}/kun"
        inline_label = "ha" if plan["inline_enabled"] else "yo'q"
        group_label = "ha" if plan["group_enabled"] else "yo'q"
        iq_label = "ha" if plan["iq_test_enabled"] else "yo'q"

        monthly_quote = calculate_plan_quote(query.from_user.id, plan_name, 30)
        yearly_quote = calculate_plan_quote(query.from_user.id, plan_name, 365)

        text = (
            f"{icon} *{format_plan_title(plan_name, plan.get('display_name'))} rejasini tanlash*\n\n"
            f"Narx: *{fmt_price(plan['price_monthly'])}/oy*\n"
            f"Yillik: *{fmt_price(plan['price_yearly'])}* (tejamkor)\n\n"
            "Kimlar uchun: har kuni faol o'rganadigan va limitga tez yetadiganlar uchun.\n\n"
            "*Imkoniyatlar:*\n"
            f"- Tekshirish: {chk}\n"
            f"- AI xabar: {ai}\n"
            f"- Quiz: {'Cheksiz' if plan['quiz_per_day'] == -1 else str(plan['quiz_per_day']) + '/kun'}\n"
            f"- Talaffuz audio: {pron_audio_label}\n"
            f"- Ovozli xabar: {voice_label}\n"
            f"- Inline rejim: {inline_label}\n"
            f"- Guruh: {group_label}\n"
            f"- IQ test: {iq_label}\n\n"
        )

        if current_plan and current_plan.get("plan_name") == plan_name and current_plan.get("plan_name") != "free":
            text += (
                "*Uzaytirish:* shu rejani qayta olsangiz, qolgan muddat ustiga qo'shiladi.\n\n"
            )

        if monthly_quote["can_upgrade"] and monthly_quote["credit_amount"] > 0:
            text += (
                "*Upgrade hisobi:*\n"
                f"- Hozirgi reja: {monthly_quote['current_plan'].capitalize()}\n"
                f"- Qolgan kredit: {fmt_price(monthly_quote['credit_amount'])}\n"
                f"- 1 oy uchun to'lov: *{fmt_price(monthly_quote['final_amount'])}*\n"
                f"- 1 yil uchun to'lov: *{fmt_price(yearly_quote['final_amount'])}*\n\n"
            )

        mode = payment_mode(cfg)
        auto_ready = checkout_ready(cfg)
        if mode == "auto" and auto_ready:
            text += "*To'lov oqimi:* Auto checkout yoqilgan.\n\n"
        elif mode == "hybrid" and auto_ready:
            text += "*To'lov oqimi:* Auto + qo'lda tasdiqlash varianti mavjud.\n\n"
        elif mode == "auto" and not auto_ready:
            text += "*Eslatma:* Auto rejim tanlangan, lekin checkout URL kiritilmagan. Hozircha qo'lda to'lov ko'rsatiladi.\n\n"
        else:
            text += "*To'lov oqimi:* Qo'lda chek yuborish orqali.\n\n"

        await safe_edit(query, text, reply_markup=build_payment_choice_keyboard(plan_name, monthly_quote, yearly_quote, cfg), parse_mode="Markdown")

    elif data.startswith("sub_auto_"):
        _, _, plan_name, days_raw = data.split("_", 3)
        days = int(days_raw)
        cfg = get_all_pay_config()
        quote = calculate_plan_quote(query.from_user.id, plan_name, days)
        amount = quote["final_amount"]
        checkout_url = build_checkout_url(cfg, query.from_user.id, plan_name, days, amount)
        if not checkout_url:
            await safe_edit(query, "Auto checkout URL sozlanmagan. Hozircha qo'lda to'lovdan foydalaning.", parse_mode="Markdown")
            return
        button_label = cfg.get("checkout_button_label", "Auto to'lovni ochish") or "Auto to'lovni ochish"
        auto_note = cfg.get("auto_payment_note", "") or ""
        keyboard = [[InlineKeyboardButton(button_label, url=checkout_url)]]
        if payment_mode(cfg) == "hybrid" or str(cfg.get("manual_review_enabled", "1")) != "0":
            keyboard.append([InlineKeyboardButton("🧾 Qo'lda to'lash", callback_data=f"sub_pay_{plan_name}_{days}")])
        keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data=f"sub_choose_{plan_name}")])
        period = "1 oy" if days == 30 else "1 yil"
        text = (
            f"*Auto to'lov oynasi - {format_plan_title(plan_name)} ({period})*\n\n"
            f"Miqdor: *{fmt_price(amount)}*\n\n"
            f"{auto_note or 'Tugmani bosib checkout sahifasini oching.'}\n\n"
            "Agar auto checkout ishlamasa, pastdagi qo'lda to'lash variantidan foydalanishingiz mumkin."
        )
        await safe_edit(query, text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("sub_pay_"):
        _, _, plan_name, days_raw = data.split("_", 3)
        days = int(days_raw)
        plan = get_plan(plan_name)
        cfg = get_all_pay_config()

        pending = get_pending_payment_for_user(query.from_user.id)
        if pending:
            await safe_edit(query, "Sizda tekshirilayotgan to'lov bor. Iltimos, tasdiqni kuting.", parse_mode="Markdown")
            return

        current_plan = get_user_plan(query.from_user.id)
        if current_plan and current_plan.get("plan_name") != "free":
            if plan.get("price_monthly", 0) < current_plan.get("price_monthly", 0):
                await safe_edit(query, "Sizda yuqori reja aktiv. Pastroq reja uchun to'lov mumkin emas.", parse_mode="Markdown")
                return

        quote = calculate_plan_quote(query.from_user.id, plan_name, days)
        amount = quote["final_amount"]
        icon = PLAN_ICONS.get(plan_name, "")
        card = cfg.get("card_number", "")
        holder = cfg.get("card_holder", "")
        note = cfg.get("payment_note", "")
        card_label = cfg.get("card_label", "Karta")
        period = "1 oy" if days == 30 else "1 yil"

        text = (
            f"*To'lov - {icon} {format_plan_title(plan_name, plan.get('display_name'))} ({period})*\n\n"
            f"Miqdor: *{fmt_price(amount)}*\n\n"
            "--------------------\n"
        )
        if quote["can_upgrade"] and quote["credit_amount"] > 0:
            text += (
                f"Upgrade krediti: {fmt_price(quote['credit_amount'])}\n"
                f"Qolgan kunlar: {quote['remaining_days']}\n"
                "--------------------\n"
            )
        if card:
            text += f"{card_label}:\n`{card}`\n"
        if holder:
            text += f"Karta egasi: {holder}\n"
        text += (
            f"\n{note}\n\n"
            "--------------------\n"
            "To'lovni amalga oshirgach, *chek (screenshot) yuboring*.\n"
            "Admin tekshiradi va obunangizni faollashtiradi."
        )

        context.user_data["pending_payment"] = {
            "plan_name": plan_name,
            "amount": amount,
            "days": days,
            "quote": quote,
        }
        keyboard = [
            [InlineKeyboardButton(f"\U0001F4B3 {card_label}", callback_data="sub_card_info")],
            [InlineKeyboardButton("\U0001F9FE Chek yuborish", callback_data="sub_send_receipt")],
            [InlineKeyboardButton("\U0001F519 Orqaga", callback_data=f"sub_choose_{plan_name}")],
        ]
        await safe_edit(query, text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "sub_card_info":
        pending = context.user_data.get("pending_payment", {})
        if not pending:
            await safe_edit(query, "To'lov oynasi topilmadi. Rejani qayta tanlang.")
            return
        cfg = get_all_pay_config()
        card = cfg.get("card_number", "")
        holder = cfg.get("card_holder", "")
        card_label = cfg.get("card_label", "Karta")
        text = (
            f"*{card_label} ma'lumotlari*\n\n"
            f"Raqam: `{card or '-'}`\n"
            f"Ega: {holder or '-'}\n\n"
            "To'lov qilgach, chek yuboring."
        )
        await safe_edit(query, text, reply_markup=payment_action_keyboard(pending["plan_name"], card_label), parse_mode="Markdown")

    elif data == "sub_send_receipt":
        await safe_edit(query, 
            "*Chek yuborish*\n\n"
            "To'lov chekini (screenshot yoki rasm) yuboring.\n"
            "Admin odatda 24 soat ichida tekshiradi.",
            parse_mode="Markdown",
        )
        context.user_data["awaiting_receipt"] = True

    elif data == "sub_back":
        await subscription_command_from_callback(query, context)

    elif data == "sub_points_packs":
        packs = get_promo_packs(active_only=True)
        points = get_points(query.from_user.id)
        lines = [f"\U0001F381 *Ball paketlari*\n\nSizdagi ball: *{points}*\n"]
        keyboard = []
        if not packs:
            lines.append("Hozircha aktiv paket yo'q.")
        for pack in packs:
            lines.append(
                f"#{pack['id']} *{escape_md(pack['title'])}*\n"
                f"- Reja: {escape_md(pack['plan_name'])}\n"
                f"- Muddat: {pack['duration_days']} kun\n"
                f"- Narx: {pack['points_cost']} ball\n"
            )
            keyboard.append([InlineKeyboardButton(f"Olish #{pack['id']} - {pack['points_cost']} ball", callback_data=f"sub_redeem_pack_{pack['id']}")])
        keyboard.append([InlineKeyboardButton("\U0001F519 Orqaga", callback_data="sub_back")])
        await safe_edit(query, "\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("sub_redeem_pack_"):
        pack_id = int(data.split("_")[-1])
        result = redeem_promo_pack(query.from_user.id, pack_id)
        if not result.get("ok"):
            if result.get("reason") == "insufficient":
                await safe_edit(query, f"Ball yetarli emas. Sizda {result.get('points', 0)} ball bor.", parse_mode="Markdown")
            else:
                await safe_edit(query, "Paket topilmadi yoki aktiv emas.")
            return
        pack = result["pack"]
        await safe_edit(
            query,
            f"\u2705 *Paket olindi!*\n\n"
            f"{escape_md(pack['title'])}\n"
            f"Reja: *{escape_md(pack['plan_name'])}*\n"
            f"Muddat: *{pack['duration_days']} kun*",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("\U0001F519 Tariflar", callback_data="sub_back")]]),
            parse_mode="Markdown",
        )


async def subscription_command_from_callback(query, context):
    user = query.from_user
    upsert_user(user.id, user.username, user.first_name)
    text, plan_name = build_subscription_text(user.id)
    await safe_edit(query, 
        text,
        reply_markup=plan_keyboard(plan_name),
        parse_mode="Markdown",
    )


async def receipt_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_receipt"):
        return False

    user = update.effective_user
    pending = context.user_data.get("pending_payment", {})
    if not pending:
        await safe_reply(update.message, "To'lov ma'lumoti topilmadi. /subscribe ni qayta bosing.")
        return True

    file_id = ""
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
    elif update.message.document:
        file_id = update.message.document.file_id

    if not file_id:
        await safe_reply(update.message, "Rasm yuboring (screenshot yoki fayl).")
        return True

    payment_id = create_payment(
        user_id=user.id,
        plan_name=pending["plan_name"],
        amount=pending["amount"],
        duration_days=pending.get("days", 30),
        method="manual",
        receipt_file_id=file_id,
    )

    context.user_data.pop("awaiting_receipt", None)
    context.user_data.pop("pending_payment", None)

    plan = get_plan(pending["plan_name"])
    icon = PLAN_ICONS.get(pending["plan_name"], "")

    await safe_reply(
        update.message,
        f"*Chek qabul qilindi!*\n\n"
        f"To'lov #{payment_id}\n"
        f"Reja: {icon} {format_plan_title(pending['plan_name'], plan.get('display_name'))}\n"
        f"Miqdor: {fmt_price(pending['amount'])}\n\n"
        "Admin tekshiradi va obunangizni faollashtiradi.",
        parse_mode="Markdown",
    )

    recipients = get_admin_ids(include_owner=True)
    if recipients:
        first_name = escape_md(user.first_name or "")
        username = escape_md(user.username or "noma")
        admin_text = (
            f"*Yangi to'lov so'rovi #{payment_id}*\n\n"
            f"Foydalanuvchi: {first_name} (@{username} | `{user.id}`)\n"
            f"Reja: {icon} {format_plan_title(pending['plan_name'], plan.get('display_name'))}\n"
            f"Miqdor: {fmt_price(pending['amount'])}\n\n"
            "Chekni ko'rib chiqing va tasdiqlang:"
        )
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("Tasdiqlash", callback_data=f"pay_approve_{payment_id}"),
            InlineKeyboardButton("Rad etish", callback_data=f"pay_reject_{payment_id}"),
        ]])
        for admin_id in recipients:
            try:
                await context.bot.send_photo(
                    admin_id,
                    file_id,
                    caption=admin_text,
                    reply_markup=kb,
                    parse_mode="Markdown",
                )
            except Exception:
                try:
                    await context.bot.send_document(
                        admin_id,
                        file_id,
                        caption=admin_text,
                        reply_markup=kb,
                        parse_mode="Markdown",
                    )
                except Exception:
                    try:
                        await context.bot.send_message(admin_id, admin_text, reply_markup=kb, parse_mode="Markdown")
                    except Exception:
                        pass
    return True


async def my_payments_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    payments = get_user_payments(user.id)
    if not payments:
        await update.message.reply_text("Sizda to'lov tarixi yo'q.")
        return

    text = "*To'lovlar tarixi:*\n\n"
    status_icons = {"pending": "⏳", "approved": "✅", "rejected": "❌", "expired": "⌛"}
    for p in payments[:5]:
        icon = status_icons.get(p["status"], "❓")
        text += (
            f"{icon} #{p['id']} - {PLAN_ICONS.get(p['plan_name'], '')} {p['plan_name']} | "
            f"{fmt_price(p['amount'])} | {p['created_at'][:10]}\n"
        )
    await update.message.reply_text(text, parse_mode="Markdown")
