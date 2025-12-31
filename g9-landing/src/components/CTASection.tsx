'use client';

import { motion } from 'framer-motion';
import GlowButton from './GlowButton';

export default function CTASection() {
  return (
    <section className="py-24 relative overflow-hidden">
      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-to-r from-cyan-500/10 to-purple-500/10" />

      {/* Grid pattern */}
      <div
        className="absolute inset-0 opacity-10"
        style={{
          backgroundImage: `
            linear-gradient(rgba(0, 245, 255, 0.1) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0, 245, 255, 0.1) 1px, transparent 1px)
          `,
          backgroundSize: '50px 50px',
        }}
      />

      <div className="container mx-auto px-6 text-center relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
        >
          <h2
            className="text-4xl md:text-5xl font-bold text-white mb-6"
            style={{ fontFamily: 'Space Grotesk, sans-serif' }}
          >
            Ready to Transform Your Data?
          </h2>
          <p className="text-xl text-slate-400 mb-10 max-w-2xl mx-auto">
            Join thousands of professionals making smarter decisions with G9 Intelligence.
          </p>

          <div className="flex flex-wrap gap-4 justify-center">
            <GlowButton variant="gradient" size="lg">
              Start Your Free Trial
            </GlowButton>
          </div>

          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="mt-12 flex flex-wrap justify-center gap-8 text-slate-500"
          >
            <div className="flex items-center gap-2">
              <span className="text-green-400">✓</span>
              14-day free trial
            </div>
            <div className="flex items-center gap-2">
              <span className="text-green-400">✓</span>
              No credit card required
            </div>
            <div className="flex items-center gap-2">
              <span className="text-green-400">✓</span>
              Cancel anytime
            </div>
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
}
