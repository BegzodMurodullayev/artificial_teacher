# 🔗 Integration Points — Artificial Teacher v2.0

> How the Bot, WebApp, API, and Database connect to each other.

---

## 1. Bot → WebApp (Opening the WebApp)

The bot sends inline keyboard buttons with `WebAppInfo` to launch the WebApp inside Telegram.

```python
# In src/bot/keyboards/user_menu.py
KeyboardButton(
    text="📱 Ilovani ochish",
    web_app=WebAppInfo(url=settings.WEB_APP_URL)  # Netlify URL
)

# Game-specific launch
InlineKeyboardButton(
    text="🕹️ X-O o'ynash",
    web_app=WebAppInfo(url=f"{settings.WEB_APP_URL}/games/xo")
)
```

**Flow**:
1. User taps the button in Telegram
2. Telegram opens the WebApp URL in an in-app browser
3. The WebApp receives `window.Telegram.WebApp.initData` from Telegram
4. WebApp calls `tg.ready()` to signal it's loaded
5. WebApp uses `initData` to authenticate with the FastAPI backend

---

## 2. WebApp → Bot (Sending Data Back)

The WebApp can send data back to the bot using the Telegram SDK.

```typescript
// In webapp/src/pages/XOGamePage.tsx (example)
window.Telegram.WebApp.sendData(JSON.stringify({
    type: 'game_result',
    game: 'xo',
    score: 100,
    won: true
}))
```

**Flow**:
1. User completes a game or action in WebApp
2. `sendData()` sends a string to the bot
3. Bot receives it as a `WebAppData` update
4. Handler processes the data (awards XP, saves score)

> ⚠️ **Note**: `sendData()` only works when WebApp was opened via a keyboard button with `web_app`. It closes the WebApp and sends data to the bot. For background API calls, use the REST API instead.

---

## 3. WebApp ↔ FastAPI (REST API)

The WebApp communicates with the backend through authenticated REST API calls.

### Authentication Flow

```
WebApp                    FastAPI                     Telegram
  │                          │                            │
  │  GET /api/user/dashboard │                            │
  │  X-Telegram-Init-Data:   │                            │
  │    hash=...&user=...     │                            │
  │─────────────────────────▶│                            │
  │                          │  validate_init_data()      │
  │                          │  HMAC-SHA256 with BOT_TOKEN│
  │                          │────────────────────────────│
  │                          │  ✅ Valid                   │
  │                          │◀───────────────────────────│
  │                          │  extract user.id           │
  │                          │  request.state.tg_user = { │
  │                          │    id: 123456789,          │
  │                          │    first_name: "Ali"       │
  │                          │  }                         │
  │◀─────────────────────────│                            │
  │  200 DashboardData        │                            │
```

### HMAC-SHA256 Validation (telegram_auth.py)

```python
# 1. Build data-check-string from sorted params (excluding hash)
data_check_string = "\n".join(sorted(
    f"{k}={v}" for k, v in params.items() if k != "hash"
))

# 2. Create secret key
secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), sha256).digest()

# 3. Compute expected hash
computed = hmac.new(secret_key, data_check_string.encode(), sha256).hexdigest()

# 4. Compare (constant-time)
if hmac.compare_digest(computed, received_hash):
    return parse_user(params["user"])
```

### Request Header Injection (api.ts)

```typescript
api.interceptors.request.use((config) => {
    const initData = window.Telegram?.WebApp?.initData
    if (initData) {
        config.headers['X-Telegram-Init-Data'] = initData
    }
    return config
})
```

---

## 4. Database Flow

### Connection Management

```python
# src/database/connection.py
# Single async SQLite connection (singleton pattern)

_db: aiosqlite.Connection | None = None

async def get_db() -> aiosqlite.Connection:
    if _db is None:
        _db = await aiosqlite.connect(DB_PATH, timeout=20)
        await _db.execute("PRAGMA journal_mode=WAL")      # Write-Ahead Log
        await _db.execute("PRAGMA synchronous=NORMAL")    # Balance safety/speed
        await _db.execute("PRAGMA busy_timeout=7000")     # 7s timeout on busy
        await _db.execute("PRAGMA foreign_keys=ON")       # Enforce FK constraints
        await _db.execute("PRAGMA cache_size=-20000")     # 20MB cache
    return _db
```

### WAL Mode Explanation
- **WAL (Write-Ahead Logging)**: Allows concurrent reads while writing
- Critical since Bot (writes) and FastAPI (reads) share the same DB connection
- `busy_timeout=7000ms` prevents "database is locked" errors under load

### Init Flow

```python
# On startup:
1. get_db()          → Connect + set pragmas
2. executescript(init_schema.sql)  → CREATE TABLE IF NOT EXISTS (idempotent)
3. _run_migrations() → ALTER TABLE for backward compat
4. _seed_default_plans() → INSERT plans if table empty
5. db.commit()
```

---

## 5. Payment Flow (Manual)

```
User                    Bot                    Admin                  DB
 │                       │                       │                     │
 │  /subscribe           │                       │                     │
 │──────────────────────▶│                       │                     │
 │  Show plan keyboard   │                       │                     │
 │◀──────────────────────│                       │                     │
 │  Select plan (e.g. Standard)                  │                     │
 │──────────────────────▶│                       │                     │
 │  Show payment instructions + card number      │                     │
 │◀──────────────────────│                       │                     │
 │  Send receipt photo   │                       │                     │
 │──────────────────────▶│                       │                     │
 │                       │  create_payment()     │                     │
 │                       │────────────────────────────────────────────▶│
 │                       │  notify admins        │                     │
 │                       │──────────────────────▶│                     │
 │  "Payment sent! Waiting for approval"         │                     │
 │◀──────────────────────│                       │                     │
 │                       │                       │  Press ✅ Approve    │
 │                       │                       │──────────────────── │
 │                       │                       │  approve_payment()  │
 │                       │                       │─────────────────────▶│
 │                       │                       │  activate_subscription()
 │                       │                       │─────────────────────▶│
 │  "✅ Payment approved!" notification           │                     │
 │◀──────────────────────│                       │                     │
```

**Key functions**:
- `payment_dao.create_payment()` → Status: `pending`
- `payment_dao.approve_payment()` → Status: `approved`
- `subscription_dao.activate_subscription()` → Creates new subscription row
- Bot notifies user via `bot.send_message(user_id, "...")`

---

## 6. Quiz Flow

```
User          Bot (quiz_start.py)       ai_service     quiz_dao       xp_dao
 │                    │                     │               │              │
 │  /quiz              │                     │               │              │
 │────────────────────▶│                     │               │              │
 │                    │  create_quiz_session()               │              │
 │                    │──────────────────────────────────────▶│              │
 │                    │  ask_json("quiz_generate", level=A1)  │              │
 │                    │────────────────────▶│               │              │
 │                    │  Question JSON      │               │              │
 │                    │◀────────────────────│               │              │
 │                    │  update_quiz_session(current_question)              │
 │                    │──────────────────────────────────────▶│              │
 │  Question + 4 options, 45s timer         │               │              │
 │◀───────────────────│                     │               │              │
 │  Press answer (A/B/C/D)                  │               │              │
 │────────────────────▶│                     │               │              │
 │                    │  check correct, update session       │              │
 │                    │──────────────────────────────────────▶│              │
 │                    │  add_xp(10, "quiz_correct")          │              │
 │                    │─────────────────────────────────────────────────────▶│
 │  Result + next question                  │               │              │
 │◀───────────────────│                     │               │              │
 │  ... (10 questions total) ...            │               │              │
 │                    │  finish_quiz_session()               │              │
 │                    │──────────────────────────────────────▶│              │
 │                    │  auto_adjust_from_quiz(level=A1)     │              │
 │  Final results (score, XP, level change) │               │              │
 │◀───────────────────│                     │               │              │
```

---

## 7. Game Flow (Chat Games vs WebApp Games)

### Chat Games (Group)
- Triggered by `/soztopish`, `/tezhisob`, etc. in group chat
- Game state stored in `game_sessions` table (`payload` JSON)
- Multiple players compete in the same group chat
- Points tracked in `group_game_scores`

### WebApp Games (Solo)
- Opened via inline button with `WebAppInfo` URL
- Pure client-side logic (no server state during game)
- On completion: `Telegram.WebApp.sendData()` OR REST API call
- XP awarded via `POST /api/games/result`

---

## 8. Middleware Injection Chain

Every bot handler receives `db_user` dict via middleware:

```python
# AuthMiddleware injects:
data["db_user"] = {
    "user_id": 123456789,
    "username": "ali_123",
    "first_name": "Ali",
    "role": "user",        # user | admin | owner
    "level": "B1",
    "is_banned": 0
}

# Used in handlers:
async def handler(message: Message, db_user: dict | None = None):
    user_id = db_user["user_id"]
    level = db_user.get("level", "A1")
```

---

*Last Updated: 2026-04-21*
