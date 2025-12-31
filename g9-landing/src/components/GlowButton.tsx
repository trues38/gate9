'use client';

import { motion } from 'framer-motion';

interface GlowButtonProps {
  children: React.ReactNode;
  variant?: 'cyan' | 'purple' | 'gradient';
  size?: 'sm' | 'md' | 'lg';
  onClick?: () => void;
  className?: string;
}

export default function GlowButton({
  children,
  variant = 'cyan',
  size = 'lg',
  onClick,
  className = '',
}: GlowButtonProps) {
  const variants = {
    cyan: 'bg-cyan-500 hover:bg-cyan-400 shadow-[0_0_30px_rgba(0,245,255,0.4)]',
    purple: 'bg-purple-500 hover:bg-purple-400 shadow-[0_0_30px_rgba(168,85,247,0.4)]',
    gradient: 'bg-gradient-to-r from-cyan-500 to-purple-500 hover:from-cyan-400 hover:to-purple-400',
  };

  const sizes = {
    sm: 'px-4 py-2 text-sm',
    md: 'px-6 py-3 text-base',
    lg: 'px-8 py-4 text-lg',
  };

  return (
    <motion.button
      whileHover={{ scale: 1.05, boxShadow: '0 0 40px rgba(0,245,255,0.5)' }}
      whileTap={{ scale: 0.95 }}
      className={`
        ${variants[variant]} ${sizes[size]}
        font-semibold rounded-lg text-white
        transition-all duration-300
        ${className}
      `}
      onClick={onClick}
    >
      {children}
    </motion.button>
  );
}
