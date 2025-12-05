import { cn } from "../../lib/utils"

interface MarketSnapshot {
    [key: string]: {
        price: number
        change: number
    }
}

interface MarketBoardProps {
    data: MarketSnapshot
    theme: 'dark' | 'light'
}

export function MarketBoard({ data, theme }: MarketBoardProps) {
    if (!data) return null

    // Helper to format numbers
    const fmt = (val: number, type: 'price' | 'rate' | 'index') => {
        if (val === undefined) return "..."
        if (type === 'rate') return `${val.toFixed(2)}%`
        if (type === 'price') return val.toLocaleString(undefined, { maximumFractionDigits: 2 })
        return val.toLocaleString(undefined, { maximumFractionDigits: 2 })
    }

    // Calculate Spread (10Y - 13W proxy for now or 2Y if available)
    // Using 13W (IRX) as short term proxy if 2Y not found
    const yield10y = data["US 10Y Yield"]?.price
    const yieldShort = data["US 13W Yield"]?.price || 0
    const spread = (yield10y - yieldShort).toFixed(2)

    const sections = [
        {
            title: "RATES",
            items: [
                { label: "10Y", value: fmt(yield10y, 'rate') },
                { label: "13W", value: fmt(yieldShort, 'rate') }, // Using 13W as proxy
                { label: "Spread", value: `${spread}bp`, color: Number(spread) < 0 ? "text-rose-500" : "text-emerald-500" }
            ]
        },
        {
            title: "FX",
            items: [
                { label: "DXY", value: fmt(data["Dollar Index"]?.price, 'index') },
                { label: "USD/KRW", value: fmt(data["USD/KRW"]?.price, 'price') },
                { label: "USD/JPY", value: fmt(data["USD/JPY"]?.price, 'price') }
            ]
        },
        {
            title: "LIQUIDITY",
            items: [
                { label: "VIX", value: fmt(data["VIX Volatility Index"]?.price, 'index'), color: data["VIX Volatility Index"]?.price > 20 ? "text-rose-500" : "text-slate-400" },
                { label: "Oil", value: `$${fmt(data["Crude Oil"]?.price, 'price')}` },
                { label: "Copper", value: `$${fmt(data["Copper"]?.price, 'price')}` }
            ]
        },
        {
            title: "ASSETS",
            items: [
                { label: "Gold", value: `$${fmt(data["Gold"]?.price, 'price')}` },
                { label: "Bitcoin", value: `$${fmt(data["Bitcoin"]?.price, 'price')}` },
                { label: "S&P 500", value: fmt(data["S&P 500"]?.price, 'price') }
            ]
        }
    ]

    return (
        <div className={cn(
            "w-full border-b transition-colors duration-300",
            theme === 'dark' ? "bg-[#050505] border-white/5" : "bg-white border-slate-200"
        )}>
            <div className="max-w-7xl mx-auto px-4 py-3">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 md:gap-8">
                    {sections.map((section, idx) => (
                        <div key={idx} className={cn(
                            "flex flex-col gap-1",
                            idx !== sections.length - 1 ? "md:border-r" : "",
                            theme === 'dark' ? "border-white/5" : "border-slate-100"
                        )}>
                            <h4 className="text-[10px] font-bold text-indigo-500 mb-1 tracking-wider">{section.title}</h4>
                            <div className="space-y-0.5">
                                {section.items.map((item, i) => (
                                    <div key={i} className="flex justify-between items-center pr-4 text-xs font-mono">
                                        <span className="text-slate-500">{item.label}</span>
                                        <span className={cn("font-medium", item.color || (theme === 'dark' ? "text-slate-300" : "text-slate-700"))}>
                                            {item.value}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    )
}
