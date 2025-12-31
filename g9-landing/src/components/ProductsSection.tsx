'use client';

import { motion } from 'framer-motion';

const products = [
  {
    name: 'G9-Sport',
    tagline: 'Edge Detection Engine',
    description: 'AI-powered sports betting analytics with real-time odds tracking, sharp money detection, and value identification.',
    color: 'cyan',
    features: ['Real-time Odds Comparison', 'Line Movement Alerts', 'Value Betting Signals', 'Sharp Money Tracking'],
    stats: [
      { label: 'Daily Signals', value: '50+' },
      { label: 'Avg Edge', value: '3.2%' },
    ],
  },
  {
    name: 'G9-Economy',
    tagline: 'Regime Analysis Platform',
    description: 'Economic cycle detection and macro trend analysis powered by graph-based AI and historical pattern matching.',
    color: 'purple',
    features: ['Regime Detection', 'Economic Indicators', 'Scenario Planning', 'Risk Assessment'],
    stats: [
      { label: 'Indicators', value: '200+' },
      { label: 'Accuracy', value: '94.7%' },
    ],
  },
];

export default function ProductsSection() {
  return (
    <section className="py-24 bg-gradient-to-b from-[#0a0f1a] to-slate-900">
      <div className="container mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <h2
            className="text-4xl md:text-5xl font-bold text-white mb-4"
            style={{ fontFamily: 'Space Grotesk, sans-serif' }}
          >
            Two Engines, One Platform
          </h2>
          <p className="text-xl text-slate-400 max-w-2xl mx-auto">
            Choose your focus or use both for comprehensive market intelligence
          </p>
        </motion.div>

        <div className="grid md:grid-cols-2 gap-8 max-w-5xl mx-auto">
          {products.map((product, i) => (
            <motion.div
              key={product.name}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: i * 0.2 }}
              whileHover={{ y: -5 }}
              className={`
                relative p-8 rounded-2xl
                bg-gradient-to-b from-slate-800/50 to-slate-900/50
                border-2 ${product.color === 'cyan' ? 'border-cyan-500/30 hover:border-cyan-500/60' : 'border-purple-500/30 hover:border-purple-500/60'}
                transition-all duration-300
              `}
            >
              {/* Product header */}
              <div className="mb-6">
                <h3
                  className={`text-3xl font-bold ${product.color === 'cyan' ? 'text-cyan-400' : 'text-purple-400'}`}
                  style={{ fontFamily: 'Orbitron, sans-serif' }}
                >
                  {product.name}
                </h3>
                <p className="text-slate-500 mt-1">{product.tagline}</p>
              </div>

              <p className="text-slate-300 mb-6">{product.description}</p>

              {/* Features list */}
              <ul className="space-y-2 mb-6">
                {product.features.map((feature) => (
                  <li key={feature} className="flex items-center gap-2 text-slate-400">
                    <span className={product.color === 'cyan' ? 'text-cyan-400' : 'text-purple-400'}>
                      ✓
                    </span>
                    {feature}
                  </li>
                ))}
              </ul>

              {/* Stats */}
              <div className="grid grid-cols-2 gap-4 pt-6 border-t border-slate-700/50">
                {product.stats.map((stat) => (
                  <div key={stat.label}>
                    <p className="text-sm text-slate-500">{stat.label}</p>
                    <p
                      className={`text-2xl font-bold ${product.color === 'cyan' ? 'text-cyan-400' : 'text-purple-400'}`}
                      style={{ fontFamily: 'JetBrains Mono, monospace' }}
                    >
                      {stat.value}
                    </p>
                  </div>
                ))}
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
