"use client"

import { useState, useEffect, useRef } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { cn } from "@/lib/utils"
import { createClient } from "@supabase/supabase-js"
import { Terminal } from "lucide-react"

interface ReportMeta {
    id: string
    date: string
    type: string
}

interface ReportContent {
    id: string
    date: string
    type: string
    content: string
    consensus_signal?: any
    created_at: string
}

export default function TerminalReport() {
    const [booted, setBooted] = useState(false)
    const [logs, setLogs] = useState<string[]>([])
    const [theme, setTheme] = useState<'dark' | 'light'>('dark')
    const [currentTime, setCurrentTime] = useState<string>("")
    const [command, setCommand] = useState("")

    // History & Data
    const [history, setHistory] = useState<ReportMeta[]>([])
    const [selectedReport, setSelectedReport] = useState<ReportContent | null>(null)
    const [loadingReport, setLoadingReport] = useState(false)

    const logsEndRef = useRef<HTMLDivElement>(null)
    const router = useRouter()

    const getSupabase = () => createClient(
        process.env.NEXT_PUBLIC_SUPABASE_URL || "https://placeholder.supabase.co",
        process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "placeholder_key"
    )

    // Boot Sequence
    useEffect(() => {
        const bootLogs = [
            "> INITIALIZING REGIME ANALYZER...",
            "> CONNECTING TO SECURE ARCHIVE...",
            "> DECRYPTING HISTORY INDEX... [OK]",
            "> ESTABLISHING UPLINK... [OK]",
            "> ACCESS GRANTED."
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

    // Fetch History
    useEffect(() => {
        async function fetchHistory() {
            const supabase = getSupabase()
            const { data, error } = await supabase
                .from('intelligence_reports')
                .select('id, date, type')
                .order('date', { ascending: false })

            if (data) {
                setHistory(data)
                // If we have history, select the latest one automatically? 
                // Or maybe just wait for user. Let's select the first one if available.
                if (data.length > 0) {
                    // fetchReport(data[0].id) // Optional: Auto-load latest
                }
            }
        }
        fetchHistory()
    }, [])

    async function fetchReport(id: string) {
        setLoadingReport(true)
        const supabase = getSupabase()
        const { data, error } = await supabase
            .from('intelligence_reports')
            .select('*')
            .eq('id', id)
            .single()

        if (data) {
            setSelectedReport(data)
        }
        setLoadingReport(false)
    }

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
                alert("COMMANDS:\n/exit - Return to dashboard")
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
    const activeItemBg = isDark ? "bg-[#00ff41]/10" : "bg-[#008020]/10"

    return (
        <div className={cn(
            "min-h-screen font-mono text-sm flex flex-col overflow-hidden transition-colors duration-300",
            bgColor, textColor
        )}>
            {/* Scanline Effect */}
            <div className="fixed inset-0 pointer-events-none z-50 bg-[linear-gradient(to_bottom,rgba(255,255,255,0),rgba(255,255,255,0)_50%,rgba(0,0,0,0.1)_50%,rgba(0,0,0,0.1))] bg-[length:100%_4px] opacity-10" />

            <div className="max-w-[1400px] w-full mx-auto p-4 flex flex-col h-full z-10">
                {/* Header */}
                <header className={cn("flex justify-between items-center border-b pb-2 mb-5", borderColor)}>
                    <div className="text-lg font-bold tracking-widest">
                        <span className={cn("animate-pulse mr-2", accentColor)}>█</span>
                        REGIME ZERO <span className={cn("text-xs font-normal ml-2", dimColor)}>ARCHIVE_ACCESS</span>
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

                {/* Main Content Area */}
                <main className="flex-1 flex overflow-hidden gap-4">
                    {!booted ? (
                        <div className="p-5 w-full">
                            {logs.map((log, i) => (
                                <div key={i} className="mb-1">
                                    <span className={dimColor}>{"> "}</span>{log}
                                </div>
                            ))}
                            <div ref={logsEndRef} />
                        </div>
                    ) : (
                        <>
                            {/* Left Sidebar: History List */}
                            <aside className={cn("w-64 flex flex-col border", borderColor, panelBg)}>
                                <div className={cn("p-2 border-b font-bold text-xs tracking-wider", borderColor, dimColor)}>
                                    [ ARCHIVE_INDEX ]
                                </div>
                                <div className="flex-1 overflow-y-auto p-2 space-y-1">
                                    {history.length === 0 ? (
                                        <div className="text-xs text-center py-4 text-gray-500">
                                            NO RECORDS FOUND
                                        </div>
                                    ) : (
                                        history.map((item) => (
                                            <button
                                                key={item.id}
                                                onClick={() => fetchReport(item.id)}
                                                className={cn(
                                                    "w-full text-left px-3 py-2 text-xs border border-transparent hover:border-current transition-all group flex justify-between items-center",
                                                    selectedReport?.id === item.id ? activeItemBg : "hover:bg-white/5"
                                                )}
                                            >
                                                <span>{item.date}</span>
                                                <span className={cn("text-[10px] uppercase opacity-50",
                                                    item.type === 'Institutional' ? "text-blue-400" : "text-amber-400"
                                                )}>
                                                    {item.type.substring(0, 4)}
                                                </span>
                                            </button>
                                        ))
                                    )}
                                </div>
                            </aside>

                            {/* Right Panel: Report Content */}
                            <section className={cn("flex-1 border flex flex-col relative", borderColor, panelBg)}>
                                <div className={cn("p-2 border-b font-bold text-xs tracking-wider flex justify-between", borderColor, dimColor)}>
                                    <span>[ REPORT_VIEWER ]</span>
                                    {selectedReport && <span>ID: {selectedReport.id.substring(0, 8)}</span>}
                                </div>

                                <div className="flex-1 overflow-y-auto p-6 relative">
                                    {loadingReport ? (
                                        <div className="absolute inset-0 flex items-center justify-center">
                                            <div className="flex flex-col items-center gap-2">
                                                <div className={cn("w-4 h-4 animate-spin border-2 border-t-transparent rounded-full", isDark ? "border-green-500" : "border-green-700")}></div>
                                                <span className="text-xs animate-pulse">DECRYPTING DATA...</span>
                                            </div>
                                        </div>
                                    ) : selectedReport ? (
                                        <div className="max-w-3xl mx-auto space-y-6">
                                            <div className="border-b border-dashed pb-4 border-gray-700">
                                                <h1 className="text-2xl font-bold mb-2">{selectedReport.date} REGIME REPORT</h1>
                                                <div className="flex gap-4 text-xs opacity-70">
                                                    <span>TYPE: {selectedReport.type}</span>
                                                    <span>GENERATED: {new Date(selectedReport.created_at).toLocaleString()}</span>
                                                </div>
                                            </div>

                                            {/* Content Rendering */}
                                            <div className="whitespace-pre-wrap leading-relaxed opacity-90">
                                                {selectedReport.content || "No content available."}
                                            </div>

                                            {/* Consensus Signal (if JSON) */}
                                            {selectedReport.consensus_signal && (
                                                <div className="mt-8 border p-4 bg-black/20">
                                                    <h3 className="text-xs font-bold mb-2 opacity-70">[ CONSENSUS SIGNAL ]</h3>
                                                    <pre className="text-xs overflow-x-auto">
                                                        {JSON.stringify(selectedReport.consensus_signal, null, 2)}
                                                    </pre>
                                                </div>
                                            )}
                                        </div>
                                    ) : (
                                        <div className="h-full flex flex-col items-center justify-center opacity-30">
                                            <Terminal size={48} className="mb-4" />
                                            <p>SELECT A FILE FROM ARCHIVE</p>
                                        </div>
                                    )}
                                </div>
                            </section>
                        </>
                    )}
                </main>

                {/* Footer */}
                <footer className={cn("mt-4 border-t pt-2", borderColor)}>
                    <div className={cn("flex items-center p-2 border mb-2", borderColor, panelBg)}>
                        <span className={cn("font-bold mr-2", accentColor)}>user@regime-zero:~$</span>
                        <input
                            type="text"
                            value={command}
                            onChange={(e) => setCommand(e.target.value)}
                            onKeyDown={handleCommand}
                            placeholder="Type /exit to return..."
                            className={cn("bg-transparent border-none outline-none flex-1 font-mono", textColor)}
                            spellCheck={false}
                            autoFocus
                        />
                    </div>
                </footer>
            </div>
        </div>
    )
}
