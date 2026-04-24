import { FormEvent, startTransition, useEffect, useState } from 'react'
import { motion } from 'framer-motion'

import { GlassCard } from '@/components/ui/GlassCard'
import { Loader } from '@/components/ui/Loader'
import { NeonButton } from '@/components/ui/NeonButton'
import { adminApi, type AdminUserData } from '@/lib/api'

const QUICK_PLANS = [
  { name: 'free', days: 0, label: 'Free' },
  { name: 'standard', days: 30, label: 'Standard' },
  { name: 'pro', days: 30, label: 'Pro' },
  { name: 'premium', days: 30, label: 'Premium' },
] as const

function planBadge(planName: string) {
  const clean = String(planName || 'free').toLowerCase()
  if (clean === 'premium') return 'bg-amber-500/20 text-amber-300 border-amber-500/30'
  if (clean === 'pro') return 'bg-fuchsia-500/20 text-fuchsia-300 border-fuchsia-500/30'
  if (clean === 'standard') return 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
  return 'bg-white/5 text-white/70 border-white/10'
}

export default function AdminUsers() {
  const [users, setUsers] = useState<AdminUserData[]>([])
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [searching, setSearching] = useState(false)
  const [actingUserId, setActingUserId] = useState<number | null>(null)
  const [statusText, setStatusText] = useState('')
  const [error, setError] = useState('')

  async function loadUsers(searchValue = '') {
    if (loading) {
      setLoading(true)
    } else {
      setSearching(true)
    }
    setError('')

    try {
      const result = await adminApi.getUsers(searchValue, 30)
      startTransition(() => {
        setUsers(result)
        setStatusText(
          searchValue.trim()
            ? `Qidiruv yakuni: ${result.length} ta foydalanuvchi`
            : `Oxirgi foydalanuvchilar: ${result.length} ta`
        )
      })
    } catch (err: any) {
      setError(err?.message || 'Foydalanuvchilarni yuklashda xato yuz berdi')
    } finally {
      setLoading(false)
      setSearching(false)
    }
  }

  useEffect(() => {
    void loadUsers()
  }, [])

  async function handleSearch(event: FormEvent) {
    event.preventDefault()
    await loadUsers(query)
  }

  async function mutateUser(userId: number, action: () => Promise<unknown>, successText: string) {
    setActingUserId(userId)
    setError('')
    try {
      await action()
      setStatusText(successText)
      await loadUsers(query)
    } catch (err: any) {
      setError(err?.message || 'Amal bajarilmadi')
    } finally {
      setActingUserId(null)
    }
  }

  if (loading) {
    return <Loader size="full" text="Foydalanuvchilar yuklanmoqda..." />
  }

  return (
    <div className="flex flex-col gap-6">
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-gradient font-bold text-2xl">Foydalanuvchilar</h1>
        <p className="text-text-muted text-sm">
          User qidirish, rol almashtirish, ban va obuna berish shu yerda.
        </p>
      </motion.div>

      <GlassCard variant="dark" padding="lg">
        <form onSubmit={handleSearch} className="grid gap-3 md:grid-cols-[1fr_auto]">
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="ID yoki @username kiriting"
            className="w-full rounded-xl border border-space-border bg-space-card px-4 py-3 text-sm text-text-primary outline-none transition-colors focus:border-neon-cyan/60"
          />
          <NeonButton type="submit" variant="cyan" loading={searching}>
            Qidirish
          </NeonButton>
        </form>
        <div className="mt-3 flex flex-wrap items-center gap-3 text-xs">
          <span className="text-text-muted">{statusText || 'Admin panel tayyor'}</span>
          {error && <span className="text-red-400">{error}</span>}
        </div>
      </GlassCard>

      <div className="grid gap-4">
        {users.length === 0 ? (
          <GlassCard variant="dark" padding="lg">
            <p className="text-sm text-text-muted">Mos foydalanuvchi topilmadi.</p>
          </GlassCard>
        ) : (
          users.map((user, index) => {
            const activeAction = actingUserId === user.user_id
            const isAdmin = ['admin', 'owner'].includes(user.role)
            const isOwner = user.role === 'owner'
            const username = user.username ? `@${user.username}` : 'username yoq'

            return (
              <motion.div
                key={user.user_id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.03 }}
              >
                <GlassCard variant="dark" padding="lg" className="space-y-4">
                  <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                    <div className="space-y-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="text-lg font-semibold text-text-primary">
                          {user.first_name || 'No name'}
                        </p>
                        <span className={`rounded-full border px-2 py-1 text-[11px] font-semibold uppercase ${planBadge(user.plan_name)}`}>
                          {user.plan_name || 'free'}
                        </span>
                        <span className={`rounded-full border px-2 py-1 text-[11px] font-semibold uppercase ${user.is_banned ? 'border-red-500/30 bg-red-500/15 text-red-300' : 'border-neon-cyan/20 bg-neon-cyan/10 text-neon-cyan'}`}>
                          {user.is_banned ? 'banned' : 'active'}
                        </span>
                      </div>
                      <p className="text-sm text-text-secondary">{username}</p>
                      <p className="text-xs text-text-muted">
                        ID: <span className="text-text-primary">{user.user_id}</span> • Rol: <span className="text-text-primary">{user.role}</span> • Level: <span className="text-text-primary">{user.level || 'A1'}</span>
                      </p>
                      <p className="text-xs text-text-muted">
                        Qolgan obuna: <span className="text-text-primary">{user.remaining_days || 0} kun</span>
                      </p>
                    </div>

                    <div className="grid grid-cols-2 gap-2 md:w-[250px]">
                      <NeonButton
                        variant={user.is_banned ? 'cyan' : 'danger'}
                        size="sm"
                        loading={activeAction}
                        onClick={() =>
                          mutateUser(
                            user.user_id,
                            () => adminApi.setUserBan(user.user_id, !Boolean(user.is_banned)),
                            user.is_banned ? 'User bandan olindi' : 'User ban qilindi'
                          )
                        }
                      >
                        {user.is_banned ? 'Unban' : 'Ban'}
                      </NeonButton>
                      <NeonButton
                        variant="ghost"
                        size="sm"
                        disabled={isOwner}
                        loading={activeAction}
                        onClick={() =>
                          mutateUser(
                            user.user_id,
                            () => adminApi.setUserRole(user.user_id, isAdmin ? 'user' : 'admin'),
                            isAdmin ? 'Rol userga ozgartirildi' : 'Rol adminga ozgartirildi'
                          )
                        }
                      >
                        {isAdmin ? 'User qil' : 'Admin qil'}
                      </NeonButton>
                    </div>
                  </div>

                  <div className="grid gap-2 md:grid-cols-4">
                    {QUICK_PLANS.map((plan) => (
                      <NeonButton
                        key={`${user.user_id}-${plan.name}`}
                        variant={plan.name === 'premium' ? 'pink' : plan.name === 'pro' ? 'purple' : 'ghost'}
                        size="sm"
                        loading={activeAction}
                        onClick={() =>
                          mutateUser(
                            user.user_id,
                            () => adminApi.grantSubscription(user.user_id, plan.name, plan.days),
                            `${user.user_id} uchun ${plan.label} obunasi berildi`
                          )
                        }
                      >
                        {plan.label}
                      </NeonButton>
                    ))}
                  </div>
                </GlassCard>
              </motion.div>
            )
          })
        )}
      </div>
    </div>
  )
}
