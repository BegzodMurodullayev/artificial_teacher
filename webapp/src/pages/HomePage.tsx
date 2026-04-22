/**
 * HomePage — Main dashboard with XP, stats, quick actions, and activity chart.
 */

import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer
} from 'recharts'
import { GlassCard } from '@/components/ui/GlassCard'
import { StatCard, XpCard } from '@/components/ui/StatCard'
import { SkeletonCard } from '@/components/ui/Loader'
import { useStore, useUser, useStats, useUsage, usePlan, useProgress, useXp } from '@/store/useStore'
import { userApi } from '@/lib/api'
import { format } from 'date-fns'

const LEVEL_COLORS: Record<string, string> = {
  A1: '#00ff88', A2: '#00f3ff', B1: '#ffe600',
  B2: '#bc13fe', C1: '#ff2d78', C2: '#ff6b00',
}

function UsageMeter({ used, limit, label, color = '#00f3ff' }: {
  used: number; limit: number; label: string; color?: string
}) {
  const pct = limit > 0 ? Math.min(100, (used / limit) * 100) : 0
  return (
    <div className="flex flex-col gap-1">
      <div className="flex justify-between text-xs">
        <span className="text-text-secondary">{label}</span>
        <span style={{ color }}>{used}/{limit}</span>
      </div>
      <div className="h-1.5 bg-space-muted rounded-full overflow-hidden">
        <motion.div
          className="h-full rounded-full"
          style={{ backgroundColor: color, boxShadow: `0 0 6px ${color}88` }}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.8, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
        />
      </div>
    </div>
  )
}

export default function HomePage() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const { hydrateDashboard, setActiveTab } = useStore()
  const user     = useUser()
  const stats    = useStats()
  const usage    = useUsage()
  const plan     = usePlan()
  const progress = useProgress()
  const xp       = useXp()

  useEffect(() => {
    userApi.getDashboard()
      .then(hydrateDashboard)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const chartData = [...progress].reverse().map(p => ({
    date:    format(new Date(p.progress_date), 'dd/MM'),
    words:   p.words,
    focus:   p.focus_minutes,
    points:  p.points,
  }))

  if (loading) {
    return (
      <div className="page">
        <SkeletonCard />
        <div className="grid grid-cols-2 gap-3">
          <SkeletonCard /><SkeletonCard /><SkeletonCard /><SkeletonCard />
        </div>
        <SkeletonCard />
      </div>
    )
  }

  const levelColor = LEVEL_COLORS[user?.level ?? 'A1'] ?? '#00f3ff'

  return (
    <div className="page">
      {/* ── Header ── */}
      <motion.div
        className="flex items-center justify-between"
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <div>
          <p className="text-text-muted text-xs">Salom 👋</p>
          <h1 className="text-text-primary font-bold text-xl">
            {user?.first_name ?? 'Student'}
          </h1>
        </div>
        <div className="flex items-center gap-2">
          <div
            className="xp-badge"
            style={{ borderColor: `${levelColor}60`, color: levelColor }}
          >
            {user?.level ?? 'A1'}
          </div>
          {plan.badge && <span className="text-lg">{plan.badge}</span>}
        </div>
      </motion.div>

      {/* ── XP Card ── */}
      <XpCard
        totalXp={xp.total_xp}
        currentLevel={xp.current_level}
        xpToNext={xp.xp_to_next}
        streakDays={stats.streak_days}
      />

      {/* ── Quick Actions ── */}
      <div className="grid grid-cols-2 gap-2">
        {[
          { icon: '✅', label: 'Check',     tab: 'quiz'     as const, accent: 'cyan'   as const },
          { icon: '🧠', label: 'Quiz',      tab: 'quiz'     as const, accent: 'purple' as const },
          { icon: '📈', label: 'Taraqqiyot',tab: 'progress' as const, accent: 'cyan'   as const },
          { icon: '🏆', label: 'Reyting',   tab: 'leaderboard' as const, accent: 'purple' as const },
        ].map((item, i) => (
          <motion.button
            key={item.label}
            onClick={() => setActiveTab(item.tab)}
            className="glass-card rounded-2xl p-3 flex items-center gap-2 active:scale-95 transition-transform"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: i * 0.05 + 0.2 }}
          >
            <span className="text-xl">{item.icon}</span>
            <span className="text-text-primary text-sm font-medium">{item.label}</span>
          </motion.button>
        ))}
      </div>

      {/* ── Games & Modules ── */}
      <h2 className="text-text-secondary text-xs font-semibold uppercase tracking-wider mt-5 mb-1 ml-1">
          O'yinlar va Bo'limlar
      </h2>
      <div className="grid grid-cols-3 gap-2 mb-4">
        {[
          { icon: '🔢', label: 'Raqam Top', route: '/games/number' },
          { icon: '⚡', label: 'Tez Hisob', route: '/games/math' },
          { icon: '📚', label: 'Kutubxona', route: null },
          { icon: '❌', label: 'X-O', route: '/games/xo' },
          { icon: '🃏', label: 'Xotira', route: '/games/memory' },
          { icon: '🧩', label: 'Sudoku', route: '/games/sudoku' },
        ].map((item, i) => (
          <motion.button
            key={item.label}
            onClick={() => {
              if (item.route) {
                navigate(item.route)
              } else {
                window.Telegram?.WebApp?.showAlert?.(`${item.label} bo'limiga xush kelibsiz! Tez kunda ishga tushadi.`)
              }
            }}
            className="glass-card rounded-2xl p-3 flex flex-col items-center justify-center gap-1 active:scale-95 transition-transform border border-white/5 hover:bg-white/5"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: i * 0.05 + 0.3 }}
          >
            <span className="text-2xl drop-shadow-lg">{item.icon}</span>
            <span className="text-text-primary text-xs font-medium text-center">{item.label}</span>
          </motion.button>
        ))}
      </div>

      {/* ── Daily Usage ── */}
      <GlassCard variant="dark">
        <h2 className="text-text-secondary text-xs font-semibold uppercase tracking-wider mb-3">
          Bugungi foydalanish
        </h2>
        <div className="flex flex-col gap-2.5">
          <UsageMeter used={usage.checks}      limit={plan.checks_per_day}     label="✅ Tekshiruv"  color="#00f3ff" />
          <UsageMeter used={usage.quiz}        limit={plan.quiz_per_day}       label="🧠 Quiz"       color="#bc13fe" />
          <UsageMeter used={usage.ai_messages} limit={plan.ai_messages_day}    label="💬 AI xabar"  color="#ff2d78" />
          <UsageMeter used={usage.pron_audio}  limit={plan.pron_audio_per_day} label="🔊 Talaffuz"  color="#00ff88" />
        </div>
        {!plan.name || plan.name === 'free' ? (
          <button
            onClick={() => setActiveTab('profile')}
            className="mt-3 w-full text-center text-xs text-neon-cyan hover:underline"
          >
            ⭐ Obunani yangilash →
          </button>
        ) : (
          <p className="mt-3 text-center text-2xs text-text-muted">
            {plan.display_name} • {plan.remaining_days} kun qoldi
          </p>
        )}
      </GlassCard>

      {/* ── Stats Grid ── */}
      <div className="grid grid-cols-2 gap-3">
        <StatCard icon="✅" label="Tekshiruvlar"  value={stats.checks_total}       accent="cyan"   index={0} />
        <StatCard icon="🧠" label="Quiz o'ynaldi"  value={stats.quiz_played}         accent="purple" index={1} />
        <StatCard icon="🌐" label="Tarjimalar"     value={stats.translations_total}  accent="pink"   index={2} />
        <StatCard icon="🔊" label="Talaffuz"       value={stats.pron_total}          accent="green"  index={3} />
      </div>

      {/* ── Weekly Activity Chart ── */}
      {chartData.length > 0 && (
        <GlassCard variant="dark">
          <h2 className="text-text-secondary text-xs font-semibold uppercase tracking-wider mb-3">
            Haftalik faollik
          </h2>
          <ResponsiveContainer width="100%" height={140}>
            <AreaChart data={chartData} margin={{ top: 4, right: 4, left: -24, bottom: 0 }}>
              <defs>
                <linearGradient id="gradCyan" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#00f3ff" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#00f3ff" stopOpacity={0}   />
                </linearGradient>
                <linearGradient id="gradPurple" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#bc13fe" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#bc13fe" stopOpacity={0}   />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
              <XAxis dataKey="date" tick={{ fill: '#4a5568', fontSize: 10 }} tickLine={false} axisLine={false} />
              <YAxis tick={{ fill: '#4a5568', fontSize: 10 }} tickLine={false} axisLine={false} />
              <Tooltip
                contentStyle={{
                  background: '#0d1117', border: '1px solid #1a2035',
                  borderRadius: 12, color: '#e8eaf0', fontSize: 12,
                }}
                cursor={{ stroke: 'rgba(0,243,255,0.2)' }}
              />
              <Area type="monotone" dataKey="words"  stroke="#00f3ff" strokeWidth={2} fill="url(#gradCyan)"   dot={false} name="So'zlar"  />
              <Area type="monotone" dataKey="focus"  stroke="#bc13fe" strokeWidth={2} fill="url(#gradPurple)" dot={false} name="Fokus (daqiqa)" />
            </AreaChart>
          </ResponsiveContainer>
        </GlassCard>
      )}

      {/* ── IQ Score ── */}
      {stats.iq_score > 0 && (
        <GlassCard variant="purple" hover>
          <div className="flex items-center gap-4">
            <div className="text-4xl font-bold text-gradient">{stats.iq_score}</div>
            <div>
              <div className="text-text-primary font-semibold">IQ Ball</div>
              <div className="text-text-muted text-xs">
                {stats.iq_score >= 130 ? 'Dahoning darajasi 🧠'
                  : stats.iq_score >= 110 ? 'Yuqori intellekt ⭐'
                  : stats.iq_score >= 90  ? 'O\'rtacha darajadan yuqori 📊'
                  : 'O\'rtacha daraja 📖'}
              </div>
            </div>
          </div>
        </GlassCard>
      )}
    </div>
  )
}
