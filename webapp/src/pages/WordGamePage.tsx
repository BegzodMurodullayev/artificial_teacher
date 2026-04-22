/**
 * WordGamePage — So'z Topish o'yini (Tezda)
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'

export default function WordGamePage() {
  const navigate = useNavigate()
  const [gameState] = useState<'menu'>('menu')

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
          <div className="text-4xl mb-2">🔤</div>
          <h2 className="text-2xl font-bold text-text-primary mb-2">So'z Topish</h2>
          <p className="text-sm text-text-secondary mb-6">
            Ushbu o'yin tez kunda WebApp orqali to'liq ishga tushadi! Ungacha bot orqali <b>/soztopish</b> buyrug'idan foydalaning.
          </p>
          
          <motion.button
            onClick={() => window.Telegram?.WebApp?.close?.()}
            className="w-full py-3 bg-gradient-to-r from-orange-500 to-amber-500 text-white rounded-xl font-bold shadow-lg shadow-orange-500/20"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            Botga qaytish
          </motion.button>
        </motion.div>
      )}
    </div>
  )
}
