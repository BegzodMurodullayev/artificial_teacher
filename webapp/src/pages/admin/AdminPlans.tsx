import { startTransition, useEffect, useState } from 'react'
import { motion } from 'framer-motion'

import { GlassCard } from '@/components/ui/GlassCard'
import { Loader } from '@/components/ui/Loader'
import { NeonButton } from '@/components/ui/NeonButton'
import { adminApi, type PlanData } from '@/lib/api'

type EditablePlan = PlanData & {
  voice_enabled: number
  inline_enabled: number
  group_enabled: number
  iq_test_enabled: number
  is_active: number
}

const NUMERIC_FIELDS: Array<{ key: keyof EditablePlan; label: string }> = [
  { key: 'price_monthly', label: 'Oy narxi' },
  { key: 'price_yearly', label: 'Yil narxi' },
  { key: 'checks_per_day', label: 'Tekshiruv / kun' },
  { key: 'quiz_per_day', label: 'Quiz / kun' },
  { key: 'lessons_per_day', label: 'Dars / kun' },
  { key: 'ai_messages_day', label: 'AI xabar / kun' },
  { key: 'pron_audio_per_day', label: 'Pronunciation / kun' },
]

const TOGGLE_FIELDS: Array<{ key: keyof EditablePlan; label: string }> = [
  { key: 'voice_enabled', label: 'Voice' },
  { key: 'inline_enabled', label: 'Inline' },
  { key: 'group_enabled', label: 'Guruh' },
  { key: 'iq_test_enabled', label: 'IQ test' },
  { key: 'is_active', label: 'Aktiv' },
]

export default function AdminPlans() {
  const [plans, setPlans] = useState<Record<string, EditablePlan>>({})
  const [loading, setLoading] = useState(true)
  const [savingPlan, setSavingPlan] = useState('')
  const [statusText, setStatusText] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    void loadPlans()
  }, [])

  async function loadPlans() {
    setLoading(true)
    setError('')
    try {
      const result = await adminApi.getPlans()
      const mapped = Object.fromEntries(result.map((plan) => [plan.name, { ...plan }]))
      startTransition(() => {
        setPlans(mapped)
        setStatusText(`Tariflar yuklandi: ${result.length} ta`)
      })
    } catch (err: any) {
      setError(err?.message || 'Tariflarni yuklashda xato yuz berdi')
    } finally {
      setLoading(false)
    }
  }

  function updateField(planName: string, field: keyof EditablePlan, value: string | number) {
    setPlans((current) => ({
      ...current,
      [planName]: {
        ...current[planName],
        [field]: value,
      },
    }))
  }

  async function savePlan(planName: string) {
    const plan = plans[planName]
    if (!plan) return

    setSavingPlan(planName)
    setError('')
    try {
      const saved = await adminApi.updatePlan(planName, plan as unknown as Record<string, unknown>)
      setPlans((current) => ({
        ...current,
        [planName]: { ...saved },
      }))
      setStatusText(`${saved.display_name || saved.name} saqlandi`)
    } catch (err: any) {
      setError(err?.message || 'Tarifni saqlab bo\'lmadi')
    } finally {
      setSavingPlan('')
    }
  }

  if (loading) {
    return <Loader size="full" text="Tariflar yuklanmoqda..." />
  }

  return (
    <div className="flex flex-col gap-6">
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-gradient font-bold text-2xl">Tariflar</h1>
        <p className="text-text-muted text-sm">
          Free, standard, pro va premium limitlarini shu yerda tahrirlang.
        </p>
      </motion.div>

      <GlassCard variant="dark" padding="lg" className="flex flex-wrap items-center gap-3">
        <span className="text-xs text-text-muted">{statusText || 'Tariflarni boshqarish paneli'}</span>
        {error && <span className="text-xs text-red-400">{error}</span>}
      </GlassCard>

      <div className="grid gap-5 xl:grid-cols-2">
        {Object.values(plans).map((plan, index) => (
          <motion.div
            key={plan.name}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.04 }}
          >
            <GlassCard variant="dark" padding="lg" className="space-y-5">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h2 className="text-lg font-semibold text-text-primary">{plan.display_name || plan.name}</h2>
                  <p className="text-xs uppercase tracking-[0.2em] text-text-muted">{plan.name}</p>
                </div>
                <NeonButton
                  variant="cyan"
                  size="sm"
                  loading={savingPlan === plan.name}
                  onClick={() => void savePlan(plan.name)}
                >
                  Saqlash
                </NeonButton>
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                <label className="space-y-1 text-sm">
                  <span className="text-text-secondary">Display name</span>
                  <input
                    value={plan.display_name || ''}
                    onChange={(event) => updateField(plan.name, 'display_name', event.target.value)}
                    className="w-full rounded-xl border border-space-border bg-space-card px-3 py-2.5 text-text-primary outline-none transition-colors focus:border-neon-cyan/60"
                  />
                </label>
                <label className="space-y-1 text-sm">
                  <span className="text-text-secondary">Badge</span>
                  <input
                    value={plan.badge || ''}
                    onChange={(event) => updateField(plan.name, 'badge', event.target.value)}
                    className="w-full rounded-xl border border-space-border bg-space-card px-3 py-2.5 text-text-primary outline-none transition-colors focus:border-neon-cyan/60"
                  />
                </label>
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                {NUMERIC_FIELDS.map((field) => (
                  <label key={`${plan.name}-${field.key}`} className="space-y-1 text-sm">
                    <span className="text-text-secondary">{field.label}</span>
                    <input
                      type="number"
                      min="0"
                      value={Number(plan[field.key] ?? 0)}
                      onChange={(event) => updateField(plan.name, field.key, Number(event.target.value || 0))}
                      className="w-full rounded-xl border border-space-border bg-space-card px-3 py-2.5 text-text-primary outline-none transition-colors focus:border-neon-cyan/60"
                    />
                  </label>
                ))}
              </div>

              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                {TOGGLE_FIELDS.map((field) => {
                  const enabled = Boolean(Number(plan[field.key] ?? 0))
                  return (
                    <button
                      key={`${plan.name}-${field.key}`}
                      type="button"
                      onClick={() => updateField(plan.name, field.key, enabled ? 0 : 1)}
                      className={`rounded-2xl border px-4 py-3 text-left transition-colors ${
                        enabled
                          ? 'border-neon-cyan/30 bg-neon-cyan/10 text-neon-cyan'
                          : 'border-space-border bg-space-card text-text-secondary'
                      }`}
                    >
                      <p className="text-sm font-semibold">{field.label}</p>
                      <p className="mt-1 text-xs">{enabled ? 'Yoqilgan' : 'Ochiq emas'}</p>
                    </button>
                  )
                })}
              </div>
            </GlassCard>
          </motion.div>
        ))}
      </div>
    </div>
  )
}
