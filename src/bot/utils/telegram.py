"""
Telegram utility helpers — safe wrappers for sending, editing, deleting messages.
All handlers should use these instead of raw Telegram API calls.
"""

import html
import logging
import re
from typing import Optional

from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

logger = logging.getLogger(__name__)


async def safe_reply(
    message: Message,
    text: str,
    parse_mode: Optional[str] = None,
    reply_markup=None,
    disable_web_page_preview: bool = True,
) -> Optional[Message]:
    """Safely reply to a message, handling common Telegram errors."""
    try:
        return await message.answer(
            text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
            disable_web_page_preview=disable_web_page_preview,
        )
    except TelegramForbiddenError:
        logger.warning("User %s blocked the bot", message.from_user.id if message.from_user else "?")
        return None
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            return None
        logger.warning("safe_reply error: %s", e)
        # Retry without parse_mode if parsing fails
        try:
            return await message.answer(
                text,
                reply_markup=reply_markup,
                disable_web_page_preview=disable_web_page_preview,
            )
        except Exception:
            return None
    except Exception as e:
        logger.exception("Unexpected error in safe_reply: %s", e)
        return None


async def safe_edit(
    target: Message | CallbackQuery,
    text: str,
    parse_mode: Optional[str] = None,
    reply_markup=None,
) -> Optional[Message]:
    """Safely edit a message, handling 'message is not modified' and other errors."""
    try:
        if isinstance(target, CallbackQuery):
            if target.message:
                return await target.message.edit_text(
                    text,
                    parse_mode=parse_mode,
                    reply_markup=reply_markup,
                )
        else:
            return await target.edit_text(
                text,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
            )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            return None
        logger.warning("safe_edit error: %s", e)
        return None
    except Exception as e:
        logger.exception("Unexpected error in safe_edit: %s", e)
        return None
    return None


async def safe_delete(message: Optional[Message]) -> bool:
    """Safely delete a message."""
    if not message:
        return False
    try:
        await message.delete()
        return True
    except Exception:
        return False


async def safe_answer_callback(callback: CallbackQuery, text: str = "", show_alert: bool = False) -> None:
    """Safely answer a callback query."""
    try:
        await callback.answer(text=text, show_alert=show_alert)
    except Exception:
        pass


def escape_html(text: str) -> str:
    """Escape text for HTML parse mode, but preserve basic formatting and convert **bold**."""
    escaped = html.escape(str(text))
    # Convert markdown **bold** to HTML <b>bold</b>
    escaped = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', escaped)
    # Unescape allowed tags that AI might have generated directly
    allowed_tags = ['b', 'i', 's', 'u', 'code', 'pre']
    for tag in allowed_tags:
        escaped = escaped.replace(f"&lt;{tag}&gt;", f"<{tag}>").replace(f"&lt;/{tag}&gt;", f"</{tag}>")
    return escaped


def escape_md(text: str) -> str:
    """Escape text for MarkdownV2 parse mode."""
    return re.sub(r'([_*\[\]()~`>#+\-=|{}.!\\])', r'\\\1', str(text or ""))


def fmt_num(n: int | float) -> str:
    """Format a number with thousand separators."""
    if isinstance(n, float):
        return f"{n:,.1f}".replace(",", " ")
    return f"{n:,}".replace(",", " ")


def fmt_price(amount: float, currency: str = "UZS") -> str:
    """Format a price with currency."""
    if currency == "UZS":
        return f"{int(amount):,} so'm".replace(",", " ")
    return f"${amount:,.2f}"


def truncate(text: str, max_len: int = 4000) -> str:
    """Truncate text to fit Telegram message limits."""
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + "..."
