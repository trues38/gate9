'use client';

import { motion } from 'framer-motion';
import FeatureCard from './FeatureCard';

const features = [
  {
    icon: '🎯',
    title: 'Sports Betting Intelligence',
    description: 'Real-time odds analysis, edge detection, and value betting signals powered by machine learning.',
  },
  {
    icon: '📊',
    title: 'Economic Regime Analysis',
    description: 'Identify market regimes, economic cycles, and macro trends with our proprietary detection system.',
  },
  {
    icon: '⚡',
    title: 'Real-time Processing',
    description: 'Process millions of data points in milliseconds. Get insights before the market moves.',
  },
  {
    icon: '🧠',
    title: 'AI-Powered Predictions',
    description: 'Advanced neural networks trained on historical patterns for high-accuracy forecasting.',
  },
  {
    icon: '🔗',
    title: 'Graph-Based Memory',
    description: 'Neo4j-powered knowledge graph that learns and remembers market patterns over time.',
  },
  {
    icon: '📈',
    title: 'Custom Dashboards',
    description: 'Build your own views with interactive charts, alerts, and automated reporting.',
  },
];

export default function FeaturesSection() {
  return (
    <section className="py-24 bg-[#0a0f1a] relative">
      {/* Background accent */}
      <div className="absolute inset-0 bg-gradient-to-b from-purple-500/5 via-transparent to-cyan-500/5" />

      <div className="container mx-auto px-6 relative z-10">
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
            Powerful Features
          </h2>
          <p className="text-xl text-slate-400 max-w-2xl mx-auto">
            Everything you need to make data-driven decisions in sports and economics
          </p>
        </motion.div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature, i) => (
            <FeatureCard key={i} {...feature} delay={i * 0.1} />
          ))}
        </div>
      </div>
    </section>
  );
}
