"""
User handlers package — registers all user-facing routers.
"""

from aiogram import Router


def get_user_router() -> Router:
    """Create and configure the user router with all sub-routers."""
    router = Router(name="user")

    # Import sub-routers
    from src.bot.handlers.user.start import router as start_router
    from src.bot.handlers.user.menu import router as menu_router
    from src.bot.handlers.user.profile import router as profile_router
    from src.bot.handlers.user.lessons import router as lessons_router
    from src.bot.handlers.user.translate import router as translate_router
    from src.bot.handlers.user.pronunciation import router as pronunciation_router
    from src.bot.handlers.user.check import router as check_router
    from src.bot.handlers.user.check import get_check_callback_router
    from src.bot.handlers.user.message_handler import router as message_router

    # Register sub-routers (order matters — specific before generic)
    router.include_router(start_router)         # /start, /help, /settings, level/mode callbacks
    router.include_router(menu_router)           # Reply keyboard button dispatch
    router.include_router(profile_router)        # /mystats, /clear
    router.include_router(lessons_router)        # lesson: and rule: callbacks
    router.include_router(translate_router)
    router.include_router(pronunciation_router)
    router.include_router(check_router)
    router.include_router(get_check_callback_router())  # rpt_prv: / rpt_pub: / aud_prv: / aud_pub: callbacks
    router.include_router(message_router)        # Catch-all text/voice → AI Teacher Smart Router (MUST be last)

    return router
