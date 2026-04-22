# 🧠 AI Knowledge Base — Artificial Teacher v2.0

> Concise reference guide for an AI assistant to understand the project and work autonomously.

---

## Project Identity

- **Name**: Artificial Teacher (Telegram bot)
- **Bot**: `@Artificial_teacher_bot`
- **Purpose**: English learning for Uzbek speakers via Telegram + WebApp
- **Language of UI**: Uzbek (O'zbek tili)
- **Monetization**: Freemium, 4 tiers: Free, Standard (29K), Pro (59K), Premium (99K) UZS/month
- **Repo root**: `d:\my work\artificial_teacher\`

---

## Critical Patterns

### 1. Always use `safe_reply` NOT `message.answer()`
```python
# ✅ Correct
from src.bot.utils.telegram import safe_reply
await safe_reply(message, "<b>Text</b>", reply_markup=keyboard)

# ❌ Wrong (no error handling)
await message.answer("Text")
```

### 2. Always use `escape_html()` for user-provided text
```python
from src.bot.utils.telegram import escape_html
user_text = escape_html(message.text)
```

### 3. Always get DB via `get_db()`
```python
from src.database.connection import get_db
db = await get_db()
async with db.execute("SELECT ...", (params,)) as cur:
    row = await cur.fetchone()
```

### 4. All DAOs are module-level async functions
```python
from src.database.dao import user_dao, stats_dao
user = await user_dao.get_user(user_id)
await stats_dao.inc_stat(user_id, "checks_total")
```

### 5. Handler functions receive `db_user` from middleware
```python
async def my_handler(message: Message, db_user: dict | None = None):
    if not db_user:
        return  # Always check first
    user_id = db_user["user_id"]
    level = db_user.get("level", "A1")
```

### 6. Register new routers in `src/bot/handlers/__init__.py`
```python
def register_all_handlers(dp: Dispatcher) -> None:
    # ...existing...
    from src.bot.handlers.user import my_new_module
    dp.include_router(my_new_module.router)
```

### 7. Keyboard layout — USER_MENU_ALIASES is the truth
Any text a user can type from the keyboard is mapped in `USER_MENU_ALIASES` in `user_menu.py`. If you add a new button, add its alias here or `smart_message_handler` will catch it.

### 8. `settings` import pattern
```python
from src.config import settings
# Access: settings.BOT_TOKEN, settings.WEB_APP_URL, etc.
```

---

## AI Service Usage

### Ask for formatted text response
```python
from src.services.ai_service import ask_ai
response = await ask_ai(
    text=user_message,
    mode="check",          # mode key from SYSTEM_PROMPTS dict
    user_id=user_id,
    level="B1",
    history=[...]           # Last N messages for context
)
```

### Ask for structured JSON response
```python
from src.services.ai_service import ask_json
result = await ask_json(
    text=user_message,
    mode="pronunciation",
    level="A1"
)
# result is a dict or None
word = result.get("word", "")
ipa_us = result.get("ipa_us", "")
```

### Available AI modes (system prompts)
| Mode | Output | Purpose |
|------|--------|---------|
| `check` | JSON: `{analysis, corrected, summary, level}` | Grammar check |
| `translate_uz_en` | JSON: `{original, translation, notes}` | UZ→EN translation |
| `translate_en_uz` | JSON: `{original, translation, notes}` | EN→UZ translation |
| `pronunciation` | JSON: `{word, ipa_us, ipa_uk, syllables, tips, examples}` | Pronunciation guide |
| `lesson` | Text (formatted) | Lesson content |
| `grammar_rule` | Text (formatted) | Grammar explanation |
| `quiz_generate` | JSON: `{question, options, correct, explanation}` | Quiz question |
| `iq_question` | JSON: `{question, options, correct, explanation}` | IQ question |
| `daily_word` | JSON: `{word, translation, example}` | Daily word |
| `bot` | Text | AI chat response |
| `teacher` | Text | Teacher Q&A |
| `intent` | JSON: `{intent}` | Intent classification |

---

## Adding New Features

### Adding a new bot command
1. Create handler file in `src/bot/handlers/user/` or `src/bot/handlers/`
2. Define `router = Router(name="...")` and handler function
3. Export `router` or `get_X_router()` from `__init__.py`
4. Register in `src/bot/handlers/__init__.py`

### Adding a new API endpoint
1. Create or edit route file in `src/api/routes/`
2. Use `APIRouter(prefix="/api/...", tags=["..."])`
3. Extract user via `_get_tg_user(request)` or `_get_uid(request)` helpers
4. Register router in `src/main.py`:
   ```python
   from src.api.routes import my_route
   app.include_router(my_route.router)
   ```

### Adding a new database table
1. Add `CREATE TABLE IF NOT EXISTS` to `src/database/migrations/init_schema.sql`
2. Create DAO file in `src/database/dao/`
3. Create dataclass model in `src/database/models.py`
4. If altering existing table, add migration in `connection.py` `_run_migrations()`

### Adding a new WebApp page
1. Create `webapp/src/pages/NewPage.tsx`
2. Add lazy import to `webapp/src/App.tsx`
3. Add `<Route path="/new-page" element={<NewPage />} />` in App.tsx
4. Add navigation to `MainLayout.tsx` bottom nav or relevant menu

---

## Subscription Plan Limits

| Feature | Free | Standard | Pro | Premium |
|---------|------|----------|-----|---------|
| Checks/day | 12 | 30 | 60 | Unlimited |
| Quiz/day | 3 | 10 | 25 | Unlimited |
| Lessons/day | 3 | 10 | 25 | Unlimited |
| AI messages/day | 20 | 50 | 100 | Unlimited |
| Pronunciation audio/day | 5 | 20 | 50 | Unlimited |
| Voice messages | ❌ | ✅ | ✅ | ✅ |
| Inline mode | ❌ | ✅ | ✅ | ✅ |
| IQ test | ❌ | ❌ | ✅ | ✅ |

---

## User Roles

| Role | How Assigned | Permissions |
|------|-------------|-------------|
| `user` | Default | Standard bot usage |
| `admin` | By owner via DB | Admin panel, broadcast |
| `owner` | Auto-promoted via `OWNER_ID` | All admin + manage admins |

---

## Key Algorithms

### XP Level Formula
```python
# From xp_dao.py
XP_PER_LEVEL = 100
current_level = total_xp // XP_PER_LEVEL  # Level 1 starts at 100 XP
xp_to_next = XP_PER_LEVEL - (total_xp % XP_PER_LEVEL)
```

### Auto-Level Detection
```python
# From level_service.py
# Signals: source (check/quiz/lesson), estimated_level (A1-C2), weight
# Algorithm: weighted average of last 6 signals
# Level up if: avg >= current + 0.9 AND count >= 3
# Level dn if: avg <= current - 0.9 AND count >= 3
```

### Intent Routing Order
```python
# From message_handler.py
if len(text) > 100 or "def " in text:  → TECHNICAL
elif bot_keywords and short:            → SUPPORT
elif is_latin and not is_cyrillic:     → CORRECTION
else:                                   → UNCLEAR (shows menu)
```

---

## Common Pitfalls

### ❌ Don't import `bot` at module level in handlers
```python
# Wrong — causes circular import
from src.bot.loader import bot

# Right — import inside function
async def handler():
    from src.bot.loader import bot
    await bot.send_message(...)
```

### ❌ Don't use `await db.commit()` after SELECT
Only commit after INSERT/UPDATE/DELETE.

### ❌ Don't forget menu alias when adding new keyboard buttons
New buttons in any sub-menu MUST be added to `USER_MENU_ALIASES` in `user_menu.py`, otherwise `smart_message_handler` treats them as user text input.

### ❌ Don't use f-strings directly in HTML messages
```python
# Wrong — XSS-like issues
await message.answer(f"Hello {user.first_name}!")

# Right — always escape
name = escape_html(user.first_name)
await safe_reply(message, f"Hello <b>{name}</b>!")
```

### ❌ Don't create a second DB connection
Always use `get_db()`. The singleton ensures WAL mode and pragmas are set correctly.

---

## File Quick Reference

| Need to... | Edit this file |
|-----------|---------------|
| Add a bot command | `src/bot/handlers/user/start.py` or new handler file |
| Change main menu buttons | `src/bot/keyboards/user_menu.py` |
| Change how messages are routed | `src/bot/handlers/user/message_handler.py` |
| Change AI prompts | `src/services/ai_service.py` (SYSTEM_PROMPTS dict) |
| Change DB schema | `src/database/migrations/init_schema.sql` + migration |
| Change plan limits | `src/database/migrations/init_schema.sql` (seed data) |
| Change env variables | `src/config.py` (Settings class) |
| Add API endpoint | `src/api/routes/` + register in `src/main.py` |
| Change WebApp pages | `webapp/src/pages/` |
| Change WebApp design | `webapp/tailwind.config.js` + `webapp/src/index.css` |
| Change global state | `webapp/src/store/useStore.ts` |
| Change API calls | `webapp/src/lib/api.ts` |

---

## Test Commands for Bot Verification

After deployment, test these scenarios:

```
1. /start                  → Welcome + main menu
2. /quiz                   → Quiz starts, questions appear
3. /settings               → Level picker keyboard
4. Send: "I goes to school" → Grammar check response
5. Send: "Kitob"           → Shows UNCLEAR prompt
6. /translate              → Enables translation mode → send "Kitob" → EN translation
7. /cancel                 → Resets to auto mode
8. /mystats                → Shows statistics
9. /subscribe              → Shows plan keyboard
10. Admin: /admin          → Dashboard with keyboard
11. Admin: "💳 To'lovlar" → Pending payments
12. Admin: "📢 Broadcast" → Broadcast instructions
13. Tap WebApp button      → WebApp opens
```

---

*Last Updated: 2026-04-21*
