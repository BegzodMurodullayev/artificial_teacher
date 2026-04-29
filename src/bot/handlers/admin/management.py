"""
Additional admin management handlers.
Inline-first admin tools for:
- Admin role management
- Payment settings management
- Sponsor channels management

Slash commands are preserved as backward-compatible fallbacks.
"""

import logging

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from src.bot.filters.role import RoleFilter
from src.bot.utils.telegram import escape_html, safe_answer_callback, safe_edit, safe_reply
from src.config import settings
from src.database.dao import reward_dao, sponsor_dao, subscription_dao, user_dao

logger = logging.getLogger(__name__)
router = Router(name="admin_management")

router.message.filter(RoleFilter("admin", "owner"))
router.callback_query.filter(RoleFilter("admin", "owner"))

STATE_ADD_ADMIN = "ADMIN_MGMT_ADD_ADMIN"
STATE_ADD_SPONSOR = "ADMIN_MGMT_ADD_SPONSOR"
STATE_CFG_EDIT = "ADMIN_MGMT_CFG_EDIT"


def _command_args(text: str) -> list[str]:
    parts = (text or "").strip().split(maxsplit=1)
    if len(parts) < 2:
        return []
    return parts[1].strip().split()


def _parse_bool_flag(value: str) -> str | None:
    clean = value.strip().lower()
    if clean in {"1", "on", "true", "yes", "ha", "active"}:
        return "1"
    if clean in {"0", "off", "false", "no", "yo'q", "yoq", "stop", "inactive"}:
        return "0"
    return None


async def _resolve_user_reference(raw: str) -> dict | None:
    token = raw.strip()
    if not token:
        return None
    if token.startswith("@"):
        return await user_dao.find_user_by_username(token[1:])
    if token.isdigit():
        user_id = int(token)
        user = await user_dao.get_user(user_id)
        if user:
            return user
        return await user_dao.upsert_user(user_id=user_id, username="", first_name="")
    return None


def _admins_keyboard(admins: list[dict], current_admin_id: int | None = None) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text="➕ Admin qo'shish", callback_data="adm_mgmt:admins:add")]
    ]
    for item in admins:
        user_id = int(item["user_id"])
        role = item.get("role", "user")
        if role == "owner":
            continue
        if current_admin_id and user_id == current_admin_id:
            continue
        label = item.get("username") or item.get("first_name") or str(user_id)
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"➖ {label[:18]}",
                    callback_data=f"adm_mgmt:admins:remove:{user_id}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="🔙 Dashboard", callback_data="adm:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _payment_config_keyboard(cfg: dict[str, str]) -> InlineKeyboardMarkup:
    manual_on = cfg.get("manual_enabled", "1") != "0"
    stars_on = cfg.get("stars_enabled", "1") != "0"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"💳 Manual to'lov: {'✅ Yoqilgan' if manual_on else '❌ O\'chirilgan'}",
                    callback_data="adm_mgmt:cfg:toggle:manual",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"⭐ Telegram Stars: {'✅ Yoqilgan' if stars_on else '❌ O\'chirilgan'}",
                    callback_data="adm_mgmt:cfg:toggle:stars",
                )
            ],
            [
                InlineKeyboardButton(text="💳 Karta raqamini kiritish", callback_data="adm_mgmt:cfg:set:card_number"),
            ],
            [
                InlineKeyboardButton(text="👤 Karta egasining ism-familiyasi", callback_data="adm_mgmt:cfg:set:card_holder"),
            ],
            [
                InlineKeyboardButton(text="🏦 To'lov usuli (Provider)", callback_data="adm_mgmt:cfg:set:provider_name"),
            ],
            [
                InlineKeyboardButton(text="📢 Cheklar jo'natiladigan kanal", callback_data="adm_mgmt:cfg:set:receipt_channel"),
            ],
            [InlineKeyboardButton(text="🔙 Dashboard", callback_data="adm:back")],
        ]
    )


def _sponsors_keyboard(sponsors: list[dict]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text="➕ Sponsor qo'shish", callback_data="adm_mgmt:sponsors:add")]
    ]
    for item in sponsors[:10]:
        channel_id = int(item["channel_id"])
        is_active = bool(item.get("is_active"))
        username = item.get("channel_username") or ""
        title = item.get("title") or str(channel_id)
        label = username if username else title
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{'✅' if is_active else '⚪'} {label[:14]}",
                    callback_data=f"adm_mgmt:sponsors:toggle:{channel_id}",
                ),
                InlineKeyboardButton(
                    text="🗑 O'chirish",
                    callback_data=f"adm_mgmt:sponsors:delete:{channel_id}",
                ),
            ]
        )
    rows.append([InlineKeyboardButton(text="🔙 Dashboard", callback_data="adm:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _render_admins_panel(target: Message | CallbackQuery, current_admin_id: int | None = None) -> None:
    admins = await user_dao.get_admins()
    lines = ["🛡 <b>Adminlar va Ownerlar</b>", ""]
    if admins:
        for item in admins:
            username = item.get("username") or "-"
            first_name = escape_html(item.get("first_name", "") or "-")
            lines.append(
                f"<code>{item['user_id']}</code> | {first_name} | "
                f"@{escape_html(username)} | <b>{escape_html(item.get('role', 'user'))}</b>"
            )
    else:
        lines.append("<i>Hozircha admin topilmadi.</i>")

    lines.extend(
        [
            "",
            "Inline tugmalar orqali qo'shish/o'chirish mumkin.",
            "➕ bosilgach, ID yoki @username yuboring.",
        ]
    )
    text = "\n".join(lines)
    kb = _admins_keyboard(admins, current_admin_id=current_admin_id)

    if isinstance(target, CallbackQuery):
        await safe_edit(target, text, reply_markup=kb)
        await safe_answer_callback(target)
    else:
        await safe_reply(target, text, reply_markup=kb)


async def _render_payment_config_panel(target: Message | CallbackQuery) -> None:
    cfg = await reward_dao.get_all_config("payment_config")
    text = (
        "💰 <b>To'lov sozlamalari</b>\n\n"
        f"Provider: <code>{escape_html(cfg.get('provider_name', 'Karta'))}</code>\n"
        f"Karta: <code>{escape_html(cfg.get('card_number', 'sozlanmagan'))}</code>\n"
        f"Karta egasi: <code>{escape_html(cfg.get('card_holder', 'sozlanmagan'))}</code>\n"
        f"Manual: <b>{'ON' if cfg.get('manual_enabled', '1') != '0' else 'OFF'}</b>\n"
        f"Stars: <b>{'ON' if cfg.get('stars_enabled', '1') != '0' else 'OFF'}</b>\n"
        f"Receipt channel: <code>{escape_html(cfg.get('receipt_channel', 'sozlanmagan'))}</code>\n\n"
        "⚙️ Tugmalar orqali qiymatlarni yangilashingiz mumkin."
    )
    kb = _payment_config_keyboard(cfg)
    if isinstance(target, CallbackQuery):
        await safe_edit(target, text, reply_markup=kb)
        await safe_answer_callback(target)
    else:
        await safe_reply(target, text, reply_markup=kb)


async def _render_sponsors_panel(target: Message | CallbackQuery) -> None:
    sponsors = await sponsor_dao.get_all_sponsors()
    lines = ["📢 <b>Homiy kanallar</b>", ""]
    if sponsors:
        for item in sponsors:
            status = "active" if item.get("is_active") else "inactive"
            username = item.get("channel_username") or "-"
            title = item.get("title") or "Untitled"
            lines.append(
                f"<code>{item['channel_id']}</code> | {escape_html(title)} | "
                f"{escape_html(username)} | <b>{status}</b>"
            )
    else:
        lines.append("<i>Hali homiy kanal qo'shilmagan.</i>")

    lines.extend(
        [
            "",
            "Inline tugmalar orqali qo'shish/toggle/o'chirish mumkin.",
            "➕ bosilgach @kanal yoki -100... kiriting.",
        ]
    )
    text = "\n".join(lines)
    kb = _sponsors_keyboard(sponsors)
    if isinstance(target, CallbackQuery):
        await safe_edit(target, text, reply_markup=kb)
        await safe_answer_callback(target)
    else:
        await safe_reply(target, text, reply_markup=kb)


@router.message(F.text == "🛡 Adminlar")
@router.message(Command("admins"))
async def _btn_adm_admins(message: Message, db_user: dict | None = None):
    current_admin_id = db_user.get("user_id") if db_user else None
    await _render_admins_panel(message, current_admin_id=current_admin_id)


@router.message(F.text == "💰 To'lov Sozlamalari")
@router.message(Command("payconfig"))
async def _btn_adm_payment_settings(message: Message, db_user: dict | None = None):
    await _render_payment_config_panel(message)


@router.message(F.text == "📢 Homiy Kanallar")
@router.message(Command("sponsors"))
async def _btn_adm_sponsors(message: Message, db_user: dict | None = None):
    await _render_sponsors_panel(message)


@router.callback_query(F.data == "adm_mgmt:admins:add")
async def callback_admins_add(callback: CallbackQuery, state: FSMContext, db_user: dict | None = None):
    await state.set_state(STATE_ADD_ADMIN)
    await safe_answer_callback(callback)
    await safe_edit(
        callback,
        "➕ <b>Admin qo'shish</b>\n\n"
        "ID yoki @username yuboring.\n"
        "Bekor qilish: <code>bekor</code>",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="❌ Bekor", callback_data="adm_mgmt:admins:cancel")]]
        ),
    )


@router.callback_query(F.data == "adm_mgmt:admins:cancel")
async def callback_admins_cancel(callback: CallbackQuery, state: FSMContext, db_user: dict | None = None):
    await state.clear()
    current_admin_id = db_user.get("user_id") if db_user else None
    await _render_admins_panel(callback, current_admin_id=current_admin_id)


@router.message(StateFilter(STATE_ADD_ADMIN), F.text.regexp(r"(?i)^(bekor|cancel)$"))
async def message_add_admin_cancel(message: Message, state: FSMContext, db_user: dict | None = None):
    await state.clear()
    current_admin_id = db_user.get("user_id") if db_user else None
    await safe_reply(message, "❌ Bekor qilindi.")
    await _render_admins_panel(message, current_admin_id=current_admin_id)


@router.message(StateFilter(STATE_ADD_ADMIN), F.text)
async def message_add_admin_apply(message: Message, state: FSMContext, db_user: dict | None = None):
    target = await _resolve_user_reference(message.text.strip())
    if not target:
        await safe_reply(message, "❌ Foydalanuvchi topilmadi. ID yoki @username yuboring.")
        return
    await user_dao.set_role(int(target["user_id"]), "admin")
    await state.clear()
    await safe_reply(message, f"✅ Admin qo'shildi: <code>{target['user_id']}</code>")
    current_admin_id = db_user.get("user_id") if db_user else None
    await _render_admins_panel(message, current_admin_id=current_admin_id)


@router.callback_query(F.data.startswith("adm_mgmt:admins:remove:"))
async def callback_admin_remove(callback: CallbackQuery, db_user: dict | None = None):
    target_id = int(callback.data.split(":")[-1])
    target = await user_dao.get_user(target_id)
    if not target:
        await safe_answer_callback(callback, "❌ User topilmadi.", show_alert=True)
        return
    if target.get("role") == "owner" or target_id == settings.OWNER_ID:
        await safe_answer_callback(callback, "❌ Owner rolini o'zgartirib bo'lmaydi.", show_alert=True)
        return
    await user_dao.set_role(target_id, "user")
    await safe_answer_callback(callback, "✅ Admin roli olindi.")
    current_admin_id = db_user.get("user_id") if db_user else None
    await _render_admins_panel(callback, current_admin_id=current_admin_id)


@router.callback_query(F.data == "adm_mgmt:cfg:toggle:manual")
async def callback_cfg_toggle_manual(callback: CallbackQuery):
    cfg = await reward_dao.get_all_config("payment_config")
    now = cfg.get("manual_enabled", "1")
    await reward_dao.set_config("payment_config", "manual_enabled", "0" if now != "0" else "1")
    await safe_answer_callback(callback, "✅ Manual holati yangilandi.")
    await _render_payment_config_panel(callback)


@router.callback_query(F.data == "adm_mgmt:cfg:toggle:stars")
async def callback_cfg_toggle_stars(callback: CallbackQuery):
    cfg = await reward_dao.get_all_config("payment_config")
    now = cfg.get("stars_enabled", "1")
    await reward_dao.set_config("payment_config", "stars_enabled", "0" if now != "0" else "1")
    await safe_answer_callback(callback, "✅ Stars holati yangilandi.")
    await _render_payment_config_panel(callback)


@router.callback_query(F.data.startswith("adm_mgmt:cfg:set:"))
async def callback_cfg_set_field(callback: CallbackQuery, state: FSMContext):
    field = callback.data.split(":")[-1]
    field_names = {
        "provider_name": "Provider nomi",
        "card_number": "Karta raqami",
        "card_holder": "Karta egasi",
        "receipt_channel": "Receipt kanal (@kanal yoki -100...)",
    }
    if field not in field_names:
        await safe_answer_callback(callback, "❌ Noma'lum maydon.", show_alert=True)
        return
    await state.set_state(STATE_CFG_EDIT)
    await state.update_data(cfg_field=field)
    await safe_answer_callback(callback)
    await safe_edit(
        callback,
        f"✏️ <b>{field_names[field]}</b>\n\n"
        "Yangi qiymatni yuboring.\n"
        "Bekor qilish: <code>bekor</code>",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="❌ Bekor", callback_data="adm_mgmt:cfg:cancel")]]
        ),
    )


@router.callback_query(F.data == "adm_mgmt:cfg:cancel")
async def callback_cfg_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await _render_payment_config_panel(callback)


@router.message(StateFilter(STATE_CFG_EDIT), F.text.regexp(r"(?i)^(bekor|cancel)$"))
async def message_cfg_cancel(message: Message, state: FSMContext):
    await state.clear()
    await safe_reply(message, "❌ Bekor qilindi.")
    await _render_payment_config_panel(message)


@router.message(StateFilter(STATE_CFG_EDIT), F.text)
async def message_cfg_apply(message: Message, state: FSMContext):
    data = await state.get_data()
    field = data.get("cfg_field")
    if not field:
        await state.clear()
        return
    value = message.text.strip()
    await reward_dao.set_config("payment_config", field, value)
    await state.clear()
    await safe_reply(message, "✅ Saqlandi.")
    await _render_payment_config_panel(message)


@router.callback_query(F.data == "adm_mgmt:sponsors:add")
async def callback_sponsors_add(callback: CallbackQuery, state: FSMContext):
    await state.set_state(STATE_ADD_SPONSOR)
    await safe_answer_callback(callback)
    await safe_edit(
        callback,
        "➕ <b>Sponsor qo'shish</b>\n\n"
        "Format:\n"
        "<code>@kanal</code> yoki <code>-100...</code>\n"
        "Ixtiyoriy nom bilan: <code>@kanal Mening kanalim</code>\n\n"
        "Bekor qilish: <code>bekor</code>",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="❌ Bekor", callback_data="adm_mgmt:sponsors:cancel")]]
        ),
    )


@router.callback_query(F.data == "adm_mgmt:sponsors:cancel")
async def callback_sponsors_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await _render_sponsors_panel(callback)


@router.message(StateFilter(STATE_ADD_SPONSOR), F.text.regexp(r"(?i)^(bekor|cancel)$"))
async def message_add_sponsor_cancel(message: Message, state: FSMContext):
    await state.clear()
    await safe_reply(message, "❌ Bekor qilindi.")
    await _render_sponsors_panel(message)


@router.message(StateFilter(STATE_ADD_SPONSOR), F.text)
async def message_add_sponsor_apply(message: Message, state: FSMContext):
    parts = message.text.strip().split(maxsplit=1)
    if not parts:
        await safe_reply(message, "❌ Noto'g'ri format.")
        return
    raw_ref = parts[0]
    custom_title = parts[1].strip() if len(parts) > 1 else ""
    try:
        chat_ref = raw_ref if raw_ref.startswith("@") else int(raw_ref)
        chat = await message.bot.get_chat(chat_ref)
    except Exception as exc:
        logger.warning("Failed to resolve sponsor chat %s: %s", raw_ref, exc)
        await safe_reply(message, "❌ Kanal topilmadi. Bot kanalga admin qilinganini tekshiring.")
        return

    title = custom_title or getattr(chat, "title", "") or raw_ref
    username = getattr(chat, "username", "") or ""
    await sponsor_dao.add_sponsor(channel_id=int(chat.id), username=username, title=title)
    await state.clear()
    await safe_reply(message, "✅ Sponsor qo'shildi.")
    await _render_sponsors_panel(message)


@router.callback_query(F.data.startswith("adm_mgmt:sponsors:toggle:"))
async def callback_sponsor_toggle(callback: CallbackQuery):
    channel_id = int(callback.data.split(":")[-1])
    sponsors = await sponsor_dao.get_all_sponsors()
    sponsor = next((item for item in sponsors if int(item["channel_id"]) == channel_id), None)
    if not sponsor:
        await safe_answer_callback(callback, "❌ Kanal topilmadi.", show_alert=True)
        return
    await sponsor_dao.set_sponsor_active(channel_id, 0 if sponsor.get("is_active") else 1)
    await safe_answer_callback(callback, "✅ Holat yangilandi.")
    await _render_sponsors_panel(callback)


@router.callback_query(F.data.startswith("adm_mgmt:sponsors:delete:"))
async def callback_sponsor_delete(callback: CallbackQuery):
    channel_id = int(callback.data.split(":")[-1])
    await sponsor_dao.delete_sponsor(channel_id)
    await safe_answer_callback(callback, "🗑 O'chirildi.")
    await _render_sponsors_panel(callback)


@router.message(Command("setcard"))
async def cmd_setcard(message: Message, db_user: dict | None = None):
    args = _command_args(message.text or "")
    if not args:
        await safe_reply(message, "Format: <code>/setcard 8600...</code>")
        return
    await reward_dao.set_config("payment_config", "card_number", "".join(args))
    await _render_payment_config_panel(message)


@router.message(Command("setcardholder"))
async def cmd_setcardholder(message: Message, db_user: dict | None = None):
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await safe_reply(message, "Format: <code>/setcardholder CARD HOLDER</code>")
        return
    await reward_dao.set_config("payment_config", "card_holder", parts[1].strip())
    await _render_payment_config_panel(message)


@router.message(Command("setprovider"))
async def cmd_setprovider(message: Message, db_user: dict | None = None):
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await safe_reply(message, "Format: <code>/setprovider Click/Payme</code>")
        return
    await reward_dao.set_config("payment_config", "provider_name", parts[1].strip())
    await _render_payment_config_panel(message)


@router.message(Command("setmanual"))
async def cmd_setmanual(message: Message, db_user: dict | None = None):
    args = _command_args(message.text or "")
    if not args:
        await safe_reply(message, "Format: <code>/setmanual on</code> yoki <code>/setmanual off</code>")
        return
    flag = _parse_bool_flag(args[0])
    if flag is None:
        await safe_reply(message, "Qiymat noto'g'ri. Faqat on/off ishlating.")
        return
    await reward_dao.set_config("payment_config", "manual_enabled", flag)
    await _render_payment_config_panel(message)


@router.message(Command("setstars"))
async def cmd_setstars(message: Message, db_user: dict | None = None):
    args = _command_args(message.text or "")
    if not args:
        await safe_reply(message, "Format: <code>/setstars on</code> yoki <code>/setstars off</code>")
        return
    flag = _parse_bool_flag(args[0])
    if flag is None:
        await safe_reply(message, "Qiymat noto'g'ri. Faqat on/off ishlating.")
        return
    await reward_dao.set_config("payment_config", "stars_enabled", flag)
    await _render_payment_config_panel(message)


@router.message(Command("setreceiptchannel"))
async def cmd_setreceiptchannel(message: Message, db_user: dict | None = None):
    args = _command_args(message.text or "")
    if not args:
        await safe_reply(message, "Format: <code>/setreceiptchannel @kanal</code>")
        return
    await reward_dao.set_config("payment_config", "receipt_channel", args[0].strip())
    await _render_payment_config_panel(message)


@router.message(Command("addsponsor"))
async def cmd_addsponsor(message: Message, db_user: dict | None = None):
    args = _command_args(message.text or "")
    if not args:
        await safe_reply(message, "Format: <code>/addsponsor @kanal</code> yoki <code>/addsponsor -100...</code>")
        return

    raw_ref = args[0]
    try:
        chat_ref = raw_ref if raw_ref.startswith("@") else int(raw_ref)
        chat = await message.bot.get_chat(chat_ref)
    except Exception as exc:
        logger.warning("Failed to resolve sponsor chat %s: %s", raw_ref, exc)
        await safe_reply(message, "Kanal topilmadi. Bot kanalga admin qilinganini tekshiring.")
        return

    title = " ".join(args[1:]).strip() or getattr(chat, "title", "") or raw_ref
    username = getattr(chat, "username", "") or ""
    await sponsor_dao.add_sponsor(channel_id=int(chat.id), username=username, title=title)
    await _render_sponsors_panel(message)


@router.message(Command("togglesponsor"))
async def cmd_togglesponsor(message: Message, db_user: dict | None = None):
    args = _command_args(message.text or "")
    if not args:
        await safe_reply(message, "Format: <code>/togglesponsor @kanal</code>")
        return
    token = args[0]
    sponsors = await sponsor_dao.get_all_sponsors()
    sponsor = next(
        (
            item
            for item in sponsors
            if str(item.get("channel_username", "")).lstrip("@").lower() == token.lstrip("@").lower()
            or str(item.get("channel_id", "")) == token
        ),
        None,
    )
    if not sponsor:
        await safe_reply(message, "Homiy kanal topilmadi.")
        return
    await sponsor_dao.set_sponsor_active(int(sponsor["channel_id"]), 0 if sponsor.get("is_active") else 1)
    await _render_sponsors_panel(message)


@router.message(Command("delsponsor"))
async def cmd_delsponsor(message: Message, db_user: dict | None = None):
    args = _command_args(message.text or "")
    if not args:
        await safe_reply(message, "Format: <code>/delsponsor @kanal</code>")
        return
    token = args[0]
    sponsors = await sponsor_dao.get_all_sponsors()
    sponsor = next(
        (
            item
            for item in sponsors
            if str(item.get("channel_username", "")).lstrip("@").lower() == token.lstrip("@").lower()
            or str(item.get("channel_id", "")) == token
        ),
        None,
    )
    if not sponsor:
        await safe_reply(message, "Homiy kanal topilmadi.")
        return
    await sponsor_dao.delete_sponsor(int(sponsor["channel_id"]))
    await _render_sponsors_panel(message)


@router.message(Command("addadmin"))
async def cmd_addadmin(message: Message, db_user: dict | None = None):
    args = _command_args(message.text or "")
    if not args:
        await safe_reply(message, "Format: <code>/addadmin 123456789</code> yoki <code>/addadmin @username</code>")
        return
    target = await _resolve_user_reference(args[0])
    if not target:
        await safe_reply(message, "Foydalanuvchi topilmadi.")
        return
    await user_dao.set_role(int(target["user_id"]), "admin")
    current_admin_id = db_user.get("user_id") if db_user else None
    await _render_admins_panel(message, current_admin_id=current_admin_id)


@router.message(Command("deladmin"))
async def cmd_deladmin(message: Message, db_user: dict | None = None):
    args = _command_args(message.text or "")
    if not args:
        await safe_reply(message, "Format: <code>/deladmin 123456789</code>")
        return
    target = await _resolve_user_reference(args[0])
    if not target:
        await safe_reply(message, "Foydalanuvchi topilmadi.")
        return
    if int(target["user_id"]) == settings.OWNER_ID or target.get("role") == "owner":
        await safe_reply(message, "Owner rolini pasaytirib bo'lmaydi.")
        return
    await user_dao.set_role(int(target["user_id"]), "user")
    current_admin_id = db_user.get("user_id") if db_user else None
    await _render_admins_panel(message, current_admin_id=current_admin_id)


@router.message(Command("grantsub"))
async def cmd_grantsub(message: Message, db_user: dict | None = None):
    args = _command_args(message.text or "")
    if len(args) < 2:
        await safe_reply(message, "Format: <code>/grantsub 123456789 pro 30</code>")
        return
    target = await _resolve_user_reference(args[0])
    if not target:
        await safe_reply(message, "Foydalanuvchi topilmadi.")
        return
    plan_name = args[1].strip().lower()
    plan = await subscription_dao.get_plan(plan_name)
    if not plan:
        await safe_reply(message, "Plan topilmadi. Masalan: free, standard, pro, premium.")
        return
    days = 30
    if len(args) >= 3:
        try:
            days = int(args[2])
        except ValueError:
            await safe_reply(message, "Kun soni butun son bo'lishi kerak.")
            return
    await subscription_dao.activate_subscription(int(target["user_id"]), plan_name, days)
    await safe_reply(
        message,
        f"Obuna berildi: <code>{target['user_id']}</code> -> <b>{escape_html(plan_name)}</b> ({days} kun)",
    )


@router.message(Command("banuser"))
async def cmd_banuser(message: Message, db_user: dict | None = None):
    args = _command_args(message.text or "")
    if not args:
        await safe_reply(message, "Format: <code>/banuser 123456789</code>")
        return
    target = await _resolve_user_reference(args[0])
    if not target:
        await safe_reply(message, "Foydalanuvchi topilmadi.")
        return
    if int(target["user_id"]) == settings.OWNER_ID:
        await safe_reply(message, "Owner foydalanuvchini ban qilib bo'lmaydi.")
        return
    await user_dao.ban_user(int(target["user_id"]), 1)
    await safe_reply(message, f"User ban qilindi: <code>{target['user_id']}</code>")


@router.message(Command("unbanuser"))
async def cmd_unbanuser(message: Message, db_user: dict | None = None):
    args = _command_args(message.text or "")
    if not args:
        await safe_reply(message, "Format: <code>/unbanuser 123456789</code>")
        return
    target = await _resolve_user_reference(args[0])
    if not target:
        await safe_reply(message, "Foydalanuvchi topilmadi.")
        return
    await user_dao.ban_user(int(target["user_id"]), 0)
    await safe_reply(message, f"User bandan olindi: <code>{target['user_id']}</code>")


@router.callback_query(F.data.startswith("adm_mgmt:"))
async def callback_admin_management_unknown(callback: CallbackQuery, db_user: dict | None = None):
    """
    Fallback for stale/legacy management buttons.
    Keeps panel responsive even if old callback_data still exists in old messages.
    """
    data = callback.data or ""
    await safe_answer_callback(callback, "⚠️ Tugma eskirgan. Bo'lim yangilandi.")
    if ":cfg:" in data:
        await _render_payment_config_panel(callback)
    elif ":sponsors:" in data:
        await _render_sponsors_panel(callback)
    else:
        current_admin_id = (db_user or {}).get("user_id")
        await _render_admins_panel(callback, current_admin_id=current_admin_id)
