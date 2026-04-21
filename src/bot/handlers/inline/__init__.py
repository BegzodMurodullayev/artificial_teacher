"""
Inline handlers package.
"""

from aiogram import Router


def get_inline_router() -> Router:
    router = Router(name="inline_root")
    from src.bot.handlers.inline.inline_handler import router as inline_router
    router.include_router(inline_router)
    return router
