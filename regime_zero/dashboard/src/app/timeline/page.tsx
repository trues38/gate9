"use client"

import { useState, useRef, useEffect } from "react"
import { motion, useScroll, useTransform, AnimatePresence } from "framer-motion"
import { ChevronLeft, ChevronRight, Zap, TrendingUp, TrendingDown, AlertTriangle } from "lucide-react"
import Link from "next/link"

// 샘플 레짐 데이터 (실제로는 API에서)
const REGIMES = [
  {
    id: 1,
    year: "2008",
    name: "Global Financial Crisis",
    family: "Risk-Off Capitulation",
    color: "#ef4444",
    icon: AlertTriangle,
    vix: 80.9,
    description: "리먼 브라더스 파산, 글로벌 신용경색",
    winners: ["금", "국채"],
    losers: ["금융주", "부동산"],
  },
  {
    id: 2,
    year: "2012",
    name: "Post-Crisis Recovery",
    family: "Goldilocks Equilibrium",
    color: "#22c55e",
    icon: TrendingUp,
    vix: 14.2,
    description: "QE 효과, 저금리 환경에서 위험자산 랠리",
    winners: ["기술주", "소비재"],
    losers: ["금", "에너지"],
  },
  {
    id: 3,
    year: "2015",
    name: "China Slowdown Fears",
    family: "Volatility Spike",
    color: "#f59e0b",
    icon: Zap,
    vix: 40.7,
    description: "중국 성장 둔화, 위안화 평가절하 충격",
    winners: ["달러", "방어주"],
    losers: ["신흥국", "원자재"],
  },
  {
    id: 4,
    year: "2017",
    name: "Synchronized Growth",
    family: "Equity Melt-Up",
    color: "#10b981",
    icon: TrendingUp,
    vix: 9.1,
    description: "전세계 동반 성장, 극도로 낮은 변동성",
    winners: ["기술주", "신흥국"],
    losers: ["변동성", "금"],
  },
  {
    id: 5,
    year: "2020",
    name: "COVID Crash",
    family: "Black Swan Crisis",
    color: "#dc2626",
    icon: AlertTriangle,
    vix: 82.7,
    description: "팬데믹 충격, 역사상 가장 빠른 약세장",
    winners: ["국채", "금"],
    losers: ["에너지", "여행"],
  },
  {
    id: 6,
    year: "2021",
    name: "Stimulus Rally",
    family: "Liquidity Flood",
    color: "#8b5cf6",
    icon: Zap,
    vix: 16.5,
    description: "대규모 재정부양, 밈주식 광풍",
    winners: ["성장주", "암호화폐"],
    losers: ["가치주", "달러"],
  },
  {
    id: 7,
    year: "2022",
    name: "Inflation Shock",
    family: "Rate Hike Regime",
    color: "#f97316",
    icon: TrendingDown,
    vix: 33.6,
    description: "40년만의 인플레이션, 공격적 금리인상",
    winners: ["에너지", "달러"],
    losers: ["성장주", "채권"],
  },
  {
    id: 8,
    year: "2024",
    name: "AI Supercycle",
    family: "Tech Dominance",
    color: "#06b6d4",
    icon: TrendingUp,
    vix: 14.4,
    description: "AI 혁명, 빅테크 주도 랠리",
    winners: ["반도체", "빅테크"],
    losers: ["소형주", "부동산"],
  },
]

export default function TimelinePage() {
  const containerRef = useRef<HTMLDivElement>(null)
  const [selectedRegime, setSelectedRegime] = useState<typeof REGIMES[0] | null>(null)
  const [currentIndex, setCurrentIndex] = useState(0)

  const scrollTo = (direction: 'left' | 'right') => {
    if (!containerRef.current) return
    const scrollAmount = 400
    const newScroll = containerRef.current.scrollLeft + (direction === 'right' ? scrollAmount : -scrollAmount)
    containerRef.current.scrollTo({ left: newScroll, behavior: 'smooth' })
  }

  // 키보드 네비게이션
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight') scrollTo('right')
      if (e.key === 'ArrowLeft') scrollTo('left')
      if (e.key === 'Escape') setSelectedRegime(null)
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  return (
    <div className="min-h-screen bg-black text-white overflow-hidden">
      {/* 패럴랙스 배경 레이어들 */}
      <div className="fixed inset-0 z-0">
        {/* 별 레이어 (가장 뒤) */}
        <div className="absolute inset-0 bg-[radial-gradient(white_1px,transparent_1px)] bg-[size:50px_50px] opacity-20" />

        {/* 그리드 레이어 */}
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#ffffff08_1px,transparent_1px),linear-gradient(to_bottom,#ffffff08_1px,transparent_1px)] bg-[size:100px_100px]" />

        {/* 그라디언트 오버레이 */}
        <div className="absolute inset-0 bg-gradient-to-b from-black via-transparent to-black" />
        <div className="absolute inset-0 bg-gradient-to-r from-black via-transparent to-black opacity-50" />
      </div>

      {/* 헤더 */}
      <header className="relative z-20 p-8 flex justify-between items-center">
        <Link href="/" className="text-slate-500 hover:text-white transition-colors">
          ← Back
        </Link>
        <div className="text-center">
          <h1 className="text-2xl font-bold tracking-wider">REGIME TIMELINE</h1>
          <p className="text-slate-500 text-sm mt-1">Navigate through economic history</p>
        </div>
        <div className="text-slate-500 text-sm">
          ← → Arrow Keys
        </div>
      </header>

      {/* 메인 타임라인 */}
      <div className="relative z-10 h-[60vh] flex items-center">
        {/* 좌측 화살표 */}
        <button
          onClick={() => scrollTo('left')}
          className="absolute left-4 z-30 p-4 bg-white/10 hover:bg-white/20 rounded-full backdrop-blur-sm transition-all hover:scale-110"
        >
          <ChevronLeft size={32} />
        </button>

        {/* 스크롤 컨테이너 */}
        <div
          ref={containerRef}
          className="flex gap-8 overflow-x-auto scrollbar-hide px-24 py-8 snap-x snap-mandatory"
          style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
        >
          {REGIMES.map((regime, index) => {
            const Icon = regime.icon
            return (
              <motion.div
                key={regime.id}
                className="snap-center flex-shrink-0"
                initial={{ opacity: 0, y: 50 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
              >
                {/* 레짐 카드 */}
                <motion.div
                  onClick={() => setSelectedRegime(regime)}
                  className="relative w-72 h-96 rounded-2xl cursor-pointer group"
                  style={{
                    background: `linear-gradient(135deg, ${regime.color}20 0%, ${regime.color}05 100%)`,
                    border: `2px solid ${regime.color}40`,
                  }}
                  whileHover={{
                    scale: 1.05,
                    y: -10,
                    boxShadow: `0 20px 60px ${regime.color}30`
                  }}
                  whileTap={{ scale: 0.98 }}
                >
                  {/* 글로우 이펙트 */}
                  <div
                    className="absolute inset-0 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-500"
                    style={{
                      background: `radial-gradient(circle at 50% 0%, ${regime.color}40 0%, transparent 70%)`
                    }}
                  />

                  {/* 연도 배지 */}
                  <div
                    className="absolute -top-4 left-1/2 -translate-x-1/2 px-6 py-2 rounded-full text-black font-bold text-lg"
                    style={{ backgroundColor: regime.color }}
                  >
                    {regime.year}
                  </div>

                  {/* 아이콘 */}
                  <div className="absolute top-8 right-6">
                    <Icon
                      size={32}
                      style={{ color: regime.color }}
                      className="opacity-60 group-hover:opacity-100 transition-opacity"
                    />
                  </div>

                  {/* 콘텐츠 */}
                  <div className="relative z-10 p-6 pt-12 h-full flex flex-col">
                    <h3 className="text-xl font-bold mb-2 leading-tight">
                      {regime.name}
                    </h3>
                    <p
                      className="text-sm font-medium mb-4"
                      style={{ color: regime.color }}
                    >
                      {regime.family}
                    </p>
                    <p className="text-slate-400 text-sm flex-1">
                      {regime.description}
                    </p>

                    {/* VIX 인디케이터 */}
                    <div className="mt-auto">
                      <div className="flex items-center justify-between text-sm mb-2">
                        <span className="text-slate-500">VIX</span>
                        <span style={{ color: regime.vix > 30 ? '#ef4444' : '#22c55e' }}>
                          {regime.vix}
                        </span>
                      </div>
                      <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                        <motion.div
                          className="h-full rounded-full"
                          style={{
                            backgroundColor: regime.vix > 30 ? '#ef4444' : '#22c55e',
                          }}
                          initial={{ width: 0 }}
                          animate={{ width: `${Math.min(regime.vix, 100)}%` }}
                          transition={{ delay: index * 0.1 + 0.3, duration: 0.8 }}
                        />
                      </div>
                    </div>

                    {/* 호버 힌트 */}
                    <div className="mt-4 text-center">
                      <span className="text-xs text-slate-500 group-hover:text-white transition-colors">
                        Click to explore →
                      </span>
                    </div>
                  </div>
                </motion.div>

                {/* 연결선 */}
                {index < REGIMES.length - 1 && (
                  <div className="absolute top-1/2 -right-4 w-8 h-0.5 bg-gradient-to-r from-white/20 to-transparent" />
                )}
              </motion.div>
            )
          })}
        </div>

        {/* 우측 화살표 */}
        <button
          onClick={() => scrollTo('right')}
          className="absolute right-4 z-30 p-4 bg-white/10 hover:bg-white/20 rounded-full backdrop-blur-sm transition-all hover:scale-110"
        >
          <ChevronRight size={32} />
        </button>
      </div>

      {/* 하단 타임라인 바 */}
      <div className="relative z-10 px-24 py-8">
        <div className="h-1 bg-white/10 rounded-full relative">
          {REGIMES.map((regime, index) => (
            <motion.div
              key={regime.id}
              className="absolute top-1/2 -translate-y-1/2 w-3 h-3 rounded-full cursor-pointer hover:scale-150 transition-transform"
              style={{
                left: `${(index / (REGIMES.length - 1)) * 100}%`,
                backgroundColor: regime.color,
              }}
              whileHover={{ scale: 1.5 }}
              onClick={() => setSelectedRegime(regime)}
            />
          ))}
        </div>
        <div className="flex justify-between mt-4 text-sm text-slate-500">
          <span>2008</span>
          <span>2024</span>
        </div>
      </div>

      {/* 선택된 레짐 상세 모달 */}
      <AnimatePresence>
        {selectedRegime && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-8 bg-black/80 backdrop-blur-sm"
            onClick={() => setSelectedRegime(null)}
          >
            <motion.div
              initial={{ scale: 0.9, y: 20 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.9, y: 20 }}
              className="relative max-w-2xl w-full rounded-3xl p-8"
              style={{
                background: `linear-gradient(135deg, ${selectedRegime.color}15 0%, #000 100%)`,
                border: `2px solid ${selectedRegime.color}50`,
              }}
              onClick={(e) => e.stopPropagation()}
            >
              {/* 닫기 */}
              <button
                onClick={() => setSelectedRegime(null)}
                className="absolute top-4 right-4 text-slate-500 hover:text-white text-2xl"
              >
                ×
              </button>

              {/* 헤더 */}
              <div className="flex items-start gap-6 mb-8">
                <div
                  className="w-20 h-20 rounded-2xl flex items-center justify-center"
                  style={{ backgroundColor: `${selectedRegime.color}20` }}
                >
                  <selectedRegime.icon size={40} style={{ color: selectedRegime.color }} />
                </div>
                <div>
                  <div
                    className="text-sm font-bold mb-1"
                    style={{ color: selectedRegime.color }}
                  >
                    {selectedRegime.year} · {selectedRegime.family}
                  </div>
                  <h2 className="text-3xl font-bold">{selectedRegime.name}</h2>
                </div>
              </div>

              {/* 설명 */}
              <p className="text-slate-300 text-lg mb-8">
                {selectedRegime.description}
              </p>

              {/* 승자/패자 */}
              <div className="grid grid-cols-2 gap-6">
                <div>
                  <h4 className="text-green-500 font-bold mb-3 flex items-center gap-2">
                    <TrendingUp size={18} /> Winners
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {selectedRegime.winners.map((w) => (
                      <span
                        key={w}
                        className="px-3 py-1 bg-green-500/20 text-green-400 rounded-full text-sm"
                      >
                        {w}
                      </span>
                    ))}
                  </div>
                </div>
                <div>
                  <h4 className="text-red-500 font-bold mb-3 flex items-center gap-2">
                    <TrendingDown size={18} /> Losers
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {selectedRegime.losers.map((l) => (
                      <span
                        key={l}
                        className="px-3 py-1 bg-red-500/20 text-red-400 rounded-full text-sm"
                      >
                        {l}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {/* VIX 상세 */}
              <div className="mt-8 p-4 bg-white/5 rounded-xl">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">VIX (Fear Index)</span>
                  <span
                    className="text-2xl font-bold"
                    style={{ color: selectedRegime.vix > 30 ? '#ef4444' : '#22c55e' }}
                  >
                    {selectedRegime.vix}
                  </span>
                </div>
                <div className="mt-2 h-3 bg-white/10 rounded-full overflow-hidden">
                  <motion.div
                    className="h-full rounded-full"
                    style={{
                      backgroundColor: selectedRegime.vix > 30 ? '#ef4444' : '#22c55e',
                    }}
                    initial={{ width: 0 }}
                    animate={{ width: `${Math.min(selectedRegime.vix, 100)}%` }}
                    transition={{ duration: 0.8 }}
                  />
                </div>
              </div>

              {/* 액션 버튼 */}
              <div className="mt-8 flex gap-4">
                <button
                  className="flex-1 py-3 rounded-xl font-bold transition-colors"
                  style={{
                    backgroundColor: selectedRegime.color,
                    color: '#000'
                  }}
                >
                  Explore This Regime
                </button>
                <button className="px-6 py-3 bg-white/10 hover:bg-white/20 rounded-xl transition-colors">
                  Compare
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* 하단 안내 */}
      <div className="relative z-10 text-center pb-8">
        <p className="text-slate-600 text-sm">
          Scroll or use arrow keys to navigate • Click a regime to explore
        </p>
      </div>
    </div>
  )
}
