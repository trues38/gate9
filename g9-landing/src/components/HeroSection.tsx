'use client';

import { motion } from 'framer-motion';
import GridBackground from './GridBackground';
import GradientOrbs from './GradientOrbs';
import ParticleField from './ParticleField';
import GlowButton from './GlowButton';
import OutlineButton from './OutlineButton';
import DashboardMockup from './DashboardMockup';

export default function HeroSection() {
  return (
    <section className="relative min-h-screen flex items-center overflow-hidden">
      {/* Background Effects */}
      <GridBackground />
      <GradientOrbs />
      <ParticleField particleCount={60} />

      <div className="relative z-10 container mx-auto px-6 py-20">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          {/* Left: Content */}
          <motion.div
            initial={{ opacity: 0, x: -50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8 }}
          >
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              className="inline-block px-4 py-2 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 text-sm mb-6"
            >
              AI-Powered Analytics Platform
            </motion.div>

            <h1
              className="text-4xl sm:text-5xl md:text-7xl font-bold leading-tight"
              style={{ fontFamily: 'Orbitron, sans-serif' }}
            >
              <motion.span
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.6, delay: 0.3 }}
                className="text-white"
              >
                G9 Intelligence
              </motion.span>
              <br />
              <motion.span
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.6, delay: 0.5 }}
                className="bg-gradient-to-r from-cyan-400 to-purple-500 bg-clip-text text-transparent"
              >
                DataLabs
              </motion.span>
            </h1>

            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.7 }}
              className="text-xl text-slate-400 mt-6 max-w-lg"
            >
              Advanced AI analytics platform combining sports betting intelligence
              and economic regime analysis. Transform data into actionable insights.
            </motion.p>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.9 }}
              className="flex flex-wrap gap-4 mt-10"
            >
              <GlowButton variant="gradient">Start Free Trial</GlowButton>
              <OutlineButton>Watch Demo</OutlineButton>
            </motion.div>

            {/* Trust indicators */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.6, delay: 1.1 }}
              className="flex items-center gap-6 mt-12"
            >
              <div className="flex -space-x-2">
                {[1, 2, 3, 4].map((i) => (
                  <div
                    key={i}
                    className="w-10 h-10 rounded-full bg-gradient-to-br from-slate-600 to-slate-800 border-2 border-slate-900"
                  />
                ))}
              </div>
              <div className="text-slate-400">
                <span className="text-white font-semibold">1,000+</span> professionals trust G9
              </div>
            </motion.div>
          </motion.div>

          {/* Right: Dashboard Preview */}
          <motion.div
            initial={{ opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="relative hidden lg:block"
          >
            <DashboardMockup />
          </motion.div>
        </div>
      </div>
    </section>
  );
}
