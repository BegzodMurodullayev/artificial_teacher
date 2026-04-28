"""
Game handlers package — registers all game-related routers.
"""

from aiogram import Router


def get_game_router() -> Router:
    """Create and configure the game router with all sub-routers."""
    router = Router(name="game")

    from src.bot.handlers.game.mafia.mafia_handler import router as mafia_router
    from src.bot.handlers.game.group_games_handler import router as group_games_router
    from src.bot.handlers.game.mini_games_handler import router as mini_games_router
    from src.bot.handlers.game.word_games_handler import router as word_games_router

    router.include_router(mafia_router)
    router.include_router(group_games_router)
    router.include_router(mini_games_router)
    router.include_router(word_games_router)

    return router
