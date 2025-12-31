# G9 Bulletin Pipeline Architecture

## 문제 (v3.4 이전)

```
┌─────────────────────────────────────────────────────────────────┐
│  BEFORE: 두 시스템이 따로 놈                                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  data_validator.py                                              │
│       ↓ VIX: 14.58                                              │
│       (Yahoo Finance 실시간)                                     │
│                                                                 │
│  bulletin_generator.py                                          │
│       ↓ LIQUIDITY_STRESS: PEAK                                  │
│       (Neo4j 과거 데이터)                                        │
│                                                                 │
│  ❌ 불일치: "VIX 14.58인데 LIQUIDITY_STRESS PEAK?"               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 해결 (v3.5 Unified Pipeline)

```
┌─────────────────────────────────────────────────────────────────┐
│  AFTER: 통합 파이프라인                                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [1] DVSS (data_validator.py)                                   │
│       ├── L1: Completeness (20%)                                │
│       ├── L2: Range (20%)                                       │
│       ├── L3: Rate of Change (35%) ⭐                           │
│       └── L4: Cross-Validation (25%)                            │
│       ↓                                                         │
│       validated_data = {VIX: 14.58, DXY: 98.0, ...}             │
│                                                                 │
│  [2] State Engine (state_machine_engine.py)                     │
│       ├── Input: validated_data                                 │
│       ├── Extract observations (관계, 불균형)                    │
│       └── Calculate state activations                           │
│       ↓                                                         │
│       states = {active_states: 0} ← VIX 14.58 = 스트레스 없음   │
│                                                                 │
│  [3] Bulletin Generator                                         │
│       ├── Input: validated_data + states                        │
│       └── Output: 일관된 보고서                                  │
│                                                                 │
│  ✅ 일치: "VIX 14.58 → 스트레스 없음 → Standard Risk"            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 핵심 파일

| 파일 | 역할 | 상태 |
|------|------|------|
| `engine/data_validator.py` | DVSS 4-Layer 검증 | ✅ 핵심 |
| `engine/unified_pipeline.py` | 통합 오케스트레이터 | ✅ 핵심 |
| `engine/generate_bulletin.py` | 간단한 CLI 진입점 | ✅ 핵심 |
| `engine/state_graph/state_machine_engine.py` | 상태 계산 엔진 | ✅ 핵심 |
| `engine/state_graph/bulletin_generator.py` | 레거시 (Neo4j 직접 읽음) | ⚠️ 정리 대상 |
| `engine/state_graph/adjudication_engine.py` | 레거시 (Neo4j 직접 읽음) | ⚠️ 정리 대상 |

## 사용법

```bash
# 통합 파이프라인 (권장)
python3 engine/generate_bulletin.py --date 2025-12-30

# 또는 직접 실행
python3 engine/unified_pipeline.py --date 2025-12-30
```

## DVSS Critical Rules

| Layer | Threshold | Action |
|-------|-----------|--------|
| L1 Completeness | < 70 | 🔴 BLOCK |
| L2 Range | < 85 | 🔴 BLOCK |
| L3 Rate of Change | < 70 OR >2x threshold | 🔴 BLOCK |
| L4 Cross-Validation | < 50 | ⚠️ WARN |

**L3 Critical Rule:**
```
DXY -9.4% = 3.1x threshold (3%)
→ CRITICAL FAILURE → Score = 0 → 발행 차단
```

## State Calculation Logic

```python
# VIX 14.58, Gold +1.78% = 스트레스 없음
if gold_chg < -1.5 and vix_chg > 2.0:
    safe_asset_liquidation = True  # 발동 안 됨

# 결과: Active States = 0 (정상)
```

**이전 시스템이 틀렸던 이유:**
- Neo4j에 저장된 과거 StateSnapshot을 읽음
- 그 시점의 데이터로 계산된 LIQUIDITY_STRESS: PEAK
- 현재 VIX 14.58과 무관

## 정리 대상

```bash
# 레거시 (통합 파이프라인으로 대체됨)
engine/state_graph/bulletin_generator.py  # → generate_bulletin.py 사용
engine/state_graph/adjudication_engine.py  # → unified_pipeline.py가 대체
```

## 한줄 요약

> **"Validation 데이터로 State를 재계산해야 VIX 14.58 ≠ LIQUIDITY_STRESS PEAK 문제가 해결됨"**
