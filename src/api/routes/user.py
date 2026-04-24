"""
User & Dashboard API routes — /api/user/*, /api/dashboard
"""

from fastapi import APIRouter, Request

from src.api.auth import get_request_user, get_tg_user
from src.api.schemas.models import UserOut, StatsOut, UsageOut, PlanOut, DashboardOut, ProgressOut
from src.database.dao import user_dao, stats_dao, subscription_dao, webapp_dao

router = APIRouter(prefix="/api/user", tags=["User"])


@router.get("/me", response_model=UserOut)
async def get_me(request: Request):
    """Get current authenticated user."""
    user = await get_request_user(request)
    return UserOut(**user)


@router.get("/dashboard", response_model=DashboardOut)
async def get_dashboard(request: Request):
    """Get full dashboard data for WebApp home screen."""
    tg = get_tg_user(request)
    uid = tg["id"]

    user = await get_request_user(request)

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
    tg = get_tg_user(request)
    stats = await stats_dao.get_stats(tg["id"])
    return StatsOut(**{k: stats.get(k, 0) for k in StatsOut.model_fields})


@router.get("/usage", response_model=UsageOut)
async def get_usage(request: Request):
    """Get today's usage counters."""
    tg = get_tg_user(request)
    usage = await stats_dao.get_usage_today(tg["id"])
    return UsageOut(**{k: usage.get(k, 0) for k in UsageOut.model_fields})
