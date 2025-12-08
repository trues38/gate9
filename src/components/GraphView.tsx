"use client"

import { useEffect, useState, useRef } from "react"
import dynamic from "next/dynamic"
import { useRouter } from "next/navigation"

// Dynamically import ForceGraph2D with no SSR
const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
    ssr: false,
    loading: () => <div className="text-slate-500">Loading Graph Engine...</div>
})

export default function GraphView({ onNodeHover }: { onNodeHover?: (node: any) => void }) {
    const [data, setData] = useState({ nodes: [], links: [] })
    const [dimensions, setDimensions] = useState({ width: 800, height: 600 })
    const [viewMode, setViewMode] = useState<'initial' | 'immersive'>('initial')
    const router = useRouter()
    const graphRef = useRef<any>(null)

    useEffect(() => {
        // Set dimensions
        setDimensions({
            width: window.innerWidth,
            height: window.innerHeight
        })

        // Timer for view mode transition
        const timer = setTimeout(() => {
            setViewMode('immersive')
        }, 5000)

        // Fetch Data
        Promise.all([
            fetch('/viz_data.json').then(res => res.json()),
            fetch('/twin_data.json').then(res => res.json()).catch(() => null)
        ]).then(([graphData, twinData]) => {
            // Process Twin Data if exists
            if (twinData) {
                const nodeIds = new Set(graphData.nodes.map((n: any) => n.id))
                if (nodeIds.has(twinData.source) && nodeIds.has(twinData.target)) {
                    graphData.links.push({
                        source: twinData.source,
                        target: twinData.target,
                        value: 5,
                        type: 'twin',
                        color: '#ff0055'
                    })
                }
            }
            setData(graphData)
        })

        // Resize handler
        const handleResize = () => {
            setDimensions({
                width: window.innerWidth,
                height: window.innerHeight
            })
        }
        window.addEventListener('resize', handleResize)
        return () => {
            window.removeEventListener('resize', handleResize)
            clearTimeout(timer)
        }
    }, [])

    useEffect(() => {
        if (graphRef.current) {
            // Universe Physics
            graphRef.current.d3Force('charge').strength(-120) // Repulsion
            graphRef.current.d3Force('link').distance(70) // Link length
            graphRef.current.d3Force('center', null) // Allow drifting
        }
    }, [data])

    return (
        <div className="fixed inset-0 z-0 bg-black">
            <ForceGraph2D
                ref={graphRef}
                width={dimensions.width}
                height={dimensions.height}
                graphData={data}
                nodeLabel="name"
                nodeAutoColorBy="group"
                nodeVal={(node: any) => (node.val || 1) * 1.5}
                linkWidth={(link: any) => link.type === 'twin' ? 0 : (link.value || 1) * 0.5}
                linkColor={(link: any) => link.type === 'twin' ? 'transparent' : 'rgba(100, 255, 218, 0.15)'}
                linkDirectionalParticles={0}
                linkDirectionalParticleSpeed={(link: any) => link.type === 'twin' ? 0.01 : 0}
                linkDirectionalParticleWidth={4}
                backgroundColor="#000000"
                cooldownTicks={100}
                onEngineStop={() => graphRef.current?.zoomToFit(400)}
                onNodeClick={(node: any) => {
                    // Center graph on node
                    graphRef.current?.centerAt(node.x, node.y, 1000)
                    graphRef.current?.zoom(6, 2000)
                    if (onNodeHover) onNodeHover(node)
                }}
                onNodeHover={(node: any) => {
                    if (onNodeHover) onNodeHover(node)
                }}
                nodeCanvasObject={(node: any, ctx, globalScale) => {
                    const isInitial = viewMode === 'initial'
                    const label = node.name
                    const fontSize = 12 / globalScale

                    // Node Drawing
                    ctx.beginPath()
                    ctx.arc(node.x, node.y, (node.val || 1) * 4, 0, 2 * Math.PI, false)

                    // Color Logic: White in initial, Group color in immersive
                    if (isInitial) {
                        ctx.fillStyle = 'rgba(255, 255, 255, 0.9)'
                        ctx.shadowBlur = 15
                        ctx.shadowColor = 'rgba(255, 255, 255, 0.5)'
                    } else {
                        ctx.fillStyle = node.color || '#00ffcc'
                        ctx.shadowBlur = 0
                        ctx.shadowColor = 'transparent'
                    }
                    ctx.fill()

                    // Reset shadow for text
                    ctx.shadowBlur = 0

                    // Label Logic: Show in initial, or if hovered (handled by hover logic usually, but we can force it here if needed)
                    // Note: onNodeHover prop handles the external UI. 
                    // For canvas text:
                    if (isInitial) {
                        ctx.font = `${fontSize}px Sans-Serif`
                        ctx.textAlign = 'center'
                        ctx.textBaseline = 'middle'
                        ctx.fillStyle = 'rgba(255, 255, 255, 0.8)'
                        ctx.fillText(label, node.x, node.y + (node.val || 1) * 4 + fontSize)
                    }
                }}
            />
        </div>
    )
}
