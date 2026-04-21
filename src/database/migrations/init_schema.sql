-- ══════════════════════════════════════════════════════════════
-- Artificial Teacher v2.0 — Complete Database Schema
-- ══════════════════════════════════════════════════════════════

-- ── USERS ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    user_id     INTEGER PRIMARY KEY,
    username    TEXT DEFAULT '',
    first_name  TEXT DEFAULT '',
    role        TEXT DEFAULT 'user',
    level       TEXT DEFAULT 'A1',
    joined_at   TEXT DEFAULT (datetime('now')),
    last_seen   TEXT DEFAULT (datetime('now')),
    is_banned   INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_level ON users(level);
CREATE INDEX IF NOT EXISTS idx_users_last_seen ON users(last_seen);
CREATE INDEX IF NOT EXISTS idx_users_banned ON users(is_banned);

-- ── PLANS ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS plans (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT UNIQUE,
    display_name    TEXT,
    price_monthly   REAL DEFAULT 0,
    price_yearly    REAL DEFAULT 0,
    checks_per_day  INTEGER DEFAULT 5,
    quiz_per_day    INTEGER DEFAULT 3,
    lessons_per_day INTEGER DEFAULT 2,
    ai_messages_day INTEGER DEFAULT 10,
    pron_audio_per_day INTEGER DEFAULT 5,
    voice_enabled   INTEGER DEFAULT 0,
    inline_enabled  INTEGER DEFAULT 0,
    group_enabled   INTEGER DEFAULT 0,
    iq_test_enabled INTEGER DEFAULT 0,
    badge           TEXT DEFAULT '',
    is_active       INTEGER DEFAULT 1
);

-- ── SUBSCRIPTIONS ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS subscriptions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER,
    plan_name   TEXT DEFAULT 'free',
    started_at  TEXT DEFAULT (datetime('now')),
    expires_at  TEXT,
    granted_days INTEGER DEFAULT 30,
    is_active   INTEGER DEFAULT 1,
    FOREIGN KEY(user_id) REFERENCES users(user_id)
);
CREATE INDEX IF NOT EXISTS idx_subs_user ON subscriptions(user_id, is_active);
CREATE INDEX IF NOT EXISTS idx_subs_plan ON subscriptions(plan_name, is_active);
CREATE INDEX IF NOT EXISTS idx_subs_expires ON subscriptions(expires_at);

-- ── PAYMENTS ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS payments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER,
    plan_name       TEXT,
    amount          REAL,
    duration_days   INTEGER DEFAULT 30,
    currency        TEXT DEFAULT 'UZS',
    method          TEXT DEFAULT 'manual',
    status          TEXT DEFAULT 'pending',
    receipt_file_id TEXT DEFAULT '',
    note            TEXT DEFAULT '',
    created_at      TEXT DEFAULT (datetime('now')),
    reviewed_at     TEXT,
    reviewed_by     INTEGER,
    FOREIGN KEY(user_id) REFERENCES users(user_id)
);
CREATE INDEX IF NOT EXISTS idx_pay_user ON payments(user_id);
CREATE INDEX IF NOT EXISTS idx_pay_status ON payments(status);
CREATE INDEX IF NOT EXISTS idx_pay_created ON payments(created_at);

-- ── PAYMENT CONFIG ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS payment_config (
    key     TEXT PRIMARY KEY,
    value   TEXT
);

-- ── DAILY USAGE ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS daily_usage (
    user_id     INTEGER,
    usage_date  TEXT,
    checks      INTEGER DEFAULT 0,
    quiz        INTEGER DEFAULT 0,
    lessons     INTEGER DEFAULT 0,
    ai_messages INTEGER DEFAULT 0,
    pron_audio  INTEGER DEFAULT 0,
    PRIMARY KEY(user_id, usage_date),
    FOREIGN KEY(user_id) REFERENCES users(user_id)
);
CREATE INDEX IF NOT EXISTS idx_usage_date ON daily_usage(user_id, usage_date);

-- ── STATS ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS stats (
    user_id             INTEGER PRIMARY KEY,
    checks_total        INTEGER DEFAULT 0,
    translations_total  INTEGER DEFAULT 0,
    pron_total          INTEGER DEFAULT 0,
    quiz_played         INTEGER DEFAULT 0,
    quiz_correct        INTEGER DEFAULT 0,
    lessons_total       INTEGER DEFAULT 0,
    messages_total      INTEGER DEFAULT 0,
    voice_total         INTEGER DEFAULT 0,
    streak_days         INTEGER DEFAULT 0,
    iq_score            INTEGER DEFAULT 0,
    max_iq_score        INTEGER DEFAULT 0,
    learning_score      INTEGER DEFAULT 0,
    FOREIGN KEY(user_id) REFERENCES users(user_id)
);
CREATE INDEX IF NOT EXISTS idx_stats_streak ON stats(streak_days DESC);

-- ── CHAT HISTORY ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER,
    role        TEXT DEFAULT 'user',
    content     TEXT DEFAULT '',
    created_at  TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(user_id) REFERENCES users(user_id)
);
CREATE INDEX IF NOT EXISTS idx_history_user ON history(user_id);

-- ── QUIZ ATTEMPTS ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS quiz_attempts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER,
    qtype           TEXT DEFAULT 'quiz',
    total           INTEGER DEFAULT 0,
    correct         INTEGER DEFAULT 0,
    wrong           INTEGER DEFAULT 0,
    mode            TEXT DEFAULT 'en',
    level_before    TEXT DEFAULT 'A1',
    level_after     TEXT DEFAULT 'A1',
    iq_score        INTEGER DEFAULT 0,
    created_at      TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(user_id) REFERENCES users(user_id)
);
CREATE INDEX IF NOT EXISTS idx_qa_user ON quiz_attempts(user_id, qtype);

-- ── QUESTION HISTORY (avoid repeats) ──────────────────────
CREATE TABLE IF NOT EXISTS question_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER,
    question_key TEXT,
    asked_at    TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(user_id) REFERENCES users(user_id)
);
CREATE INDEX IF NOT EXISTS idx_qh_user ON question_history(user_id);

-- ── LEVEL SIGNALS ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS level_signals (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER,
    source      TEXT DEFAULT 'check',
    estimated_level TEXT DEFAULT 'A1',
    weight      REAL DEFAULT 1.0,
    created_at  TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(user_id) REFERENCES users(user_id)
);
CREATE INDEX IF NOT EXISTS idx_ls_user ON level_signals(user_id);

-- ── GROUP SETTINGS ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS group_settings (
    chat_id                 INTEGER PRIMARY KEY,
    check_enabled           INTEGER DEFAULT 1,
    bot_enabled             INTEGER DEFAULT 1,
    translate_enabled       INTEGER DEFAULT 1,
    pronunciation_enabled   INTEGER DEFAULT 1,
    daily_word              INTEGER DEFAULT 0
);

-- ── SPONSOR CHANNELS ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS sponsor_channels (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id          INTEGER UNIQUE,
    channel_username    TEXT DEFAULT '',
    title               TEXT DEFAULT '',
    is_active           INTEGER DEFAULT 1
);

-- ── REWARD WALLET ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS reward_wallet (
    user_id         INTEGER PRIMARY KEY,
    points          REAL DEFAULT 0,
    cash_balance    REAL DEFAULT 0,
    referral_code   TEXT UNIQUE DEFAULT '',
    referred_by     INTEGER DEFAULT 0,
    total_referrals INTEGER DEFAULT 0,
    FOREIGN KEY(user_id) REFERENCES users(user_id)
);

-- ── REWARD SETTINGS ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS reward_settings (
    key     TEXT PRIMARY KEY,
    value   TEXT
);

-- ── PROMO CODES ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS promo_codes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    code        TEXT UNIQUE,
    plan_name   TEXT DEFAULT '',
    days        INTEGER DEFAULT 0,
    max_uses    INTEGER DEFAULT 1,
    used_count  INTEGER DEFAULT 0,
    created_by  INTEGER DEFAULT 0,
    created_at  TEXT DEFAULT (datetime('now')),
    expires_at  TEXT,
    is_active   INTEGER DEFAULT 1
);

-- ── PROMO PACKS ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS promo_packs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT DEFAULT '',
    plan_name   TEXT DEFAULT '',
    days        INTEGER DEFAULT 0,
    cost_points REAL DEFAULT 0,
    description TEXT DEFAULT '',
    is_active   INTEGER DEFAULT 1
);

-- ── WEBAPP PROGRESS ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS webapp_progress (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER,
    progress_date   TEXT,
    words           INTEGER DEFAULT 0,
    quiz            INTEGER DEFAULT 0,
    lessons         INTEGER DEFAULT 0,
    focus_minutes   INTEGER DEFAULT 0,
    topics          TEXT DEFAULT '',
    note            TEXT DEFAULT '',
    points          INTEGER DEFAULT 0,
    FOREIGN KEY(user_id) REFERENCES users(user_id)
);
CREATE INDEX IF NOT EXISTS idx_wp_user ON webapp_progress(user_id, progress_date);

-- ══════════════════════════════════════════════════════════
-- GAMIFICATION: XP & ACHIEVEMENTS (NEW in v2.0)
-- ══════════════════════════════════════════════════════════

-- XP transaction log (immutable audit trail)
CREATE TABLE IF NOT EXISTS xp_transactions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    amount      INTEGER NOT NULL,
    source      TEXT NOT NULL,
    source_id   TEXT DEFAULT '',
    metadata    TEXT DEFAULT '{}',
    created_at  TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(user_id) REFERENCES users(user_id)
);
CREATE INDEX IF NOT EXISTS idx_xp_user ON xp_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_xp_source ON xp_transactions(source);
CREATE INDEX IF NOT EXISTS idx_xp_created ON xp_transactions(created_at);

-- User XP summary cache
CREATE TABLE IF NOT EXISTS user_xp (
    user_id         INTEGER PRIMARY KEY,
    total_xp        INTEGER DEFAULT 0,
    current_level   INTEGER DEFAULT 1,
    xp_to_next      INTEGER DEFAULT 100,
    streak_days     INTEGER DEFAULT 0,
    longest_streak  INTEGER DEFAULT 0,
    last_active_date TEXT DEFAULT '',
    daily_xp_today  INTEGER DEFAULT 0,
    daily_xp_date   TEXT DEFAULT '',
    FOREIGN KEY(user_id) REFERENCES users(user_id)
);

-- Achievement definitions
CREATE TABLE IF NOT EXISTS achievements (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    code        TEXT UNIQUE NOT NULL,
    title       TEXT NOT NULL,
    description TEXT DEFAULT '',
    icon        TEXT DEFAULT '🏅',
    xp_reward   INTEGER DEFAULT 0,
    category    TEXT DEFAULT 'general',
    condition   TEXT DEFAULT '{}',
    is_active   INTEGER DEFAULT 1
);

-- User earned achievements
CREATE TABLE IF NOT EXISTS user_achievements (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id          INTEGER NOT NULL,
    achievement_code TEXT NOT NULL,
    earned_at        TEXT DEFAULT (datetime('now')),
    UNIQUE(user_id, achievement_code),
    FOREIGN KEY(user_id) REFERENCES users(user_id)
);
CREATE INDEX IF NOT EXISTS idx_ua_user ON user_achievements(user_id);

-- ══════════════════════════════════════════════════════════
-- GAME ENGINE (NEW in v2.0 — replaces active_group_games)
-- ══════════════════════════════════════════════════════════

-- Game sessions with structured state
CREATE TABLE IF NOT EXISTS game_sessions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id      INTEGER NOT NULL,
    game_type    TEXT NOT NULL,
    status       TEXT DEFAULT 'waiting',
    round_number INTEGER DEFAULT 0,
    payload      TEXT DEFAULT '{}',
    created_by   INTEGER DEFAULT 0,
    created_at   TEXT DEFAULT (datetime('now')),
    updated_at   TEXT DEFAULT (datetime('now')),
    finished_at  TEXT
);
CREATE INDEX IF NOT EXISTS idx_gs_chat ON game_sessions(chat_id, status);

-- Game participation log
CREATE TABLE IF NOT EXISTS game_participations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      INTEGER NOT NULL,
    chat_id         INTEGER NOT NULL,
    user_id         INTEGER NOT NULL,
    points_earned   INTEGER DEFAULT 0,
    answers_correct INTEGER DEFAULT 0,
    answers_total   INTEGER DEFAULT 0,
    joined_at       TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(session_id) REFERENCES game_sessions(id),
    FOREIGN KEY(user_id) REFERENCES users(user_id)
);
CREATE INDEX IF NOT EXISTS idx_gp_user ON game_participations(user_id);
CREATE INDEX IF NOT EXISTS idx_gp_session ON game_participations(session_id);

-- Group game scores (leaderboard — kept for backward compat)
CREATE TABLE IF NOT EXISTS group_game_scores (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id     INTEGER,
    user_id     INTEGER,
    username    TEXT DEFAULT '',
    points      INTEGER DEFAULT 0,
    wins        INTEGER DEFAULT 0,
    UNIQUE(chat_id, user_id)
);
CREATE INDEX IF NOT EXISTS idx_ggs_chat ON group_game_scores(chat_id);
CREATE INDEX IF NOT EXISTS idx_ggs_user ON group_game_scores(user_id);

-- ══════════════════════════════════════════════════════════
-- DB-BACKED QUIZ SESSIONS (NEW in v2.0 — replaces in-memory dict)
-- ══════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS quiz_sessions (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id          INTEGER NOT NULL,
    qtype            TEXT DEFAULT 'quiz',
    level            TEXT DEFAULT 'A1',
    language         TEXT DEFAULT 'en',
    total_questions  INTEGER DEFAULT 10,
    question_timeout INTEGER DEFAULT 45,
    asked            INTEGER DEFAULT 0,
    answered         INTEGER DEFAULT 0,
    correct          INTEGER DEFAULT 0,
    xp_earned        INTEGER DEFAULT 0,
    status           TEXT DEFAULT 'active',
    current_question TEXT DEFAULT '{}',
    history          TEXT DEFAULT '[]',
    used_keys        TEXT DEFAULT '[]',
    chat_id          INTEGER DEFAULT 0,
    message_id       INTEGER DEFAULT 0,
    started_at       TEXT DEFAULT (datetime('now')),
    finished_at      TEXT,
    FOREIGN KEY(user_id) REFERENCES users(user_id)
);
CREATE INDEX IF NOT EXISTS idx_qs_user ON quiz_sessions(user_id, status);
