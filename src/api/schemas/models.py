"""
API Schemas — Pydantic models for request/response validation.
"""

from pydantic import BaseModel, Field
from typing import Optional


# ── User ──

class UserOut(BaseModel):
    user_id: int
    username: str = ""
    first_name: str = ""
    role: str = "user"
    level: str = "A1"
    joined_at: str = ""


# ── Stats ──

class StatsOut(BaseModel):
    checks_total: int = 0
    translations_total: int = 0
    pron_total: int = 0
    quiz_played: int = 0
    quiz_correct: int = 0
    lessons_total: int = 0
    messages_total: int = 0
    streak_days: int = 0
    iq_score: int = 0
    learning_score: int = 0


class UsageOut(BaseModel):
    checks: int = 0
    quiz: int = 0
    lessons: int = 0
    ai_messages: int = 0
    pron_audio: int = 0


# ── Plan ──

class PlanOut(BaseModel):
    name: str
    display_name: str
    price_monthly: float = 0
    price_yearly: float = 0
    checks_per_day: int = 0
    quiz_per_day: int = 0
    lessons_per_day: int = 0
    ai_messages_day: int = 0
    pron_audio_per_day: int = 0
    voice_enabled: int = 0
    inline_enabled: int = 0
    iq_test_enabled: int = 0
    badge: str = ""


# ── Progress ──

class ProgressIn(BaseModel):
    words: int = Field(0, ge=0)
    quiz: int = Field(0, ge=0)
    lessons: int = Field(0, ge=0)
    focus_minutes: int = Field(0, ge=0)
    topics: str = ""
    note: str = ""
    points: int = Field(0, ge=0)


class ProgressOut(BaseModel):
    progress_date: str
    words: int = 0
    quiz: int = 0
    lessons: int = 0
    focus_minutes: int = 0
    topics: str = ""
    note: str = ""
    points: int = 0


# ── Leaderboard ──

class LeaderboardEntry(BaseModel):
    rank: int
    user_id: int
    username: str = ""
    first_name: str = ""
    level: str = "A1"
    total_xp: int = 0
    learning_score: int = 0
    streak_days: int = 0


# ── Dashboard ──

class DashboardOut(BaseModel):
    user: UserOut
    stats: StatsOut
    usage_today: UsageOut
    plan: PlanOut
    remaining_days: int = 0
    progress_week: list[ProgressOut] = []


# ── Quiz ──

class QuizStartIn(BaseModel):
    total_questions: int = Field(10, ge=5, le=30)
    question_timeout: int = Field(45, ge=15, le=120)
    language: str = "en"


class QuizAnswerIn(BaseModel):
    session_id: int
    answer: str  # A, B, C, D, or "skip"
