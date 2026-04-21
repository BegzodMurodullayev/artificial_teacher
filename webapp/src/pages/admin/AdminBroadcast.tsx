/**
 * AdminBroadcast — send messages to all users.
 */

import { useState } from 'react'
import { motion } from 'framer-motion'
import { GlassCard } from '@/components/ui/GlassCard'
import { NeonButton } from '@/components/ui/NeonButton'
import api from '@/lib/api'

interface BroadcastResult {
  total: number; sent: number; failed: number
}

export default function AdminBroadcast() {
  const [text, setText]     = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<BroadcastResult | null>(null)
  const [error, setError]   = useState('')

  async function handleBroadcast() {
    if (!text.trim()) return
    setLoading(true); setError(''); setResult(null)
    try {
      const res = await api.post('/admin/broadcast', { text })
      setResult(res.data)
      setText('')
    } catch {
      setError('Broadcast yuborishda xato yuz berdi')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col gap-6 max-w-2xl">
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-gradient font-bold text-2xl">📢 Broadcast</h1>
        <p className="text-text-muted text-sm">Barcha foydalanuvchilarga xabar yuborish</p>
      </motion.div>

      <GlassCard variant="dark" padding="lg">
        <label className="text-text-secondary text-sm font-medium block mb-2">
          Xabar matni (HTML qo'llab-quvvatlanadi)
        </label>
        <textarea
          value={text}
          onChange={e => setText(e.target.value)}
          placeholder="Salom! 🎉 Yangi funksiya qo'shildi..."
          className="w-full bg-space-card text-text-primary placeholder-text-muted border border-space-border rounded-xl p-3 text-sm outline-none resize-none min-h-[140px] focus:border-neon-cyan/60 transition-colors"
        />
        <p className="text-text-muted text-xs mt-1 text-right">
          {text.length} / 4096 belgi
        </p>

        {error && (
          <p className="text-neon-pink text-sm mt-2">{error}</p>
        )}

        <NeonButton
          variant="cyan" size="lg" fullWidth
          onClick={handleBroadcast}
          loading={loading}
          disabled={!text.trim()}
          className="mt-4"
        >
          📢 Yuborish
        </NeonButton>
      </GlassCard>

      {result && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
        >
          <GlassCard variant="cyan">
            <h3 className="text-text-primary font-semibold mb-3">✅ Broadcast yakunlandi!</h3>
            <div className="grid grid-cols-3 gap-3 text-center">
              <div>
                <div className="text-text-primary font-bold text-2xl">{result.total}</div>
                <div className="text-text-muted text-xs">Jami</div>
              </div>
              <div>
                <div className="text-neon-green font-bold text-2xl">{result.sent}</div>
                <div className="text-text-muted text-xs">Yuborildi</div>
              </div>
              <div>
                <div className="text-neon-pink font-bold text-2xl">{result.failed}</div>
                <div className="text-text-muted text-xs">Xato</div>
              </div>
            </div>
          </GlassCard>
        </motion.div>
      )}

      <GlassCard variant="dark">
        <h3 className="text-text-muted text-xs font-semibold uppercase tracking-wider mb-3">
          Qo'llanma
        </h3>
        <div className="flex flex-col gap-2 text-sm text-text-secondary">
          <p>• <code className="text-neon-cyan bg-space-muted px-1 rounded">&lt;b&gt;bold&lt;/b&gt;</code> — qalin matn</p>
          <p>• <code className="text-neon-cyan bg-space-muted px-1 rounded">&lt;i&gt;italic&lt;/i&gt;</code> — kursiv</p>
          <p>• <code className="text-neon-cyan bg-space-muted px-1 rounded">&lt;code&gt;kod&lt;/code&gt;</code> — kod</p>
        </div>
      </GlassCard>
    </div>
  )
}
