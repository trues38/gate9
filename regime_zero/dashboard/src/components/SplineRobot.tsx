"use client"

import { useEffect, useRef, useState } from "react"
import Spline from '@splinetool/react-spline'

/**
 * Spline 3D Robot Component
 *
 * How to integrate your Spline robot:
 *
 * 1. Export from Spline:
 *    - Open your robot in Spline
 *    - File → Export → Code Export → React
 *    - Copy the Spline scene URL
 *
 * 2. Option A: Embed Spline (Easiest)
 *    - Replace the sceneUrl below with your Spline URL
 *
 * 3. Option B: Export as GLB (Better performance)
 *    - File → Export → 3D Model → GLB/GLTF
 *    - Place in /public/models/robot.glb
 *    - Use @react-three/drei's useGLTF
 */

interface SplineRobotProps {
    className?: string
    interactive?: boolean
}

export default function SplineRobot({ className = "", interactive = true }: SplineRobotProps) {
    const splineRef = useRef<any>(null)
    const [loaded, setLoaded] = useState(false)

    const onLoad = (splineApp: any) => {
        splineRef.current = splineApp
        setLoaded(true)

        // Optional: Control the robot programmatically
        // Example: Find and animate objects
        // const robot = splineApp.findObjectByName('Robot')
        // if (robot) {
        //   robot.rotation.y += 0.01
        // }
    }

    return (
        <div className={`relative ${className}`}>
            {/* Loading State */}
            {!loaded && (
                <div className="absolute inset-0 flex items-center justify-center">
                    <div className="text-cyan-400 text-sm font-mono animate-pulse">
                        Loading 3D Robot...
                    </div>
                </div>
            )}

            {/* Spline Scene */}
            <Spline
                scene="https://prod.spline.design/5Uvzkk1M7ZSOwqVt/scene.splinecode"
                onLoad={onLoad}
                style={{
                    width: '100%',
                    height: '100%',
                    pointerEvents: interactive ? 'auto' : 'none'
                }}
            />

            {/* Holographic Frame Effect - Subtle for center ghost mode */}
            <div className="absolute inset-0 pointer-events-none opacity-20">
                {/* Circular holographic ring */}
                <div className="absolute inset-0 rounded-full border border-cyan-400/30 animate-pulse" style={{ animationDuration: '3s' }} />
                <div className="absolute inset-8 rounded-full border border-cyan-400/20 animate-pulse" style={{ animationDuration: '4s', animationDelay: '0.5s' }} />
                <div className="absolute inset-16 rounded-full border border-cyan-400/10 animate-pulse" style={{ animationDuration: '5s', animationDelay: '1s' }} />
            </div>
        </div>
    )
}

/**
 * Alternative: GLB Robot Component (if you export as GLB instead)
 *
 * This provides better performance for production use.
 */

// import { Canvas } from "@react-three/fiber"
// import { useGLTF, OrbitControls, Environment } from "@react-three/drei"
// import { Suspense } from "react"

// function RobotModel() {
//     const { scene } = useGLTF('/models/robot.glb')

//     return (
//         <primitive
//             object={scene}
//             scale={2}
//             position={[0, -1, 0]}
//         />
//     )
// }

// export function GLBRobot({ className = "" }: { className?: string }) {
//     return (
//         <div className={`relative ${className}`}>
//             <Canvas camera={{ position: [2, 2, 5], fov: 50 }}>
//                 <Suspense fallback={null}>
//                     <ambientLight intensity={0.5} />
//                     <directionalLight position={[10, 10, 5]} intensity={1} />
//                     <RobotModel />
//                     <OrbitControls
//                         enableZoom={false}
//                         enablePan={false}
//                         autoRotate
//                         autoRotateSpeed={0.5}
//                     />
//                     <Environment preset="studio" />
//                 </Suspense>
//             </Canvas>
//         </div>
//     )
// }
