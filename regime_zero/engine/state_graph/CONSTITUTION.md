# G9 STATE ADJUDICATION BULLETIN — CONSTITUTION

> 이 문서는 State Graph Adjudication Engine의 출력 규격을 정의한다.
> 모든 Bulletin은 이 형식을 따라야 한다.

---

## PRODUCT IDENTITY

| 항목 | 정의 |
|------|------|
| 제품명 | G9 State Adjudication Bulletin |
| 엔진 | State Graph Adjudication Engine v2.0 |
| 데이터 소스 | Neo4j State Graph + Supabase Quant Layer |
| 출력 빈도 | 구조적 변화 감지 시 (Not daily) |
| 핵심 가치 | 예측 회피, 구조 진단, 모순 감지 |

---

## OUTPUT STRUCTURE (MANDATORY)

### 1. EXECUTIVE ENTRY (Human Layer · 30초 컷)
- 3줄 이내 요약
- "What this means now" 섹션
- 비전문가도 이해 가능

### 2. SYSTEM VERDICT (1-Line Judgment)
```
VERDICT: [STRUCTURAL INSTABILITY / COHERENT / TRANSITION_IMMINENT]
```
- Neutral/Stable/Tradable 여부 명시
- "현재 상태 자체가 리스크 시그널" 판정 포함

### 3. DOMINANT STATE PRESSURES
- Intensity ≥ 0.5 상태만 포함
- 각 상태별:
  - Intensity (0.0–1.0)
  - Level (PEAK/HIGH/ELEVATED)
  - Activation (FULL/PARTIAL)
  - Mechanisms 나열

### 4. STRUCTURAL CONTRADICTIONS
- 각 모순별:
  - 기술적 명칭 (LIQUIDATION_HEDGE_PARADOX 등)
  - 왜 지속 불가능한지
  - 무엇이 부서져야 해결되는지
- 최종 Status: RESOLUTION_SUSPENDED / ACTIVE / COMPLETED

### 5. TRANSITION ZONE (Quantified)
```
Computed Score: X.X → [LOW/MEDIUM/HIGH]

Elevated states      = X.0
Peak state           = X.0
Reinforcing interaction = X.X
Stabilizers          = -X.X
──────────────────────────
TOTAL                = X.X
```

### 6. WHAT THE MARKET IS LYING ABOUT
- LIE #1, #2, #3 형식
- 각각: Claim → Reality → Consequence

### 7. RESOLUTION PATHS
- PATH A (ESCALATION): Speed, Triggers, Mechanism
- PATH B (ABSORPTION): Speed, Triggers, Mechanism
- ASYMMETRY NOTE: 어느 경로가 구조적으로 더 쉬운지

### 8. ACTIONABLE WATCH WINDOW (48–72H)
- High-Priority Triggers 리스트
- 각 트리거 → 활성화될 상태 → 의미

### 9. FINAL ADJUDICATION
- 단일 문단
- 시스템이 결정 못하는 것
- 가장 민감한 부분
- 급속 해결을 강제할 조건

---

## HARD CONSTRAINTS

| 금지 | 이유 |
|------|------|
| 투자 조언 | 법적 리스크 |
| "아마도", "likely" 무조건부 사용 | 근거 없는 확신 |
| 매끄러운 서사 | 모순을 가림 |
| 거시경제 클리셰 | 차별성 없음 |
| 일일 발행 | 희소성 파괴 |

---

## DATA ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────┐
│                    HYBRID RAG LAYER                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐         ┌─────────────────┐           │
│  │   SUPABASE      │         │    NEO4J        │           │
│  │  (Quant Layer)  │         │ (State Graph)   │           │
│  ├─────────────────┤         ├─────────────────┤           │
│  │ • Daily Metrics │         │ • 25 State Nodes│           │
│  │ • Z-scores      │         │ • Interactions  │           │
│  │ • Price Data    │         │ • Blocking Rules│           │
│  │ • News Headlines│         │ • 20K Regimes   │           │
│  │ • Quant Proxies │         │ • Transition    │           │
│  └────────┬────────┘         └────────┬────────┘           │
│           │                           │                     │
│           └───────────┬───────────────┘                     │
│                       │                                     │
│              ┌────────▼────────┐                           │
│              │  ADJUDICATION   │                           │
│              │     ENGINE      │                           │
│              └────────┬────────┘                           │
│                       │                                     │
│              ┌────────▼────────┐                           │
│              │    BULLETIN     │                           │
│              │    OUTPUT       │                           │
│              └─────────────────┘                           │
└─────────────────────────────────────────────────────────────┘
```

---

## VERSION HISTORY

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-30 | 헌법 제정 |

---

*© G9 Regime Zero*
