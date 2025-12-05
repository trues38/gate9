import { cn } from "../../lib/utils"
import { ArrowUpRight } from "lucide-react"
import { getCountryFlag } from "../../lib/config"

export interface NewsItem {
    id: number
    title: string
    clean_title?: string
    published_at: string
    summary: string
    url?: string
    source?: string
    country?: string
    category?: string
    importance_score?: number
    short_summary?: string
    title_ko?: string
    summary_ko?: string
}

interface NewsCardProps {
    item: NewsItem
    theme: 'dark' | 'light'
    selectedLanguage: string
}

export function NewsCard({ item, theme, selectedLanguage }: NewsCardProps) {
    return (
        <a
            href={item.url || "#"}
            target="_blank"
            rel="noopener noreferrer"
            className={cn(
                "flex items-start gap-3 p-3 transition-colors group",
                theme === 'dark' ? "hover:bg-white/5" : "hover:bg-slate-50"
            )}
        >
            <div className="shrink-0 w-24 text-center pt-1 flex flex-col items-center gap-1.5">
                {/* Top: Category Badge */}
                <span className={cn(
                    "text-[10px] font-bold px-2 py-0.5 rounded border w-full text-center truncate",
                    item.category === 'ECONOMY' ? "text-emerald-500 border-emerald-500/30 bg-emerald-500/10" :
                        item.category === 'FINANCE' ? "text-blue-500 border-blue-500/30 bg-blue-500/10" :
                            item.category === 'CRYPTO' ? "text-amber-500 border-amber-500/30 bg-amber-500/10" :
                                item.category === 'POLITICS' ? "text-rose-500 border-rose-500/30 bg-rose-500/10" :
                                    "text-slate-400 border-slate-500/30 bg-slate-500/10"
                )}>
                    {item.category || "GEN"}
                </span>

                {/* Bottom: Flag + Score */}
                <div className="flex items-center justify-center gap-2">
                    <span className="text-lg leading-none" title={item.country || "Global"}>
                        {getCountryFlag(item.country || 'ALL')}
                    </span>
                    {item.importance_score && item.importance_score > 0 ? (
                        <span className="text-xs font-bold font-mono text-slate-400">
                            {item.importance_score}
                        </span>
                    ) : (
                        <span className="text-[9px] font-mono text-slate-600 animate-pulse">
                            ...
                        </span>
                    )}
                </div>
            </div>
            <div className="flex-1 min-w-0">
                <h4 className={cn(
                    "text-sm font-medium transition-colors font-mono leading-tight mb-1",
                    theme === 'dark' ? "text-slate-200 group-hover:text-indigo-300" : "text-slate-800 group-hover:text-indigo-600"
                )}>
                    {/* Use selectedLanguage for translation */}
                    {(selectedLanguage === 'KO' && item.title_ko) ? item.title_ko : (item.clean_title || item.title)}
                </h4>
            </div>
            <div className="shrink-0 text-right pt-1 hidden sm:block">
                <span className="text-[10px] text-slate-600 font-mono block">
                    {new Date(item.published_at).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'America/New_York' })} EST
                </span>
                <span className="text-[10px] text-indigo-400 font-mono block">
                    {new Date(item.published_at).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'Asia/Seoul' })} KST
                </span>
            </div>
            <ArrowUpRight size={14} className="text-slate-700 group-hover:text-indigo-400 transition-colors opacity-0 group-hover:opacity-100 mt-1" />
        </a>
    )
}
