---
name: saas-bold-tech
description: "Create bold, high-impact SaaS landing pages for data-driven tech products. Use when building landing pages for analytics platforms, sports betting analysis, economic analysis tools, or any product emphasizing data visualization and technical sophistication. Produces dark-themed, neon-accented designs with 3D graphics, animated data visualizations, and premium tech aesthetics. Tech stack: React + Tailwind CSS + Framer Motion + Three.js."
---

# SaaS Bold Tech - G9 Design System

고급 데이터 분석 플랫폼(G9-Sport, G9-Economy)을 위한 대담하고 차별화된 랜딩페이지 제작 가이드.

## Design Philosophy

**Core Identity**: "데이터의 힘을 시각적으로 압도"
- 다크 베이스 + 네온 액센트
- 실시간 데이터 시각화 느낌
- 3D 요소로 깊이감 연출
- 프리미엄 테크 감성

## Quick Start

```jsx
// 기본 페이지 구조
<div className="min-h-screen bg-slate-950 text-white">
  <HeroSection />
  <FeaturesGrid />
  <DataShowcase />
  <PricingTable />
  <CTASection />
  <Footer />
</div>
```

## Color System

```css
/* G9 Core Palette */
--g9-bg-primary: #0a0f1a;      /* 깊은 다크 */
--g9-bg-secondary: #111827;     /* 카드 배경 */
--g9-bg-elevated: #1e293b;      /* 호버/강조 */

/* Neon Accents */
--g9-neon-cyan: #00f5ff;        /* 프라이머리 액센트 */
--g9-neon-purple: #a855f7;      /* 세컨더리 액센트 */
--g9-neon-green: #22c55e;       /* 성공/상승 */
--g9-neon-red: #ef4444;         /* 경고/하락 */
--g9-neon-gold: #fbbf24;        /* 프리미엄/VIP */

/* Gradients */
--g9-gradient-hero: linear-gradient(135deg, #0a0f1a 0%, #1a1a2e 50%, #16213e 100%);
--g9-gradient-card: linear-gradient(180deg, rgba(17,24,39,0.8) 0%, rgba(10,15,26,0.9) 100%);
--g9-gradient-neon: linear-gradient(90deg, #00f5ff 0%, #a855f7 100%);
```

### Tailwind Config Extension

```js
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        g9: {
          dark: '#0a0f1a',
          card: '#111827',
          elevated: '#1e293b',
          cyan: '#00f5ff',
          purple: '#a855f7',
        }
      },
      boxShadow: {
        'neon-cyan': '0 0 20px rgba(0, 245, 255, 0.3)',
        'neon-purple': '0 0 20px rgba(168, 85, 247, 0.3)',
      },
      animation: {
        'pulse-neon': 'pulseNeon 2s ease-in-out infinite',
        'float': 'float 6s ease-in-out infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
      }
    }
  }
}
```

## Typography

| Element | Font | Size | Weight |
|---------|------|------|--------|
| Hero Title | Orbitron | 4-6rem | 700-800 |
| Section Title | Space Grotesk | 2.5-3rem | 600 |
| Body | Inter | 1rem | 400 |
| Data/Numbers | JetBrains Mono | varies | 500 |
| Accent Text | Rajdhani | varies | 600 |

```html
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@700;800;900&family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&family=Rajdhani:wght@500;600;700&display=swap" rel="stylesheet">
```

## Section Patterns

### 1. Hero Section

필수 요소:
- 3D/파티클 배경 효과
- 대담한 타이틀 + 네온 그라디언트
- 실시간 데이터 프리뷰 또는 대시보드 목업
- Glow CTA 버튼

See `references/components.md` → Hero Section

### 2. Features Grid

3열 그리드, 아이콘 + 제목 + 설명, 호버 시 glow 효과

See `references/components.md` → FeatureCard

### 3. Data Showcase

좌우 분할 레이아웃, 인터랙티브 차트/대시보드 프리뷰

### 4. Pricing Table

3단 가격표, 중앙 "Pro" 강조, 네온 보더 효과

See `references/components.md` → PricingCard

## Product Variants

### G9-Sport
- 액센트: Cyan + Green/Red
- 키워드: "Edge Detection", "Real-time Odds", "Value Betting"
- 특화: 오즈 비교표, 라이브 스코어보드

### G9-Economy  
- 액센트: Purple + Gold
- 키워드: "Regime Analysis", "Economic Indicators"
- 특화: 레짐 대시보드, 시나리오 비교

## 3D & Animation

상세 구현은 `references/3d-effects.md` 참조:
- GridBackground (CSS grid pattern)
- ParticleField (canvas/Three.js)
- GradientOrbs (floating blurred circles)
- Scroll-triggered animations (Framer Motion)

## Implementation Checklist

- [ ] 다크 테마 + 폰트 설정
- [ ] Tailwind 색상 확장
- [ ] Hero + 배경 효과
- [ ] Features 그리드
- [ ] Data Showcase
- [ ] Pricing 테이블
- [ ] CTA + Footer
- [ ] 애니메이션 추가
- [ ] 반응형 확인
