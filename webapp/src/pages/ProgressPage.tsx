/**
 * ProgressPage — Weekly progress tracker + Pomodoro focus timer.
 */

import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line,
} from 'recharts'
import { GlassCard } from '@/components/ui/GlassCard'
import { NeonButton } from '@/components/ui/NeonButton'
import { progressApi } from '@/lib/api'
import { format } from 'date-fns'
import type { ProgressData } from '@/lib/api'

// ══════════════════════════════════════════════
// POMODORO TIMER
// ══════════════════════════════════════════════

type PomMode = 'focus' | 'short' | 'long'
const DURATIONS: Record<PomMode, number> = { focus: 25 * 60, short: 5 * 60, long: 15 * 60 }
const MODE_LABELS: Record<PomMode, string> = { focus: '🎯 Fokus', short: '☕ Qisqa tanaffus', long: '🛋 Uzun tanaffus' }

function PomodoroTimer() {
  const [mode, setMode]     = useState<PomMode>('focus')
  const [time, setTime]     = useState(DURATIONS.focus)
  const [running, setRunning] = useState(false)
  const [sessions, setSessions] = useState(0)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    setTime(DURATIONS[mode])
    setRunning(false)
  }, [mode])

  useEffect(() => {
    if (running) {
      intervalRef.current = setInterval(() => {
        setTime(t => {
          if (t <= 1) {
            clearInterval(intervalRef.current!)
            setRunning(false)
            if (mode === 'focus') {
              setSessions(s => s + 1)
              // Sync focus time to backend
              progressApi.sync({ focus_minutes: 25 }).catch(() => {})
              window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success')
            }
            return 0
          }
          return t - 1
        })
      }, 1000)
    } else {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
    return () => { if (intervalRef.current) clearInterval(intervalRef.current) }
  }, [running, mode])

  const total  = DURATIONS[mode]
  const pct    = ((total - time) / total) * 100
  const mins   = Math.floor(time / 60).toString().padStart(2, '0')
  const secs   = (time % 60).toString().padStart(2, '0')
  const radius = 80
  const circ   = 2 * Math.PI * radius
  const offset = circ * (1 - pct / 100)

  return (
    <GlassCard variant="cyan" padding="lg">
      <h2 className="text-text-primary font-bold text-center mb-4">⏱ Pomodoro Timer</h2>

      {/* Mode selector */}
      <div className="flex gap-2 mb-6">
        {(Object.keys(DURATIONS) as PomMode[]).map(m => (
          <button
            key={m}
            onClick={() => setMode(m)}
            className={`flex-1 py-1.5 rounded-xl text-xs font-medium transition-all ${
              mode === m
                ? 'bg-neon-cyan/20 text-neon-cyan border border-neon-cyan/40'
                : 'text-text-muted hover:text-text-secondary'
            }`}
          >
            {m === 'focus' ? 'Fokus' : m === 'short' ? 'Qisqa' : 'Uzun'}
          </button>
        ))}
      </div>

      {/* Circle timer */}
      <div className="flex justify-center mb-6">
        <div className="relative" style={{ width: 200, height: 200 }}>
          <svg className="absolute inset-0 -rotate-90" width="200" height="200">
            <circle cx="100" cy="100" r={radius} fill="none" stroke="rgba(0,243,255,0.1)" strokeWidth="8" />
            <motion.circle
              cx="100" cy="100" r={radius}
              fill="none"
              stroke={mode === 'focus' ? '#00f3ff' : '#bc13fe'}
              strokeWidth="8"
              strokeLinecap="round"
              strokeDasharray={circ}
              animate={{ strokeDashoffset: offset }}
              transition={{ duration: 0.5 }}
              style={{
                filter: `drop-shadow(0 0 8px ${mode === 'focus' ? '#00f3ff' : '#bc13fe'})`
              }}
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-4xl font-mono font-bold text-text-primary">{mins}:{secs}</span>
            <span className="text-text-muted text-xs mt-1">{MODE_LABELS[mode]}</span>
          </div>
        </div>
      </div>

      {/* Controls */}
      <div className="flex gap-3">
        <NeonButton
          variant={running ? 'danger' : 'cyan'}
          size="lg"
          fullWidth
          onClick={() => setRunning(v => !v)}
        >
          {running ? '⏸ Pauza' : '▶ Boshlash'}
        </NeonButton>
        <NeonButton
          variant="ghost"
          size="lg"
          onClick={() => { setRunning(false); setTime(DURATIONS[mode]) }}
        >
          ↺
        </NeonButton>
      </div>

      {sessions > 0 && (
        <p className="text-center text-neon-green text-xs mt-3">
          🍅 Bugun {sessions} ta pomodoro yakunlandi!
        </p>
      )}
    </GlassCard>
  )
}

// ══════════════════════════════════════════════
// PROGRESS PAGE
// ══════════════════════════════════════════════

export default function ProgressPage() {
  const [progress, setProgress] = useState<ProgressData[]>([])
  const [loading, setLoading]   = useState(true)
  const [tab, setTab]           = useState<'chart' | 'timer'>('chart')

  useEffect(() => {
    progressApi.getWeek()
      .then(data => setProgress([...data].reverse()))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const chartData = progress.map(p => ({
    date:  format(new Date(p.progress_date), 'dd/MM'),
    words: p.words,
    quiz:  p.quiz,
    focus: p.focus_minutes,
  }))

  const totalWords  = progress.reduce((s, p) => s + p.words, 0)
  const totalFocus  = progress.reduce((s, p) => s + p.focus_minutes, 0)
  const totalPoints = progress.reduce((s, p) => s + p.points, 0)

  return (
    <div className="page">
      <motion.h1
        className="text-gradient font-bold text-2xl"
        initial={{ opacity: 0, x: -16 }}
        animate={{ opacity: 1, x: 0 }}
      >
        📈 Taraqqiyot
      </motion.h1>

      {/* Tab switcher */}
      <div className="flex gap-2">
        {[
          { id: 'chart', label: '📊 Statistika' },
          { id: 'timer', label: '⏱ Pomodoro' },
        ].map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id as typeof tab)}
            className={`flex-1 py-2.5 rounded-xl text-sm font-medium transition-all ${
              tab === t.id
                ? 'bg-neon-cyan/15 text-neon-cyan border border-neon-cyan/30'
                : 'glass-card text-text-secondary'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        {tab === 'chart' ? (
          <motion.div
            key="chart"
            className="flex flex-col gap-4"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.2 }}
          >
            {/* Summary */}
            <div className="grid grid-cols-3 gap-3">
              <div className="glass-card rounded-2xl p-3 text-center">
                <div className="text-neon-cyan font-bold text-lg">{totalWords}</div>
                <div className="text-text-muted text-2xs">So'zlar</div>
              </div>
              <div className="glass-card rounded-2xl p-3 text-center">
                <div className="text-neon-purple font-bold text-lg">{totalFocus}</div>
                <div className="text-text-muted text-2xs">Daqiqa</div>
              </div>
              <div className="glass-card rounded-2xl p-3 text-center">
                <div className="text-neon-green font-bold text-lg">{totalPoints}</div>
                <div className="text-text-muted text-2xs">Ball</div>
              </div>
            </div>

            {/* Bar chart */}
            {!loading && chartData.length > 0 ? (
              <GlassCard variant="dark">
                <h3 className="text-text-secondary text-xs font-semibold uppercase tracking-wider mb-3">
                  Haftalik so'zlar
                </h3>
                <ResponsiveContainer width="100%" height={160}>
                  <BarChart data={chartData} margin={{ top: 4, right: 4, left: -24, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                    <XAxis dataKey="date" tick={{ fill: '#4a5568', fontSize: 10 }} tickLine={false} axisLine={false} />
                    <YAxis tick={{ fill: '#4a5568', fontSize: 10 }} tickLine={false} axisLine={false} />
                    <Tooltip
                      contentStyle={{
                        background: '#0d1117', border: '1px solid #1a2035',
                        borderRadius: 12, color: '#e8eaf0', fontSize: 12,
                      }}
                    />
                    <Bar dataKey="words" fill="#00f3ff" radius={[4, 4, 0, 0]}
                         style={{ filter: 'drop-shadow(0 0 4px #00f3ff88)' }} />
                  </BarChart>
                </ResponsiveContainer>
              </GlassCard>
            ) : (
              <div className="glass-card rounded-2xl p-8 text-center text-text-muted">
                {loading ? '⏳ Yuklanmoqda...' : '📭 Ma\'lumot yo\'q'}
              </div>
            )}

            {/* Focus chart */}
            {!loading && chartData.length > 0 && (
              <GlassCard variant="dark">
                <h3 className="text-text-secondary text-xs font-semibold uppercase tracking-wider mb-3">
                  Fokus vaqti (daqiqa)
                </h3>
                <ResponsiveContainer width="100%" height={140}>
                  <LineChart data={chartData} margin={{ top: 4, right: 4, left: -24, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                    <XAxis dataKey="date" tick={{ fill: '#4a5568', fontSize: 10 }} tickLine={false} axisLine={false} />
                    <YAxis tick={{ fill: '#4a5568', fontSize: 10 }} tickLine={false} axisLine={false} />
                    <Tooltip
                      contentStyle={{
                        background: '#0d1117', border: '1px solid #1a2035',
                        borderRadius: 12, color: '#e8eaf0', fontSize: 12,
                      }}
                    />
                    <Line
                      type="monotone" dataKey="focus" stroke="#bc13fe" strokeWidth={2.5}
                      dot={{ fill: '#bc13fe', r: 3 }} activeDot={{ r: 5 }}
                      style={{ filter: 'drop-shadow(0 0 4px #bc13fe88)' }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </GlassCard>
            )}
          </motion.div>
        ) : (
          <motion.div
            key="timer"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.2 }}
          >
            <PomodoroTimer />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
