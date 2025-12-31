"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { ArrowRight, Activity, Lock, TrendingUp, Database, Zap } from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"
import dynamic from "next/dynamic"
import { useAuth } from "@/components/auth/AuthProvider"

// Dynamic import for graph with SSR disabled
const ResponsiveGraph = dynamic(() => import("@/components/ResponsiveGraph"), {
  ssr: false,
  loading: () => (
    <div className="absolute inset-0 bg-black flex items-center justify-center">
      <div className="w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
    </div>
  )
})

// Value propositions
const VALUE_PROPS = [
  {
    icon: Database,
    title: "20,000+ Regime Nodes",
    description: "Historical patterns from 2008 to today"
  },
  {
    icon: TrendingUp,
    title: "Real-time Analysis",
    description: "NBA + Soccer + Economic indicators"
  },
  {
    icon: Zap,
    title: "Graph-Powered Insights",
    description: "Neo4j-based structural analysis"
  }
]

export default function Home() {
  const { user, loading } = useAuth()
  const [selectedNode, setSelectedNode] = useState<any>(null)
  const [showPromo, setShowPromo] = useState(false)

  // Show promo after delay
  useEffect(() => {
    const timer = setTimeout(() => setShowPromo(true), 2000)
    return () => clearTimeout(timer)
  }, [])

  return (
    <div className="min-h-screen bg-black text-white overflow-hidden relative font-sans">
      {/* Background Graph - Full Screen */}
      <div className="absolute inset-0 z-0">
        <ResponsiveGraph className="w-full h-full" />
      </div>

      {/* Gradient Overlay for readability */}
      <div className="absolute inset-0 bg-gradient-to-r from-black/80 via-black/40 to-transparent z-10 pointer-events-none" />
      <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-black/40 z-10 pointer-events-none" />

      {/* Left Sidebar: Logo & Info */}
      <div className="absolute top-8 left-8 z-20 flex flex-col gap-6 w-[380px] pointer-events-none">
        {/* Logo Section */}
        <div className="flex items-center gap-3 text-white/90">
          <div className="p-2 bg-white/10 rounded-lg backdrop-blur-md border border-white/20">
            <Activity size={20} className="text-emerald-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-widest font-mono">REGIME ZERO</h1>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-[10px] text-emerald-500 font-mono tracking-wider">SYSTEM ONLINE</span>
            </div>
          </div>
        </div>

        {/* Info Panel */}
        <div className="min-h-[200px] transition-all duration-500 font-mono">
          <AnimatePresence mode="wait">
            {selectedNode ? (
              <motion.div
                key="node-info"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="bg-black/80 backdrop-blur-xl border border-emerald-500/30 p-6 rounded-lg shadow-2xl pointer-events-auto"
              >
                <div className="flex justify-between items-start mb-4 border-b border-emerald-500/20 pb-2">
                  <h2 className="text-xl font-bold text-emerald-400 tracking-tight">
                    <span className="text-emerald-700 mr-2">::</span>
                    {selectedNode.name}
                  </h2>
                  <span className="text-[10px] text-emerald-600 border border-emerald-800 px-2 py-0.5 rounded">
                    ID: {selectedNode.group || "UNK"}
                  </span>
                </div>
                <p className="text-xs text-emerald-600/80 mb-4 flex items-center gap-2">
                  <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" />
                  DETECTED: {selectedNode.date}
                </p>

                <div className="space-y-4 text-xs">
                  <div>
                    <span className="text-[10px] font-bold text-emerald-700 uppercase tracking-widest">Vibe Analysis</span>
                    <p className="text-emerald-100/80 mt-1 leading-relaxed border-l-2 border-emerald-500/30 pl-3">
                      {selectedNode.vibe || "DATA CORRUPTED"}
                    </p>
                  </div>

                  <div>
                    <span className="text-[10px] font-bold text-emerald-700 uppercase tracking-widest">Structural Integrity</span>
                    <p className="text-emerald-100/80 mt-1 leading-relaxed border-l-2 border-emerald-500/30 pl-3">
                      {selectedNode.desc || "NO DATA"}
                    </p>
                  </div>
                </div>
              </motion.div>
            ) : (
              <motion.div
                key="value-props"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="space-y-4"
              >
                {/* Tagline */}
                <div className="p-6 border border-emerald-500/20 rounded-lg bg-black/60 backdrop-blur-sm pointer-events-auto">
                  <h2 className="text-2xl font-bold mb-2 text-white">
                    Graph-Powered
                    <br />
                    <span className="text-emerald-400">Regime Analysis</span>
                  </h2>
                  <p className="text-sm text-slate-400 mb-4">
                    The world's first structural pattern detection system for sports and economic markets.
                  </p>

                  {/* Value Props */}
                  <div className="space-y-3">
                    {VALUE_PROPS.map((prop, idx) => (
                      <div key={idx} className="flex items-center gap-3">
                        <prop.icon className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                        <div>
                          <span className="text-xs font-semibold text-white">{prop.title}</span>
                          <span className="text-xs text-slate-500 ml-2">{prop.description}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Terminal hint */}
                <div className="p-4 border border-slate-800 rounded-lg bg-black/40 text-xs font-mono text-slate-600">
                  &gt; Hover on graph nodes for insights<br />
                  &gt; <span className="animate-pulse">_</span>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* CTA Buttons (Top-Right) */}
      <div className="absolute top-8 right-8 z-20 pointer-events-auto flex gap-4">
        {!loading && (
          <>
            {user ? (
              <Link
                href="/dashboard"
                className="group flex items-center gap-2 px-6 py-3 bg-emerald-600 text-white rounded-full font-bold hover:bg-emerald-500 transition-all shadow-lg shadow-emerald-500/20"
              >
                Dashboard
                <ArrowRight className="group-hover:translate-x-1 transition-transform" size={18} />
              </Link>
            ) : (
              <Link
                href="/login"
                className="group flex items-center gap-2 px-6 py-3 bg-white text-black rounded-full font-bold hover:bg-slate-200 transition-all shadow-lg shadow-white/10"
              >
                Enter System
                <ArrowRight className="group-hover:translate-x-1 transition-transform" size={18} />
              </Link>
            )}

            <Link
              href="/pricing"
              className="flex items-center gap-2 px-6 py-3 bg-slate-900/80 text-white border border-slate-700 rounded-full font-medium hover:bg-slate-800 transition-all backdrop-blur-sm"
            >
              <Lock size={16} />
              Get Pass
            </Link>
          </>
        )}
      </div>

      {/* Bottom Stats Bar */}
      <AnimatePresence>
        {showPromo && (
          <motion.div
            initial={{ opacity: 0, y: 50 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 50 }}
            className="absolute bottom-0 left-0 right-0 z-20 pointer-events-none"
          >
            <div className="max-w-4xl mx-auto px-8 pb-8">
              <div className="flex items-center justify-between gap-8 p-4 bg-slate-900/80 backdrop-blur-lg border border-slate-800 rounded-xl">
                <div className="flex items-center gap-6 text-xs">
                  <div>
                    <span className="text-slate-500 block">Sports Nodes</span>
                    <span className="text-xl font-bold text-white">15,000+</span>
                  </div>
                  <div className="w-px h-8 bg-slate-700" />
                  <div>
                    <span className="text-slate-500 block">Economy Nodes</span>
                    <span className="text-xl font-bold text-white">20,000+</span>
                  </div>
                  <div className="w-px h-8 bg-slate-700" />
                  <div>
                    <span className="text-slate-500 block">Daily Matches</span>
                    <span className="text-xl font-bold text-white">50+</span>
                  </div>
                </div>

                <Link
                  href="/pricing"
                  className="pointer-events-auto flex items-center gap-2 px-5 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-semibold rounded-lg transition-colors"
                >
                  Start from $19
                  <ArrowRight size={16} />
                </Link>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
