/**
 * API client — Axios instance connected to the FastAPI backend.
 * Base URL is read from VITE_API_URL env var (falls back to /api for dev proxy).
 */

import axios, {
  type AxiosInstance,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
} from 'axios'

// ── Config ────────────────────────────────────────────

const BASE_URL = import.meta.env.VITE_API_URL ?? '/api'

// ── Create Instance ───────────────────────────────────

export const api: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 15_000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// ── Request Interceptor: inject Telegram initData ──────

api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Get Telegram WebApp initData for authentication
    const tg = window.Telegram?.WebApp
    if (tg?.initData) {
      config.headers['X-Telegram-Init-Data'] = tg.initData
    }
    return config
  },
  (error) => Promise.reject(error)
)

// ── Response Interceptor: normalize errors ─────────────

api.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error) => {
    const status = error.response?.status
    const message = error.response?.data?.detail ?? error.message

    if (status === 401 || status === 403) {
      console.warn('[API] Auth error:', message)
      // Telegram WebApp — notify user via haptic
      window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('error')
    }

    if (status === 429) {
      console.warn('[API] Rate limited')
    }

    if (status >= 500) {
      console.error('[API] Server error:', message)
    }

    return Promise.reject({
      status,
      message,
      raw: error,
    })
  }
)

// ══════════════════════════════════════════════════════
// API Functions — typed wrappers
// ══════════════════════════════════════════════════════

// ── Types ─────────────────────────────────────────────

export interface UserData {
  user_id:    number
  username:   string
  first_name: string
  role:       string
  level:      string
  joined_at:  string
}

export interface StatsData {
  checks_total:      number
  translations_total:number
  pron_total:        number
  quiz_played:       number
  quiz_correct:      number
  lessons_total:     number
  messages_total:    number
  streak_days:       number
  iq_score:          number
  learning_score:    number
}

export interface UsageData {
  checks:      number
  quiz:        number
  lessons:     number
  ai_messages: number
  pron_audio:  number
}

export interface PlanData {
  name:               string
  display_name:       string
  price_monthly:      number
  price_yearly:       number
  checks_per_day:     number
  quiz_per_day:       number
  lessons_per_day:    number
  ai_messages_day:    number
  pron_audio_per_day: number
  voice_enabled:      number
  inline_enabled:     number
  iq_test_enabled:    number
  badge:              string
}

export interface ProgressData {
  progress_date:  string
  words:          number
  quiz:           number
  lessons:        number
  focus_minutes:  number
  topics:         string
  note:           string
  points:         number
}

export interface DashboardData {
  user:           UserData
  stats:          StatsData
  usage_today:    UsageData
  plan:           PlanData
  remaining_days: number
  progress_week:  ProgressData[]
}

export interface LeaderboardEntry {
  rank:           number
  user_id:        number
  username:       string
  first_name:     string
  level:          string
  total_xp:       number
  learning_score: number
  streak_days:    number
}

export interface GameResultData {
  game_name: string
  difficulty: string
  score: number
  won: boolean
}

// ── User API ──────────────────────────────────────────

export const userApi = {
  getMe:        () => api.get<UserData>('/user/me').then(r => r.data),
  getDashboard: () => api.get<DashboardData>('/user/dashboard').then(r => r.data),
  getStats:     () => api.get<StatsData>('/user/stats').then(r => r.data),
  getUsage:     () => api.get<UsageData>('/user/usage').then(r => r.data),
}

// ── Progress API ──────────────────────────────────────

export const progressApi = {
  getToday: () => api.get<ProgressData>('/progress/today').then(r => r.data),
  getWeek:  () => api.get<ProgressData[]>('/progress/week').then(r => r.data),
  sync: (data: Partial<ProgressData>) =>
    api.post('/progress/sync', data).then(r => r.data),
}

// ── Leaderboard API ───────────────────────────────────

export const leaderboardApi = {
  getGlobal: (limit = 20) =>
    api.get<LeaderboardEntry[]>(`/leaderboard/global?limit=${limit}`).then(r => r.data),
  getMyRank: () =>
    api.get<{ rank: number; user_id: number }>('/leaderboard/myrank').then(r => r.data),
}

// ── Games API ─────────────────────────────────────────

export const gamesApi = {
  saveResult: (data: GameResultData) => api.post('/games/result', data).then(r => r.data),
}

export interface MaterialData {
  id: number
  material_type: string
  category: string | null
  title: string
  author: string | null
  description: string | null
  content: any | null
  created_at: string
}

export const materialsApi = {
  getMaterials: (type: string, limit = 50, offset = 0) =>
    api.get<MaterialData[]>(`/materials?material_type=${type}&limit=${limit}&offset=${offset}`).then(r => r.data),
  searchMaterials: (q: string, type?: string, limit = 20) =>
    api.get<MaterialData[]>(`/materials/search?q=${q}${type ? `&material_type=${type}` : ''}&limit=${limit}`).then(r => r.data),
  getMaterialById: (id: number) =>
    api.get<MaterialData>(`/materials/${id}`).then(r => r.data),
}

export default api
