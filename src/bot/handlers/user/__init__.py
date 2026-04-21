"""
User handlers package — registers all user-facing routers.
"""

from aiogram import Router


def get_user_router() -> Router:
    """Create and configure the user router with all sub-routers."""
    router = Router(name="user")

    # Import sub-routers
    from src.bot.handlers.user.start import router as start_router
    from src.bot.handlers.user.check import router as check_router
    from src.bot.handlers.user.translate import router as translate_router
    from src.bot.handlers.user.pronunciation import router as pronunciation_router
    from src.bot.handlers.user.profile import router as profile_router

    # Register sub-routers (order matters — specific before generic)
    router.include_router(start_router)
    router.include_router(profile_router)
    router.include_router(translate_router)
    router.include_router(pronunciation_router)
    router.include_router(check_router)  # Catch-all — must be last

    return router
