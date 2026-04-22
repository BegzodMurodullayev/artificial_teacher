# ⚛️ Frontend Structure — Artificial Teacher WebApp v2.0

> React 18 + Vite + TypeScript + Tailwind CSS WebApp embedded in Telegram.

---

## 📁 Directory Structure

```
webapp/
├── .env                        # VITE_API_URL=https://backend-url.onrender.com
├── package.json                # Dependencies & scripts
├── vite.config.ts              # Vite config with @ alias
├── tailwind.config.js          # Dark space theme config
├── tsconfig.json               # TypeScript config
├── postcss.config.js           # PostCSS + Tailwind + Autoprefixer
├── index.html                  # Entry HTML
│
├── src/
│   ├── main.tsx                # ReactDOM.createRoot entry
│   ├── App.tsx                 # Router setup with lazy loading
│   ├── index.css               # Global CSS (animations, starfield, glass)
│   ├── vite-env.d.ts           # Vite type declarations
│   │
│   ├── lib/
│   │   └── api.ts              # Axios instance + API functions + types
│   │
│   ├── store/
│   │   └── useStore.ts         # Zustand global state (single store)
│   │
│   ├── pages/                  # Page components
│   │   ├── HomePage.tsx        # Dashboard (XP, stats, usage, chart)
│   │   ├── QuizPage.tsx        # Quiz interface
│   │   ├── ProfilePage.tsx     # User profile + subscription
│   │   ├── ProgressPage.tsx    # Weekly progress + Pomodoro
│   │   ├── LeaderboardPage.tsx # Global leaderboard
│   │   ├── GamesPage.tsx       # Games hub/index
│   │   ├── XOGamePage.tsx      # Tic-Tac-Toe (vs AI)
│   │   ├── MemoryGamePage.tsx  # Memory card matching game
│   │   ├── NumberGamePage.tsx  # Number guessing game
│   │   ├── MathGamePage.tsx    # Quick math challenge
│   │   ├── SudokuGamePage.tsx  # Sudoku puzzle
│   │   ├── admin/
│   │   │   ├── AdminDashboard.tsx  # Admin stats panel
│   │   │   └── AdminBroadcast.tsx  # Broadcast interface
│   │   └── games/              # (empty, games in pages root)
│   │
│   ├── components/
│   │   ├── ui/                 # Reusable UI components
│   │   │   ├── GlassCard.tsx   # Glassmorphism card container
│   │   │   ├── NeonButton.tsx  # Neon-glow button
│   │   │   ├── NeonInput.tsx   # Styled input field
│   │   │   ├── StatCard.tsx    # Stat display card + XpCard
│   │   │   └── Loader.tsx     # Loading spinner + skeleton
│   │   ├── dashboard/          # Dashboard-specific components
│   │   ├── focus/              # Pomodoro timer components
│   │   ├── layout/             # Layout components
│   │   ├── progress/           # Progress chart components
│   │   ├── quiz/               # Quiz UI components
│   │   ├── settings/           # Settings components
│   │   └── tracker/            # Activity tracker components
│   │
│   ├── layouts/
│   │   ├── MainLayout.tsx      # Main app layout with bottom nav
│   │   └── AdminLayout.tsx     # Admin panel layout
│   │
│   ├── hooks/                  # (empty — custom hooks to add)
│   ├── stores/                 # (empty — legacy, using store/)
│   ├── styles/                 # Additional stylesheets
│   └── types/
│       └── telegram.d.ts       # Telegram WebApp type declarations
│
├── public/                     # Static assets
└── dist/                       # Build output (deployed to Netlify)
```

---

## 🗺 Routing (App.tsx)

```tsx
<BrowserRouter>
  <Routes>
    {/* Main WebApp — TabLayout with bottom nav */}
    <Route path="/" element={<MainLayout />} />

    {/* Games — Standalone pages with space background */}
    <Route path="/games/*">
      <Route path=""       element={<GamesPage />} />
      <Route path="xo"     element={<XOGamePage />} />
      <Route path="memory"  element={<MemoryGamePage />} />
      <Route path="number"  element={<NumberGamePage />} />
      <Route path="math"    element={<MathGamePage />} />
      <Route path="sudoku"  element={<SudokuGamePage />} />
    </Route>

    {/* Admin Panel */}
    <Route path="/admin" element={<AdminLayout />}>
      <Route index            element={<AdminDashboard />} />
      <Route path="broadcast" element={<AdminBroadcast />} />
    </Route>

    {/* Fallback */}
    <Route path="*" element={<Navigate to="/" />} />
  </Routes>
</BrowserRouter>
```

All game/admin pages use **lazy loading** with `React.lazy()` + `<Suspense>`.

---

## 🏪 State Management (Zustand)

Single store at `src/store/useStore.ts`:

```typescript
interface AppState {
  // ── Data ──
  user: UserData | null
  stats: StatsData
  usage: UsageData
  plan: PlanData
  xp: XpData
  progress: ProgressData[]
  remainingDays: number

  // ── UI ──
  activeTab: TabKey    // 'home' | 'quiz' | 'progress' | 'leaderboard' | 'profile'
  loading: boolean
  error: string | null

  // ── Actions ──
  hydrateDashboard(data: DashboardData): void
  setActiveTab(tab: TabKey): void
  setLoading(v: boolean): void
  setError(v: string | null): void
}
```

**Selector hooks** (for render optimization):
- `useUser()` — user data
- `useStats()` — stats data
- `useUsage()` — today's usage
- `usePlan()` — current plan
- `useXp()` — XP/level data
- `useProgress()` — weekly progress

---

## 🌐 API Integration (`lib/api.ts`)

### Axios Instance
- **Base URL**: `VITE_API_URL` env var (fallback: `/api`)
- **Auth**: Injects `X-Telegram-Init-Data` header from `window.Telegram.WebApp.initData`
- **Timeout**: 15 seconds
- **Error handling**: Haptic feedback on 401/403

### API Functions

```typescript
// User
userApi.getMe()          → UserData
userApi.getDashboard()   → DashboardData  // Main data load
userApi.getStats()       → StatsData
userApi.getUsage()       → UsageData

// Progress
progressApi.getToday()   → ProgressData
progressApi.getWeek()    → ProgressData[]
progressApi.sync(data)   → { status: "ok" }

// Leaderboard
leaderboardApi.getGlobal(limit) → LeaderboardEntry[]
leaderboardApi.getMyRank()      → { rank, user_id }
```

### TypeScript Interfaces
All API types are defined in `api.ts`:
- `UserData`, `StatsData`, `UsageData`, `PlanData`
- `ProgressData`, `DashboardData`, `LeaderboardEntry`

---

## 🎨 Design System (Tailwind Config)

### Color Palette

| Token | Hex | Usage |
|-------|-----|-------|
| `space-black` | `#05050a` | Page background |
| `space-deep` | `#080b14` | Deep sections |
| `space-dark` | `#0d1117` | Card backgrounds |
| `space-card` | `#0f1420` | Elevated cards |
| `space-border` | `#1a2035` | Borders |
| `space-muted` | `#1e2a45` | Muted backgrounds |
| `neon-cyan` | `#00f3ff` | Primary accent |
| `neon-purple` | `#bc13fe` | Secondary accent |
| `neon-pink` | `#ff2d78` | Tertiary accent |
| `neon-green` | `#00ff88` | Success |
| `neon-yellow` | `#ffe600` | Warning |
| `text-primary` | `#e8eaf0` | Main text |
| `text-secondary` | `#8892aa` | Secondary text |
| `text-muted` | `#4a5568` | Muted text |

### Box Shadows (Neon Glows)

| Token | Effect |
|-------|--------|
| `neon-cyan` | 3-layer cyan glow (8px, 24px, 48px) |
| `neon-purple` | 3-layer purple glow |
| `neon-pink` | 3-layer pink glow |
| `neon-green` | 2-layer green glow |
| `glass` | Card shadow with inner highlight |
| `inner-glow` | Inset cyan glow |

### Gradients

| Token | Direction |
|-------|-----------|
| `grad-cyan-purple` | 135° cyan → purple |
| `grad-purple-pink` | 135° purple → pink |
| `grad-space` | 180° black → deep → dark |
| `grad-card` | 145° card with opacity |
| `shimmer` | Horizontal shimmer animation |

### Animations

| Name | Duration | Effect |
|------|----------|--------|
| `glow-pulse` | 2s | Pulsing neon glow |
| `float` | 6s | Gentle vertical float |
| `shimmer` | 2.5s | Horizontal shimmer |
| `fade-up` | 0.4s | Fade + slide up |
| `scale-in` | 0.3s | Fade + scale in |
| `slide-up` | 0.5s | Spring slide up |
| `slide-right` | 0.4s | Spring slide right |

### Typography
- **Sans**: Inter, system-ui, sans-serif
- **Mono**: JetBrains Mono, Fira Code, monospace

---

## 🧩 UI Components

### `GlassCard.tsx`
Glassmorphism card with backdrop blur and border glow.
```tsx
<GlassCard variant="dark" | "purple" | "cyan" hover>
  {children}
</GlassCard>
```

### `NeonButton.tsx`
Button with neon glow effect.
```tsx
<NeonButton accent="cyan" | "purple" | "pink" | "green" size="sm" | "md" | "lg" onClick={fn}>
  Button Text
</NeonButton>
```

### `StatCard.tsx`
Stat display with icon and accent color + entrance animation.
```tsx
<StatCard icon="✅" label="Tekshiruvlar" value={42} accent="cyan" index={0} />
```

### `XpCard` (in StatCard.tsx)
XP progress card with level, progress bar, and streak.
```tsx
<XpCard totalXp={1500} currentLevel={6} xpToNext={300} streakDays={5} />
```

### `Loader.tsx`
Loading spinner and skeleton card.
```tsx
<Loader size="sm" | "md" | "full" text="Loading..." />
<SkeletonCard />
```

---

## 📱 Key Pages

### HomePage
- Welcome header with name + level badge
- XP card with level progress
- Quick action grid (Check, Quiz, Progress, Leaderboard)
- Games & modules grid (6 items)
- Daily usage meters (checks, quiz, AI, pronunciation)
- Stats grid (4 stat cards)
- Weekly activity area chart (Recharts)
- IQ score card (if available)

### QuizPage
- Quiz start interface with difficulty selection
- Question display with 4-option buttons
- Timer countdown
- Results summary with XP earned

### ProfilePage
- User info, plan badge, level
- Subscription details + upgrade prompt
- Settings controls

### ProgressPage
- Weekly progress chart
- Pomodoro timer (basic)
- Activity log

### LeaderboardPage
- Global ranking table
- User's own rank highlight

### Game Pages
- **XOGamePage**: Tic-Tac-Toe vs AI (minimax) with neon styling
- **MemoryGamePage**: Card matching with emoji pairs
- **NumberGamePage**: Guess the number (1-100) with hints
- **MathGamePage**: Quick math problems with timer
- **SudokuGamePage**: Sudoku puzzle with difficulty levels

---

## 🔧 Telegram WebApp Integration

### Initialization (in AppInitializer)
```typescript
const tg = window.Telegram?.WebApp
if (tg) {
  tg.ready()                      // Signal WebApp is ready
  tg.expand()                     // Expand to full height
  tg.enableClosingConfirmation()  // Confirm before close
}
```

### Type Declarations (`types/telegram.d.ts`)
Declares `window.Telegram.WebApp` interface with:
- `initData`, `initDataUnsafe`
- `ready()`, `expand()`, `close()`
- `sendData(data)`, `showAlert(msg)`
- `HapticFeedback.notificationOccurred(type)`
- `MainButton`, `BackButton`

### Auth Flow
1. WebApp loads → `Telegram.WebApp.initData` available
2. Axios interceptor adds `X-Telegram-Init-Data` header
3. FastAPI middleware validates HMAC-SHA256
4. Extracts `user.id` → queries DB → returns data

---

## 📦 Build & Deploy

### Development
```bash
cd webapp
npm install
npm run dev          # Vite dev server on http://localhost:5173
```

### Production Build
```bash
npm run build        # tsc && vite build → dist/
```

### Netlify Deploy
- **Build command**: `npm run build`
- **Publish directory**: `dist`
- **Environment**: `VITE_API_URL=https://your-backend.onrender.com`

---

*Last Updated: 2026-04-21*
