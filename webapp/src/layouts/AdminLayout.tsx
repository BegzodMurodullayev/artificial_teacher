/**
 * AdminLayout - sidebar + header shell for admin panel.
 */

import { useState } from 'react'
import { Link, Navigate, Outlet, useLocation } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { clsx } from 'clsx'

import { useIsAdmin } from '@/store/useStore'

const NAV_ITEMS = [
  { path: '/admin', icon: '📊', label: 'Dashboard' },
  { path: '/admin/users', icon: '👥', label: 'Foydalanuvchilar' },
  { path: '/admin/plans', icon: '⭐', label: 'Rejalar' },
  { path: '/admin/settings', icon: '⚙️', label: 'Sozlamalar' },
  { path: '/admin/broadcast', icon: '📢', label: 'Broadcast' },
]

export function AdminLayout() {
  const isAdmin = useIsAdmin()
  const location = useLocation()
  const [open, setOpen] = useState(false)

  if (!isAdmin) return <Navigate to="/" replace />

  return (
    <div className="flex min-h-screen bg-space-black">
      <aside className="hidden md:flex w-56 flex-col glass-dark border-r border-space-border p-4 gap-2">
        <div className="text-gradient font-bold text-lg mb-4 px-2">🎓 Admin</div>
        {NAV_ITEMS.map((item) => (
          <Link
            key={item.path}
            to={item.path}
            className={clsx(
              'flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-all duration-150',
              location.pathname === item.path
                ? 'bg-neon-cyan/15 text-neon-cyan border border-neon-cyan/30'
                : 'text-text-secondary hover:bg-space-muted hover:text-text-primary'
            )}
          >
            <span>{item.icon}</span>
            {item.label}
          </Link>
        ))}
      </aside>

      <div className="flex-1 flex flex-col">
        <header className="md:hidden flex items-center justify-between px-4 py-3 glass-dark border-b border-space-border">
          <span className="text-gradient font-bold">🎓 Admin</span>
          <button onClick={() => setOpen((v) => !v)} className="text-text-secondary p-2">
            ☰
          </button>
        </header>

        <AnimatePresence>
          {open && (
            <motion.div
              className="md:hidden fixed inset-0 z-50 flex"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <div className="absolute inset-0 bg-black/60" onClick={() => setOpen(false)} />
              <motion.nav
                className="relative w-56 glass-dark border-r border-space-border p-4 flex flex-col gap-2"
                initial={{ x: -56 }}
                animate={{ x: 0 }}
                exit={{ x: -56 }}
                transition={{ type: 'spring', stiffness: 400, damping: 30 }}
              >
                <div className="text-gradient font-bold text-lg mb-4">🎓 Admin</div>
                {NAV_ITEMS.map((item) => (
                  <Link
                    key={item.path}
                    to={item.path}
                    onClick={() => setOpen(false)}
                    className={clsx(
                      'flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-all',
                      location.pathname === item.path
                        ? 'bg-neon-cyan/15 text-neon-cyan border border-neon-cyan/30'
                        : 'text-text-secondary hover:bg-space-muted'
                    )}
                  >
                    <span>{item.icon}</span>
                    {item.label}
                  </Link>
                ))}
              </motion.nav>
            </motion.div>
          )}
        </AnimatePresence>

        <main className="flex-1 p-4 md:p-6 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
