"use client"

import { useState } from "react"
import Link from "next/link"
import { ArrowRight, Activity, Lock } from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"
import GraphView from "@/components/GraphView"

export default function Home() {
  const [selectedNode, setSelectedNode] = useState<any>(null)

  return (
    <div className="min-h-screen bg-black text-white overflow-hidden relative font-sans">
      {/* Background Graph */}
      <GraphView onNodeHover={setSelectedNode} />

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

        {/* Info Panel (Fixed Position) */}
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

                  {selectedNode.risks && (
                    <div>
                      <span className="text-[10px] font-bold text-rose-500 uppercase tracking-widest">Critical Risks</span>
                      <ul className="mt-1 space-y-1 text-rose-300/80 pl-3 border-l-2 border-rose-900/50">
                        {selectedNode.risks.map((r: string, i: number) => (
                          <li key={i} className="flex items-start gap-2">
                            <span>!</span> {r}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </motion.div>
            ) : (
              <motion.div
                key="empty-state"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="p-6 border border-emerald-500/20 rounded-lg bg-black/40 backdrop-blur-sm"
              >
                <p className="text-emerald-500/50 text-xs leading-relaxed typing-cursor">
                  &gt; WAITING FOR USER INPUT...<br />
                  &gt; SELECT NODE TO INITIALIZE ANALYSIS<br />
                  &gt; <span className="animate-pulse">_</span>
                </p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Buttons Section (Fixed Top-Right) */}
      <div className="absolute top-8 right-8 z-20 pointer-events-auto flex gap-4">
        <Link
          href="/login"
          className="group flex items-center gap-2 px-6 py-3 bg-white text-black rounded-full font-bold hover:bg-slate-200 transition-all shadow-lg shadow-white/10"
        >
          Enter System
          <ArrowRight className="group-hover:translate-x-1 transition-transform" size={18} />
        </Link>

        <Link
          href="/pricing"
          className="flex items-center gap-2 px-6 py-3 bg-slate-900/80 text-white border border-slate-700 rounded-full font-medium hover:bg-slate-800 transition-all backdrop-blur-sm"
        >
          <Lock size={16} />
          Access Plans
        </Link>
      </div>
    </div>
  )
}
