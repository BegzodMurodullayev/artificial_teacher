import { useEffect, useMemo, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useSearchParams } from 'react-router-dom'

import { materialsApi, MaterialData } from '../lib/api'
import { useTranslation } from '../lib/i18n'
import { usePlan } from '@/store/useStore'

type Tab = 'book' | 'fact' | 'quiz' | 'guide'

const TAB_ORDER: Tab[] = ['book', 'fact', 'quiz', 'guide']
const PLAN_RANK: Record<string, number> = {
  free: 0,
  standard: 1,
  pro: 2,
  premium: 3,
}
const TIER_RANK: Record<string, number> = {
  free: 0,
  standard: 1,
  pro: 2,
  premium: 3,
}

function normalizeTab(value: string | null): Tab {
  return TAB_ORDER.includes(value as Tab) ? (value as Tab) : 'book'
}

function getTier(content: any): string {
  return String(content?.tier || 'free').toLowerCase()
}

function canAccess(planName: string, tier: string): boolean {
  return (PLAN_RANK[planName] ?? 0) >= (TIER_RANK[tier] ?? 0)
}

function parseArray(value: unknown): string[] {
  return Array.isArray(value) ? value.map((item) => String(item)) : []
}

export default function LibraryPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [activeTab, setActiveTab] = useState<Tab>(normalizeTab(searchParams.get('tab')))
  const [materials, setMaterials] = useState<MaterialData[]>([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const t = useTranslation()
  const plan = usePlan()

  useEffect(() => {
    setActiveTab(normalizeTab(searchParams.get('tab')))
  }, [searchParams])

  useEffect(() => {
    void fetchMaterials(activeTab)
  }, [activeTab])

  const tabLabels = useMemo(() => ({
    book: { label: t('lib_books'), icon: '📚' },
    fact: { label: t('lib_facts'), icon: '💡' },
    quiz: { label: t('lib_quiz'), icon: '🧠' },
    guide: { label: "Qo'llanmalar", icon: '🗂' },
  }), [t])

  async function fetchMaterials(tab: Tab) {
    setLoading(true)
    try {
      const data = await materialsApi.getMaterials(tab, 50, 0)
      setMaterials(data)
    } catch (error) {
      console.error('Failed to load materials', error)
      setMaterials([])
    } finally {
      setLoading(false)
    }
  }

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    if (!search.trim()) {
      await fetchMaterials(activeTab)
      return
    }

    setLoading(true)
    try {
      const data = await materialsApi.searchMaterials(search, activeTab)
      setMaterials(data)
    } catch (error) {
      console.error('Failed to search materials', error)
      setMaterials([])
    } finally {
      setLoading(false)
    }
  }

  function switchTab(tab: Tab) {
    setSearch('')
    setActiveTab(tab)
    setSearchParams({ tab })
  }

  return (
    <div className="page pb-20">
      <div className="flex items-center justify-between gap-3 mb-6">
        <div>
          <h1 className="text-text-primary font-bold text-2xl">📚 {t('lib_title')}</h1>
          <p className="text-white/60 text-sm">
            {plan.display_name || 'Free'} • {t('lib_desc')}
          </p>
        </div>
        <div className="rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-xs text-white/70 uppercase tracking-[0.2em]">
          {plan.name || 'free'}
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-6 bg-white/5 p-1.5 rounded-2xl">
        {TAB_ORDER.map((tab) => (
          <button
            key={tab}
            onClick={() => switchTab(tab)}
            className={`py-2.5 rounded-xl text-sm font-semibold transition-all ${
              activeTab === tab
                ? 'bg-gradient-to-r from-blue-500 to-indigo-500 text-white shadow-lg shadow-blue-500/20'
                : 'text-text-secondary hover:text-white'
            }`}
          >
            {tabLabels[tab].icon} {tabLabels[tab].label}
          </button>
        ))}
      </div>

      <form onSubmit={handleSearch} className="mb-6 relative">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={t('lib_search', { x: tabLabels[activeTab].label.toLowerCase() })}
          className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-white/40 focus:outline-none focus:border-blue-500 focus:bg-white/10 transition-all shadow-inner"
        />
        <button
          type="submit"
          className="absolute right-3 top-1/2 -translate-y-1/2 text-white/60 hover:text-white"
        >
          🔍
        </button>
      </form>

      {loading ? (
        <div className="flex justify-center py-10">
          <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <AnimatePresence mode="popLayout">
            {materials.length === 0 && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="col-span-full text-center py-10 text-white/50 bg-white/5 rounded-2xl border border-white/10"
              >
                {t('lib_not_found')}
              </motion.div>
            )}

            {materials.map((material) => {
              const content = material.content ?? {}
              const tier = getTier(content)
              const locked = !canAccess(plan.name || 'free', tier)
              const bullets = parseArray(content?.bullets)
              const modules = parseArray(content?.modules)
              const variants = parseArray(content?.variantlar)

              return (
                <motion.div
                  layout
                  initial={{ opacity: 0, scale: 0.94 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.94 }}
                  key={material.id}
                  className={`rounded-2xl p-5 border transition-colors ${
                    locked
                      ? 'bg-gradient-to-br from-white/5 to-white/[0.03] border-amber-400/20'
                      : 'bg-white/5 border-white/10 hover:bg-white/10'
                  }`}
                >
                  <div className="flex justify-between items-start gap-3 mb-3">
                    <div className="flex flex-wrap gap-2">
                      <span className="text-xs font-bold px-2 py-1 bg-blue-500/20 text-blue-300 rounded-lg uppercase tracking-wider">
                        {material.category || activeTab}
                      </span>
                      <span className={`text-xs font-bold px-2 py-1 rounded-lg uppercase tracking-wider ${
                        tier === 'premium'
                          ? 'bg-amber-500/20 text-amber-300'
                          : tier === 'pro'
                            ? 'bg-fuchsia-500/20 text-fuchsia-300'
                            : tier === 'standard'
                              ? 'bg-emerald-500/20 text-emerald-300'
                              : 'bg-white/10 text-white/70'
                      }`}>
                        {tier}
                      </span>
                    </div>
                    {locked && <span className="text-lg">🔒</span>}
                  </div>

                  <h3 className="text-lg font-bold text-white mb-2 leading-tight">
                    {material.title}
                  </h3>

                  <p className={`text-sm mb-4 ${locked ? 'text-white/55' : 'text-white/70'}`}>
                    {material.description}
                  </p>

                  {content?.preview && (
                    <div className="rounded-xl border border-white/10 bg-black/20 p-3 text-sm text-white/75 mb-3">
                      <span className="text-white/45 uppercase tracking-[0.2em] text-[10px]">Preview</span>
                      <p className="mt-1">{String(content.preview)}</p>
                    </div>
                  )}

                  {!locked && bullets.length > 0 && (
                    <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3 mb-3">
                      {bullets.map((item, index) => (
                        <p key={`${material.id}-bullet-${index}`} className="text-sm text-white/80">
                          • {item}
                        </p>
                      ))}
                    </div>
                  )}

                  {!locked && modules.length > 0 && (
                    <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3 mb-3">
                      <p className="text-[10px] uppercase tracking-[0.2em] text-white/45 mb-2">Modullar</p>
                      {modules.map((item, index) => (
                        <p key={`${material.id}-module-${index}`} className="text-sm text-white/80">
                          • {item}
                        </p>
                      ))}
                    </div>
                  )}

                  {!locked && material.material_type === 'fact' && (
                    <div className="mt-3 pt-3 border-t border-white/10 text-xs text-white/60 flex gap-4">
                      <p><strong className="text-white/80">{t('lib_year')}:</strong> {String(content?.year || '-')}</p>
                      <p><strong className="text-white/80">{t('lib_region')}:</strong> {String(content?.region || '-')}</p>
                    </div>
                  )}

                  {!locked && material.material_type === 'quiz' && (
                    <div className="mt-4 pt-4 border-t border-white/10">
                      <p className="text-sm text-white/80 mb-2">{String(content?.savol || material.description || '')}</p>
                      {variants.length > 0 && (
                        <div className="grid gap-2 mb-3">
                          {variants.map((variant, index) => (
                            <div key={`${material.id}-variant-${index}`} className="rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2 text-sm text-white/70">
                              {variant}
                            </div>
                          ))}
                        </div>
                      )}
                      <details className="text-sm group">
                        <summary className="text-blue-400 hover:text-blue-300 cursor-pointer font-semibold outline-none select-none transition-colors">
                          {t('lib_show_answer')}
                        </summary>
                        <div className="mt-3 p-3 bg-gradient-to-br from-green-500/10 to-green-500/5 border border-green-500/20 rounded-xl text-green-300">
                          <p className="font-semibold">{String(content?.javob || '-')}</p>
                          {content?.izoh && <p className="mt-2 text-sm text-green-200/80">{String(content.izoh)}</p>}
                        </div>
                      </details>
                    </div>
                  )}

                  {locked && (
                    <div className="rounded-xl border border-amber-400/20 bg-amber-500/10 p-3 text-sm text-amber-100">
                      <p className="font-semibold mb-1">Bu material sizning tarifda yopiq.</p>
                      <p>{String(content?.cta || "Ko'proq material uchun tarifni oshiring.")}</p>
                    </div>
                  )}
                </motion.div>
              )
            })}
          </AnimatePresence>
        </div>
      )}
    </div>
  )
}
