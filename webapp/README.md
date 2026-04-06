# Web App (artificial_teacher/webapp)

## Features
- Pomodoro focus timer
- Daily tracker (words, quizzes, lessons)
- Progress canvas chart
- Free/Pro/Premium gates via URL query (`?plan=free|pro|premium`)
- Telegram WebApp `sendData` sync to bot

## Deploy
This folder is static.

Use any static hosting:
- Cloudflare Pages
- Netlify
- Vercel (static)

After deploy, set the URL to bot `.env`:
- `WEB_APP_URL=https://your-domain.example`
