"""
Additional admin management handlers.
Provides sponsor, payment config, admin-role, and manual moderation tools.
"""

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from src.bot.filters.role import RoleFilter
from src.bot.utils.telegram import escape_html, safe_reply
from src.config import settings
from src.database.dao import reward_dao, sponsor_dao, subscription_dao, user_dao

logger = logging.getLogger(__name__)
router = Router(name="admin_management")

router.message.filter(RoleFilter("admin", "owner"))
router.callback_query.filter(RoleFilter("admin", "owner"))


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


async def _resolve_sponsor_reference(raw: str) -> dict | None:
    token = raw.strip()
    sponsors = await sponsor_dao.get_all_sponsors()
    if token.startswith("@"):
        username = token.lstrip("@").lower()
        return next(
            (
                item
                for item in sponsors
                if str(item.get("channel_username", "")).lstrip("@").lower() == username
            ),
            None,
        )
    try:
        channel_id = int(token)
    except ValueError:
        return None
    return next((item for item in sponsors if int(item.get("channel_id", 0)) == channel_id), None)


def _format_admin_help() -> str:
    return (
        "Buyruqlar:\n"
        "<code>/admins</code>\n"
        "<code>/addadmin 123456789</code> yoki <code>/addadmin @username</code>\n"
        "<code>/deladmin 123456789</code>\n"
        "<code>/grantsub 123456789 pro 30</code>\n"
        "<code>/banuser 123456789</code>\n"
        "<code>/unbanuser 123456789</code>"
    )


def _format_payment_help() -> str:
    return (
        "Buyruqlar:\n"
        "<code>/payconfig</code>\n"
        "<code>/setcard 8600...</code>\n"
        "<code>/setcardholder CARD HOLDER</code>\n"
        "<code>/setprovider Click/Payme</code>\n"
        "<code>/setmanual on|off</code>\n"
        "<code>/setstars on|off</code>\n"
        "<code>/setreceiptchannel @kanal</code>"
    )


def _format_sponsor_help() -> str:
    return (
        "Buyruqlar:\n"
        "<code>/sponsors</code>\n"
        "<code>/addsponsor @kanal</code> yoki <code>/addsponsor -100...</code>\n"
        "<code>/togglesponsor @kanal</code>\n"
        "<code>/delsponsor @kanal</code>"
    )


async def _send_admins_overview(message: Message) -> None:
    admins = await user_dao.get_admins()
    lines = ["<b>Adminlar va ownerlar</b>", ""]
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
    lines.extend(["", _format_admin_help()])
    await safe_reply(message, "\n".join(lines))


async def _send_payment_config(message: Message) -> None:
    cfg = await reward_dao.get_all_config("payment_config")
    text = (
        "<b>To'lov sozlamalari</b>\n\n"
        f"Provider: <code>{escape_html(cfg.get('provider_name', 'Karta'))}</code>\n"
        f"Karta: <code>{escape_html(cfg.get('card_number', 'sozlanmagan'))}</code>\n"
        f"Karta egasi: <code>{escape_html(cfg.get('card_holder', 'sozlanmagan'))}</code>\n"
        f"Manual: <b>{'ON' if cfg.get('manual_enabled', '1') != '0' else 'OFF'}</b>\n"
        f"Stars: <b>{'ON' if cfg.get('stars_enabled', '1') != '0' else 'OFF'}</b>\n"
        f"Receipt channel: <code>{escape_html(cfg.get('receipt_channel', 'sozlanmagan'))}</code>\n\n"
        f"{_format_payment_help()}"
    )
    await safe_reply(message, text)


async def _send_sponsors_overview(message: Message) -> None:
    sponsors = await sponsor_dao.get_all_sponsors()
    lines = ["<b>Homiy kanallar</b>", ""]
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
    lines.extend(["", _format_sponsor_help()])
    await safe_reply(message, "\n".join(lines))


@router.message(F.text == "🛡 Adminlar")
@router.message(Command("admins"))
async def _btn_adm_admins(message: Message, db_user: dict | None = None):
    await _send_admins_overview(message)


@router.message(F.text == "💰 To'lov Sozlamalari")
@router.message(Command("payconfig"))
async def _btn_adm_payment_settings(message: Message, db_user: dict | None = None):
    await _send_payment_config(message)


@router.message(F.text == "📢 Homiy Kanallar")
@router.message(Command("sponsors"))
async def _btn_adm_sponsors(message: Message, db_user: dict | None = None):
    await _send_sponsors_overview(message)


@router.message(Command("setcard"))
async def cmd_setcard(message: Message, db_user: dict | None = None):
    args = _command_args(message.text or "")
    if not args:
        await safe_reply(message, "Format: <code>/setcard 8600...</code>")
        return
    await reward_dao.set_config("payment_config", "card_number", "".join(args))
    await _send_payment_config(message)


@router.message(Command("setcardholder"))
async def cmd_setcardholder(message: Message, db_user: dict | None = None):
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await safe_reply(message, "Format: <code>/setcardholder CARD HOLDER</code>")
        return
    await reward_dao.set_config("payment_config", "card_holder", parts[1].strip())
    await _send_payment_config(message)


@router.message(Command("setprovider"))
async def cmd_setprovider(message: Message, db_user: dict | None = None):
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await safe_reply(message, "Format: <code>/setprovider Click/Payme</code>")
        return
    await reward_dao.set_config("payment_config", "provider_name", parts[1].strip())
    await _send_payment_config(message)


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
    await _send_payment_config(message)


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
    await _send_payment_config(message)


@router.message(Command("setreceiptchannel"))
async def cmd_setreceiptchannel(message: Message, db_user: dict | None = None):
    args = _command_args(message.text or "")
    if not args:
        await safe_reply(message, "Format: <code>/setreceiptchannel @kanal</code>")
        return
    await reward_dao.set_config("payment_config", "receipt_channel", args[0].strip())
    await _send_payment_config(message)


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
    await _send_sponsors_overview(message)


@router.message(Command("togglesponsor"))
async def cmd_togglesponsor(message: Message, db_user: dict | None = None):
    args = _command_args(message.text or "")
    if not args:
        await safe_reply(message, "Format: <code>/togglesponsor @kanal</code>")
        return
    sponsor = await _resolve_sponsor_reference(args[0])
    if not sponsor:
        await safe_reply(message, "Homiy kanal topilmadi.")
        return
    await sponsor_dao.set_sponsor_active(int(sponsor["channel_id"]), 0 if sponsor.get("is_active") else 1)
    await _send_sponsors_overview(message)


@router.message(Command("delsponsor"))
async def cmd_delsponsor(message: Message, db_user: dict | None = None):
    args = _command_args(message.text or "")
    if not args:
        await safe_reply(message, "Format: <code>/delsponsor @kanal</code>")
        return
    sponsor = await _resolve_sponsor_reference(args[0])
    if not sponsor:
        await safe_reply(message, "Homiy kanal topilmadi.")
        return
    await sponsor_dao.delete_sponsor(int(sponsor["channel_id"]))
    await _send_sponsors_overview(message)


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
    await _send_admins_overview(message)


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
    await _send_admins_overview(message)


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
