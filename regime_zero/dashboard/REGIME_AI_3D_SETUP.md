# Regime AI 3D Dashboard Setup Guide
## 토니 스타크 스타일 홀로그래픽 대시보드 구현

---

## 🎯 목표

**세계최초 AI 기반 레짐 분석 시스템**을 3D 홀로그래픽 인터페이스로 시각화

### 주요 기능
1. ✅ **3D 로봇 컴패니언** (Spline 모델)
2. ✅ **2만개 레짐 노드** 3D Force Graph
3. ✅ **홀로그래픽 구체** 투명 효과
4. ✅ **인터랙티브 노드 선택**
5. ✅ **토니 스타크 스타일 HUD**

---

## 📦 설치 단계

### 1. 필수 패키지 설치

```bash
cd /Users/js/g9/regime_zero/dashboard

# 3D 그래프 라이브러리
npm install react-force-graph-3d three

# React Three Fiber (3D 렌더링)
npm install @react-three/fiber @react-three/drei

# Spline Integration (옵션)
npm install @splinetool/react-spline

# TypeScript 타입 정의
npm install --save-dev @types/three
```

### 2. Spline 로봇 통합 (2가지 방법)

#### Option A: Spline Embed (가장 쉬움)

1. Spline에서 로봇 디자인 완성
2. **Export → Code Export → React** 선택
3. Spline scene URL 복사
4. `src/components/SplineRobot.tsx`의 `sceneUrl` 교체

```tsx
<Spline
  scene="https://prod.spline.design/YOUR_ACTUAL_SCENE_ID/scene.splinecode"
  onLoad={onLoad}
/>
```

#### Option B: GLB Export (더 나은 성능)

1. Spline에서 **Export → 3D Model → GLB** 선택
2. 파일을 `/public/models/robot.glb`에 저장
3. `SplineRobot.tsx`의 GLB 컴포넌트 주석 해제

```tsx
function RobotModel() {
    const { scene } = useGLTF('/models/robot.glb')
    return <primitive object={scene} scale={2} position={[0, -1, 0]} />
}
```

### 3. 데이터 준비

현재 `/public/viz_data.json`에 레짐 데이터 있음. 형식:

```json
{
  "nodes": [
    {"id": "regime_1", "name": "Bull Market 2020", "group": 1, "val": 5},
    {"id": "regime_2", "name": "Bear Market 2022", "group": 2, "val": 3}
  ],
  "links": [
    {"source": "regime_1", "target": "regime_2", "value": 2}
  ]
}
```

---

## 🚀 실행 방법

### 개발 서버 시작

```bash
cd /Users/js/g9/regime_zero/dashboard
npm run dev
```

### 페이지 접속

```
http://localhost:3000/regime-ai
```

---

## 🎨 커스터마이징 가이드

### 1. 색상 테마 변경

`src/app/regime-ai/page.tsx`에서:

```tsx
// 현재: 사이버 블루 (Cyan)
className="text-cyan-400"

// 변경 예시:
// Iron Man Red: text-red-500
// Matrix Green: text-green-400
// Purple Haze: text-purple-500
```

### 2. 홀로그래픽 구체 크기 조정

`src/components/GraphView3D.tsx` → `HolographicSphere` 컴포넌트:

```tsx
<sphereGeometry args={[500, 64, 64]} />
//                    ^^^
// 500 = 반지름 (더 크게: 800, 더 작게: 300)
```

### 3. 노드 크기 및 색상

```tsx
nodeVal={(node: any) => (node.val || 1) * 2}
//                                       ^^^
// 곱하기 값이 클수록 노드가 커짐

nodeAutoColorBy="group"
// 그룹별 자동 색상 지정
```

### 4. Force Physics 조정

```tsx
graphRef.current.d3Force('charge').strength(-200)
//                                           ^^^^
// -200 = 반발력 (더 강하게: -300, 더 약하게: -100)

graphRef.current.d3Force('link').distance(80)
//                                         ^^
// 80 = 링크 거리 (더 멀리: 120, 더 가까이: 50)
```

---

## 📊 데이터 형식 가이드

### 노드 속성

```typescript
interface RegimeNode {
  id: string              // 고유 ID
  name: string            // 레짐 이름
  group?: number          // 그룹 (색상 구분용)
  val?: number            // 중요도 (노드 크기)
  color?: string          // 커스텀 색상 (옵션)

  // 3D 좌표 (자동 계산됨)
  x?: number
  y?: number
  z?: number
}
```

### 링크 속성

```typescript
interface RegimeLink {
  source: string          // 출발 노드 ID
  target: string          // 도착 노드 ID
  value?: number          // 링크 강도 (두께)
  type?: string           // "twin" = 특수 효과
  color?: string          // 커스텀 색상
}
```

---

## 🎬 애니메이션 효과

### 1. 초기 로딩 애니메이션

현재 3초 후 `immersive` 모드로 전환됨.

```tsx
const timer = setTimeout(() => {
    setViewMode('immersive')
}, 3000)  // 3초 → 원하는 시간으로 변경
```

### 2. 카메라 자동 회전

```tsx
// GraphView3D.tsx에 추가
useEffect(() => {
    const interval = setInterval(() => {
        if (graphRef.current) {
            const angle = Date.now() * 0.0001
            graphRef.current.cameraPosition(
                {
                    x: 300 * Math.cos(angle),
                    y: 300,
                    z: 300 * Math.sin(angle)
                },
                { x: 0, y: 0, z: 0 },
                1000
            )
        }
    }, 2000)
    return () => clearInterval(interval)
}, [])
```

### 3. 노드 펄스 효과

```tsx
// 시간 기반 크기 변화
nodeVal={(node: any) => {
    const pulse = Math.sin(Date.now() * 0.001) * 0.5 + 1
    return (node.val || 1) * 2 * pulse
}}
```

---

## 🖼️ Spline 로봇 디자인 팁

### 추천 설정

1. **크기**: 로봇 전체 높이 2-3 units
2. **재질**: Metallic + Reflective (블랙 크롬)
3. **조명**: Point Light 3개 (앞/좌/우)
4. **애니메이션**: Idle 루프 (미세한 움직임)

### Export 체크리스트

- ✅ Optimize for web
- ✅ Include animations
- ✅ Compress textures
- ✅ Max poly count: 50K triangles

---

## 🐛 문제 해결

### "Module not found: react-force-graph-3d"

```bash
npm install react-force-graph-3d --legacy-peer-deps
```

### Spline 씬이 로드되지 않음

1. Spline URL 확인 (올바른 scene ID)
2. CORS 설정 확인
3. Browser console 에러 확인

### 3D 그래프가 너무 느림

1. 노드 개수 줄이기 (테스트: 1000개)
2. `nodeResolution` 낮추기 (16 → 8)
3. `linkDirectionalParticles` 끄기 (0으로)

### 로봇이 안 보임

1. `showRobot` state 확인
2. Z-index 확인 (`z-20`)
3. Spline scene 로드 상태 확인

---

## 📱 반응형 디자인

현재는 데스크톱 최적화. 모바일 대응:

```tsx
// Mobile detection
const isMobile = window.innerWidth < 768

return (
    <div className={isMobile ? "mobile-layout" : "desktop-layout"}>
        {/* Adjust layout for mobile */}
        {!isMobile && <SplineRobot />}  // Hide robot on mobile
    </div>
)
```

---

## 🚢 프로덕션 배포

### 1. 빌드

```bash
npm run build
```

### 2. 성능 최적화

- [ ] Code splitting: `dynamic import`
- [ ] Image optimization: WebP 변환
- [ ] 3D assets: GLB 압축 (Draco)
- [ ] Lazy loading: 초기 로드 최소화

### 3. SEO & Meta Tags

```tsx
// src/app/regime-ai/page.tsx에 추가
export const metadata = {
  title: 'Regime AI - World\'s First AI-Powered Regime Analysis',
  description: '20,000+ regime nodes visualized in 3D holographic interface',
  openGraph: {
    images: ['/regime-ai-preview.png'],
  },
}
```

---

## 🎯 다음 단계

1. **실시간 데이터 연동**
   - WebSocket으로 실시간 레짐 업데이트
   - Neo4j Graph DB 연동

2. **AI 분석 통합**
   - LLM으로 레짐 요약 생성
   - Regime transition 예측

3. **협업 기능**
   - 멀티 유저 동시 접속
   - 레짐 주석 달기

4. **VR/AR 확장**
   - WebXR로 VR 헤드셋 지원
   - AR 모바일 앱

---

## 📞 문의

- **프로젝트**: Regime Zero
- **대시보드**: `/Users/js/g9/regime_zero/dashboard`
- **문서**: `REGIME_AI_3D_SETUP.md`

**Built with**: Next.js 14 + Three.js + Spline + React Force Graph

**Inspired by**: Tony Stark's Holographic Interface (MCU)
