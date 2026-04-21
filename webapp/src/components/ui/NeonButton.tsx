/**
 * NeonButton — gradient button with glow on hover.
 */

import { motion } from 'framer-motion'
import { clsx } from 'clsx'
import type { HTMLMotionProps } from 'framer-motion'

interface NeonButtonProps extends HTMLMotionProps<'button'> {
  variant?: 'cyan' | 'purple' | 'pink' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg' | 'xl'
  fullWidth?: boolean
  loading?: boolean
  icon?: React.ReactNode
  children: React.ReactNode
}

const variants = {
  cyan: clsx(
    'bg-gradient-to-r from-neon-cyan to-neon-cyan-dim text-space-black font-semibold',
    'hover:shadow-neon-cyan active:scale-95'
  ),
  purple: clsx(
    'bg-gradient-to-r from-neon-purple to-neon-purple-dim text-white font-semibold',
    'hover:shadow-neon-purple active:scale-95'
  ),
  pink: clsx(
    'bg-gradient-to-r from-neon-pink to-neon-purple text-white font-semibold',
    'hover:shadow-neon-pink active:scale-95'
  ),
  ghost: clsx(
    'bg-transparent border border-neon-cyan/40 text-neon-cyan font-medium',
    'hover:bg-neon-cyan/10 hover:border-neon-cyan/80 active:scale-95'
  ),
  danger: clsx(
    'bg-red-500/20 border border-red-500/40 text-red-400 font-medium',
    'hover:bg-red-500/30 active:scale-95'
  ),
}

const sizes = {
  sm:  'px-3 py-1.5 text-xs rounded-lg  min-h-[32px]',
  md:  'px-4 py-2.5 text-sm rounded-xl  min-h-[40px]',
  lg:  'px-6 py-3   text-sm rounded-xl  min-h-[48px]',
  xl:  'px-8 py-4   text-base rounded-2xl min-h-[56px]',
}

export function NeonButton({
  variant = 'cyan',
  size = 'md',
  fullWidth = false,
  loading = false,
  icon,
  className,
  disabled,
  children,
  ...props
}: NeonButtonProps) {
  return (
    <motion.button
      className={clsx(
        'inline-flex items-center justify-center gap-2',
        'transition-all duration-200 outline-none touch-target',
        'disabled:opacity-40 disabled:cursor-not-allowed disabled:active:scale-100',
        variants[variant],
        sizes[size],
        fullWidth && 'w-full',
        className
      )}
      whileTap={!disabled && !loading ? { scale: 0.96 } : undefined}
      whileHover={!disabled && !loading ? { scale: 1.02 } : undefined}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? (
        <svg
          className="animate-spin h-4 w-4"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      ) : icon}
      {children}
    </motion.button>
  )
}
