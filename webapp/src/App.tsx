/**
 * App.tsx — Router setup with lazy pages and layouts.
 */

import { lazy, Suspense, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { MainLayout } from '@/layouts/MainLayout'
import { AdminLayout } from '@/layouts/AdminLayout'
import { Loader } from '@/components/ui/Loader'
import { useStore } from '@/store/useStore'
import { userApi } from '@/lib/api'

// Lazy admin pages
const AdminDashboard = lazy(() => import('@/pages/admin/AdminDashboard'))
const AdminBroadcast = lazy(() => import('@/pages/admin/AdminBroadcast'))

// Lazy game pages
const GamesPage = lazy(() => import('@/pages/GamesPage'))
const XOGamePage = lazy(() => import('@/pages/XOGamePage'))
const MemoryGamePage = lazy(() => import('@/pages/MemoryGamePage'))
const NumberGamePage = lazy(() => import('@/pages/NumberGamePage'))
const MathGamePage = lazy(() => import('@/pages/MathGamePage'))
const SudokuGamePage = lazy(() => import('@/pages/SudokuGamePage'))
const LibraryPage = lazy(() => import('@/pages/LibraryPage'))

function AdminPageSuspense({ children }: { children: React.ReactNode }) {
  return <Suspense fallback={<Loader size="full" text="Yuklanmoqda..." />}>{children}</Suspense>
}

function GamePageSuspense({ children }: { children: React.ReactNode }) {
  return <Suspense fallback={<Loader size="full" text="Yuklanmoqda..." />}>{children}</Suspense>
}

function AppInitializer() {
  const { hydrateDashboard, setLoading, setError } = useStore()

  useEffect(() => {
    // Initialize Telegram WebApp
    const tg = window.Telegram?.WebApp
    if (tg) {
      tg.ready()
      tg.expand()
      tg.enableClosingConfirmation()
    }

    // Load dashboard
    setLoading(true)
    userApi.getDashboard()
      .then(hydrateDashboard)
      .catch((err) => {
        console.warn('Dashboard load failed (dev mode?):', err)
        setError(null) // Silent fail in dev
        setLoading(false)
      })
  }, [])

  return null
}

export default function App() {
  return (
    <BrowserRouter>
      <AppInitializer />
      <Routes>
        {/* ── User WebApp ── */}
        <Route path="/" element={<MainLayout />} />

        {/* ── Games (Standalone inside WebApp context) ── */}
        <Route path="/games/*" element={
          <div className="flex flex-col min-h-screen bg-space-black no-overscroll">
            <div className="starfield" aria-hidden />
            <div className="bg-grid fixed inset-0 z-0 opacity-50 pointer-events-none" aria-hidden />
            <main className="relative z-10 flex-1 p-safe" style={{ paddingBottom: '90px' }}>
              <Routes>
                <Route path="" element={<GamePageSuspense><GamesPage /></GamePageSuspense>} />
                <Route path="xo" element={<GamePageSuspense><XOGamePage /></GamePageSuspense>} />
                <Route path="memory" element={<GamePageSuspense><MemoryGamePage /></GamePageSuspense>} />
                <Route path="number" element={<GamePageSuspense><NumberGamePage /></GamePageSuspense>} />
                <Route path="math" element={<GamePageSuspense><MathGamePage /></GamePageSuspense>} />
                <Route path="sudoku" element={<GamePageSuspense><SudokuGamePage /></GamePageSuspense>} />
              </Routes>
            </main>
          </div>
        } />

        {/* ── Admin Panel ── */}
        <Route path="/admin" element={<AdminLayout />}>
          <Route index element={
            <AdminPageSuspense><AdminDashboard /></AdminPageSuspense>
          } />
          <Route path="broadcast" element={
            <AdminPageSuspense><AdminBroadcast /></AdminPageSuspense>
          } />
        </Route>

        {/* ── Library ── */}
        <Route path="/library" element={<LibraryPage />} />

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
