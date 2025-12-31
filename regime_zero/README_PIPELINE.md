# G9 Regime Zero - Clean Pipeline Architecture

**최종 정리: 2025-12-30**

---

## 🎯 핵심 원칙

```
Yahoo Finance (Primary) → DVSS → State Engine → Bulletin
           ↓
      SQLite (History, Write-Only)
```

**단일 소스, 실시간, 일관성 보장**

---

## 📊 데이터 소스 정책

| Source | Role | Status |
|--------|------|--------|
| **Yahoo Finance** | 🟢 Primary (실시간) | ACTIVE |
| **SQLite** | 🟡 History (쓰기 전용) | ACTIVE |
| **Neo4j** | 🟡 Optional (분석용) | OPTIONAL |
| **Supabase** | 🔵 Web Auth Only | AUTH-ONLY |

### 중요: 읽기 금지

- SQLite는 **절대 읽지 않음** (과거 데이터 오염 위험)
- Neo4j는 선택적 사용 (분석, 관계 탐색 전용)
- 모든 실시간 데이터는 Yahoo Finance에서

---

## 🚀 빠른 시작

### 1. Bulletin 생성 (권장)

```bash
cd /Users/js/g9/regime_zero
python3 engine/generate_bulletin.py --date 2025-12-30
```

**출력:**
- Console: 파이프라인 실행 로그 + Bulletin
- File: `reports/bulletins/BULLETIN_2025-12-30.md`

### 2. 직접 파이프라인 실행

```bash
python3 engine/unified_pipeline.py --date 2025-12-30 \
  --output bulletin.md \
  --json result.json
```

### 3. History 확인

```bash
python3 engine/history_writer.py
```

---

## 📁 파일 구조

```
regime_zero/
├── engine/
│   ├── unified_pipeline.py      # ✅ MAIN - 통합 파이프라인
│   ├── generate_bulletin.py     # ✅ MAIN - Bulletin 생성기
│   ├── data_validator.py        # ✅ ACTIVE - DVSS v2.0
│   ├── history_writer.py        # ✅ ACTIVE - SQLite 쓰기 전용
│   │
│   ├── state_graph/
│   │   ├── state_machine_engine.py  # ✅ ACTIVE - State 계산
│   │   ├── bulletin_generator.py    # ⚠️ DEPRECATED (레거시)
│   │   ├── adjudication_engine.py   # ⚠️ DEPRECATED (레거시)
│   │   └── hybrid_rag_engine.py     # ⚠️ DEPRECATED (레거시)
│   │
│   └── ...
│
├── data/
│   ├── pipeline_history.db      # ✅ NEW - 히스토리 전용
│   └── deprecated/
│       └── market_stress.db     # ❌ DELETED - 오염된 DB
│
└── docs/
    ├── DATA_SOURCE_MAP.md       # 📚 데이터 소스 맵
    └── README_PIPELINE.md       # 📚 이 파일
```

---

## 🔄 파이프라인 구조

### STEP 1: DVSS Validation

```python
from data_validator import DataValidator

validator = DataValidator()
dvss_report = validator.validate("2025-12-30")

# 4-Layer 검증:
# - L1: Completeness (데이터 존재)
# - L2: Range (정상 범위)
# - L3: Rate of Change (변화율)
# - L4: Cross-Validation (상관관계)
```

**통과 기준:**
- Total Score ≥ 70/100
- L1 ≥ 80/100 (핵심 데이터 필수)

### STEP 2: State Calculation

```python
from state_graph.state_machine_engine import StateMachineEngine

state_engine = StateMachineEngine()
state_result = state_engine.process(validated_data, date)

# 산출:
# - active_states: 활성화된 스트레스 상태
# - observation_summary: 시장 관찰 요약
# - imbalances: 시장 불균형 지표
```

### STEP 3: Bulletin Generation

```python
bulletin = _build_bulletin_from_result(pipeline_result)

# 포함 내용:
# 1. DVSS 검증 리포트
# 2. 시장 데이터 (검증됨)
# 3. State 분석 (실시간 계산)
# 4. 전략적 요약
```

### STEP 4: History Save (Optional)

```python
from history_writer import HistoryWriter

writer = HistoryWriter()
writer.save_snapshot(pipeline_result)

# 저장 위치: data/pipeline_history.db
# 용도: 히스토리 보관 (읽기 금지!)
```

---

## 🧪 테스트

### 전체 파이프라인 테스트

```bash
python3 engine/unified_pipeline.py --date 2025-12-30
```

**예상 출력:**
```
=================================================================
  UNIFIED PIPELINE v1.0
  Date: 2025-12-30
=================================================================

[STEP 1] Running DVSS Validation...

✅ DVSS Score: 85/100 (Grade A)

[STEP 2] Converting validated data to market format...
  Converted 7 indicators

[STEP 3] Calculating States from validated data...
  Active States: 3
    - LIQUIDITY_STRESS: LOW (0.32)
    - EQUITY_TURBULENCE: BASELINE (0.45)
    - SAFE_HAVEN_DEMAND: ELEVATED (0.58)

[STEP 4] Building unified result...

[VERIFICATION] Checking data-state consistency...
  ✅ VIX=14.6 consistent with state levels
  ✅ Data and states are consistent

=================================================================
  PIPELINE COMPLETE
=================================================================

✅ History saved: 2025-12-30 (7 indicators, 3 states)
```

### History 확인

```bash
python3 engine/history_writer.py
```

**예상 출력:**
```
📊 SQLite History Database Stats
==================================================
Total snapshots: 15
Latest: 2025-12-30 at 2025-12-30 20:56:42
  DVSS: 85/100 (Grade A)
Date range: 2025-12-16 → 2025-12-30

⚠️ This database is WRITE-ONLY
Pipeline should always fetch from Yahoo Finance, not this DB.
```

---

## ⚠️ 주의사항

### ❌ 절대 하지 말 것

1. **SQLite에서 읽지 마세요**
   ```python
   # ❌ BAD
   cursor.execute("SELECT * FROM market_history WHERE date = ?", (date,))

   # ✅ GOOD
   validator.validate(date)  # Yahoo Finance에서 가져옴
   ```

2. **레거시 파일 사용 금지**
   ```python
   # ❌ DEPRECATED
   from bulletin_generator import generate_bulletin
   from adjudication_engine import AdjudicationEngine
   from hybrid_rag_engine import HybridRAG

   # ✅ USE THIS
   from unified_pipeline import UnifiedPipeline
   ```

3. **Supabase 데이터 테이블 접근 금지**
   ```python
   # ❌ Supabase = Web Auth Only
   supabase.table("econ_daily").select("*")  # 테이블 없음!

   # ✅ Use Yahoo Finance
   validator.validate(date)
   ```

### ✅ 권장 사항

1. **항상 unified_pipeline.py 사용**
2. **DVSS 검증 통과 확인**
3. **히스토리는 선택적 저장**
4. **Neo4j는 분석 시에만 사용** (optional)

---

## 🔧 설정

### 환경변수 (.env)

```bash
# Yahoo Finance (자동, API 키 불필요)
# 기본적으로 작동함

# Optional: Neo4j (분석용)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# Supabase (Web Auth 전용)
NEXT_PUBLIC_SUPABASE_URL=https://...
NEXT_PUBLIC_SUPABASE_ANON_KEY=...
```

### Dependencies

```bash
pip3 install yfinance pandas python-dotenv
```

**Optional (분석용):**
```bash
pip3 install neo4j  # Graph 분석 시에만
```

---

## 📈 성능

| Metric | Value |
|--------|-------|
| Pipeline 실행 시간 | ~5초 |
| DVSS Validation | ~2초 |
| State Calculation | ~1초 |
| Bulletin Generation | ~1초 |
| History Save | ~0.5초 |

**총 소요 시간: ~5초 (실시간 데이터 포함)**

---

## 🎓 아키텍처 철학

### 단순함 = 신뢰성

```
복잡도 ∝ 장애점 개수
```

- 4개 데이터 소스 (3개 죽음) → **1개로 단일화**
- 3개 레거시 엔진 → **1개 통합 파이프라인**
- 읽기/쓰기 혼재 → **읽기는 Yahoo, 쓰기는 SQLite**

### 일관성 > 완벽함

```
실시간 데이터 + 검증된 상태 = 일관된 Bulletin
```

- VIX 14.58 → LIQUIDITY_STRESS: LOW ✅
- 오래된 Neo4j → LIQUIDITY_STRESS: PEAK ❌

**실시간 계산이 정답입니다.**

---

## 📞 문제 해결

### Bulletin이 이상할 때

1. **DVSS 점수 확인**
   ```bash
   python3 engine/unified_pipeline.py --date 2025-12-30
   ```
   - Total Score < 70 → 데이터 문제
   - L1 < 80 → 핵심 데이터 누락

2. **State 일관성 확인**
   - VIX 낮은데 LIQUIDITY_STRESS 높음 → 문제!
   - 파이프라인이 자동으로 경고 출력

3. **히스토리 확인**
   ```bash
   python3 engine/history_writer.py
   ```
   - 최근 스냅샷 날짜 확인
   - DVSS Grade 추이 확인

### 데이터가 안 나올 때

1. **Yahoo Finance 접근 확인**
   ```python
   import yfinance as yf
   vix = yf.Ticker("^VIX")
   print(vix.history(period="1d"))
   ```

2. **인터넷 연결 확인**

3. **시장 휴일 확인** (주말, 공휴일)

---

## 🚀 다음 단계

### 완료된 작업 ✅

- [x] 데이터 소스 단일화 (Yahoo Finance)
- [x] DVSS 4-Layer 검증
- [x] State 실시간 계산
- [x] SQLite 히스토리 저장 (write-only)
- [x] 레거시 파일 DEPRECATED 처리

### 향후 계획 📋

- [ ] Neo4j 그래프 분석 (optional)
- [ ] 과거 데이터 백테스팅
- [ ] Bulletin 품질 개선 (LLM)
- [ ] Web Dashboard 연동

---

**문서 버전: v1.0 (2025-12-30)**

*단순함이 정답입니다. 복잡성 = 장애점.*
