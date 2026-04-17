"""
database/db.py - To'liq ma'lumotlar bazasi
Obuna, to'lov, foydalanuvchi, guruh, statistika
"""
import json
import sqlite3, os
from pathlib import Path
from datetime import datetime, date, timedelta

DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "engbot.db"
DB_PATH = os.getenv("DB_PATH", str(DEFAULT_DB_PATH))
LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]

def conn():
    c = sqlite3.connect(DB_PATH, timeout=20)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA synchronous=NORMAL")
    c.execute("PRAGMA busy_timeout=7000")
    c.execute("PRAGMA temp_store=MEMORY")
    c.execute("PRAGMA foreign_keys=ON")
    c.execute("PRAGMA wal_autocheckpoint=1000")
    c.execute("PRAGMA cache_size=-20000")
    return c

def init_db():
    db = conn()
    c = db.cursor()

    # â”€â”€ Foydalanuvchilar â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id     INTEGER PRIMARY KEY,
        username    TEXT DEFAULT '',
        first_name  TEXT DEFAULT '',
        role        TEXT DEFAULT 'user',   -- user | admin | owner
        level       TEXT DEFAULT 'A1',
        joined_at   TEXT DEFAULT (datetime('now')),
        last_seen   TEXT DEFAULT (datetime('now')),
        is_banned   INTEGER DEFAULT 0
    )""")

    # Eski bazalarni moslashtirish (migration)
    user_cols = {row[1] for row in c.execute("PRAGMA table_info(users)").fetchall()}
    if "role" not in user_cols:
        c.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
    if "is_banned" not in user_cols:
        c.execute("ALTER TABLE users ADD COLUMN is_banned INTEGER DEFAULT 0")
    c.execute("UPDATE users SET role='user' WHERE role IS NULL OR role=''")
    c.execute("UPDATE users SET is_banned=0 WHERE is_banned IS NULL")

    # â”€â”€ Obuna rejalari (owner boshqaradi) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    c.execute("""CREATE TABLE IF NOT EXISTS plans (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        name            TEXT UNIQUE,       -- free | standard | pro | premium
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
    )""")

    plan_cols = {row[1] for row in c.execute("PRAGMA table_info(plans)").fetchall()}
    if "pron_audio_per_day" not in plan_cols:
        c.execute("ALTER TABLE plans ADD COLUMN pron_audio_per_day INTEGER DEFAULT 5")

    # â”€â”€ Foydalanuvchi obunalari â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    c.execute("""CREATE TABLE IF NOT EXISTS subscriptions (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     INTEGER,
        plan_name   TEXT DEFAULT 'free',
        started_at  TEXT DEFAULT (datetime('now')),
        expires_at  TEXT,
        granted_days INTEGER DEFAULT 30,
        is_active   INTEGER DEFAULT 1,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )""")
    sub_cols = {row[1] for row in c.execute("PRAGMA table_info(subscriptions)").fetchall()}
    if "granted_days" not in sub_cols:
        c.execute("ALTER TABLE subscriptions ADD COLUMN granted_days INTEGER DEFAULT 30")
    c.execute("UPDATE subscriptions SET granted_days=30 WHERE granted_days IS NULL OR granted_days=0")

    # â”€â”€ To'lovlar â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    c.execute("""CREATE TABLE IF NOT EXISTS payments (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id         INTEGER,
        plan_name       TEXT,
        amount          REAL,
        duration_days   INTEGER DEFAULT 30,
        currency        TEXT DEFAULT 'UZS',
        method          TEXT DEFAULT 'manual',  -- manual | stars | click | payme | stripe
        status          TEXT DEFAULT 'pending', -- pending | approved | rejected | expired
        receipt_file_id TEXT DEFAULT '',        -- Telegram file_id (chek rasmi)
        note            TEXT DEFAULT '',
        created_at      TEXT DEFAULT (datetime('now')),
        reviewed_at     TEXT,
        reviewed_by     INTEGER,                -- admin user_id
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )""")
    pay_cols = {row[1] for row in c.execute("PRAGMA table_info(payments)").fetchall()}
    if "duration_days" not in pay_cols:
        c.execute("ALTER TABLE payments ADD COLUMN duration_days INTEGER DEFAULT 30")
    c.execute("UPDATE payments SET duration_days=30 WHERE duration_days IS NULL OR duration_days=0")

    # â”€â”€ To'lov sozlamalari (admin/owner o'zgartiradi) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    c.execute("""CREATE TABLE IF NOT EXISTS payment_config (
        key     TEXT PRIMARY KEY,
        value   TEXT
    )""")

    # â”€â”€ Foydalanuvchi kunlik limitlari â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    c.execute("""CREATE TABLE IF NOT EXISTS daily_usage (
        user_id     INTEGER,
        usage_date  TEXT,
        checks      INTEGER DEFAULT 0,
        quiz        INTEGER DEFAULT 0,
        lessons     INTEGER DEFAULT 0,
        ai_messages INTEGER DEFAULT 0,
        pron_audio  INTEGER DEFAULT 0,
        PRIMARY KEY(user_id, usage_date)
    )""")
    usage_cols = {row[1] for row in c.execute("PRAGMA table_info(daily_usage)").fetchall()}
    if "pron_audio" not in usage_cols:
        c.execute("ALTER TABLE daily_usage ADD COLUMN pron_audio INTEGER DEFAULT 0")

    c.execute("""CREATE TABLE IF NOT EXISTS webapp_progress (
        user_id             INTEGER,
        progress_date       TEXT,
        focus_minutes       INTEGER DEFAULT 0,
        words_learned       INTEGER DEFAULT 0,
        quiz_completed      INTEGER DEFAULT 0,
        lessons_completed   INTEGER DEFAULT 0,
        points_earned       INTEGER DEFAULT 0,
        updated_at          TEXT DEFAULT (datetime('now')),
        PRIMARY KEY(user_id, progress_date)
    )""")


    # â”€â”€ Statistika â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    c.execute("""CREATE TABLE IF NOT EXISTS stats (
        user_id         INTEGER PRIMARY KEY,
        checks_total    INTEGER DEFAULT 0,
        errors_found    INTEGER DEFAULT 0,
        quiz_played     INTEGER DEFAULT 0,
        quiz_correct    INTEGER DEFAULT 0,
        messages_total  INTEGER DEFAULT 0,
        streak_days     INTEGER DEFAULT 0,
        last_active_day TEXT,
        iq_score        INTEGER DEFAULT 0
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS quiz_attempts (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id         INTEGER NOT NULL,
        qtype           TEXT NOT NULL,
        level_before    TEXT DEFAULT 'A1',
        level_after     TEXT DEFAULT 'A1',
        correct_answers INTEGER DEFAULT 0,
        total_questions INTEGER DEFAULT 0,
        accuracy        REAL DEFAULT 0,
        iq_score        INTEGER DEFAULT 0,
        created_at      TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS question_history (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id         INTEGER NOT NULL,
        qtype           TEXT NOT NULL,
        question_key    TEXT NOT NULL,
        created_at      TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS level_signals (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id         INTEGER NOT NULL,
        source          TEXT DEFAULT 'check',
        suggested_level TEXT NOT NULL,
        created_at      TEXT DEFAULT (datetime('now'))
    )""")

    # â”€â”€ Suhbat tarixi â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    c.execute("""CREATE TABLE IF NOT EXISTS history (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     INTEGER,
        role        TEXT,
        content     TEXT,
        created_at  TEXT DEFAULT (datetime('now'))
    )""")

    # â”€â”€ Guruh sozlamalari â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    c.execute("""CREATE TABLE IF NOT EXISTS group_settings (
        chat_id               INTEGER PRIMARY KEY,
        check_enabled         INTEGER DEFAULT 1,
        bot_enabled           INTEGER DEFAULT 1,
        translate_enabled     INTEGER DEFAULT 1,
        pronunciation_enabled INTEGER DEFAULT 1,
        daily_enabled         INTEGER DEFAULT 1,
        lang                  TEXT DEFAULT 'uz'
    )""")

    group_cols = {row[1] for row in c.execute("PRAGMA table_info(group_settings)").fetchall()}
    if "translate_enabled" not in group_cols:
        c.execute("ALTER TABLE group_settings ADD COLUMN translate_enabled INTEGER DEFAULT 1")
    if "pronunciation_enabled" not in group_cols:
        c.execute("ALTER TABLE group_settings ADD COLUMN pronunciation_enabled INTEGER DEFAULT 1")

    c.execute("""CREATE TABLE IF NOT EXISTS sponsor_channels (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_ref    TEXT UNIQUE,
        chat_id_text TEXT DEFAULT '',
        title       TEXT DEFAULT '',
        join_url    TEXT DEFAULT '',
        bot_is_admin INTEGER DEFAULT 0,
        member_check_ok INTEGER DEFAULT 0,
        last_checked_at TEXT DEFAULT '',
        is_active   INTEGER DEFAULT 1,
        created_at  TEXT DEFAULT (datetime('now'))
    )""")
    sponsor_cols = {row[1] for row in c.execute("PRAGMA table_info(sponsor_channels)").fetchall()}
    if "chat_id_text" not in sponsor_cols:
        c.execute("ALTER TABLE sponsor_channels ADD COLUMN chat_id_text TEXT DEFAULT ''")
    if "bot_is_admin" not in sponsor_cols:
        c.execute("ALTER TABLE sponsor_channels ADD COLUMN bot_is_admin INTEGER DEFAULT 0")
    if "member_check_ok" not in sponsor_cols:
        c.execute("ALTER TABLE sponsor_channels ADD COLUMN member_check_ok INTEGER DEFAULT 0")
    if "last_checked_at" not in sponsor_cols:
        c.execute("ALTER TABLE sponsor_channels ADD COLUMN last_checked_at TEXT DEFAULT ''")

    c.execute("""CREATE TABLE IF NOT EXISTS active_group_games (
        chat_id      INTEGER PRIMARY KEY,
        game_type    TEXT NOT NULL,
        status       TEXT DEFAULT 'running',
        payload      TEXT DEFAULT '{}',
        updated_at   TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS group_game_scores (
        chat_id      INTEGER NOT NULL,
        user_id      INTEGER NOT NULL,
        username     TEXT DEFAULT '',
        points       REAL DEFAULT 0,
        wins         INTEGER DEFAULT 0,
        played       INTEGER DEFAULT 0,
        updated_at   TEXT DEFAULT (datetime('now')),
        PRIMARY KEY(chat_id, user_id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS group_game_settings (
        chat_id                        INTEGER PRIMARY KEY,
        word_time_limit                INTEGER DEFAULT 30,
        word_points                    INTEGER DEFAULT 10,
        error_time_limit               INTEGER DEFAULT 45,
        error_points                   INTEGER DEFAULT 15,
        translation_time_limit         INTEGER DEFAULT 60,
        translation_points_perfect     INTEGER DEFAULT 20,
        translation_points_partial     INTEGER DEFAULT 5,
        mafia_min_players              INTEGER DEFAULT 6,
        mafia_max_players              INTEGER DEFAULT 12,
        mafia_night_time               INTEGER DEFAULT 60,
        mafia_day_time                 INTEGER DEFAULT 120
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS reward_wallet (
        user_id          INTEGER PRIMARY KEY,
        points           REAL DEFAULT 0,
        cash_balance     REAL DEFAULT 0,
        referral_code    TEXT UNIQUE,
        referred_by      INTEGER,
        total_referrals  INTEGER DEFAULT 0,
        total_referral_earnings REAL DEFAULT 0
    )""")

    reward_cols = {row[1] for row in c.execute("PRAGMA table_info(reward_wallet)").fetchall()}
    if "cash_balance" not in reward_cols:
        c.execute("ALTER TABLE reward_wallet ADD COLUMN cash_balance REAL DEFAULT 0")
    if "total_referral_earnings" not in reward_cols:
        c.execute("ALTER TABLE reward_wallet ADD COLUMN total_referral_earnings REAL DEFAULT 0")

    c.execute("""CREATE TABLE IF NOT EXISTS reward_settings (
        key     TEXT PRIMARY KEY,
        value   TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS promo_packs (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        title           TEXT NOT NULL,
        plan_name       TEXT NOT NULL,
        duration_days   INTEGER DEFAULT 7,
        points_cost     INTEGER DEFAULT 0,
        is_active       INTEGER DEFAULT 1,
        created_at      TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS promo_codes (
        code            TEXT PRIMARY KEY,
        points_bonus    INTEGER DEFAULT 0,
        max_uses        INTEGER DEFAULT 1,
        used_count      INTEGER DEFAULT 0,
        is_active       INTEGER DEFAULT 1,
        created_at      TEXT DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS promo_code_redemptions (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        code            TEXT NOT NULL,
        user_id         INTEGER NOT NULL,
        created_at      TEXT DEFAULT (datetime('now')),
        UNIQUE(code, user_id)
    )""")

    # Performance indexes for high-load scenarios
    c.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_users_role_banned ON users(role, is_banned)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_users_last_seen ON users(last_seen)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_user_active ON subscriptions(user_id, is_active)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_plan_active ON subscriptions(plan_name, is_active)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_expires ON subscriptions(expires_at, is_active)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_payments_status_created ON payments(status, created_at)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_payments_user_status ON payments(user_id, status)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_stats_last_active_day ON stats(last_active_day)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_daily_usage_user_date ON daily_usage(user_id, usage_date)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_history_user_id ON history(user_id, id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_quiz_attempts_user_qtype ON quiz_attempts(user_id, qtype, id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_question_history_user_qtype ON question_history(user_id, qtype, id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_level_signals_user_id ON level_signals(user_id, id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_sponsor_active_id ON sponsor_channels(is_active, id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_webapp_progress_user_date ON webapp_progress(user_id, progress_date)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_group_games_status ON active_group_games(status, updated_at)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_group_game_scores_chat_points ON group_game_scores(chat_id, points DESC)")

    # â”€â”€ Default rejalar â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    plans = [
        ("free",     "Free",      0,     0,   12,  5,  2,  20, 5, 0, 0, 0, 0, ""),
        ("standard", "Standard", 29000, 290000, 40, 15,  6,  80, 10, 0, 1, 1, 0, "STD"),
        ("pro",      "Pro",      59000, 590000,120, 40, 20, 250, 20, 1, 1, 1, 1, "PRO"),
        ("premium",  "Premium",  99000, 990000, -1, -1, -1,  -1, 40, 1, 1, 1, 1, "PREM"),
    ]
    for p in plans:
        c.execute("""INSERT OR IGNORE INTO plans
            (name,display_name,price_monthly,price_yearly,
             checks_per_day,quiz_per_day,lessons_per_day,ai_messages_day,pron_audio_per_day,
             voice_enabled,inline_enabled,group_enabled,iq_test_enabled,badge)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", p)

    c.execute("UPDATE plans SET pron_audio_per_day=5 WHERE name='free' AND (pron_audio_per_day IS NULL OR pron_audio_per_day=0)")
    pa_rows = c.execute("SELECT name, pron_audio_per_day FROM plans WHERE name IN ('free','standard','pro','premium')").fetchall()
    pa_map = {row["name"]: int(row["pron_audio_per_day"] or 0) for row in pa_rows}
    if (
        pa_map.get("free") == 5
        and pa_map.get("standard") == 5
        and pa_map.get("pro") == 5
        and pa_map.get("premium") == 5
    ):
        # Legacy fix: old DBlarda yangi ustun default 5 bilan to'lib qolgan bo'ladi.
        c.execute("UPDATE plans SET pron_audio_per_day=10 WHERE name='standard'")
        c.execute("UPDATE plans SET pron_audio_per_day=20 WHERE name='pro'")
        c.execute("UPDATE plans SET pron_audio_per_day=40 WHERE name='premium'")

    # Legacy limitlardan balansli limitlarga yumshoq o'tish (faqat eski qiymat bo'lsa)
    old_limits = {
        "free": (5, 3, 2, 10),
        "standard": (20, 10, 5, 50),
        "pro": (60, 30, 15, 150),
    }
    new_limits = {
        "free": (12, 5, 2, 20),
        "standard": (40, 15, 6, 80),
        "pro": (120, 40, 20, 250),
    }
    for name, old in old_limits.items():
        row = c.execute(
            "SELECT checks_per_day, quiz_per_day, lessons_per_day, ai_messages_day FROM plans WHERE name=?",
            (name,)
        ).fetchone()
        if row and tuple(row) == old:
            nl = new_limits[name]
            c.execute(
                "UPDATE plans SET checks_per_day=?, quiz_per_day=?, lessons_per_day=?, ai_messages_day=? WHERE name=?",
                (nl[0], nl[1], nl[2], nl[3], name),
            )

    # â”€â”€ Default to'lov sozlamalari â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # Reja nomlarini bir xil formatga keltirish (eski ikonali/takror qiymatlar)
    canonical_display = {
        "free": "Free",
        "standard": "Standard",
        "pro": "Pro",
        "premium": "Premium",
    }
    for name, label in canonical_display.items():
        icon = "\U0001F193" if name == "free" else "\u2B50" if name == "standard" else "\U0001F48E" if name == "pro" else "\U0001F451"
        short = "FREE" if name == "free" else "STD" if name == "standard" else "PRO" if name == "pro" else "PREM"
        c.execute(
            """UPDATE plans SET display_name=?
               WHERE name=? AND (
                   display_name IS NULL OR TRIM(display_name)='' OR
                   display_name IN (?, ?, ?, ?, ?, ?, ?)
               )""",
            (
                label, name,
                label,
                f"{icon} {label}",
                f"{icon}{label}",
                f"[{short}] {label}",
                f"[{short}]{label}",
                f"{label.upper()} {label}",
                f"{label} {label}",
            ),
        )

    defaults = [
        ("payment_method",       "manual"),
        ("payment_mode",         "manual"),
        ("payment_provider",     "manual"),
        ("manual_review_enabled", "1"),
        ("checkout_url_template", ""),
        ("checkout_button_label", "Auto to'lovni ochish"),
        ("auto_payment_note",    "Auto to'lov yoqilganda foydalanuvchi checkout sahifasiga yo'naltiriladi."),
        ("card_label",           "Uzcard / Humo"),
        ("card_number",          ""),
        ("card_holder",          ""),
        ("click_merchant",       ""),
        ("payme_merchant",       ""),
        ("provider_token",       ""),
        ("provider_secret",      ""),
        ("stars_enabled",        "0"),
        ("payment_note",         "To'lovni amalga oshirgach, chekni yuboring."),
    ]
    for k, v in defaults:
        c.execute("INSERT OR IGNORE INTO payment_config (key,value) VALUES (?,?)", (k, v))

    reward_defaults = {
        "referral_points": "25",
        "quiz_correct_points": "0.5",
        "payment_referral_percent": "2",
    }
    for k, v in reward_defaults.items():
        existing = c.execute("SELECT value FROM reward_settings WHERE key=?", (k,)).fetchone()
        if not existing:
            c.execute("INSERT INTO reward_settings (key,value) VALUES (?,?)", (k, v))
        elif k == "quiz_correct_points" and str(existing["value"]) == "2":
            c.execute("UPDATE reward_settings SET value=? WHERE key=?", (v, k))

    db.commit()
    db.close()


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# USERS
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def upsert_user(user_id, username, first_name):
    db = conn()
    db.execute("""INSERT INTO users (user_id,username,first_name,last_seen)
        VALUES (?,?,?,datetime('now'))
        ON CONFLICT(user_id) DO UPDATE SET
        username=excluded.username, first_name=excluded.first_name,
        last_seen=datetime('now')""", (user_id, username or "", first_name or ""))
    db.execute("INSERT OR IGNORE INTO stats (user_id) VALUES (?)", (user_id,))
    db.execute(
        "INSERT OR IGNORE INTO reward_wallet (user_id, referral_code) VALUES (?, ?)",
        (user_id, f"AT{user_id}"),
    )
    # Default free obuna
    db.execute("""INSERT OR IGNORE INTO subscriptions (user_id,plan_name,expires_at)
        VALUES (?,?,NULL)""", (user_id, "free"))
    db.commit(); db.close()

def get_user(user_id):
    db = conn()
    r = db.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    db.close()
    return dict(r) if r else None


def find_user_by_username(username):
    lookup = str(username or "").strip().lstrip("@").lower()
    if not lookup:
        return None
    db = conn()
    row = db.execute("SELECT * FROM users WHERE lower(username)=? LIMIT 1", (lookup,)).fetchone()
    db.close()
    return dict(row) if row else None


def get_active_subscription(user_id):
    db = conn()
    r = db.execute("""SELECT * FROM subscriptions
        WHERE user_id=? AND is_active=1
        ORDER BY started_at DESC LIMIT 1""", (user_id,)).fetchone()
    db.close()
    return dict(r) if r else None


def has_pending_payment(user_id):
    db = conn()
    r = db.execute("SELECT 1 FROM payments WHERE user_id=? AND status='pending' LIMIT 1", (user_id,)).fetchone()
    db.close()
    return bool(r)


def get_pending_payment_for_user(user_id):
    db = conn()
    r = db.execute("SELECT * FROM payments WHERE user_id=? AND status='pending' ORDER BY created_at DESC LIMIT 1", (user_id,)).fetchone()
    db.close()
    return dict(r) if r else None


def set_role(user_id, role):
    db = conn()
    db.execute("UPDATE users SET role=? WHERE user_id=?", (role, user_id))
    db.commit(); db.close()

def set_level(user_id, level):
    db = conn()
    db.execute("UPDATE users SET level=? WHERE user_id=?", (level, user_id))
    db.commit(); db.close()

def set_iq_score(user_id, score):
    db = conn()
    db.execute("INSERT OR IGNORE INTO stats (user_id) VALUES (?)", (user_id,))
    db.execute("UPDATE stats SET iq_score=? WHERE user_id=?", (score, user_id))
    db.commit(); db.close()

def ban_user(user_id, banned=True):
    db = conn()
    db.execute("UPDATE users SET is_banned=? WHERE user_id=?", (1 if banned else 0, user_id))
    db.commit(); db.close()

def get_all_users():
    db = conn()
    rows = db.execute("SELECT * FROM users ORDER BY joined_at DESC").fetchall()
    db.close()
    return [dict(r) for r in rows]


def iter_broadcast_user_ids(batch_size=1000):
    batch_size = max(1, int(batch_size or 1000))
    db = conn()
    offset = 0
    try:
        while True:
            rows = db.execute(
                "SELECT user_id FROM users WHERE is_banned=0 ORDER BY user_id LIMIT ? OFFSET ?",
                (batch_size, offset),
            ).fetchall()
            if not rows:
                break
            yield [int(row["user_id"]) for row in rows]
            if len(rows) < batch_size:
                break
            offset += batch_size
    finally:
        db.close()


def get_admin_ids(include_owner=True):
    db = conn()
    rows = db.execute("SELECT user_id FROM users WHERE role IN ('admin','owner')").fetchall()
    db.close()
    ids = {r["user_id"] for r in rows}
    if include_owner:
        owner_id = int(os.getenv("OWNER_ID", "0") or 0)
        if owner_id:
            ids.add(owner_id)
    return sorted(ids)

def get_users_with_active_plans():
    db = conn()
    rows = db.execute("""SELECT
               u.user_id, u.username, u.first_name, u.role, u.is_banned, u.joined_at,
               COALESCE((SELECT s.plan_name FROM subscriptions s
                         WHERE s.user_id = u.user_id AND s.is_active=1
                         ORDER BY s.expires_at DESC, s.id DESC LIMIT 1), 'free') AS plan_name,
               (SELECT s.expires_at FROM subscriptions s
                         WHERE s.user_id = u.user_id AND s.is_active=1
                         ORDER BY s.expires_at DESC, s.id DESC LIMIT 1) AS expires_at
        FROM users u
        ORDER BY u.joined_at DESC""").fetchall()
    db.close()
    return [dict(r) for r in rows]


def iter_users_with_active_plans(batch_size=1000):
    batch_size = max(1, int(batch_size or 1000))
    db = conn()
    try:
        cursor = db.execute("""SELECT
               u.user_id, u.username, u.first_name, u.role, u.level, u.is_banned, u.joined_at,
               COALESCE((SELECT s.plan_name FROM subscriptions s
                         WHERE s.user_id = u.user_id AND s.is_active=1
                         ORDER BY s.expires_at DESC, s.id DESC LIMIT 1), 'free') AS plan_name,
               (SELECT s.expires_at FROM subscriptions s
                         WHERE s.user_id = u.user_id AND s.is_active=1
                         ORDER BY s.expires_at DESC, s.id DESC LIMIT 1) AS expires_at
        FROM users u
        ORDER BY u.joined_at DESC""")
        while True:
            rows = cursor.fetchmany(batch_size)
            if not rows:
                break
            yield [dict(r) for r in rows]
    finally:
        db.close()


def get_user_count():
    db = conn()
    n = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    db.close()
    return n


def get_reward_wallet(user_id):
    db = conn()
    db.execute(
        "INSERT OR IGNORE INTO reward_wallet (user_id, referral_code) VALUES (?, ?)",
        (user_id, f"AT{user_id}"),
    )
    row = db.execute("SELECT * FROM reward_wallet WHERE user_id=?", (user_id,)).fetchone()
    db.commit(); db.close()
    return dict(row) if row else {
        "user_id": user_id,
        "points": 0.0,
        "cash_balance": 0.0,
        "referral_code": f"AT{user_id}",
        "referred_by": None,
        "total_referrals": 0,
        "total_referral_earnings": 0.0,
    }


def get_points(user_id):
    wallet = get_reward_wallet(user_id)
    return float(wallet.get("points", 0) or 0)


def get_cash_balance(user_id):
    wallet = get_reward_wallet(user_id)
    return float(wallet.get("cash_balance", 0) or 0)


def add_points(user_id, amount):
    db = conn()
    db.execute(
        "INSERT OR IGNORE INTO reward_wallet (user_id, referral_code) VALUES (?, ?)",
        (user_id, f"AT{user_id}"),
    )
    db.execute("UPDATE reward_wallet SET points = MAX(points + ?, 0) WHERE user_id=?", (float(amount), user_id))
    db.commit(); db.close()


def add_cash_reward(user_id, amount):
    db = conn()
    db.execute(
        "INSERT OR IGNORE INTO reward_wallet (user_id, referral_code) VALUES (?, ?)",
        (user_id, f"AT{user_id}"),
    )
    db.execute(
        "UPDATE reward_wallet SET cash_balance = MAX(cash_balance + ?, 0), total_referral_earnings = MAX(total_referral_earnings + ?, 0) WHERE user_id=?",
        (float(amount), float(amount), user_id),
    )
    db.commit(); db.close()


def get_reward_setting(key, default=0):
    db = conn()
    row = db.execute("SELECT value FROM reward_settings WHERE key=?", (key,)).fetchone()
    db.close()
    if not row:
        return default
    try:
        return float(row["value"])
    except Exception:
        return default


def set_reward_setting(key, value):
    db = conn()
    db.execute("INSERT OR REPLACE INTO reward_settings (key, value) VALUES (?, ?)", (key, str(value)))
    db.commit(); db.close()


def get_all_reward_settings():
    db = conn()
    rows = db.execute("SELECT * FROM reward_settings").fetchall()
    db.close()
    return {row["key"]: row["value"] for row in rows}


def apply_referral_code(new_user_id, code):
    code = (code or "").strip().upper()
    if code.startswith("REF_"):
        code = code[4:]
    if not code:
        return {"applied": False, "reason": "empty"}
    db = conn()
    db.execute(
        "INSERT OR IGNORE INTO reward_wallet (user_id, referral_code) VALUES (?, ?)",
        (new_user_id, f"AT{new_user_id}"),
    )
    wallet = db.execute("SELECT * FROM reward_wallet WHERE user_id=?", (new_user_id,)).fetchone()
    if wallet and wallet["referred_by"]:
        db.commit(); db.close()
        return {"applied": False, "reason": "already_referred"}
    ref = db.execute("SELECT * FROM reward_wallet WHERE referral_code=?", (code,)).fetchone()
    if not ref or ref["user_id"] == new_user_id:
        db.commit(); db.close()
        return {"applied": False, "reason": "invalid"}
    bonus = get_reward_setting("referral_points", 25)
    db.execute("UPDATE reward_wallet SET referred_by=? WHERE user_id=?", (ref["user_id"], new_user_id))
    db.execute("UPDATE reward_wallet SET points=points+?, total_referrals=total_referrals+1 WHERE user_id=?", (float(bonus), ref["user_id"]))
    db.commit(); db.close()
    return {"applied": True, "referrer_id": ref["user_id"], "bonus": bonus}


def add_promo_pack(title, plan_name, duration_days, points_cost):
    db = conn()
    db.execute(
        """INSERT INTO promo_packs (title, plan_name, duration_days, points_cost, is_active)
           VALUES (?, ?, ?, ?, 1)""",
        (title, plan_name, int(duration_days), int(points_cost)),
    )
    db.commit(); db.close()


def get_promo_packs(active_only=True):
    db = conn()
    sql = "SELECT * FROM promo_packs"
    if active_only:
        sql += " WHERE is_active=1"
    sql += " ORDER BY points_cost ASC, id DESC"
    rows = db.execute(sql).fetchall()
    db.close()
    return [dict(r) for r in rows]


def remove_promo_pack(pack_id):
    db = conn()
    db.execute("DELETE FROM promo_packs WHERE id=?", (pack_id,))
    db.commit(); db.close()


def redeem_promo_pack(user_id, pack_id):
    db = conn()
    db.execute(
        "INSERT OR IGNORE INTO reward_wallet (user_id, referral_code) VALUES (?, ?)",
        (user_id, f"AT{user_id}"),
    )
    pack = db.execute("SELECT * FROM promo_packs WHERE id=? AND is_active=1", (pack_id,)).fetchone()
    wallet = db.execute("SELECT * FROM reward_wallet WHERE user_id=?", (user_id,)).fetchone()
    if not pack or not wallet:
        db.commit(); db.close()
        return {"ok": False, "reason": "not_found"}
    if float(wallet["points"] or 0) < float(pack["points_cost"] or 0):
        db.commit(); db.close()
        return {"ok": False, "reason": "insufficient", "points": float(wallet["points"] or 0)}
    db.execute("UPDATE reward_wallet SET points=points-? WHERE user_id=?", (float(pack["points_cost"]), user_id))
    db.commit(); db.close()
    activate_subscription(user_id, pack["plan_name"], int(pack["duration_days"] or 7))
    return {"ok": True, "pack": dict(pack)}


def add_promo_code(code, points_bonus, max_uses=1):
    db = conn()
    db.execute(
        """INSERT OR REPLACE INTO promo_codes (code, points_bonus, max_uses, used_count, is_active)
           VALUES (?, ?, ?, COALESCE((SELECT used_count FROM promo_codes WHERE code=?), 0), 1)""",
        (code.upper().strip(), float(points_bonus), int(max_uses), code.upper().strip()),
    )
    db.commit(); db.close()


def redeem_promo_code(user_id, code):
    code = code.upper().strip()
    db = conn()
    db.execute(
        "INSERT OR IGNORE INTO reward_wallet (user_id, referral_code) VALUES (?, ?)",
        (user_id, f"AT{user_id}"),
    )
    promo = db.execute("SELECT * FROM promo_codes WHERE code=? AND is_active=1", (code,)).fetchone()
    if not promo:
        db.commit(); db.close()
        return {"ok": False, "reason": "not_found"}
    already = db.execute("SELECT 1 FROM promo_code_redemptions WHERE code=? AND user_id=?", (code, user_id)).fetchone()
    if already:
        db.commit(); db.close()
        return {"ok": False, "reason": "already_used"}
    if int(promo["used_count"] or 0) >= int(promo["max_uses"] or 0):
        db.commit(); db.close()
        return {"ok": False, "reason": "limit"}
    db.execute("INSERT INTO promo_code_redemptions (code, user_id) VALUES (?, ?)", (code, user_id))
    db.execute("UPDATE promo_codes SET used_count=used_count+1 WHERE code=?", (code,))
    db.execute("UPDATE reward_wallet SET points=points+? WHERE user_id=?", (float(promo["points_bonus"] or 0), user_id))
    db.commit(); db.close()
    return {"ok": True, "points": float(promo["points_bonus"] or 0)}

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# SUBSCRIPTIONS & PLANS
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def get_plan(name):
    db = conn()
    r = db.execute("SELECT * FROM plans WHERE name=?", (name,)).fetchone()
    db.close()
    return dict(r) if r else None

def get_all_plans():
    db = conn()
    rows = db.execute("SELECT * FROM plans WHERE is_active=1 ORDER BY price_monthly").fetchall()
    db.close()
    return [dict(r) for r in rows]

def update_plan(name, field, value):
    db = conn()
    db.execute(f"UPDATE plans SET {field}=? WHERE name=?", (value, name))
    db.commit(); db.close()

def get_user_plan(user_id):
    db = conn()
    r = db.execute("""SELECT s.*, p.* FROM subscriptions s
        JOIN plans p ON s.plan_name=p.name
        WHERE s.user_id=? AND s.is_active=1
        ORDER BY p.price_monthly DESC LIMIT 1""", (user_id,)).fetchone()
    db.close()
    if r:
        d = dict(r)
        # Muddati tugaganmi?
        if d.get("expires_at"):
            from datetime import datetime
            if datetime.now() > datetime.fromisoformat(d["expires_at"]):
                # Muddati o'tgan â€” free ga qaytarish
                db2 = conn()
                db2.execute("UPDATE subscriptions SET is_active=0 WHERE user_id=? AND plan_name!=?", (user_id, "free"))
                db2.commit(); db2.close()
                return get_plan("free") | {"plan_name": "free", "expires_at": None}
        return d
    return get_plan("free") | {"plan_name": "free", "expires_at": None}


def get_subscription_credit(user_id):
    current = get_active_subscription(user_id)
    if not current or current.get("plan_name") == "free" or not current.get("expires_at"):
        return {
            "current_plan": "free",
            "remaining_days": 0,
            "credit_amount": 0,
            "granted_days": 0,
        }

    try:
        expires_at = datetime.fromisoformat(current["expires_at"])
    except Exception:
        return {
            "current_plan": current.get("plan_name", "free"),
            "remaining_days": 0,
            "credit_amount": 0,
            "granted_days": int(current.get("granted_days") or 30),
        }

    remaining_seconds = max((expires_at - datetime.now()).total_seconds(), 0)
    remaining_days = remaining_seconds / 86400
    granted_days = max(int(current.get("granted_days") or 30), 1)
    plan = get_plan(current["plan_name"]) or {}
    current_price = plan.get("price_yearly", 0) if granted_days >= 300 else plan.get("price_monthly", 0)
    credit_amount = round((current_price / granted_days) * remaining_days, 2)
    return {
        "current_plan": current.get("plan_name", "free"),
        "remaining_days": round(remaining_days, 1),
        "credit_amount": credit_amount,
        "granted_days": granted_days,
    }


def calculate_plan_quote(user_id, target_plan_name, duration_days):
    target_plan = get_plan(target_plan_name) or {}
    base_amount = target_plan.get("price_yearly", 0) if duration_days >= 300 else target_plan.get("price_monthly", 0)
    credit = get_subscription_credit(user_id)
    current_plan = credit["current_plan"]
    current_plan_row = get_plan(current_plan) or {"price_monthly": 0, "price_yearly": 0}
    target_price_monthly = target_plan.get("price_monthly", 0)
    current_price_monthly = current_plan_row.get("price_monthly", 0)

    can_upgrade = current_plan not in ("free", target_plan_name) and target_price_monthly > current_price_monthly
    credit_amount = credit["credit_amount"] if can_upgrade else 0
    final_amount = max(round(base_amount - credit_amount, 2), 0)
    return {
        "base_amount": base_amount,
        "credit_amount": credit_amount,
        "final_amount": final_amount,
        "current_plan": current_plan,
        "remaining_days": credit["remaining_days"],
        "can_upgrade": can_upgrade,
    }

def activate_subscription(user_id, plan_name, days=30):
    db = conn()
    now = datetime.now()
    current = db.execute("""SELECT * FROM subscriptions
        WHERE user_id=? AND is_active=1
        ORDER BY started_at DESC LIMIT 1""", (user_id,)).fetchone()

    if current and current["plan_name"] == plan_name and current["expires_at"]:
        try:
            cur_exp = datetime.fromisoformat(current["expires_at"])
            new_exp = cur_exp + timedelta(days=days)
        except Exception:
            new_exp = now + timedelta(days=days)
        db.execute("UPDATE subscriptions SET expires_at=? WHERE id=?", (new_exp.isoformat(), current["id"]))
        db.commit(); db.close()
        return

    # deactivate old
    db.execute("UPDATE subscriptions SET is_active=0 WHERE user_id=?", (user_id,))

    if plan_name == "free":
        expires = None
    else:
        expires = (now + timedelta(days=days)).isoformat()

    db.execute("""INSERT INTO subscriptions (user_id,plan_name,expires_at,granted_days,is_active)
        VALUES (?,?,?,?,1)""", (user_id, plan_name, expires, days))
    db.commit(); db.close()


def set_subscription(user_id, plan_name, days=30):
    db = conn()
    expires = (datetime.now() + timedelta(days=days)).isoformat()
    # Oldingi obunani o'chirish
    db.execute("UPDATE subscriptions SET is_active=0 WHERE user_id=?", (user_id,))
    db.execute("""INSERT INTO subscriptions (user_id,plan_name,expires_at,granted_days,is_active)
        VALUES (?,?,?,?,1)""", (user_id, plan_name, expires if plan_name != "free" else None, days))
    db.commit(); db.close()


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# PAYMENTS
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def create_payment(user_id, plan_name, amount, duration_days=30, method="manual", receipt_file_id=""):
    db = conn()
    db.execute("""INSERT INTO payments (user_id,plan_name,amount,duration_days,method,receipt_file_id)
        VALUES (?,?,?,?,?,?)""", (user_id, plan_name, amount, duration_days, method, receipt_file_id))
    payment_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    db.commit(); db.close()
    return payment_id

def get_payment(payment_id):
    db = conn()
    r = db.execute("SELECT * FROM payments WHERE id=?", (payment_id,)).fetchone()
    db.close()
    return dict(r) if r else None

def approve_payment(payment_id, admin_id):
    db = conn()
    p = db.execute("SELECT * FROM payments WHERE id=?", (payment_id,)).fetchone()
    if not p:
        db.close()
        return None

    db.execute(
        """UPDATE payments SET status='approved', reviewed_at=datetime('now'),
            reviewed_by=? WHERE id=?""",
        (admin_id, payment_id),
    )
    db.commit()
    payment = dict(p)
    db.close()

    activate_subscription(payment["user_id"], payment["plan_name"], int(payment.get("duration_days") or 30))

    wallet = get_reward_wallet(payment["user_id"])
    referrer_id = wallet.get("referred_by")
    referral_bonus = 0.0
    if referrer_id:
        percent = float(get_reward_setting("payment_referral_percent", 2) or 0)
        amount = float(payment.get("amount") or 0)
        referral_bonus = round(amount * (percent / 100.0), 2)
        if referral_bonus > 0:
            add_cash_reward(referrer_id, referral_bonus)

    payment["referral_bonus"] = referral_bonus
    payment["referrer_id"] = referrer_id
    return payment

def reject_payment(payment_id, admin_id, note=""):
    db = conn()
    db.execute("""UPDATE payments SET status='rejected', reviewed_at=datetime('now'),
        reviewed_by=?, note=? WHERE id=?""", (admin_id, note, payment_id))
    db.commit(); db.close()

def get_pending_payments():
    db = conn()
    rows = db.execute("""SELECT p.*, u.first_name, u.username
        FROM payments p JOIN users u ON p.user_id=u.user_id
        WHERE p.status='pending' ORDER BY p.created_at""").fetchall()
    db.close()
    return [dict(r) for r in rows]

def get_user_payments(user_id):
    db = conn()
    rows = db.execute("SELECT * FROM payments WHERE user_id=? ORDER BY created_at DESC LIMIT 10",
        (user_id,)).fetchall()
    db.close()
    return [dict(r) for r in rows]


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# PAYMENT CONFIG
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def get_pay_config(key, default=""):
    db = conn()
    r = db.execute("SELECT value FROM payment_config WHERE key=?", (key,)).fetchone()
    db.close()
    return r["value"] if r else default

def set_pay_config(key, value):
    db = conn()
    db.execute("INSERT OR REPLACE INTO payment_config (key,value) VALUES (?,?)", (key, value))
    db.commit(); db.close()

def get_all_pay_config():
    db = conn()
    rows = db.execute("SELECT * FROM payment_config").fetchall()
    db.close()
    return {r["key"]: r["value"] for r in rows}


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# DAILY LIMITS
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def get_usage(user_id):
    today = str(date.today())
    db = conn()
    db.execute("INSERT OR IGNORE INTO daily_usage (user_id,usage_date) VALUES (?,?)", (user_id, today))
    r = db.execute("SELECT * FROM daily_usage WHERE user_id=? AND usage_date=?",
        (user_id, today)).fetchone()
    db.commit(); db.close()
    return dict(r)

def inc_usage(user_id, field):
    today = str(date.today())
    db = conn()
    db.execute("INSERT OR IGNORE INTO daily_usage (user_id,usage_date) VALUES (?,?)", (user_id, today))
    db.execute(f"UPDATE daily_usage SET {field}={field}+1 WHERE user_id=? AND usage_date=?",
        (user_id, today))
    db.commit(); db.close()

def check_limit(user_id, field) -> tuple[bool, int, int]:
    """(allowed, used, limit) qaytaradi. limit=-1 cheksiz"""
    plan = get_user_plan(user_id)
    limit_map = {
        "checks":      "checks_per_day",
        "quiz":        "quiz_per_day",
        "lessons":     "lessons_per_day",
        "ai_messages": "ai_messages_day",
        "pron_audio":  "pron_audio_per_day",
    }
    limit_field = limit_map.get(field, "ai_messages_day")
    limit = plan.get(limit_field, 5)
    if limit == -1:
        return True, 0, -1
    usage = get_usage(user_id)
    used = usage.get(field, 0)
    return used < limit, used, limit


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# STATS
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def inc_stat(user_id, field, amount=1):
    db = conn()
    db.execute(f"UPDATE stats SET {field}={field}+? WHERE user_id=?", (amount, user_id))
    today = str(date.today())
    yesterday = str(date.today() - timedelta(days=1))
    r = db.execute("SELECT last_active_day FROM stats WHERE user_id=?", (user_id,)).fetchone()
    if r:
        last = r["last_active_day"]
        if last == today:
            pass
        elif last == yesterday:
            db.execute("UPDATE stats SET streak_days=streak_days+1, last_active_day=? WHERE user_id=?",
                (today, user_id))
        else:
            db.execute("UPDATE stats SET streak_days=1, last_active_day=? WHERE user_id=?",
                (today, user_id))
    db.commit(); db.close()

def get_stats(user_id):
    db = conn()
    r = db.execute("SELECT * FROM stats WHERE user_id=?", (user_id,)).fetchone()
    db.close()
    return dict(r) if r else None

def add_quiz_attempt(user_id, qtype, level_before, level_after, correct_answers, total_questions, iq_score=0):
    accuracy = round((correct_answers / total_questions) * 100, 2) if total_questions else 0
    db = conn()
    db.execute(
        """INSERT INTO quiz_attempts
           (user_id, qtype, level_before, level_after, correct_answers, total_questions, accuracy, iq_score)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, qtype, level_before, level_after, correct_answers, total_questions, accuracy, iq_score),
    )
    db.commit(); db.close()

def remember_question_key(user_id, qtype, question_key):
    if not question_key:
        return
    db = conn()
    db.execute(
        "INSERT INTO question_history (user_id, qtype, question_key) VALUES (?, ?, ?)",
        (user_id, qtype, question_key),
    )
    db.execute(
        """DELETE FROM question_history
           WHERE user_id=? AND qtype=? AND id NOT IN (
               SELECT id FROM question_history
               WHERE user_id=? AND qtype=?
               ORDER BY id DESC LIMIT 120
           )""",
        (user_id, qtype, user_id, qtype),
    )
    db.commit(); db.close()

def get_recent_question_keys(user_id, qtype, limit=80):
    db = conn()
    rows = db.execute(
        """SELECT question_key FROM question_history
           WHERE user_id=? AND qtype=?
           ORDER BY id DESC LIMIT ?""",
        (user_id, qtype, limit),
    ).fetchall()
    db.close()
    return [r["question_key"] for r in rows]

def record_level_signal(user_id, source, suggested_level):
    if suggested_level not in LEVELS:
        return
    db = conn()
    db.execute(
        "INSERT INTO level_signals (user_id, source, suggested_level) VALUES (?, ?, ?)",
        (user_id, source or "check", suggested_level),
    )
    db.execute(
        """DELETE FROM level_signals
           WHERE user_id=? AND id NOT IN (
               SELECT id FROM level_signals
               WHERE user_id=?
               ORDER BY id DESC LIMIT 30
           )""",
        (user_id, user_id),
    )
    db.commit(); db.close()

def get_recent_level_signals(user_id, limit=6):
    db = conn()
    rows = db.execute(
        """SELECT * FROM level_signals
           WHERE user_id=?
           ORDER BY id DESC LIMIT ?""",
        (user_id, limit),
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]

def auto_adjust_level_from_signals(user_id):
    current = get_user(user_id)
    old_level = (current or {}).get("level", "A1")
    if old_level not in LEVELS:
        old_level = "A1"

    signals = get_recent_level_signals(user_id, limit=6)
    if len(signals) < 4:
        return {
            "old_level": old_level,
            "new_level": old_level,
            "changed": False,
            "reason": "Signal yetarli emas.",
        }

    current_idx = LEVELS.index(old_level)
    indexes = [LEVELS.index(row["suggested_level"]) for row in signals if row["suggested_level"] in LEVELS]
    if len(indexes) < 4:
        return {
            "old_level": old_level,
            "new_level": old_level,
            "changed": False,
            "reason": "Signal yetarli emas.",
        }

    recent4 = indexes[:4]
    recent5 = indexes[:5]
    avg_idx = sum(indexes) / len(indexes)
    up_votes = sum(1 for idx in recent4 if idx >= current_idx + 1)
    down_votes = sum(1 for idx in recent5 if idx <= current_idx - 1)

    new_idx = current_idx
    reason = "Daraja saqlandi."
    if avg_idx >= current_idx + 0.9 and up_votes >= 3:
        new_idx = min(current_idx + 1, len(LEVELS) - 1)
        if new_idx != current_idx:
            reason = "Yozuvlaringizdagi tahlil signallari bir necha marta yuqoriroq darajani ko'rsatdi."
    elif avg_idx <= current_idx - 0.9 and down_votes >= 3:
        new_idx = max(current_idx - 1, 0)
        if new_idx != current_idx:
            reason = "Yozuvlaringizdagi tahlil signallari darajani qayta moslash kerakligini ko'rsatdi."

    new_level = LEVELS[new_idx]
    if new_level != old_level:
        set_level(user_id, new_level)

    return {
        "old_level": old_level,
        "new_level": new_level,
        "changed": new_level != old_level,
        "reason": reason,
    }

def get_recent_quiz_attempts(user_id, qtype="quiz", limit=3, level_before=None):
    db = conn()
    sql = """SELECT * FROM quiz_attempts
             WHERE user_id=? AND qtype=?"""
    params = [user_id, qtype]
    if level_before:
        sql += " AND level_before=?"
        params.append(level_before)
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    rows = db.execute(sql, tuple(params)).fetchall()
    db.close()
    return [dict(r) for r in rows]

def auto_adjust_level_from_quiz(user_id, level_before, correct_answers, total_questions):
    current = get_user(user_id)
    old_level = (current or {}).get("level", level_before or "A1")
    level_before = level_before or old_level
    if level_before not in LEVELS:
        level_before = old_level if old_level in LEVELS else "A1"

    recent = get_recent_quiz_attempts(user_id, qtype="quiz", limit=3, level_before=level_before)
    current_ratio = (correct_answers / total_questions) if total_questions else 0
    prior_good = sum(1 for row in recent if row["total_questions"] and row["correct_answers"] / row["total_questions"] >= 0.85)
    prior_weak = sum(1 for row in recent if row["total_questions"] and row["correct_answers"] / row["total_questions"] <= 0.4)
    prior_questions = sum(int(row.get("total_questions", 0)) for row in recent)

    idx = LEVELS.index(level_before)
    new_idx = idx
    reason = "Daraja saqlandi."

    if current_ratio >= 0.9 and total_questions >= 10 and prior_good >= 1 and (prior_questions + total_questions) >= 20:
        new_idx = min(idx + 1, len(LEVELS) - 1)
        if new_idx != idx:
            reason = "Bir necha quiz davomida yuqori natija ko'rsatdingiz, daraja oshirildi."
    elif current_ratio <= 0.35 and total_questions >= 10 and prior_weak >= 2 and (prior_questions + total_questions) >= 25:
        new_idx = max(idx - 1, 0)
        if new_idx != idx:
            reason = "Bir necha quiz davomida mavzu qiyin bo'ldi, daraja qayta moslandi."

    new_level = LEVELS[new_idx]
    if new_level != old_level:
        set_level(user_id, new_level)

    return {
        "old_level": old_level,
        "new_level": new_level,
        "changed": new_level != old_level,
        "reason": reason,
        "accuracy": round(current_ratio * 100),
    }

def get_global_stats():
    db = conn()
    total_users = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_checks = db.execute("SELECT SUM(checks_total) FROM stats").fetchone()[0] or 0
    total_quiz = db.execute("SELECT SUM(quiz_played) FROM stats").fetchone()[0] or 0
    paid_users = db.execute("""SELECT COUNT(DISTINCT user_id) FROM subscriptions
        WHERE plan_name!='free' AND is_active=1""").fetchone()[0]
    pending_pay = db.execute("SELECT COUNT(*) FROM payments WHERE status='pending'").fetchone()[0]
    db.close()

    free_users = max(total_users - paid_users, 0)
    conversion_rate = round((paid_users / total_users) * 100, 2) if total_users else 0.0
    conversion_rate = min(max(conversion_rate, 0.0), 100.0)
    return {
        "total_users": total_users,
        "total_checks": total_checks,
        "total_quiz": total_quiz,
        "paid_users": paid_users,
        "free_users": free_users,
        "conversion_rate": conversion_rate,
        "pending_payments": pending_pay,
    }


def get_sales_funnel_stats():
    db = conn()

    total_users = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    plan_rows = db.execute(
        "SELECT plan_name, COUNT(DISTINCT user_id) AS cnt FROM subscriptions WHERE is_active=1 GROUP BY plan_name"
    ).fetchall()
    plan_counts = {r["plan_name"]: r["cnt"] for r in plan_rows}

    paid_users = db.execute(
        "SELECT COUNT(DISTINCT user_id) FROM subscriptions WHERE is_active=1 AND plan_name!='free'"
    ).fetchone()[0]
    paid_users = min(paid_users, total_users or 0)
    free_users = max((total_users or 0) - paid_users, 0)

    pending_count = db.execute("SELECT COUNT(*) FROM payments WHERE status='pending'").fetchone()[0]
    pending_amount = db.execute("SELECT COALESCE(SUM(amount), 0) FROM payments WHERE status='pending'").fetchone()[0] or 0

    approved_count = db.execute("SELECT COUNT(*) FROM payments WHERE status='approved'").fetchone()[0]
    approved_amount_30d = db.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM payments WHERE status='approved' AND created_at >= datetime('now', '-30 day')"
    ).fetchone()[0] or 0

    rejected_count = db.execute("SELECT COUNT(*) FROM payments WHERE status='rejected'").fetchone()[0]
    new_users_7d = db.execute("SELECT COUNT(*) FROM users WHERE joined_at >= datetime('now', '-7 day')").fetchone()[0]
    active_users_7d = db.execute("SELECT COUNT(*) FROM users WHERE last_seen >= datetime('now', '-7 day')").fetchone()[0]

    db.close()

    conversion_rate = round((paid_users / total_users) * 100, 2) if total_users else 0.0
    conversion_rate = min(max(conversion_rate, 0.0), 100.0)
    return {
        "total_users": total_users,
        "paid_users": paid_users,
        "free_users": free_users,
        "conversion_rate": conversion_rate,
        "plan_counts": plan_counts,
        "pending_count": pending_count,
        "pending_amount": pending_amount,
        "approved_count": approved_count,
        "approved_amount_30d": approved_amount_30d,
        "rejected_count": rejected_count,
        "new_users_7d": new_users_7d,
        "active_users_7d": active_users_7d,
    }
def _leaderboard_base_sql():
    return """
        WITH web AS (
            SELECT
                user_id,
                COALESCE(SUM(focus_minutes), 0) AS focus_minutes,
                COALESCE(SUM(words_learned), 0) AS words_learned,
                COALESCE(SUM(quiz_completed), 0) AS quiz_completed,
                COALESCE(SUM(lessons_completed), 0) AS lessons_completed,
                COALESCE(SUM(points_earned), 0) AS web_points
            FROM webapp_progress
            GROUP BY user_id
        ),
        base AS (
            SELECT
                u.user_id,
                u.username,
                u.first_name,
                u.level,
                u.last_seen,
                COALESCE(s.checks_total, 0) AS checks_total,
                COALESCE(s.quiz_played, 0) AS quiz_played,
                COALESCE(s.quiz_correct, 0) AS quiz_correct,
                COALESCE(s.streak_days, 0) AS streak_days,
                COALESCE(s.iq_score, 0) AS iq_score,
                COALESCE(rw.points, 0) AS wallet_points,
                COALESCE(web.focus_minutes, 0) AS focus_minutes,
                COALESCE(web.words_learned, 0) AS words_learned,
                COALESCE(web.quiz_completed, 0) AS quiz_completed,
                COALESCE(web.lessons_completed, 0) AS lessons_completed,
                COALESCE(web.web_points, 0) AS web_points,
                (
                    COALESCE(s.checks_total, 0) * 2 +
                    COALESCE(s.quiz_correct, 0) * 12 +
                    COALESCE(s.quiz_played, 0) * 3 +
                    COALESCE(s.streak_days, 0) * 15 +
                    MIN(COALESCE(s.iq_score, 0), 140) * 4 +
                    COALESCE(rw.points, 0) +
                    COALESCE(web.focus_minutes, 0) +
                    COALESCE(web.words_learned, 0) * 3 +
                    COALESCE(web.quiz_completed, 0) * 14 +
                    COALESCE(web.lessons_completed, 0) * 18 +
                    COALESCE(web.web_points, 0) +
                    CASE COALESCE(u.level, 'A1')
                        WHEN 'A1' THEN 50
                        WHEN 'A2' THEN 120
                        WHEN 'B1' THEN 220
                        WHEN 'B2' THEN 360
                        WHEN 'C1' THEN 520
                        WHEN 'C2' THEN 700
                        ELSE 50
                    END
                ) AS learning_score
            FROM users u
            LEFT JOIN stats s ON s.user_id = u.user_id
            LEFT JOIN reward_wallet rw ON rw.user_id = u.user_id
            LEFT JOIN web ON web.user_id = u.user_id
            WHERE COALESCE(u.is_banned, 0) = 0
        ),
        ranked AS (
            SELECT
                *,
                ROW_NUMBER() OVER (ORDER BY learning_score DESC, last_seen DESC, user_id ASC) AS rank,
                COUNT(*) OVER () AS total_users
            FROM base
        )
    """


def get_leaderboard(limit=10):
    limit = max(1, min(int(limit or 10), 100))
    db = conn()
    rows = db.execute(
        _leaderboard_base_sql() + """
        SELECT * FROM ranked
        ORDER BY rank ASC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]


def get_user_rank_snapshot(user_id):
    db = conn()
    row = db.execute(
        _leaderboard_base_sql() + """
        SELECT * FROM ranked WHERE user_id=? LIMIT 1
        """,
        (user_id,),
    ).fetchone()
    db.close()
    return dict(row) if row else None


def get_webapp_totals(user_id, days=30):
    days = max(1, min(int(days or 30), 180))
    db = conn()
    row = db.execute(
        """SELECT
                COALESCE(SUM(focus_minutes), 0) AS focus_minutes,
                COALESCE(SUM(words_learned), 0) AS words_learned,
                COALESCE(SUM(quiz_completed), 0) AS quiz_completed,
                COALESCE(SUM(lessons_completed), 0) AS lessons_completed,
                COALESCE(SUM(points_earned), 0) AS points_earned
            FROM webapp_progress
            WHERE user_id=? AND progress_date >= date('now', ?)
        """,
        (user_id, f'-{days - 1} day'),
    ).fetchone()
    db.close()
    return dict(row) if row else {
        "focus_minutes": 0,
        "words_learned": 0,
        "quiz_completed": 0,
        "lessons_completed": 0,
        "points_earned": 0,
    }


# 
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# HISTORY
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def add_history(user_id, role, content):
    db = conn()
    db.execute("INSERT INTO history (user_id,role,content) VALUES (?,?,?)", (user_id, role, content))
    db.execute("""DELETE FROM history WHERE user_id=? AND id NOT IN (
        SELECT id FROM history WHERE user_id=? ORDER BY id DESC LIMIT 10)""",
        (user_id, user_id))
    db.commit(); db.close()

def get_history(user_id):
    db = conn()
    rows = db.execute("SELECT role,content FROM history WHERE user_id=? ORDER BY id ASC",
        (user_id,)).fetchall()
    db.close()
    return [dict(r) for r in rows]

def clear_history(user_id):
    db = conn()
    db.execute("DELETE FROM history WHERE user_id=?", (user_id,))
    db.commit(); db.close()


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# GROUP SETTINGS
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def get_group(chat_id):
    db = conn()
    db.execute("INSERT OR IGNORE INTO group_settings (chat_id) VALUES (?)", (chat_id,))
    db.commit()
    r = db.execute("SELECT * FROM group_settings WHERE chat_id=?", (chat_id,)).fetchone()
    db.close()
    return dict(r)

def set_group(chat_id, field, value):
    allowed_fields = {
        "check_enabled",
        "bot_enabled",
        "translate_enabled",
        "pronunciation_enabled",
        "daily_enabled",
        "lang",
    }
    if field not in allowed_fields:
        return
    db = conn()
    db.execute(f"UPDATE group_settings SET {field}=? WHERE chat_id=?", (value, chat_id))
    db.commit(); db.close()

def get_daily_groups():
    db = conn()
    rows = db.execute("SELECT * FROM group_settings WHERE daily_enabled=1").fetchall()
    db.close()
    return [dict(r) for r in rows]


def add_sponsor_channel(chat_ref, title, join_url, chat_id_text="", bot_is_admin=0, member_check_ok=0, last_checked_at=""):
    db = conn()
    db.execute(
        """INSERT OR REPLACE INTO sponsor_channels
           (chat_ref, chat_id_text, title, join_url, bot_is_admin, member_check_ok, last_checked_at, is_active)
           VALUES (?, ?, ?, ?, ?, ?, ?, 1)""",
        (
            str(chat_ref or "").strip(),
            str(chat_id_text or "").strip(),
            str(title or "").strip(),
            str(join_url or "").strip(),
            int(bool(bot_is_admin)),
            int(bool(member_check_ok)),
            str(last_checked_at or "").strip(),
        ),
    )
    db.commit(); db.close()

def remove_sponsor_channel(channel_id):
    db = conn()
    db.execute("DELETE FROM sponsor_channels WHERE id=?", (channel_id,))
    db.commit(); db.close()

def get_sponsor_channels(active_only=False):
    db = conn()
    sql = "SELECT * FROM sponsor_channels"
    if active_only:
        sql += " WHERE is_active=1"
    sql += " ORDER BY id DESC"
    rows = db.execute(sql).fetchall()
    db.close()
    return [dict(r) for r in rows]


def get_group_game(chat_id):
    db = conn()
    row = db.execute("SELECT * FROM active_group_games WHERE chat_id=?", (chat_id,)).fetchone()
    db.close()
    return dict(row) if row else None


def get_active_group_games(game_type=None, status=None):
    db = conn()
    sql = "SELECT * FROM active_group_games WHERE 1=1"
    params = []
    if game_type:
        sql += " AND game_type=?"
        params.append(str(game_type))
    if status:
        if isinstance(status, (list, tuple, set)):
            marks = ",".join("?" for _ in status)
            sql += f" AND status IN ({marks})"
            params.extend(str(item) for item in status)
        else:
            sql += " AND status=?"
            params.append(str(status))
    sql += " ORDER BY updated_at DESC"
    rows = db.execute(sql, tuple(params)).fetchall()
    db.close()
    return [dict(r) for r in rows]


def save_group_game(chat_id, game_type, status="running", payload=None):
    payload_text = json.dumps(payload or {}, ensure_ascii=False)
    db = conn()
    db.execute(
        """INSERT OR REPLACE INTO active_group_games (chat_id, game_type, status, payload, updated_at)
           VALUES (?, ?, ?, ?, datetime('now'))""",
        (chat_id, game_type, status, payload_text),
    )
    db.commit(); db.close()


def clear_group_game(chat_id):
    db = conn()
    db.execute("DELETE FROM active_group_games WHERE chat_id=?", (chat_id,))
    db.commit(); db.close()


def get_group_game_scores(chat_id, limit=10):
    db = conn()
    rows = db.execute(
        """SELECT * FROM group_game_scores
           WHERE chat_id=?
           ORDER BY points DESC, wins DESC, updated_at ASC
           LIMIT ?""",
        (chat_id, int(limit)),
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]


def add_group_game_points(chat_id, user_id, username, points, won=0):
    db = conn()
    db.execute(
        """INSERT OR IGNORE INTO group_game_scores (chat_id, user_id, username, points, wins, played)
           VALUES (?, ?, ?, 0, 0, 0)""",
        (chat_id, user_id, str(username or "")),
    )
    db.execute(
        """UPDATE group_game_scores
           SET username=?,
               points=points + ?,
               wins=wins + ?,
               played=played + 1,
               updated_at=datetime('now')
           WHERE chat_id=? AND user_id=?""",
        (str(username or ""), float(points or 0), int(won or 0), chat_id, user_id),
    )
    db.commit(); db.close()


def reset_group_game_scores(chat_id):
    db = conn()
    db.execute("DELETE FROM group_game_scores WHERE chat_id=?", (chat_id,))
    db.commit(); db.close()


def get_group_game_settings(chat_id):
    db = conn()
    db.execute("INSERT OR IGNORE INTO group_game_settings (chat_id) VALUES (?)", (chat_id,))
    db.commit()
    row = db.execute("SELECT * FROM group_game_settings WHERE chat_id=?", (chat_id,)).fetchone()
    db.close()
    return dict(row) if row else {
        "chat_id": chat_id,
        "word_time_limit": 30,
        "word_points": 10,
        "error_time_limit": 45,
        "error_points": 15,
        "translation_time_limit": 60,
        "translation_points_perfect": 20,
        "translation_points_partial": 5,
        "mafia_min_players": 6,
        "mafia_max_players": 12,
        "mafia_night_time": 60,
        "mafia_day_time": 120,
    }


def update_group_game_setting(chat_id, field, value):
    allowed_fields = {
        "word_time_limit",
        "word_points",
        "error_time_limit",
        "error_points",
        "translation_time_limit",
        "translation_points_perfect",
        "translation_points_partial",
        "mafia_min_players",
        "mafia_max_players",
        "mafia_night_time",
        "mafia_day_time",
    }
    if field not in allowed_fields:
        return
    db = conn()
    db.execute("INSERT OR IGNORE INTO group_game_settings (chat_id) VALUES (?)", (chat_id,))
    db.execute(f"UPDATE group_game_settings SET {field}=? WHERE chat_id=?", (value, chat_id))
    db.commit(); db.close()





def add_webapp_progress(user_id, focus_minutes=0, words_learned=0, quiz_completed=0, lessons_completed=0, points_earned=0):
    today = date.today().isoformat()
    db = conn()
    db.execute(
        """INSERT OR IGNORE INTO webapp_progress
           (user_id, progress_date, focus_minutes, words_learned, quiz_completed, lessons_completed, points_earned)
           VALUES (?, ?, 0, 0, 0, 0, 0)""",
        (user_id, today),
    )
    db.execute(
        """UPDATE webapp_progress
           SET focus_minutes = focus_minutes + ?,
               words_learned = words_learned + ?,
               quiz_completed = quiz_completed + ?,
               lessons_completed = lessons_completed + ?,
               points_earned = points_earned + ?,
               updated_at = datetime('now')
           WHERE user_id=? AND progress_date=?""",
        (
            max(0, int(focus_minutes or 0)),
            max(0, int(words_learned or 0)),
            max(0, int(quiz_completed or 0)),
            max(0, int(lessons_completed or 0)),
            max(0, int(points_earned or 0)),
            user_id,
            today,
        ),
    )
    db.commit(); db.close()



def set_webapp_progress_snapshot(user_id, words_learned=0, quiz_completed=0, lessons_completed=0, points_earned=0):
    today = date.today().isoformat()
    db = conn()
    db.execute(
        """INSERT OR IGNORE INTO webapp_progress
           (user_id, progress_date, focus_minutes, words_learned, quiz_completed, lessons_completed, points_earned)
           VALUES (?, ?, 0, 0, 0, 0, 0)""",
        (user_id, today),
    )
    db.execute(
        """UPDATE webapp_progress
           SET words_learned = ?,
               quiz_completed = ?,
               lessons_completed = ?,
               points_earned = ?,
               updated_at = datetime('now')
           WHERE user_id=? AND progress_date=?""",
        (
            max(0, int(words_learned or 0)),
            max(0, int(quiz_completed or 0)),
            max(0, int(lessons_completed or 0)),
            max(0, int(points_earned or 0)),
            user_id,
            today,
        ),
    )
    db.commit(); db.close()
def get_webapp_progress(user_id, days=14):
    days = max(1, min(int(days or 14), 90))
    db = conn()
    rows = db.execute(
        """SELECT * FROM webapp_progress
           WHERE user_id=?
           ORDER BY progress_date DESC
           LIMIT ?""",
        (user_id, days),
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]







def _ensure_service_hits_table(db):
    db.execute(
        """CREATE TABLE IF NOT EXISTS service_hits (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            path        TEXT DEFAULT '/',
            ip          TEXT DEFAULT '',
            user_agent  TEXT DEFAULT '',
            created_at  TEXT DEFAULT (datetime('now'))
        )"""
    )
    db.execute("CREATE INDEX IF NOT EXISTS idx_service_hits_created ON service_hits(created_at)")


def record_service_hit(path='/', ip='', user_agent=''):
    db = conn()
    _ensure_service_hits_table(db)
    db.execute(
        "INSERT INTO service_hits (path, ip, user_agent) VALUES (?, ?, ?)",
        ((path or '/')[:120], (ip or '')[:80], (user_agent or '')[:240]),
    )
    db.commit(); db.close()


def get_service_hit_summary(limit=12):
    limit = max(1, min(int(limit or 12), 100))
    db = conn()
    _ensure_service_hits_table(db)

    total_row = db.execute("SELECT COUNT(*) AS c FROM service_hits").fetchone()
    last_row = db.execute("SELECT created_at FROM service_hits ORDER BY id DESC LIMIT 1").fetchone()
    h1_row = db.execute(
        "SELECT COUNT(*) AS c FROM service_hits WHERE created_at >= datetime('now', '-1 hour')"
    ).fetchone()
    h24_row = db.execute(
        "SELECT COUNT(*) AS c FROM service_hits WHERE created_at >= datetime('now', '-24 hour')"
    ).fetchone()
    recent_rows = db.execute(
        "SELECT path, ip, user_agent, created_at FROM service_hits ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    db.close()

    return {
        "total": int((total_row["c"] if total_row else 0) or 0),
        "last_at": (last_row["created_at"] if last_row else None),
        "last_1h": int((h1_row["c"] if h1_row else 0) or 0),
        "last_24h": int((h24_row["c"] if h24_row else 0) or 0),
        "recent": [dict(r) for r in recent_rows],
    }





