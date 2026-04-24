"""
Entry point — starts Bot (aiogram), API (FastAPI), and Scheduler (APScheduler).
"""

import asyncio
import logging
import sys
import io
import time

# Fix UnicodeEncodeError for emojis on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import uvicorn

from src.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("artificial_teacher")


def register_all_handlers():
    """Register all bot routers with the dispatcher."""
    from src.bot.loader import dp
    from src.bot.handlers import register_all_handlers as _register
    _register(dp)
    logger.info("All handlers registered")


def register_middlewares():
    """Register all middlewares with the dispatcher."""
    from src.bot.loader import dp
    from src.bot.middlewares.auth import AuthMiddleware
    from src.bot.middlewares.throttle import ThrottleMiddleware
    from src.bot.middlewares.sponsor import SponsorMiddleware

    # Order matters: auth → sponsor  (throttle temporarily disabled for debugging)
    # dp.message.middleware(ThrottleMiddleware(rate_limit=0.5))
    dp.message.middleware(AuthMiddleware())
    dp.message.middleware(SponsorMiddleware())

    # dp.callback_query.middleware(ThrottleMiddleware(rate_limit=0.3))
    dp.callback_query.middleware(AuthMiddleware())
    dp.callback_query.middleware(SponsorMiddleware())

    dp.inline_query.middleware(AuthMiddleware())

    logger.info("All middlewares registered")


def create_api_app():
    """Create FastAPI application with all routes."""
    from fastapi import FastAPI, Request
    from fastapi.middleware.cors import CORSMiddleware
    from src.api.middleware.telegram_auth import TelegramAuthMiddleware

    app = FastAPI(
        title="Artificial Teacher API",
        description="Backend API for the Artificial Teacher WebApp",
        version="2.0.0",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Telegram initData auth
    app.add_middleware(TelegramAuthMiddleware)

    # Health check (supports GET and HEAD for UptimeRobot)
    @app.api_route("/", methods=["GET", "HEAD"])
    async def health(request: Request):
        return {"status": "ok", "service": "Artificial Teacher v2.0", "timestamp": time.time()}

    @app.api_route("/health", methods=["GET", "HEAD"])
    async def health_check(request: Request):
        return {"status": "ok"}

    @app.get("/ping")
    async def ping():
        return "pong"

    # Register API routes
    from src.api.routes.user import router as user_router
    from src.api.routes.progress import router as progress_router
    from src.api.routes.leaderboard import router as leaderboard_router
    from src.api.routes.games import router as games_router
    from src.api.routes.materials import router as materials_router
    from src.api.routes.admin import router as admin_router

    app.include_router(user_router)
    app.include_router(progress_router)
    app.include_router(leaderboard_router)
    app.include_router(games_router)
    app.include_router(materials_router)
    app.include_router(admin_router)

    logger.info("FastAPI app created with %d routes", len(app.routes))
    return app


async def main():
    """Main entry point — orchestrates all services."""
    from src.database.connection import init_db, close_db
    from src.bot.loader import bot, dp, scheduler

    logger.info("=" * 60)
    logger.info("🎓 Artificial Teacher v2.0 — Starting...")
    logger.info("=" * 60)

    # 1. Initialize database
    await init_db()
    logger.info("✅ Database initialized")

    # 1.1 Seed materials if needed (runs synchronously, which is fine on startup)
    try:
        from scripts.seed_materials import seed_materials_async
        seeded_count = await seed_materials_async()
        logger.info("✅ Materials seeded")
    except Exception as e:
        logger.error(f"Error seeding materials: {e}")

    # 2. Register middlewares
    register_middlewares()
    logger.info("✅ Middlewares registered")

    # 3. Register handlers
    register_all_handlers()
    logger.info("✅ Handlers registered")

    # 4. Register scheduled jobs & start scheduler
    from src.bot.jobs.daily_word import send_daily_word
    scheduler.add_job(send_daily_word, "cron", hour=8, minute=0, id="daily_word")
    scheduler.start()
    logger.info("✅ Scheduler started (daily_word at 08:00 UTC)")

    # 5. Start FastAPI in background
    api_app = create_api_app()
    config = uvicorn.Config(
        api_app,
        host=settings.API_HOST,
        port=settings.API_PORT,
        log_level="warning",
    )
    server = uvicorn.Server(config)
    api_task = asyncio.create_task(server.serve())
    logger.info("✅ API server started on %s:%s", settings.API_HOST, settings.API_PORT)

    # 6. Start bot
    try:
        logger.info("🤖 Starting bot polling...")
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
            tasks_concurrency_limit=settings.UPDATE_CONCURRENCY,
        )
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped by user")
    finally:
        scheduler.shutdown()
        await close_db()
        api_task.cancel()
        try:
            await api_task
        except asyncio.CancelledError:
            pass
        logger.info("🛑 Artificial Teacher stopped")


if __name__ == "__main__":
    asyncio.run(main())
