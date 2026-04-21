"""
Data models — framework-agnostic dataclasses for all domain entities.
Used by services and DAOs. No Telegram or aiogram imports here.
"""

from dataclasses import dataclass, field
from typing import Optional


# ══════════════════════════════════════════════════════════
# CORE ENTITIES
# ══════════════════════════════════════════════════════════

@dataclass
class User:
    user_id: int
    username: str = ""
    first_name: str = ""
    role: str = "user"  # user | admin | owner
    level: str = "A1"   # A1 | A2 | B1 | B2 | C1 | C2
    joined_at: str = ""
    last_seen: str = ""
    is_banned: int = 0


@dataclass
class Plan:
    id: int = 0
    name: str = "free"
    display_name: str = "Free ✨"
    price_monthly: float = 0
    price_yearly: float = 0
    checks_per_day: int = 12
    quiz_per_day: int = 5
    lessons_per_day: int = 3
    ai_messages_day: int = 20
    pron_audio_per_day: int = 5
    voice_enabled: int = 0
    inline_enabled: int = 0
    group_enabled: int = 0
    iq_test_enabled: int = 0
    badge: str = ""
    is_active: int = 1


@dataclass
class Subscription:
    id: int = 0
    user_id: int = 0
    plan_name: str = "free"
    started_at: str = ""
    expires_at: str = ""
    granted_days: int = 30
    is_active: int = 1


@dataclass
class Payment:
    id: int = 0
    user_id: int = 0
    plan_name: str = ""
    amount: float = 0
    duration_days: int = 30
    currency: str = "UZS"
    method: str = "manual"      # manual | stars | click | payme | stripe
    status: str = "pending"     # pending | approved | rejected | expired
    receipt_file_id: str = ""
    note: str = ""
    created_at: str = ""
    reviewed_at: str = ""
    reviewed_by: int = 0


# ══════════════════════════════════════════════════════════
# STATS & USAGE
# ══════════════════════════════════════════════════════════

@dataclass
class UserStats:
    user_id: int = 0
    checks_total: int = 0
    translations_total: int = 0
    pron_total: int = 0
    quiz_played: int = 0
    quiz_correct: int = 0
    lessons_total: int = 0
    messages_total: int = 0
    voice_total: int = 0
    streak_days: int = 0
    iq_score: int = 0
    max_iq_score: int = 0
    learning_score: int = 0


@dataclass
class DailyUsage:
    user_id: int = 0
    usage_date: str = ""
    checks: int = 0
    quiz: int = 0
    lessons: int = 0
    ai_messages: int = 0
    pron_audio: int = 0


# ══════════════════════════════════════════════════════════
# GAMIFICATION
# ══════════════════════════════════════════════════════════

@dataclass
class UserXP:
    user_id: int = 0
    total_xp: int = 0
    current_level: int = 1      # Gamification level (1-100), NOT English level
    xp_to_next: int = 100
    streak_days: int = 0
    longest_streak: int = 0
    last_active_date: str = ""
    daily_xp_today: int = 0
    daily_xp_date: str = ""


@dataclass
class Achievement:
    id: int = 0
    code: str = ""
    title: str = ""
    description: str = ""
    icon: str = "🏅"
    xp_reward: int = 0
    category: str = "general"   # general | quiz | game | social | streak
    condition: str = "{}"       # JSON condition
    is_active: int = 1


@dataclass
class XPTransaction:
    id: int = 0
    user_id: int = 0
    amount: int = 0
    source: str = ""            # quiz_correct | check | game_win | streak | daily_login | pomodoro
    source_id: str = ""
    metadata: str = "{}"
    created_at: str = ""


# ══════════════════════════════════════════════════════════
# QUIZ
# ══════════════════════════════════════════════════════════

@dataclass
class QuizSession:
    id: int = 0
    user_id: int = 0
    qtype: str = "quiz"         # quiz | iq
    level: str = "A1"
    language: str = "en"
    total_questions: int = 10
    question_timeout: int = 45
    asked: int = 0
    answered: int = 0
    correct: int = 0
    xp_earned: int = 0
    status: str = "active"      # active | finished | timeout
    current_question: str = "{}"  # JSON
    history: str = "[]"          # JSON array
    used_keys: str = "[]"        # JSON array
    chat_id: int = 0
    message_id: int = 0
    started_at: str = ""
    finished_at: Optional[str] = None


@dataclass
class QuizAttempt:
    id: int = 0
    user_id: int = 0
    qtype: str = "quiz"
    total: int = 0
    correct: int = 0
    wrong: int = 0
    mode: str = "en"
    level_before: str = "A1"
    level_after: str = "A1"
    iq_score: int = 0
    created_at: str = ""


# ══════════════════════════════════════════════════════════
# GAMES
# ══════════════════════════════════════════════════════════

@dataclass
class GameSession:
    id: int = 0
    chat_id: int = 0
    game_type: str = ""         # word | error | translation | mafia
    status: str = "waiting"     # waiting | running | night | day | finished
    round_number: int = 0
    payload: str = "{}"         # JSON state
    created_by: int = 0
    created_at: str = ""
    updated_at: str = ""
    finished_at: Optional[str] = None


@dataclass
class GameParticipation:
    id: int = 0
    session_id: int = 0
    chat_id: int = 0
    user_id: int = 0
    points_earned: int = 0
    answers_correct: int = 0
    answers_total: int = 0
    joined_at: str = ""


# ══════════════════════════════════════════════════════════
# REWARDS & REFERRAL
# ══════════════════════════════════════════════════════════

@dataclass
class RewardWallet:
    user_id: int = 0
    points: float = 0
    cash_balance: float = 0
    referral_code: str = ""
    referred_by: int = 0
    total_referrals: int = 0


@dataclass
class PromoCode:
    id: int = 0
    code: str = ""
    plan_name: str = ""
    days: int = 0
    max_uses: int = 1
    used_count: int = 0
    created_by: int = 0
    created_at: str = ""
    expires_at: Optional[str] = None
    is_active: int = 1


# ══════════════════════════════════════════════════════════
# GROUPS & SETTINGS
# ══════════════════════════════════════════════════════════

@dataclass
class GroupSettings:
    chat_id: int = 0
    check_enabled: int = 1
    bot_enabled: int = 1
    translate_enabled: int = 1
    pronunciation_enabled: int = 1
    daily_word: int = 0


@dataclass
class SponsorChannel:
    id: int = 0
    channel_id: int = 0
    channel_username: str = ""
    title: str = ""
    is_active: int = 1
