"""
Handlers package — central registration point for all routers.
"""

from aiogram import Dispatcher
import logging

logger = logging.getLogger(__name__)


def register_all_handlers(dp: Dispatcher) -> None:
    """Register all bot handler routers with the dispatcher."""

    # Admin handlers (highest priority — checked first)
    from src.bot.handlers.admin import get_admin_router
    dp.include_router(get_admin_router())
    logger.info("  ✓ Admin handlers registered")

    # Subscription handlers
    from src.bot.handlers.subscription import get_subscription_router
    dp.include_router(get_subscription_router())
    logger.info("  ✓ Subscription handlers registered")

    # Quiz handlers
    from src.bot.handlers.quiz import get_quiz_router
    dp.include_router(get_quiz_router())
    logger.info("  ✓ Quiz handlers registered")

    # Group handlers
    from src.bot.handlers.group import get_group_router
    dp.include_router(get_group_router())
    logger.info("  ✓ Group handlers registered")

    # User handlers (lowest priority — catch-all is last)
    from src.bot.handlers.user import get_user_router
    dp.include_router(get_user_router())
    logger.info("  ✓ User handlers registered")
