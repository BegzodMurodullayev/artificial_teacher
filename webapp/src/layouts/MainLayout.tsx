/**
 * MainLayout — persistent shell for the user webapp.
 * Contains the starfield background, bottom nav, and page outlet.
 */

import { motion, AnimatePresence } from 'framer-motion'
import { BottomNav } from '@/components/layout/BottomNav'
import { useActiveTab } from '@/store/useStore'

// Lazy page imports
import { lazy, Suspense } from 'react'
import { Loader } from '@/components/ui/Loader'

const HomePage        = lazy(() => import('@/pages/HomePage'))
const ProgressPage    = lazy(() => import('@/pages/ProgressPage'))
const QuizPage        = lazy(() => import('@/pages/QuizPage'))
const LeaderboardPage = lazy(() => import('@/pages/LeaderboardPage'))
const ProfilePage     = lazy(() => import('@/pages/ProfilePage'))

const pageVariants = {
  initial:  { opacity: 0, y: 12 },
  animate:  { opacity: 1, y: 0  },
  exit:     { opacity: 0, y: -6 },
}

function PageSuspense({ children }: { children: React.ReactNode }) {
  return <Suspense fallback={<Loader size="full" text="Yuklanmoqda..." />}>{children}</Suspense>
}

export function MainLayout() {
  const activeTab = useActiveTab()

  const pages: Record<string, React.ReactNode> = {
    home:        <PageSuspense><HomePage /></PageSuspense>,
    progress:    <PageSuspense><ProgressPage /></PageSuspense>,
    quiz:        <PageSuspense><QuizPage /></PageSuspense>,
    leaderboard: <PageSuspense><LeaderboardPage /></PageSuspense>,
    profile:     <PageSuspense><ProfilePage /></PageSuspense>,
  }

  return (
    <div className="flex flex-col min-h-screen bg-space-black no-overscroll">
      {/* Star-field ambient background */}
      <div className="starfield" aria-hidden />
      <div className="bg-grid fixed inset-0 z-0 opacity-50 pointer-events-none" aria-hidden />

      {/* Page content */}
      <main className="relative z-10 flex-1">
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            variants={pageVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
          >
            {pages[activeTab]}
          </motion.div>
        </AnimatePresence>
      </main>

      {/* Bottom navigation */}
      <BottomNav />
    </div>
  )
}
