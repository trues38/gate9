import { cn } from "@/lib/utils"
import { Info } from "lucide-react"

interface RegimeCardProps {
    title: string
    status: string
    vibe: string
    color: string
    border: string
    theme: 'dark' | 'light'
}

export function RegimeCard({ title, status, vibe, color, border, theme }: RegimeCardProps) {
    return (
        <div className={cn(
            "border rounded-xl p-4 transition-all cursor-pointer group",
            theme === 'dark'
                ? "bg-white/5 hover:bg-white/10"
                : "bg-white hover:bg-slate-50 shadow-sm",
            border
        )}>
            <div className="flex justify-between items-start mb-2">
                <span className="text-slate-400 text-xs font-bold">{title}</span>
                <Info size={12} className="text-slate-600 opacity-0 group-hover:opacity-100 transition-opacity" />
            </div>
            <div className={cn("text-lg font-bold mb-1", theme === 'dark' ? "text-white" : "text-slate-900")}>
                {status}
            </div>
            <div className={cn("text-xs font-mono", color)}>
                {vibe}
            </div>
        </div>
    )
}
