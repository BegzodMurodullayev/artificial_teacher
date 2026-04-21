/**
 * GlassCard — glassmorphism container with optional neon border glow.
 */

import { motion } from 'framer-motion'
import { clsx } from 'clsx'
import type { HTMLMotionProps } from 'framer-motion'

interface GlassCardProps extends HTMLMotionProps<'div'> {
  variant?: 'default' | 'cyan' | 'purple' | 'dark'
  padding?: 'none' | 'sm' | 'md' | 'lg'
  hover?: boolean
  children: React.ReactNode
}

const variants = {
  default: 'glass-card border border-space-border',
  cyan:    'glass-card border-glow-cyan',
  purple:  'glass-card border-glow-purple',
  dark:    'glass-dark border border-space-border/50',
}

const paddings = {
  none: '',
  sm:   'p-3',
  md:   'p-4',
  lg:   'p-6',
}

export function GlassCard({
  variant = 'default',
  padding = 'md',
  hover = false,
  className,
  children,
  ...props
}: GlassCardProps) {
  return (
    <motion.div
      className={clsx(
        'rounded-2xl',
        variants[variant],
        paddings[padding],
        hover && 'cursor-pointer',
        className
      )}
      whileHover={hover ? { scale: 1.01, y: -2 } : undefined}
      transition={{ type: 'spring', stiffness: 400, damping: 25 }}
      {...props}
    >
      {children}
    </motion.div>
  )
}
