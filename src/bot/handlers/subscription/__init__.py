"""
Subscription handlers package.
"""

from aiogram import Router


def get_subscription_router() -> Router:
    router = Router(name="subscription")
    from src.bot.handlers.subscription.plans import router as plans_router
    router.include_router(plans_router)
    return router
