/**
 * LeaderboardPage — global learning leaderboard with rank display.
 */

import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { GlassCard } from '@/components/ui/GlassCard'
import { Loader } from '@/components/ui/Loader'
import { leaderboardApi, type LeaderboardEntry } from '@/lib/api'
import { useUser } from '@/store/useStore'

const RANK_COLORS: Record<number, string> = {
  1: '#FFD700',
  2: '#C0C0C0',
  3: '#CD7F32',
}

const RANK_ICONS: Record<number, string> = {
  1: '🥇',
  2: '🥈',
  3: '🥉',
}

const LEVEL_COLORS: Record<string, string> = {
  A1: '#00ff88', A2: '#00f3ff', B1: '#ffe600',
  B2: '#bc13fe', C1: '#ff2d78', C2: '#ff6b00',
}

function RankBadge({ rank }: { rank: number }) {
  if (rank <= 3) {
    return (
      <span className="text-2xl">{RANK_ICONS[rank]}</span>
    )
  }
  return (
    <div className="w-8 h-8 rounded-full bg-space-muted flex items-center justify-center text-text-muted text-xs font-bold">
      {rank}
    </div>
  )
}

function LeaderboardRow({ entry, isMe, index }: {
  entry: LeaderboardEntry
  isMe: boolean
  index: number
}) {
  const levelColor = LEVEL_COLORS[entry.level] ?? '#00f3ff'
  const rankColor  = RANK_COLORS[entry.rank]

  return (
    <motion.div
      className={`flex items-center gap-3 px-4 py-3 rounded-2xl transition-all ${
        isMe
          ? 'border-glow-cyan bg-neon-cyan/5'
          : 'glass-card'
      }`}
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.04 }}
    >
      <RankBadge rank={entry.rank} />

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span
            className={`font-semibold text-sm truncate ${isMe ? 'text-neon-cyan' : 'text-text-primary'}`}
            style={rankColor ? { color: rankColor } : undefined}
          >
            {entry.first_name || entry.username || `User ${entry.user_id}`}
          </span>
          {isMe && <span className="text-2xs text-neon-cyan bg-neon-cyan/10 px-1.5 py-0.5 rounded-full">Sen</span>}
        </div>
        <div className="flex items-center gap-2 mt-0.5">
          <span
            className="text-2xs font-medium px-1.5 py-0.5 rounded-full"
            style={{ color: levelColor, backgroundColor: `${levelColor}20`, border: `1px solid ${levelColor}40` }}
          >
            {entry.level}
          </span>
          {entry.streak_days > 0 && (
            <span className="text-2xs text-text-muted">🔥 {entry.streak_days}</span>
          )}
        </div>
      </div>

      <div className="text-right shrink-0">
        <div className="text-neon-cyan text-sm font-bold">
          {entry.total_xp.toLocaleString()}
        </div>
        <div className="text-text-muted text-2xs">XP</div>
      </div>
    </motion.div>
  )
}

export default function LeaderboardPage() {
  const [data, setData]       = useState<LeaderboardEntry[]>([])
  const [myRank, setMyRank]  = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const user = useUser()

  useEffect(() => {
    Promise.all([
      leaderboardApi.getGlobal(30),
      leaderboardApi.getMyRank(),
    ])
      .then(([entries, rankData]) => {
        setData(entries)
        setMyRank(rankData.rank)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <Loader size="full" text="Reyting yuklanmoqda..." />

  return (
    <div className="page">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <h1 className="text-gradient font-bold text-2xl">🏆 Reyting</h1>
        <p className="text-text-muted text-sm mt-0.5">Global o'quvchilar reytingi</p>
      </motion.div>

      {/* My rank card */}
      {myRank && (
        <GlassCard variant="cyan">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-text-muted text-xs">Sizning o'rningiz</p>
              <p className="text-neon-cyan font-bold text-3xl">#{myRank}</p>
            </div>
            <div className="text-right">
              <p className="text-text-muted text-xs">Daraja</p>
              <p className="text-text-primary font-bold text-xl">{user?.level ?? 'A1'}</p>
            </div>
            <div className="text-4xl">🎯</div>
          </div>
        </GlassCard>
      )}

      {/* Top 3 podium */}
      {data.length >= 3 && (
        <div className="flex items-end justify-center gap-4 py-2">
          {/* 2nd place */}
          <motion.div
            className="flex flex-col items-center gap-2"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            <div className="w-16 h-16 rounded-full bg-gradient-to-br from-gray-400 to-gray-600 flex items-center justify-center text-2xl border-2 border-gray-400">
              {data[1]?.first_name?.[0] ?? '👤'}
            </div>
            <span className="text-text-secondary text-xs font-medium truncate max-w-[64px] text-center">
              {data[1]?.first_name || 'Player'}
            </span>
            <div className="w-20 h-12 bg-gray-500/20 border border-gray-500/40 rounded-t-xl flex items-center justify-center">
              <span className="text-gray-400 font-bold">🥈</span>
            </div>
          </motion.div>

          {/* 1st place */}
          <motion.div
            className="flex flex-col items-center gap-2"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <motion.div
              animate={{ y: [0, -6, 0] }}
              transition={{ duration: 2, repeat: Infinity }}
              className="w-20 h-20 rounded-full bg-gradient-to-br from-yellow-400 to-yellow-600 flex items-center justify-center text-3xl border-2 border-yellow-400"
              style={{ boxShadow: '0 0 20px rgba(255,215,0,0.5)' }}
            >
              {data[0]?.first_name?.[0] ?? '👤'}
            </motion.div>
            <span className="text-yellow-400 text-xs font-bold truncate max-w-[80px] text-center">
              {data[0]?.first_name || 'Champion'}
            </span>
            <div className="w-24 h-16 bg-yellow-500/20 border border-yellow-500/40 rounded-t-xl flex items-center justify-center">
              <span className="text-yellow-400 font-bold">🥇</span>
            </div>
          </motion.div>

          {/* 3rd place */}
          <motion.div
            className="flex flex-col items-center gap-2"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <div className="w-14 h-14 rounded-full bg-gradient-to-br from-amber-600 to-amber-800 flex items-center justify-center text-xl border-2 border-amber-600">
              {data[2]?.first_name?.[0] ?? '👤'}
            </div>
            <span className="text-amber-600 text-xs font-medium truncate max-w-[56px] text-center">
              {data[2]?.first_name || 'Player'}
            </span>
            <div className="w-16 h-8 bg-amber-600/20 border border-amber-600/40 rounded-t-xl flex items-center justify-center">
              <span className="text-amber-600 font-bold">🥉</span>
            </div>
          </motion.div>
        </div>
      )}

      {/* Full list */}
      <div className="neon-divider" />

      <div className="flex flex-col gap-2">
        {data.map((entry, i) => (
          <LeaderboardRow
            key={entry.user_id}
            entry={entry}
            isMe={entry.user_id === user?.user_id}
            index={i}
          />
        ))}
        {data.length === 0 && (
          <div className="text-center py-12 text-text-muted">
            <div className="text-4xl mb-3">📭</div>
            <p>Reyting bo'sh</p>
          </div>
        )}
      </div>
    </div>
  )
}
