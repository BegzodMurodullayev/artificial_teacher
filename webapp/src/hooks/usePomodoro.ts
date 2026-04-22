import { useState, useEffect, useRef, useCallback } from 'react'

export type TimerMode = 'pomodoro' | 'shortBreak' | 'longBreak'

interface PomodoroSettings {
  pomodoroTime: number // in minutes
  shortBreakTime: number // in minutes
  longBreakTime: number // in minutes
  longBreakInterval: number // number of pomodoros before long break
}

const DEFAULT_SETTINGS: PomodoroSettings = {
  pomodoroTime: 25,
  shortBreakTime: 5,
  longBreakTime: 15,
  longBreakInterval: 4,
}

export function usePomodoro(onComplete?: (mode: TimerMode) => void) {
  const [settings, setSettings] = useState<PomodoroSettings>(DEFAULT_SETTINGS)
  const [mode, setMode] = useState<TimerMode>('pomodoro')
  const [timeLeft, setTimeLeft] = useState(settings.pomodoroTime * 60)
  const [isActive, setIsActive] = useState(false)
  const [pomodorosCompleted, setPomodorosCompleted] = useState(0)

  // We use target time to ensure timer accuracy even if the browser throttles setTimeout
  const targetTimeRef = useRef<number | null>(null)
  const intervalRef = useRef<number | null>(null)

  const playAlarm = useCallback(() => {
    // Generate a simple beep using Web Audio API
    try {
      const AudioContext = window.AudioContext || (window as any).webkitAudioContext
      if (AudioContext) {
        const ctx = new AudioContext()
        const osc = ctx.createOscillator()
        const gainNode = ctx.createGain()
        osc.connect(gainNode)
        gainNode.connect(ctx.destination)
        
        osc.type = 'sine'
        osc.frequency.setValueAtTime(440, ctx.currentTime) // A4
        gainNode.gain.setValueAtTime(0.5, ctx.currentTime)
        
        osc.start(ctx.currentTime)
        osc.stop(ctx.currentTime + 0.5) // beep for 0.5s

        // Second beep
        const osc2 = ctx.createOscillator()
        const gainNode2 = ctx.createGain()
        osc2.connect(gainNode2)
        gainNode2.connect(ctx.destination)
        
        osc2.type = 'sine'
        osc2.frequency.setValueAtTime(440, ctx.currentTime + 0.6)
        gainNode2.gain.setValueAtTime(0.5, ctx.currentTime + 0.6)
        
        osc2.start(ctx.currentTime + 0.6)
        osc2.stop(ctx.currentTime + 1.1)
      }
    } catch (e) {
      console.warn("Audio Context not supported", e)
    }

    if ("Notification" in window && Notification.permission === "granted") {
      new Notification("Vaqt tugadi!", {
        body: mode === 'pomodoro' ? "Tanaffus vaqti keldi!" : "Diqqatni jamlash vaqti keldi!",
      })
    }
  }, [mode])

  const completeTimer = useCallback(() => {
    setIsActive(false)
    playAlarm()

    if (mode === 'pomodoro') {
      const newCount = pomodorosCompleted + 1
      setPomodorosCompleted(newCount)
      
      if (newCount % settings.longBreakInterval === 0) {
        switchMode('longBreak')
      } else {
        switchMode('shortBreak')
      }
    } else {
      switchMode('pomodoro')
    }
  }, [mode, pomodorosCompleted, settings.longBreakInterval, playAlarm])

  const switchMode = useCallback((newMode: TimerMode) => {
    setIsActive(false)
    setMode(newMode)
    let minutes = settings.pomodoroTime
    if (newMode === 'shortBreak') minutes = settings.shortBreakTime
    if (newMode === 'longBreak') minutes = settings.longBreakTime
    setTimeLeft(minutes * 60)
    targetTimeRef.current = null
  }, [settings])

  const tick = useCallback(() => {
    if (!targetTimeRef.current) return

    const now = Date.now()
    const remaining = Math.round((targetTimeRef.current - now) / 1000)

    if (remaining <= 0) {
      setTimeLeft(0)
      if (onComplete) onComplete(mode)
      completeTimer()
    } else {
      setTimeLeft(remaining)
    }
  }, [completeTimer])

  useEffect(() => {
    if (isActive) {
      if (!targetTimeRef.current) {
        targetTimeRef.current = Date.now() + timeLeft * 1000
      }
      intervalRef.current = window.setInterval(tick, 200) // check frequently for accuracy
    } else {
      if (intervalRef.current) clearInterval(intervalRef.current)
      targetTimeRef.current = null
    }

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [isActive, tick, timeLeft])

  const toggleTimer = () => setIsActive(!isActive)
  const resetTimer = () => switchMode(mode)

  const updateSettings = (newSettings: Partial<PomodoroSettings>) => {
    setSettings(prev => {
      const updated = { ...prev, ...newSettings }
      // If we update the current mode's setting and the timer isn't active, update timeLeft
      if (!isActive) {
        let minutes = updated.pomodoroTime
        if (mode === 'shortBreak') minutes = updated.shortBreakTime
        if (mode === 'longBreak') minutes = updated.longBreakTime
        setTimeLeft(minutes * 60)
      }
      return updated
    })
  }

  // Request notification permission
  useEffect(() => {
    if ("Notification" in window && Notification.permission !== "denied") {
      Notification.requestPermission()
    }
  }, [])

  return {
    timeLeft,
    isActive,
    mode,
    pomodorosCompleted,
    settings,
    toggleTimer,
    resetTimer,
    switchMode,
    updateSettings
  }
}
