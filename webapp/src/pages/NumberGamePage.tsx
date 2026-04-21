/**
 * NumberGamePage — Raqam Topish o'yini
 * Guess the hidden number within range, with difficulty levels
 */
import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'

type Difficulty = 'easy' | 'medium' | 'hard'
const DIFFICULTIES = {
  easy:   { min: 1, max: 50,  attempts: 10, label: 'Oson', color: '#4ade80' },
  medium: { min: 1, max: 100, attempts: 7,  label: "O'rta", color: '#fbbf24' },
  hard:   { min: 1, max: 200, attempts: 5,  label: 'Qiyin', color: '#f87171' },
}

export default function NumberGamePage() {
  const navigate = useNavigate()
  const [screen, setScreen] = useState<'setup' | 'game' | 'over'>('setup')
  const [difficulty, setDifficulty] = useState<Difficulty>('medium')
  const [secret, setSecret] = useState(0)
  const [guess, setGuess] = useState('')
  const [remaining, setRemaining] = useState(0)
  const [history, setHistory] = useState<{ num: number; hint: string }[]>([])
  const [won, setWon] = useState(false)
  const [score, setScore] = useState(0)
  const [totalScore, setTotalScore] = useState(0)
  const [round, setRound] = useState(1)

  const startGame = useCallback(() => {
    const conf = DIFFICULTIES[difficulty]
    const num = Math.floor(Math.random() * (conf.max - conf.min + 1)) + conf.min
    setSecret(num)
    setGuess('')
    setRemaining(conf.attempts)
    setHistory([])
    setWon(false)
    setScore(0)
    setScreen('game')
  }, [difficulty])

  const handleGuess = useCallback(() => {
    const conf = DIFFICULTIES[difficulty]
    const num = parseInt(guess)
    if (isNaN(num) || num < conf.min || num > conf.max) return

    const newHistory = [...history]
    let hint = ''

    if (num === secret) {
      hint = '🎯 To\'g\'ri!'
      const pts = remaining * (difficulty === 'easy' ? 10 : difficulty === 'medium' ? 20 : 40)
      setScore(pts)
      setTotalScore(prev => prev + pts)
      setWon(true)
      newHistory.push({ num, hint })
      setHistory(newHistory)
      setScreen('over')
      return
    }

    const diff = Math.abs(num - secret)
    if (diff <= 5) hint = num < secret ? '🔥 Juda yaqin! Kattaroq' : '🔥 Juda yaqin! Kichikroq'
    else if (diff <= 20) hint = num < secret ? '♨️ Iliq! Kattaroq' : '♨️ Iliq! Kichikroq'
    else hint = num < secret ? '❄️ Sovuq! Kattaroq' : '❄️ Sovuq! Kichikroq'

    newHistory.push({ num, hint })
    setHistory(newHistory)
    setGuess('')

    const newRemaining = remaining - 1
    setRemaining(newRemaining)
    if (newRemaining === 0) {
      setWon(false)
      setScreen('over')
    }
  }, [guess, secret, history, remaining, difficulty])

  const conf = DIFFICULTIES[difficulty]

  return (
    <div className="page" style={{ paddingBottom: '16px' }}>
      <AnimatePresence mode="wait">

        {/* Setup */}
        {screen === 'setup' && (
          <motion.div key="setup" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
            <div className="flex items-center gap-3 mb-5">
              <button onClick={() => navigate('/games')} style={{ background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.12)', color: 'rgba(180,200,255,0.8)', padding: '6px 12px', borderRadius: '8px', fontSize: '13px', cursor: 'pointer' }}>← Orqaga</button>
              <h1 className="text-text-primary font-bold text-xl">🔢 Raqam Topish</h1>
            </div>
            {totalScore > 0 && (
              <div style={{ background: 'rgba(96,165,250,0.1)', border: '1px solid rgba(96,165,250,0.2)', borderRadius: '14px', padding: '12px', textAlign: 'center', marginBottom: '16px' }}>
                <div style={{ color: 'rgba(180,200,255,0.6)', fontSize: '12px' }}>Jami ball</div>
                <div style={{ color: '#60a5fa', fontSize: '24px', fontWeight: 800 }}>{totalScore}</div>
              </div>
            )}
            <p className="text-text-muted text-sm mb-4">Daraja tanlang</p>
            <div className="grid grid-cols-1 gap-3">
              {(Object.entries(DIFFICULTIES) as [Difficulty, typeof DIFFICULTIES[Difficulty]][]).map(([key, d]) => (
                <button key={key} onClick={() => setDifficulty(key)}
                  style={{ padding: '16px 20px', borderRadius: '16px', cursor: 'pointer', textAlign: 'left',
                    background: difficulty === key ? `${d.color}15` : 'rgba(255,255,255,0.05)',
                    border: difficulty === key ? `1px solid ${d.color}` : '1px solid rgba(255,255,255,0.1)',
                    display: 'flex', alignItems: 'center', gap: '14px', transition: 'all 0.2s' }}>
                  <span style={{ fontSize: '28px' }}>{key === 'easy' ? '😊' : key === 'medium' ? '🧠' : '🤯'}</span>
                  <div>
                    <div style={{ color: '#fff', fontWeight: 700, fontSize: '15px' }}>{d.label}</div>
                    <div style={{ color: 'rgba(180,200,255,0.5)', fontSize: '12px' }}>{d.min}–{d.max} orasidan | {d.attempts} ta urinish</div>
                  </div>
                  {difficulty === key && <div style={{ marginLeft: 'auto', color: d.color, fontSize: '18px' }}>✓</div>}
                </button>
              ))}
            </div>
            <button onClick={startGame} style={{ width: '100%', marginTop: '16px', padding: '14px', borderRadius: '16px', border: 'none', background: 'linear-gradient(135deg, #60a5fa, #818cf8)', color: '#fff', fontSize: '15px', fontWeight: 800, cursor: 'pointer' }}>
              🎲 O'yinni boshlash
            </button>
          </motion.div>
        )}

        {/* Game */}
        {screen === 'game' && (
          <motion.div key="game" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
            <div className="flex items-center justify-between mb-5">
              <h1 className="text-text-primary font-bold text-lg">🔢 Raqam toping</h1>
              <div style={{ background: `${conf.color}20`, border: `1px solid ${conf.color}44`, borderRadius: '10px', padding: '4px 12px', fontSize: '12px', color: conf.color }}>
                {conf.label}
              </div>
            </div>

            <div style={{ textAlign: 'center', marginBottom: '20px' }}>
              <div style={{ color: 'rgba(180,200,255,0.6)', fontSize: '13px', marginBottom: '4px' }}>
                {conf.min}–{conf.max} orasidagi raqamni toping
              </div>
              <div style={{ display: 'flex', gap: '6px', justifyContent: 'center', marginTop: '8px' }}>
                {Array.from({ length: DIFFICULTIES[difficulty].attempts }, (_, i) => (
                  <div key={i} style={{ width: '28px', height: '8px', borderRadius: '4px', background: i < remaining ? conf.color : 'rgba(255,255,255,0.1)', transition: 'all 0.3s' }} />
                ))}
              </div>
              <div style={{ color: 'rgba(180,200,255,0.5)', fontSize: '12px', marginTop: '6px' }}>{remaining} ta urinish qoldi</div>
            </div>

            {/* Input */}
            <div style={{ display: 'flex', gap: '10px', marginBottom: '16px' }}>
              <input
                type="number" value={guess}
                onChange={e => setGuess(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleGuess()}
                placeholder={`${conf.min}–${conf.max}`}
                min={conf.min} max={conf.max}
                style={{ flex: 1, padding: '14px 16px', borderRadius: '14px', border: '1px solid rgba(255,255,255,0.15)', background: 'rgba(255,255,255,0.06)', color: '#fff', fontSize: '18px', fontWeight: 700, outline: 'none', textAlign: 'center' }}
              />
              <button onClick={handleGuess} style={{ padding: '14px 20px', borderRadius: '14px', border: 'none', background: 'linear-gradient(135deg, #60a5fa, #818cf8)', color: '#fff', fontWeight: 800, cursor: 'pointer', fontSize: '16px' }}>
                →
              </button>
            </div>

            {/* History */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '280px', overflowY: 'auto' }}>
              {[...history].reverse().map((h, i) => (
                <motion.div key={i} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }}
                  style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px', padding: '10px 16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span style={{ color: '#fff', fontWeight: 700, fontSize: '18px' }}>{h.num}</span>
                  <span style={{ color: 'rgba(200,220,255,0.8)', fontSize: '13px' }}>{h.hint}</span>
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}

        {/* Over */}
        {screen === 'over' && (
          <motion.div key="over" initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }} style={{ textAlign: 'center', padding: '20px 0' }}>
            <div style={{ fontSize: '64px', marginBottom: '16px' }}>{won ? '🏆' : '😔'}</div>
            <h2 style={{ color: '#fff', fontSize: '22px', fontWeight: 800, marginBottom: '8px' }}>
              {won ? "To'g'ri topdingiz!" : "Uyg'un!"}
            </h2>
            <p style={{ color: 'rgba(180,200,255,0.7)', fontSize: '14px', marginBottom: '8px' }}>
              {won ? `+${score} ball!` : `Javob: ${secret} edi`}
            </p>
            {totalScore > 0 && (
              <p style={{ color: '#60a5fa', fontSize: '14px', marginBottom: '24px' }}>Jami ball: <strong>{totalScore}</strong></p>
            )}
            <div className="grid grid-cols-2 gap-3">
              <button onClick={() => { setRound(r => r + 1); startGame() }} style={{ padding: '14px', borderRadius: '14px', border: 'none', background: 'linear-gradient(135deg, #60a5fa, #818cf8)', color: '#fff', fontWeight: 700, cursor: 'pointer', fontSize: '14px' }}>
                🔄 Yangi raqam
              </button>
              <button onClick={() => { setTotalScore(0); setRound(1); setScreen('setup') }} style={{ padding: '14px', borderRadius: '14px', border: '1px solid rgba(255,255,255,0.15)', background: 'rgba(255,255,255,0.07)', color: 'rgba(200,220,255,0.8)', cursor: 'pointer', fontSize: '14px' }}>
                ← Sozlashga
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
