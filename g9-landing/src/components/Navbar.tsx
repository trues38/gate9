'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import GlowButton from './GlowButton';

export default function Navbar() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 glass">
      <div className="container mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          {/* Logo */}
          <a
            href="#"
            className="text-2xl font-bold text-white"
            style={{ fontFamily: 'Orbitron, sans-serif' }}
          >
            <span className="text-cyan-400">G9</span> Intelligence
          </a>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center gap-8">
            <a href="#features" className="text-slate-300 hover:text-cyan-400 transition">
              Features
            </a>
            <a href="#products" className="text-slate-300 hover:text-cyan-400 transition">
              Products
            </a>
            <a href="#pricing" className="text-slate-300 hover:text-cyan-400 transition">
              Pricing
            </a>
            <a href="#" className="text-slate-300 hover:text-cyan-400 transition">
              Docs
            </a>
          </div>

          {/* CTA Buttons */}
          <div className="hidden md:flex items-center gap-4">
            <a href="#" className="text-slate-300 hover:text-white transition">
              Sign In
            </a>
            <GlowButton size="sm">Get Started</GlowButton>
          </div>

          {/* Mobile Menu Button */}
          <button
            onClick={() => setIsOpen(!isOpen)}
            className="md:hidden text-white p-2"
          >
            <svg
              className="w-6 h-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              {isOpen ? (
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              ) : (
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 6h16M4 12h16M4 18h16"
                />
              )}
            </svg>
          </button>
        </div>

        {/* Mobile Menu */}
        <AnimatePresence>
          {isOpen && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="md:hidden mt-4 pb-4"
            >
              <div className="flex flex-col gap-4">
                <a href="#features" className="text-slate-300 hover:text-cyan-400 transition">
                  Features
                </a>
                <a href="#products" className="text-slate-300 hover:text-cyan-400 transition">
                  Products
                </a>
                <a href="#pricing" className="text-slate-300 hover:text-cyan-400 transition">
                  Pricing
                </a>
                <a href="#" className="text-slate-300 hover:text-cyan-400 transition">
                  Docs
                </a>
                <hr className="border-slate-700" />
                <a href="#" className="text-slate-300 hover:text-white transition">
                  Sign In
                </a>
                <GlowButton size="sm" className="w-full">
                  Get Started
                </GlowButton>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </nav>
  );
}
