import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { materialsApi, MaterialData } from '../lib/api'

type Tab = 'book' | 'fact' | 'quiz'

export default function LibraryPage() {
  const [activeTab, setActiveTab] = useState<Tab>('book')
  const [materials, setMaterials] = useState<MaterialData[]>([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')

  useEffect(() => {
    fetchMaterials()
  }, [activeTab])

  const fetchMaterials = async () => {
    setLoading(true)
    try {
      const data = await materialsApi.getMaterials(activeTab, 50, 0)
      setMaterials(data)
    } catch (error) {
      console.error('Failed to load materials', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!search.trim()) {
      fetchMaterials()
      return
    }
    setLoading(true)
    try {
      const data = await materialsApi.searchMaterials(search, activeTab)
      setMaterials(data)
    } catch (error) {
      console.error('Failed to search', error)
    } finally {
      setLoading(false)
    }
  }

  const tabLabels = {
    book: { label: 'Kitoblar', icon: '📚' },
    fact: { label: 'Faktlar', icon: '💡' },
    quiz: { label: 'Zakovat', icon: '🧠' },
  }

  return (
    <div className="page pb-20">
      <div className="flex items-center gap-3 mb-6">
        <h1 className="text-text-primary font-bold text-2xl">📚 Kutubxona</h1>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6 bg-white/5 p-1.5 rounded-2xl">
        {(Object.keys(tabLabels) as Tab[]).map((tab) => (
          <button
            key={tab}
            onClick={() => {
              setActiveTab(tab)
              setSearch('')
            }}
            className={`flex-1 py-2.5 rounded-xl text-sm font-semibold transition-all ${
              activeTab === tab
                ? 'bg-gradient-to-r from-blue-500 to-indigo-500 text-white shadow-lg'
                : 'text-text-secondary hover:text-white'
            }`}
          >
            {tabLabels[tab].icon} {tabLabels[tab].label}
          </button>
        ))}
      </div>

      {/* Search */}
      <form onSubmit={handleSearch} className="mb-6 relative">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={`${tabLabels[activeTab].label}dan izlash...`}
          className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-white/40 focus:outline-none focus:border-blue-500 transition-colors"
        />
        <button
          type="submit"
          className="absolute right-3 top-1/2 -translate-y-1/2 text-white/60 hover:text-white"
        >
          🔍
        </button>
      </form>

      {/* Content Grid */}
      {loading ? (
        <div className="flex justify-center py-10">
          <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <AnimatePresence mode="popLayout">
            {materials.length === 0 && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="col-span-full text-center py-10 text-white/50"
              >
                Hech narsa topilmadi 😔
              </motion.div>
            )}
            {materials.map((m) => (
              <motion.div
                layout
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                key={m.id}
                className="bg-white/5 border border-white/10 rounded-2xl p-5 hover:bg-white/10 transition-colors"
              >
                <div className="flex justify-between items-start mb-2">
                  <span className="text-xs font-bold px-2 py-1 bg-blue-500/20 text-blue-400 rounded-lg uppercase tracking-wider">
                    {m.category || activeTab}
                  </span>
                  {m.author && (
                    <span className="text-xs text-white/50 bg-white/5 px-2 py-1 rounded-lg">
                      ✍️ {m.author}
                    </span>
                  )}
                </div>
                
                <h3 className="text-lg font-bold text-white mb-2 leading-tight">
                  {m.title}
                </h3>
                
                {m.description && (
                  <p className="text-sm text-white/70 line-clamp-3 mb-4">
                    {m.description}
                  </p>
                )}

                {/* Show quiz answer if it's a quiz, hidden by default maybe? */}
                {m.material_type === 'quiz' && m.content && (
                  <div className="mt-4 pt-4 border-t border-white/10">
                    <details className="text-sm">
                      <summary className="text-blue-400 cursor-pointer font-semibold outline-none select-none">
                        Javobni ko'rish
                      </summary>
                      <div className="mt-2 p-3 bg-green-500/10 border border-green-500/20 rounded-xl text-green-300 font-medium">
                        {typeof m.content === 'string' ? JSON.parse(m.content)?.javob : m.content?.javob}
                      </div>
                    </details>
                  </div>
                )}
                
                {m.material_type === 'fact' && m.content && (
                  <div className="mt-3 pt-3 border-t border-white/10 text-xs text-white/60">
                    <p><strong>Yil:</strong> {typeof m.content === 'string' ? JSON.parse(m.content)?.year : m.content?.year}</p>
                    <p><strong>Hudud:</strong> {typeof m.content === 'string' ? JSON.parse(m.content)?.region : m.content?.region}</p>
                  </div>
                )}
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}
    </div>
  )
}
