/**
 * ProfilePage — user profile, plan info, achievements, settings.
 */

import { motion } from 'framer-motion'
import { GlassCard } from '@/components/ui/GlassCard'
import { NeonButton } from '@/components/ui/NeonButton'
import { useUser, useStats, usePlan, useIsPaid, useQuizAccuracy } from '@/store/useStore'

const LEVELS = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
const LEVEL_DESCS: Record<string, string> = {
  A1: 'Boshlang\'ich',
  A2: 'Elementar',
  B1: 'O\'rta',
  B2: 'O\'rta-yuqori',
  C1: 'Ilg\'or',
  C2: 'Professional',
}

const ALL_FEATURES = [
  { icon: '✅', text: 'Grammatika tekshiruvi',      plans: ['free', 'standard', 'pro', 'premium'] },
  { icon: '🌐', text: 'UZ↔EN Tarjima',              plans: ['free', 'standard', 'pro', 'premium'] },
  { icon: '🔊', text: 'Talaffuz + Audio',             plans: ['free', 'standard', 'pro', 'premium'] },
  { icon: '🧠', text: 'Cheksiz Quiz',                 plans: ['pro', 'premium'] },
  { icon: '🎤', text: 'Ovozli xabarlar',              plans: ['standard', 'pro', 'premium'] },
  { icon: '⚡', text: 'Inline rejim',                 plans: ['standard', 'pro', 'premium'] },
  { icon: '🧩', text: 'IQ Test',                      plans: ['pro', 'premium'] },
  { icon: '👥', text: 'Guruh komandalari',             plans: ['premium'] },
]

function StatRow({ icon, label, value }: { icon: string; label: string; value: string | number }) {
  return (
    <div className="flex items-center justify-between py-2.5 border-b border-space-border/50 last:border-0">
      <span className="text-text-secondary text-sm flex items-center gap-2">
        <span>{icon}</span>{label}
      </span>
      <span className="text-text-primary font-semibold text-sm">{value}</span>
    </div>
  )
}

function PlanBadge({ plan }: { plan: string }) {
  const configs: Record<string, { label: string; color: string; glow: string }> = {
    free:     { label: 'Free ✨',     color: 'text-text-muted',      glow: ''                                },
    standard: { label: 'Standard ⭐', color: 'text-yellow-400',      glow: 'shadow-[0_0_12px_#ffd70066]'   },
    pro:      { label: 'Pro 💎',      color: 'text-neon-cyan',        glow: 'shadow-neon-sm-cyan'            },
    premium:  { label: 'Premium 👑',  color: 'text-neon-purple',      glow: 'shadow-neon-sm-purple'          },
  }
  const c = configs[plan] ?? configs.free
  return (
    <span className={`font-bold text-lg ${c.color} ${c.glow}`}>{c.label}</span>
  )
}

export default function ProfilePage() {
  const user    = useUser()
  const stats   = useStats()
  const plan    = usePlan()
  const isPaid  = useIsPaid()
  const accuracy = useQuizAccuracy()

  const levelIndex = LEVELS.indexOf(user?.level ?? 'A1')

  return (
    <div className="page">
      {/* ── Header ── */}
      <motion.div
        className="flex items-center gap-4 pb-2"
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div className="relative">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-neon-cyan to-neon-purple flex items-center justify-center text-2xl font-bold text-space-black shadow-neon-cyan">
            {user?.first_name?.[0]?.toUpperCase() ?? '?'}
          </div>
          <div className="absolute -bottom-1 -right-1 xp-badge text-2xs">
            {user?.level ?? 'A1'}
          </div>
        </div>
        <div>
          <h1 className="text-text-primary font-bold text-xl">{user?.first_name ?? 'Student'}</h1>
          {user?.username && (
            <p className="text-text-muted text-sm">@{user.username}</p>
          )}
          <PlanBadge plan={plan.name} />
        </div>
      </motion.div>

      {/* ── Level Progress ── */}
      <GlassCard variant="cyan">
        <p className="text-text-muted text-xs mb-3">Ingliz tili darajasi</p>
        <div className="flex justify-between mb-2">
          {LEVELS.map((lvl, i) => (
            <div key={lvl} className="flex flex-col items-center gap-1">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
                  i < levelIndex ? 'bg-neon-green/20 text-neon-green' :
                  i === levelIndex ? 'bg-neon-cyan/20 text-neon-cyan border border-neon-cyan/60 shadow-neon-sm-cyan' :
                  'bg-space-muted text-text-muted'
                }`}
              >
                {lvl}
              </div>
              {i === levelIndex && (
                <motion.div
                  className="w-1 h-1 rounded-full bg-neon-cyan"
                  animate={{ scale: [1, 1.5, 1] }}
                  transition={{ duration: 1.5, repeat: Infinity }}
                />
              )}
            </div>
          ))}
        </div>
        <div className="h-1 bg-space-muted rounded-full overflow-hidden mt-2">
          <motion.div
            className="h-full bg-gradient-to-r from-neon-green via-neon-cyan to-neon-purple"
            initial={{ width: 0 }}
            animate={{ width: `${(levelIndex / (LEVELS.length - 1)) * 100}%` }}
            transition={{ duration: 1, delay: 0.3 }}
          />
        </div>
        <p className="text-text-muted text-xs mt-2 text-center">
          {LEVEL_DESCS[user?.level ?? 'A1']} darajasi
        </p>
      </GlassCard>

      {/* ── Stats ── */}
      <GlassCard variant="dark">
        <h2 className="text-text-muted text-xs font-semibold uppercase tracking-wider mb-2">
          Statistika
        </h2>
        <StatRow icon="✅" label="Tekshiruvlar"  value={stats.checks_total.toLocaleString()} />
        <StatRow icon="🌐" label="Tarjimalar"    value={stats.translations_total.toLocaleString()} />
        <StatRow icon="🔊" label="Talaffuz"      value={stats.pron_total.toLocaleString()} />
        <StatRow icon="🧠" label="Quiz o'yinlari" value={stats.quiz_played.toLocaleString()} />
        <StatRow icon="📊" label="Quiz davomiyligi" value={`${accuracy}%`} />
        <StatRow icon="💬" label="AI xabarlar"  value={stats.messages_total.toLocaleString()} />
        <StatRow icon="🔥" label="Streak"        value={`${stats.streak_days} kun`} />
        {stats.iq_score > 0 && (
          <StatRow icon="🧩" label="IQ Ball"     value={stats.iq_score} />
        )}
      </GlassCard>

      {/* ── Plan Info ── */}
      <GlassCard variant={isPaid ? 'purple' : 'default'}>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-text-primary font-semibold">Obuna rejasi</h2>
          <PlanBadge plan={plan.name} />
        </div>

        {isPaid && plan.remaining_days > 0 && (
          <div className="flex items-center gap-2 mb-3 text-sm">
            <span className="text-neon-green">✅</span>
            <span className="text-text-secondary">{plan.remaining_days} kun qoldi</span>
          </div>
        )}

        <div className="grid grid-cols-2 gap-2 mb-4">
          {[
            { label: 'Tekshiruv/kun', value: plan.checks_per_day },
            { label: 'Quiz/kun',      value: plan.quiz_per_day    },
            { label: 'AI xabar/kun',  value: plan.ai_messages_day },
            { label: 'Talaffuz/kun',  value: plan.pron_audio_per_day },
          ].map(item => (
            <div key={item.label} className="bg-space-muted/50 rounded-xl p-2.5 text-center">
              <div className="text-neon-cyan font-bold">{item.value}</div>
              <div className="text-text-muted text-2xs">{item.label}</div>
            </div>
          ))}
        </div>

        {/* Feature list */}
        <div className="flex flex-col gap-1.5">
          {ALL_FEATURES.map(f => {
            const included = f.plans.includes(plan.name)
            return (
              <div key={f.text} className="flex items-center gap-2 text-sm">
                <span>{f.icon}</span>
                <span className={included ? 'text-text-secondary' : 'text-text-muted line-through'}>
                  {f.text}
                </span>
                <span className="ml-auto">{included ? '✅' : '🔒'}</span>
              </div>
            )
          })}
        </div>

        {!isPaid && (
          <NeonButton variant="purple" size="lg" fullWidth className="mt-4">
            ⭐ Obunani yangilash
          </NeonButton>
        )}
      </GlassCard>

      {/* ── Achievements Preview ── */}
      <GlassCard variant="dark">
        <h2 className="text-text-muted text-xs font-semibold uppercase tracking-wider mb-3">
          Yutuqlar
        </h2>
        <div className="grid grid-cols-4 gap-2">
          {[
            { icon: '👣', label: 'First Step', earned: stats.checks_total >= 1 },
            { icon: '📝', label: 'Grammar Fan', earned: stats.checks_total >= 10 },
            { icon: '🧠', label: 'Quiz Start', earned: stats.quiz_played >= 1 },
            { icon: '🔥', label: '3-Day', earned: stats.streak_days >= 3 },
            { icon: '⚡', label: '7-Day', earned: stats.streak_days >= 7 },
            { icon: '💯', label: 'Perfect', earned: false },
            { icon: '🏆', label: 'Champion', earned: false },
            { icon: '🌟', label: '30-Day', earned: stats.streak_days >= 30 },
          ].map((ach, i) => (
            <motion.div
              key={ach.label}
              className={`aspect-square rounded-xl flex flex-col items-center justify-center gap-1 ${
                ach.earned
                  ? 'bg-neon-cyan/10 border border-neon-cyan/30'
                  : 'bg-space-muted/30 border border-space-border/30'
              }`}
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: i * 0.04, type: 'spring', stiffness: 300 }}
            >
              <span className={`text-2xl ${!ach.earned && 'opacity-30 grayscale'}`}>
                {ach.icon}
              </span>
              <span className={`text-2xs text-center ${ach.earned ? 'text-neon-cyan' : 'text-text-muted'}`}>
                {ach.label}
              </span>
            </motion.div>
          ))}
        </div>
      </GlassCard>
    </div>
  )
}
