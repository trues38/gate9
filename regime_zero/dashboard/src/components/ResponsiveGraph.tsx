"use client"

import { useEffect, useState, useCallback } from 'react'
import dynamic from 'next/dynamic'
import { Loader2 } from 'lucide-react'

// Dynamic imports for graph components (no SSR)
const GraphView = dynamic(() => import('./GraphView'), {
  ssr: false,
  loading: () => <GraphLoader />
})

const GraphView3D = dynamic(() => import('./GraphView3D'), {
  ssr: false,
  loading: () => <GraphLoader />
})

function GraphLoader() {
  return (
    <div className="absolute inset-0 flex items-center justify-center bg-black/50">
      <div className="text-center">
        <Loader2 className="w-8 h-8 animate-spin text-emerald-500 mx-auto mb-2" />
        <p className="text-slate-400 text-sm">Loading graph...</p>
      </div>
    </div>
  )
}

interface ResponsiveGraphProps {
  className?: string
  showLabels?: boolean
  interactive?: boolean
}

export default function ResponsiveGraph({
  className = '',
  showLabels = false,
  interactive = true
}: ResponsiveGraphProps) {
  const [is3D, setIs3D] = useState(true)
  const [isMounted, setIsMounted] = useState(false)

  // Detect device capabilities
  const checkDevice = useCallback(() => {
    if (typeof window === 'undefined') return

    const width = window.innerWidth
    const isMobile = width < 768
    const isLowPower = navigator.hardwareConcurrency
      ? navigator.hardwareConcurrency < 4
      : false
    const prefersReducedMotion = window.matchMedia(
      '(prefers-reduced-motion: reduce)'
    ).matches

    // Use 2D for mobile, low-power devices, or reduced motion preference
    setIs3D(!isMobile && !isLowPower && !prefersReducedMotion)
  }, [])

  useEffect(() => {
    setIsMounted(true)
    checkDevice()

    // Listen for resize
    window.addEventListener('resize', checkDevice)
    return () => window.removeEventListener('resize', checkDevice)
  }, [checkDevice])

  if (!isMounted) {
    return <GraphLoader />
  }

  return (
    <div className={`relative ${className}`}>
      {is3D ? (
        <GraphView3D />
      ) : (
        <GraphView viewMode={interactive ? 'immersive' : 'initial'} />
      )}

      {/* Toggle button for desktop */}
      {typeof window !== 'undefined' && window.innerWidth >= 768 && (
        <button
          onClick={() => setIs3D(!is3D)}
          className="absolute bottom-4 right-4 px-3 py-1.5 bg-slate-800/80 hover:bg-slate-700 border border-slate-700 rounded-full text-xs text-slate-300 backdrop-blur-sm transition-colors z-10"
        >
          {is3D ? '2D View' : '3D View'}
        </button>
      )}
    </div>
  )
}
