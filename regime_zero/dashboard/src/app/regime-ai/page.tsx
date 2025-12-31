"use client"

import { useState } from "react"
import GraphView3D from "@/components/GraphView3D"
import SplineRobot from "@/components/SplineRobot"

/**
 * Regime AI Dashboard - Tony Stark Style
 *
 * The World's First AI-Powered Regime Analysis System
 *
 * Features:
 * - 3D Robot Companion (Spline)
 * - 20,000+ Regime Nodes in 3D Force Graph
 * - Holographic Sphere Visualization
 * - Interactive Node Selection
 * - Real-time Graph Analytics
 */

export default function RegimeAIPage() {
    const [selectedNode, setSelectedNode] = useState<any>(null)
    const [showRobot, setShowRobot] = useState(false)  // 🤖 로봇 1차 후퇴

    return (
        <div className="relative w-screen h-screen bg-black overflow-hidden">
            {/* Main 3D Graph Universe */}
            <div className="absolute inset-0 z-0">
                <GraphView3D
                    onNodeHover={(node) => {
                        if (node) {
                            setSelectedNode(node)
                        }
                    }}
                />
            </div>

            {/* 3D Robot Companion (CENTER - Transparent Ghost) */}
            {showRobot && (
                <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] z-15 opacity-40 mix-blend-screen pointer-events-none">
                    <SplineRobot
                        className="w-full h-full"
                        interactive={false}
                    />
                </div>
            )}

            {/* Top Header - System Status */}
            <div className="absolute top-0 left-0 right-0 z-30 p-8">
                <div className="max-w-7xl mx-auto flex items-center justify-between">
                    {/* Left: Logo */}
                    <div className="space-y-1">
                        <div className="text-cyan-400 text-3xl font-bold tracking-wider">
                            REGIME AI
                        </div>
                        <div className="text-cyan-600 text-xs font-mono">
                            WORLD'S FIRST AI-POWERED REGIME ANALYSIS
                        </div>
                    </div>

                    {/* Right: Controls */}
                    <div className="flex items-center space-x-4">
                        <button
                            onClick={() => setShowRobot(!showRobot)}
                            className="px-4 py-2 bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-500/50 text-cyan-400 text-sm font-mono rounded transition-colors"
                        >
                            {showRobot ? 'HIDE ROBOT' : 'SHOW ROBOT'}
                        </button>

                        <div className="px-4 py-2 bg-black/50 border border-cyan-500/30 text-cyan-400 text-xs font-mono rounded">
                            <div className="flex items-center space-x-2">
                                <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
                                <span>SYSTEM ONLINE</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Right Sidebar - Selected Regime Details */}
            {selectedNode && (
                <div className="absolute top-32 right-8 w-80 z-30">
                    <div className="bg-black/70 backdrop-blur-md border border-cyan-500/30 rounded-lg p-6 space-y-4">
                        {/* Header */}
                        <div className="flex items-start justify-between">
                            <div>
                                <div className="text-cyan-300 text-xs font-mono mb-1">
                                    SELECTED REGIME
                                </div>
                                <div className="text-white text-lg font-bold">
                                    {selectedNode.name}
                                </div>
                            </div>
                            <button
                                onClick={() => setSelectedNode(null)}
                                className="text-cyan-500 hover:text-cyan-400 text-xl"
                            >
                                ×
                            </button>
                        </div>

                        {/* Properties */}
                        <div className="space-y-2 text-sm">
                            {selectedNode.id && (
                                <div className="flex justify-between">
                                    <span className="text-cyan-600">ID:</span>
                                    <span className="text-cyan-300 font-mono">{selectedNode.id}</span>
                                </div>
                            )}

                            {selectedNode.group && (
                                <div className="flex justify-between">
                                    <span className="text-cyan-600">Group:</span>
                                    <span className="text-cyan-300">{selectedNode.group}</span>
                                </div>
                            )}

                            {selectedNode.val && (
                                <div className="flex justify-between">
                                    <span className="text-cyan-600">Importance:</span>
                                    <span className="text-cyan-300">{selectedNode.val}</span>
                                </div>
                            )}
                        </div>

                        {/* Connections */}
                        <div className="pt-4 border-t border-cyan-500/30">
                            <div className="text-cyan-300 text-xs font-mono mb-2">
                                REGIME CONNECTIONS
                            </div>
                            <div className="text-cyan-500 text-sm">
                                Analyzing historical regime patterns...
                            </div>
                        </div>

                        {/* Action Buttons */}
                        <div className="pt-4 border-t border-cyan-500/30 space-y-2">
                            <button className="w-full px-4 py-2 bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-500/50 text-cyan-400 text-sm font-mono rounded transition-colors">
                                VIEW REGIME DETAILS
                            </button>
                            <button className="w-full px-4 py-2 bg-cyan-500/10 hover:bg-cyan-500/20 border border-cyan-500/30 text-cyan-500 text-sm font-mono rounded transition-colors">
                                ANALYZE CONNECTIONS
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Bottom Bar - Quick Stats */}
            <div className="absolute bottom-0 left-0 right-0 z-30 p-8">
                <div className="max-w-7xl mx-auto">
                    <div className="bg-black/50 backdrop-blur-sm border border-cyan-500/30 rounded-lg p-4">
                        <div className="flex items-center justify-between text-sm font-mono">
                            <div className="flex items-center space-x-8">
                                <div>
                                    <span className="text-cyan-600">Total Regimes:</span>
                                    <span className="text-cyan-300 ml-2 font-bold">20,847</span>
                                </div>
                                <div>
                                    <span className="text-cyan-600">Active Connections:</span>
                                    <span className="text-cyan-300 ml-2 font-bold">156,293</span>
                                </div>
                                <div>
                                    <span className="text-cyan-600">Analysis Accuracy:</span>
                                    <span className="text-green-400 ml-2 font-bold">98.7%</span>
                                </div>
                            </div>

                            <div className="text-cyan-500 text-xs">
                                Last Updated: {new Date().toLocaleTimeString()}
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Easter Egg: Hidden Command Interface */}
            <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 z-50 pointer-events-none">
                <div className="text-cyan-400/20 text-[200px] font-bold tracking-widest select-none">
                    G9
                </div>
            </div>

            {/* Loading Animation Overlay */}
            {/* This can be removed after initial load */}
        </div>
    )
}
