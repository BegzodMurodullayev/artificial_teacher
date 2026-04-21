"""
Group handlers package.
"""

from aiogram import Router


def get_group_router() -> Router:
    router = Router(name="group")
    from src.bot.handlers.group.message import router as msg_router
    router.include_router(msg_router)
    return router
