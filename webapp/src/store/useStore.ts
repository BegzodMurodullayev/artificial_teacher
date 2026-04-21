/**
 * Global Zustand store — single source of truth for the WebApp.
 */

import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'
import type { DashboardData, ProgressData } from '@/lib/api'

// ══════════════════════════════════════════════════════
// TYPE DEFINITIONS
// ══════════════════════════════════════════════════════

interface UserState {
  user_id:    number
  first_name: string
  username:   string
  role:       string
  level:      string        // English level: A1-C2
  joined_at:  string
}

interface XpState {
  total_xp:       number
  current_level:  number   // Gamification level 1-100
  xp_to_next:     number
  streak_days:    number
  longest_streak: number
}

interface StatsState {
  checks_total:       number
  translations_total: number
  pron_total:         number
  quiz_played:        number
  quiz_correct:       number
  lessons_total:      number
  messages_total:     number
  streak_days:        number
  iq_score:           number
  learning_score:     number
}

interface UsageState {
  checks:      number
  quiz:        number
  lessons:     number
  ai_messages: number
  pron_audio:  number
}

interface PlanState {
  name:               string
  display_name:       string
  price_monthly:      number
  checks_per_day:     number
  quiz_per_day:       number
  lessons_per_day:    number
  ai_messages_day:    number
  pron_audio_per_day: number
  voice_enabled:      boolean
  inline_enabled:     boolean
  iq_test_enabled:    boolean
  badge:              string
  remaining_days:     number
}

interface UIState {
  isLoading:      boolean
  error:          string | null
  activeTab:      'home' | 'progress' | 'quiz' | 'leaderboard' | 'profile'
  theme:          'dark'
}

interface AppStore {
  // ── State ──
  user:    UserState | null
  xp:      XpState
  stats:   StatsState
  usage:   UsageState
  plan:    PlanState
  progress: ProgressData[]
  ui:      UIState

  // ── Computed ──
  isAdmin:   () => boolean
  isPaid:    () => boolean
  quizAccuracy: () => number

  // ── Actions ──
  setUser:      (u: UserState) => void
  setXp:        (x: Partial<XpState>) => void
  setStats:     (s: StatsState) => void
  setUsage:     (u: UsageState) => void
  setPlan:      (p: PlanState) => void
  setProgress:  (p: ProgressData[]) => void
  setLoading:   (v: boolean) => void
  setError:     (e: string | null) => void
  setActiveTab: (t: UIState['activeTab']) => void

  // ── Hydrate from API dashboard response ──
  hydrateDashboard: (data: DashboardData) => void

  // ── Reset ──
  reset: () => void
}

// ══════════════════════════════════════════════════════
// DEFAULT STATE
// ══════════════════════════════════════════════════════

const defaultXp: XpState = {
  total_xp: 0, current_level: 1, xp_to_next: 100,
  streak_days: 0, longest_streak: 0,
}

const defaultStats: StatsState = {
  checks_total: 0, translations_total: 0, pron_total: 0,
  quiz_played: 0, quiz_correct: 0, lessons_total: 0,
  messages_total: 0, streak_days: 0, iq_score: 0, learning_score: 0,
}

const defaultUsage: UsageState = {
  checks: 0, quiz: 0, lessons: 0, ai_messages: 0, pron_audio: 0,
}

const defaultPlan: PlanState = {
  name: 'free', display_name: 'Free ✨', price_monthly: 0,
  checks_per_day: 12, quiz_per_day: 5, lessons_per_day: 3,
  ai_messages_day: 20, pron_audio_per_day: 5,
  voice_enabled: false, inline_enabled: false, iq_test_enabled: false,
  badge: '', remaining_days: 0,
}

const defaultUI: UIState = {
  isLoading: false, error: null, activeTab: 'home', theme: 'dark',
}

// ══════════════════════════════════════════════════════
// STORE
// ══════════════════════════════════════════════════════

export const useStore = create<AppStore>()(
  devtools(
    persist(
      (set, get) => ({
        // ── Initial State ──
        user:     null,
        xp:       defaultXp,
        stats:    defaultStats,
        usage:    defaultUsage,
        plan:     defaultPlan,
        progress: [],
        ui:       defaultUI,

        // ── Computed ──
        isAdmin:  () => ['admin', 'owner'].includes(get().user?.role ?? ''),
        isPaid:   () => !['', 'free'].includes(get().plan.name),
        quizAccuracy: () => {
          const { quiz_played, quiz_correct } = get().stats
          return quiz_played > 0 ? Math.round((quiz_correct / quiz_played) * 100) : 0
        },

        // ── Setters ──
        setUser:      (u) => set({ user: u }),
        setXp:        (x) => set((s) => ({ xp: { ...s.xp, ...x } })),
        setStats:     (s) => set({ stats: s }),
        setUsage:     (u) => set({ usage: u }),
        setPlan:      (p) => set({ plan: p }),
        setProgress:  (p) => set({ progress: p }),
        setLoading:   (v) => set((s) => ({ ui: { ...s.ui, isLoading: v } })),
        setError:     (e) => set((s) => ({ ui: { ...s.ui, error: e } })),
        setActiveTab: (t) => set((s) => ({ ui: { ...s.ui, activeTab: t } })),

        // ── Hydrate from dashboard API ──
        hydrateDashboard: (data: DashboardData) => {
          const { user, stats, usage_today, plan, remaining_days, progress_week } = data
          set({
            user: {
              user_id:    user.user_id,
              first_name: user.first_name,
              username:   user.username,
              role:       user.role,
              level:      user.level,
              joined_at:  user.joined_at,
            },
            stats,
            usage: usage_today,
            plan: {
              name:               plan.name,
              display_name:       plan.display_name,
              price_monthly:      plan.price_monthly,
              checks_per_day:     plan.checks_per_day,
              quiz_per_day:       plan.quiz_per_day,
              lessons_per_day:    plan.lessons_per_day,
              ai_messages_day:    plan.ai_messages_day,
              pron_audio_per_day: plan.pron_audio_per_day,
              voice_enabled:      Boolean(plan.voice_enabled),
              inline_enabled:     Boolean(plan.inline_enabled),
              iq_test_enabled:    Boolean(plan.iq_test_enabled),
              badge:              plan.badge,
              remaining_days,
            },
            xp: {
              ...defaultXp,
              streak_days: stats.streak_days,
            },
            progress: progress_week,
            ui: { ...defaultUI, isLoading: false, error: null },
          })
        },

        // ── Reset ──
        reset: () => set({
          user: null, xp: defaultXp, stats: defaultStats,
          usage: defaultUsage, plan: defaultPlan, progress: [],
          ui: defaultUI,
        }),
      }),
      {
        name: 'artificial-teacher-store',
        partialize: (state) => ({
          // Only persist non-sensitive UI state
          ui: { activeTab: state.ui.activeTab },
        }),
      }
    ),
    { name: 'ArtificialTeacher' }
  )
)

// ── Selector hooks (for performance) ──────────────────

export const useUser         = () => useStore((s) => s.user)
export const useXp           = () => useStore((s) => s.xp)
export const useStats        = () => useStore((s) => s.stats)
export const useUsage        = () => useStore((s) => s.usage)
export const usePlan         = () => useStore((s) => s.plan)
export const useProgress     = () => useStore((s) => s.progress)
export const useUI           = () => useStore((s) => s.ui)
export const useActiveTab    = () => useStore((s) => s.ui.activeTab)
export const useIsAdmin      = () => useStore((s) => s.isAdmin())
export const useIsPaid       = () => useStore((s) => s.isPaid())
export const useQuizAccuracy = () => useStore((s) => s.quizAccuracy())
