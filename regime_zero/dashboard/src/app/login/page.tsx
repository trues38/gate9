import Link from "next/link"
import { ArrowLeft } from "lucide-react"

export default function Login() {
    return (
        <div className="min-h-screen bg-black text-white flex flex-col items-center justify-center p-4">
            <Link href="/" className="absolute top-8 left-8 text-slate-500 hover:text-white transition-colors flex items-center gap-2">
                <ArrowLeft size={20} /> Back
            </Link>

            <div className="w-full max-w-md space-y-8">
                <div className="text-center">
                    <h2 className="text-3xl font-bold tracking-tight">Welcome Back</h2>
                    <p className="text-slate-400 mt-2">Sign in to access your terminal</p>
                </div>

                <div className="space-y-4">
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-slate-300">Email</label>
                        <input
                            type="email"
                            className="w-full px-4 py-3 bg-slate-900 border border-slate-800 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 text-white placeholder:text-slate-600"
                            placeholder="analyst@regime.zero"
                        />
                    </div>
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-slate-300">Password</label>
                        <input
                            type="password"
                            className="w-full px-4 py-3 bg-slate-900 border border-slate-800 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 text-white"
                            placeholder="••••••••"
                        />
                    </div>

                    <Link
                        href="/dashboard"
                        className="block w-full py-3 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-lg text-center transition-colors mt-6"
                    >
                        Sign In
                    </Link>
                </div>

                <div className="text-center text-sm text-slate-500">
                    Don't have an account? <Link href="/pricing" className="text-emerald-500 hover:underline">Subscribe now</Link>
                </div>
            </div>
        </div>
    )
}
