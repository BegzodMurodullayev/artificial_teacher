"""
Shared API auth helpers.
Keeps bot/webapp roles in sync with Telegram-authenticated requests.
"""

from fastapi import HTTPException, Request

from src.config import settings
from src.database.dao import user_dao


def _configured_admin_ids() -> set[int]:
    admin_ids = {
        int(item.strip())
        for item in settings.ADMIN_IDS.split(",")
        if item.strip().isdigit()
    }
    if settings.OWNER_ID:
        admin_ids.add(settings.OWNER_ID)
    return admin_ids


def get_tg_user(request: Request) -> dict:
    """Extract authenticated Telegram user from request state."""
    tg_user = getattr(request.state, "tg_user", None)
    if not tg_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return tg_user


async def get_request_user(request: Request) -> dict:
    """Upsert request user and reconcile role from config when needed."""
    tg = get_tg_user(request)
    user = await user_dao.upsert_user(
        user_id=tg["id"],
        username=tg.get("username", ""),
        first_name=tg.get("first_name", ""),
    )

    desired_role = None
    if tg["id"] == settings.OWNER_ID and settings.OWNER_ID:
        desired_role = "owner"
    elif tg["id"] in _configured_admin_ids():
        desired_role = "admin"

    if desired_role and user.get("role") != desired_role:
        await user_dao.set_role(tg["id"], desired_role)
        user["role"] = desired_role

    refreshed = await user_dao.get_user(tg["id"])
    return refreshed or user


async def require_admin_user(request: Request) -> dict:
    """Require the authenticated request user to be admin/owner."""
    user = await get_request_user(request)
    if user.get("role") not in {"admin", "owner"}:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
