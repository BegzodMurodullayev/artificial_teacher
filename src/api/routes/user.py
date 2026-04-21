"""
User & Dashboard API routes — /api/user/*, /api/dashboard
"""

from fastapi import APIRouter, Request, HTTPException

from src.api.schemas.models import UserOut, StatsOut, UsageOut, PlanOut, DashboardOut, ProgressOut
from src.database.dao import user_dao, stats_dao, subscription_dao, webapp_dao

router = APIRouter(prefix="/api/user", tags=["User"])


def _get_tg_user(request: Request) -> dict:
    """Extract authenticated Telegram user from request state."""
    tg_user = getattr(request.state, "tg_user", None)
    if not tg_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return tg_user


@router.get("/me", response_model=UserOut)
async def get_me(request: Request):
    """Get current authenticated user."""
    tg = _get_tg_user(request)
    user = await user_dao.get_user(tg["id"])
    if not user:
        user = await user_dao.upsert_user(
            user_id=tg["id"],
            username=tg.get("username", ""),
            first_name=tg.get("first_name", ""),
        )
    return UserOut(**user)


@router.get("/dashboard", response_model=DashboardOut)
async def get_dashboard(request: Request):
    """Get full dashboard data for WebApp home screen."""
    tg = _get_tg_user(request)
    uid = tg["id"]

    user = await user_dao.get_user(uid)
    if not user:
        user = await user_dao.upsert_user(uid, tg.get("username", ""), tg.get("first_name", ""))

    stats = await stats_dao.get_stats(uid)
    usage = await stats_dao.get_usage_today(uid)
    plan_data = await subscription_dao.get_user_plan(uid)
    remaining = await subscription_dao.remaining_days(uid)
    progress = await webapp_dao.get_progress(uid, days=7)

    return DashboardOut(
        user=UserOut(**user),
        stats=StatsOut(**{k: stats.get(k, 0) for k in StatsOut.model_fields}),
        usage_today=UsageOut(**{k: usage.get(k, 0) for k in UsageOut.model_fields}),
        plan=PlanOut(**{k: plan_data.get(k, "") for k in PlanOut.model_fields}),
        remaining_days=remaining,
        progress_week=[
            ProgressOut(**{k: p.get(k, 0) for k in ProgressOut.model_fields})
            for p in progress
        ],
    )


@router.get("/stats", response_model=StatsOut)
async def get_stats(request: Request):
    """Get user statistics."""
    tg = _get_tg_user(request)
    stats = await stats_dao.get_stats(tg["id"])
    return StatsOut(**{k: stats.get(k, 0) for k in StatsOut.model_fields})


@router.get("/usage", response_model=UsageOut)
async def get_usage(request: Request):
    """Get today's usage counters."""
    tg = _get_tg_user(request)
    usage = await stats_dao.get_usage_today(tg["id"])
    return UsageOut(**{k: usage.get(k, 0) for k in UsageOut.model_fields})
