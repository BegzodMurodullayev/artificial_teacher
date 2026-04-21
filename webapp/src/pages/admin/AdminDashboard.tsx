/**
 * Admin Dashboard — stats overview + pending payments.
 */

import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { GlassCard } from '@/components/ui/GlassCard'
import { NeonButton } from '@/components/ui/NeonButton'
import { StatCard } from '@/components/ui/StatCard'
import { Loader } from '@/components/ui/Loader'
import api from '@/lib/api'

interface AdminStats {
  total_users:  number
  paid_users:   number
  revenue:      number
  pending:      number
  conversion:   string
}

interface Payment {
  id:           number
  user_id:      number
  plan_name:    string
  amount:       number
  duration_days:number
  status:       string
  created_at:   string
}

export default function AdminDashboard() {
  const [stats, setStats]       = useState<AdminStats | null>(null)
  const [payments, setPayments] = useState<Payment[]>([])
  const [loading, setLoading]   = useState(true)
  const [acting, setActing]     = useState<number | null>(null)

  async function loadData() {
    try {
      const [sRes, pRes] = await Promise.all([
        api.get('/admin/stats'),
        api.get('/admin/payments/pending'),
      ])
      setStats(sRes.data)
      setPayments(pRes.data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadData() }, [])

  async function handlePayment(id: number, action: 'approve' | 'reject') {
    setActing(id)
    try {
      await api.post(`/admin/payments/${id}/${action}`)
      setPayments(ps => ps.filter(p => p.id !== id))
    } catch (e) {
      console.error(e)
    } finally {
      setActing(null)
    }
  }

  if (loading) return <Loader size="full" text="Dashboard yuklanmoqda..." />

  return (
    <div className="flex flex-col gap-6">
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-gradient font-bold text-2xl">📊 Admin Dashboard</h1>
        <p className="text-text-muted text-sm">Artificial Teacher boshqaruv paneli</p>
      </motion.div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard icon="👥" label="Jami userlar"   value={stats?.total_users ?? 0}      accent="cyan"   index={0} />
        <StatCard icon="💎" label="Pulli obunalar" value={stats?.paid_users ?? 0}       accent="purple" index={1} />
        <StatCard icon="💰" label="Jami tushum"    value={`${(stats?.revenue ?? 0).toLocaleString()} so'm`} accent="green" index={2} />
        <StatCard icon="⏳" label="Kutilayotgan"   value={stats?.pending ?? 0}          accent="pink"   index={3} />
      </div>

      {/* Conversion */}
      <GlassCard variant="dark">
        <div className="flex justify-between items-center">
          <p className="text-text-muted text-sm">Konversiya darajasi</p>
          <p className="text-neon-cyan font-bold text-2xl">{stats?.conversion ?? '0%'}</p>
        </div>
        <div className="h-2 bg-space-muted rounded-full overflow-hidden mt-2">
          <motion.div
            className="h-full bg-gradient-to-r from-neon-cyan to-neon-purple rounded-full"
            initial={{ width: 0 }}
            animate={{ width: stats?.conversion ?? '0%' }}
            transition={{ duration: 1, delay: 0.3 }}
          />
        </div>
      </GlassCard>

      {/* Pending payments */}
      <GlassCard variant="dark">
        <h2 className="text-text-primary font-semibold mb-4">
          💳 Kutilayotgan to'lovlar
          {payments.length > 0 && (
            <span className="ml-2 bg-neon-pink/20 text-neon-pink text-xs px-2 py-0.5 rounded-full">
              {payments.length}
            </span>
          )}
        </h2>

        {payments.length === 0 ? (
          <p className="text-text-muted text-sm text-center py-6">
            ✅ Kutilayotgan to'lovlar yo'q
          </p>
        ) : (
          <div className="flex flex-col gap-3">
            {payments.map(p => (
              <motion.div
                key={p.id}
                className="border border-space-border rounded-2xl p-4 flex flex-col gap-3"
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
              >
                <div className="flex justify-between">
                  <div>
                    <p className="text-text-primary font-medium">
                      #{p.id} — {p.plan_name.charAt(0).toUpperCase() + p.plan_name.slice(1)}
                    </p>
                    <p className="text-text-muted text-xs">
                      User: {p.user_id} • {p.duration_days} kun
                    </p>
                  </div>
                  <p className="text-neon-green font-bold">
                    {p.amount.toLocaleString()} so'm
                  </p>
                </div>
                <div className="flex gap-2">
                  <NeonButton
                    variant="cyan" size="sm" fullWidth
                    loading={acting === p.id}
                    onClick={() => handlePayment(p.id, 'approve')}
                  >
                    ✅ Tasdiqlash
                  </NeonButton>
                  <NeonButton
                    variant="danger" size="sm" fullWidth
                    loading={acting === p.id}
                    onClick={() => handlePayment(p.id, 'reject')}
                  >
                    ❌ Rad etish
                  </NeonButton>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </GlassCard>
    </div>
  )
}
