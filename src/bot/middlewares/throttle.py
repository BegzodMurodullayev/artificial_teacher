"""
Throttle middleware — anti-flood rate limiting.
Limits users to 1 message per second (configurable).
"""

import time
import logging
from typing import Callable, Awaitable, Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

logger = logging.getLogger(__name__)


class ThrottleMiddleware(BaseMiddleware):
    """Rate-limit users: max 1 event per `rate_limit` seconds."""

    def __init__(self, rate_limit: float = 0.5):
        self.rate_limit = rate_limit
        self._timestamps: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if not user:
            return await handler(event, data)

        uid = user.id
        now = time.monotonic()
        last = self._timestamps.get(uid, 0)

        if now - last < self.rate_limit:
            logger.debug("Throttled user %s (%.2fs since last)", uid, now - last)
            return None  # Silently drop

        self._timestamps[uid] = now

        # Cleanup old entries periodically (every ~1000 events)
        if len(self._timestamps) > 5000:
            cutoff = now - 60
            self._timestamps = {
                k: v for k, v in self._timestamps.items() if v > cutoff
            }

        return await handler(event, data)
