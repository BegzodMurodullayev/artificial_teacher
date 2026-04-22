/**
 * XOGamePage — X va O o'yini (Tic-Tac-Toe)
 * React port of the Electron-based game from bolimlar test/oyinlar/x_o/
 * Supports: 2-player, AI (easy/medium/hard), board sizes 3x3, 4x4, 5x5
 */

import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { gamesApi } from '../lib/api'

type Mark = 'X' | 'O' | ''
type Screen = 'who' | 'difficulty' | 'size' | 'game'
type Mode = '2player' | 'ai'
type Difficulty = 'easy' | 'medium' | 'hard'

// ── AI Logic ──────────────────────────────────────────────────────────────────
function checkWinner(board: Mark[], n: number, mark: Mark): number[] | null {
  // Rows
  for (let r = 0; r < n; r++) {
    const row = Array.from({ length: n }, (_, c) => r * n + c)
    if (row.every(i => board[i] === mark)) return row
  }
  // Cols
  for (let c = 0; c < n; c++) {
    const col = Array.from({ length: n }, (_, r) => r * n + c)
    if (col.every(i => board[i] === mark)) return col
  }
  // Diagonals
  const d1 = Array.from({ length: n }, (_, i) => i * n + i)
  const d2 = Array.from({ length: n }, (_, i) => i * n + (n - 1 - i))
  if (d1.every(i => board[i] === mark)) return d1
  if (d2.every(i => board[i] === mark)) return d2
  return null
}

function minimax(
  board: Mark[], n: number, depth: number, isMax: boolean, alpha: number, beta: number
): number {
  if (checkWinner(board, n, 'O')) return 10 - depth
  if (checkWinner(board, n, 'X')) return depth - 10
  if (board.every(v => v)) return 0

  if (isMax) {
    let best = -Infinity
    for (let i = 0; i < n * n; i++) {
      if (!board[i]) {
        board[i] = 'O'
        best = Math.max(best, minimax(board, n, depth + 1, false, alpha, beta))
        board[i] = ''
        alpha = Math.max(alpha, best)
        if (beta <= alpha) break
      }
    }
    return best
  } else {
    let best = Infinity
    for (let i = 0; i < n * n; i++) {
      if (!board[i]) {
        board[i] = 'X'
        best = Math.min(best, minimax(board, n, depth + 1, true, alpha, beta))
        board[i] = ''
        beta = Math.min(beta, best)
        if (beta <= alpha) break
      }
    }
    return best
  }
}

function getAIMove(board: Mark[], n: number, difficulty: Difficulty): number {
  const empty = board.map((v, i) => v ? null : i).filter(v => v !== null) as number[]
  if (!empty.length) return -1

  if (difficulty === 'easy') {
    return empty[Math.floor(Math.random() * empty.length)]
  }

  if (n === 3 || difficulty === 'hard') {
    // Full minimax for 3x3, smart for bigger
    if (n === 3) {
      let best = -Infinity, move = empty[0]
      const b = [...board]
      for (const i of empty) {
        b[i] = 'O'
        const score = minimax(b, n, 0, false, -Infinity, Infinity)
        b[i] = ''
        if (score > best) { best = score; move = i }
      }
      return move
    }
  }

  // Smart heuristic for 4x4, 5x5
  const b = [...board]
  // Win
  for (const i of empty) { b[i] = 'O'; if (checkWinner(b, n, 'O')) { b[i] = ''; return i } b[i] = '' }
  // Block
  for (const i of empty) { b[i] = 'X'; if (checkWinner(b, n, 'X')) { b[i] = ''; return i } b[i] = '' }
  // Center
  const center = Math.floor(n / 2) * n + Math.floor(n / 2)
  if (!board[center]) return center
  // Random
  return empty[Math.floor(Math.random() * empty.length)]
}

// ── Component ─────────────────────────────────────────────────────────────────
export default function XOGamePage() {
  const navigate = useNavigate()
  const playerName = window.Telegram?.WebApp?.initDataUnsafe?.user?.first_name ?? "O'yinchi"

  const [screen, setScreen] = useState<Screen>('who')
  const [mode, setMode] = useState<Mode>('ai')
  const [difficulty, setDifficulty] = useState<Difficulty>('medium')
  const [n, setN] = useState(3)
  const [board, setBoard] = useState<Mark[]>([])
  const [current, setCurrent] = useState<Mark>('X')
  const [gameOver, setGameOver] = useState(false)
  const [winner, setWinner] = useState<Mark | 'draw' | null>(null)
  const [winCells, setWinCells] = useState<number[]>([])
  const [scores, setScores] = useState({ X: 0, O: 0, draw: 0 })
  const [moveCount, setMoveCount] = useState(0)
  const [result, setResult] = useState<{ emoji: string; title: string; sub: string } | null>(null)

  const startGame = useCallback((size = n) => {
    setBoard(Array(size * size).fill(''))
    setCurrent('X')
    setGameOver(false)
    setWinner(null)
    setWinCells([])
    setMoveCount(0)
    setResult(null)
    setScreen('game')
  }, [n])

  const handleCell = useCallback((idx: number) => {
    if (gameOver || board[idx] || (mode === 'ai' && current === 'O')) return

    const newBoard = [...board]
    newBoard[idx] = current
    const newMove = moveCount + 1
    setMoveCount(newMove)

    const winLine = checkWinner(newBoard, n, current)
    if (winLine) {
      setWinCells(winLine)
      setBoard(newBoard)
      setGameOver(true)
      setWinner(current)
      setScores(s => ({ ...s, [current]: s[current as keyof typeof s] + 1 }))
      if (current === 'X') {
        const pts = mode === 'ai' ? (difficulty === 'easy' ? 15 : difficulty === 'medium' ? 30 : 50) : 10
        gamesApi.saveResult({ game_name: 'tic-tac-toe', difficulty: mode === 'ai' ? difficulty : 'easy', score: pts, won: true }).catch(console.error)
      } else {
        gamesApi.saveResult({ game_name: 'tic-tac-toe', difficulty: mode === 'ai' ? difficulty : 'easy', score: 0, won: false }).catch(console.error)
      }
      setTimeout(() => {
        const nom = current === 'X' ? playerName : (mode === 'ai' ? 'AI' : "2-O'yinchi")
        setResult({ emoji: '🏆', title: `${nom} g'alaba qozondi!`, sub: `${current} belgisi yutdi!` })
      }, 600)
      return
    }
    if (newBoard.every(v => v)) {
      setBoard(newBoard)
      setGameOver(true)
      setWinner('draw')
      setScores(s => ({ ...s, draw: s.draw + 1 }))
      gamesApi.saveResult({ game_name: 'tic-tac-toe', difficulty: mode === 'ai' ? difficulty : 'easy', score: 5, won: false }).catch(console.error)
      setTimeout(() => {
        setResult({ emoji: '🤝', title: 'Durrang!', sub: 'Hech kim yutmadi!' })
      }, 400)
      return
    }

    const nextMark: Mark = current === 'X' ? 'O' : 'X'
    setBoard(newBoard)
    setCurrent(nextMark)

    if (mode === 'ai' && nextMark === 'O') {
      setTimeout(() => {
        const aiIdx = getAIMove(newBoard, n, difficulty)
        if (aiIdx === -1) return
        const afterAI = [...newBoard]
        afterAI[aiIdx] = 'O'
        const aiWin = checkWinner(afterAI, n, 'O')
        if (aiWin) {
          setWinCells(aiWin)
          setBoard(afterAI)
          setGameOver(true)
          setWinner('O')
          setScores(s => ({ ...s, O: s.O + 1 }))
          gamesApi.saveResult({ game_name: 'tic-tac-toe', difficulty: mode === 'ai' ? difficulty : 'easy', score: 0, won: false }).catch(console.error)
          setTimeout(() => setResult({ emoji: '🤖', title: 'AI g\'alaba qildi!', sub: 'Qayta harakat qiling!' }), 500)
          return
        }
        if (afterAI.every(v => v)) {
          setBoard(afterAI)
          setGameOver(true)
          setWinner('draw')
          setScores(s => ({ ...s, draw: s.draw + 1 }))
          gamesApi.saveResult({ game_name: 'tic-tac-toe', difficulty: mode === 'ai' ? difficulty : 'easy', score: 5, won: false }).catch(console.error)
          setTimeout(() => setResult({ emoji: '🤝', title: 'Durrang!', sub: 'Hech kim yutmadi!' }), 400)
          return
        }
        setBoard(afterAI)
        setCurrent('X')
      }, 400)
    }
  }, [board, current, gameOver, mode, difficulty, n, moveCount, playerName])

  // Cell size based on board size
  const cellSize = n === 3 ? 80 : n === 4 ? 68 : 56
  const fontSize = n === 3 ? '32px' : n === 4 ? '26px' : '20px'

  const statusText = () => {
    if (gameOver) return winner === 'draw' ? '🤝 Durrang!' : `${winner === 'X' ? `${playerName} ❌` : (mode === 'ai' ? '🤖 AI' : "2-O'yinchi ⭕")} g'alaba!`
    if (mode === 'ai' && current === 'O') return '🤖 AI o\'ylayapti...'
    return current === 'X' ? `${playerName} ❌ navbati` : "2-O'yinchi ⭕ navbati"
  }

  return (
    <div className="page" style={{ paddingBottom: '16px' }}>
      <AnimatePresence mode="wait">

        {/* ── WHO TO PLAY ── */}
        {screen === 'who' && (
          <motion.div key="who" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }}>
            <div className="flex items-center gap-3 mb-6">
              <button onClick={() => navigate('/games')} style={{ background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.12)', color: 'rgba(180,200,255,0.8)', padding: '6px 12px', borderRadius: '8px', fontSize: '13px', cursor: 'pointer' }}>← Orqaga</button>
              <h1 className="text-text-primary font-bold text-xl">❌⭕ X va O</h1>
            </div>
            <p className="text-text-muted text-sm mb-4">Kim bilan o'ynaysiz?</p>
            <div className="grid grid-cols-2 gap-3">
              {[
                { id: '2player' as Mode, icon: '👥', title: '2 O\'yinchi', desc: 'Birgalikda' },
                { id: 'ai' as Mode, icon: '🤖', title: 'AI bilan', desc: 'Off-line AI' },
              ].map(opt => (
                <motion.button key={opt.id} whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}
                  onClick={() => { setMode(opt.id); opt.id === 'ai' ? setScreen('difficulty') : setScreen('size') }}
                  style={{ background: 'rgba(15,20,50,0.8)', border: '1px solid rgba(255,255,255,0.12)', borderRadius: '18px', padding: '24px 16px', cursor: 'pointer', textAlign: 'center' }}>
                  <div style={{ fontSize: '32px', marginBottom: '8px' }}>{opt.icon}</div>
                  <div style={{ color: '#fff', fontWeight: 700, fontSize: '15px' }}>{opt.title}</div>
                  <div style={{ color: 'rgba(180,200,255,0.5)', fontSize: '12px' }}>{opt.desc}</div>
                </motion.button>
              ))}
            </div>
          </motion.div>
        )}

        {/* ── DIFFICULTY ── */}
        {screen === 'difficulty' && (
          <motion.div key="diff" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }}>
            <div className="flex items-center gap-3 mb-6">
              <button onClick={() => setScreen('who')} style={{ background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.12)', color: 'rgba(180,200,255,0.8)', padding: '6px 12px', borderRadius: '8px', fontSize: '13px', cursor: 'pointer' }}>← Orqaga</button>
              <h1 className="text-text-primary font-bold text-xl">🤖 AI Darajasi</h1>
            </div>
            <div className="grid grid-cols-1 gap-3">
              {[
                { id: 'easy' as Difficulty, icon: '😊', color: '#4ade80', title: 'Oson', desc: 'Tasodifiy harakat' },
                { id: 'medium' as Difficulty, icon: '🧠', color: '#fbbf24', title: "O'rta", desc: 'Aqlli harakat' },
                { id: 'hard' as Difficulty, icon: '🤖', color: '#f87171', title: 'Qiyin', desc: 'Minimax AI' },
              ].map(opt => (
                <motion.button key={opt.id} whileHover={{ x: 4 }} whileTap={{ scale: 0.98 }}
                  onClick={() => { setDifficulty(opt.id); setScreen('size') }}
                  style={{ background: 'rgba(15,20,50,0.8)', border: `1px solid ${opt.color}44`, borderRadius: '16px', padding: '16px 20px', cursor: 'pointer', textAlign: 'left', display: 'flex', alignItems: 'center', gap: '14px' }}>
                  <span style={{ fontSize: '28px' }}>{opt.icon}</span>
                  <div>
                    <div style={{ color: '#fff', fontWeight: 700, fontSize: '15px' }}>{opt.title}</div>
                    <div style={{ color: 'rgba(180,200,255,0.5)', fontSize: '12px' }}>{opt.desc}</div>
                  </div>
                </motion.button>
              ))}
            </div>
          </motion.div>
        )}

        {/* ── BOARD SIZE ── */}
        {screen === 'size' && (
          <motion.div key="size" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }}>
            <div className="flex items-center gap-3 mb-6">
              <button onClick={() => setScreen(mode === 'ai' ? 'difficulty' : 'who')} style={{ background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.12)', color: 'rgba(180,200,255,0.8)', padding: '6px 12px', borderRadius: '8px', fontSize: '13px', cursor: 'pointer' }}>← Orqaga</button>
              <h1 className="text-text-primary font-bold text-xl">📐 Taxta hajmi</h1>
            </div>
            <div className="grid grid-cols-3 gap-3">
              {[3, 4, 5].map(sz => (
                <motion.button key={sz} whileHover={{ scale: 1.05, y: -3 }} whileTap={{ scale: 0.95 }}
                  onClick={() => { setN(sz); startGame(sz) }}
                  style={{ background: 'rgba(15,20,50,0.8)', border: '1px solid rgba(96,165,250,0.3)', borderRadius: '16px', padding: '20px 10px', cursor: 'pointer', textAlign: 'center' }}>
                  <div style={{ fontSize: '28px', marginBottom: '6px' }}>{sz === 3 ? '🟦' : sz === 4 ? '🟪' : '🟧'}</div>
                  <div style={{ color: '#fff', fontWeight: 700 }}>{sz} × {sz}</div>
                  <div style={{ color: 'rgba(180,200,255,0.5)', fontSize: '11px' }}>{sz === 3 ? 'Klassik' : sz === 4 ? 'Qiziqroq' : 'Murakkab'}</div>
                </motion.button>
              ))}
            </div>
          </motion.div>
        )}

        {/* ── GAME ── */}
        {screen === 'game' && (
          <motion.div key="game" initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }}>
            {/* Scoreboard */}
            <div className="flex justify-between items-center mb-4">
              <div style={{ background: 'rgba(248,113,113,0.15)', border: '1px solid rgba(248,113,113,0.3)', borderRadius: '14px', padding: '10px 16px', textAlign: 'center', flex: 1, marginRight: '8px', opacity: current === 'X' || gameOver ? 1 : 0.5 }}>
                <div style={{ fontSize: '11px', color: 'rgba(248,113,113,0.7)' }}>{playerName}</div>
                <div style={{ fontSize: '24px', fontWeight: 800, color: '#f87171' }}>{scores.X}</div>
                <div style={{ fontSize: '20px' }}>❌</div>
              </div>
              <div style={{ textAlign: 'center', padding: '0 8px' }}>
                <div style={{ fontSize: '11px', color: 'rgba(180,200,255,0.5)' }}>Hamla</div>
                <div style={{ fontSize: '18px', fontWeight: 800, color: '#fff' }}>{moveCount}</div>
                <div style={{ fontSize: '11px', color: 'rgba(180,200,255,0.4)' }}>Draw:{scores.draw}</div>
              </div>
              <div style={{ background: 'rgba(96,165,250,0.15)', border: '1px solid rgba(96,165,250,0.3)', borderRadius: '14px', padding: '10px 16px', textAlign: 'center', flex: 1, marginLeft: '8px', opacity: current === 'O' || gameOver ? 1 : 0.5 }}>
                <div style={{ fontSize: '11px', color: 'rgba(96,165,250,0.7)' }}>{mode === 'ai' ? 'AI' : "2-O'yinchi"}</div>
                <div style={{ fontSize: '24px', fontWeight: 800, color: '#60a5fa' }}>{scores.O}</div>
                <div style={{ fontSize: '20px' }}>⭕</div>
              </div>
            </div>

            {/* Status */}
            <div style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px', padding: '10px', textAlign: 'center', fontSize: '14px', color: 'rgba(200,220,255,0.9)', marginBottom: '16px' }}>
              {statusText()}
            </div>

            {/* Board */}
            <div style={{ display: 'flex', justifyContent: 'center' }}>
              <div style={{ display: 'grid', gridTemplateColumns: `repeat(${n}, ${cellSize}px)`, gap: '8px' }}>
                {board.map((cell, idx) => (
                  <motion.button
                    key={idx}
                    onClick={() => handleCell(idx)}
                    whileHover={!cell && !gameOver ? { scale: 1.07 } : {}}
                    whileTap={!cell && !gameOver ? { scale: 0.93 } : {}}
                    style={{
                      width: cellSize, height: cellSize,
                      borderRadius: '14px',
                      background: winCells.includes(idx) ? 'rgba(74,222,128,0.2)' : 'rgba(255,255,255,0.06)',
                      border: winCells.includes(idx) ? '1px solid #4ade80' : '1px solid rgba(255,255,255,0.1)',
                      cursor: !cell && !gameOver ? 'pointer' : 'default',
                      fontSize, fontWeight: 900,
                      color: cell === 'X' ? '#f87171' : '#60a5fa',
                      boxShadow: winCells.includes(idx) ? '0 0 20px rgba(74,222,128,0.3)' : 'none',
                      transition: 'all 0.2s',
                    }}
                  >
                    <motion.span
                      initial={cell ? { scale: 0 } : {}}
                      animate={cell ? { scale: 1 } : {}}
                      transition={{ type: 'spring', stiffness: 500, damping: 15 }}
                    >
                      {cell === 'X' ? '✕' : cell === 'O' ? '◯' : ''}
                    </motion.span>
                  </motion.button>
                ))}
              </div>
            </div>

            {/* Buttons */}
            <div className="flex gap-3 mt-4">
              <button onClick={() => { startGame(n); setScores({ X: 0, O: 0, draw: 0 }) }} style={{ flex: 1, padding: '12px', borderRadius: '14px', border: 'none', background: 'linear-gradient(135deg, #3b82f6, #7c3aed)', color: '#fff', fontWeight: 700, cursor: 'pointer', fontSize: '14px' }}>
                🔄 Yangi o'yin
              </button>
              <button onClick={() => setScreen('who')} style={{ padding: '12px 16px', borderRadius: '14px', border: '1px solid rgba(255,255,255,0.15)', background: 'rgba(255,255,255,0.07)', color: 'rgba(200,220,255,0.8)', cursor: 'pointer', fontSize: '14px' }}>
                ←
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Result Modal ── */}
      <AnimatePresence>
        {result && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(8px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}
          >
            <motion.div
              initial={{ scale: 0.5, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ type: 'spring', stiffness: 400, damping: 20 }}
              style={{ background: 'rgba(10,15,40,0.98)', border: '1px solid rgba(255,255,255,0.15)', borderRadius: '28px', padding: '36px 32px', textAlign: 'center', minWidth: '280px' }}
            >
              <div style={{ fontSize: '52px', marginBottom: '12px' }}>{result.emoji}</div>
              <div style={{ fontSize: '20px', fontWeight: 800, color: '#fff', marginBottom: '8px' }}>{result.title}</div>
              <div style={{ fontSize: '13px', color: 'rgba(180,210,255,0.7)', marginBottom: '24px' }}>{result.sub}</div>
              <div className="flex gap-3 justify-center">
                <button onClick={() => startGame(n)} style={{ padding: '12px 24px', borderRadius: '14px', border: 'none', background: 'linear-gradient(135deg, #3b82f6, #7c3aed)', color: '#fff', fontWeight: 700, cursor: 'pointer' }}>🔄 Qayta</button>
                <button onClick={() => { setResult(null); setScreen('who') }} style={{ padding: '12px 20px', borderRadius: '14px', border: '1px solid rgba(255,255,255,0.15)', background: 'rgba(255,255,255,0.08)', color: 'rgba(200,220,255,0.8)', cursor: 'pointer' }}>← Menyu</button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
