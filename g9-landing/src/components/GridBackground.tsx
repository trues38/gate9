'use client';

export default function GridBackground() {
  return (
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
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-[#0a0f1a]/50 to-[#0a0f1a]" />
    </div>
  );
}
