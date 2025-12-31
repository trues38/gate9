'use client';

import { motion } from 'framer-motion';

interface FeatureCardProps {
  icon: string;
  title: string;
  description: string;
  delay?: number;
}

export default function FeatureCard({ icon, title, description, delay = 0 }: FeatureCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.5, delay }}
      whileHover={{ y: -5, boxShadow: '0 0 30px rgba(0,245,255,0.1)' }}
      className="
        group p-6 rounded-2xl
        bg-gradient-to-b from-slate-800/50 to-slate-900/50
        border border-slate-700/50
        hover:border-cyan-500/50
        transition-all duration-300
      "
    >
      <div className="
        w-12 h-12 rounded-lg mb-4
        bg-gradient-to-br from-cyan-500/20 to-purple-500/20
        flex items-center justify-center text-2xl
        group-hover:scale-110 transition-transform
      ">
        {icon}
      </div>
      <h3 className="text-xl font-semibold text-white mb-2">{title}</h3>
      <p className="text-slate-400 leading-relaxed">{description}</p>
    </motion.div>
  );
}
