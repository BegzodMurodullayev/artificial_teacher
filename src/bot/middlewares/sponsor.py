"""
Sponsor check middleware — enforces mandatory channel subscriptions.
Skips for admins/owners and allows through if no sponsors configured.
"""

import logging
from typing import Callable, Awaitable, Any

from aiogram import BaseMiddleware, Bot
from aiogram.types import TelegramObject, Message, CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)


class SponsorMiddleware(BaseMiddleware):
    """
    Checks if user is subscribed to all active sponsor channels.
    Sends subscription prompt if not.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        # Skip for non-private chats
        if isinstance(event, Message) and event.chat.type != "private":
            return await handler(event, data)

        # Skip for admins/owners
        db_user = data.get("db_user")
        if db_user and db_user.get("role") in ("admin", "owner"):
            return await handler(event, data)

        # Check sponsor channels
        from src.database.dao.sponsor_dao import get_active_sponsors
        sponsors = await get_active_sponsors()

        if not sponsors:
            return await handler(event, data)

        bot: Bot = data["bot"]
        user = data.get("event_from_user")
        if not user:
            return await handler(event, data)

        not_subscribed = []
        for sponsor in sponsors:
            try:
                member = await bot.get_chat_member(
                    chat_id=sponsor["channel_id"],
                    user_id=user.id,
                )
                if member.status in ("left", "kicked"):
                    not_subscribed.append(sponsor)
            except Exception:
                # If we can't check, skip this sponsor
                continue

        if not not_subscribed:
            return await handler(event, data)

        # Build subscription prompt
        buttons = []
        for s in not_subscribed:
            username = s.get("channel_username", "")
            title = s.get("title", "Kanal")
            if username:
                url = f"https://t.me/{username.lstrip('@')}"
                buttons.append([InlineKeyboardButton(text=f"📢 {title}", url=url)])

        buttons.append([InlineKeyboardButton(
            text="✅ Tekshirish",
            callback_data="check_sponsor",
        )])

        text = (
            "📢 <b>Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:</b>\n\n"
            "Obuna bo'lgach, <b>✅ Tekshirish</b> tugmasini bosing."
        )

        if isinstance(event, Message):
            await event.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
        elif isinstance(event, CallbackQuery) and event.message:
            await event.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

        return None  # Block handler
