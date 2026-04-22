/**
 * MathGamePage — Tez Hisob o'yini (Fast Math)
 * Answer math questions against a countdown timer
 */
import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { gamesApi } from '../lib/api'

type Op = '+' | '-' | '×' | '÷'
type Difficulty = 'easy' | 'medium' | 'hard'

const CONFIGS = {
  easy:   { ops: ['+', '-'] as Op[],       range: 20,  time: 30, questions: 10, label: 'Oson',  color: '#4ade80' },
  medium: { ops: ['+', '-', '×'] as Op[],  range: 50,  time: 25, questions: 15, label: "O'rta", color: '#fbbf24' },
  hard:   { ops: ['+', '-', '×', '÷'] as Op[], range: 100, time: 20, questions: 20, label: 'Qiyin', color: '#f87171' },
}

interface Question { a: number; b: number; op: Op; answer: number; display: string }

function generateQuestion(difficulty: Difficulty): Question {
  const conf = CONFIGS[difficulty]
  const op = conf.ops[Math.floor(Math.random() * conf.ops.length)]
  let a = Math.floor(Math.random() * conf.range) + 1
  let b = Math.floor(Math.random() * conf.range) + 1
  let answer: number

  switch (op) {
    case '+': answer = a + b; break
    case '-':
      if (a < b) [a, b] = [b, a]
      answer = a - b; break
    case '×':
      a = Math.floor(Math.random() * 12) + 1
      b = Math.floor(Math.random() * 12) + 1
      answer = a * b; break
    case '÷':
      b = Math.floor(Math.random() * 12) + 1
      answer = Math.floor(Math.random() * 12) + 1
      a = b * answer; break
    default: answer = 0
  }

  return { a, b, op, answer, display: `${a} ${op} ${b}` }
}

function generateOptions(answer: number): number[] {
  const opts = new Set<number>([answer])
  while (opts.size < 4) {
    const offset = Math.floor(Math.random() * 20) - 10
    const wrong = answer + offset
    if (wrong !== answer && wrong >= 0) opts.add(wrong)
  }
  return [...opts].sort(() => Math.random() - 0.5)
}

export default function MathGamePage() {
  const navigate = useNavigate()
  const [screen, setScreen] = useState<'setup' | 'game' | 'over'>('setup')
  const [difficulty, setDifficulty] = useState<Difficulty>('medium')
  const [question, setQuestion] = useState<Question | null>(null)
  const [options, setOptions] = useState<number[]>([])
  const [qIndex, setQIndex] = useState(0)
  const [score, setScore] = useState(0)
  const [correct, setCorrect] = useState(0)
  const [timeLeft, setTimeLeft] = useState(0)
  const [selected, setSelected] = useState<number | null>(null)
  const [feedback, setFeedback] = useState<'correct' | 'wrong' | null>(null)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const stopTimer = () => { if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null } }

  const nextQuestion = useCallback((idx: number, d: Difficulty) => {
    const conf = CONFIGS[d]
    if (idx >= conf.questions) {
      stopTimer()
      setScreen('over')
      gamesApi.saveResult({ game_name: 'math', difficulty: d, score, won: correct >= conf.questions * 0.5 }).catch(console.error)
      return
    }
    const q = generateQuestion(d)
    setQuestion(q)
    setOptions(generateOptions(q.answer))
    setSelected(null)
    setFeedback(null)
    setQIndex(idx)
    setTimeLeft(conf.time)
  }, [])

  const startGame = useCallback(() => {
    stopTimer()
    const conf = CONFIGS[difficulty]
    setScore(0)
    setCorrect(0)
    setQIndex(0)
    nextQuestion(0, difficulty)
    setScreen('game')

    timerRef.current = setInterval(() => {
      setTimeLeft(prev => {
        if (prev <= 1) { 
          stopTimer()
          setScreen('over')
          gamesApi.saveResult({ game_name: 'math', difficulty, score, won: correct >= conf.questions * 0.5 }).catch(console.error)
          return 0 
        }
        return prev - 1
      })
    }, 1000)
  }, [difficulty, nextQuestion])

  // Auto next after feedback
  useEffect(() => {
    if (feedback !== null) {
      const t = setTimeout(() => {
        nextQuestion(qIndex + 1, difficulty)
      }, 700)
      return () => clearTimeout(t)
    }
  }, [feedback, qIndex, difficulty, nextQuestion])

  useEffect(() => () => stopTimer(), [])

  const handleAnswer = useCallback((opt: number) => {
    if (selected !== null || !question) return
    setSelected(opt)
    if (opt === question.answer) {
      setFeedback('correct')
      const pts = difficulty === 'easy' ? 10 : difficulty === 'medium' ? 15 : 25
      setScore(prev => prev + pts + Math.floor(timeLeft / 2))
      setCorrect(prev => prev + 1)
    } else {
      setFeedback('wrong')
    }
  }, [selected, question, difficulty, timeLeft])

  const conf = CONFIGS[difficulty]
  const progress = question ? (qIndex / conf.questions) * 100 : 0
  const timerPct = (timeLeft / conf.time) * 100

  return (
    <div className="page" style={{ paddingBottom: '16px' }}>
      <AnimatePresence mode="wait">

        {/* Setup */}
        {screen === 'setup' && (
          <motion.div key="setup" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
            <div className="flex items-center gap-3 mb-5">
              <button onClick={() => navigate('/games')} style={{ background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.12)', color: 'rgba(180,200,255,0.8)', padding: '6px 12px', borderRadius: '8px', fontSize: '13px', cursor: 'pointer' }}>← Orqaga</button>
              <h1 className="text-text-primary font-bold text-xl">⚡ Tez Hisob</h1>
            </div>
            <p className="text-text-muted text-sm mb-4">Daraja tanlang</p>
            <div className="grid grid-cols-1 gap-3 mb-5">
              {(Object.entries(CONFIGS) as [Difficulty, typeof CONFIGS[Difficulty]][]).map(([key, d]) => (
                <button key={key} onClick={() => setDifficulty(key)}
                  style={{ padding: '16px 20px', borderRadius: '16px', cursor: 'pointer', textAlign: 'left',
                    background: difficulty === key ? `${d.color}15` : 'rgba(255,255,255,0.05)',
                    border: difficulty === key ? `1px solid ${d.color}` : '1px solid rgba(255,255,255,0.1)',
                    display: 'flex', alignItems: 'center', gap: '14px', transition: 'all 0.2s' }}>
                  <span style={{ fontSize: '28px' }}>{key === 'easy' ? '😊' : key === 'medium' ? '🧠' : '⚡'}</span>
                  <div>
                    <div style={{ color: '#fff', fontWeight: 700, fontSize: '15px' }}>{d.label}</div>
                    <div style={{ color: 'rgba(180,200,255,0.5)', fontSize: '12px' }}>
                      {d.questions} savol | {d.time}s countdown | {d.ops.join(', ')}
                    </div>
                  </div>
                  {difficulty === key && <div style={{ marginLeft: 'auto', color: d.color, fontSize: '18px' }}>✓</div>}
                </button>
              ))}
            </div>
            <button onClick={startGame} style={{ width: '100%', padding: '14px', borderRadius: '16px', border: 'none', background: 'linear-gradient(135deg, #4ade80, #22c55e)', color: '#052e16', fontSize: '15px', fontWeight: 800, cursor: 'pointer' }}>
              ⚡ Boshlash
            </button>
          </motion.div>
        )}

        {/* Game */}
        {screen === 'game' && question && (
          <motion.div key="game" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            {/* Top bar */}
            <div className="flex justify-between items-center mb-3">
              <div style={{ color: 'rgba(180,200,255,0.7)', fontSize: '13px' }}>{qIndex + 1}/{conf.questions}</div>
              <div style={{ background: timeLeft <= 5 ? 'rgba(248,113,113,0.2)' : 'rgba(74,222,128,0.15)', border: `1px solid ${timeLeft <= 5 ? '#f87171' : '#4ade80'}44`, borderRadius: '10px', padding: '4px 14px', fontSize: '16px', fontWeight: 800, color: timeLeft <= 5 ? '#f87171' : '#4ade80' }}>
                ⏱ {timeLeft}s
              </div>
              <div style={{ color: '#fbbf24', fontWeight: 700 }}>⭐ {score}</div>
            </div>

            {/* Progress bar */}
            <div style={{ height: '4px', background: 'rgba(255,255,255,0.1)', borderRadius: '2px', marginBottom: '16px', overflow: 'hidden' }}>
              <motion.div style={{ height: '100%', background: '#4ade80', borderRadius: '2px' }} animate={{ width: `${progress}%` }} />
            </div>
            {/* Timer bar */}
            <div style={{ height: '4px', background: 'rgba(255,255,255,0.1)', borderRadius: '2px', marginBottom: '24px', overflow: 'hidden' }}>
              <motion.div style={{ height: '100%', background: timeLeft <= 5 ? '#f87171' : '#60a5fa', borderRadius: '2px' }} animate={{ width: `${timerPct}%` }} transition={{ duration: 1, ease: 'linear' }} />
            </div>

            {/* Question */}
            <AnimatePresence mode="wait">
              <motion.div key={qIndex}
                initial={{ opacity: 0, y: 20, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -20 }}
                style={{ textAlign: 'center', marginBottom: '28px' }}>
                <div style={{ fontSize: '11px', color: 'rgba(180,200,255,0.5)', letterSpacing: '2px', textTransform: 'uppercase', marginBottom: '8px' }}>Hisoblang</div>
                <div style={{ fontSize: '42px', fontWeight: 900, color: '#fff' }}>{question.display} = ?</div>
                {feedback && (
                  <motion.div initial={{ opacity: 0, scale: 0.5 }} animate={{ opacity: 1, scale: 1 }} style={{ marginTop: '8px', fontSize: '20px' }}>
                    {feedback === 'correct' ? '✅ To\'g\'ri!' : `❌ Noto'g'ri! Javob: ${question.answer}`}
                  </motion.div>
                )}
              </motion.div>
            </AnimatePresence>

            {/* Options */}
            <div className="grid grid-cols-2 gap-3">
              {options.map((opt, i) => {
                const isSelected = selected === opt
                const isCorrect = opt === question.answer
                let bg = 'rgba(255,255,255,0.07)'
                let border = '1px solid rgba(255,255,255,0.12)'
                let color = '#fff'
                if (selected !== null) {
                  if (isCorrect) { bg = 'rgba(74,222,128,0.2)'; border = '1px solid #4ade80'; color = '#4ade80' }
                  else if (isSelected) { bg = 'rgba(248,113,113,0.2)'; border = '1px solid #f87171'; color = '#f87171' }
                  else { bg = 'rgba(255,255,255,0.04)'; color = 'rgba(255,255,255,0.4)' }
                }
                return (
                  <motion.button key={i}
                    whileHover={selected === null ? { scale: 1.04 } : {}}
                    whileTap={selected === null ? { scale: 0.95 } : {}}
                    onClick={() => handleAnswer(opt)}
                    style={{ padding: '18px', borderRadius: '16px', border, background: bg, color, fontSize: '22px', fontWeight: 800, cursor: selected === null ? 'pointer' : 'default', transition: 'all 0.2s' }}>
                    {opt}
                  </motion.button>
                )
              })}
            </div>
          </motion.div>
        )}

        {/* Over */}
        {screen === 'over' && (
          <motion.div key="over" initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }} style={{ textAlign: 'center', padding: '20px 0' }}>
            <div style={{ fontSize: '64px', marginBottom: '16px' }}>
              {correct >= conf.questions * 0.8 ? '🏆' : correct >= conf.questions * 0.5 ? '🎉' : '💪'}
            </div>
            <h2 style={{ color: '#fff', fontSize: '22px', fontWeight: 800, marginBottom: '16px' }}>
              {correct >= conf.questions * 0.8 ? 'Ajoyib!' : correct >= conf.questions * 0.5 ? "Zo'r!" : 'Mashq qilish kerak!'}
            </h2>
            <div className="grid grid-cols-3 gap-3 mb-6">
              {[
                { label: 'Ball', value: score, color: '#fbbf24' },
                { label: "To'g'ri", value: `${correct}/${conf.questions}`, color: '#4ade80' },
                { label: 'Aniqlik', value: `${Math.round(correct / conf.questions * 100)}%`, color: '#60a5fa' },
              ].map((s, i) => (
                <div key={i} style={{ background: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '14px', padding: '14px 8px' }}>
                  <div style={{ fontSize: '22px', fontWeight: 800, color: s.color }}>{s.value}</div>
                  <div style={{ fontSize: '10px', color: 'rgba(180,200,255,0.6)', marginTop: '2px' }}>{s.label}</div>
                </div>
              ))}
            </div>
            <div className="grid grid-cols-2 gap-3">
              <button onClick={startGame} style={{ padding: '14px', borderRadius: '14px', border: 'none', background: 'linear-gradient(135deg, #4ade80, #22c55e)', color: '#052e16', fontWeight: 700, cursor: 'pointer', fontSize: '14px' }}>🔄 Qayta</button>
              <button onClick={() => setScreen('setup')} style={{ padding: '14px', borderRadius: '14px', border: '1px solid rgba(255,255,255,0.15)', background: 'rgba(255,255,255,0.07)', color: 'rgba(200,220,255,0.8)', cursor: 'pointer', fontSize: '14px' }}>← Sozlash</button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
