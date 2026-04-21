"""
Game handlers package — registers all game-related routers.
"""

from aiogram import Router


def get_game_router() -> Router:
    """Create and configure the game router with all sub-routers."""
    router = Router(name="game")

    from src.bot.handlers.game.mafia.mafia_handler import router as mafia_router
    router.include_router(mafia_router)

    return router
