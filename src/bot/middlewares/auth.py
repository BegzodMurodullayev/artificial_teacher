"""
Auth middleware — automatically registers/updates users on every incoming event.
Injects `db_user` dict into handler kwargs for downstream use.
"""

import logging
from typing import Callable, Awaitable, Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseMiddleware):
    """
    Runs before every handler:
    1. Extracts the Telegram user from the event
    2. Upserts them in the database
    3. Injects `db_user` dict into handler data
    4. Blocks banned users
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user:
            from src.database.dao.user_dao import upsert_user, get_user
            db_user = await upsert_user(
                user_id=user.id,
                username=user.username or "",
                first_name=user.first_name or "",
            )
            data["db_user"] = db_user

            # Auto-promote OWNER_ID to owner role
            from src.config import settings
            if db_user and user.id == settings.OWNER_ID and db_user.get("role") != "owner":
                from src.database.dao.user_dao import set_role
                await set_role(user.id, "owner")
                db_user["role"] = "owner"
                logger.info("Auto-promoted user %s to owner", user.id)

            # Block banned users
            if db_user and db_user.get("is_banned"):
                logger.info("Blocked banned user %s", user.id)
                return None
        else:
            data["db_user"] = None

        return await handler(event, data)
