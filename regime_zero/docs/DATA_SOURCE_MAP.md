# G9 데이터 소스 맵

## 현재 상태 (2025-12-30) - 정리 완료

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CLEAN ARCHITECTURE (v2)                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Yahoo Finance ──→ DVSS ──→ State Engine ──→ Bulletin                       │
│       │             │            │              │                           │
│   실시간 데이터   4-Layer     실시간 계산    일관된 출력                      │
│                   검증                                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                         DEPRECATED (2025-12-30)                              │
├──────────────────┬──────────────────┬──────────────────────────────────────┤
│     SQLite       │      Neo4j       │    Supabase                          │
│  market_stress   │  StateSnapshot   │    econ_daily                        │
├──────────────────┼──────────────────┼──────────────────────────────────────┤
│ ❌ 백업 후 삭제  │ 🟡 참조용 보관   │ ❌ web auth 전용                      │
│ deprecated/      │ (선택적 사용)    │    데이터 테이블 없음                 │
└──────────────────┴──────────────────┴──────────────────────────────────────┘
```

## 엔진별 데이터 소스 의존성

| 엔진 | 읽는 소스 | 상태 | 결과 |
|------|-----------|------|------|
| `bulletin_generator.py` | SQLite (market_stress) | 🔴 1년 전 | "data not available" |
| `adjudication_engine.py` | Neo4j (StateSnapshot) | 🟡 17시간 전 | LIQUIDITY_STRESS: PEAK |
| `hybrid_rag_engine.py` | Supabase (econ_daily) | 🔴 테이블 없음 | fallback to local |
| `conflict_resolution_engine.py` | Supabase (econ_daily_snapshot) | 🔴 테이블 없음 | 실패 |
| `data_validator.py` | Yahoo Finance | ✅ 실시간 | VIX: 14.58, DXY: 97.99 |
| `unified_pipeline.py` | Yahoo Finance → State Engine | ✅ 실시간 | 정상 작동 |

## 문제 분석

### 1. SQLite (market_stress.db)

```
위치: /Users/js/g9/regime_zero/data/market_stress.db

스키마:
- id: INTEGER
- indicator: TEXT (VIX, DXY, IG_SPREAD, etc.)
- value: REAL
- date: TEXT
- threshold: REAL
- is_stressed: INTEGER

문제:
- 최신 데이터: 2024-12-27 (1년 전!)
- DXY: 128.697 (실제 ~98, 오염됨)
- 업데이트 파이프라인 중단됨
```

### 2. Neo4j (StateSnapshot)

```
스키마:
- StateSnapshot: {id, date, timestamp, liquidity_pressure, ...}
- StateNode: {id, drivers, signals, ...}
- ACTIVATED 관계: {level, confidence, drivers}

문제:
- 데이터는 있지만 새벽 3:29에 계산됨
- 17시간 전 시장 상황 반영
- Bulletin 생성 시 stale 데이터
```

### 3. Supabase (econ_daily)

```
기대 스키마:
- date, vix, spx, gold, dxy, btc, etc.
- vix_pct_change, spx_pct_change, etc.

문제:
- 테이블 자체가 존재하지 않음
- PGRST205: Could not find table 'public.econ_daily'
- 아예 생성 안 됨
```

## 해결 방안

### Option A: 모든 데이터 소스 수리

```
[파이프라인 복구]
1. market_stress_collector.py 재가동 → SQLite 업데이트
2. Supabase에 econ_daily 테이블 생성
3. Neo4j StateSnapshot 실시간 업데이트

문제: 파이프라인 복잡, 유지보수 부담
```

### Option B: Yahoo Finance 단일 소스 (Unified Pipeline) ✅

```
[단순화]
1. Yahoo Finance에서 실시간 데이터 fetch
2. DVSS로 검증
3. State Engine에서 실시간 계산
4. Bulletin 생성

장점: 단일 소스, 항상 최신, 검증됨
```

## 권장 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                   UNIFIED PIPELINE (권장)                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Yahoo Finance ──→ DVSS ──→ State Engine ──→ Bulletin           │
│       │              │            │              │              │
│   실시간 데이터   4-Layer 검증   실시간 계산    일관된 출력       │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                   LEGACY (참고용 보관)                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  SQLite ──→ bulletin_generator.py (레거시)                      │
│  Neo4j ──→ adjudication_engine.py (레거시)                      │
│  Supabase ──→ hybrid_rag_engine.py (비활성)                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 정리 완료 (2025-12-30)

| 파일 | 이전 역할 | 조치 | 상태 |
|------|-----------|------|------|
| `engine/state_graph/bulletin_generator.py` | SQLite + Neo4j 읽기 | DEPRECATED 주석 추가 | ✅ |
| `engine/state_graph/adjudication_engine.py` | Neo4j StateSnapshot 읽기 | DEPRECATED 주석 추가 | ✅ |
| `engine/state_graph/hybrid_rag_engine.py` | Supabase 읽기 시도 | DEPRECATED 주석 추가 | ✅ |
| `data/market_stress.db` | 1년 전 오염 데이터 | `data/deprecated/`로 백업 | ✅ |

## 핵심 파일 (유지)

| 파일 | 역할 |
|------|------|
| `engine/data_validator.py` | DVSS 4-Layer 검증 (Yahoo Finance) |
| `engine/unified_pipeline.py` | 통합 오케스트레이터 |
| `engine/generate_bulletin.py` | CLI 진입점 |
| `engine/state_graph/state_machine_engine.py` | 상태 계산 로직 |
| `engine/state_graph/state_ontology.py` | 상태 정의 |

## 한줄 요약

> **SQLite 1년 전, Neo4j 17시간 전, Supabase 없음 → Yahoo Finance 실시간이 유일한 정상 소스**
