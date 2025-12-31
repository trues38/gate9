# 빠른 시작 가이드: Regime AI 3D Dashboard

## 🚀 5분 안에 실행하기

### 1. 패키지 설치

```bash
cd /Users/js/g9/regime_zero/dashboard
npm install
```

설치될 주요 라이브러리:
- ✅ `react-force-graph-3d` - 3D 그래프 엔진
- ✅ `@react-three/fiber` - React용 Three.js
- ✅ `@react-three/drei` - Three.js 헬퍼
- ✅ `@splinetool/react-spline` - Spline 통합
- ✅ `three` - 3D 렌더링 라이브러리

### 2. 개발 서버 시작

```bash
npm run dev
```

### 3. 페이지 열기

브라우저에서:
```
http://localhost:3000/regime-ai
```

---

## 📁 생성된 파일

```
dashboard/
├── src/
│   ├── components/
│   │   ├── GraphView3D.tsx          # ✨ 3D 그래프 (메인)
│   │   ├── SplineRobot.tsx          # ✨ 3D 로봇
│   │   └── GraphView.tsx            # (기존 2D)
│   └── app/
│       └── regime-ai/
│           └── page.tsx             # ✨ 통합 페이지
├── REGIME_AI_3D_SETUP.md            # 📖 상세 가이드
├── QUICKSTART_3D.md                 # 📖 이 파일
└── package.json                     # ✨ 업데이트됨
```

---

## 🎨 Spline 로봇 추가 (Optional)

### 방법 1: Spline URL 사용

1. Spline에서 로봇 디자인
2. **Export → Code Export → React**
3. URL 복사
4. `src/components/SplineRobot.tsx` 열기
5. 36번 줄 수정:

```tsx
scene="https://prod.spline.design/[YOUR_SCENE_ID]/scene.splinecode"
```

### 방법 2: GLB 파일 사용

1. Spline에서 **Export → 3D Model → GLB**
2. 파일을 `/public/models/robot.glb`에 저장
3. `SplineRobot.tsx`의 83-105줄 주석 해제

---

## 🎬 데모 확인

실행 후 보이는 것:

1. ⚫ **검은 배경** (우주 느낌)
2. 🌐 **3D 그래프** (노드들이 떠다님)
3. 📊 **HUD** (상단/하단 정보 패널)
4. 🤖 **로봇** (왼쪽 하단, Spline 설정 필요)

### 인터랙션:
- **마우스 드래그**: 회전
- **스크롤**: 줌
- **노드 클릭**: 상세 정보 (우측 패널)
- **호버**: 하이라이트

---

## 🔧 커스터마이징

### 색상 변경 (사이버 블루 → 다른 색)

`src/app/regime-ai/page.tsx`에서:

```tsx
// 현재: 사이버 블루
className="text-cyan-400"

// 변경:
className="text-red-500"      // Iron Man 레드
className="text-purple-500"   // 퍼플
className="text-green-400"    // Matrix 그린
```

### 노드 크기 조정

`src/components/GraphView3D.tsx`:

```tsx
nodeVal={(node: any) => (node.val || 1) * 2}
//                                       ^^^
// 2 → 4 (더 크게)
// 2 → 1 (더 작게)
```

### 애니메이션 속도 변경

```tsx
linkDirectionalParticleSpeed={0.005}
//                             ^^^^^
// 0.01 (더 빠르게)
// 0.002 (더 느리게)
```

---

## 🐛 문제 해결

### "Module not found: react-force-graph-3d"

```bash
npm install react-force-graph-3d --legacy-peer-deps
```

### 화면이 검은색만 나옴

1. `/public/viz_data.json` 파일 확인
2. Browser console (F12) 에러 확인
3. 노드 데이터가 비어있는지 확인

### Spline 로봇이 안 보임

1. Spline scene URL 확인
2. `showRobot` 버튼 클릭 (우측 상단)
3. Browser console 확인

### 성능이 느림

데이터 줄이기:
```tsx
// viz_data.json
// 노드 개수: 20,000 → 1,000 (테스트용)
```

---

## 📊 데이터 형식

`/public/viz_data.json`:

```json
{
  "nodes": [
    {
      "id": "regime_1",
      "name": "Bull Market 2020",
      "group": 1,
      "val": 5
    },
    {
      "id": "regime_2",
      "name": "Bear Market 2022",
      "group": 2,
      "val": 3
    }
  ],
  "links": [
    {
      "source": "regime_1",
      "target": "regime_2",
      "value": 2
    }
  ]
}
```

---

## 🎯 다음 단계

### 단기 (오늘 가능)
1. ✅ Spline 로봇 추가
2. ✅ 색상 테마 커스터마이징
3. ✅ 실제 레짐 데이터 연결

### 중기 (1-2주)
1. 📡 Neo4j 실시간 연동
2. 🤖 AI 분석 통합
3. 📱 모바일 반응형

### 장기 (1-3개월)
1. 🎮 VR 헤드셋 지원
2. 👥 멀티 유저 협업
3. 📈 레짐 전환 예측 AI

---

## 💡 참고 자료

- **Three.js Docs**: https://threejs.org/docs/
- **React Three Fiber**: https://docs.pmnd.rs/react-three-fiber/
- **Force Graph**: https://github.com/vasturiano/react-force-graph
- **Spline**: https://spline.design/

---

## 📞 도움말

문제 발생시:
1. `/dashboard/REGIME_AI_3D_SETUP.md` 확인
2. Browser console (F12) 에러 확인
3. `npm run dev` 재시작

**Built with ❤️ for Regime Zero**
**Inspired by Tony Stark's Holographic Interface**
