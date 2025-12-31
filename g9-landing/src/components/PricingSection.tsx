'use client';

import { motion } from 'framer-motion';
import GlowButton from './GlowButton';

const plans = [
  {
    tier: 'Starter',
    price: '49',
    description: 'Perfect for individual analysts',
    features: ['5 Daily Signals', 'Basic Analytics Dashboard', 'Email Alerts', '1 Product Access', 'Community Support'],
  },
  {
    tier: 'Pro',
    price: '149',
    description: 'For serious data-driven decisions',
    features: ['Unlimited Signals', 'Advanced Analytics Suite', 'Real-time Alerts', 'Both Products Access', 'API Access', 'Priority Support'],
    featured: true,
  },
  {
    tier: 'Enterprise',
    price: 'Custom',
    description: 'For teams and institutions',
    features: ['Everything in Pro', 'Custom Integrations', 'Dedicated Account Manager', 'SLA Guarantee', 'White-label Options', 'On-premise Deployment'],
  },
];

export default function PricingSection() {
  return (
    <section className="py-24 bg-[#0a0f1a]">
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
            Simple Pricing
          </h2>
          <p className="text-xl text-slate-400 max-w-2xl mx-auto">
            Start free, scale as you grow. No hidden fees.
          </p>
        </motion.div>

        <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
          {plans.map((plan, i) => (
            <motion.div
              key={plan.tier}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
              className={`
                relative p-8 rounded-2xl
                ${plan.featured
                  ? 'bg-gradient-to-b from-cyan-500/10 to-purple-500/10 border-2 border-cyan-500/50 scale-105'
                  : 'bg-slate-800/50 border border-slate-700/50'
                }
              `}
            >
              {plan.featured && (
                <div className="absolute -top-4 left-1/2 -translate-x-1/2 px-4 py-1 bg-gradient-to-r from-cyan-500 to-purple-500 rounded-full text-sm font-semibold">
                  MOST POPULAR
                </div>
              )}

              <h3 className="text-xl font-semibold text-slate-300">{plan.tier}</h3>
              <p className="text-sm text-slate-500 mt-1">{plan.description}</p>

              <div className="mt-6 mb-6">
                <span
                  className="text-5xl font-bold text-white"
                  style={{ fontFamily: 'Orbitron, sans-serif' }}
                >
                  {plan.price === 'Custom' ? '' : '$'}{plan.price}
                </span>
                {plan.price !== 'Custom' && (
                  <span className="text-slate-400">/month</span>
                )}
              </div>

              <ul className="space-y-3 mb-8">
                {plan.features.map((feature) => (
                  <li key={feature} className="flex items-center gap-2 text-slate-300">
                    <span className="text-cyan-400">✓</span>
                    {feature}
                  </li>
                ))}
              </ul>

              <GlowButton
                variant={plan.featured ? 'gradient' : 'cyan'}
                className="w-full justify-center"
              >
                {plan.price === 'Custom' ? 'Contact Sales' : 'Get Started'}
              </GlowButton>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
