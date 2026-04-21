/**
 * MemoryGamePage — Xotira o'yini (Memory Card Match)
 * React port of bolimlar test/oyinlar/xotira/
 * Features: 6 card themes, 3 difficulty levels, timer, score tracking
 */

import { useState, useCallback, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'

// ── Data ─────────────────────────────────────────────────────────────────────
const THEMES: Record<string, string[]> = {
  emoji:  ['😀','😂','🥰','😎','🤩','😜','🥳','😇','🤠','🥸','😍','🤣','😴','🤯','🥶'],
  number: ['1','2','3','4','5','6','7','8','9','10','11','12','13','14','15'],
  letter: ['A','B','D','E','F','G','H','I','J','K','L','M','N','O','P'],
  shape:  ['🔴','🟠','🟡','🟢','🔵','🟣','⚫','⚪','🟤','🔶','🔷','🔸','🔹','🔺','🔻'],
  animal: ['🐶','🐱','🐭','🐹','🐰','🦊','🐻','🐼','🐨','🐯','🦁','🐮','🐷','🐸','🐙'],
  fruit:  ['🍎','🍊','🍋','🍇','🍓','🍑','🍒','🥭','🍍','🥥','🍌','🍉','🍈','🫐','🥝'],
}

const DIFFICULTIES = {
  easy:   { cols: 4, rows: 4, pairs: 8,  size: 72, label: 'Oson 🟢' },
  medium: { cols: 5, rows: 4, pairs: 10, size: 62, label: "O'rta 🟡" },
  hard:   { cols: 6, rows: 5, pairs: 15, size: 54, label: 'Qiyin 🔴' },
}
type Difficulty = keyof typeof DIFFICULTIES
type Screen = 'setup' | 'game'

interface Card { id: number; symbol: string; flipped: boolean; matched: boolean }

function shuffle<T>(arr: T[]): T[] {
  return [...arr].sort(() => Math.random() - 0.5)
}

// ── Component ─────────────────────────────────────────────────────────────────
export default function MemoryGamePage() {
  const navigate = useNavigate()

  const [screen, setScreen] = useState<Screen>('setup')
  const [selectedThemes, setSelectedThemes] = useState<Set<string>>(new Set())
  const [difficulty, setDifficulty] = useState<Difficulty | null>(null)
  const [cards, setCards] = useState<Card[]>([])
  const [flipped, setFlipped] = useState<number[]>([])
  const [blocked, setBlocked] = useState(false)
  const [matched, setMatched] = useState(0)
  const [attempts, setAttempts] = useState(0)
  const [score, setScore] = useState(0)
  const [seconds, setSeconds] = useState(0)
  const [result, setResult] = useState<{ emoji: string; title: string; sub: string; vaqt: string; attempts: number; score: number } | null>(null)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const stopTimer = () => { if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null } }

  const formatTime = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`

  const startGame = useCallback(() => {
    if (!difficulty || selectedThemes.size === 0) return
    const { pairs } = DIFFICULTIES[difficulty]
    const pool = shuffle([...new Set(
      [...selectedThemes].flatMap(t => THEMES[t])
    )]).slice(0, pairs)

    const deck = shuffle([...pool, ...pool]).map((sym, i) => ({
      id: i, symbol: sym, flipped: false, matched: false
    }))

    setCards(deck)
    setFlipped([])
    setBlocked(false)
    setMatched(0)
    setAttempts(0)
    setScore(0)
    setSeconds(0)
    setResult(null)
    setScreen('game')

    stopTimer()
    timerRef.current = setInterval(() => setSeconds(s => s + 1), 1000)
  }, [difficulty, selectedThemes])

  useEffect(() => () => stopTimer(), [])

  const handleCard = useCallback((id: number) => {
    if (blocked) return
    const card = cards.find(c => c.id === id)
    if (!card || card.flipped || card.matched) return
    if (flipped.length >= 2) return

    const newFlipped = [...flipped, id]
    setCards(prev => prev.map(c => c.id === id ? { ...c, flipped: true } : c))
    setFlipped(newFlipped)

    if (newFlipped.length === 2) {
      const [a, b] = newFlipped.map(fid => cards.find(c => c.id === fid)!)
      setAttempts(prev => prev + 1)
      setBlocked(true)

      if (a.symbol === b.symbol) {
        const pts = difficulty === 'easy' ? 100 : difficulty === 'medium' ? 150 : 200
        setScore(prev => prev + pts)
        setTimeout(() => {
          setCards(prev => prev.map(c =>
            newFlipped.includes(c.id) ? { ...c, matched: true, flipped: true } : c
          ))
          setMatched(prev => {
            const newMatched = prev + 1
            const totalPairs = DIFFICULTIES[difficulty!].pairs
            if (newMatched === totalPairs) {
              stopTimer()
              setTimeout(() => {
                setSeconds(s => {
                  const bonusBall = Math.max(0, 1000 - s * 5)
                  const finalScore = score + pts + bonusBall
                  setScore(finalScore)
                  const eff = Math.round((newMatched / (attempts + 1)) * 100)
                  setResult({
                    emoji: eff >= 80 ? '🏆' : eff >= 60 ? '🎉' : '👍',
                    title: eff >= 80 ? 'Ajoyib xotira!' : eff >= 60 ? "Zo'r!" : 'Yaxshi!',
                    sub: `${formatTime(s)} da barcha juftlarni topdingiz!`,
                    vaqt: formatTime(s), attempts: attempts + 1, score: finalScore
                  })
                  return s
                })
              }, 400)
            }
            return newMatched
          })
          setFlipped([])
          setBlocked(false)
        }, 400)
      } else {
        setTimeout(() => {
          setCards(prev => prev.map(c =>
            newFlipped.includes(c.id) ? { ...c, flipped: false } : c
          ))
          setFlipped([])
          setBlocked(false)
        }, 900)
      }
    }
  }, [blocked, cards, flipped, difficulty, score, attempts])

  const totalPairs = difficulty ? DIFFICULTIES[difficulty].pairs : 0
  const conf = difficulty ? DIFFICULTIES[difficulty] : null

  const toggleTheme = (t: string) => {
    setSelectedThemes(prev => {
      const next = new Set(prev)
      next.has(t) ? next.delete(t) : next.add(t)
      return next
    })
  }

  const themeLabels: Record<string, { icon: string; label: string }> = {
    emoji:  { icon: '😊', label: 'Stikerlar' },
    number: { icon: '🔢', label: 'Raqamlar' },
    letter: { icon: '🔤', label: 'Harflar' },
    shape:  { icon: '🔷', label: 'Shakllar' },
    animal: { icon: '🐶', label: 'Hayvonlar' },
    fruit:  { icon: '🍎', label: 'Mevalar' },
  }

  return (
    <div className="page" style={{ paddingBottom: '16px' }}>
      <AnimatePresence mode="wait">

        {/* ── SETUP ── */}
        {screen === 'setup' && (
          <motion.div key="setup" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }}>
            <div className="flex items-center gap-3 mb-5">
              <button onClick={() => navigate('/games')} style={{ background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.12)', color: 'rgba(180,200,255,0.8)', padding: '6px 12px', borderRadius: '8px', fontSize: '13px', cursor: 'pointer' }}>← Orqaga</button>
              <h1 className="text-text-primary font-bold text-xl">🃏 Xotira</h1>
            </div>

            {/* Theme select */}
            <p style={{ color: 'rgba(180,200,255,0.6)', fontSize: '11px', letterSpacing: '2px', textTransform: 'uppercase', marginBottom: '10px' }}>Karta turi (bir yoki bir nechta)</p>
            <div className="flex flex-wrap gap-2 mb-5">
              {Object.entries(themeLabels).map(([key, { icon, label }]) => (
                <button key={key}
                  onClick={() => toggleTheme(key)}
                  style={{
                    padding: '8px 14px', borderRadius: '12px', cursor: 'pointer', fontSize: '13px', fontWeight: 600,
                    border: selectedThemes.has(key) ? '1px solid #fbbf24' : '1px solid rgba(255,255,255,0.15)',
                    background: selectedThemes.has(key) ? 'rgba(251,191,36,0.15)' : 'rgba(255,255,255,0.05)',
                    color: selectedThemes.has(key) ? '#fbbf24' : 'rgba(200,220,255,0.7)',
                    transition: 'all 0.2s',
                  }}>
                  {icon} {label}
                </button>
              ))}
            </div>

            {/* Difficulty */}
            <p style={{ color: 'rgba(180,200,255,0.6)', fontSize: '11px', letterSpacing: '2px', textTransform: 'uppercase', marginBottom: '10px' }}>Daraja</p>
            <div className="grid grid-cols-3 gap-2 mb-5">
              {(Object.entries(DIFFICULTIES) as [Difficulty, typeof DIFFICULTIES[Difficulty]][]).map(([key, d]) => (
                <button key={key} onClick={() => setDifficulty(key)}
                  style={{
                    padding: '12px 8px', borderRadius: '14px', cursor: 'pointer', textAlign: 'center',
                    background: difficulty === key ? 'rgba(255,255,255,0.12)' : 'rgba(255,255,255,0.05)',
                    border: difficulty === key
                      ? (key === 'easy' ? '1px solid #4ade80' : key === 'medium' ? '1px solid #fbbf24' : '1px solid #f87171')
                      : '1px solid rgba(255,255,255,0.1)',
                    transition: 'all 0.2s',
                  }}>
                  <div style={{ fontSize: '20px', marginBottom: '4px' }}>{key === 'easy' ? '🟢' : key === 'medium' ? '🟡' : '🔴'}</div>
                  <div style={{ color: '#fff', fontWeight: 700, fontSize: '12px' }}>{key === 'easy' ? 'Oson' : key === 'medium' ? "O'rta" : 'Qiyin'}</div>
                  <div style={{ color: 'rgba(180,200,255,0.5)', fontSize: '10px' }}>{d.cols}×{d.rows}</div>
                </button>
              ))}
            </div>

            <button
              disabled={selectedThemes.size === 0 || !difficulty}
              onClick={startGame}
              style={{
                width: '100%', padding: '14px', borderRadius: '16px', border: 'none',
                background: (selectedThemes.size > 0 && difficulty) ? 'linear-gradient(135deg, #fbbf24, #f59e0b)' : 'rgba(255,255,255,0.1)',
                color: (selectedThemes.size > 0 && difficulty) ? '#1a0a00' : 'rgba(180,200,255,0.4)',
                fontSize: '15px', fontWeight: 800, cursor: (selectedThemes.size > 0 && difficulty) ? 'pointer' : 'not-allowed',
                transition: 'all 0.3s',
              }}>
              🃏 Boshlash
            </button>
          </motion.div>
        )}

        {/* ── GAME ── */}
        {screen === 'game' && conf && (
          <motion.div key="game" initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }}>
            {/* Stats */}
            <div className="grid grid-cols-4 gap-2 mb-3">
              {[
                { label: '⏱ Vaqt', value: formatTime(seconds) },
                { label: '🔄 Harakat', value: attempts },
                { label: '✅ Topildi', value: matched },
                { label: '⭐ Ball', value: score },
              ].map((s, i) => (
                <div key={i} style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px', padding: '8px', textAlign: 'center' }}>
                  <div style={{ fontSize: '10px', color: 'rgba(180,200,255,0.5)' }}>{s.label}</div>
                  <div style={{ fontSize: '16px', fontWeight: 800, color: '#fff' }}>{s.value}</div>
                </div>
              ))}
            </div>

            {/* Status */}
            <div style={{ background: 'rgba(255,255,255,0.06)', borderRadius: '10px', padding: '8px 12px', textAlign: 'center', fontSize: '13px', color: 'rgba(200,220,255,0.8)', marginBottom: '12px' }}>
              🃏 {matched}/{totalPairs} juft topildi — Qoldi: {totalPairs - matched}
            </div>

            {/* Cards Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: `repeat(${conf.cols}, ${conf.size}px)`, gap: '8px', justifyContent: 'center' }}>
              {cards.map(card => (
                <div key={card.id} onClick={() => handleCard(card.id)}
                  style={{ width: conf.size, height: conf.size, perspective: '600px', cursor: !card.flipped && !card.matched ? 'pointer' : 'default' }}>
                  <motion.div
                    animate={{ rotateY: card.flipped || card.matched ? 180 : 0 }}
                    transition={{ duration: 0.4 }}
                    style={{ width: '100%', height: '100%', position: 'relative', transformStyle: 'preserve-3d' }}
                  >
                    {/* Front */}
                    <div style={{
                      position: 'absolute', inset: 0, borderRadius: '12px',
                      background: 'rgba(12,18,50,0.8)', border: '1px solid rgba(255,255,255,0.12)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      backfaceVisibility: 'hidden', fontSize: '22px',
                    }}>🎴</div>
                    {/* Back */}
                    <div style={{
                      position: 'absolute', inset: 0, borderRadius: '12px',
                      background: card.matched ? 'rgba(74,222,128,0.2)' : 'rgba(15,22,55,0.9)',
                      border: card.matched ? '1px solid #4ade80' : '1px solid rgba(255,255,255,0.15)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      backfaceVisibility: 'hidden', transform: 'rotateY(180deg)',
                      fontSize: conf.size > 60 ? '24px' : '18px',
                      boxShadow: card.matched ? '0 0 16px rgba(74,222,128,0.3)' : 'none',
                    }}>{card.symbol}</div>
                  </motion.div>
                </div>
              ))}
            </div>

            {/* Buttons */}
            <div className="flex gap-3 mt-4">
              <button onClick={() => { stopTimer(); startGame() }} style={{ flex: 1, padding: '12px', borderRadius: '14px', border: 'none', background: 'linear-gradient(135deg, #fbbf24, #f59e0b)', color: '#1a0a00', fontWeight: 700, cursor: 'pointer', fontSize: '14px' }}>🔄 Qayta</button>
              <button onClick={() => { stopTimer(); setScreen('setup') }} style={{ padding: '12px 16px', borderRadius: '14px', border: '1px solid rgba(255,255,255,0.15)', background: 'rgba(255,255,255,0.07)', color: 'rgba(200,220,255,0.8)', cursor: 'pointer', fontSize: '14px' }}>← Sozlash</button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Result Modal ── */}
      <AnimatePresence>
        {result && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(8px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}>
            <motion.div initial={{ scale: 0.5, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} transition={{ type: 'spring', stiffness: 400, damping: 20 }}
              style={{ background: 'rgba(10,15,40,0.98)', border: '1px solid rgba(255,255,255,0.15)', borderRadius: '28px', padding: '36px 32px', textAlign: 'center', minWidth: '300px' }}>
              <div style={{ fontSize: '52px', marginBottom: '12px' }}>{result.emoji}</div>
              <div style={{ fontSize: '20px', fontWeight: 800, color: '#fff', marginBottom: '6px' }}>{result.title}</div>
              <div style={{ fontSize: '13px', color: 'rgba(180,210,255,0.7)', marginBottom: '20px' }}>{result.sub}</div>
              <div className="grid grid-cols-3 gap-3 mb-5">
                {[
                  { label: 'Vaqt', value: result.vaqt },
                  { label: 'Harakat', value: result.attempts },
                  { label: 'Ball', value: result.score },
                ].map((s, i) => (
                  <div key={i} style={{ background: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '14px', padding: '12px 8px' }}>
                    <div style={{ fontSize: '20px', fontWeight: 800, color: '#fff' }}>{s.value}</div>
                    <div style={{ fontSize: '10px', color: 'rgba(180,200,255,0.6)', marginTop: '2px' }}>{s.label}</div>
                  </div>
                ))}
              </div>
              <div className="flex gap-3 justify-center">
                <button onClick={() => { setResult(null); startGame() }} style={{ padding: '12px 24px', borderRadius: '14px', border: 'none', background: 'linear-gradient(135deg, #fbbf24, #f59e0b)', color: '#1a0a00', fontWeight: 700, cursor: 'pointer' }}>🔄 Qayta</button>
                <button onClick={() => { setResult(null); setScreen('setup') }} style={{ padding: '12px 20px', borderRadius: '14px', border: '1px solid rgba(255,255,255,0.15)', background: 'rgba(255,255,255,0.08)', color: 'rgba(200,220,255,0.8)', cursor: 'pointer' }}>← Menyu</button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
