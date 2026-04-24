import { FormEvent, startTransition, useEffect, useState } from 'react'
import { motion } from 'framer-motion'

import { GlassCard } from '@/components/ui/GlassCard'
import { Loader } from '@/components/ui/Loader'
import { NeonButton } from '@/components/ui/NeonButton'
import { adminApi, type PaymentSettingsData, type SponsorData } from '@/lib/api'

const defaultSettings: PaymentSettingsData = {
  provider_name: '',
  card_number: '',
  card_holder: '',
  receipt_channel: '',
  manual_enabled: true,
  stars_enabled: true,
}

export default function AdminSettings() {
  const [settings, setSettings] = useState<PaymentSettingsData>(defaultSettings)
  const [sponsors, setSponsors] = useState<SponsorData[]>([])
  const [sponsorRef, setSponsorRef] = useState('')
  const [sponsorTitle, setSponsorTitle] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [sponsorBusy, setSponsorBusy] = useState<number | null>(null)
  const [statusText, setStatusText] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    void loadData()
  }, [])

  async function loadData() {
    setLoading(true)
    setError('')
    try {
      const [paymentSettings, sponsorList] = await Promise.all([
        adminApi.getPaymentSettings(),
        adminApi.getSponsors(),
      ])
      startTransition(() => {
        setSettings(paymentSettings)
        setSponsors(sponsorList)
        setStatusText('Payment va sponsor sozlamalari yuklandi')
      })
    } catch (err: any) {
      setError(err?.message || 'Sozlamalarni yuklashda xato yuz berdi')
    } finally {
      setLoading(false)
    }
  }

  function setField<Key extends keyof PaymentSettingsData>(field: Key, value: PaymentSettingsData[Key]) {
    setSettings((current) => ({ ...current, [field]: value }))
  }

  async function savePaymentSettings(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    setError('')
    try {
      const saved = await adminApi.updatePaymentSettings(settings)
      setSettings(saved)
      setStatusText('To\'lov sozlamalari saqlandi')
    } catch (err: any) {
      setError(err?.message || 'To\'lov sozlamalari saqlanmadi')
    } finally {
      setSaving(false)
    }
  }

  async function handleSponsorAction(action: () => Promise<unknown>, successText: string, busyKey = 0) {
    setSponsorBusy(busyKey)
    setError('')
    try {
      await action()
      await loadData()
      setStatusText(successText)
    } catch (err: any) {
      setError(err?.message || 'Homiy kanal amali bajarilmadi')
    } finally {
      setSponsorBusy(null)
    }
  }

  async function addSponsor(event: FormEvent) {
    event.preventDefault()
    if (!sponsorRef.trim()) return
    await handleSponsorAction(
      async () => {
        await adminApi.addSponsor(sponsorRef.trim(), sponsorTitle.trim())
        setSponsorRef('')
        setSponsorTitle('')
      },
      'Homiy kanal qoshildi',
      -1
    )
  }

  if (loading) {
    return <Loader size="full" text="Sozlamalar yuklanmoqda..." />
  }

  return (
    <div className="flex flex-col gap-6">
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-gradient font-bold text-2xl">Sozlamalar</h1>
        <p className="text-text-muted text-sm">
          To'lov tizimi, chek kanali va homiy kanallar shu bo'limda boshqariladi.
        </p>
      </motion.div>

      <GlassCard variant="dark" padding="lg" className="flex flex-wrap items-center gap-3">
        <span className="text-xs text-text-muted">{statusText || 'Sozlamalar paneli'}</span>
        {error && <span className="text-xs text-red-400">{error}</span>}
      </GlassCard>

      <div className="grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">
        <GlassCard variant="dark" padding="lg">
          <form onSubmit={savePaymentSettings} className="space-y-4">
            <div>
              <h2 className="text-lg font-semibold text-text-primary">To'lov sozlamalari</h2>
              <p className="text-xs text-text-muted">
                Manual karta, Stars va receipt channel bir xil bazada saqlanadi.
              </p>
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              <label className="space-y-1 text-sm">
                <span className="text-text-secondary">Provider</span>
                <input
                  value={settings.provider_name}
                  onChange={(event) => setField('provider_name', event.target.value)}
                  className="w-full rounded-xl border border-space-border bg-space-card px-3 py-2.5 text-text-primary outline-none transition-colors focus:border-neon-cyan/60"
                />
              </label>
              <label className="space-y-1 text-sm">
                <span className="text-text-secondary">Karta raqami</span>
                <input
                  value={settings.card_number}
                  onChange={(event) => setField('card_number', event.target.value)}
                  className="w-full rounded-xl border border-space-border bg-space-card px-3 py-2.5 text-text-primary outline-none transition-colors focus:border-neon-cyan/60"
                />
              </label>
              <label className="space-y-1 text-sm">
                <span className="text-text-secondary">Karta egasi</span>
                <input
                  value={settings.card_holder}
                  onChange={(event) => setField('card_holder', event.target.value)}
                  className="w-full rounded-xl border border-space-border bg-space-card px-3 py-2.5 text-text-primary outline-none transition-colors focus:border-neon-cyan/60"
                />
              </label>
              <label className="space-y-1 text-sm">
                <span className="text-text-secondary">Receipt channel</span>
                <input
                  value={settings.receipt_channel}
                  onChange={(event) => setField('receipt_channel', event.target.value)}
                  placeholder="@kanal yoki -100..."
                  className="w-full rounded-xl border border-space-border bg-space-card px-3 py-2.5 text-text-primary outline-none transition-colors focus:border-neon-cyan/60"
                />
              </label>
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              <button
                type="button"
                onClick={() => setField('manual_enabled', !settings.manual_enabled)}
                className={`rounded-2xl border px-4 py-3 text-left transition-colors ${
                  settings.manual_enabled
                    ? 'border-neon-cyan/30 bg-neon-cyan/10 text-neon-cyan'
                    : 'border-space-border bg-space-card text-text-secondary'
                }`}
              >
                <p className="text-sm font-semibold">Manual payment</p>
                <p className="mt-1 text-xs">{settings.manual_enabled ? 'Yoqilgan' : 'Ochiq emas'}</p>
              </button>
              <button
                type="button"
                onClick={() => setField('stars_enabled', !settings.stars_enabled)}
                className={`rounded-2xl border px-4 py-3 text-left transition-colors ${
                  settings.stars_enabled
                    ? 'border-neon-cyan/30 bg-neon-cyan/10 text-neon-cyan'
                    : 'border-space-border bg-space-card text-text-secondary'
                }`}
              >
                <p className="text-sm font-semibold">Telegram Stars</p>
                <p className="mt-1 text-xs">{settings.stars_enabled ? 'Yoqilgan' : 'Ochiq emas'}</p>
              </button>
            </div>

            <NeonButton type="submit" variant="cyan" loading={saving}>
              Sozlamalarni saqlash
            </NeonButton>
          </form>
        </GlassCard>

        <div className="space-y-5">
          <GlassCard variant="dark" padding="lg">
            <form onSubmit={addSponsor} className="space-y-3">
              <div>
                <h2 className="text-lg font-semibold text-text-primary">Homiy kanal qo'shish</h2>
                <p className="text-xs text-text-muted">
                  Bot kanalga admin qilingan bo'lishi kerak, aks holda check ishlamaydi.
                </p>
              </div>
              <input
                value={sponsorRef}
                onChange={(event) => setSponsorRef(event.target.value)}
                placeholder="@kanal yoki -100..."
                className="w-full rounded-xl border border-space-border bg-space-card px-3 py-2.5 text-text-primary outline-none transition-colors focus:border-neon-cyan/60"
              />
              <input
                value={sponsorTitle}
                onChange={(event) => setSponsorTitle(event.target.value)}
                placeholder="Ko'rinadigan sarlavha ixtiyoriy"
                className="w-full rounded-xl border border-space-border bg-space-card px-3 py-2.5 text-text-primary outline-none transition-colors focus:border-neon-cyan/60"
              />
              <NeonButton type="submit" variant="purple" loading={sponsorBusy === -1}>
                Kanal qo'shish
              </NeonButton>
            </form>
          </GlassCard>

          <GlassCard variant="dark" padding="lg" className="space-y-3">
            <div>
              <h2 className="text-lg font-semibold text-text-primary">Homiy kanallar</h2>
              <p className="text-xs text-text-muted">Join-check oqimida ishlatiladigan real ro'yxat.</p>
            </div>

            {sponsors.length === 0 ? (
              <p className="text-sm text-text-muted">Hali sponsor qo'shilmagan.</p>
            ) : (
              sponsors.map((sponsor) => (
                <div
                  key={sponsor.channel_id}
                  className="rounded-2xl border border-space-border bg-space-card p-4"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold text-text-primary">{sponsor.title || sponsor.channel_username || sponsor.channel_id}</p>
                      <p className="text-xs text-text-muted">
                        {sponsor.channel_username || sponsor.channel_id}
                      </p>
                    </div>
                    <span className={`rounded-full px-2 py-1 text-[11px] font-semibold uppercase ${
                      sponsor.is_active ? 'bg-neon-cyan/10 text-neon-cyan' : 'bg-white/5 text-white/60'
                    }`}>
                      {sponsor.is_active ? 'active' : 'inactive'}
                    </span>
                  </div>

                  <div className="mt-3 grid grid-cols-2 gap-2">
                    <NeonButton
                      variant="ghost"
                      size="sm"
                      loading={sponsorBusy === sponsor.channel_id}
                      onClick={() =>
                        void handleSponsorAction(
                          () => adminApi.toggleSponsor(sponsor.channel_id),
                          'Sponsor holati yangilandi',
                          sponsor.channel_id
                        )
                      }
                    >
                      {sponsor.is_active ? 'Pauza' : 'Yoqish'}
                    </NeonButton>
                    <NeonButton
                      variant="danger"
                      size="sm"
                      loading={sponsorBusy === sponsor.channel_id}
                      onClick={() =>
                        void handleSponsorAction(
                          () => adminApi.deleteSponsor(sponsor.channel_id),
                          'Sponsor o\'chirildi',
                          sponsor.channel_id
                        )
                      }
                    >
                      O'chirish
                    </NeonButton>
                  </div>
                </div>
              ))
            )}
          </GlassCard>
        </div>
      </div>
    </div>
  )
}
