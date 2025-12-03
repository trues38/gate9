"use client"

import { useState, useEffect, Suspense } from "react"
import Link from "next/link"
import { useSearchParams } from "next/navigation"
import {
    CloudSun, TrendingUp, Shield, DollarSign, Activity, Zap,
    ChevronRight, Info, CloudRain, CloudLightning, Sun, Terminal,
    ArrowUpRight, ArrowDownRight, Globe, Lock, Unlock
} from "lucide-react"
import { cn } from "@/lib/utils"
import { supabase } from "@/lib/supabase"

interface NewsItem {
    id: number
    title: string
    clean_title?: string
    published_at: string
    summary: string
    url?: string
    source?: string
    country?: string
}

function DashboardContent() {
    const searchParams = useSearchParams()
    const initialCountry = searchParams.get('country') || 'ALL'

    const [selectedFactor, setSelectedFactor] = useState<string | null>(null)
    const [selectedCountry, setSelectedCountry] = useState<string>(initialCountry)
    const [news, setNews] = useState<NewsItem[]>([])
    const [loading, setLoading] = useState(true)
    const [currentDate, setCurrentDate] = useState<string>("")

    const countries = ['ALL', 'US', 'KR', 'CN', 'JP', 'EU', 'CRYPTO']

    useEffect(() => {
        setCurrentDate(new Date().toLocaleDateString('en-US', {
            weekday: 'short',
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        }))
    }, [])

    useEffect(() => {
        async function fetchData() {
            setLoading(true)
            let query = supabase
                .from('ingest_news')
                .select('id, title, clean_title, published_at, summary, url, source, country')
                .order('published_at', { ascending: false })
                .limit(50)

            if (selectedCountry !== 'ALL') {
                if (selectedCountry === 'CRYPTO') {
                    // Assuming crypto news might be tagged or we filter by keywords/category
                    // For now, let's try a text search or specific country code if used
                    // If no specific column, we might fallback to text search
                    query = query.textSearch('title', "'bitcoin' | 'crypto' | 'btc' | 'eth'")
                } else {
                    query = query.eq('country', selectedCountry)
                }
            }

            const { data, error } = await query

            if (data) {
                setNews(data)
            }
            setLoading(false)
        }
        fetchData()

        // Real-time subscription
        const channel = supabase
            .channel('public:ingest_news')
            .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'ingest_news' }, (payload) => {
                console.log('New news:', payload)
                // In a real app, we'd prepend this to the list
            })
            .subscribe()

        return () => {
            supabase.removeChannel(channel)
        }
    }, [selectedCountry])

    // Mock Data for Macro Bar
    const macroIndicators = [
        { label: "RATES", value: "Hawkish Hold", trend: "neutral", icon: Activity },
        { label: "DXY", value: "103.45", trend: "up", change: "+0.2%", icon: DollarSign },
        { label: "OIL", value: "$78.20", trend: "down", change: "-1.2%", icon: Zap }, // Using Zap as generic energy
        { label: "GOLD", value: "$2,045", trend: "up", change: "+1.5%", icon: Shield },
        { label: "LIQUIDITY", value: "Stable", trend: "neutral", icon: Unlock },
        { label: "RISK", value: "Elevated", trend: "warning", icon: CloudLightning },
    ]

    // Mock Data for Regime Cards
    const regimeCards = [
        { title: "BTC", status: "Accumulation", vibe: "Institutional Bid", color: "text-emerald-400", border: "border-emerald-500/30" },
        { title: "FED", status: "Hawkish Hold", vibe: "Higher for Longer", color: "text-indigo-400", border: "border-indigo-500/30" },
        { title: "OIL", status: "Weakness", vibe: "Demand Fears", color: "text-rose-400", border: "border-rose-500/30" },
        { title: "GOLD", status: "Safe Haven", vibe: "Geopolitics", color: "text-amber-400", border: "border-amber-500/30" },
        { title: "NEWS", status: "Mixed", vibe: "Noise High", color: "text-slate-400", border: "border-slate-500/30" },
    ]

    return (
        <div className="min-h-screen bg-[#050505] text-slate-200 font-sans selection:bg-indigo-500/30 flex flex-col">

            {/* LAYER 1: MACRO NOW BAR (Sticky Top) */}
            <div className="sticky top-0 z-50 bg-[#0a0a0a]/95 backdrop-blur-md border-b border-white/5 shadow-lg">
                <div className="max-w-[1600px] mx-auto px-4 h-12 flex items-center justify-between overflow-x-auto no-scrollbar">
                    <div className="flex items-center gap-6 text-xs font-mono whitespace-nowrap">
                        <div className="flex items-center gap-2 text-indigo-400 font-bold mr-4">
                            <Activity size={14} />
                            <span>MACRO NOW</span>
                        </div>
                        {macroIndicators.map((item, idx) => (
                            <div key={idx} className="flex items-center gap-2 border-r border-white/5 pr-6 last:border-0">
                                <span className="text-slate-500 font-bold">{item.label}</span>
                                <span className={cn(
                                    "font-medium flex items-center gap-1",
                                    item.trend === 'up' ? "text-emerald-400" :
                                        item.trend === 'down' ? "text-rose-400" :
                                            item.trend === 'warning' ? "text-amber-400" : "text-slate-300"
                                )}>
                                    {item.value}
                                    {item.change && <span className="opacity-70 text-[10px]">{item.change}</span>}
                                </span>
                            </div>
                        ))}
                    </div>
                    <div className="hidden md:flex items-center gap-3">
                        <Link href="/report" className="flex items-center gap-2 bg-white/5 hover:bg-white/10 text-slate-300 px-3 py-1 rounded-full text-[10px] font-mono transition-colors border border-white/10">
                            <Terminal size={12} />
                            TERMINAL VIEW
                        </Link>
                        <span className="text-[10px] font-mono text-emerald-500 animate-pulse">● LIVE</span>
                    </div>
                </div>
            </div>

            <div className="flex-1 max-w-[1600px] w-full mx-auto p-6 grid grid-cols-1 lg:grid-cols-12 gap-8">

                {/* LAYER 2: DAILY REGIME SUMMARY (Middle) */}
                <div className="lg:col-span-12 space-y-6">
                    {/* Header */}
                    <div className="flex justify-between items-end border-b border-white/5 pb-4">
                        <div>
                            <div className="flex items-center gap-3 mb-1">
                                <h1 className="text-3xl font-bold tracking-tight text-white">Factor-7</h1>
                                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-500/20 text-indigo-400 border border-indigo-500/20">PRO</span>
                            </div>
                            <p className="text-slate-400 text-sm font-mono">{currentDate}</p>
                        </div>
                        <div className="flex items-center gap-4 text-right">
                            <div>
                                <div className="text-xl font-bold text-white flex items-center justify-end gap-2">
                                    <CloudSun className="text-slate-400" size={24} />
                                    Partly Cloudy
                                </div>
                                <p className="text-xs text-slate-500">Market is digesting mixed signals.</p>
                            </div>
                        </div>
                    </div>

                    {/* Split View: Regimes & Twin */}
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

                        {/* Left: Today's Regimes */}
                        <div className="lg:col-span-2">
                            <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-4 flex items-center gap-2">
                                <Globe size={12} /> Today's Regime Matrix
                            </h3>
                            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                                {regimeCards.map((card, idx) => (
                                    <div key={idx} className={cn(
                                        "bg-white/5 border rounded-xl p-4 hover:bg-white/10 transition-all cursor-pointer group",
                                        card.border
                                    )}>
                                        <div className="flex justify-between items-start mb-2">
                                            <span className="text-slate-400 text-xs font-bold">{card.title}</span>
                                            <Info size={12} className="text-slate-600 opacity-0 group-hover:opacity-100 transition-opacity" />
                                        </div>
                                        <div className="text-lg font-bold text-white mb-1">{card.status}</div>
                                        <div className={cn("text-xs font-mono", card.color)}>{card.vibe}</div>
                                    </div>
                                ))}
                            </div>

                            {/* Interpretation & Signals */}
                            <div className="mt-6 bg-white/5 border border-white/10 rounded-xl p-5">
                                <div className="flex items-start gap-4">
                                    <div className="p-2 bg-indigo-500/10 rounded-lg text-indigo-400 shrink-0">
                                        <Activity size={20} />
                                    </div>
                                    <div>
                                        <h4 className="text-sm font-bold text-white mb-1">AI Interpretation</h4>
                                        <p className="text-xs text-slate-400 leading-relaxed">
                                            Institutional accumulation in crypto assets is diverging from traditional risk assets.
                                            While oil shows weakness due to demand fears, gold maintains its safe-haven bid.
                                            The Fed's "Hawkish Hold" stance remains the primary constraint on broader liquidity.
                                        </p>
                                        <div className="flex gap-2 mt-3">
                                            <span className="px-2 py-1 rounded bg-emerald-500/10 text-emerald-400 text-[10px] font-bold border border-emerald-500/20">BUY DIP: BTC</span>
                                            <span className="px-2 py-1 rounded bg-rose-500/10 text-rose-400 text-[10px] font-bold border border-rose-500/20">AVOID: OIL</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Right: Historical Twin */}
                        <div className="lg:col-span-1">
                            <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-4 flex items-center gap-2">
                                <Terminal size={12} /> Historical Twin
                            </h3>
                            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 h-full relative overflow-hidden">
                                <div className="absolute top-0 right-0 p-3 opacity-10">
                                    <Terminal size={100} />
                                </div>
                                <div className="relative z-10">
                                    <div className="text-xs text-slate-500 mb-1">MATCH DATE</div>
                                    <div className="text-3xl font-bold text-amber-500 font-mono mb-4">2022-03-15</div>

                                    <div className="space-y-4">
                                        <div>
                                            <div className="text-[10px] text-slate-500 uppercase font-bold">Context</div>
                                            <div className="text-sm text-slate-300">Ukraine War Early Phase</div>
                                        </div>
                                        <div>
                                            <div className="text-[10px] text-slate-500 uppercase font-bold">Outcome</div>
                                            <div className="text-sm text-slate-300 flex items-center gap-2">
                                                <span className="text-emerald-400 font-bold">+15% (3w)</span>
                                                <span className="text-slate-600">→</span>
                                                <span className="text-rose-400 font-bold">-25% (6w)</span>
                                            </div>
                                        </div>
                                        <div className="pt-4 border-t border-white/5">
                                            <div className="flex justify-between items-center">
                                                <span className="text-xs text-slate-500">Similarity Score</span>
                                                <span className="text-xl font-bold text-white">87%</span>
                                            </div>
                                            <div className="w-full bg-slate-800 h-1 mt-2 rounded-full overflow-hidden">
                                                <div className="bg-amber-500 h-full w-[87%]" />
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* LAYER 3: LIVE INTELLIGENCE FEED (Bottom) */}
                <div className="lg:col-span-12 mt-4">
                    <div className="flex flex-col md:flex-row justify-between items-center mb-4 gap-4">
                        <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest flex items-center gap-2">
                            <Zap size={12} className="text-amber-400" /> Live Intelligence Feed
                        </h3>
                        <div className="flex flex-wrap gap-1 bg-white/5 p-1 rounded-lg border border-white/5">
                            {countries.map(country => (
                                <button
                                    key={country}
                                    onClick={() => setSelectedCountry(country)}
                                    className={cn(
                                        "px-3 py-1 text-[10px] font-bold rounded-md transition-all font-mono",
                                        selectedCountry === country
                                            ? "bg-indigo-600 text-white shadow-lg"
                                            : "text-slate-500 hover:text-slate-300 hover:bg-white/5"
                                    )}
                                >
                                    {country}
                                </button>
                            ))}
                        </div>
                    </div>

                    <div className="bg-[#0a0a0a] border border-white/10 rounded-xl overflow-hidden min-h-[400px]">
                        {loading ? (
                            <div className="flex flex-col items-center justify-center h-[400px] text-slate-500 gap-3">
                                <div className="w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
                                <span className="text-xs font-mono animate-pulse">ESTABLISHING SECURE UPLINK...</span>
                            </div>
                        ) : news.length === 0 ? (
                            <div className="flex flex-col items-center justify-center h-[400px] text-slate-500">
                                <Info size={24} className="mb-2 opacity-50" />
                                <span className="text-xs font-mono">NO INTELLIGENCE FOUND FOR {selectedCountry}</span>
                            </div>
                        ) : (
                            <div className="divide-y divide-white/5">
                                {news.map((item, idx) => (
                                    <a
                                        key={idx}
                                        href={item.url || "#"}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="flex items-center gap-4 p-4 hover:bg-white/5 transition-colors group"
                                    >
                                        <div className="shrink-0 w-16 text-center">
                                            <span className={cn(
                                                "text-[10px] font-bold px-1.5 py-0.5 rounded border",
                                                item.country === 'US' ? "text-blue-400 border-blue-500/30 bg-blue-500/10" :
                                                    item.country === 'KR' ? "text-rose-400 border-rose-500/30 bg-rose-500/10" :
                                                        item.country === 'CN' ? "text-red-400 border-red-500/30 bg-red-500/10" :
                                                            item.country === 'JP' ? "text-white border-white/30 bg-white/10" :
                                                                item.country === 'EU' ? "text-indigo-400 border-indigo-500/30 bg-indigo-500/10" :
                                                                    "text-slate-400 border-slate-500/30 bg-slate-500/10"
                                            )}>
                                                {item.country || "GLO"}
                                            </span>
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <h4 className="text-sm font-medium text-slate-200 group-hover:text-indigo-300 transition-colors truncate font-mono">
                                                {item.clean_title || item.title}
                                            </h4>
                                        </div>
                                        <div className="shrink-0 text-right">
                                            <span className="text-[10px] text-slate-600 font-mono">
                                                {new Date(item.published_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                            </span>
                                        </div>
                                        <ArrowUpRight size={14} className="text-slate-700 group-hover:text-indigo-400 transition-colors opacity-0 group-hover:opacity-100" />
                                    </a>
                                ))}
                            </div>
                        )}
                    </div>
                </div>

            </div>
        </div>
    )
}

export default function Dashboard() {
    return (
        <Suspense fallback={<div className="min-h-screen bg-[#050505] flex items-center justify-center text-slate-500">Loading...</div>}>
            <DashboardContent />
        </Suspense>
    )
}
