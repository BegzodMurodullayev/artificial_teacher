"""
Centralized configuration — single source of truth.
Uses pydantic-settings to load from .env with type validation.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Telegram ───────────────────────────────────────────
    BOT_TOKEN: str = ""
    OWNER_ID: int = 0
    ADMIN_IDS: str = ""
    BOT_USERNAME: str = "@Artificial_teacher_bot"

    # ── Database ───────────────────────────────────────────
    DB_PATH: str = "data/engbot.db"

    # ── AI ─────────────────────────────────────────────────
    OPENROUTER_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    AI_MODEL: str = "openai/gpt-4o-mini"
    AI_CONCURRENCY: int = 6
    AI_TIMEOUT: int = 30
    AI_MAX_RETRIES: int = 2

    # ── TTS ────────────────────────────────────────────────
    TOPMEDIAI_API_KEY: str = ""
    TOPMEDIAI_API_BASE: str = "https://api.topmediai.com/v1"
    TTS_CONCURRENCY: int = 3

    # ── FastAPI ────────────────────────────────────────────
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8080

    # ── URLs ───────────────────────────────────────────────
    WEB_APP_URL: str = ""
    WEBHOOK_URL: str = ""
    SUPPORT_URL: str = ""
    WEBSITE_URL: str = ""
    CHANNEL_URL: str = ""
    INSTAGRAM_URL: str = ""

    # ── Telegram Channels (for inline caching) ─────────────
    INLINE_HTML_CHANNEL: str | int = 0
    INLINE_AUDIO_CHANNEL: str | int = 0

    # ── Performance ────────────────────────────────────────
    UPDATE_CONCURRENCY: int = 12
    TG_CONNECTION_POOL: int = 12

    # ── Levels ─────────────────────────────────────────────
    LEVELS: list[str] = ["A1", "A2", "B1", "B2", "C1", "C2"]


settings = Settings()
