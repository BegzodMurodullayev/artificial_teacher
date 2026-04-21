/**
 * Loader — space-themed animated spinner.
 */

import { motion } from 'framer-motion'
import { clsx } from 'clsx'

interface LoaderProps {
  size?: 'sm' | 'md' | 'lg' | 'full'
  text?: string
}

export function Loader({ size = 'md', text }: LoaderProps) {
  const isFullScreen = size === 'full'

  const sizeMap = { sm: 24, md: 40, lg: 64, full: 80 }
  const dim = sizeMap[isFullScreen ? 'full' : size]

  return (
    <div
      className={clsx(
        'flex flex-col items-center justify-center gap-3',
        isFullScreen && 'min-h-screen'
      )}
    >
      <div style={{ width: dim, height: dim }} className="relative">
        {/* Outer ring */}
        <motion.div
          className="absolute inset-0 rounded-full border-2 border-neon-cyan/20"
          style={{ borderTopColor: '#00f3ff' }}
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
        />
        {/* Middle ring */}
        <motion.div
          className="absolute inset-2 rounded-full border-2 border-neon-purple/20"
          style={{ borderBottomColor: '#bc13fe' }}
          animate={{ rotate: -360 }}
          transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }}
        />
        {/* Center dot */}
        <motion.div
          className="absolute inset-0 flex items-center justify-center"
          animate={{ scale: [0.8, 1.1, 0.8] }}
          transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
        >
          <div
            className="rounded-full bg-neon-cyan"
            style={{ width: dim * 0.15, height: dim * 0.15, boxShadow: '0 0 8px #00f3ff' }}
          />
        </motion.div>
      </div>

      {text && (
        <motion.p
          className="text-text-secondary text-sm"
          animate={{ opacity: [0.5, 1, 0.5] }}
          transition={{ duration: 1.5, repeat: Infinity }}
        >
          {text}
        </motion.p>
      )}
    </div>
  )
}

/** Inline shimmer skeleton for content loading */
export function SkeletonLine({ width = 'w-full', height = 'h-4' }: { width?: string; height?: string }) {
  return (
    <div className={clsx('rounded-lg bg-space-muted shimmer', width, height)} />
  )
}

export function SkeletonCard() {
  return (
    <div className="glass-card rounded-2xl p-4 flex flex-col gap-3">
      <SkeletonLine width="w-1/3" height="h-3" />
      <SkeletonLine width="w-full" height="h-6" />
      <SkeletonLine width="w-2/3" height="h-3" />
    </div>
  )
}
