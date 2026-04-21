/**
 * StatCard — metric display with icon, value, label, and optional trend.
 */

import { motion } from 'framer-motion'
import { clsx } from 'clsx'

interface StatCardProps {
  icon:     React.ReactNode
  label:    string
  value:    string | number
  sub?:     string
  trend?:   number          // positive = up, negative = down
  accent?:  'cyan' | 'purple' | 'pink' | 'green'
  index?:   number          // for stagger animation
  onClick?: () => void
}

const accents = {
  cyan:   { text: 'text-neon-cyan',   bg: 'bg-neon-cyan/10',   glow: 'shadow-neon-sm-cyan' },
  purple: { text: 'text-neon-purple', bg: 'bg-neon-purple/10', glow: 'shadow-neon-sm-purple' },
  pink:   { text: 'text-neon-pink',   bg: 'bg-neon-pink/10',   glow: '' },
  green:  { text: 'text-neon-green',  bg: 'bg-neon-green/10',  glow: '' },
}

export function StatCard({
  icon,
  label,
  value,
  sub,
  trend,
  accent = 'cyan',
  index = 0,
  onClick,
}: StatCardProps) {
  const a = accents[accent]

  return (
    <motion.div
      className={clsx(
        'glass-card rounded-2xl p-4 flex flex-col gap-2',
        onClick && 'cursor-pointer active:scale-95'
      )}
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.06, type: 'spring', stiffness: 300, damping: 24 }}
      whileHover={onClick ? { scale: 1.02, y: -2 } : undefined}
      onClick={onClick}
    >
      {/* Icon */}
      <div className={clsx('w-9 h-9 rounded-xl flex items-center justify-center', a.bg, a.glow)}>
        <span className={clsx('text-lg', a.text)}>{icon}</span>
      </div>

      {/* Value */}
      <div>
        <div className={clsx('text-xl font-bold', a.text)}>
          {typeof value === 'number' ? value.toLocaleString() : value}
        </div>
        <div className="text-text-secondary text-xs mt-0.5">{label}</div>
      </div>

      {/* Sub & Trend */}
      {(sub !== undefined || trend !== undefined) && (
        <div className="flex items-center gap-1.5 mt-auto">
          {trend !== undefined && trend !== 0 && (
            <span className={clsx(
              'text-xs font-semibold',
              trend > 0 ? 'text-neon-green' : 'text-neon-pink'
            )}>
              {trend > 0 ? '↑' : '↓'} {Math.abs(trend)}%
            </span>
          )}
          {sub && <span className="text-text-muted text-xs">{sub}</span>}
        </div>
      )}
    </motion.div>
  )
}

/** XP Progress bar card */
interface XpCardProps {
  totalXp:       number
  currentLevel:  number
  xpToNext:      number
  streakDays:    number
}

export function XpCard({ totalXp, currentLevel, xpToNext, streakDays }: XpCardProps) {
  const xpForThisLevel = Math.pow(currentLevel - 1, 2) * 50
  const xpForNextLevel = Math.pow(currentLevel, 2) * 50
  const progress = xpForNextLevel > xpForThisLevel
    ? ((totalXp - xpForThisLevel) / (xpForNextLevel - xpForThisLevel)) * 100
    : 100

  return (
    <motion.div
      className="glass-card border-glow-cyan rounded-2xl p-4 flex flex-col gap-3"
      initial={{ opacity: 0, scale: 0.96 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ type: 'spring', stiffness: 300, damping: 24 }}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="xp-badge">Lv.{currentLevel}</div>
          {streakDays > 0 && (
            <div className="xp-badge" style={{ borderColor: 'rgba(255,165,0,0.4)', color: '#ffa500' }}>
              🔥 {streakDays}
            </div>
          )}
        </div>
        <span className="text-text-muted text-xs">{totalXp.toLocaleString()} XP</span>
      </div>

      <div>
        <div className="progress-neon h-2">
          <motion.div
            className="progress-neon-fill"
            initial={{ width: 0 }}
            animate={{ width: `${Math.min(100, progress)}%` }}
            transition={{ duration: 1, delay: 0.3, ease: [0.16, 1, 0.3, 1] }}
          />
        </div>
        <div className="flex justify-between mt-1">
          <span className="text-text-muted text-2xs">Level {currentLevel}</span>
          <span className="text-neon-cyan text-2xs">{xpToNext} XP to next</span>
        </div>
      </div>
    </motion.div>
  )
}
