import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { gamesApi } from '../lib/api';

const N = 9;

// Helper: check if placing num at grid[r][c] is safe
function isSafe(grid: number[][], r: number, c: number, num: number) {
  for (let i = 0; i < N; i++) {
    if (grid[r][i] === num || grid[i][c] === num) return false;
  }
  const br = Math.floor(r / 3) * 3;
  const bc = Math.floor(c / 3) * 3;
  for (let i = br; i < br + 3; i++) {
    for (let j = bc; j < bc + 3; j++) {
      if (grid[i][j] === num) return false;
    }
  }
  return true;
}

// Generate fully solved Sudoku
function generateSudoku(): number[][] {
  const grid = Array.from({ length: N }, () => Array(N).fill(0));
  function fillGrid() {
    for (let r = 0; r < N; r++) {
      for (let c = 0; c < N; c++) {
        if (grid[r][c] === 0) {
          const nums = Array.from({ length: N }, (_, i) => i + 1).sort(() => Math.random() - 0.5);
          for (const num of nums) {
            if (isSafe(grid, r, c, num)) {
              grid[r][c] = num;
              if (fillGrid()) return true;
              grid[r][c] = 0;
            }
          }
          return false;
        }
      }
    }
    return true;
  }
  fillGrid();
  return grid;
}

// Remove cells based on difficulty
function reduceSudoku(grid: number[][], difficulty: 'easy' | 'medium' | 'hard') {
  const toRemove = difficulty === 'easy' ? 30 : difficulty === 'medium' ? 45 : 55;
  const copy = grid.map(r => [...r]);
  const cells = Array.from({ length: N * N }, (_, i) => i).sort(() => Math.random() - 0.5);
  for (let i = 0; i < toRemove; i++) {
    const idx = cells[i];
    copy[Math.floor(idx / N)][idx % N] = 0;
  }
  return copy;
}

export default function SudokuGamePage() {
  const navigate = useNavigate();

  const [gameState, setGameState] = useState<'menu' | 'playing' | 'won'>('menu');
  const [difficulty, setDifficulty] = useState<'easy' | 'medium' | 'hard'>('medium');
  const [solvedGrid, setSolvedGrid] = useState<number[][]>([]);
  const [initialGrid, setInitialGrid] = useState<number[][]>([]);
  const [grid, setGrid] = useState<number[][]>([]);
  const [selectedCell, setSelectedCell] = useState<{ r: number, c: number } | null>(null);
  const [mistakes, setMistakes] = useState(0);
  const [hints, setHints] = useState(3);
  const [timeStr, setTimeStr] = useState('0:00');
  let startTime = Date.now();

  const startGame = () => {
    const solved = generateSudoku();
    const reduced = reduceSudoku(solved, difficulty);
    setSolvedGrid(solved);
    setInitialGrid(reduced.map(r => [...r]));
    setGrid(reduced.map(r => [...r]));
    setMistakes(0);
    setHints(3);
    setGameState('playing');
    setSelectedCell(null);
  };

  useEffect(() => {
    if (gameState === 'playing') {
      const interval = setInterval(() => {
        const diff = Math.floor((Date.now() - startTime) / 1000);
        const m = Math.floor(diff / 60);
        const s = diff % 60;
        setTimeStr(`${m}:${s.toString().padStart(2, '0')}`);
      }, 1000);
      return () => clearInterval(interval);
    }
  }, [gameState, startTime]);

  const handleCellClick = (r: number, c: number) => {
    if (initialGrid[r][c] !== 0) return; // Cannot edit initial cells
    setSelectedCell({ r, c });
  };

  const checkWin = (currentGrid: number[][]) => {
    for (let r = 0; r < N; r++) {
      for (let c = 0; c < N; c++) {
        if (currentGrid[r][c] !== solvedGrid[r][c]) return false;
      }
    }
    return true;
  };

  const handleNumClick = (num: number) => {
    if (!selectedCell) return;
    const { r, c } = selectedCell;
    if (initialGrid[r][c] !== 0) return;

    const newGrid = [...grid];
    newGrid[r] = [...newGrid[r]];
    newGrid[r][c] = num;

    if (num !== 0 && num !== solvedGrid[r][c]) {
      setMistakes(prev => prev + 1);
    }

    setGrid(newGrid);

    if (checkWin(newGrid)) {
      setGameState('won');
      const pts = difficulty === 'easy' ? 100 : difficulty === 'medium' ? 200 : 300;
      gamesApi.saveResult({ game_name: 'sudoku', difficulty, score: Math.max(10, pts - mistakes * 20), won: true }).catch(console.error);
    }
  };

  const useHint = () => {
    if (hints <= 0) return;
    const emptyCells = [];
    for (let r = 0; r < N; r++) {
      for (let c = 0; c < N; c++) {
        if (grid[r][c] !== solvedGrid[r][c] && initialGrid[r][c] === 0) {
          emptyCells.push({ r, c });
        }
      }
    }
    if (emptyCells.length === 0) return;
    const { r, c } = emptyCells[Math.floor(Math.random() * emptyCells.length)];
    
    const newGrid = [...grid];
    newGrid[r] = [...newGrid[r]];
    newGrid[r][c] = solvedGrid[r][c];
    setGrid(newGrid);
    setHints(prev => prev - 1);

    if (checkWin(newGrid)) {
      setGameState('won');
      const pts = difficulty === 'easy' ? 100 : difficulty === 'medium' ? 200 : 300;
      gamesApi.saveResult({ game_name: 'sudoku', difficulty, score: Math.max(10, pts - mistakes * 20), won: true }).catch(console.error);
    }
  };


  return (
    <div className="p-4 pt-16 flex flex-col items-center justify-center min-h-[calc(100vh-60px)] relative">
      <motion.button
        onClick={() => navigate('/games')}
        className="absolute top-4 left-4 bg-white/10 hover:bg-white/20 border border-white/10 text-text-primary px-3 py-1.5 rounded-xl text-sm font-medium flex items-center justify-center"
        whileTap={{ scale: 0.95 }}
      >
        <span className="mr-1">←</span> Orqaga
      </motion.button>

      {gameState === 'menu' && (
        <motion.div 
          className="glass-card rounded-2xl p-6 w-full max-w-sm text-center"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div className="text-3xl mb-2">🧩</div>
          <h2 className="text-2xl font-bold text-text-primary mb-6">Sudoku</h2>
          
          <div className="mb-6">
            <p className="text-xs text-text-secondary uppercase tracking-wider mb-2 text-left">Qiyinlik darajasi</p>
            <div className="flex gap-2">
              <button 
                onClick={() => setDifficulty('easy')}
                className={`flex-1 py-2 rounded-xl text-sm font-semibold transition-colors border ${difficulty === 'easy' ? 'bg-green-500/20 border-green-500 text-green-400' : 'bg-white/5 border-white/10 text-white/70 hover:bg-white/10'}`}
              >
                Oson
              </button>
              <button 
                onClick={() => setDifficulty('medium')}
                className={`flex-1 py-2 rounded-xl text-sm font-semibold transition-colors border ${difficulty === 'medium' ? 'bg-yellow-500/20 border-yellow-500 text-yellow-400' : 'bg-white/5 border-white/10 text-white/70 hover:bg-white/10'}`}
              >
                O'rta
              </button>
              <button 
                onClick={() => setDifficulty('hard')}
                className={`flex-1 py-2 rounded-xl text-sm font-semibold transition-colors border ${difficulty === 'hard' ? 'bg-red-500/20 border-red-500 text-red-400' : 'bg-white/5 border-white/10 text-white/70 hover:bg-white/10'}`}
              >
                Qiyin
              </button>
            </div>
          </div>
          
          <motion.button
            onClick={startGame}
            className="w-full py-3 bg-gradient-to-r from-purple-500 to-indigo-500 text-white rounded-xl font-bold shadow-lg shadow-purple-500/20"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            🧩 O'yinni Boshlash
          </motion.button>
        </motion.div>
      )}

      {gameState === 'playing' && (
        <motion.div 
          className="flex flex-col items-center w-full max-w-sm"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          <div className="flex justify-between w-full mb-4 px-2">
            <div className="glass-card px-3 py-1.5 rounded-lg text-xs font-semibold text-white/80">
              ⏱ {timeStr}
            </div>
            <div className="glass-card px-3 py-1.5 rounded-lg text-xs font-semibold text-white/80">
              ❌ {mistakes}
            </div>
          </div>

          <div className="bg-purple-500/20 border border-purple-500/30 rounded-xl p-[2px] shadow-lg mb-4">
            <div className="grid grid-cols-9 gap-[1px] bg-purple-500/30">
              {grid.map((row, r) => 
                row.map((val, c) => {
                  const isSelected = selectedCell?.r === r && selectedCell?.c === c;
                  const isInitial = initialGrid[r][c] !== 0;
                  const isWrong = !isInitial && val !== 0 && val !== solvedGrid[r][c];
                  
                  // thick borders for 3x3 boxes
                  const pt = r % 3 === 0 && r !== 0 ? 'mt-[1px]' : '';
                  const pl = c % 3 === 0 && c !== 0 ? 'ml-[1px]' : '';

                  return (
                    <div
                      key={`${r}-${c}`}
                      onClick={() => handleCellClick(r, c)}
                      className={`w-8 h-8 flex items-center justify-center text-sm sm:text-base font-bold cursor-pointer transition-colors ${pt} ${pl}
                        ${isSelected ? 'bg-purple-500/40' : 'bg-[#0F172A] hover:bg-purple-500/20'}
                        ${isInitial ? 'text-purple-300' : isWrong ? 'text-red-400' : 'text-green-400'}
                      `}
                    >
                      {val === 0 ? '' : val}
                    </div>
                  );
                })
              )}
            </div>
          </div>

          <div className="grid grid-cols-5 gap-2 w-full mb-4">
            {[1, 2, 3, 4, 5, 6, 7, 8, 9, 0].map(n => (
              <button
                key={n}
                onClick={() => handleNumClick(n)}
                className={`glass-card h-10 rounded-xl text-lg font-bold transition-all active:scale-95
                  ${n === 0 ? 'text-red-400 bg-red-500/10' : 'text-white/90 hover:bg-white/10'}
                `}
              >
                {n === 0 ? '⌫' : n}
              </button>
            ))}
          </div>

          <div className="flex gap-2 w-full">
            <button 
              onClick={useHint} 
              disabled={hints <= 0}
              className="flex-1 glass-card py-2 rounded-xl text-sm font-semibold text-yellow-400 disabled:opacity-50"
            >
              💡 Hint ({hints})
            </button>
          </div>
        </motion.div>
      )}

      {gameState === 'won' && (
        <motion.div 
          className="glass-card rounded-2xl p-6 w-full max-w-sm text-center relative overflow-hidden"
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
        >
          <div className="text-4xl mb-2">🏆</div>
          <h2 className="text-2xl font-bold text-green-400 mb-1">Ajoyib!</h2>
          <p className="text-sm text-text-secondary mb-6">Siz sudokuni muvaffaqiyatli yechdingiz</p>
          
          <div className="flex justify-center gap-4 mb-6">
            <div className="bg-white/5 border border-white/10 rounded-xl p-3">
              <p className="text-xs text-text-secondary">Vaqt</p>
              <p className="text-lg font-bold text-white">{timeStr}</p>
            </div>
            <div className="bg-white/5 border border-white/10 rounded-xl p-3">
              <p className="text-xs text-text-secondary">Xatolar</p>
              <p className="text-lg font-bold text-white">{mistakes}</p>
            </div>
          </div>

          <motion.button
            onClick={() => setGameState('menu')}
            className="w-full py-3 bg-gradient-to-r from-green-500 to-emerald-500 text-white rounded-xl font-bold"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            Yangi O'yin
          </motion.button>
        </motion.div>
      )}
    </div>
  );
}
