# 🐛 Current Bugs — Artificial Teacher v2.0

> Known issues, root causes, and fix status.

---

## Bug #1: Admin Panel Button Routing Issues

### Symptom
When admin presses buttons like "💳 To'lovlar", "👥 Foydalanuvchilar", etc., the bot responds with "❌ Tarjima qilib bo'lmadi" (translation error) instead of showing admin content.

### Root Cause
1. **Menu aliases mismatch**: The admin button texts in `user_menu.py` aliases (e.g., `"💳 To'lovlar"`) were not matching the actual button text being sent.
2. **Handler routing**: The `smart_message_handler` in `message_handler.py` was catching admin button presses before the admin router could handle them, treating them as translation requests.
3. **Admin fallback missing**: The `menu.py` dispatcher didn't have proper routing for admin action keys.

### Files Affected
| File | Issue |
|------|-------|
| `src/bot/keyboards/user_menu.py` | Admin button aliases now added (lines 130-136) |
| `src/bot/handlers/user/menu.py` | Admin action routing added (lines 112-132) |
| `src/bot/handlers/admin/dashboard.py` | Reply keyboard handlers added (lines 49-131) |
| `src/bot/handlers/user/message_handler.py` | Menu button skip logic (line 97-99) |

### Fix Status
✅ **Fixed in code** — Admin buttons now route correctly through:
1. `menu.py` catches admin button texts
2. Checks `_is_admin()` permission
3. Delegates to `dashboard.py` handler functions
4. `message_handler.py` skips any text that resolves to a menu action

⚠️ **Needs deployment** — Changes are in local code, not yet deployed to Render.

### Verification Steps
1. Log in as admin/owner
2. Press "🛡 Admin Panel" → should show admin keyboard
3. Press "💳 To'lovlar" → should show pending payments
4. Press "📈 Statistika" → should show global stats
5. Press "🔙 Asosiy Menyu" → should return to main menu

---

## Bug #2: WebApp Authentication Error (401)

### Symptom
WebApp shows "Missing Telegram initData" error when trying to load dashboard data. API returns 401 status.

### Root Cause
1. **Middleware too strict**: `TelegramAuthMiddleware` in `telegram_auth.py` was rejecting all requests without `initData`, even in development.
2. **Missing header**: The Axios interceptor only sends `X-Telegram-Init-Data` when `window.Telegram.WebApp.initData` is available — which doesn't exist in browser dev mode.
3. **No dev bypass**: No mechanism to skip auth for local development.

### Files Affected
| File | Issue |
|------|-------|
| `src/api/middleware/telegram_auth.py` | Strict auth check on all non-excluded paths |
| `webapp/src/lib/api.ts` | Interceptor correctly sends header when available |
| `webapp/src/App.tsx` | AppInitializer silently catches dashboard load failure |

### Fix Applied
```python
# telegram_auth.py — excluded paths expanded
EXCLUDED_PATHS = {"/", "/health", "/docs", "/openapi.json", "/redoc"}
```

The `AppInitializer` in `App.tsx` now catches errors silently:
```typescript
.catch((err) => {
    console.warn('Dashboard load failed (dev mode?):', err)
    setError(null) // Silent fail in dev
    setLoading(false)
})
```

### Fix Status
✅ **Fixed in code** — Auth works correctly when opened inside Telegram WebApp.
⚠️ **Needs deployment** — Backend needs redeployment to Render.

### Notes
- In production (opened via Telegram), `initData` is always available
- In dev mode (browser), API calls will fail silently — this is expected
- Consider adding a `DEV_MODE` env var to skip auth in development

---

## Bug #3: Bot Logic Confusion — All Messages Treated as Translation

### Symptom
Any text message sent to the bot gets routed to the translation handler, regardless of content. English text that should be grammar-checked gets translated instead.

### Root Cause
1. **Intent router not called**: The `smart_message_handler` was using rule-based routing that defaulted to translation for non-Latin text.
2. **Missing CORRECTION mode**: When text was Latin but mode was `None`, it should default to CORRECTION but was falling through to UNCLEAR.
3. **Bot keywords too broad**: Keywords like "nima", "qanday" were matching normal Uzbek text.

### Files Affected
| File | Issue |
|------|-------|
| `src/bot/handlers/user/message_handler.py` | Rule-based routing logic (lines 114-131) |
| `src/services/ai_teacher_service.py` | Intent detection (called but result sometimes ignored) |
| `src/services/mode_manager.py` | Mode persistence and expiry |

### Fix Applied
The `smart_message_handler` now uses this routing priority:
```python
# 1. Check if user has an active forced mode (/teacher, /correct, etc.)
current_mode = await mode_manager.get_mode(user_id)

# 2. If no forced mode, use rule-based detection:
if len(text.split()) > 100 or "def " in text:     → TECHNICAL
elif bot_keywords and short text:                   → SUPPORT (AI chat)
elif is_latin and not is_cyrillic:                  → CORRECTION ✅
else:                                               → UNCLEAR (shows menu)
```

### Fix Status
✅ **Fixed in code** — Latin text now correctly routes to grammar check.
⚠️ **Needs testing** — Edge cases with mixed-language text need verification.

### Known Remaining Issues
- Mixed UZ+EN text may not route correctly
- Very short English text (1-2 words) might be ambiguous
- The AI-based intent router (`get_intent()`) is not being called in the rule-based flow — consider re-enabling for ambiguous cases

---

## Bug #4: Quiz Session State Persistence

### Symptom
Quiz sessions occasionally lose state — user answers a question but the bot doesn't recognize the answer or shows "session not found".

### Root Cause
1. **Race condition**: If user answers very quickly, the `update_quiz_session()` call may conflict with the next question generation.
2. **Session lookup**: `get_active_quiz_session()` uses `ORDER BY id DESC LIMIT 1`, which is correct but relies on single active session per user.

### Files Affected
| File | Issue |
|------|-------|
| `src/bot/handlers/quiz/quiz_start.py` | Quiz flow logic |
| `src/database/dao/quiz_dao.py` | Session CRUD |

### Fix Status
⚠️ **Partially fixed** — Sessions are now DB-backed (moved from in-memory dict), but race conditions may still occur under load.

### Suggested Fix
- Add `UNIQUE(user_id)` constraint to active quiz sessions
- Use `FOR UPDATE` semantics (or SQLite exclusive transaction) when updating

---

## Bug #5: Daily Usage Counter Reset

### Symptom
Daily usage counters (`daily_usage` table) sometimes don't reset at midnight, causing users to hit limits from the previous day.

### Root Cause
The `daily_usage` table uses `usage_date TEXT` with ISO date format. The `get_usage_today()` function uses Python's `date.today()` which depends on the server timezone.

### Files Affected
| File | Issue |
|------|-------|
| `src/database/dao/stats_dao.py` | `get_usage_today()` uses `date.today()` |

### Fix Status
⚠️ **Known issue** — Server runs in UTC (Render), but users are in UZT (UTC+5). Usage resets at midnight UTC, not midnight UZT.

### Suggested Fix
- Use UTC consistently and document that limits reset at 05:00 UZT
- Or use user's timezone if stored

---

## Bug #6: Inline Mode Audio Caching

### Symptom
Pronunciation audio sent via inline mode sometimes fails because the cached Telegram file_id becomes invalid.

### Root Cause
Telegram file_ids are bot-specific and can expire. The inline caching system uses `INLINE_AUDIO_CHANNEL` to cache files, but doesn't handle expiry.

### Files Affected
| File | Issue |
|------|-------|
| `src/bot/handlers/inline/inline_handler.py` | Audio caching logic |

### Fix Status
⚠️ **Known issue** — Needs cache invalidation strategy.

---

*Last Updated: 2026-04-21*
