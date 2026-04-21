/**
 * QuizPage — Interactive quiz inside the WebApp.
 */

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { GlassCard } from '@/components/ui/GlassCard'
import { NeonButton } from '@/components/ui/NeonButton'
import { useUsage, usePlan } from '@/store/useStore'

type QuizMode = 'idle' | 'settings' | 'playing' | 'result'

// Sample questions (in real app — fetched from API)
const SAMPLE_QUESTIONS = [
  {
    id: 1, question: "Choose the correct form:",
    full: "She ___ to school every day.",
    options: { A: 'go', B: 'goes', C: 'going', D: 'gone' },
    answer: 'B',
    explanation: "Third person singular (she/he/it) requires 's' — 'goes'.",
    difficulty: 0.2,
  },
  {
    id: 2, question: "Which is correct?",
    full: "If I ___ rich, I would travel.",
    options: { A: 'am', B: 'was', C: 'were', D: 'be' },
    answer: 'C',
    explanation: "Second conditional uses 'were' for all subjects.",
    difficulty: 0.5,
  },
  {
    id: 3, question: "Fill in the blank:",
    full: "I have ___ to London three times.",
    options: { A: 'gone', B: 'went', C: 'go', D: 'been' },
    answer: 'D',
    explanation: "'Have been' = visited and returned. 'Have gone' = still there.",
    difficulty: 0.6,
  },
  {
    id: 4, question: "Choose the correct article:",
    full: "___ Eiffel Tower is in Paris.",
    options: { A: 'A', B: 'An', C: 'The', D: 'No article' },
    answer: 'C',
    explanation: "We use 'the' with specific, well-known landmarks.",
    difficulty: 0.3,
  },
  {
    id: 5, question: "Which sentence is grammatically correct?",
    full: "",
    options: {
      A: 'He don\'t like pizza',
      B: 'He doesn\'t likes pizza',
      C: 'He doesn\'t like pizza',
      D: 'He not like pizza',
    },
    answer: 'C',
    explanation: "Negative: subject + doesn't + base form (no 's').",
    difficulty: 0.3,
  },
]

const OPTION_LETTERS = ['A', 'B', 'C', 'D'] as const

export default function QuizPage() {
  const [mode, setMode]       = useState<QuizMode>('idle')
  const [qIndex, setQIndex]   = useState(0)
  const [selected, setSelected] = useState<string | null>(null)
  const [showResult, setShowResult] = useState(false)
  const [score, setScore]     = useState(0)
  const [answers, setAnswers] = useState<boolean[]>([])
  const [count, setCount]     = useState(5)

  const plan  = usePlan()
  const usage = useUsage()

  const questions = SAMPLE_QUESTIONS.slice(0, count)
  const current   = questions[qIndex]
  const isLast    = qIndex >= questions.length - 1
  const limitReached = usage.quiz >= plan.quiz_per_day

  function handleStart() {
    setQIndex(0); setScore(0); setAnswers([])
    setSelected(null); setShowResult(false)
    setMode('playing')
  }

  function handleAnswer(letter: string) {
    if (selected) return
    setSelected(letter)
    setShowResult(true)
    const correct = letter === current.answer
    if (correct) setScore(s => s + 1)
    setAnswers(a => [...a, correct])
  }

  function handleNext() {
    if (isLast) {
      setMode('result')
    } else {
      setQIndex(i => i + 1)
      setSelected(null)
      setShowResult(false)
    }
  }

  const accuracy = answers.length > 0
    ? Math.round((answers.filter(Boolean).length / answers.length) * 100)
    : 0

  return (
    <div className="page">
      <motion.h1
        className="text-gradient font-bold text-2xl"
        initial={{ opacity: 0, x: -16 }}
        animate={{ opacity: 1, x: 0 }}
      >
        🧠 Quiz
      </motion.h1>

      <AnimatePresence mode="wait">

        {/* ── IDLE ── */}
        {mode === 'idle' && (
          <motion.div
            key="idle" className="flex flex-col gap-4"
            initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
          >
            <GlassCard variant="cyan" padding="lg">
              <div className="text-center mb-6">
                <div className="text-5xl mb-3 animate-float">🧠</div>
                <h2 className="text-text-primary font-bold text-xl">Bilimingizni sinang!</h2>
                <p className="text-text-secondary text-sm mt-1">
                  Grammatika, lug'at va mantiqiy savollar
                </p>
              </div>

              <div className="flex flex-col gap-3 mb-6">
                <p className="text-text-muted text-xs text-center">Savollar soni:</p>
                <div className="flex gap-2">
                  {[5, 10, 15, 20].map(n => (
                    <button
                      key={n}
                      onClick={() => setCount(n)}
                      className={`flex-1 py-2 rounded-xl text-sm font-medium transition-all ${
                        count === n
                          ? 'bg-neon-cyan/20 text-neon-cyan border border-neon-cyan/40'
                          : 'glass-card text-text-secondary'
                      }`}
                    >
                      {n}
                    </button>
                  ))}
                </div>
              </div>

              {limitReached ? (
                <div className="text-center py-3 text-neon-pink text-sm">
                  ⚠️ Kunlik quiz limiti tugadi ({plan.quiz_per_day} ta)
                </div>
              ) : (
                <NeonButton variant="cyan" size="xl" fullWidth onClick={handleStart}>
                  🚀 Boshlash ({count} ta savol)
                </NeonButton>
              )}
            </GlassCard>

            {/* Stats */}
            <GlassCard variant="dark">
              <h3 className="text-text-muted text-xs font-semibold uppercase tracking-wider mb-3">
                Bugun
              </h3>
              <div className="flex justify-around">
                <div className="text-center">
                  <div className="text-neon-cyan font-bold text-lg">{usage.quiz}</div>
                  <div className="text-text-muted text-2xs">O'ynaldi</div>
                </div>
                <div className="text-center">
                  <div className="text-neon-purple font-bold text-lg">{plan.quiz_per_day - usage.quiz}</div>
                  <div className="text-text-muted text-2xs">Qoldi</div>
                </div>
              </div>
            </GlassCard>
          </motion.div>
        )}

        {/* ── PLAYING ── */}
        {mode === 'playing' && current && (
          <motion.div
            key={`q-${qIndex}`} className="flex flex-col gap-4"
            initial={{ opacity: 0, x: 30 }} animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -30 }} transition={{ type: 'spring', stiffness: 300, damping: 25 }}
          >
            {/* Progress */}
            <div className="flex items-center gap-3">
              <div className="flex-1 h-1.5 bg-space-muted rounded-full overflow-hidden">
                <motion.div
                  className="h-full bg-gradient-to-r from-neon-cyan to-neon-purple rounded-full"
                  animate={{ width: `${((qIndex + 1) / questions.length) * 100}%` }}
                  transition={{ duration: 0.4 }}
                />
              </div>
              <span className="text-text-muted text-xs whitespace-nowrap">
                {qIndex + 1} / {questions.length}
              </span>
            </div>

            {/* Question */}
            <GlassCard variant="dark" padding="lg">
              <p className="text-text-secondary text-xs mb-1">{current.question}</p>
              <p className="text-text-primary font-semibold text-lg leading-relaxed">
                {current.full || current.question}
              </p>
              <div className="flex items-center gap-2 mt-2">
                <div className="w-1.5 h-1.5 rounded-full bg-neon-cyan" />
                <span className="text-text-muted text-xs">
                  {current.difficulty < 0.3 ? 'Oson' : current.difficulty < 0.6 ? "O'rtacha" : 'Qiyin'}
                </span>
              </div>
            </GlassCard>

            {/* Options */}
            <div className="flex flex-col gap-2">
              {OPTION_LETTERS.map(letter => {
                const text    = current.options[letter]
                const isRight = letter === current.answer
                const isSel   = selected === letter
                let style     = 'glass-card border border-space-border text-text-primary'

                if (showResult) {
                  if (isRight) style = 'bg-neon-green/20 border border-neon-green/60 text-neon-green'
                  else if (isSel) style = 'bg-neon-pink/20 border border-neon-pink/60 text-neon-pink'
                  else style = 'glass-card border border-space-border/30 text-text-muted opacity-50'
                }

                return (
                  <motion.button
                    key={letter}
                    className={`w-full text-left px-4 py-3 rounded-xl text-sm font-medium transition-all flex items-center gap-3 ${style}`}
                    onClick={() => handleAnswer(letter)}
                    whileTap={!selected ? { scale: 0.98 } : undefined}
                    disabled={!!selected}
                  >
                    <span className="w-6 h-6 rounded-full bg-space-muted flex items-center justify-center text-xs font-bold shrink-0">
                      {letter}
                    </span>
                    {text}
                    {showResult && isRight && <span className="ml-auto">✅</span>}
                    {showResult && isSel && !isRight && <span className="ml-auto">❌</span>}
                  </motion.button>
                )
              })}
            </div>

            {/* Explanation */}
            <AnimatePresence>
              {showResult && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0 }}
                >
                  <GlassCard variant="dark" padding="sm">
                    <p className="text-text-secondary text-xs">
                      💡 {current.explanation}
                    </p>
                  </GlassCard>
                  <NeonButton
                    variant={isLast ? 'cyan' : 'ghost'}
                    size="lg" fullWidth
                    onClick={handleNext}
                    className="mt-3"
                  >
                    {isLast ? '🏁 Natijani ko\'rish' : 'Keyingi savol →'}
                  </NeonButton>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        )}

        {/* ── RESULT ── */}
        {mode === 'result' && (
          <motion.div
            key="result" className="flex flex-col gap-4"
            initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }}
          >
            <GlassCard variant="cyan" padding="lg">
              <div className="text-center">
                <motion.div
                  className="text-6xl mb-3"
                  animate={{ scale: [1, 1.2, 1], rotate: [0, 10, -10, 0] }}
                  transition={{ duration: 0.6 }}
                >
                  {accuracy >= 90 ? '🏆' : accuracy >= 70 ? '✅' : accuracy >= 50 ? '📚' : '💪'}
                </motion.div>
                <h2 className="text-gradient font-bold text-3xl">{accuracy}%</h2>
                <p className="text-text-secondary mt-1">
                  {score}/{questions.length} to'g'ri javob
                </p>
                <p className="text-text-muted text-sm mt-2">
                  {accuracy >= 90 ? 'A\'lo! Zo\'r natija! 🌟'
                    : accuracy >= 70 ? 'Yaxshi! Davom eting! 👍'
                    : accuracy >= 50 ? "O'rtacha. Yana mashq qiling! 📖"
                    : "Ko'proq mashq kerak. Hafsalangizni yo'qotmang! 💪"}
                </p>
              </div>
            </GlassCard>

            {/* Answer breakdown */}
            <div className="flex gap-1.5">
              {answers.map((correct, i) => (
                <motion.div
                  key={i}
                  className={`flex-1 h-2 rounded-full ${correct ? 'bg-neon-green' : 'bg-neon-pink'}`}
                  initial={{ scaleX: 0 }}
                  animate={{ scaleX: 1 }}
                  transition={{ delay: i * 0.08 }}
                  style={{ boxShadow: correct ? '0 0 4px #00ff88' : '0 0 4px #ff2d78' }}
                />
              ))}
            </div>

            <div className="flex gap-3">
              <NeonButton variant="cyan" size="lg" fullWidth onClick={handleStart}>
                🔄 Qaytadan
              </NeonButton>
              <NeonButton variant="ghost" size="lg" fullWidth onClick={() => setMode('idle')}>
                🏠 Menu
              </NeonButton>
            </div>
          </motion.div>
        )}

      </AnimatePresence>
    </div>
  )
}
