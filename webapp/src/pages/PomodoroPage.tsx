import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { usePomodoro, TimerMode } from '../hooks/usePomodoro'
import { gamesApi } from '../lib/api'

export default function PomodoroPage() {
  const [showSettings, setShowSettings] = useState(false)
  
  const handleComplete = (completedMode: TimerMode) => {
    // Reward XP when a pomodoro block completes
    if (completedMode === 'pomodoro') {
      try {
        gamesApi.saveResult({
          game_name: 'Pomodoro',
          difficulty: 'focus',
          score: 1, // 1 block
          won: true,
        })
        // The popup is managed by telegram or we could show an inner toast
        console.log('XP rewarded for Pomodoro!')
      } catch (error) {
        console.error('Failed to reward XP', error)
      }
    }
  }

  const {
    timeLeft,
    isActive,
    mode,
    pomodorosCompleted,
    settings,
    toggleTimer,
    resetTimer,
    switchMode,
    updateSettings
  } = usePomodoro(handleComplete)

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60)
    const s = seconds % 60
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
  }

  const progressPercentage = () => {
    let total = settings.pomodoroTime * 60
    if (mode === 'shortBreak') total = settings.shortBreakTime * 60
    if (mode === 'longBreak') total = settings.longBreakTime * 60
    return ((total - timeLeft) / total) * 100
  }

  const modeLabels = {
    pomodoro: '🍅 Diqqat (Focus)',
    shortBreak: '☕ Qisqa tanaffus',
    longBreak: '🛋️ Uzoq tanaffus',
  }

  const modeColors = {
    pomodoro: 'from-red-500 to-orange-500',
    shortBreak: 'from-green-400 to-emerald-500',
    longBreak: 'from-blue-400 to-indigo-500',
  }

  // Update Telegram WebApp MainButton if inside TG
  useEffect(() => {
    const tg = window.Telegram?.WebApp
    if (tg) {
      if (isActive) {
        tg.MainButton.text = "PAUZA QILISH"
        tg.MainButton.color = "#FF9800"
      } else {
        tg.MainButton.text = timeLeft < (mode === 'pomodoro' ? settings.pomodoroTime * 60 : mode === 'shortBreak' ? settings.shortBreakTime * 60 : settings.longBreakTime * 60) 
          ? "DAVOM ETISH" 
          : "BOSHLASH"
        tg.MainButton.color = "#2196F3"
      }
      tg.MainButton.show()
      
      const onClick = () => toggleTimer()
      tg.MainButton.onClick(onClick)
      
      return () => {
        tg.MainButton.offClick(onClick)
      }
    }
  }, [isActive, timeLeft, toggleTimer, mode, settings])

  useEffect(() => {
    return () => {
      window.Telegram?.WebApp?.MainButton.hide()
    }
  }, [])

  return (
    <div className="page pb-20 flex flex-col items-center justify-center min-h-[80vh]">
      <div className="w-full max-w-sm">
        
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-2xl font-bold text-white">Pomodoro</h1>
          <button 
            onClick={() => setShowSettings(!showSettings)}
            className="p-2 bg-white/10 rounded-full text-white/70 hover:text-white"
          >
            ⚙️
          </button>
        </div>

        {/* Settings Panel */}
        {showSettings && (
          <motion.div 
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-white/10 p-4 rounded-2xl mb-8 border border-white/20"
          >
            <h3 className="font-bold text-white mb-3">Sozlamalar (daqiqa)</h3>
            <div className="flex gap-2">
              <label className="flex-1 text-xs text-white/70 text-center">
                Focus
                <input 
                  type="number" 
                  value={settings.pomodoroTime}
                  onChange={(e) => updateSettings({ pomodoroTime: Number(e.target.value) })}
                  className="w-full bg-black/30 rounded p-2 text-white mt-1 text-center"
                  min="1" max="60"
                />
              </label>
              <label className="flex-1 text-xs text-white/70 text-center">
                Qisqa T.
                <input 
                  type="number" 
                  value={settings.shortBreakTime}
                  onChange={(e) => updateSettings({ shortBreakTime: Number(e.target.value) })}
                  className="w-full bg-black/30 rounded p-2 text-white mt-1 text-center"
                  min="1" max="30"
                />
              </label>
              <label className="flex-1 text-xs text-white/70 text-center">
                Uzoq T.
                <input 
                  type="number" 
                  value={settings.longBreakTime}
                  onChange={(e) => updateSettings({ longBreakTime: Number(e.target.value) })}
                  className="w-full bg-black/30 rounded p-2 text-white mt-1 text-center"
                  min="1" max="60"
                />
              </label>
            </div>
            <button 
              onClick={() => setShowSettings(false)}
              className="mt-4 w-full py-2 bg-blue-500 rounded-xl text-white font-bold"
            >
              Yopish
            </button>
          </motion.div>
        )}

        {/* Mode Selector */}
        <div className="flex bg-white/5 p-1 rounded-xl mb-8">
          {(['pomodoro', 'shortBreak', 'longBreak'] as TimerMode[]).map((m) => (
            <button
              key={m}
              onClick={() => switchMode(m)}
              className={`flex-1 py-2 rounded-lg text-xs font-bold transition-colors ${
                mode === m ? 'bg-white/20 text-white' : 'text-white/50 hover:text-white/80'
              }`}
            >
              {m === 'pomodoro' ? 'Focus' : m === 'shortBreak' ? 'Short' : 'Long'}
            </button>
          ))}
        </div>

        {/* Timer Circle */}
        <div className="relative w-64 h-64 mx-auto mb-8 flex items-center justify-center">
          <svg className="absolute inset-0 w-full h-full -rotate-90" viewBox="0 0 100 100">
            <circle
              className="text-white/10 stroke-current"
              strokeWidth="4"
              cx="50" cy="50" r="45" fill="none"
            />
            <circle
              className={`text-transparent stroke-[url(#gradient)] transition-all duration-1000 ease-linear`}
              strokeWidth="4"
              strokeDasharray="283"
              strokeDashoffset={283 - (283 * progressPercentage()) / 100}
              strokeLinecap="round"
              cx="50" cy="50" r="45" fill="none"
            />
            <defs>
              <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                {mode === 'pomodoro' && (
                  <>
                    <stop offset="0%" stopColor="#ef4444" />
                    <stop offset="100%" stopColor="#f97316" />
                  </>
                )}
                {mode === 'shortBreak' && (
                  <>
                    <stop offset="0%" stopColor="#4ade80" />
                    <stop offset="100%" stopColor="#10b981" />
                  </>
                )}
                {mode === 'longBreak' && (
                  <>
                    <stop offset="0%" stopColor="#60a5fa" />
                    <stop offset="100%" stopColor="#6366f1" />
                  </>
                )}
              </linearGradient>
            </defs>
          </svg>
          
          <div className="text-center z-10">
            <div className={`text-sm font-bold bg-gradient-to-r ${modeColors[mode]} bg-clip-text text-transparent mb-2`}>
              {modeLabels[mode]}
            </div>
            <div className="text-6xl font-black text-white tracking-tight font-mono">
              {formatTime(timeLeft)}
            </div>
            <div className="mt-2 text-white/50 text-xs">
              Sikl: #{pomodorosCompleted}
            </div>
          </div>
        </div>

        {/* Controls */}
        <div className="flex gap-4 justify-center">
          {!window.Telegram?.WebApp?.MainButton.isVisible && (
            <button
              onClick={toggleTimer}
              className={`px-8 py-4 rounded-2xl font-bold text-lg shadow-lg transition-transform hover:scale-105 active:scale-95 ${
                isActive 
                  ? 'bg-white/10 text-white' 
                  : `bg-gradient-to-r ${modeColors[mode]} text-white`
              }`}
            >
              {isActive ? 'PAUZA' : 'BOSHLASH'}
            </button>
          )}
          
          <button
            onClick={resetTimer}
            className="p-4 bg-white/5 rounded-2xl text-white/70 hover:text-white hover:bg-white/10 transition-colors"
          >
            🔄
          </button>
        </div>

        <p className="text-center text-white/40 text-xs mt-8">
          Diqqatni jamlash orqali XP ishlash imkoniyatiga egasiz! <br/>
          Har bir 100% tugatilgan fokus vaqti = +XP
        </p>
      </div>
    </div>
  )
}
