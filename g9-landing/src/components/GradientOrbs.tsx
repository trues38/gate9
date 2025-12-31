'use client';

export default function GradientOrbs() {
  return (
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
}
