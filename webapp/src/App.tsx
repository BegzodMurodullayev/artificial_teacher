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

function AdminPageSuspense({ children }: { children: React.ReactNode }) {
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

        {/* ── Admin Panel ── */}
        <Route path="/admin" element={<AdminLayout />}>
          <Route index element={
            <AdminPageSuspense><AdminDashboard /></AdminPageSuspense>
          } />
          <Route path="broadcast" element={
            <AdminPageSuspense><AdminBroadcast /></AdminPageSuspense>
          } />
        </Route>

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
