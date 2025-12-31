# G9 3D Effects & Animations

배경 효과, 3D 요소, 애니메이션 구현 코드.

## Background Effects

### GridBackground (CSS Grid Pattern)

```jsx
const GridBackground = () => (
  <div className="absolute inset-0 overflow-hidden">
    {/* Grid Pattern */}
    <div 
      className="absolute inset-0 opacity-20"
      style={{
        backgroundImage: `
          linear-gradient(rgba(0, 245, 255, 0.1) 1px, transparent 1px),
          linear-gradient(90deg, rgba(0, 245, 255, 0.1) 1px, transparent 1px)
        `,
        backgroundSize: '50px 50px',
      }}
    />
    
    {/* Radial fade */}
    <div className="absolute inset-0 bg-gradient-to-b from-transparent via-slate-950/50 to-slate-950" />
  </div>
);
```

### GradientOrbs (Floating Blurred Circles)

```jsx
const GradientOrbs = () => (
  <div className="absolute inset-0 overflow-hidden pointer-events-none">
    {/* Cyan Orb */}
    <div 
      className="absolute w-96 h-96 rounded-full blur-3xl animate-float"
      style={{
        background: 'radial-gradient(circle, rgba(0,245,255,0.15) 0%, transparent 70%)',
        top: '10%',
        left: '10%',
      }}
    />
    
    {/* Purple Orb */}
    <div 
      className="absolute w-80 h-80 rounded-full blur-3xl animate-float"
      style={{
        background: 'radial-gradient(circle, rgba(168,85,247,0.15) 0%, transparent 70%)',
        top: '50%',
        right: '15%',
        animationDelay: '-3s',
      }}
    />
    
    {/* Small accent orb */}
    <div 
      className="absolute w-64 h-64 rounded-full blur-2xl animate-float"
      style={{
        background: 'radial-gradient(circle, rgba(0,245,255,0.1) 0%, transparent 70%)',
        bottom: '20%',
        left: '30%',
        animationDelay: '-5s',
      }}
    />
  </div>
);
```

### ParticleField (Canvas Implementation)

```jsx
import { useEffect, useRef } from 'react';

const ParticleField = ({ particleCount = 50 }) => {
  const canvasRef = useRef(null);
  
  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    
    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resize();
    window.addEventListener('resize', resize);
    
    // Particles
    const particles = Array.from({ length: particleCount }, () => ({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      vx: (Math.random() - 0.5) * 0.5,
      vy: (Math.random() - 0.5) * 0.5,
      size: Math.random() * 2 + 1,
      opacity: Math.random() * 0.5 + 0.2,
    }));
    
    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      
      particles.forEach(p => {
        // Update position
        p.x += p.vx;
        p.y += p.vy;
        
        // Wrap around
        if (p.x < 0) p.x = canvas.width;
        if (p.x > canvas.width) p.x = 0;
        if (p.y < 0) p.y = canvas.height;
        if (p.y > canvas.height) p.y = 0;
        
        // Draw particle
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(0, 245, 255, ${p.opacity})`;
        ctx.fill();
      });
      
      // Draw connections
      particles.forEach((p1, i) => {
        particles.slice(i + 1).forEach(p2 => {
          const dx = p1.x - p2.x;
          const dy = p1.y - p2.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          
          if (dist < 150) {
            ctx.beginPath();
            ctx.moveTo(p1.x, p1.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.strokeStyle = `rgba(0, 245, 255, ${0.1 * (1 - dist / 150)})`;
            ctx.stroke();
          }
        });
      });
      
      requestAnimationFrame(animate);
    };
    
    animate();
    
    return () => window.removeEventListener('resize', resize);
  }, [particleCount]);
  
  return (
    <canvas 
      ref={canvasRef} 
      className="absolute inset-0 pointer-events-none"
    />
  );
};
```

## CSS Animations

### Tailwind Keyframes (tailwind.config.js)

```js
module.exports = {
  theme: {
    extend: {
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-20px)' },
        },
        pulseNeon: {
          '0%, 100%': { 
            boxShadow: '0 0 20px rgba(0, 245, 255, 0.4)',
            opacity: 1 
          },
          '50%': { 
            boxShadow: '0 0 40px rgba(0, 245, 255, 0.6)',
            opacity: 0.8 
          },
        },
        glow: {
          '0%': { boxShadow: '0 0 20px rgba(0, 245, 255, 0.3)' },
          '100%': { boxShadow: '0 0 40px rgba(0, 245, 255, 0.5)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        slideUp: {
          '0%': { opacity: 0, transform: 'translateY(20px)' },
          '100%': { opacity: 1, transform: 'translateY(0)' },
        },
        scaleIn: {
          '0%': { opacity: 0, transform: 'scale(0.9)' },
          '100%': { opacity: 1, transform: 'scale(1)' },
        },
      },
      animation: {
        'float': 'float 6s ease-in-out infinite',
        'pulse-neon': 'pulseNeon 2s ease-in-out infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
        'shimmer': 'shimmer 2s linear infinite',
        'slide-up': 'slideUp 0.5s ease-out',
        'scale-in': 'scaleIn 0.3s ease-out',
      },
    },
  },
};
```

## Framer Motion Patterns

### Scroll Reveal

```jsx
import { motion } from 'framer-motion';

// Container with staggered children
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.2,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { 
    opacity: 1, 
    y: 0,
    transition: { duration: 0.5 }
  },
};

// Usage
<motion.div
  variants={containerVariants}
  initial="hidden"
  whileInView="visible"
  viewport={{ once: true, margin: "-100px" }}
>
  {items.map((item, i) => (
    <motion.div key={i} variants={itemVariants}>
      {item}
    </motion.div>
  ))}
</motion.div>
```

### Hover Effects

```jsx
// Card hover with 3D tilt
const Card3D = ({ children }) => (
  <motion.div
    whileHover={{ 
      scale: 1.02,
      rotateX: 5,
      rotateY: 5,
    }}
    transition={{ type: "spring", stiffness: 300 }}
    style={{ transformStyle: "preserve-3d" }}
  >
    {children}
  </motion.div>
);

// Glow on hover
const GlowHover = ({ children }) => (
  <motion.div
    whileHover={{ 
      boxShadow: "0 0 40px rgba(0, 245, 255, 0.4)"
    }}
    transition={{ duration: 0.3 }}
  >
    {children}
  </motion.div>
);
```

### Page Transitions

```jsx
const pageVariants = {
  initial: { opacity: 0, y: 20 },
  animate: { 
    opacity: 1, 
    y: 0,
    transition: { duration: 0.6, ease: "easeOut" }
  },
  exit: { 
    opacity: 0, 
    y: -20,
    transition: { duration: 0.3 }
  },
};
```

## Three.js 3D Effects

### Basic Scene Setup

```jsx
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Float } from '@react-three/drei';

const Scene3D = () => (
  <Canvas camera={{ position: [0, 0, 5] }}>
    <ambientLight intensity={0.5} />
    <pointLight position={[10, 10, 10]} color="#00f5ff" />
    
    <Float speed={2} rotationIntensity={0.5} floatIntensity={1}>
      <mesh>
        <icosahedronGeometry args={[1, 1]} />
        <meshStandardMaterial 
          color="#00f5ff" 
          wireframe 
          emissive="#00f5ff"
          emissiveIntensity={0.2}
        />
      </mesh>
    </Float>
    
    <OrbitControls enableZoom={false} autoRotate autoRotateSpeed={1} />
  </Canvas>
);
```

### Floating Data Points

```jsx
const DataPoints = ({ count = 100 }) => {
  const points = useMemo(() => {
    return Array.from({ length: count }, () => ({
      position: [
        (Math.random() - 0.5) * 10,
        (Math.random() - 0.5) * 10,
        (Math.random() - 0.5) * 10,
      ],
      size: Math.random() * 0.1 + 0.02,
    }));
  }, [count]);

  return (
    <group>
      {points.map((point, i) => (
        <mesh key={i} position={point.position}>
          <sphereGeometry args={[point.size, 8, 8]} />
          <meshBasicMaterial color="#00f5ff" transparent opacity={0.6} />
        </mesh>
      ))}
    </group>
  );
};
```

## Dashboard Mockup Component

```jsx
const DashboardMockup = () => (
  <div className="relative">
    {/* Glow effect behind */}
    <div className="absolute -inset-4 bg-gradient-to-r from-cyan-500/20 to-purple-500/20 blur-3xl" />
    
    {/* Mock dashboard */}
    <div className="relative bg-slate-900/90 rounded-2xl border border-slate-700/50 p-6 backdrop-blur-sm shadow-2xl">
      {/* Header */}
      <div className="flex items-center gap-2 mb-6">
        <div className="w-3 h-3 rounded-full bg-red-500" />
        <div className="w-3 h-3 rounded-full bg-yellow-500" />
        <div className="w-3 h-3 rounded-full bg-green-500" />
      </div>
      
      {/* Stats row */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        {[
          { label: 'Accuracy', value: '94.7%', trend: 'up' },
          { label: 'Signals', value: '1,247', trend: 'up' },
          { label: 'ROI', value: '+18.3%', trend: 'up' },
        ].map((stat, i) => (
          <div key={i} className="bg-slate-800/50 rounded-lg p-3">
            <p className="text-xs text-slate-400">{stat.label}</p>
            <p className="text-lg font-bold text-white" style={{ fontFamily: 'JetBrains Mono' }}>
              {stat.value}
            </p>
          </div>
        ))}
      </div>
      
      {/* Chart placeholder */}
      <div className="h-32 bg-slate-800/30 rounded-lg flex items-end justify-around p-4">
        {[40, 65, 45, 80, 55, 90, 70].map((h, i) => (
          <div
            key={i}
            className="w-6 bg-gradient-to-t from-cyan-500 to-purple-500 rounded-t"
            style={{ height: `${h}%` }}
          />
        ))}
      </div>
    </div>
  </div>
);
```

## Utility Classes

```css
/* globals.css */

/* Neon text glow */
.text-glow-cyan {
  text-shadow: 0 0 20px rgba(0, 245, 255, 0.5);
}

.text-glow-purple {
  text-shadow: 0 0 20px rgba(168, 85, 247, 0.5);
}

/* Glass effect */
.glass {
  background: rgba(17, 24, 39, 0.7);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

/* Gradient border */
.gradient-border {
  position: relative;
  background: linear-gradient(#111827, #111827) padding-box,
              linear-gradient(135deg, #00f5ff, #a855f7) border-box;
  border: 2px solid transparent;
  border-radius: 1rem;
}

/* Shimmer effect for loading */
.shimmer {
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(0, 245, 255, 0.1) 50%,
    transparent 100%
  );
  background-size: 200% 100%;
  animation: shimmer 2s linear infinite;
}
```
