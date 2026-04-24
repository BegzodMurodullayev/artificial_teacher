"""
Bot loader — singleton instances of Bot, Dispatcher, and Scheduler.
Import these in handlers and services as needed.
"""

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.config import settings


session = AiohttpSession(limit=settings.TG_CONNECTION_POOL)

bot = Bot(
    token=settings.BOT_TOKEN,
    session=session,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)

dp = Dispatcher(storage=MemoryStorage())

scheduler = AsyncIOScheduler(timezone="UTC")
