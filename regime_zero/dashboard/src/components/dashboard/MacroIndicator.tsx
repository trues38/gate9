import { cn } from "@/lib/utils"
import { LucideIcon } from "lucide-react"

interface MacroIndicatorProps {
    label: string
    value: string | number
    trend?: 'up' | 'down' | 'neutral' | 'warning'
    change?: string
    theme: 'dark' | 'light'
}

export function MacroIndicator({ label, value, trend = 'neutral', change, theme }: MacroIndicatorProps) {
    return (
        <div className={cn(
            "flex items-center gap-2 border-r pr-6 last:border-0",
            theme === 'dark' ? "border-white/5" : "border-slate-200"
        )}>
            <span className={cn("font-bold", theme === 'dark' ? "text-slate-500" : "text-slate-400")}>
                {label}
            </span>
            <span className={cn(
                "font-medium flex items-center gap-1",
                trend === 'up' ? "text-emerald-500" :
                    trend === 'down' ? "text-rose-500" :
                        trend === 'warning' ? "text-amber-500" :
                            (theme === 'dark' ? "text-slate-300" : "text-slate-600")
            )}>
                {value}
                {change && <span className="opacity-70 text-[10px]">{change}</span>}
            </span>
        </div>
    )
}
