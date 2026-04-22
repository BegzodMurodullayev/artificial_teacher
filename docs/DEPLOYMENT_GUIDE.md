# 🚀 Deployment Guide — Artificial Teacher v2.0

> Step-by-step guide for deploying the backend (Render) and frontend (Netlify).

---

## Architecture Overview

```
GitHub (main branch)
       │
       ├──▶ Render.com ──▶ Backend (Bot + FastAPI)
       │         Docker   DB_PATH=/tmp/engbot.db
       │
       └──▶ Netlify ──▶ Frontend (WebApp)
                VITE_API_URL=https://...onrender.com
```

---

## 🐳 Backend — Render.com (Docker)

### Files Used
- `Dockerfile` — Docker build instructions
- `render.yaml` — Render service config
- `requirements_v2.txt` — Python dependencies

### Dockerfile (current)
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements_v2.txt .
RUN pip install --no-cache-dir -r requirements_v2.txt
COPY . .
CMD ["python", "-m", "src.main"]
```

### Deploy Steps

1. **Connect GitHub repo to Render**
   - Sign in to [render.com](https://render.com)
   - New → Web Service → Connect GitHub repo
   - Select `artificial_teacher` repository

2. **Service settings**
   - Name: `artificial-teacher-bot`
   - Runtime: Docker
   - Dockerfile path: `./Dockerfile`
   - Plan: Free (or Starter for always-on)

3. **Set Environment Variables** (in Render Dashboard → Environment)

   | Key | Value | Notes |
   |-----|-------|-------|
   | `BOT_TOKEN` | `7xxx:AAA...` | From @BotFather |
   | `OWNER_ID` | `123456789` | Your Telegram user ID |
   | `BOT_USERNAME` | `@Artificial_teacher_bot` | Exact username |
   | `DB_PATH` | `/tmp/engbot.db` | Render ephemeral storage |
   | `OPENROUTER_API_KEY` | `sk-or-v1-...` | OpenRouter dashboard |
   | `OPENAI_API_KEY` | `sk-...` | For Whisper transcription |
   | `TOPMEDIAI_API_KEY` | `...` | TopMediai dashboard |
   | `AI_MODEL` | `openai/gpt-4o-mini` | Or any OpenRouter model |
   | `WEB_APP_URL` | `https://your-app.netlify.app` | After Netlify deploy |
   | `SUPPORT_URL` | `https://t.me/your_support` | |
   | `WEBSITE_URL` | `https://your-site.com` | |
   | `API_HOST` | `0.0.0.0` | |
   | `API_PORT` | `8080` | Render uses PORT env var |

4. **Deploy**
   - Click "Deploy" or push to `main` branch
   - Render auto-builds and deploys

### Important Notes

> ⚠️ **DB_PATH is ephemeral on Render's free plan!** The `/tmp/` directory is reset on every redeploy. All user data is lost. For production, use:
> - Render Persistent Disk ($7/month)
> - Or migrate to PostgreSQL (requires codebase changes)

> ⚠️ **Free plan sleeps after 15 minutes of inactivity**. Bot polling keeps it awake, so this is less of an issue.

### Verify Backend is Running

```bash
curl https://your-app.onrender.com/health
# Should return: {"status": "ok"}
```

---

## ⚛️ Frontend — Netlify

### Files Used
- `webapp/` directory
- `webapp/package.json` — Build scripts
- `webapp/vite.config.ts` — Build config

### Deploy Steps

1. **Connect GitHub to Netlify**
   - Sign in to [netlify.com](https://netlify.com)
   - New site from Git → Connect GitHub
   - Select `artificial_teacher` repository

2. **Build settings**
   - Base directory: `webapp`
   - Build command: `npm run build`
   - Publish directory: `webapp/dist`

3. **Environment Variables** (Netlify → Site Settings → Environment)

   | Key | Value |
   |-----|-------|
   | `VITE_API_URL` | `https://your-app.onrender.com` |

4. **Deploy**
   - Netlify auto-builds on push to `main`
   - Or trigger manually: Site → Deploys → Trigger deploy

### Verify Frontend

Visit `https://your-app.netlify.app` in a regular browser — you should see the WebApp UI (may show loading error since no Telegram auth in browser — that's normal).

Test inside Telegram: Open the bot and tap "📱 Ilovani ochish".

---

## 🤖 Telegram Bot Setup

### BotFather Commands

```
/setname — Artificial Teacher
/setdescription — AI-powered English learning bot for Uzbek speakers
/setabouttext — Learn English with AI! Grammar ✅ | Translation 🌐 | Quiz 🧠 | Games 🎮
/setuserpic — Upload bot avatar
/setcommands —
start - Asosiy menyu
help - Yordam
quiz - Quiz boshlash
mystats - Statistika
subscribe - Obuna rejalari
settings - Sozlamalar
clear - Suhbat tarixini tozalash
teacher - O'qituvchi rejimi
translate - Tarjima rejimi
correct - Grammatika rejimi
cancel - Rejimni bekor qilish
admin - Admin panel (admin only)
```

### Configure WebApp

```
/newapp — Create WebApp for your bot
/setdomain — your-app.netlify.app
/setwebhook — (skip if using long polling)
```

### Enable Inline Mode (Optional)
```
/setinline — Enable inline mode
Inline placeholder: check: text | tr: text | p: us: word
```

---

## 🔄 CI/CD Workflow

Current workflow is simple push-to-deploy:

```
git add .
git commit -m "fix: admin panel routing"
git push origin main
# → Render rebuilds backend (2-3 min)
# → Netlify rebuilds frontend (1-2 min)
```

### Recommended Git Branches
- `main` — production (auto-deploys)
- `dev` — development (manual deploys)

---

## 🗄 Database Management

### Local Development

```bash
# Create fresh DB
python -m src.main  # Creates DB on first run

# View DB
sqlite3 data/engbot.db
.tables
SELECT * FROM users LIMIT 5;
.quit
```

### Render Production

```bash
# SSH into Render shell (requires paid plan)
# Or use Render's Shell tab in Dashboard
sqlite3 /tmp/engbot.db .tables
```

### Backup Strategy (Important!)

Since `/tmp` is ephemeral on Render free plan, implement a periodic backup:

```python
# In src/bot/jobs/ — add backup_job.py
# Every 6 hours: dump DB to a Telegram channel as file
# Or: use Render Persistent Disk ($7/month)
```

---

## 🔐 Security Checklist

- [x] Bot token stored as Render env var (never in code)
- [x] Telegram initData validated with HMAC-SHA256
- [x] Rate limiting (ThrottleMiddleware, 0.5s per message)
- [x] Role-based access control (RoleFilter)
- [x] User ban system
- [x] HTML escaping in all bot messages (escape_html())
- [ ] CORS configuration for FastAPI (if WebApp domain changes)
- [ ] API rate limiting (consider adding to FastAPI middleware)
- [ ] Sensitive logs not exposing token/keys

---

## 🔧 Monitoring

### Render Logs
- Render Dashboard → Logs tab
- Filter by level: ERROR, WARNING

### Bot Error Notifications
Add to `main.py`:
```python
# Send critical errors to owner
async def error_handler(update, exception):
    await bot.send_message(settings.OWNER_ID, f"❌ Error: {exception}")
```

### Health Check Endpoint
```
GET https://your-app.onrender.com/health
→ {"status": "ok", "db": "connected", "bot": "polling"}
```

---

*Last Updated: 2026-04-21*
