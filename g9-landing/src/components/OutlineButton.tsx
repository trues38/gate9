'use client';

import { motion } from 'framer-motion';

interface OutlineButtonProps {
  children: React.ReactNode;
  onClick?: () => void;
  className?: string;
}

export default function OutlineButton({
  children,
  onClick,
  className = '',
}: OutlineButtonProps) {
  return (
    <motion.button
      whileHover={{ scale: 1.05, borderColor: 'rgba(0,245,255,0.5)' }}
      whileTap={{ scale: 0.95 }}
      className={`
        px-8 py-4 text-lg font-semibold rounded-lg
        border border-slate-600 text-slate-300
        hover:border-cyan-500 hover:text-cyan-400
        transition-all duration-300
        hover:shadow-[0_0_20px_rgba(0,245,255,0.2)]
        ${className}
      `}
      onClick={onClick}
    >
      {children}
    </motion.button>
  );
}
