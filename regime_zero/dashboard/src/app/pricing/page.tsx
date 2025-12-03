import Link from "next/link"
import { Check, ArrowLeft } from "lucide-react"

export default function Pricing() {
    return (
        <div className="min-h-screen bg-black text-white p-8">
            <Link href="/" className="text-slate-500 hover:text-white transition-colors flex items-center gap-2 mb-12">
                <ArrowLeft size={20} /> Back to Home
            </Link>

            <div className="max-w-5xl mx-auto">
                <div className="text-center mb-16">
                    <h1 className="text-4xl font-bold mb-4">Access Regime Zero</h1>
                    <p className="text-slate-400">Choose your level of intelligence access.</p>
                </div>

                <div className="grid md:grid-cols-3 gap-8">
                    {/* Basic Plan */}
                    <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-8 flex flex-col">
                        <h3 className="text-xl font-bold text-slate-300">Observer</h3>
                        <div className="text-3xl font-bold mt-4 mb-6">$49<span className="text-sm text-slate-500 font-normal">/mo</span></div>
                        <ul className="space-y-4 mb-8 flex-1">
                            <li className="flex gap-3 text-sm text-slate-300"><Check size={16} className="text-emerald-500" /> Daily Regime Reports</li>
                            <li className="flex gap-3 text-sm text-slate-300"><Check size={16} className="text-emerald-500" /> Basic Graph View</li>
                        </ul>
                        <button className="w-full py-3 border border-slate-700 rounded-lg hover:bg-slate-800 transition-colors">Select Plan</button>
                    </div>

                    {/* Pro Plan */}
                    <div className="bg-slate-900 border border-emerald-500/30 rounded-2xl p-8 flex flex-col relative overflow-hidden">
                        <div className="absolute top-0 right-0 bg-emerald-500 text-black text-xs font-bold px-3 py-1 rounded-bl-lg">POPULAR</div>
                        <h3 className="text-xl font-bold text-white">Analyst</h3>
                        <div className="text-3xl font-bold mt-4 mb-6">$199<span className="text-sm text-slate-500 font-normal">/mo</span></div>
                        <ul className="space-y-4 mb-8 flex-1">
                            <li className="flex gap-3 text-sm text-white"><Check size={16} className="text-emerald-500" /> Real-time Dashboard</li>
                            <li className="flex gap-3 text-sm text-white"><Check size={16} className="text-emerald-500" /> Full History Access</li>
                            <li className="flex gap-3 text-sm text-white"><Check size={16} className="text-emerald-500" /> Terminal Access</li>
                        </ul>
                        <Link href="/dashboard" className="block w-full py-3 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-lg text-center transition-colors">
                            Subscribe via Stripe
                        </Link>
                    </div>

                    {/* Enterprise Plan */}
                    <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-8 flex flex-col">
                        <h3 className="text-xl font-bold text-slate-300">Institution</h3>
                        <div className="text-3xl font-bold mt-4 mb-6">Custom</div>
                        <ul className="space-y-4 mb-8 flex-1">
                            <li className="flex gap-3 text-sm text-slate-300"><Check size={16} className="text-emerald-500" /> API Access</li>
                            <li className="flex gap-3 text-sm text-slate-300"><Check size={16} className="text-emerald-500" /> Custom Data Ingestion</li>
                            <li className="flex gap-3 text-sm text-slate-300"><Check size={16} className="text-emerald-500" /> Dedicated Support</li>
                        </ul>
                        <button className="w-full py-3 border border-slate-700 rounded-lg hover:bg-slate-800 transition-colors">Contact Sales</button>
                    </div>
                </div>
            </div>
        </div>
    )
}
