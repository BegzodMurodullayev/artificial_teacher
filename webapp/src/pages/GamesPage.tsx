/**
 * GamesPage — Hub page for all mini-games in the WebApp.
 */

import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'

const GAMES = [
  {
    id: 'xo',
    emoji: '❌⭕',
    title: "X va O",
    desc: "AI yoki do'stingiz bilan o'ynang",
    color: '#f87171',
    glow: 'rgba(248,113,113,0.3)',
    route: '/games/xo',
  },
  {
    id: 'memory',
    emoji: '🃏',
    title: "Xotira",
    desc: "Juft kartalarni toping",
    color: '#fbbf24',
    glow: 'rgba(251,191,36,0.3)',
    route: '/games/memory',
  },
  {
    id: 'number',
    emoji: '🔢',
    title: "Raqam Topish",
    desc: "Yashirin raqamni toping",
    color: '#60a5fa',
    glow: 'rgba(96,165,250,0.3)',
    route: '/games/number',
  },
  {
    id: 'math',
    emoji: '⚡',
    title: "Tez Hisob",
    desc: "Matematik qobiliyatingizni sinang",
    color: '#4ade80',
    glow: 'rgba(74,222,128,0.3)',
    route: '/games/math',
  },
  {
    id: 'sudoku',
    emoji: '🔷',
    title: "Sudoku",
    desc: "Mantiqiy raqamlar o'yini",
    color: '#a78bfa',
    glow: 'rgba(167,139,250,0.3)',
    route: '/games/sudoku',
  },
  {
    id: 'word',
    emoji: '🔤',
    title: "So'z Topish",
    desc: "Inglizcha so'zlarni toping",
    color: '#fb923c',
    glow: 'rgba(251,146,60,0.3)',
    route: '/games/word',
  },
]

export default function GamesPage() {
  const navigate = useNavigate()

  return (
    <div className="page">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="mb-4"
      >
        <p className="text-text-muted text-xs">WebApp</p>
        <h1 className="text-text-primary font-bold text-xl">🎮 O'yinlar</h1>
      </motion.div>

      {/* Game Grid */}
      <div className="grid grid-cols-2 gap-3">
        {GAMES.map((game, i) => (
          <motion.button
            key={game.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: i * 0.07 }}
            onClick={() => navigate(game.route)}
            style={{
              background: `rgba(15,20,50,0.7)`,
              border: `1px solid ${game.color}33`,
              borderRadius: '18px',
              padding: '16px',
              textAlign: 'left',
              cursor: 'pointer',
              opacity: 1,
              position: 'relative',
              overflow: 'hidden',
              transition: 'all 0.25s ease',
            }}
            whileHover={{ scale: 1.03, y: -3 }}
            whileTap={{ scale: 0.98 }}
          >
            {/* Glow */}
            <div style={{
              position: 'absolute', top: 0, left: 0, right: 0, height: '2px',
              background: `linear-gradient(90deg, transparent, ${game.color}, transparent)`,
            }} />

            <div style={{ fontSize: '28px', marginBottom: '8px' }}>{game.emoji}</div>
            <div style={{ color: '#fff', fontWeight: 700, fontSize: '14px', marginBottom: '3px' }}>
              {game.title}
            </div>
            <div style={{ color: 'rgba(180,200,255,0.6)', fontSize: '11px', lineHeight: 1.3 }}>
              {game.desc}
            </div>
          </motion.button>
        ))}
      </div>

      {/* Back button */}
      <motion.button
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
        onClick={() => navigate('/')}
        style={{
          marginTop: '20px', width: '100%',
          padding: '12px', borderRadius: '14px',
          border: '1px solid rgba(255,255,255,0.1)',
          background: 'rgba(255,255,255,0.05)',
          color: 'rgba(180,200,255,0.7)',
          fontSize: '14px', cursor: 'pointer',
        }}
      >
        ← Asosiy sahifaga
      </motion.button>
    </div>
  )
}
