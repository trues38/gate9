"use client"

import { useEffect, useState, useRef, useMemo, useCallback } from 'react'
import dynamic from 'next/dynamic'
import { Loader2 } from 'lucide-react'

const ForceGraph3D = dynamic(() => import('react-force-graph-3d'), { ssr: false })

// Cluster configuration with 3D positions
const CLUSTERS = {
  sports: {
    position: { x: -300, y: 0, z: 0 },
    color: '#ff6b6b',
    subClusters: {
      NBA: { offset: { x: -50, y: 50, z: 0 }, color: '#ff6b6b' },
      Soccer: { offset: { x: 50, y: -50, z: 0 }, color: '#4ecdc4' }
    }
  },
  economy: {
    position: { x: 300, y: 0, z: 0 },
    color: '#3498db',
    subClusters: {
      Macro: { offset: { x: -50, y: 50, z: 0 }, color: '#3498db' },
      Regime: { offset: { x: 50, y: -50, z: 0 }, color: '#9b59b6' }
    }
  }
}

interface GraphNode {
  id: string
  label: string
  name: string
  cluster: 'sports' | 'economy'
  subCluster?: string
  color?: string
  size?: number
  x?: number
  y?: number
  z?: number
  fx?: number
  fy?: number
  fz?: number
}

interface GraphLink {
  source: string | GraphNode
  target: string | GraphNode
  type: string
}

interface GraphData {
  nodes: GraphNode[]
  links: GraphLink[]
}

export default function ClusteredGraph() {
  const graphRef = useRef<any>(null)
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
  const [cameraDistance, setCameraDistance] = useState(1000)

  // Load graph data from API with fallback to static files
  useEffect(() => {
    async function loadData() {
      setLoading(true)
      setError(null)

      try {
        // Try API first
        const response = await fetch('/api/graph?type=all&limit=6000')

        if (response.ok) {
          const data = await response.json()
          if (data.nodes?.length > 0) {
            setGraphData(applyClusterPositions(data))
            setLoading(false)
            return
          }
        }

        // Fallback to static file
        const staticResponse = await fetch('/viz_data.json')
        if (staticResponse.ok) {
          const staticData = await staticResponse.json()
          // Mark all static data as economy cluster
          const economyData = {
            nodes: staticData.nodes.map((n: any) => ({
              ...n,
              cluster: 'economy' as const,
              subCluster: 'Regime'
            })),
            links: staticData.links
          }
          setGraphData(applyClusterPositions(economyData))
        }
      } catch (err) {
        console.error('Failed to load graph data:', err)
        setError('Failed to load graph data')
      } finally {
        setLoading(false)
      }
    }

    loadData()
  }, [])

  // Apply cluster positions to nodes
  const applyClusterPositions = useCallback((data: GraphData): GraphData => {
    const nodes = data.nodes.map(node => {
      const cluster = CLUSTERS[node.cluster] || CLUSTERS.economy
      const subCluster = node.subCluster && cluster.subClusters[node.subCluster as keyof typeof cluster.subClusters]

      // Calculate position with some randomness
      const baseX = cluster.position.x + (subCluster?.offset.x || 0)
      const baseY = cluster.position.y + (subCluster?.offset.y || 0)
      const baseZ = cluster.position.z + (subCluster?.offset.z || 0)

      // Add random spread within cluster
      const spread = 100
      const x = baseX + (Math.random() - 0.5) * spread
      const y = baseY + (Math.random() - 0.5) * spread
      const z = baseZ + (Math.random() - 0.5) * spread

      return {
        ...node,
        x,
        y,
        z,
        color: subCluster?.color || cluster.color || node.color,
        size: node.size || 4
      }
    })

    return { nodes, links: data.links }
  }, [])

  // LOD: Sample nodes based on camera distance
  const visibleData = useMemo(() => {
    if (cameraDistance > 800) {
      // Far away: show only 20% of nodes
      const sampledNodes = graphData.nodes.filter((_, i) => i % 5 === 0)
      const nodeIds = new Set(sampledNodes.map(n => n.id))
      const sampledLinks = graphData.links.filter(l => {
        const sourceId = typeof l.source === 'string' ? l.source : l.source.id
        const targetId = typeof l.target === 'string' ? l.target : l.target.id
        return nodeIds.has(sourceId) && nodeIds.has(targetId)
      })
      return { nodes: sampledNodes, links: sampledLinks }
    } else if (cameraDistance > 500) {
      // Medium: show 50%
      const sampledNodes = graphData.nodes.filter((_, i) => i % 2 === 0)
      const nodeIds = new Set(sampledNodes.map(n => n.id))
      const sampledLinks = graphData.links.filter(l => {
        const sourceId = typeof l.source === 'string' ? l.source : l.source.id
        const targetId = typeof l.target === 'string' ? l.target : l.target.id
        return nodeIds.has(sourceId) && nodeIds.has(targetId)
      })
      return { nodes: sampledNodes, links: sampledLinks }
    }
    return graphData
  }, [graphData, cameraDistance])

  // Handle node click
  const handleNodeClick = useCallback((node: GraphNode) => {
    setSelectedNode(node)

    // Center camera on node
    if (graphRef.current) {
      const distance = 150
      graphRef.current.cameraPosition(
        { x: node.x! + distance, y: node.y! + distance, z: node.z! + distance },
        { x: node.x, y: node.y, z: node.z },
        1500
      )
    }
  }, [])

  if (loading) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-black">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-emerald-500 mx-auto mb-2" />
          <p className="text-slate-400 text-sm">Loading graph data...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-black">
        <p className="text-red-400 text-sm">{error}</p>
      </div>
    )
  }

  return (
    <div className="relative w-full h-full">
      <ForceGraph3D
        ref={graphRef}
        graphData={visibleData}
        backgroundColor="#000000"

        // Node appearance
        nodeLabel={(node: any) => `${node.name} (${node.label})`}
        nodeColor={(node: any) => node.color || '#888888'}
        nodeVal={(node: any) => node.size || 4}
        nodeResolution={6}
        nodeOpacity={0.9}

        // Link appearance
        linkColor={() => 'rgba(255,255,255,0.15)'}
        linkWidth={0.5}
        linkOpacity={0.3}
        linkDirectionalParticles={0}

        // Physics optimization
        warmupTicks={50}
        cooldownTicks={100}
        cooldownTime={3000}
        d3AlphaDecay={0.05}
        d3VelocityDecay={0.3}

        // Interactions
        onNodeClick={handleNodeClick}
        onZoom={(zoom: any) => setCameraDistance(1000 / zoom.k)}

        // Performance
        enableNodeDrag={false}
        enableNavigationControls={true}
        showNavInfo={false}
      />

      {/* Cluster Labels */}
      <div className="absolute top-4 left-4 space-y-2 pointer-events-none">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-[#ff6b6b]" />
          <span className="text-xs text-slate-400">Sports (NBA + Soccer)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-[#3498db]" />
          <span className="text-xs text-slate-400">Economy (Macro + Regimes)</span>
        </div>
      </div>

      {/* Node Count */}
      <div className="absolute bottom-4 left-4 text-xs text-slate-500">
        {visibleData.nodes.length.toLocaleString()} nodes / {visibleData.links.length.toLocaleString()} links
      </div>

      {/* Selected Node Info */}
      {selectedNode && (
        <div className="absolute top-4 right-4 bg-slate-900/90 border border-slate-700 rounded-lg p-4 max-w-xs backdrop-blur-sm">
          <button
            onClick={() => setSelectedNode(null)}
            className="absolute top-2 right-2 text-slate-500 hover:text-white"
          >
            &times;
          </button>
          <h3 className="font-bold text-white mb-1">{selectedNode.name}</h3>
          <p className="text-xs text-slate-400 mb-2">
            {selectedNode.label} - {selectedNode.cluster}
            {selectedNode.subCluster && ` (${selectedNode.subCluster})`}
          </p>
        </div>
      )}
    </div>
  )
}
