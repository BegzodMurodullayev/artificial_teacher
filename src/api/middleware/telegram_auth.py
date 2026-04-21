"""
Telegram WebApp auth middleware — validates initData using HMAC-SHA256.
"""

import hashlib
import hmac
import json
import logging
import time
from urllib.parse import unquote, parse_qs

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from src.config import settings

logger = logging.getLogger(__name__)


def validate_init_data(init_data: str, bot_token: str) -> dict | None:
    """
    Validate Telegram WebApp initData using HMAC-SHA256.
    Returns parsed user data if valid, None otherwise.
    """
    try:
        parsed = parse_qs(init_data, keep_blank_values=True)
        received_hash = parsed.get("hash", [None])[0]
        if not received_hash:
            return None

        # Build data-check-string
        data_pairs = []
        for key in sorted(parsed.keys()):
            if key != "hash":
                data_pairs.append(f"{key}={unquote(parsed[key][0])}")
        data_check_string = "\n".join(data_pairs)

        # Compute secret key
        secret_key = hmac.new(
            b"WebAppData", bot_token.encode(), hashlib.sha256
        ).digest()

        # Compute hash
        computed_hash = hmac.new(
            secret_key, data_check_string.encode(), hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(computed_hash, received_hash):
            logger.warning("initData hash mismatch")
            return None

        # Check auth_date (not older than 24h)
        auth_date = int(parsed.get("auth_date", ["0"])[0])
        if time.time() - auth_date > 86400:
            logger.warning("initData expired (auth_date=%s)", auth_date)
            return None

        # Parse user
        user_raw = parsed.get("user", [None])[0]
        if user_raw:
            return json.loads(unquote(user_raw))

        return None

    except Exception as e:
        logger.exception("initData validation error: %s", e)
        return None


class TelegramAuthMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware that validates Telegram initData on protected routes.
    Injects `request.state.tg_user` for downstream handlers.
    """

    EXCLUDED_PATHS = {"/", "/health", "/docs", "/openapi.json", "/redoc"}

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Skip auth for excluded paths
        if path in self.EXCLUDED_PATHS or path.startswith("/static"):
            return await call_next(request)

        # Get initData from header or query param
        init_data = request.headers.get("X-Telegram-Init-Data", "")
        if not init_data:
            init_data = request.query_params.get("initData", "")

        if not init_data:
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=401, content={"detail": "Missing Telegram initData"})

        user = validate_init_data(init_data, settings.BOT_TOKEN)
        if not user:
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=403, content={"detail": "Invalid Telegram initData"})

        # Inject user into request state
        request.state.tg_user = user
        return await call_next(request)
