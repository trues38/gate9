'use client';

import { motion } from 'framer-motion';

export default function DashboardMockup() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.8, delay: 0.4 }}
      className="relative"
    >
      {/* Glow effect behind */}
      <div className="absolute -inset-4 bg-gradient-to-r from-cyan-500/20 to-purple-500/20 blur-3xl" />

      {/* Mock dashboard */}
      <div className="relative bg-slate-900/90 rounded-2xl border border-slate-700/50 p-6 backdrop-blur-sm shadow-2xl">
        {/* Header */}
        <div className="flex items-center gap-2 mb-6">
          <div className="w-3 h-3 rounded-full bg-red-500" />
          <div className="w-3 h-3 rounded-full bg-yellow-500" />
          <div className="w-3 h-3 rounded-full bg-green-500" />
          <span className="ml-4 text-slate-500 text-sm">G9 Dashboard</span>
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          {[
            { label: 'Accuracy', value: '94.7%', trend: 'up' },
            { label: 'Signals', value: '1,247', trend: 'up' },
            { label: 'ROI', value: '+18.3%', trend: 'up' },
          ].map((stat, i) => (
            <div key={i} className="bg-slate-800/50 rounded-lg p-3">
              <p className="text-xs text-slate-400">{stat.label}</p>
              <p className="text-lg font-bold text-white" style={{ fontFamily: 'JetBrains Mono' }}>
                {stat.value}
              </p>
              <span className="text-xs text-green-400">+2.1%</span>
            </div>
          ))}
        </div>

        {/* Chart placeholder */}
        <div className="h-32 bg-slate-800/30 rounded-lg flex items-end justify-around p-4">
          {[40, 65, 45, 80, 55, 90, 70, 85, 60].map((h, i) => (
            <motion.div
              key={i}
              initial={{ height: 0 }}
              animate={{ height: `${h}%` }}
              transition={{ duration: 0.8, delay: 0.5 + i * 0.1 }}
              className="w-4 bg-gradient-to-t from-cyan-500 to-purple-500 rounded-t"
            />
          ))}
        </div>

        {/* Bottom row */}
        <div className="grid grid-cols-2 gap-4 mt-4">
          <div className="bg-slate-800/50 rounded-lg p-3">
            <p className="text-xs text-slate-400 mb-1">Current Regime</p>
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-green-500" />
              <span className="text-sm font-medium text-green-400">Expansion</span>
            </div>
          </div>
          <div className="bg-slate-800/50 rounded-lg p-3">
            <p className="text-xs text-slate-400 mb-1">Active Signals</p>
            <p className="text-lg font-bold text-cyan-400" style={{ fontFamily: 'JetBrains Mono' }}>
              12
            </p>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
