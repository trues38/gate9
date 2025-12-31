"use client"

import { useEffect, useState, useRef } from "react"
import dynamic from "next/dynamic"
import { Canvas } from "@react-three/fiber"
import { OrbitControls, Environment, PerspectiveCamera } from "@react-three/drei"
import * as THREE from "three"

// Dynamically import ForceGraph3D with no SSR
const ForceGraph3D = dynamic(() => import("react-force-graph-3d"), {
    ssr: false,
    loading: () => <div className="text-slate-500">Initializing 3D Regime Universe...</div>
})

// Holographic Sphere Component
function HolographicSphere() {
    const meshRef = useRef<THREE.Mesh>(null)

    useEffect(() => {
        if (meshRef.current) {
            // Animate rotation
            const animate = () => {
                if (meshRef.current) {
                    meshRef.current.rotation.y += 0.001
                    meshRef.current.rotation.x += 0.0005
                }
                requestAnimationFrame(animate)
            }
            animate()
        }
    }, [])

    return (
        <mesh ref={meshRef} position={[0, 0, 0]}>
            <sphereGeometry args={[500, 64, 64]} />
            <meshBasicMaterial
                color="#00ffff"
                transparent
                opacity={0.05}
                wireframe
                side={THREE.BackSide}
            />
        </mesh>
    )
}

export default function GraphView3D({ onNodeHover }: { onNodeHover?: (node: any) => void }) {
    const [data, setData] = useState({ nodes: [], links: [] })
    const [selectedNode, setSelectedNode] = useState<any>(null)
    const [viewMode, setViewMode] = useState<'initial' | 'immersive'>('initial')
    const graphRef = useRef<any>(null)
    const [robotLoaded, setRobotLoaded] = useState(false)

    // 🚀 PERFORMANCE: Reuse geometry and materials (don't create per node)
    const sharedGeometry = useRef<Map<number, THREE.SphereGeometry>>(new Map())
    const sharedMaterial = useRef<Map<string, THREE.MeshBasicMaterial>>(new Map())

    useEffect(() => {
        // Timer for view mode transition (Iron Man style reveal)
        const timer = setTimeout(() => {
            setViewMode('immersive')
        }, 3000)

        // Fetch Regime Data
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

            // Add 3D coordinates
            graphData.nodes = graphData.nodes.map((node: any) => ({
                ...node,
                // Random initial 3D position for force simulation
                fx: undefined,
                fy: undefined,
                fz: undefined
            }))

            setData(graphData)
        })

        return () => clearTimeout(timer)
    }, [])

    useEffect(() => {
        if (graphRef.current && data.nodes.length > 0) {
            // 🚀 PERFORMANCE: Optimize force physics
            graphRef.current.d3Force('charge').strength(-150) // Reduced from -200
            graphRef.current.d3Force('link').distance(60) // Reduced from 80

            // Keep gentle rotation for visual interest
            const rotateCamera = () => {
                if (graphRef.current) {
                    const distance = 400
                    const angle = Date.now() * 0.0001 // Slow rotation
                    graphRef.current.cameraPosition({
                        x: distance * Math.sin(angle),
                        y: 150,
                        z: distance * Math.cos(angle)
                    })
                }
                requestAnimationFrame(rotateCamera)
            }
            setTimeout(rotateCamera, 6000) // Start after initial animation

            // Camera animation after data loads
            setTimeout(() => {
                graphRef.current?.cameraPosition(
                    { x: 300, y: 300, z: 300 }, // position
                    { x: 0, y: 0, z: 0 }, // lookAt
                    3000 // transition duration
                )
            }, 1000)
        }
    }, [data])

    // 🚀 PERFORMANCE: Get or create shared geometry
    const getGeometry = (size: number) => {
        if (!sharedGeometry.current.has(size)) {
            // Lower resolution: 8 segments instead of 16
            sharedGeometry.current.set(size, new THREE.SphereGeometry(size, 8, 8))
        }
        return sharedGeometry.current.get(size)!
    }

    // 🚀 PERFORMANCE: Get or create shared material
    const getMaterial = (color: number, opacity: number = 0.8) => {
        const key = `${color}_${opacity}`
        if (!sharedMaterial.current.has(key)) {
            sharedMaterial.current.set(key, new THREE.MeshBasicMaterial({
                color,
                transparent: true,
                opacity
            }))
        }
        return sharedMaterial.current.get(key)!
    }

    const handleNodeClick = (node: any) => {
        // Center camera on node (Jarvis-style focus)
        graphRef.current?.cameraPosition(
            { x: node.x + 100, y: node.y + 100, z: node.z + 100 },
            node,
            1000
        )
        setSelectedNode(node)
        if (onNodeHover) onNodeHover(node)
    }

    return (
        <div className="relative w-screen h-screen bg-black overflow-hidden">
            {/* Background Grid (Tony Stark HUD style) */}
            <div className="absolute inset-0 z-0 opacity-10">
                <div className="absolute inset-0 bg-[linear-gradient(to_right,#00ffff33_1px,transparent_1px),linear-gradient(to_bottom,#00ffff33_1px,transparent_1px)] bg-[size:50px_50px]" />
            </div>

            {/* 3D Robot (Spline Model Placeholder) */}
            <div className="absolute bottom-10 left-10 z-20">
                <div className="relative w-64 h-64">
                    {/* TODO: Replace with Spline embed or GLB import */}
                    <div className="text-cyan-400 text-sm font-mono animate-pulse">
                        [ 3D ROBOT MODEL ]
                        <br />
                        Spline Export → GLB
                    </div>
                </div>
            </div>

            {/* Main 3D Force Graph */}
            <div className="absolute inset-0 z-10">
                <ForceGraph3D
                    ref={graphRef}
                    graphData={data}
                    nodeLabel="name"
                    nodeAutoColorBy="group"
                    nodeVal={(node: any) => (node.val || 1) * 2}
                    nodeOpacity={0.9}
                    nodeResolution={8}  // 🚀 PERFORMANCE: Reduced from 16 to 8

                    // Animation settings - keep moving for landing page
                    warmupTicks={50}
                    cooldownTicks={0}  // Never stop
                    cooldownTime={0}   // Never stop

                    // Links
                    linkWidth={(link: any) => link.type === 'twin' ? 2 : (link.value || 1) * 0.5}
                    linkColor={(link: any) => {
                        if (link.type === 'twin') return '#ff0055'
                        return viewMode === 'initial' ? 'rgba(255, 255, 255, 0.2)' : 'rgba(0, 255, 255, 0.3)'
                    }}
                    linkDirectionalParticles={(link: any) => link.type === 'twin' ? 4 : 0}
                    linkDirectionalParticleSpeed={0.005}
                    linkDirectionalParticleWidth={2}
                    linkDirectionalParticleColor={() => '#ff0055'}

                    // 🚀 PERFORMANCE: Optimized node rendering with shared resources
                    nodeThreeObject={(node: any) => {
                        const isSelected = selectedNode?.id === node.id
                        const isInitial = viewMode === 'initial'

                        const size = (node.val || 1) * 3
                        const color = isInitial ? 0xffffff : (node.color || 0x00ffcc)
                        const opacity = isSelected ? 1 : 0.8

                        // Use shared geometry and material
                        const geometry = getGeometry(Math.round(size))
                        const material = getMaterial(color, opacity)
                        const mesh = new THREE.Mesh(geometry, material)

                        // Add glow effect for selected node only
                        if (isSelected) {
                            const glowGeometry = getGeometry(Math.round(size * 1.3))
                            const glowMaterial = getMaterial(0x00ffff, 0.3)
                            const glowMesh = new THREE.Mesh(glowGeometry, glowMaterial)
                            mesh.add(glowMesh)
                        }

                        return mesh
                    }}

                    // Interaction
                    onNodeClick={handleNodeClick}
                    onNodeHover={(node: any) => {
                        if (node && onNodeHover) {
                            onNodeHover(node)
                        }
                    }}

                    // Visual Settings
                    backgroundColor="#000000"
                    showNavInfo={false}
                    controlType="orbit"
                    enableNodeDrag={false}
                />
            </div>

            {/* HUD Overlay (Tony Stark style) */}
            <div className="absolute top-10 right-10 z-30 text-cyan-400 font-mono text-sm space-y-2">
                <div className="bg-black/50 backdrop-blur-sm border border-cyan-500/30 p-4 rounded">
                    <div className="text-cyan-300 text-xs mb-2">[ REGIME AI SYSTEM ]</div>
                    <div className="space-y-1 text-xs">
                        <div>Nodes: {data.nodes.length.toLocaleString()}</div>
                        <div>Links: {data.links.length.toLocaleString()}</div>
                        <div>Mode: {viewMode === 'initial' ? 'INITIALIZING' : 'ACTIVE'}</div>
                        {selectedNode && (
                            <>
                                <div className="mt-2 pt-2 border-t border-cyan-500/30">
                                    <div className="text-cyan-300">SELECTED REGIME:</div>
                                    <div className="text-white">{selectedNode.name}</div>
                                    {selectedNode.group && (
                                        <div className="text-cyan-200">Group: {selectedNode.group}</div>
                                    )}
                                </div>
                            </>
                        )}
                    </div>
                </div>
            </div>

            {/* Loading Animation (Initial Phase) */}
            {viewMode === 'initial' && (
                <div className="absolute inset-0 z-40 bg-black/80 flex items-center justify-center">
                    <div className="text-center space-y-4">
                        <div className="text-cyan-400 text-2xl font-bold animate-pulse">
                            REGIME AI ANALYSIS
                        </div>
                        <div className="text-cyan-300 text-sm font-mono">
                            Initializing 20,000+ Regime Nodes...
                        </div>
                        <div className="flex justify-center space-x-1">
                            {[0, 1, 2, 3, 4].map((i) => (
                                <div
                                    key={i}
                                    className="w-2 h-8 bg-cyan-400 animate-pulse"
                                    style={{
                                        animationDelay: `${i * 0.1}s`
                                    }}
                                />
                            ))}
                        </div>
                    </div>
                </div>
            )}

            {/* Corner Labels (World's First) */}
            <div className="absolute bottom-10 right-10 z-30">
                <div className="text-cyan-400 font-mono text-xs text-right">
                    <div className="text-cyan-300 font-bold">WORLD'S FIRST</div>
                    <div>Regime AI Analysis</div>
                    <div className="text-cyan-500">Powered by Graph RAG</div>
                </div>
            </div>
        </div>
    )
}
