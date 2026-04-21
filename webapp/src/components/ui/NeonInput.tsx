/**
 * NeonInput — text input with neon glow on focus.
 */

import { clsx } from 'clsx'
import type { InputHTMLAttributes } from 'react'

interface NeonInputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  hint?: string
  error?: string
  icon?: React.ReactNode
  accent?: 'cyan' | 'purple'
}

export function NeonInput({
  label,
  hint,
  error,
  icon,
  accent = 'cyan',
  className,
  ...props
}: NeonInputProps) {
  const focusRing = accent === 'cyan'
    ? 'focus:border-neon-cyan/70 focus:shadow-[0_0_12px_rgba(0,243,255,0.25)]'
    : 'focus:border-neon-purple/70 focus:shadow-[0_0_12px_rgba(188,19,254,0.25)]'

  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label className="text-text-secondary text-sm font-medium px-1">
          {label}
        </label>
      )}
      <div className="relative">
        {icon && (
          <div className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted">
            {icon}
          </div>
        )}
        <input
          className={clsx(
            'w-full bg-space-card text-text-primary placeholder-text-muted',
            'border border-space-border rounded-xl outline-none',
            'transition-all duration-200',
            'min-h-[44px] px-4 py-3 text-sm',
            icon && 'pl-10',
            focusRing,
            error && '!border-red-500/60',
            className
          )}
          {...props}
        />
      </div>
      {error && (
        <p className="text-red-400 text-xs px-1">{error}</p>
      )}
      {hint && !error && (
        <p className="text-text-muted text-xs px-1">{hint}</p>
      )}
    </div>
  )
}
