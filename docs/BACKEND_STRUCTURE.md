# 🐍 Backend Structure — Artificial Teacher v2.0

> Complete backend architecture reference for the `src/` directory.

---

## 📁 Directory Structure

```
src/
├── __init__.py
├── main.py                          # Entry point: Bot + FastAPI + Scheduler
├── config.py                        # Centralized settings (pydantic-settings)
│
├── bot/                             # Telegram Bot (aiogram 3.x)
│   ├── __init__.py
│   ├── loader.py                    # Singletons: Bot, Dispatcher, Scheduler
│   ├── handlers/                    # All message/callback handlers
│   │   ├── __init__.py              # register_all_handlers(dp)
│   │   ├── user/                    # User-facing features
│   │   │   ├── __init__.py          # get_user_router()
│   │   │   ├── start.py             # /start, /help, /settings, level picker
│   │   │   ├── menu.py              # Reply keyboard button dispatcher
│   │   │   ├── message_handler.py   # Smart router (text/voice catch-all)
│   │   │   ├── check.py             # Grammar checking logic
│   │   │   ├── translate.py         # Translation logic
│   │   │   ├── pronunciation.py     # Pronunciation + TTS logic
│   │   │   ├── profile.py           # /mystats, /profile
│   │   │   └── lessons.py           # Lesson/grammar callbacks
│   │   ├── admin/                   # Admin panel
│   │   │   ├── __init__.py          # get_admin_router()
│   │   │   └── dashboard.py         # /admin, payments, broadcast, stats
│   │   ├── quiz/                    # Quiz system
│   │   │   ├── __init__.py          # get_quiz_router()
│   │   │   └── quiz_start.py        # /quiz, question flow, results
│   │   ├── game/                    # Group games
│   │   │   ├── __init__.py          # get_game_router()
│   │   │   ├── word_games_handler.py # Word/error/translation games
│   │   │   ├── mini_games_handler.py # In-chat mini games
│   │   │   └── mafia/               # Mafia game (placeholder)
│   │   ├── subscription/            # Payment flow
│   │   │   ├── __init__.py          # get_subscription_router()
│   │   │   └── plans.py             # /subscribe, plan selection, payment
│   │   ├── group/                   # Group chat handlers
│   │   │   ├── __init__.py          # get_group_router()
│   │   │   └── message.py           # #check, #t, #p, #bot hashtag handlers
│   │   └── inline/                  # Inline queries
│   │       ├── __init__.py          # get_inline_router()
│   │       └── inline_handler.py    # @bot check:, @bot tr:, @bot p:
│   ├── keyboards/
│   │   ├── __init__.py
│   │   └── user_menu.py             # All keyboards + menu aliases
│   ├── middlewares/
│   │   ├── __init__.py
│   │   ├── auth.py                  # User upsert + ban check + owner auto-promote
│   │   ├── throttle.py              # Rate limiting (0.5s per message)
│   │   └── sponsor.py               # Mandatory channel subscription check
│   ├── filters/
│   │   ├── __init__.py
│   │   └── role.py                  # RoleFilter, PlanFilter, IsPrivate, IsGroup
│   ├── utils/
│   │   ├── __init__.py
│   │   └── telegram.py              # safe_reply, safe_edit, escape_html, fmt_num
│   └── jobs/
│       └── daily_word.py            # Scheduled daily word job (08:00 UTC)
│
├── database/                        # Database layer
│   ├── __init__.py
│   ├── connection.py                # Async SQLite singleton + init + migrations
│   ├── models.py                    # 15 dataclass models
│   ├── dao/                         # 12 Data Access Objects
│   │   ├── __init__.py
│   │   ├── user_dao.py              # CRUD for users table
│   │   ├── quiz_dao.py              # Quiz sessions, attempts, question history
│   │   ├── xp_dao.py                # XP transactions, achievements, streaks
│   │   ├── subscription_dao.py      # Plans + subscriptions lifecycle
│   │   ├── payment_dao.py           # Payment CRUD + approval workflow
│   │   ├── stats_dao.py             # Stats + daily usage tracking
│   │   ├── game_dao.py              # Game sessions, scores, participation
│   │   ├── reward_dao.py            # Wallet, referral, promo codes, config
│   │   ├── history_dao.py           # Chat history (for AI context)
│   │   ├── leaderboard_dao.py       # Global leaderboard queries
│   │   ├── sponsor_dao.py           # Sponsor channel management
│   │   └── webapp_dao.py            # WebApp progress data
│   └── migrations/
│       └── init_schema.sql          # Complete schema (374 lines, 20+ tables)
│
├── services/                        # Business logic
│   ├── __init__.py
│   ├── ai_service.py                # OpenRouter client + system prompts
│   ├── ai_teacher_service.py        # Intent detection + teacher Q&A
│   ├── tts_service.py               # TopMediai TTS synthesis
│   ├── level_service.py             # Auto-level adjustment algorithm
│   ├── content_service.py           # Static lessons + grammar + moderation
│   ├── mode_manager.py              # User mode tracking (SQLite-backed)
│   └── transcription_service.py     # OpenAI Whisper voice-to-text
│
├── api/                             # FastAPI REST API
│   ├── __init__.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── user.py                  # /api/user/me, /dashboard, /stats, /usage
│   │   ├── progress.py              # /api/progress/today, /week, /sync
│   │   └── leaderboard.py           # /api/leaderboard/global, /myrank
│   ├── middleware/
│   │   ├── __init__.py
│   │   └── telegram_auth.py         # HMAC-SHA256 initData validation
│   └── schemas/
│       ├── __init__.py
│       └── models.py                # Pydantic request/response models
│
└── templates/                       # Jinja2 templates (currently unused)
```

---

## 🗄 Database Schema

### Core Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `users` | User accounts | `user_id` (PK), `username`, `first_name`, `role`, `level`, `is_banned` |
| `plans` | Subscription plan definitions | `name` (UNIQUE), `display_name`, `price_monthly`, `checks_per_day`, `quiz_per_day`, etc. |
| `subscriptions` | Active user subscriptions | `user_id` (FK), `plan_name`, `started_at`, `expires_at`, `is_active` |
| `payments` | Payment records | `user_id`, `plan_name`, `amount`, `status` (pending/approved/rejected), `receipt_file_id` |
| `payment_config` | Key-value config | `key` (PK), `value` |

### Stats & Usage

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `stats` | Cumulative user statistics | `user_id` (PK), `checks_total`, `quiz_played`, `streak_days`, `iq_score`, `learning_score` |
| `daily_usage` | Per-day usage counters | `user_id + usage_date` (composite PK), `checks`, `quiz`, `ai_messages`, `pron_audio` |
| `history` | Chat history for AI context | `user_id`, `role`, `content`, `created_at` |

### Gamification

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `user_xp` | XP summary cache | `user_id` (PK), `total_xp`, `current_level`, `streak_days`, `daily_xp_today` |
| `xp_transactions` | Immutable XP audit trail | `user_id`, `amount`, `source`, `metadata` (JSON) |
| `achievements` | Achievement definitions | `code` (UNIQUE), `title`, `xp_reward`, `category`, `condition` (JSON) |
| `user_achievements` | Earned achievements | `user_id + achievement_code` (UNIQUE) |

### Quiz & Games

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `quiz_sessions` | DB-backed quiz state | `user_id`, `qtype`, `level`, `status`, `current_question` (JSON), `history` (JSON) |
| `quiz_attempts` | Completed quiz records | `user_id`, `qtype`, `total`, `correct`, `iq_score` |
| `question_history` | Avoid repeated questions | `user_id`, `question_key` |
| `level_signals` | Level estimation signals | `user_id`, `source`, `estimated_level`, `weight` |
| `game_sessions` | Group game state | `chat_id`, `game_type`, `status`, `payload` (JSON) |
| `game_participations` | Game player records | `session_id`, `user_id`, `points_earned` |
| `group_game_scores` | Group leaderboard | `chat_id + user_id` (UNIQUE), `points`, `wins` |

### Other

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `group_settings` | Per-group bot config | `chat_id` (PK), `check_enabled`, `daily_word` |
| `sponsor_channels` | Mandatory subscriptions | `channel_id` (UNIQUE), `channel_username`, `is_active` |
| `reward_wallet` | Referral/points wallet | `user_id` (PK), `points`, `referral_code` (UNIQUE), `referred_by` |
| `promo_codes` | Promo code definitions | `code` (UNIQUE), `plan_name`, `days`, `max_uses`, `used_count` |
| `promo_packs` | Redeemable packs | `name`, `plan_name`, `cost_points` |
| `webapp_progress` | WebApp daily progress | `user_id`, `progress_date`, `words`, `quiz`, `focus_minutes`, `points` |

---

## 📦 DAO Layer

### `user_dao.py`
| Function | Purpose |
|----------|---------|
| `upsert_user(user_id, username, first_name)` | Insert or update user, return user dict |
| `get_user(user_id)` | Get user by ID |
| `set_role(user_id, role)` | Set role (user/admin/owner) |
| `set_level(user_id, level)` | Set English level (A1-C2) |
| `ban_user(user_id, is_banned)` | Ban/unban user |
| `get_all_user_ids()` | Get all non-banned IDs (for broadcast) |
| `count_users()` | Total user count |
| `find_user_by_username(username)` | Search by @username |
| `get_admins()` | List admin/owner users |
| `get_users_page(offset, limit)` | Paginated user list |

### `quiz_dao.py`
| Function | Purpose |
|----------|---------|
| `create_quiz_session(...)` | Create new active quiz session |
| `get_active_quiz_session(user_id)` | Get user's active session |
| `update_quiz_session(session_id, **fields)` | Update session fields |
| `finish_quiz_session(session_id)` | Mark as finished |
| `record_quiz_attempt(...)` | Save completed attempt |
| `get_recent_question_keys(user_id)` | Avoid repeat questions |
| `add_level_signal(...)` | Record level estimation |
| `get_recent_signals(user_id)` | Get signals for auto-adjust |

### `xp_dao.py`
| Function | Purpose |
|----------|---------|
| `add_xp(user_id, amount, source)` | Award XP, recalculate level |
| `get_xp_summary(user_id)` | Get total XP, level, streak |
| `update_streak(user_id)` | Update daily streak |
| `get_achievements()` | List all achievements |
| `get_user_achievements(user_id)` | User's earned achievements |
| `grant_achievement(user_id, code)` | Grant achievement (idempotent) |
| `seed_achievements()` | Seed 13 default achievements |

### `subscription_dao.py`
| Function | Purpose |
|----------|---------|
| `get_plan(name)` | Get plan by name |
| `get_all_plans()` | List all active plans |
| `get_active_subscription(user_id)` | Get non-expired subscription |
| `get_active_plan_name(user_id)` | Get current plan name (→ "free") |
| `get_user_plan(user_id)` | Full plan details for user |
| `activate_subscription(user_id, plan, days)` | Deactivate old + create new |
| `remaining_days(user_id)` | Days left on subscription |
| `deactivate_expired()` | Bulk expire old subscriptions |

### `stats_dao.py`
| Function | Purpose |
|----------|---------|
| `get_stats(user_id)` | Get cumulative stats |
| `inc_stat(user_id, field, amount)` | Increment a stat field |
| `set_stat(user_id, field, value)` | Set stat to specific value |
| `inc_usage(user_id, field)` | Increment daily usage |
| `get_usage_today(user_id)` | Get today's usage counters |
| `check_limit(user_id, field, plan_limit)` | Check if under daily limit |

### `payment_dao.py`
| Function | Purpose |
|----------|---------|
| `create_payment(...)` | Create pending payment |
| `get_payment(payment_id)` | Get by ID |
| `approve_payment(payment_id, admin_id)` | Mark approved |
| `reject_payment(payment_id, admin_id, note)` | Mark rejected |
| `get_pending_payments()` | List all pending |
| `get_total_revenue()` | Sum of approved payments |

### `game_dao.py`
| Function | Purpose |
|----------|---------|
| `create_game_session(chat_id, game_type)` | Start new game |
| `get_active_game(chat_id)` | Get running game for chat |
| `update_game_session(session_id, status, payload)` | Update game state |
| `add_game_points(chat_id, user_id, points)` | Add to leaderboard |
| `get_game_scores(chat_id)` | Get top scores |

### `reward_dao.py`
| Function | Purpose |
|----------|---------|
| `get_wallet(user_id)` | Get/create reward wallet |
| `add_points(user_id, amount)` | Add referral points |
| `deduct_points(user_id, amount)` | Deduct (returns bool) |
| `find_by_referral_code(code)` | Lookup referrer |
| `get_promo_code(code)` | Validate promo code |
| `create_promo_code(...)` | Admin create promo |
| `get_config(table, key)` | Read config value |
| `set_config(table, key, value)` | Write config value |

---

## ⚙️ Services

### `ai_service.py` — OpenRouter AI Client
- **Purpose**: Single point of contact for all AI interactions
- **Key function**: `ask_ai(text, mode, user_id, level, history)` → string response
- **Key function**: `ask_json(text, mode, level)` → parsed JSON dict
- **Concurrency**: Semaphore-limited (default 6 concurrent requests)
- **Retry**: Up to `AI_MAX_RETRIES` (default 2) with exponential backoff
- **System Prompts**: 12 modes — `check`, `translate_uz_en`, `translate_en_uz`, `pronunciation`, `lesson`, `grammar_rule`, `quiz_generate`, `iq_question`, `daily_word`, `bot`, `intent`, `teacher`

### `ai_teacher_service.py` — Intent Router & Teacher Q&A
- **Purpose**: Smart message routing + contextual Q&A
- **`get_intent(text)`**: Classifies into TEACHER/CORRECTION/TRANSLATION/TECHNICAL/PRONUNCIATION
- **`ask_teacher(text, user_id)`**: Answers using bot documentation + chat history

### `tts_service.py` — Text-to-Speech
- **Purpose**: Pronunciation audio via TopMediai API
- **`synthesize_pronunciation(text, accent, gender)`** → MP3 bytes
- **Voices**: US/UK × Male/Female (4 voices)
- **Polling**: Supports async task-based TTS with polling

### `level_service.py` — Auto-Level Adjustment
- **Algorithm**: Signal-based weighted average of last 6 signals
- **Level up**: avg ≥ current + 0.9 AND count ≥ 3
- **Level down**: avg ≤ current - 0.9 AND count ≥ 3
- **Quiz signals**: 90%+ → higher signal (weight 1.5), ≤40% → lower signal

### `content_service.py` — Static Content
- **Lesson Packs**: 3 built-in (greetings, shopping, travel) with vocabulary + grammar + exercises
- **Grammar Rules**: 6 rules (tenses, articles, prepositions, questions, conditionals, passive)
- **Moderation**: Bad word filter (EN/RU/UZ)

### `mode_manager.py` — User Mode Tracking
- **Purpose**: Remember user's selected interaction mode (TEACHER/TRANSLATION/etc.)
- **Storage**: `user_modes` table in SQLite
- **Expiry**: Auto-resets after 600 seconds (10 minutes)

### `transcription_service.py` — Voice-to-Text
- **Purpose**: Transcribe Telegram voice messages using OpenAI Whisper
- **Limit**: Max 60 seconds audio
- **Requires**: `OPENAI_API_KEY` env var

---

## 🔀 Handler Registration Order

Order matters — handlers registered first have higher priority:

```python
# In src/bot/handlers/__init__.py → register_all_handlers(dp)
1. Inline handlers     # Fastest: inline queries
2. Admin handlers      # Checked before user (role-filtered)
3. Subscription handlers
4. Quiz handlers
5. Game handlers
6. Group handlers
7. User handlers       # LAST: catch-all message handler
```

> ⚠️ **Critical**: The `smart_message_handler` in `user/message_handler.py` is a catch-all `F.text | F.voice` handler. It MUST be registered last to avoid intercepting menu buttons, commands, etc.

---

## 🔌 Middleware Pipeline

Applied in order for each incoming update:

```
Message arrives → ThrottleMiddleware → AuthMiddleware → SponsorMiddleware → Handler
```

| Middleware | Rate | Purpose |
|------------|------|---------|
| `ThrottleMiddleware` | 0.5s (msg), 0.3s (callback) | Anti-flood, silently drops |
| `AuthMiddleware` | Every event | Upserts user, injects `db_user`, blocks banned, auto-promotes owner |
| `SponsorMiddleware` | Private only | Checks mandatory channel subs, shows prompt if not subscribed |

---

## 🌐 FastAPI API Routes

| Method | Path | Purpose | Auth |
|--------|------|---------|------|
| `GET` | `/` | Health check | ❌ |
| `GET` | `/health` | Health check | ❌ |
| `GET` | `/api/user/me` | Get current user | ✅ |
| `GET` | `/api/user/dashboard` | Full dashboard data | ✅ |
| `GET` | `/api/user/stats` | User statistics | ✅ |
| `GET` | `/api/user/usage` | Today's usage counters | ✅ |
| `GET` | `/api/progress/today` | Today's progress | ✅ |
| `GET` | `/api/progress/week` | Last 7 days progress | ✅ |
| `POST` | `/api/progress/sync` | Sync progress from WebApp | ✅ |
| `GET` | `/api/leaderboard/global` | Global leaderboard | ✅ |
| `GET` | `/api/leaderboard/myrank` | Current user's rank | ✅ |

**Auth**: Telegram `initData` via `X-Telegram-Init-Data` header, validated with HMAC-SHA256.

---

## 🔑 Key Configuration (`config.py`)

```python
class Settings(BaseSettings):
    # Telegram
    BOT_TOKEN: str              # Bot API token
    OWNER_ID: int               # Auto-promoted to "owner" role
    ADMIN_IDS: str              # Comma-separated admin IDs
    BOT_USERNAME: str           # @Artificial_teacher_bot
    
    # Database
    DB_PATH: str = "data/engbot.db"
    
    # AI (OpenRouter)
    OPENROUTER_API_KEY: str
    AI_MODEL: str = "openai/gpt-4o-mini"
    AI_CONCURRENCY: int = 6     # Max concurrent AI requests
    AI_TIMEOUT: int = 30        # Seconds per request
    
    # TTS
    TOPMEDIAI_API_KEY: str
    
    # FastAPI
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8080
    
    # URLs
    WEB_APP_URL: str            # Netlify WebApp URL
    
    # Levels
    LEVELS: list[str] = ["A1", "A2", "B1", "B2", "C1", "C2"]
```

---

## 🚀 Startup Flow (`main.py`)

```
1. init_db()           → Create tables from SQL, run migrations, seed plans
2. register_middlewares() → Throttle → Auth → Sponsor (order matters)
3. register_all_handlers() → All 7 handler groups
4. Start APScheduler   → daily_word at 08:00 UTC
5. Start FastAPI        → uvicorn on API_HOST:API_PORT (background task)
6. Start bot polling    → dp.start_polling(bot)
```

---

*Last Updated: 2026-04-21*
