"""
Admin handlers package.
"""

from aiogram import Router


def get_admin_router() -> Router:
    router = Router(name="admin_root")
    from src.bot.handlers.admin.dashboard import router as dashboard_router
    router.include_router(dashboard_router)
    return router
