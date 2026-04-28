# Artificial Teacher

## Yangi tuzilma

```text
artificial_teacher/
  bot/
    bot.py
    database/
    handlers/
    utils/
    templates/
    html_maker.py
  webapp/
    index.html
    styles.css
    app.js
  engbot.db
  requirements.txt
  .env
```

## Ishga tushirish

1. `pip install -r requirements.txt`
2. `.env` yarating (`.env.example` dan)
3. Bot: `python bot/bot.py`

## Web App ulash

1. Web app fayllarini host qiling (masalan: Vercel/Netlify/Cloudflare Pages).
2. Host URL ni `.env` ichiga yozing:
   - `WEB_APP_URL=https://your-webapp-url`
   - ixtiyoriy plan bo'yicha URLlar:
     - `WEB_APP_URL_FREE=...`
     - `WEB_APP_URL_STANDARD=...`
     - `WEB_APP_URL_PRO=...`
     - `WEB_APP_URL_PREMIUM=...`
3. Agar `materials/` ichidagi alohida sahifalarni Netlify/Vercel ga joylasangiz, ular uchun alohida env ishlating:
   - `MATERIALS_URL=...`
   - `MATERIALS_URL_FREE=...`
   - `MATERIALS_URL_STANDARD=...`
   - `MATERIALS_URL_PRO=...`
   - `MATERIALS_URL_PREMIUM=...`
4. Botda `/app` buyrug'ini bosing yoki `Web App` tugmasini oching.

Muhim:
- `WEB_APP_URL*` faqat asosiy React WebApp uchun.
- `MATERIALS_URL*` esa Netlify'dagi qo'shimcha material/prezentatsiya sahifalari uchun.
- Ikkisini aralashtirib yuborsangiz `IQ Test`, `Pomodoro`, `Games` kabi route'lar noto'g'ri ochilishi mumkin.

## Web App -> Bot sync

Web app `Telegram.WebApp.sendData()` orqali botga quyidagi eventlarni yuboradi:
- `{"action":"pomodoro_done","minutes":25}`
- `{"action":"tracker_sync","words":10,"quizzes":2,"lessons":1}`

Bot bu ma'lumotni `webapp_progress` jadvaliga yozadi.


## Payment mode

Owner panel orqali to'lov tizimini kodga kirmasdan boshqarish mumkin:
- `manual` - faqat chek yuborish va admin tasdig'i
- `hybrid` - auto checkout + qo'lda tasdiqlash ham mavjud
- `auto` - checkout link orqali avtomatik oqim

Owner paneldagi `To'lov sozlamalari` bo'limida quyidagilar boshqariladi:
- provider nomi
- checkout url template
- checkout tugma nomi
- provider token
- provider secret
- karta nomi, raqami, egasi
- manual/auto izohlar

Demak keyin token yoki provider tayyor bo'lganda kod ochmasdan paneldan sozlash mumkin.

## Runtime tuning

User ko'payganda avval host resursini oshirish, keyin kerak bo'lsa faqat `.env` tuning qilish tavsiya etiladi.

Asosiy runtime o'zgaruvchilar:
- `UPDATE_CONCURRENCY`
- `TG_CONNECTION_POOL`
- `TG_POOL_TIMEOUT`
- `AI_CONCURRENCY`
- `AI_QUEUE_WAIT_SEC`
- `AI_REQUEST_TIMEOUT`
- `AI_CONNECT_TIMEOUT`
- `AI_MAX_CONNECTIONS`
- `AI_KEEPALIVE_CONNECTIONS`
- `TTS_CONCURRENCY`
- `TTS_QUEUE_WAIT_SEC`
- `TTS_REQUEST_TIMEOUT`
- `TTS_CONNECT_TIMEOUT`
- `TTS_MAX_CONNECTIONS`
- `TTS_KEEPALIVE_CONNECTIONS`
- `BROADCAST_CHUNK_SIZE`
- `BROADCAST_PAUSE_SEC`
- `HTML_SEND_CONCURRENCY`
- `HTML_SEND_WAIT_SEC`
- `SPONSOR_CACHE_SEC`

## Scale yo'li

Bosqichma-bosqich o'sish tavsiyasi:
1. `1k+` user: RAM/CPU oshirish, `.env` tuning.
2. `10k+` user: webhook rejimiga o'tish tavsiya etiladi.
3. `50k+` user: `SQLite` dan `PostgreSQL` ga o'tish rejalashtiriladi.
4. `100k+` user: Redis queue / background worker / alohida web backend kerak bo'ladi.

Hozirgi kod MVP va early startup stage uchun optimizatsiya qilingan: batch broadcast, sponsor cache, AI/TTS semaphore, HTML send semaphore, payment mode dashboard orqali boshqariladi.

## Docker (local)

1. `.env` ni to'ldiring
2. Ishga tushirish:

```bash
docker compose up --build -d
```

3. Log:

```bash
docker compose logs -f bot
```

## Render deploy

Loyihada `render.yaml` tayyor:
- `artificial-teacher-bot` (Background Worker, Docker)
- `artificial-teacher-webapp` (Static Site)

Qadamlar:
1. GitHub repo'ga push qiling
2. Render -> New -> Blueprint -> repo tanlang
3. Environment variable'larni kiriting (`BOT_TOKEN`, `OWNER_ID`, API keylar)
4. Deploy bosing

Eslatma:
- `WEB_APP_URL` ga static site URL ni yozing (Render webapp deploy bo'lgach)
- DB persistent bo'lishi uchun worker service disk (`/var/data`) ulanadi

## Render Free (faqat bot)

Agar Render `free` ishlatsangiz:
- `render.yaml` ichida faqat bitta `web` service qoldirilgan.
- Bot polling rejimda ishlaydi va ichki health server (`PORT`) ochadi.
- Servis uxlab qolmasligi uchun Telegramga xabar yuborish emas, service URL'ga ping yuborish kerak.

Tavsiya:
- UptimeRobot/Cron-job orqali har 10 daqiqada `https://<render-service>.onrender.com/` ga GET ping yuboring.
- Netlify'dagi web app URL ni `WEB_APP_URL` env ga kiriting.

Eslatma: `free` rejimda `/tmp/engbot.db` vaqtinchalik. Deploy/restart bo'lsa ma'lumot yo'qolishi mumkin.
