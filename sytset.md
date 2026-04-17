# Artificial Teacher tugmalar va oqimlar daraxti

Bu sxema quyidagi manbalardan yig'ildi:
- `bot/bot.py`
- `bot/handlers/admin.py`
- `bot/handlers/subscription.py`
- `bot/handlers/quiz.py`
- `webapp/index.html`
- `webapp/app.js`

Quyida "qaysi tugma nimani ochadi, qaysi tizim qaysisiga ulanadi" degan mantiqda daraxt berilgan.

---

## 1. Telegram bot

```text
Telegram bot
├─ Sponsor tekshiruvi (agar homiy kanal majburiy bo'lsa)
│  ├─ `📢 Kanal nomi`
│  │  └─ Tashqi `t.me/...` linkni ochadi
│  └─ `Tekshirdim`
│     └─ Obuna qayta tekshiriladi
│        ├─ OK bo'lsa → Asosiy menyu
│        └─ Yo'q bo'lsa → Shu ekran qaytadi
│
├─ User panel (reply keyboard)
│  ├─ `✅ Tekshiruv`
│  │  └─ Grammar check mode
│  │     └─ User matn yuboradi
│  │        ├─ Xatolar tahlili
│  │        ├─ To'g'ri variant
│  │        ├─ Daraja signali
│  │        └─ HTML export
│  │
│  ├─ `🔁 Tarjima`
│  │  ├─ `🇺🇿 UZ → EN`
│  │  │  └─ Uzbek matn → English tarjima → HTML export
│  │  ├─ `🇬🇧 EN → UZ`
│  │  │  └─ English matn → Uzbek tarjima → HTML export
│  │  └─ `🏠 Menyu`
│  │     └─ Asosiy menyuga qaytadi
│  │
│  ├─ `🔊 Talaffuz`
│  │  └─ Pronunciation mode
│  │     ├─ `🇺🇸 US`
│  │     │  └─ Aksentni US qiladi
│  │     ├─ `🇬🇧 UK`
│  │     │  └─ Aksentni UK qiladi
│  │     ├─ User so'z/gap yuboradi
│  │     │  ├─ Audio talaffuz qaytadi
│  │     │  ├─ AI tahlil qaytadi
│  │     │  └─ HTML pronunciation guide yuboriladi
│  │     └─ `🔙/🏠 Menyu`
│  │        └─ Asosiy menyuga qaytadi
│  │
│  ├─ `🎯 Quiz`
│  │  └─ Quiz oqimi
│  │     ├─ `5 ta savol` / `10 ta savol` / `15 ta savol` / `20 ta savol`
│  │     ├─ `30 soniya` / `45 soniya` / `60 soniya`
│  │     ├─ `English` / `O'zbekcha`
│  │     ├─ Har savolda `A/B/C/D` variantlar
│  │     │  ├─ To'g'ri/Noto'g'ri feedback
│  │     │  ├─ `➡️ Keyingi savol`
│  │     │  └─ `🛑 Tugatish`
│  │     ├─ Timeout bo'lsa
│  │     │  ├─ `Vaqt tugadi` feedback
│  │     │  ├─ `➡️ Keyingi savol`
│  │     │  └─ `🛑 Tugatish`
│  │     └─ Oxiri
│  │        ├─ `📊 Natijani ko'rish`
│  │        ├─ Yakuniy natija
│  │        ├─ Auto level update
│  │        └─ HTML result fayl
│  │
│  ├─ `🧠 IQ test`
│  │  └─ Quiz oqimiga o'xshaydi
│  │     ├─ Faqat Pro/Premium uchun ochiq
│  │     ├─ Yopiq bo'lsa `💎 Pro olish`
│  │     └─ Oxirida IQ estimate + HTML result
│  │
│  ├─ `📚 Dars`
│  │  └─ Lesson oqimi
│  │     ├─ User level aniqlanadi
│  │     ├─ Levelga mos topic tugmalari chiqadi
│  │     │  └─ `lesson__topic`
│  │     ├─ Topic bosilsa
│  │     │  ├─ AI/Content bank dars tayyorlaydi
│  │     │  ├─ Chatga preview yuboradi
│  │     │  └─ HTML lesson pack yuboradi
│  │     ├─ Limit tugasa `💳 Obuna`
│  │     └─ `🔙 Menyu`
│  │
│  ├─ `📖 Grammatika`
│  │  └─ Grammar menu
│  │     ├─ `📖 Tenses`
│  │     ├─ `📖 Articles`
│  │     ├─ `📖 Prepositions`
│  │     ├─ `❓ Questions`
│  │     ├─ `📖 Conditionals`
│  │     ├─ `📖 Passive Voice`
│  │     ├─ `✍️ O'z mavzum`
│  │     │  └─ User custom mavzu yuboradi → AI tushuntirish qaytadi
│  │     ├─ Mavzu bosilsa → tushuntirish chiqadi
│  │     ├─ `🔙 Grammatika`
│  │     │  └─ Grammar ro'yxatiga qaytadi
│  │     └─ `🏠 Menyu`
│  │
│  ├─ `📅 Kunlik so'z`
│  │  └─ Daily word generator
│  │     ├─ So'z + misol + izoh chiqaradi
│  │     ├─ `🔊 Talaffuz`
│  │     │  └─ Shu so'z pronunciation flowga o'tadi
│  │     └─ `🏠 Menyu`
│  │
│  ├─ `📈 Darajam / Reyting`
│  │  └─ Progress panel
│  │     ├─ User stats
│  │     ├─ Reyting snapshot
│  │     ├─ `📄 HTML hisobot`
│  │     │  └─ Progress report HTML yuboradi
│  │     ├─ `🏆 Top reyting`
│  │     │  └─ Top 10 leaderboard
│  │     ├─ `🎁 Bonuslar`
│  │     │  └─ Bonus markaziga o'tadi
│  │     ├─ `💳 To'lovlar`
│  │     │  └─ User payment history
│  │     ├─ `📦 Tariflar`
│  │     │  └─ Subscription tizimi
│  │     ├─ `📱 Web App`
│  │     │  └─ Mini app ochiladi
│  │     └─ `🏠 Menyu`
│  │
│  ├─ `🎁 Bonuslar`
│  │  └─ Bonus center
│  │     ├─ Referral ball
│  │     ├─ Referral cashback
│  │     ├─ Referral code
│  │     ├─ `🎫 Promo kod`
│  │     │  └─ User promo code yuboradi → ball qo'shiladi
│  │     ├─ `💳 To'lovlar`
│  │     │  └─ Payment history
│  │     ├─ `📦 Tariflar`
│  │     │  └─ Subscription tizimi
│  │     ├─ `📈 Darajam / Reyting`
│  │     │  └─ Progress panel
│  │     ├─ `🔗 Referral bo'limi`
│  │     │  └─ Referral panel
│  │     │     ├─ `📤 Havolani ochish`
│  │     │     │  └─ Referral linkni ochadi
│  │     │     ├─ `🎁 Bonus markazi`
│  │     │     │  └─ Bonus centerga qaytadi
│  │     │     └─ `🔙 Orqaga`
│  │     │        └─ Bonus centerga qaytadi
│  │     ├─ `📱 Web App`
│  │     │  └─ Mini app
│  │     └─ `🏠 Menyu`
│  │
│  ├─ `💳 Tariflar`
│  │  └─ Subscription / payment flow
│  │     ├─ `⭐ Standard`
│  │     ├─ `💎 Pro`
│  │     ├─ `👑 Premium`
│  │     ├─ `🎁 Ball bilan paketlar`
│  │     │  └─ Promo packs
│  │     │     ├─ `Olish #id - X ball`
│  │     │     │  └─ Ball evaziga vaqtinchalik plan/reja beriladi
│  │     │     └─ `🔙 Orqaga`
│  │     ├─ `🏠 Menyu`
│  │     └─ Har bir plan ichida
│  │        ├─ Plan detail
│  │        ├─ `⚡ Auto 1 oy`
│  │        │  └─ Checkout page
│  │        │     ├─ Provider button
│  │        │     │  └─ Tashqi to'lov sahifasi
│  │        │     ├─ `🧾 Qo'lda to'lash` (hybrid/manual-review bo'lsa)
│  │        │     └─ `🔙 Orqaga`
│  │        ├─ `⚡ Auto 1 yil`
│  │        │  └─ Yuqoridagi bilan bir xil, faqat 365 kun
│  │        ├─ `🧾 Qo'lda 1 oy`
│  │        ├─ `🧾 Qo'lda 1 yil`
│  │        │  └─ Manual payment screen
│  │        │     ├─ Karta raqami / egasi / izoh ko'rsatiladi
│  │        │     ├─ `💳 Karta`
│  │        │     │  └─ Card detail screen
│  │        │     ├─ `🧾 Chek yuborish`
│  │        │     │  └─ Receipt kutish rejimi
│  │        │     │     ├─ User rasm/fayl yuboradi
│  │        │     │     ├─ Pending payment DBga yoziladi
│  │        │     │     └─ Adminlarga approve/reject tugmasi bilan yuboriladi
│  │        │     └─ `🔙 Orqaga`
│  │        └─ `🔙 Orqaga`
│  │
│  ├─ `ℹ️ Aloqa`
│  │  └─ About/contact panel
│  │     ├─ `💳 Obuna`
│  │     │  └─ Subscription tizimi
│  │     ├─ `🔙 Menyu`
│  │     ├─ `💬 Aloqa`
│  │     ├─ `📢 Telegram kanal`
│  │     ├─ `📸 Instagram`
│  │     ├─ `🌐 Sayt`
│  │     ├─ `📱 Web App`
│  │     └─ `📞 Dasturchi`
│  │        └─ Barchasi tashqi linklar / mini app
│  │
│  ├─ `📱 Web App`
│  │  └─ Telegram mini appni ochadi
│  │
│  └─ `🛡 Admin panel`
│     └─ Faqat admin/owner foydalanuvchilar uchun
│
├─ Admin panel
│  ├─ `📊 Dashboard`
│  │  └─ Admin summary
│  │
│  ├─ `💳 To'lovlar`
│  │  └─ Pending payments list
│  │     ├─ `#ID Ko'rish`
│  │     │  └─ To'lov detail
│  │     │     ├─ `✅ Tasdiqlash`
│  │     │     │  ├─ Payment approved
│  │     │     │  ├─ Subscription faollashadi
│  │     │     │  ├─ Userga xabar ketadi
│  │     │     │  └─ Referral cashback bo'lsa referrerga ham xabar ketadi
│  │     │     ├─ `❌ Rad etish`
│  │     │     │  ├─ Payment rejected
│  │     │     │  └─ Userga qayta urinish xabari ketadi
│  │     │     └─ `🔙 Orqaga`
│  │     └─ `🔙 Orqaga`
│  │
│  ├─ `👥 Userlar`
│  │  └─ Search flow
│  │     ├─ ID yoki `@username` yuboriladi
│  │     └─ User detail
│  │        ├─ `🚫 Banlash` / `✅ Unban` (dynamic)
│  │        │  └─ User block holatini almashtiradi
│  │        ├─ `🎁 Obuna berish`
│  │        │  └─ Grant flow
│  │        │     ├─ `⭐ Standard (30 kun)`
│  │        │     ├─ `⭐ Standard (365 kun)`
│  │        │     ├─ `💎 Pro (30 kun)`
│  │        │     ├─ `💎 Pro (365 kun)`
│  │        │     ├─ `👑 Premium (30 kun)`
│  │        │     ├─ `👑 Premium (365 kun)`
│  │        │     ├─ `🆓 Free ga qaytarish`
│  │        │     └─ `🔙 Orqaga`
│  │        └─ `🔙 Orqaga`
│  │
│  ├─ `📊 Statistika`
│  │  ├─ Global stats
│  │  ├─ `📄 HTML hisobot`
│  │  │  └─ Global stats HTML yuboradi
│  │  └─ `🔙 Orqaga`
│  │
│  ├─ `📈 Funnel`
│  │  ├─ Sales funnel stats
│  │  ├─ `📄 HTML hisobot`
│  │  │  └─ Funnel HTML yuboradi
│  │  └─ `🔙 Orqaga`
│  │
│  ├─ `📄 HTML hisobotlar`
│  │  ├─ `📊 Global statistika HTML`
│  │  ├─ `📈 Sotuv funnel HTML`
│  │  ├─ `📄 User eksport HTML`
│  │  └─ `🔙 Orqaga`
│  │
│  ├─ `🏆 Reyting`
│  │  └─ Platform leaderboard
│  │
│  ├─ `📄 User eksport`
│  │  └─ `users_export.html` yuboradi
│  │
│  ├─ `📢 Homiy kanallar`
│  │  ├─ Kanal ro'yxati
│  │  ├─ `➕ Kanal qo'shish`
│  │  │  └─ Input kutadi (`@username | nom | link`)
│  │  ├─ `❌ O'chirish #id`
│  │  │  └─ Sponsor channelni o'chiradi
│  │  └─ `🔙 Orqaga`
│  │
│  ├─ `📦 Rejalar`
│  │  ├─ Plan narxlari
│  │  ├─ `Narxni o'zgartirish: Plan`
│  │  │  └─ Yangi monthly narx inputini kutadi
│  │  └─ `🔙 Orqaga`
│  │
│  ├─ `📣 Reklama`
│  │  ├─ Matn yuborilsa → barcha userlarga broadcast
│  │  ├─ Media yuborilsa → barcha userlarga copy broadcast
│  │  └─ `🔙 Orqaga`
│  │
│  ├─ `👤 User panel`
│  │  └─ Oddiy user keyboardiga qaytaradi
│  │
│  ├─ Owner only
│  │  ├─ `⚙️ To'lov sozlamalari`
│  │  │  ├─ `Manual` / `Hybrid` / `Auto`
│  │  │  ├─ `✅/❌ Manual review`
│  │  │  ├─ `Provider`
│  │  │  ├─ `Checkout URL`
│  │  │  ├─ `Checkout label`
│  │  │  ├─ `Provider token`
│  │  │  ├─ `Provider secret`
│  │  │  ├─ `Karta nomi`
│  │  │  ├─ `Karta raqami`
│  │  │  ├─ `Karta egasi`
│  │  │  ├─ `Manual izoh`
│  │  │  ├─ `Auto izoh`
│  │  │  ├─ Har biri bosilganda input kutadi
│  │  │  └─ `🔙 Orqaga`
│  │  │
│  │  ├─ `ℹ️ Aloqa sozlamalari`
│  │  │  ├─ `Dasturchi`
│  │  │  ├─ `Aloqa link`
│  │  │  ├─ `Telegram kanal`
│  │  │  ├─ `Instagram`
│  │  │  ├─ `Sayt`
│  │  │  ├─ `Izoh`
│  │  │  ├─ Har biri bosilganda input kutadi
│  │  │  └─ `🔙 Orqaga`
│  │  │
│  │  ├─ `🎁 Marketing`
│  │  │  ├─ `Referral bonus`
│  │  │  │  └─ Ball miqdori input
│  │  │  ├─ `Quiz balli`
│  │  │  │  └─ To'g'ri javob uchun ball input
│  │  │  ├─ `Promo pack qo'shish`
│  │  │  │  └─ Format: `Nomi | plan | kun | ball`
│  │  │  ├─ `Promo code qo'shish`
│  │  │  │  └─ 3 bosqich
│  │  │  │     ├─ Code
│  │  │  │     ├─ Points
│  │  │  │     └─ Limit
│  │  │  ├─ `❌ Pack o'chirish #id`
│  │  │  └─ `🔙 Orqaga`
│  │  │
│  │  └─ `👮 Adminlar`
│  │     ├─ Hozirgi adminlar ro'yxati
│  │     ├─ ID yoki `@username` yuboriladi
│  │     ├─ `✅ Tasdiqlash`
│  │     │  └─ Role `admin` bo'ladi
│  │     ├─ `❌ Bekor qilish`
│  │     └─ `🔙 Orqaga`
│  │
│  └─ `🔙 Orqaga`
│     └─ Dashboardga qaytadi
│
├─ Group admin (`/admin` group ichida)
│  └─ Guruh sozlamalari
│     ├─ `#check`
│     │  └─ Grammar/check triggerini yoqadi/o'chiradi
│     ├─ `#bot`
│     │  └─ Guruh bot javoblarini yoqadi/o'chiradi
│     ├─ `#t`
│     │  └─ Translate triggerini yoqadi/o'chiradi
│     ├─ `#p`
│     │  └─ Pronunciation triggerini yoqadi/o'chiradi
│     └─ `Kunlik so'z`
│        └─ Daily word funksiyasini yoqadi/o'chiradi
│
└─ Kodda bor, lekin hozir asosiy keyboardda bevosita ko'rinmaydigan callback entry'lar
   ├─ `do_check`
   ├─ `do_translate`
   ├─ `do_quiz`
   ├─ `do_iq`
   ├─ `do_daily`
   ├─ `do_lesson`
   ├─ `do_pron`
   ├─ `do_rules`
   ├─ `do_stats`
   ├─ `do_level`
   │  └─ A1/A2/B1/B2/C1/C2 manual level tanlash
   ├─ `do_level_auto`
   │  └─ Auto level mode yoqadi
   ├─ `do_about`
   └─ `do_webapp`
```

---

## 2. Telegram Web App (mini app)

```text
Web App
├─ Sidebar navigation
│  ├─ `Dashboard`
│  ├─ `Focus`
│  ├─ `Tracker`
│  ├─ `Progress`
│  └─ `Settings`
│
├─ Sidebar cards
│  ├─ `Snapshot yangilash`
│  │  ├─ Inputsdan state yig'adi
│  │  ├─ `tracker_sync` queuega qo'shadi
│  │  └─ Chart/statsni yangilaydi
│  └─ Quick stats / server snapshot / upsell
│     └─ Faqat ko'rsatish bloki
│
├─ Dashboard page
│  ├─ `Tracker` (top action)
│  │  └─ Tracker pagega o'tadi
│  ├─ `Start focus` (top action)
│  │  ├─ Focus pagega o'tadi
│  │  └─ Timerni ishga tushiradi
│  ├─ Daily goals
│  └─ Activity feed
│
├─ Focus page
│  ├─ `Start`
│  │  └─ Pomodoro timer start
│  ├─ `Pause`
│  │  └─ Timerni to'xtatadi
│  ├─ `Reset`
│  │  └─ Focus modega reset qiladi
│  ├─ `Focus (min)`
│  ├─ `Break (min)`
│  ├─ `Long break (min)`
│  │  └─ Free plan'da disable, Pro/Premium'da editable
│  └─ Session tugasa
│     ├─ `pomodoro_done` queuega tushadi
│     ├─ Points oshadi
│     └─ Activity feedga yoziladi
│
├─ Tracker page
│  ├─ `Learned words`
│  ├─ `Solved quiz`
│  ├─ `Lessons done`
│  ├─ `Topics covered`
│  ├─ `Study note`
│  ├─ `Saqlash`
│  │  └─ Local state saqlanadi
│  └─ `Bot uchun navbatga qo'shish`
│     └─ `tracker_sync` queuega tushadi
│
├─ Progress page
│  ├─ Canvas chart
│  └─ `Export JSON`
│     ├─ Faqat Pro/Premium
│     └─ `artificial-teacher-progress.json` download qiladi
│
├─ Settings page
│  ├─ `Theme`
│  ├─ `Language`
│  ├─ `Daily words goal`
│  ├─ `Daily quiz goal`
│  ├─ `Daily lesson goal`
│  ├─ `Haptic feedback`
│  ├─ `Save settings`
│  │  ├─ Local save
│  │  ├─ Theme apply
│  │  └─ `settings_sync` queuega tushadi
│  └─ `Reset all local data`
│     └─ localStorage tozalanadi va sahifa reload bo'ladi
│
└─ Bot bilan sync
   ├─ Web App `sendData()` ishlatadi
   ├─ `pagehide` yoki `visibilitychange=hidden` bo'lganda bulk sync yuboradi
   └─ Bot tomonda `web_app_data_handler`
      ├─ `pomodoro_done` → DBga focus minutes + points yozadi
      ├─ `tracker_sync` → words/quizzes/lessons snapshotni yozadi
      └─ `settings_sync` → user web settingsni yozadi
```

---

## 3. Tizimlararo ulanishlar

```text
User `💳 Tariflar`
→ subscription flow
→ manual receipt yoki auto checkout
→ pending payment
→ Admin `💳 To'lovlar`
→ `✅ Tasdiqlash` / `❌ Rad etish`
→ subscription status update

User `📱 Web App`
→ mini app ochiladi
→ local tracker/focus/settings yig'iladi
→ botga bulk sync ketadi
→ DB progress yangilanadi
→ `📈 Darajam / Reyting` panelida ko'rinadi

User `🎯 Quiz`
→ correct answers
→ reward setting bo'yicha points
→ Bonus center / referral walletga ta'sir qiladi

Admin `🎁 Marketing`
→ referral ball / quiz ball / promo pack / promo code
→ User `🎁 Bonuslar` bo'limiga ta'sir qiladi
```

---

## 4. Qo'shimcha kichik UI

```text
Service page (`bot/site/index.html`)
└─ `Health check`
   └─ `/health` endpointni ochadi
```
