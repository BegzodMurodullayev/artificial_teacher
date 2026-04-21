"""
Quiz handlers package.
"""

from aiogram import Router


def get_quiz_router() -> Router:
    router = Router(name="quiz_root")
    from src.bot.handlers.quiz.quiz_start import router as quiz_router
    router.include_router(quiz_router)
    return router
