# 📋 Features to Implement — Artificial Teacher v2.0

> Prioritized feature backlog with implementation details.

---

## Priority 1 — Critical

### 🎮 1.1 Games XP Integration
WebApp games (X-O, Memory, Number, Math, Sudoku) are already built in `webapp/src/pages/`. Missing: XP rewards, stats tracking, and `sendData()` back to bot.

**New files needed**:
- `src/api/routes/games.py` — `POST /api/games/result`
- `src/database/dao/webapp_game_dao.py` — Game result persistence

### 🔧 1.2 Deploy Current Fixes
All bug fixes need deployment to Render (backend) and Netlify (frontend).

---

## Priority 2 — Important

### 📚 2.1 Library/Materials Module
Source: `bolimlar test/kutubxona/`, `evrika/`, `zakovat/`. Create `materials` table, DAO, API routes, bot `/library` command, and `LibraryPage.tsx`.

### ⏱ 2.2 Pomodoro Timer (Full)
Customizable timers, audio alerts, notifications, background mode (Service Worker), stats, XP rewards. Create `PomodoroPage.tsx` and timer hook.

### 🧠 2.3 IQ Test Mode
Full IQ test flow with timed pattern/logic questions, score tracking, and achievements.

---

## Priority 3 — Nice to Have

- 🎙 Voice transcription improvements (longer audio, accuracy scoring)
- 🔍 Inline mode enhancements (quiz sharing, word cards)
- 📊 Advanced admin analytics (growth charts, revenue trends, CSV export)
- ⭐ XP system expansion (multipliers, challenges, seasonal events)
- 🏆 Leaderboard views (weekly/monthly, categories, friend ranking)
- 🕵️ Mafia game engine (roles, night/day phases, voting)
- 💰 Auto-payment (Click.uz, Payme, Telegram Stars, Stripe)
- 🌐 Multi-language UI (Russian, English options)

---

*Last Updated: 2026-04-21*
