import json
import os
import sqlite3
from datetime import date, timedelta
from typing import Dict, List, Optional, Sequence


DB_PATH = os.getenv("DB_PATH", "teacher_bot.db")

FEATURE_COLUMNS = {
    "check": "check_enabled",
    "bot": "bot_enabled",
    "translate": "translate_enabled",
    "quiz": "quiz_enabled",
    "lesson": "lesson_enabled",
    "tracker": "tracker_enabled",
}


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                level TEXT DEFAULT 'A1',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS stats (
                user_id INTEGER PRIMARY KEY,
                checks INTEGER DEFAULT 0,
                questions INTEGER DEFAULT 0,
                translations INTEGER DEFAULT 0,
                quizzes INTEGER DEFAULT 0,
                quiz_correct INTEGER DEFAULT 0,
                quiz_total INTEGER DEFAULT 0,
                focus_minutes INTEGER DEFAULT 0,
                tasks_created INTEGER DEFAULT 0,
                tasks_done INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                mode TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_messages_user_created
            ON messages(user_id, created_at DESC);

            CREATE TABLE IF NOT EXISTS chat_settings (
                chat_id INTEGER PRIMARY KEY,
                check_enabled INTEGER DEFAULT 1,
                bot_enabled INTEGER DEFAULT 1,
                translate_enabled INTEGER DEFAULT 1,
                quiz_enabled INTEGER DEFAULT 1,
                lesson_enabled INTEGER DEFAULT 1,
                tracker_enabled INTEGER DEFAULT 1,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS daily_subscriptions (
                chat_id INTEGER PRIMARY KEY,
                is_active INTEGER DEFAULT 1,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS focus_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                minutes INTEGER NOT NULL,
                source TEXT DEFAULT 'bot',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_focus_user_created
            ON focus_sessions(user_id, created_at DESC);

            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                web_id TEXT,
                title TEXT NOT NULL,
                status TEXT DEFAULT 'todo',
                source TEXT DEFAULT 'bot',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT,
                UNIQUE(user_id, web_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_tasks_user_status
            ON tasks(user_id, status, created_at DESC);

            CREATE TABLE IF NOT EXISTS webapp_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )


def ensure_user(user_id: int, username: Optional[str], first_name: Optional[str]) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO users(id, username, first_name, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                username=excluded.username,
                first_name=excluded.first_name,
                updated_at=CURRENT_TIMESTAMP
            """,
            (user_id, username or "", first_name or ""),
        )
        conn.execute(
            """
            INSERT INTO stats(user_id) VALUES (?)
            ON CONFLICT(user_id) DO NOTHING
            """,
            (user_id,),
        )


def log_message(user_id: int, role: str, mode: str, content: str) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO messages(user_id, role, mode, content)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, role, mode, content),
        )


def get_recent_context(user_id: int, limit: int = 6) -> List[Dict[str, str]]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT role, content
            FROM messages
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, max(1, limit)),
        ).fetchall()
    ordered = list(reversed(rows))
    return [{"role": row["role"], "content": row["content"]} for row in ordered]


def increment_stat(user_id: int, key: str, amount: int = 1) -> None:
    if key not in {
        "checks",
        "questions",
        "translations",
        "quizzes",
        "quiz_correct",
        "quiz_total",
        "focus_minutes",
        "tasks_created",
        "tasks_done",
    }:
        return
    with _connect() as conn:
        conn.execute(f"UPDATE stats SET {key} = {key} + ? WHERE user_id = ?", (amount, user_id))


def save_quiz_result(user_id: int, correct: int, total: int) -> None:
    with _connect() as conn:
        conn.execute(
            """
            UPDATE stats
            SET quizzes = quizzes + 1,
                quiz_correct = quiz_correct + ?,
                quiz_total = quiz_total + ?
            WHERE user_id = ?
            """,
            (correct, total, user_id),
        )


def get_user_level(user_id: int) -> str:
    with _connect() as conn:
        row = conn.execute("SELECT level FROM users WHERE id = ?", (user_id,)).fetchone()
    if not row:
        return "A1"
    return row["level"] or "A1"


def set_user_level(user_id: int, level: str) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE users SET level = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (level, user_id),
        )


def get_user_stats(user_id: int) -> Dict[str, int]:
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT
                s.checks,
                s.questions,
                s.translations,
                s.quizzes,
                s.quiz_correct,
                s.quiz_total,
                s.focus_minutes,
                s.tasks_created,
                s.tasks_done,
                u.level
            FROM stats s
            JOIN users u ON u.id = s.user_id
            WHERE s.user_id = ?
            """,
            (user_id,),
        ).fetchone()
    if not row:
        return {
            "checks": 0,
            "questions": 0,
            "translations": 0,
            "quizzes": 0,
            "quiz_correct": 0,
            "quiz_total": 0,
            "focus_minutes": 0,
            "tasks_created": 0,
            "tasks_done": 0,
            "level": "A1",
        }
    return dict(row)


def set_chat_feature(chat_id: int, feature: str, enabled: bool) -> None:
    column = FEATURE_COLUMNS.get(feature)
    if not column:
        return
    with _connect() as conn:
        conn.execute(
            "INSERT INTO chat_settings(chat_id) VALUES (?) ON CONFLICT(chat_id) DO NOTHING",
            (chat_id,),
        )
        conn.execute(
            f"""
            UPDATE chat_settings
            SET {column} = ?, updated_at = CURRENT_TIMESTAMP
            WHERE chat_id = ?
            """,
            (1 if enabled else 0, chat_id),
        )


def is_feature_enabled(chat_id: int, feature: str) -> bool:
    column = FEATURE_COLUMNS.get(feature)
    if not column:
        return True
    with _connect() as conn:
        row = conn.execute(f"SELECT {column} FROM chat_settings WHERE chat_id = ?", (chat_id,)).fetchone()
    if not row:
        return True
    return bool(row[column])


def list_feature_states(chat_id: int) -> Dict[str, bool]:
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT check_enabled, bot_enabled, translate_enabled, quiz_enabled, lesson_enabled, tracker_enabled
            FROM chat_settings
            WHERE chat_id = ?
            """,
            (chat_id,),
        ).fetchone()
    if not row:
        return {key: True for key in FEATURE_COLUMNS}
    return {
        "check": bool(row["check_enabled"]),
        "bot": bool(row["bot_enabled"]),
        "translate": bool(row["translate_enabled"]),
        "quiz": bool(row["quiz_enabled"]),
        "lesson": bool(row["lesson_enabled"]),
        "tracker": bool(row["tracker_enabled"]),
    }


def enable_daily_subscription(chat_id: int, enabled: bool) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO daily_subscriptions(chat_id, is_active, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(chat_id) DO UPDATE SET
                is_active=excluded.is_active,
                updated_at=CURRENT_TIMESTAMP
            """,
            (chat_id, 1 if enabled else 0),
        )


def list_daily_subscriptions() -> List[int]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT chat_id FROM daily_subscriptions WHERE is_active = 1"
        ).fetchall()
    return [int(row["chat_id"]) for row in rows]


def add_focus_session(user_id: int, minutes: int, source: str = "bot") -> None:
    minutes = max(1, int(minutes))
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO focus_sessions(user_id, minutes, source)
            VALUES (?, ?, ?)
            """,
            (user_id, minutes, source),
        )
        conn.execute(
            "UPDATE stats SET focus_minutes = focus_minutes + ? WHERE user_id = ?",
            (minutes, user_id),
        )


def get_focus_summary(user_id: int, days: int = 7) -> List[Dict[str, int]]:
    days = max(1, days)
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT date(created_at) AS day, SUM(minutes) AS total_minutes
            FROM focus_sessions
            WHERE user_id = ? AND datetime(created_at) >= datetime('now', ?)
            GROUP BY day
            ORDER BY day ASC
            """,
            (user_id, f"-{days} day"),
        ).fetchall()
    values = {row["day"]: int(row["total_minutes"] or 0) for row in rows}
    output: List[Dict[str, int]] = []
    for i in range(days - 1, -1, -1):
        day = (date.today() - timedelta(days=i)).isoformat()
        output.append({"day": day, "minutes": values.get(day, 0)})
    return output


def add_task(user_id: int, title: str, source: str = "bot", web_id: Optional[str] = None) -> int:
    with _connect() as conn:
        normalized = title.strip()
        if web_id:
            existing = conn.execute(
                "SELECT id FROM tasks WHERE user_id = ? AND web_id = ?",
                (user_id, web_id),
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE tasks SET title = ? WHERE id = ?",
                    (normalized, existing["id"]),
                )
                return int(existing["id"])

        cursor = conn.execute(
            """
            INSERT INTO tasks(user_id, web_id, title, source)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, web_id, normalized, source),
        )
        conn.execute(
            "UPDATE stats SET tasks_created = tasks_created + 1 WHERE user_id = ?",
            (user_id,),
        )
        return int(cursor.lastrowid)


def complete_task(user_id: int, task_id: int) -> bool:
    with _connect() as conn:
        row = conn.execute(
            "SELECT status FROM tasks WHERE id = ? AND user_id = ?",
            (task_id, user_id),
        ).fetchone()
        if not row:
            return False
        if row["status"] == "done":
            return True
        conn.execute(
            """
            UPDATE tasks
            SET status = 'done', completed_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
            """,
            (task_id, user_id),
        )
        conn.execute(
            "UPDATE stats SET tasks_done = tasks_done + 1 WHERE user_id = ?",
            (user_id,),
        )
    return True


def set_task_state_by_web_id(user_id: int, web_id: str, title: str, done: bool) -> None:
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT id, status
            FROM tasks
            WHERE user_id = ? AND web_id = ?
            """,
            (user_id, web_id),
        ).fetchone()
        if row:
            previous = row["status"]
            new_status = "done" if done else "todo"
            conn.execute(
                """
                UPDATE tasks
                SET title = ?, status = ?, completed_at = CASE WHEN ? = 1 THEN CURRENT_TIMESTAMP ELSE NULL END
                WHERE id = ?
                """,
                (title, new_status, 1 if done else 0, row["id"]),
            )
            if previous != "done" and done:
                conn.execute(
                    "UPDATE stats SET tasks_done = tasks_done + 1 WHERE user_id = ?",
                    (user_id,),
                )
        else:
            conn.execute(
                """
                INSERT INTO tasks(user_id, web_id, title, status, source, completed_at)
                VALUES (?, ?, ?, ?, 'webapp', CASE WHEN ? = 1 THEN CURRENT_TIMESTAMP ELSE NULL END)
                """,
                (user_id, web_id, title, "done" if done else "todo", 1 if done else 0),
            )
            conn.execute(
                "UPDATE stats SET tasks_created = tasks_created + 1 WHERE user_id = ?",
                (user_id,),
            )
            if done:
                conn.execute(
                    "UPDATE stats SET tasks_done = tasks_done + 1 WHERE user_id = ?",
                    (user_id,),
                )


def list_tasks(user_id: int, only_open: bool = False, limit: int = 20) -> List[Dict[str, object]]:
    query = """
        SELECT id, web_id, title, status, source, created_at, completed_at
        FROM tasks
        WHERE user_id = ?
    """
    params: Sequence[object] = [user_id]
    if only_open:
        query += " AND status != 'done'"
    query += " ORDER BY CASE WHEN status = 'done' THEN 1 ELSE 0 END, id DESC LIMIT ?"
    params = [user_id, limit]
    with _connect() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def save_webapp_snapshot(user_id: int, payload: Dict[str, object]) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO webapp_snapshots(user_id, payload_json)
            VALUES (?, ?)
            """,
            (user_id, json.dumps(payload, ensure_ascii=False)),
        )


def get_latest_snapshot(user_id: int) -> Optional[Dict[str, object]]:
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT payload_json
            FROM webapp_snapshots
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()
    if not row:
        return None
    try:
        return json.loads(row["payload_json"])
    except json.JSONDecodeError:
        return None
