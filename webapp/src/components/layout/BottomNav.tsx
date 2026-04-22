/**
 * BottomNav — mobile tab bar with neon active indicator.
 */

import { motion, AnimatePresence } from 'framer-motion'
import { clsx } from 'clsx'
import { useStore, useActiveTab } from '@/store/useStore'

interface Tab {
  id: 'home' | 'education' | 'games' | 'leaderboard' | 'profile'
  icon: string
  label: string
}

const TABS: Tab[] = [
  { id: 'home',        icon: '🏠', label: 'Bosh'     },
  { id: 'education',   icon: '🎓', label: 'Ta\'lim'  },
  { id: 'games',       icon: '🎮', label: 'O\'yinlar'},
  { id: 'leaderboard', icon: '🏆', label: 'Reyting'  },
  { id: 'profile',     icon: '👤', label: 'Profil'   },
]

export function BottomNav() {
  const activeTab    = useActiveTab()
  const setActiveTab = useStore(s => s.setActiveTab)

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 glass-dark border-t border-space-border pb-safe">
      <div className="flex items-center justify-around px-2 pt-2 pb-2">
        {TABS.map((tab) => {
          const isActive = activeTab === tab.id
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={clsx(
                'flex flex-col items-center gap-0.5 py-1 px-3 rounded-xl touch-target',
                'transition-all duration-200 select-none',
                isActive ? 'text-neon-cyan' : 'text-text-muted'
              )}
            >
              <span className={clsx('text-xl transition-all duration-200', isActive && 'glow-cyan')}>
                {tab.icon}
              </span>
              <span className={clsx('text-2xs font-medium transition-all duration-200', isActive && 'text-neon-cyan')}>
                {tab.label}
              </span>
              <AnimatePresence>
                {isActive && (
                  <motion.div
                    className="w-1 h-1 rounded-full bg-neon-cyan"
                    style={{ boxShadow: '0 0 6px #00f3ff' }}
                    layoutId="tab-indicator"
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    exit={{ scale: 0 }}
                    transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                  />
                )}
              </AnimatePresence>
            </button>
          )
        })}
      </div>
    </nav>
  )
}
