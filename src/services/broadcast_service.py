"""
Broadcast service for sending messages to large user sets in bounded batches.
"""

import asyncio
from typing import Any, Awaitable, Callable

from aiogram.types import Message

from src.bot.loader import bot
from src.config import settings
from src.database.dao import user_dao


ProgressCallback = Callable[[int, int, int, int], Awaitable[None]]


async def send_broadcast(
    text: str = "",
    *,
    batch_size: int = 100,
    progress_callback: ProgressCallback | None = None,
    source_message: Message | None = None,
) -> dict[str, Any]:
    """Send a broadcast message to all active users."""
    if not text and not source_message:
        raise ValueError("Either text or source_message must be provided")

    user_ids = await user_dao.get_all_user_ids()
    total = len(user_ids)
    sent = 0
    failed = 0
    concurrency = max(1, min(settings.TG_CONNECTION_POOL, 32))
    semaphore = asyncio.Semaphore(concurrency)

    async def _send_one(target_user_id: int) -> bool:
        async with semaphore:
            try:
                if source_message:
                    await bot.copy_message(
                        chat_id=target_user_id,
                        from_chat_id=source_message.chat.id,
                        message_id=source_message.message_id,
                    )
                else:
                    await bot.send_message(target_user_id, text)
                return True
            except Exception:
                return False

    for start in range(0, total, batch_size):
        chunk = user_ids[start:start + batch_size]
        results = await asyncio.gather(*(_send_one(uid) for uid in chunk))
        sent += sum(1 for ok in results if ok)
        failed += sum(1 for ok in results if not ok)
        if progress_callback:
            await progress_callback(min(start + len(chunk), total), total, sent, failed)

    return {
        "total": total,
        "sent": sent,
        "failed": failed,
    }
