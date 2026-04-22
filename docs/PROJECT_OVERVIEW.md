# 🎓 Artificial Teacher — Project Overview

> **Telegram-based English learning bot** for Uzbek-speaking users, powered by AI, with a modern WebApp dashboard.

---

## 📋 Project Info

| Field | Value |
|-------|-------|
| **Project Name** | Artificial Teacher |
| **Version** | 2.0.0 |
| **Bot Username** | `@Artificial_teacher_bot` |
| **Primary Language** | Uzbek (UI), English (learning content) |
| **Monetization** | Freemium subscription model (UZS) |

---

## 🛠 Tech Stack

### Backend
| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.12 | Core language |
| aiogram | ≥3.4 | Telegram Bot framework (async) |
| FastAPI | ≥0.110 | REST API for WebApp |
| aiosqlite | ≥0.20 | Async SQLite driver |
| httpx | ≥0.27 | HTTP client (for OpenRouter/TTS) |
| openai | ≥1.0 | Whisper transcription |
| pydantic-settings | ≥2.0 | Config management |
| APScheduler | ≥3.10 | Scheduled jobs (daily word) |
| uvicorn | ≥0.29 | ASGI server |
| Jinja2 | ≥3.1 | Template rendering |

### Frontend (WebApp)
| Technology | Version | Purpose |
|------------|---------|---------|
| React | 18.3.x | UI framework |
| Vite | 5.3.x | Build tool |
| TypeScript | 5.4.x | Type safety |
| Tailwind CSS | 3.4.x | Styling (dark space theme) |
| Zustand | 4.5.x | State management |
| Framer Motion | 11.2.x | Animations |
| Recharts | 2.12.x | Charts & graphs |
| Axios | 1.7.x | HTTP client |
| React Router DOM | 6.23.x | Client-side routing |
| Lucide React | 0.390.x | Icons |
| date-fns | 3.6.x | Date formatting |
| @telegram-apps/sdk | 2.0.x | Telegram WebApp SDK |

### Deployment
| Service | Target | Purpose |
|---------|--------|---------|
| Render.com | Backend | Bot + FastAPI (Docker, free plan) |
| Netlify | Frontend | WebApp static hosting |

---

## 🏗 Architecture

```
┌──────────────────────────────────────────────────────┐
│                    Telegram User                      │
│              (Private Chat / Group Chat)              │
└─────────┬──────────────────────────────────┬─────────┘
          │ Messages/Commands                │ WebApp
          ▼                                  ▼
┌─────────────────────┐          ┌─────────────────────┐
│   aiogram 3.x Bot   │          │   React WebApp      │
│   ┌───────────────┐ │          │  (Vite + TS + TW)   │
│   │ Middlewares    │ │          │   ┌───────────────┐ │
│   │ ├─ Throttle    │ │          │   │ Zustand Store │ │
│   │ ├─ Auth        │ │          │   │ API Client    │ │
│   │ └─ Sponsor     │ │          │   │ Pages/Comps   │ │
│   ├───────────────┤ │          │   └───────┬───────┘ │
│   │ Handlers      │ │          └───────────┼─────────┘
│   │ ├─ User       │ │                      │
│   │ ├─ Admin      │ │                      │ X-Telegram-Init-Data
│   │ ├─ Quiz       │ │                      ▼
│   │ ├─ Game       │ │          ┌─────────────────────┐
│   │ ├─ Inline     │ │          │    FastAPI Server    │
│   │ ├─ Group      │ │          │  (HMAC-SHA256 Auth)  │
│   │ └─ Subscription│ │         │   ├─ /api/user/*    │
│   └───────────────┘ │          │   ├─ /api/progress/* │
└────────┬────────────┘          │   └─ /api/leaderboard│
         │                       └──────────┬──────────┘
         │                                   │
         ▼                                   ▼
┌──────────────────────────────────────────────────────┐
│                   SQLite (WAL Mode)                   │
│  ┌─────────┐ ┌──────┐ ┌───────┐ ┌───────────────┐   │
│  │ users   │ │plans │ │stats  │ │quiz_sessions  │   │
│  │ subs    │ │pays  │ │daily  │ │xp_transactions│   │
│  │ history │ │games │ │wallet │ │achievements   │   │
│  └─────────┘ └──────┘ └───────┘ └───────────────┘   │
└──────────────────────────────────────────────────────┘
         │                    │
         ▼                    ▼
┌─────────────────┐  ┌─────────────────┐
│  OpenRouter AI  │  │  TopMediai TTS  │
│  (GPT-4o-mini)  │  │  (Pronunciation) │
└─────────────────┘  └─────────────────┘
```

---

## ✨ Key Features

### Core Learning
- ✅ **Grammar Checking** — AI-powered grammar analysis with corrections and explanations
- 🌐 **Translation** — Bidirectional UZ↔EN translation with notes
- 🔊 **Pronunciation** — IPA guides + TTS audio (TopMediai API)
- 📚 **Lessons** — Static lesson packs (greetings, shopping, travel) + AI-generated custom lessons
- 📖 **Grammar Rules** — Built-in rule database (tenses, articles, prepositions, etc.)
- 🎙 **Voice Transcription** — Whisper API for voice message processing

### Testing & Games
- 🧠 **Quiz** — AI-generated multiple-choice quizzes (DB-backed sessions)
- 🧠 **IQ Test** — Logical reasoning test with scoring
- 🎮 **Group Games** — Word games, error finding, translation races (in Telegram groups)
- 🕹️ **WebApp Games** — X-O, Memory, Sudoku, Number Guessing, Math Challenge

### Gamification
- ⭐ **XP System** — Earn XP from all activities, level up (1-100)
- 🏅 **Achievements** — 13 built-in achievements with XP rewards
- 🔥 **Streaks** — Daily activity tracking with longest streak record
- 🏆 **Leaderboard** — Global ranking by learning score

### Monetization
- 💳 **4-tier Subscription** — Free, Standard (29K UZS), Pro (59K), Premium (99K)
- 📋 **Manual Payments** — Receipt upload → admin approval workflow
- 🎁 **Promo Codes** — Admin-created codes for free upgrades
- 👥 **Referral System** — Unique referral codes with point rewards

### Admin Panel
- 📊 **Dashboard** — User count, revenue, conversion stats
- 💳 **Payment Management** — Approve/reject pending payments
- 📢 **Broadcast** — Send messages to all users
- 👥 **User Management** — Search by ID/username
- ⚙️ **Plan Management** — View/edit subscription plans

---

## 📁 Folder Structure

```
artificial_teacher/
├── .env                        # Environment variables (secret)
├── .env.example                # Environment template
├── Dockerfile                  # Docker config for Render
├── render.yaml                 # Render.com deploy config
├── requirements_v2.txt         # Python dependencies (active)
├── requirements.txt            # Old dependencies (v1)
│
├── src/                        # 🐍 Backend source code
│   ├── main.py                 # Entry point (Bot + API + Scheduler)
│   ├── config.py               # Centralized settings (pydantic-settings)
│   ├── bot/                    # Telegram bot module
│   │   ├── loader.py           # Singleton: Bot, Dispatcher, Scheduler
│   │   ├── handlers/           # Message/callback handlers
│   │   │   ├── user/           # User-facing handlers
│   │   │   ├── admin/          # Admin dashboard
│   │   │   ├── quiz/           # Quiz system
│   │   │   ├── game/           # Group games + mini-games
│   │   │   ├── subscription/   # Payment/plan handlers
│   │   │   ├── group/          # Group message handlers
│   │   │   └── inline/         # Inline query handlers
│   │   ├── keyboards/          # Reply + Inline keyboards
│   │   ├── middlewares/        # Throttle, Auth, Sponsor
│   │   ├── filters/            # Role, Plan, ChatType filters
│   │   ├── utils/              # Telegram helpers (safe_reply, etc.)
│   │   └── jobs/               # Scheduled tasks (daily word)
│   ├── database/               # Database layer
│   │   ├── connection.py       # Async SQLite singleton (WAL mode)
│   │   ├── models.py           # Dataclass models (framework-agnostic)
│   │   ├── dao/                # Data Access Objects (12 DAOs)
│   │   └── migrations/         # init_schema.sql
│   ├── services/               # Business logic services
│   │   ├── ai_service.py       # OpenRouter API client
│   │   ├── ai_teacher_service.py # Intent router + teacher Q&A
│   │   ├── tts_service.py      # TopMediai TTS
│   │   ├── level_service.py    # Auto-level adjustment
│   │   ├── content_service.py  # Static lessons + grammar + moderation
│   │   ├── mode_manager.py     # User mode tracking (SQLite-backed)
│   │   └── transcription_service.py # Whisper voice-to-text
│   ├── api/                    # FastAPI REST API
│   │   ├── routes/             # User, Progress, Leaderboard
│   │   ├── middleware/         # Telegram initData auth
│   │   └── schemas/            # Pydantic request/response models
│   └── templates/              # Jinja2 templates (unused currently)
│
├── webapp/                     # ⚛️ Frontend (React WebApp)
│   ├── package.json            # Dependencies
│   ├── vite.config.ts          # Vite build config
│   ├── tailwind.config.js      # Tailwind theme (dark space)
│   ├── tsconfig.json           # TypeScript config
│   ├── src/
│   │   ├── App.tsx             # Router setup with lazy loading
│   │   ├── main.tsx            # React entry point
│   │   ├── index.css           # Global CSS + animations
│   │   ├── lib/api.ts          # Axios API client
│   │   ├── store/useStore.ts   # Zustand state management
│   │   ├── pages/              # Page components
│   │   ├── components/         # Reusable components
│   │   ├── layouts/            # MainLayout, AdminLayout
│   │   └── types/              # TypeScript declarations
│   └── dist/                   # Built output (Netlify deploy)
│
├── bolimlar test/              # 📂 Source material for future features
│   ├── oyinlar/                # HTML/JS game prototypes (X-O, Memory, etc.)
│   ├── kutubxona/              # Library content
│   ├── evrika/                 # Fun facts
│   ├── zakovat/                # Logic quiz material
│   ├── reyting/                # Leaderboard prototypes
│   └── sozlamalar/             # Settings prototypes
│
├── docs/                       # 📖 Documentation (this directory)
├── bot/                        # (Legacy bot files, unused)
├── bot.py                      # (Legacy monolith, unused in v2)
├── database.py                 # (Legacy DB module, unused in v2)
└── tests/                      # (Empty, tests needed)
```

---

## 🌍 Environment Variables

See `.env.example` for full template. Key variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `BOT_TOKEN` | ✅ | Telegram Bot API token |
| `OWNER_ID` | ✅ | Telegram user ID of bot owner |
| `OPENROUTER_API_KEY` | ✅ | OpenRouter API key for AI |
| `OPENAI_API_KEY` | ⬜ | OpenAI key (for Whisper transcription) |
| `TOPMEDIAI_API_KEY` | ⬜ | TopMediai key (for TTS audio) |
| `DB_PATH` | ✅ | SQLite database file path |
| `WEB_APP_URL` | ⬜ | Netlify URL for WebApp |
| `AI_MODEL` | ✅ | OpenRouter model ID (default: `openai/gpt-4o-mini`) |
| `API_HOST` / `API_PORT` | ✅ | FastAPI server bind (default: `0.0.0.0:8080`) |

---

## 📊 Current Status

### ✅ Done (Implemented)
- Complete bot v2 architecture (modular handlers, DAOs, services)
- Grammar checking with AI (check mode)
- Translation (UZ↔EN with AI)
- Pronunciation guide + TTS audio
- Quiz system (DB-backed sessions)
- Static lessons and grammar rules
- Admin dashboard (stats, payments, broadcast, user management)
- Subscription system (4-tier plans, manual payment workflow)
- XP & achievements gamification
- Daily word scheduler
- Voice message transcription (Whisper)
- Intent-based smart message routing
- WebApp (React) — Home, Quiz, Profile, Leaderboard, Progress pages
- WebApp Games — X-O, Memory, Number Guessing, Math, Sudoku
- Inline mode (@bot queries)
- Group chat support (#check, #t, #p, #bot)
- Sponsor channel enforcement

### ⚠️ Partially Done / Needs Testing
- Admin panel button routing (was broken, patched)
- WebApp auth (401 error fixed in code, needs deployment)
- Intent router accuracy (needs fine-tuning)

### ❌ Not Yet Implemented
- Library/Materials module (kutubxona, evrika, zakovat)
- Pomodoro timer (full-featured)
- Mafia game engine (basic structure exists)
- Voice message support in WebApp
- Advanced analytics dashboard
- Stripe/Payme/Click payment integration
- Tests (test directory is empty)

---

*Last Updated: 2026-04-21*
