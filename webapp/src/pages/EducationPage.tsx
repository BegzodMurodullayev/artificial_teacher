/**
 * EducationPage — Hub for all educational materials
 */
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'

const EDU_MODULES = [
  {
    id: 'library',
    emoji: '📚',
    title: "Kutubxona",
    desc: "Ingliz tili kitoblari va qoidalar",
    color: '#3b82f6',
    route: '/library?tab=book',
  },
  {
    id: 'evrika',
    emoji: '💡',
    title: "Evrika",
    desc: "Qiziqarli faktlar va ma'lumotlar",
    color: '#fbbf24',
    route: '/library?tab=fact',
  },
  {
    id: 'zakovat',
    emoji: '🧠',
    title: "Zakovat",
    desc: "Qiyin va mantiqiy savollar",
    color: '#a855f7',
    route: '/library?tab=quiz',
  },
  {
    id: 'iqtest',
    emoji: '🎯',
    title: "IQ Test",
    desc: "Mantiqiy fikrlashni sinash",
    color: '#f43f5e',
    route: '/iqtest',
  },
  {
    id: 'pomodoro',
    emoji: '⏱',
    title: "Pomodoro",
    desc: "Vaqtni boshqarish usuli",
    color: '#10b981',
    route: '/pomodoro',
  },
]

export default function EducationPage() {
  const navigate = useNavigate()

  return (
    <div className="page pb-24">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="mb-6"
      >
        <p className="text-text-muted text-xs">Asosiy</p>
        <h1 className="text-text-primary font-bold text-2xl">🎓 Ta'lim</h1>
      </motion.div>

      {/* Grid */}
      <div className="grid grid-cols-2 gap-3">
        {EDU_MODULES.map((mod, i) => (
          <motion.button
            key={mod.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: i * 0.07 }}
            onClick={() => navigate(mod.route)}
            style={{
              background: `rgba(15,20,50,0.7)`,
              border: `1px solid ${mod.color}33`,
              borderRadius: '18px',
              padding: '16px',
              textAlign: 'left',
              cursor: 'pointer',
              position: 'relative',
              overflow: 'hidden',
              transition: 'all 0.25s ease',
            }}
            whileHover={{ scale: 1.03, y: -3 }}
            whileTap={{ scale: 0.98 }}
          >
            <div style={{
              position: 'absolute', top: 0, left: 0, right: 0, height: '2px',
              background: `linear-gradient(90deg, transparent, ${mod.color}, transparent)`,
            }} />

            <div style={{ fontSize: '28px', marginBottom: '8px' }}>{mod.emoji}</div>
            <div style={{ color: '#fff', fontWeight: 700, fontSize: '15px', marginBottom: '3px' }}>
              {mod.title}
            </div>
            <div style={{ color: 'rgba(180,200,255,0.6)', fontSize: '11px', lineHeight: 1.3 }}>
              {mod.desc}
            </div>
          </motion.button>
        ))}
      </div>
    </div>
  )
}
