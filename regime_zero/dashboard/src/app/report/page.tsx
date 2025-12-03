"use client"

import { useState, useEffect, useRef } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { cn } from "@/lib/utils"

export default function TerminalReport() {
    const [booted, setBooted] = useState(false)
    const [logs, setLogs] = useState<string[]>([])
    const [theme, setTheme] = useState<'dark' | 'light'>('dark')
    const [currentTime, setCurrentTime] = useState<string>("")
    const [command, setCommand] = useState("")
    const logsEndRef = useRef<HTMLDivElement>(null)
    const router = useRouter()

    // Boot Sequence
    useEffect(() => {
        const bootLogs = [
            "> INITIALIZING REGIME ANALYZER...",
            "> CONNECTING TO DATA STREAMS...",
            "> FETCHING BTC PRICE ACTION... [OK]",
            "> ANALYZING FED HAWKISHNESS... [OK]",
            "> SCANNING 20,000+ HISTORICAL PATTERNS...",
            "> CALCULATING COSINE SIMILARITY...",
            "> MATCH FOUND: 2022-03-15 (SCORE: 0.87)",
            "> GENERATING REPORT UI..."
        ]

        let delay = 0
        bootLogs.forEach((log, index) => {
            setTimeout(() => {
                setLogs(prev => [...prev, log])
                if (index === bootLogs.length - 1) {
                    setTimeout(() => setBooted(true), 800)
                }
            }, delay)
            delay += Math.random() * 300 + 100
        })
    }, [])

    // Auto-scroll logs
    useEffect(() => {
        logsEndRef.current?.scrollIntoView({ behavior: "smooth" })
    }, [logs])

    // Clock
    useEffect(() => {
        const timer = setInterval(() => {
            setCurrentTime(new Date().toISOString().replace('T', ' ').substring(0, 19) + ' UTC')
        }, 1000)
        return () => clearInterval(timer)
    }, [])

    const toggleTheme = () => {
        setTheme(prev => prev === 'dark' ? 'light' : 'dark')
    }

    const handleCommand = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter') {
            if (command.trim() === '/exit') {
                router.push('/')
            } else if (command.trim() === '/help') {
                alert("COMMANDS:\n/today - Show today's report\n/exit - Return to dashboard")
            }
            setCommand("")
        }
    }

    // Styles based on theme
    const isDark = theme === 'dark'
    const bgColor = isDark ? "bg-[#050505]" : "bg-[#f0f0f0]"
    const textColor = isDark ? "text-[#e0e0e0]" : "text-[#1a1a1a]"
    const accentColor = isDark ? "text-[#00ff41]" : "text-[#008020]"
    const panelBg = isDark ? "bg-[#141414]/80" : "bg-white/90"
    const borderColor = isDark ? "border-[#333]" : "border-[#ccc]"
    const dimColor = "text-[#666666]"

    return (
        <div className={cn(
            "min-h-screen font-mono text-sm flex flex-col overflow-hidden transition-colors duration-300",
            bgColor, textColor
        )}>
            {/* Scanline Effect */}
            <div className="fixed inset-0 pointer-events-none z-50 bg-[linear-gradient(to_bottom,rgba(255,255,255,0),rgba(255,255,255,0)_50%,rgba(0,0,0,0.1)_50%,rgba(0,0,0,0.1))] bg-[length:100%_4px] opacity-10" />

            <div className="max-w-[1200px] w-full mx-auto p-4 flex flex-col h-full z-10">
                {/* Header */}
                <header className={cn("flex justify-between items-center border-b pb-2 mb-5", borderColor)}>
                    <div className="text-lg font-bold tracking-widest">
                        <span className={cn("animate-pulse mr-2", accentColor)}>█</span>
                        REGIME ZERO <span className={cn("text-xs font-normal ml-2", dimColor)}>v1.0.5</span>
                    </div>
                    <div className="flex items-center gap-4">
                        <button
                            onClick={toggleTheme}
                            className={cn("border px-2 py-0.5 text-xs hover:text-opacity-80 transition-colors", borderColor, dimColor)}
                        >
                            [ {isDark ? "LIGHT MODE" : "DARK MODE"} ]
                        </button>
                        <Link
                            href="/"
                            className={cn("border px-2 py-0.5 text-xs hover:text-opacity-80 transition-colors", borderColor, dimColor)}
                        >
                            [ EXIT ]
                        </Link>
                        <div className={dimColor}>{currentTime || "LOADING..."}</div>
                    </div>
                </header>

                {/* Main Content */}
                <main className="flex-1 overflow-y-auto pr-1">
                    {!booted ? (
                        <div className="p-5">
                            {logs.map((log, i) => (
                                <div key={i} className="mb-1">
                                    <span className={dimColor}>{"> "}</span>{log}
                                </div>
                            ))}
                            <div ref={logsEndRef} />
                        </div>
                    ) : (
                        <div className="animate-in fade-in duration-500 space-y-5">

                            {/* Top Panel: Match */}
                            <section className={cn("border p-5", borderColor, panelBg)}>
                                <div className={cn("flex justify-between mb-4 border-b border-dashed pb-2", borderColor)}>
                                    <span className={cn("font-bold uppercase", dimColor)}>[ MARKET REGIME ANALYSIS ]</span>
                                    <span className={cn("text-xs", accentColor)}>● LIVE</span>
                                </div>
                                <div className="flex justify-around items-center">
                                    <div className="flex flex-col items-center">
                                        <span className={cn("text-xs uppercase mb-2", dimColor)}>SIMILARITY MATCH</span>
                                        <span className={cn("text-2xl font-bold", accentColor)}>87%</span>
                                    </div>
                                    <div className="flex flex-col items-center">
                                        <span className={cn("text-xs uppercase mb-2", dimColor)}>HISTORICAL TWIN</span>
                                        <span className="text-2xl font-bold text-amber-500">2022-03-15</span>
                                    </div>
                                    <div className="flex flex-col items-center">
                                        <span className={cn("text-xs uppercase mb-2", dimColor)}>REGIME TYPE</span>
                                        <span className="text-xl font-bold">INSTITUTIONAL ACCUMULATION</span>
                                    </div>
                                </div>
                            </section>

                            {/* Comparison Grid */}
                            <section className={cn("border p-5", borderColor, panelBg)}>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                                    {/* Today */}
                                    <div>
                                        <div className={cn("mb-4 border-b pb-1", borderColor, dimColor)}>┌─ TODAY (2025-12-03) ──────────────┐</div>
                                        <div className="space-y-2">
                                            <div className="flex justify-between hover:bg-white/5 px-2 py-1 border-l-2 border-transparent hover:border-emerald-500">
                                                <span className="font-bold">BTC</span>
                                                <span className={dimColor}>Institutional Accumulation</span>
                                            </div>
                                            <div className="flex justify-between hover:bg-white/5 px-2 py-1 border-l-2 border-transparent hover:border-emerald-500">
                                                <span className="font-bold">FED</span>
                                                <span className={dimColor}>Hawkish Hold (+1.24%)</span>
                                            </div>
                                            <div className="flex justify-between hover:bg-white/5 px-2 py-1 border-l-2 border-transparent hover:border-emerald-500">
                                                <span className="font-bold">OIL</span>
                                                <span className="text-red-500">Bearish Action (-1.26%)</span>
                                            </div>
                                            <div className="flex justify-between hover:bg-white/5 px-2 py-1 border-l-2 border-transparent hover:border-emerald-500">
                                                <span className="font-bold">GOLD</span>
                                                <span className={accentColor}>Safe Haven Bid (+1.51%)</span>
                                            </div>
                                        </div>
                                        <div className={cn("mt-2 border-t pt-1", borderColor, dimColor)}>└───────────────────────────────────┘</div>
                                    </div>

                                    {/* Twin */}
                                    <div>
                                        <div className={cn("mb-4 border-b pb-1", borderColor, dimColor)}>┌─ TWIN (2022-03-15) ───────────────┐</div>
                                        <div className="space-y-2">
                                            <div className="flex justify-between px-2 py-1">
                                                <span className={dimColor}>Context:</span>
                                                <span>Ukraine War Early Phase</span>
                                            </div>
                                            <div className="flex justify-between px-2 py-1">
                                                <span className={dimColor}>Result:</span>
                                                <span>
                                                    <span className={accentColor}>+15% (3w)</span> → <span className="text-red-500">-25% (6w)</span>
                                                </span>
                                            </div>
                                            <div className="flex justify-between px-2 py-1">
                                                <span className={dimColor}>Trigger:</span>
                                                <span>Fed Hawkish Surprise</span>
                                            </div>
                                        </div>
                                        <div className={cn("mt-2 border-t pt-1", borderColor, dimColor)}>└───────────────────────────────────┘</div>
                                    </div>
                                </div>
                            </section>

                            {/* Bottom Grid */}
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                                <section className={cn("border p-5 md:col-span-2", borderColor, panelBg)}>
                                    <div className={cn("mb-4 border-b border-dashed pb-2 font-bold", borderColor, dimColor)}>[ INTERPRETATION ]</div>
                                    <div className="space-y-3">
                                        <p>{"> "}Both periods show institutional crypto adoption amid tight Fed policy.</p>
                                        <p>{"> "}Key difference: 2025 has lower geopolitical risk compared to 2022.</p>
                                        <p>{"> "}Short-term rally possible, but Fed remains constraining factor.</p>
                                    </div>
                                </section>

                                <section className={cn("border p-5", borderColor, panelBg)}>
                                    <div className={cn("mb-4 border-b border-dashed pb-2 font-bold", borderColor, dimColor)}>[ ACTION SIGNALS ]</div>
                                    <div className="space-y-2">
                                        <div className={cn("border p-2 flex items-center gap-2 border-l-4 border-l-amber-500", borderColor)}>
                                            <span className="text-amber-500 font-bold">⚠</span> CAUTION: Mixed signals
                                        </div>
                                        <div className={cn("border p-2 flex items-center gap-2 border-l-4 border-l-emerald-500", borderColor)}>
                                            <span className="text-emerald-500 font-bold">✓</span> SUPPORT: Inst. bid
                                        </div>
                                        <div className={cn("border p-2 flex items-center gap-2 border-l-4 border-l-red-500", borderColor)}>
                                            <span className="text-red-500 font-bold">✗</span> RISK: Macro headwinds
                                        </div>
                                    </div>
                                </section>
                            </div>

                            {/* ASCII Chart */}
                            <section className={cn("border p-5", borderColor, panelBg)}>
                                <div className={cn("mb-4 border-b border-dashed pb-2 font-bold", borderColor, dimColor)}>[ BTC PRICE ACTION (7D) ]</div>
                                <pre className="text-xs leading-tight overflow-x-auto whitespace-pre font-mono">
                                    {`$96,000 ┤           ╭──╮
$94,000 ┤        ╭──╯  ╰─╮
$92,000 ┤      ╭─╯       ╰──╮
$90,000 ┤   ╭──╯            ╰─
$88,000 ┤╭──╯
        └┴──┴──┴──┴──┴──┴──┴──
         M  T  W  T  F  S  S`}
                                </pre>
                            </section>

                        </div>
                    )}
                </main>

                {/* Footer */}
                <footer className={cn("mt-5 border-t pt-4", borderColor)}>
                    <div className={cn("flex items-center p-2 border mb-2", borderColor, panelBg)}>
                        <span className={cn("font-bold mr-2", accentColor)}>user@regime-zero:~$</span>
                        <input
                            type="text"
                            value={command}
                            onChange={(e) => setCommand(e.target.value)}
                            onKeyDown={handleCommand}
                            placeholder="Type /help for commands..."
                            className={cn("bg-transparent border-none outline-none flex-1 font-mono", textColor)}
                            spellCheck={false}
                            autoFocus
                        />
                    </div>
                    <div className={cn("flex justify-end gap-5 text-xs", dimColor)}>
                        <span>CONNECTED: 12ms</span>
                        <span>MEM: 24GB</span>
                        <span>CPU: 12%</span>
                    </div>
                </footer>
            </div>
        </div>
    )
}
