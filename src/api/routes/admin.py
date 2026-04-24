"""
Admin API routes for the WebApp panel.
"""

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from src.api.auth import require_admin_user
from src.bot.loader import bot
from src.database.dao import payment_dao, reward_dao, sponsor_dao, subscription_dao, user_dao
from src.services.broadcast_service import send_broadcast

router = APIRouter(prefix="/api/admin", tags=["Admin"])


class BroadcastIn(BaseModel):
    text: str = Field(min_length=1, max_length=4096)


class PaymentConfigIn(BaseModel):
    provider_name: str | None = None
    card_number: str | None = None
    card_holder: str | None = None
    receipt_channel: str | None = None
    manual_enabled: bool | None = None
    stars_enabled: bool | None = None


class SponsorIn(BaseModel):
    chat_ref: str
    title: str = ""


class RoleIn(BaseModel):
    role: str = Field(pattern="^(user|admin)$")


class BanIn(BaseModel):
    is_banned: bool


class GrantSubscriptionIn(BaseModel):
    plan_name: str
    days: int = Field(default=30, ge=0, le=3650)


async def _payment_summary() -> dict[str, Any]:
    total_users = await user_dao.count_users()
    paid_users = await subscription_dao.count_paid_users()
    pending = await payment_dao.count_pending_payments()
    revenue = await payment_dao.get_total_revenue()
    conversion = f"{(paid_users / total_users * 100):.1f}%" if total_users else "0%"
    return {
        "total_users": total_users,
        "paid_users": paid_users,
        "pending": pending,
        "revenue": revenue,
        "conversion": conversion,
    }


async def _serialize_pending_payments() -> list[dict[str, Any]]:
    payments = await payment_dao.get_pending_payments()
    enriched: list[dict[str, Any]] = []
    for item in payments:
        user = await user_dao.get_user(item["user_id"])
        enriched.append(
            {
                **item,
                "first_name": (user or {}).get("first_name", ""),
                "username": (user or {}).get("username", ""),
            }
        )
    return enriched


async def _approve_or_reject_payment(payment_id: int, action: str, admin_id: int) -> dict[str, Any]:
    payment = await payment_dao.get_payment(payment_id)
    if not payment or payment["status"] != "pending":
        raise HTTPException(status_code=404, detail="Pending payment not found")

    if action == "approve":
        await payment_dao.approve_payment(payment_id, admin_id)
        await subscription_dao.activate_subscription(
            user_id=payment["user_id"],
            plan_name=payment["plan_name"],
            days=payment.get("duration_days", 30),
        )
        try:
            await bot.send_message(
                payment["user_id"],
                (
                    "🎉 <b>To'lov tasdiqlandi!</b>\n\n"
                    f"📋 Reja: <b>{payment['plan_name'].title()}</b>\n"
                    f"📅 Davomiylik: <b>{payment.get('duration_days', 30)} kun</b>"
                ),
            )
        except Exception:
            pass
        return {"status": "approved", "payment_id": payment_id}

    if action == "reject":
        await payment_dao.reject_payment(payment_id, admin_id, "Rejected from WebApp admin")
        try:
            await bot.send_message(
                payment["user_id"],
                f"❌ <b>To'lov #{payment_id} rad etildi.</b>\nMuammo bo'lsa admin bilan bog'laning.",
            )
        except Exception:
            pass
        return {"status": "rejected", "payment_id": payment_id}

    raise HTTPException(status_code=400, detail="Unsupported action")


@router.get("/stats")
async def get_admin_stats(request: Request):
    await require_admin_user(request)
    return await _payment_summary()


@router.get("/payments/pending")
async def get_pending_payments(request: Request):
    await require_admin_user(request)
    return await _serialize_pending_payments()


@router.post("/payments/{payment_id}/{action}")
async def handle_payment_action(payment_id: int, action: str, request: Request):
    admin = await require_admin_user(request)
    return await _approve_or_reject_payment(payment_id, action, admin["user_id"])


@router.post("/broadcast")
async def post_broadcast(payload: BroadcastIn, request: Request):
    await require_admin_user(request)
    return await send_broadcast(payload.text)


@router.get("/users")
async def get_admin_users(
    request: Request,
    query: str | None = Query(default=None),
    limit: int = Query(default=25, ge=1, le=100),
):
    await require_admin_user(request)

    users: list[dict[str, Any]] = []
    if query:
        query = query.strip()
        if query.isdigit():
            user = await user_dao.get_user(int(query))
            users = [user] if user else []
        else:
            user = await user_dao.find_user_by_username(query.lstrip("@"))
            users = [user] if user else []
    else:
        users = await user_dao.get_users_page(limit=limit)

    enriched: list[dict[str, Any]] = []
    for user in users:
        if not user:
            continue
        plan_name = await subscription_dao.get_active_plan_name(user["user_id"])
        remaining_days = await subscription_dao.remaining_days(user["user_id"])
        enriched.append(
            {
                **user,
                "plan_name": plan_name,
                "remaining_days": remaining_days,
            }
        )
    return enriched


@router.post("/users/{user_id}/role")
async def update_user_role(user_id: int, payload: RoleIn, request: Request):
    admin = await require_admin_user(request)
    target = await user_dao.get_user(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.get("role") == "owner" and payload.role != "owner":
        raise HTTPException(status_code=400, detail="Owner role cannot be downgraded")
    if user_id == admin["user_id"] and payload.role == "user":
        raise HTTPException(status_code=400, detail="You cannot downgrade yourself to user")
    await user_dao.set_role(user_id, payload.role)
    return {"status": "ok", "user_id": user_id, "role": payload.role}


@router.post("/users/{user_id}/ban")
async def update_user_ban(user_id: int, payload: BanIn, request: Request):
    admin = await require_admin_user(request)
    if user_id == admin["user_id"]:
        raise HTTPException(status_code=400, detail="You cannot ban yourself")
    await user_dao.ban_user(user_id, 1 if payload.is_banned else 0)
    return {"status": "ok", "user_id": user_id, "is_banned": payload.is_banned}


@router.post("/users/{user_id}/grant-subscription")
async def grant_subscription(user_id: int, payload: GrantSubscriptionIn, request: Request):
    await require_admin_user(request)
    plan = await subscription_dao.get_plan(payload.plan_name)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    await subscription_dao.activate_subscription(user_id, payload.plan_name, payload.days)
    return {"status": "ok", "user_id": user_id, "plan_name": payload.plan_name, "days": payload.days}


@router.get("/plans")
async def get_admin_plans(request: Request):
    await require_admin_user(request)
    return await subscription_dao.get_all_plans()


@router.post("/plans/{plan_name}")
async def update_plan(plan_name: str, payload: dict[str, Any], request: Request):
    await require_admin_user(request)
    current = await subscription_dao.get_plan(plan_name)
    if not current:
        raise HTTPException(status_code=404, detail="Plan not found")

    allowed = {
        "display_name",
        "price_monthly",
        "price_yearly",
        "checks_per_day",
        "quiz_per_day",
        "lessons_per_day",
        "ai_messages_day",
        "pron_audio_per_day",
        "voice_enabled",
        "inline_enabled",
        "group_enabled",
        "iq_test_enabled",
        "badge",
        "is_active",
    }

    for key, value in payload.items():
        if key not in allowed:
            continue
        await subscription_dao.update_plan_field(plan_name, key, value)

    return await subscription_dao.get_plan(plan_name)


@router.get("/settings/payment")
async def get_payment_settings(request: Request):
    await require_admin_user(request)
    config = await reward_dao.get_all_config("payment_config")
    return {
        "provider_name": config.get("provider_name", "Karta"),
        "card_number": config.get("card_number", ""),
        "card_holder": config.get("card_holder", ""),
        "receipt_channel": config.get("receipt_channel", ""),
        "manual_enabled": config.get("manual_enabled", "1") != "0",
        "stars_enabled": config.get("stars_enabled", "1") != "0",
    }


@router.post("/settings/payment")
async def update_payment_settings(payload: PaymentConfigIn, request: Request):
    await require_admin_user(request)
    updates = payload.model_dump(exclude_none=True)
    for key, value in updates.items():
        if isinstance(value, bool):
            await reward_dao.set_config("payment_config", key, "1" if value else "0")
        else:
            await reward_dao.set_config("payment_config", key, str(value))
    return await get_payment_settings(request)


@router.get("/sponsors")
async def get_sponsors(request: Request):
    await require_admin_user(request)
    return await sponsor_dao.get_all_sponsors()


@router.post("/sponsors")
async def add_sponsor(payload: SponsorIn, request: Request):
    await require_admin_user(request)
    try:
        chat_ref = payload.chat_ref if payload.chat_ref.startswith("@") else int(payload.chat_ref)
        chat = await bot.get_chat(chat_ref)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to resolve channel: {exc}") from exc

    title = payload.title.strip() or getattr(chat, "title", "") or payload.chat_ref
    username = getattr(chat, "username", "") or ""
    await sponsor_dao.add_sponsor(int(chat.id), username=username, title=title)
    return await sponsor_dao.get_all_sponsors()


@router.post("/sponsors/{channel_id}/toggle")
async def toggle_sponsor(channel_id: int, request: Request):
    await require_admin_user(request)
    sponsors = await sponsor_dao.get_all_sponsors()
    sponsor = next((item for item in sponsors if int(item["channel_id"]) == channel_id), None)
    if not sponsor:
        raise HTTPException(status_code=404, detail="Sponsor not found")
    await sponsor_dao.set_sponsor_active(channel_id, 0 if sponsor.get("is_active") else 1)
    return await sponsor_dao.get_all_sponsors()


@router.delete("/sponsors/{channel_id}")
async def delete_sponsor(channel_id: int, request: Request):
    await require_admin_user(request)
    await sponsor_dao.delete_sponsor(channel_id)
    return {"status": "ok", "channel_id": channel_id}
