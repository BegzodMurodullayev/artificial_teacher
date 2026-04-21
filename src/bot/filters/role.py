"""
Custom filters for role-based access control, plan gating, and chat type filtering.
"""

from aiogram.filters import Filter
from aiogram.types import Message, CallbackQuery


class RoleFilter(Filter):
    """Filter by user role: admin, owner, or any combination."""

    def __init__(self, *roles: str):
        self.roles = set(roles)

    async def __call__(self, event: Message | CallbackQuery, db_user: dict | None = None) -> bool:
        if not db_user:
            return False
            
        user_role = db_user.get("role", "user")
        if user_role in self.roles:
            return True
            
        # Fallback to config IDs if db role is missing
        user = getattr(event, "from_user", None)
        if user:
            from src.config import settings
            if "owner" in self.roles and user.id == settings.OWNER_ID:
                return True
            if "admin" in self.roles:
                admin_ids = [int(i.strip()) for i in settings.ADMIN_IDS.split(",") if i.strip().isdigit()]
                if user.id in admin_ids or user.id == settings.OWNER_ID:
                    return True
                    
        return False


class PlanFilter(Filter):
    """Filter by minimum subscription plan level."""

    PLAN_ORDER = {"free": 0, "standard": 1, "pro": 2, "premium": 3}

    def __init__(self, min_plan: str = "standard"):
        self.min_level = self.PLAN_ORDER.get(min_plan, 0)

    async def __call__(self, event: Message | CallbackQuery, db_user: dict | None = None) -> bool:
        if not db_user:
            return False
        # Get user's current plan
        from src.database.dao.subscription_dao import get_active_plan_name
        plan_name = await get_active_plan_name(db_user["user_id"])
        user_level = self.PLAN_ORDER.get(plan_name, 0)
        return user_level >= self.min_level


class IsPrivateFilter(Filter):
    """Only allow private (DM) chats."""

    async def __call__(self, event: Message | CallbackQuery) -> bool:
        if isinstance(event, Message):
            return event.chat.type == "private"
        if isinstance(event, CallbackQuery) and event.message:
            return event.message.chat.type == "private"
        return False


class IsGroupFilter(Filter):
    """Only allow group/supergroup chats."""

    async def __call__(self, event: Message | CallbackQuery) -> bool:
        if isinstance(event, Message):
            return event.chat.type in ("group", "supergroup")
        if isinstance(event, CallbackQuery) and event.message:
            return event.message.chat.type in ("group", "supergroup")
        return False


class IsOwnerFilter(Filter):
    """Only allow the bot owner (OWNER_ID from config)."""

    async def __call__(self, event: Message | CallbackQuery, db_user: dict | None = None) -> bool:
        if not db_user:
            return False
        return db_user.get("role") == "owner"
