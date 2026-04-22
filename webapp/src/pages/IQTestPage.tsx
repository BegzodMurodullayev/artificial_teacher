import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { iqApi, IQQuestion } from '../lib/api'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from '../lib/i18n'

export default function IQTestPage() {
  const [questions, setQuestions] = useState<IQQuestion[]>([])
  const [loading, setLoading] = useState(true)
  const [currentIdx, setCurrentIdx] = useState(0)
  const [answers, setAnswers] = useState<Record<number, number>>({})
  const [timeLeft, setTimeLeft] = useState(600) // 10 minutes
  const [isFinished, setIsFinished] = useState(false)
  const [result, setResult] = useState<{score: number, new_best: boolean} | null>(null)
  
  const navigate = useNavigate()
  const t = useTranslation()

  useEffect(() => {
    const fetchQuestions = async () => {
      try {
        const data = await iqApi.getQuestions()
        setQuestions(data.questions)
      } catch (e) {
        console.error(e)
      } finally {
        setLoading(false)
      }
    }
    fetchQuestions()
  }, [])

  useEffect(() => {
    if (loading || isFinished) return
    const timer = setInterval(() => {
      setTimeLeft(prev => {
        if (prev <= 1) {
          clearInterval(timer)
          handleSubmit()
          return 0
        }
        return prev - 1
      })
    }, 1000)
    return () => clearInterval(timer)
  }, [loading, isFinished])

  const handleSelectOption = (qId: number, optIdx: number) => {
    setAnswers(prev => ({ ...prev, [qId]: optIdx }))
    // auto-advance after short delay if not last question
    if (currentIdx < questions.length - 1) {
      setTimeout(() => setCurrentIdx(c => c + 1), 300)
    }
  }

  const handleSubmit = async () => {
    setIsFinished(true)
    try {
      const res = await iqApi.submitResult(answers)
      setResult({ score: res.score, new_best: res.new_best })
    } catch (e) {
      console.error(e)
      alert(t('iq_submit_err'))
    }
  }

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60)
    const s = seconds % 60
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
  }

  if (loading) {
    return (
      <div className="page flex items-center justify-center h-[80vh]">
        <div className="w-10 h-10 border-4 border-purple-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    )
  }

  if (isFinished) {
    return (
      <div className="page flex flex-col items-center justify-center min-h-[80vh] text-center px-4">
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          className="bg-white/10 p-8 rounded-3xl border border-white/20 w-full max-w-sm"
        >
          <div className="text-6xl mb-4">🧠</div>
          <h2 className="text-2xl font-bold text-white mb-2">{t('iq_result')}</h2>
          
          {result ? (
            <>
              <div className="text-7xl font-black text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-600 my-6">
                {result.score}
              </div>
              {result.new_best && (
                <div className="inline-block bg-yellow-500/20 text-yellow-300 px-3 py-1 rounded-full text-sm font-bold mb-4">
                  {t('iq_new_best')}
                </div>
              )}
              <p className="text-white/70 mb-6 text-sm">
                {t('iq_desc_res')}
              </p>
            </>
          ) : (
            <div className="w-8 h-8 border-4 border-purple-500 border-t-transparent rounded-full animate-spin mx-auto my-6"></div>
          )}

          <button
            onClick={() => navigate('/')}
            className="w-full py-4 bg-gradient-to-r from-purple-500 to-pink-500 rounded-2xl text-white font-bold text-lg hover:shadow-lg hover:shadow-purple-500/30 transition-all active:scale-95"
          >
            {t('iq_back_home')}
          </button>
        </motion.div>
      </div>
    )
  }

  if (questions.length === 0) {
    return <div className="page p-5 text-white/50 text-center">{t('iq_no_questions')}</div>
  }

  const currentQ = questions[currentIdx]

  return (
    <div className="page pb-20 max-w-lg mx-auto">
      {/* Header */}
      <div className="flex justify-between items-center mb-6 bg-white/5 p-4 rounded-2xl">
        <div>
          <div className="text-xs text-white/50 font-bold uppercase tracking-wider mb-1">{t('iq_question')}</div>
          <div className="text-xl font-black text-white">
            {currentIdx + 1} <span className="text-white/30">/ {questions.length}</span>
          </div>
        </div>
        <div className="text-right">
          <div className="text-xs text-white/50 font-bold uppercase tracking-wider mb-1">{t('iq_time')}</div>
          <div className={`text-xl font-mono font-black ${timeLeft < 60 ? 'text-red-400 animate-pulse' : 'text-white'}`}>
            {formatTime(timeLeft)}
          </div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="w-full h-2 bg-white/10 rounded-full mb-8 overflow-hidden">
        <motion.div 
          className="h-full bg-gradient-to-r from-purple-500 to-pink-500"
          initial={{ width: 0 }}
          animate={{ width: `${((currentIdx) / questions.length) * 100}%` }}
        />
      </div>

      {/* Question Card */}
      <AnimatePresence mode="wait">
        <motion.div
          key={currentQ.id}
          initial={{ x: 20, opacity: 0, scale: 0.95 }}
          animate={{ x: 0, opacity: 1, scale: 1 }}
          exit={{ x: -20, opacity: 0, filter: 'blur(4px)' }}
          transition={{ duration: 0.2 }}
          className="bg-white/10 border border-white/20 p-6 rounded-3xl shadow-xl"
        >
          <div className="inline-block bg-white/10 px-3 py-1 rounded-lg text-xs font-bold text-purple-300 uppercase tracking-wider mb-4">
            {currentQ.type}
          </div>
          
          <h2 className="text-xl font-medium text-white mb-8 leading-relaxed whitespace-pre-wrap">
            {currentQ.question}
          </h2>

          <div className="space-y-3">
            {currentQ.options.map((opt, idx) => {
              const isSelected = answers[currentQ.id] === idx
              return (
                <button
                  key={idx}
                  onClick={() => handleSelectOption(currentQ.id, idx)}
                  className={`w-full text-left p-4 rounded-2xl border-2 transition-all ${
                    isSelected 
                      ? 'border-purple-500 bg-purple-500/20 text-white' 
                      : 'border-white/10 bg-white/5 text-white/80 hover:bg-white/10 hover:border-white/20'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                      isSelected ? 'bg-purple-500 text-white' : 'bg-white/10 text-white/50'
                    }`}>
                      {String.fromCharCode(65 + idx)}
                    </div>
                    <span className="font-medium text-sm md:text-base">{opt}</span>
                  </div>
                </button>
              )
            })}
          </div>
        </motion.div>
      </AnimatePresence>

      <div className="flex justify-between mt-8">
        <button
          onClick={() => setCurrentIdx(c => Math.max(0, c - 1))}
          disabled={currentIdx === 0}
          className="px-6 py-3 rounded-xl bg-white/10 text-white font-bold disabled:opacity-30 transition-opacity"
        >
          {t('iq_prev')}
        </button>
        
        {currentIdx === questions.length - 1 ? (
          <button
            onClick={handleSubmit}
            className="px-6 py-3 rounded-xl bg-gradient-to-r from-purple-500 to-pink-500 text-white font-bold shadow-lg shadow-purple-500/30"
          >
            {t('iq_finish')}
          </button>
        ) : (
          <button
            onClick={() => setCurrentIdx(c => Math.min(questions.length - 1, c + 1))}
            className="px-6 py-3 rounded-xl bg-white/20 text-white font-bold hover:bg-white/30 transition-colors"
          >
            {t('iq_next')}
          </button>
        )}
      </div>
    </div>
  )
}
