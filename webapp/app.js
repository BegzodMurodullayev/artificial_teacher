(function () {
  const tg = window.Telegram?.WebApp;
  if (tg) {
    tg.ready();
    tg.expand();
  }

  const qs = new URLSearchParams(window.location.search);
  const plan = (qs.get("plan") || "free").toLowerCase();
  const uid = qs.get("uid") || "0";

  const level = qs.get("level") || "A1";
  const serverRank = Number(qs.get("rank") || 0);
  const serverScore = Number(qs.get("score") || 0);

  const isPro = plan === "pro" || plan === "premium";
  const isPremium = plan === "premium";

  const POMODORO_RING = 327;
  const STORAGE_KEY = "at_webapp_v2";
  const SYNC_QUEUE_LIMIT = 20;
  let signalCtx = null;

  const state = {
    plan,
    uid,
    page: "dashboard",
    timerMode: "focus",
    focusMinutes: 25,
    breakMinutes: 5,
    longBreakMinutes: 15,
    remainingSec: 25 * 60,
    running: false,
    timerId: null,
    sessionCount: 0,
    totalFocusMinutes: 0,
    words: 0,
    quizzes: 0,
    lessons: 0,
    topics: "",
    note: "",
    points: 0,
    goals: { words: 20, quiz: 5, lessons: 2 },
    settings: { theme: "system", lang: "uz", haptic: "on" },
    activity: [],
    syncQueue: [],
    lastSyncLabel: "Auto sync tayyor",
    serverLevel: level,
    serverRank,
    serverScore,
  };

  const refs = {
    planText: document.getElementById("planText"),
    sideWords: document.getElementById("sideWords"),
    sideQuiz: document.getElementById("sideQuiz"),
    sideLessons: document.getElementById("sideLessons"),
    sideLevel: document.getElementById("sideLevel"),
    sideRank: document.getElementById("sideRank"),
    sideScore: document.getElementById("sideScore"),
    syncStatus: document.getElementById("syncStatus"),
    upsellTitle: document.getElementById("upsellTitle"),
    upsellCopy: document.getElementById("upsellCopy"),
    topEyebrow: document.getElementById("topEyebrow"),
    topTitle: document.getElementById("topTitle"),
    topDesc: document.getElementById("topDesc"),
    metricPoints: document.getElementById("metricPoints"),
    metricFocus: document.getElementById("metricFocus"),
    metricCompletion: document.getElementById("metricCompletion"),
    metricMode: document.getElementById("metricMode"),
    activityFeed: document.getElementById("activityFeed"),
    goalWords: document.getElementById("goalWords"),
    goalQuiz: document.getElementById("goalQuiz"),
    goalLessons: document.getElementById("goalLessons"),
    barWords: document.getElementById("barWords"),
    barQuiz: document.getElementById("barQuiz"),
    barLessons: document.getElementById("barLessons"),
    timerView: document.getElementById("timerView"),
    sessionLabel: document.getElementById("sessionLabel"),
    ringFg: document.getElementById("ringFg"),
    focusInput: document.getElementById("focusInput"),
    breakInput: document.getElementById("breakInput"),
    longBreakInput: document.getElementById("longBreakInput"),
    focusGate: document.getElementById("focusGate"),
    wordsInput: document.getElementById("wordsInput"),
    quizInput: document.getElementById("quizInput"),
    lessonInput: document.getElementById("lessonInput"),
    topicsInput: document.getElementById("topicsInput"),
    noteInput: document.getElementById("noteInput"),
    exportGate: document.getElementById("exportGate"),
    progressCanvas: document.getElementById("progressCanvas"),
    themeSelect: document.getElementById("themeSelect"),
    langSelect: document.getElementById("langSelect"),
    hapticSelect: document.getElementById("hapticSelect"),
    goalWordsInput: document.getElementById("goalWordsInput"),
    goalQuizInput: document.getElementById("goalQuizInput"),
    goalLessonInput: document.getElementById("goalLessonInput"),
  };

  const pageMeta = {
    dashboard: {
      eyebrow: "Dashboard",
      title: "Learning Control Panel",
      desc: "Kunlik natijalar, goals va faollik bir joyda.",
    },
    focus: {
      eyebrow: "Focus",
      title: "Pomodoro Session",
      desc: "Diqqat bilan ishlash va break muvozanati.",
    },
    tracker: {
      eyebrow: "Tracker",
      title: "Daily Learning Tracker",
      desc: "Words, quiz, lessons va mavzularni saqlang.",
    },
    progress: {
      eyebrow: "Progress",
      title: "Analytics View",
      desc: "Mahalliy data asosida vizual natijalar.",
    },
    settings: {
      eyebrow: "Settings",
      title: "Personal Preferences",
      desc: "Theme va ishlash sozlamalarini boshqaring.",
    },
  };

  function emitHaptic(type = "light") {
    if (state.settings.haptic !== "on") return;
    if (!tg || !tg.HapticFeedback) return;
    if (type === "success") {
      tg.HapticFeedback.notificationOccurred("success");
      return;
    }
    tg.HapticFeedback.impactOccurred("light");
  }

  function playSignal(kind = "focus") {
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) return;
    try {
      if (!signalCtx) signalCtx = new AudioCtx();
      const now = signalCtx.currentTime;
      const gain = signalCtx.createGain();
      gain.connect(signalCtx.destination);
      gain.gain.setValueAtTime(0.0001, now);
      gain.gain.exponentialRampToValueAtTime(0.08, now + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.45);

      const osc = signalCtx.createOscillator();
      osc.type = kind === "break" ? "triangle" : "sine";
      osc.frequency.setValueAtTime(kind === "break" ? 740 : 880, now);
      osc.connect(gain);
      osc.start(now);
      osc.stop(now + 0.45);
    } catch (_) {
      // ignore audio issues
    }
  }

  function updateSyncStatus(label) {
    if (label) state.lastSyncLabel = label;
    if (refs.syncStatus) refs.syncStatus.textContent = state.lastSyncLabel || "Auto sync tayyor";
  }

  function queueSync(payload) {
    if (!payload || !payload.action) return;
    const action = String(payload.action);
    if (action === "tracker_sync" || action === "settings_sync") {
      state.syncQueue = state.syncQueue.filter((item) => item.action !== action);
      state.syncQueue.push(payload);
    } else if (action === "pomodoro_done") {
      const existing = state.syncQueue.find((item) => item.action === "pomodoro_done");
      if (existing) {
        existing.minutes = Number(existing.minutes || 0) + Number(payload.minutes || 0);
        existing.points = Number(existing.points || 0) + Number(payload.points || 0);
      } else {
        state.syncQueue.push(payload);
      }
    } else {
      state.syncQueue.push(payload);
    }
    if (state.syncQueue.length > SYNC_QUEUE_LIMIT) {
      state.syncQueue = state.syncQueue.slice(-SYNC_QUEUE_LIMIT);
    }
    updateSyncStatus(`Sync navbatida: ${state.syncQueue.length}`);
    saveLocal();
  }

  function flushSyncQueue() {
    if (!state.syncQueue.length) return;
    if (!tg || typeof tg.sendData !== "function") return;
    try {
      tg.sendData(JSON.stringify({ action: "bulk_sync", items: state.syncQueue }));
      state.syncQueue = [];
      updateSyncStatus("Sync yuborildi");
      saveLocal();
    } catch (_) {
      updateSyncStatus("Sync navbatda qoldi");
    }
  }


  function pushActivity(text) {
    const stamp = new Date().toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
    if (/sync qilindi/i.test(text)) return;
    state.activity.unshift(`${stamp} - ${text}`);
    state.activity = state.activity.slice(0, isPremium ? 40 : 20);
  }

  function saveLocal() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }

  function loadLocal() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const data = JSON.parse(raw);
      const keep = [
        "focusMinutes", "breakMinutes", "longBreakMinutes", "sessionCount", "totalFocusMinutes",
        "words", "quizzes", "lessons", "topics", "note", "points", "goals", "settings", "activity", "syncQueue", "lastSyncLabel",
      ];
      keep.forEach((k) => {
        if (data[k] !== undefined) state[k] = data[k];
      });
      if (!Array.isArray(state.activity)) state.activity = [];
      state.activity = state.activity.filter((item) => !/sync qilindi/i.test(String(item || "")));
      if (!Array.isArray(state.syncQueue)) state.syncQueue = [];
    } catch (_) {
      // ignore
    }
  }


  function applyTheme() {
    const selected = state.settings.theme || "system";
    let finalTheme = selected;
    if (selected === "system") {
      finalTheme = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    }
    document.documentElement.setAttribute("data-theme", finalTheme);
  }

  function setPage(page) {
    state.page = page;
    document.querySelectorAll(".nav-item").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.page === page);
    });
    document.querySelectorAll(".page").forEach((el) => {
      el.classList.toggle("active", el.id === `page-${page}`);
    });
    const m = pageMeta[page] || pageMeta.dashboard;
    refs.topEyebrow.textContent = m.eyebrow;
    refs.topTitle.textContent = m.title;
    refs.topDesc.textContent = m.desc;
  }

  function calcCompletion() {
    const gw = Math.max(1, Number(state.goals.words || 1));
    const gq = Math.max(1, Number(state.goals.quiz || 1));
    const gl = Math.max(1, Number(state.goals.lessons || 1));
    const p1 = Math.min(100, Math.round((state.words / gw) * 100));
    const p2 = Math.min(100, Math.round((state.quizzes / gq) * 100));
    const p3 = Math.min(100, Math.round((state.lessons / gl) * 100));
    return Math.round((p1 + p2 + p3) / 3);
  }

  function renderFeed() {
    refs.activityFeed.innerHTML = "";
    if (!state.activity.length) {
      const li = document.createElement("li");
      li.textContent = "Hali activity yo'q.";
      refs.activityFeed.appendChild(li);
      return;
    }
    state.activity.forEach((item) => {
      const li = document.createElement("li");
      li.textContent = item;
      refs.activityFeed.appendChild(li);
    });
  }

  function renderGoals() {
    refs.goalWords.textContent = `${state.words} / ${state.goals.words}`;
    refs.goalQuiz.textContent = `${state.quizzes} / ${state.goals.quiz}`;
    refs.goalLessons.textContent = `${state.lessons} / ${state.goals.lessons}`;

    const w = Math.min(100, (state.words / Math.max(1, state.goals.words)) * 100);
    const q = Math.min(100, (state.quizzes / Math.max(1, state.goals.quiz)) * 100);
    const l = Math.min(100, (state.lessons / Math.max(1, state.goals.lessons)) * 100);
    refs.barWords.style.width = `${w}%`;
    refs.barQuiz.style.width = `${q}%`;
    refs.barLessons.style.width = `${l}%`;
  }

  function renderStats() {
    refs.planText.textContent = `Plan: ${state.plan.toUpperCase()}`;
    refs.sideWords.textContent = String(state.words);
    refs.sideQuiz.textContent = String(state.quizzes);
    refs.sideLessons.textContent = String(state.lessons);
    refs.sideLevel.textContent = String(state.serverLevel || "A1");
    refs.sideRank.textContent = state.serverRank > 0 ? `#${state.serverRank}` : "-";
    refs.sideScore.textContent = String(state.serverScore || 0);
    refs.metricPoints.textContent = String(state.points);
    refs.metricFocus.textContent = String(state.totalFocusMinutes);
    refs.metricCompletion.textContent = `${calcCompletion()}%`;
    refs.metricMode.textContent = state.plan.charAt(0).toUpperCase() + state.plan.slice(1);
    updateSyncStatus();
    if (refs.upsellTitle && refs.upsellCopy) {
      if (isPremium) {
        refs.upsellTitle.textContent = "Premium analytics";
        refs.upsellCopy.textContent = "To'liq export, chuqur progress nazorati va maksimal flexibility sizda ochiq.";
      } else if (isPro) {
        refs.upsellTitle.textContent = "Pro growth";
        refs.upsellCopy.textContent = "Ko'proq export va custom focus rejimlari yoqilgan. Premium yanada chuqur analytics beradi.";
      } else {
        refs.upsellTitle.textContent = "Free plan";
        refs.upsellCopy.textContent = "Free foydali, lekin Pro/Premium'da custom timer, export va kuchli analytics bilan o'sish tezroq bo'ladi.";
      }
    }
    renderGoals();
    renderFeed();
  }

  function drawChart() {
    const cvs = refs.progressCanvas;
    const ctx = cvs.getContext("2d");
    const values = [state.words, state.quizzes, state.lessons, state.totalFocusMinutes];
    const labels = ["Words", "Quiz", "Lessons", "Focus"];
    const colors = ["#3b82f6", "#14b8a6", "#f59e0b", "#8b5cf6"];
    const max = Math.max(10, ...values);

    const w = cvs.width;
    const h = cvs.height;
    ctx.clearRect(0, 0, w, h);

    ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue("--surface-soft");
    ctx.fillRect(0, 0, w, h);

    const left = 70;
    const top = 25;
    const bottom = h - 55;
    const usableW = w - left - 25;
    const barW = Math.min(150, Math.floor(usableW / (values.length * 1.6)));

    ctx.strokeStyle = getComputedStyle(document.documentElement).getPropertyValue("--line");
    for (let i = 0; i <= 5; i += 1) {
      const y = top + ((bottom - top) / 5) * i;
      ctx.beginPath();
      ctx.moveTo(left, y);
      ctx.lineTo(w - 15, y);
      ctx.stroke();
    }

    values.forEach((v, i) => {
      const x = left + i * (barW + 80) + 30;
      const bh = Math.max(2, Math.round((v / max) * (bottom - top)));
      const y = bottom - bh;

      ctx.fillStyle = colors[i];
      ctx.fillRect(x, y, barW, bh);

      ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue("--ink");
      ctx.font = "bold 14px Segoe UI";
      ctx.fillText(String(v), x + 6, y - 8);
      ctx.font = "13px Segoe UI";
      ctx.fillText(labels[i], x, bottom + 20);
    });
  }

  function setRingProgress(totalSec, remainingSec) {
    const progress = Math.max(0, Math.min(1, remainingSec / Math.max(1, totalSec)));
    const dashOffset = POMODORO_RING * (1 - progress);
    refs.ringFg.style.strokeDasharray = String(POMODORO_RING);
    refs.ringFg.style.strokeDashoffset = String(dashOffset);
  }

  function formatTime(sec) {
    const m = Math.floor(sec / 60).toString().padStart(2, "0");
    const s = Math.floor(sec % 60).toString().padStart(2, "0");
    return `${m}:${s}`;
  }

  function renderTimer() {
    refs.timerView.textContent = formatTime(state.remainingSec);
    const total = state.timerMode === "focus" ? state.focusMinutes * 60 : state.breakMinutes * 60;
    setRingProgress(total, state.remainingSec);
  }

  function applyPlanGate() {
    refs.focusGate.textContent = "";
    refs.exportGate.textContent = "";

    if (!isPro) {
      state.focusMinutes = 25;
      state.breakMinutes = 5;
      state.longBreakMinutes = 15;
      refs.focusInput.value = "25";
      refs.breakInput.value = "5";
      refs.longBreakInput.value = "15";
      refs.focusInput.disabled = true;
      refs.breakInput.disabled = true;
      refs.longBreakInput.disabled = true;
      refs.focusGate.textContent = "Free plan: 25/5 focus rejimi saqlanadi. Pro yoki Premium'da custom pomodoro ochiladi.";
      refs.exportGate.textContent = "JSON export va chuqur analytics Pro/Premium uchun ochiq.";
      document.getElementById("exportJson").disabled = true;
    } else {
      refs.focusInput.disabled = false;
      refs.breakInput.disabled = false;
      refs.longBreakInput.disabled = false;
      document.getElementById("exportJson").disabled = false;
      if (isPremium) {
        refs.exportGate.textContent = "Premium analytics mode yoqilgan.";
      }
    }
  }

  function startTimer() {
    if (state.running) return;

    state.focusMinutes = Number(refs.focusInput.value || state.focusMinutes || 25);
    state.breakMinutes = Number(refs.breakInput.value || state.breakMinutes || 5);
    state.longBreakMinutes = Number(refs.longBreakInput.value || state.longBreakMinutes || 15);

    if (state.remainingSec <= 0) {
      state.remainingSec = state.focusMinutes * 60;
      state.timerMode = "focus";
      refs.sessionLabel.textContent = "Focus";
    }

    state.running = true;
    state.timerId = setInterval(() => {
      state.remainingSec -= 1;
      renderTimer();

      if (state.remainingSec <= 0) {
        clearInterval(state.timerId);
        state.timerId = null;
        state.running = false;

        if (state.timerMode === "focus") {
          state.sessionCount += 1;
          state.totalFocusMinutes += state.focusMinutes;
          state.points += Math.max(1, Math.floor(state.focusMinutes / 5));
          pushActivity(`Focus session tugadi (${state.focusMinutes} min)`);
          queueSync({ action: "pomodoro_done", minutes: state.focusMinutes, points: Math.max(1, Math.floor(state.focusMinutes / 5)) });
          emitHaptic("success");
          playSignal("focus");

          state.timerMode = "break";
          refs.sessionLabel.textContent = "Break";
          state.remainingSec = state.breakMinutes * 60;
          renderStats();
          drawChart();
          saveLocal();
        } else {
          state.timerMode = "focus";
          refs.sessionLabel.textContent = "Focus";
          state.remainingSec = state.focusMinutes * 60;
          pushActivity("Break tugadi, keyingi focus tayyor");
          playSignal("break");
          renderStats();
          saveLocal();
        }

        renderTimer();
      }
    }, 1000);
  }

  function pauseTimer() {
    state.running = false;
    clearInterval(state.timerId);
    state.timerId = null;
  }

  function resetTimer() {
    pauseTimer();
    state.timerMode = "focus";
    refs.sessionLabel.textContent = "Focus";
    state.focusMinutes = Number(refs.focusInput.value || 25);
    state.remainingSec = state.focusMinutes * 60;
    renderTimer();
  }

  function syncTrackerToBot() {
    queueSync({
      action: "tracker_sync",
      words: state.words,
      quizzes: state.quizzes,
      lessons: state.lessons,
      points: state.points,
    });
    emitHaptic("light");
    renderFeed();
    saveLocal();
  }


  function applyInputsToState() {
    state.words = Math.max(0, Number(refs.wordsInput.value || 0));
    state.quizzes = Math.max(0, Number(refs.quizInput.value || 0));
    state.lessons = Math.max(0, Number(refs.lessonInput.value || 0));
    state.topics = String(refs.topicsInput.value || "").trim();
    state.note = String(refs.noteInput.value || "").trim();
    state.points = state.words + state.quizzes * 3 + state.lessons * 4 + Math.floor(state.totalFocusMinutes / 5);
  }

  function hydrateInputs() {
    refs.focusInput.value = state.focusMinutes;
    refs.breakInput.value = state.breakMinutes;
    refs.longBreakInput.value = state.longBreakMinutes;
    refs.wordsInput.value = state.words;
    refs.quizInput.value = state.quizzes;
    refs.lessonInput.value = state.lessons;
    refs.topicsInput.value = state.topics;
    refs.noteInput.value = state.note;
    refs.themeSelect.value = state.settings.theme || "system";
    refs.langSelect.value = state.settings.lang || "uz";
    refs.hapticSelect.value = state.settings.haptic || "on";
    refs.goalWordsInput.value = state.goals.words;
    refs.goalQuizInput.value = state.goals.quiz;
    refs.goalLessonInput.value = state.goals.lessons;
  }

  function exportJson() {
    if (!isPro) return;
    const payload = {
      uid: state.uid,
      plan: state.plan,
      words: state.words,
      quizzes: state.quizzes,
      lessons: state.lessons,
      focusMinutesTotal: state.totalFocusMinutes,
      sessionCount: state.sessionCount,
      topics: state.topics,
      note: state.note,
      goals: state.goals,
      settings: state.settings,
      exportedAt: new Date().toISOString(),
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "artificial-teacher-progress.json";
    a.click();
    URL.revokeObjectURL(url);
    pushActivity("JSON export olindi");
    renderFeed();
  }

  function saveSettings() {
    state.settings.theme = refs.themeSelect.value;
    state.settings.lang = refs.langSelect.value;
    state.settings.haptic = refs.hapticSelect.value;
    state.goals.words = Math.max(5, Number(refs.goalWordsInput.value || 20));
    state.goals.quiz = Math.max(1, Number(refs.goalQuizInput.value || 5));
    state.goals.lessons = Math.max(1, Number(refs.goalLessonInput.value || 2));

    applyTheme();
    renderStats();
    drawChart();
    saveLocal();

    queueSync({ action: "settings_sync", theme: state.settings.theme, lang: state.settings.lang });
    pushActivity("Settings saqlandi");
    renderFeed();
    emitHaptic("success");
  }

  function resetAll() {
    pauseTimer();
    localStorage.removeItem(STORAGE_KEY);
    location.reload();
  }

  function bindEvents() {
    document.querySelectorAll(".nav-item").forEach((btn) => {
      btn.addEventListener("click", () => {
        setPage(btn.dataset.page);
      });
    });

    document.getElementById("openFocusTop").addEventListener("click", () => {
      setPage("focus");
      startTimer();
    });

    document.getElementById("sendTrackerTop").addEventListener("click", () => {
      setPage("tracker");
    });

    document.getElementById("syncBtn").addEventListener("click", () => {
      applyInputsToState();
      syncTrackerToBot();
      updateSyncStatus("Tracker snapshot yangilandi");
      renderStats();
      drawChart();
    });

    document.getElementById("startTimer").addEventListener("click", startTimer);
    document.getElementById("pauseTimer").addEventListener("click", pauseTimer);
    document.getElementById("resetTimer").addEventListener("click", resetTimer);

    document.getElementById("saveTracker").addEventListener("click", () => {
      applyInputsToState();
      pushActivity("Tracker local saqlandi");
      renderStats();
      drawChart();
      saveLocal();
      emitHaptic("light");
    });

    document.getElementById("sendTracker").addEventListener("click", () => {
      applyInputsToState();
      syncTrackerToBot();
      updateSyncStatus("Tracker navbatga qo'shildi");
      renderStats();
      drawChart();
    });

    document.getElementById("exportJson").addEventListener("click", exportJson);
    document.getElementById("saveSettings").addEventListener("click", saveSettings);
    document.getElementById("resetAll").addEventListener("click", resetAll);

    [refs.wordsInput, refs.quizInput, refs.lessonInput].forEach((el) => {
      el.addEventListener("input", () => {
        applyInputsToState();
        renderStats();
        drawChart();
      });
    });
  }


  function init() {
    state.plan = plan;
    loadLocal();
    hydrateInputs();
    applyTheme();
    applyPlanGate();
    setPage("dashboard");

    renderTimer();
    renderStats();
    drawChart();
    bindEvents();

    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "hidden") flushSyncQueue();
    });
    window.addEventListener("pagehide", flushSyncQueue);
  }

  init();
})();
