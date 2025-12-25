# G9 시스템 개념 아키텍처 분석

> **핵심 명제**: G9는 승패 예측 시스템이 아니라, **시장이 잘못 가격 매긴 경기 형태(Regime)를 탐지하는 시장 오류 탐지 시스템**이다.

---

## 1. 시스템의 암묵적 핵심 가정들

### 1.1 Market Efficiency Hypothesis (선택적)

**가정**: 시장은 승자 예측에선 효율적이지만, 경기 형태(spread/total/arc)에선 비효율적이다.

**코드 증거**:
- `institutional_evidence.json`: NEUTRAL zone (Edge 45-55) → 50% win rate (Random Walk)
- `g9_pipeline.py:156-163`: Favorite/Underdog 분류 후 **spread/total 베팅만** 생성
- **Moneyline은 SANCTUARY (Edge > 75)에서만** 허용

**함의**:
- G9는 moneyline(승자)을 맞히려 하지 않음
- 대신 시장이 spread/total을 잘못 설정한 경우를 찾음

---

### 1.2 Regime Repeatability (패턴 반복성)

**가정**: 특정 조건 조합(Edge + Flow + Pace + Narrative)이 반복 가능한 게임 아크를 만든다.

**코드 증거**:
- `nba_regime_index.json`: 6,000+ 과거 경기가 9개 Regime으로 분류됨
- `institutional_evidence.json`: GRIND → UNDER 69.4% (379 샘플), COLLAPSE → FADE 63.5% (215 샘플)
- `regime_builder.py:104`: LLM이 9개 고정 클래스 중 하나로 분류 (자유 생성 아님)

**Regime 발생 조건**:
```
GRIND = (Pace < 99 AND Defense > Avg AND Low Volatility)
SANCTUARY = (Edge > 75 AND Flow ∈ {STABLE, UP} AND No Injury)
COLLAPSE = (Flow = STRONG_DOWN AND Fatigue = True AND Public > 60%)
RESILIENT = (Underdog AND Defense Top 10 AND Home)
```

**함의**: Regime은 무작위가 아니라 **조건부 결정론적 패턴**이다.

---

### 1.3 Temporal Persistence (시간적 연속성)

**가정**: Regime은 단일 경기 속성이 아니라 시계열 국면(phase)이다.

**코드 증거**:
- `quant_core.py:28-63`: Window Function으로 L5 Momentum, Volatility 계산
- `07_regime_engine.py:99-146`: SignalIntegrator가 history 기반 트렌드 분류
  - `momentum_phase`: Surging, Ascending, Slumping, Stable
  - `health_phase`: Deteriorating, Recovering, Managed
- `rdata_treasury.csv`: 시간 윈도우 컬럼 (avg_V_4, avg_P_8, NetRtg_L10 등)

**Regime Phase Transitions**:
```
Stable → Ascending (trend > 0.2)
Ascending → Surging (mean_score > 0.7 AND trend > 0.3)
Surging → Slumping (mean_score < -0.5 AND trend < -0.2)
```

**함의**: Regime은 **현재 상태**이자 **과거로부터의 궤적**이다.

---

### 1.4 Narrative Causality (내러티브 인과성)

**가정**: 스토리/감정/맥락은 수치 데이터만큼 중요한 인과 요인이다.

**코드 증거**:
- `/stories_processed/`: 2,269개 경기 스토리 LLM 처리
- `07_regime_engine.py:14-38`: TAG_WEIGHTS 딕셔너리
  - `InjuryReport: -1.2`, `Clutch: 0.8`, `EmotionalTone_Desperate: -0.5`
- `/chroma_db/`: 벡터 DB로 의미적 유사 경기 검색 (Twin matching)
- `g9_pipeline.py:104-110`: preview_text에서 "injury", "pace" 등 키워드 추출

**Tag-to-Regime 매핑**:
```
INJURY tag → COLLAPSE regime (favorite fragility)
Clutch tag → RESILIENT regime (underdog competence)
Fatigue tag → DEAD_ZONE (avoid betting)
```

**함의**: Regime은 **정량적 신호 + 정성적 스토리**의 융합이다.

---

### 1.5 Dead Zone Existence (구조적 예측 불가능 영역)

**가정**: 시장이 정확한 영역(Edge ~50%)은 구조적으로 베팅 불가능하다.

**코드 증거**:
- `institutional_evidence.json`:
  - `DEAD_ZONE`: 1,500 샘플, 50.1% win rate, "No structural advantage"
  - `NEUTRAL`: 4,120 샘플, 50.0% win rate, "Market efficiency is highest"
- `g9_pipeline.py:51-62`: Edge 40-75 사이는 NEUTRAL 처리
- `g9_pipeline.py:162`: NEUTRAL base → `["PASS"]` 반환

**Dead Zone 정의**:
```
Edge ∈ [40, 60] AND (No Strong Tags OR Conflicting Signals) → PASS
```

**함의**: G9는 "모든 경기 예측"이 아니라 **극단(Edge < 40 또는 > 75) 탐지**다.

---

### 1.6 Evidence Gate Requirement (증거 게이트)

**가정**: Regime은 조건 체크리스트를 통과해야만 "진짜" 발생한 것으로 간주된다.

**코드 증거**:
- `g9_pipeline.py:64-100`: `generate_classification_gate()` 함수
- 각 Regime Class마다 2-4개 조건 검증:
  ```python
  gate.append({"cond": "Pace (L4) < 99.0", "met": pace < 99.0})
  gate.append({"cond": "Flow State is STABLE or UP", "met": flow in ["STABLE", "STRONG_UP"]})
  ```
- `g9_pipeline.py:223-230`: 리포트에 "Conditions Met: 3/3" 표시

**Gate 예시 (GRIND)**:
| Condition | Status |
|-----------|--------|
| Pace (L4) < 99.0 | ✅ |
| Defensive Rating > Avg | ✅ |
| Star Usage Volatility Low | ✅ |

**함의**: Regime은 **확률적 예측이 아니라 조건부 검증**이다.

---

## 2. Regime 정의의 분산 위치

Regime은 **단일 정의**가 아니라 **5계층에 분산된 복합 개념**이다:

### 2.1 데이터 계층 (Historical Labels)

**위치**: `/g9_core_export/DATA/nba_regime_index.json`

**정의 방식**: LLM이 사후 분류 (Expectation vs Reality)

**구조**:
```json
{
  "id": "20191022_LOS",
  "regime_type": "Underdog_Upset",
  "regime_delta": "Despite being underdog (42.0%), Clippers won decisively",
  "edge_score": 43.9,
  "flow_state": "UP",
  "result": "Win"
}
```

**Regime Types**:
- Underdog_Upset, Favorite_Collapse, Star_Takeover
- Grind_Win, Grind_Loss, Blowout_Win, Blowout_Loss
- Favorite_Hold, Underdog_Resilience

**특징**: 결과론적 분류 (게임 후 헤드라인 + 결과 기반)

---

### 2.2 로직 계층 (Classification Rules)

**위치**: `/pipeline/07_regime_engine.py`

**구조**:
```
FeatureBuilder → SignalIntegrator → RegimeComposer
```

**1단계 - FeatureBuilder**:
- TAG_WEIGHTS로 스토리 태그를 숫자로 변환
- 벡터 임베딩 평균 방향 계산
- 출력: `{"tag_scores": [0.5, 0.8, 1.2], "mean_vector": [...]}`

**2단계 - SignalIntegrator**:
- 시계열 트렌드 계산 (L3 vs L10 비교)
- Phase 분류:
  ```python
  if mean_score > 0.7 and trend > 0.3: return "Surging"
  if trend > 0.2: return "Ascending"
  if mean_score < -0.5 and trend < -0.2: return "Slumping"
  if abs(trend) < 0.05: return "Stable"
  ```

**3단계 - RegimeComposer**:
- 최종 Regime 객체 생성:
  ```json
  {
    "momentum": "Surging",
    "health": "Deteriorating",
    "variance": "HighVariance",
    "narrative_arc": "RevengeArc"
  }
  ```

**특징**: 시계열 신호 + 태그 가중치 조합

---

### 2.3 의사결정 계층 (Evidence Gates)

**위치**: `/g9_core_export/FACTORY/g9_pipeline.py`

**함수**: `RegimeEngine.generate_classification_gate(regime_class, team_stats)`

**조건 매트릭스**:

| Regime Class | Gate Conditions | Bet Action |
|--------------|-----------------|------------|
| **GRIND** | Pace < 99 AND Defense > Avg | UNDER |
| **SANCTUARY** | Edge > 75 AND Flow ∈ {STABLE, UP} | MONEYLINE_OK |
| **COLLAPSE** | Flow = STRONG_DOWN AND Fatigue | FADE_FAVORITE |
| **RESILIENT** | Underdog AND Defense Top 10 | DOG_SPREAD |
| **TRACK_MEET** | Both Pace > 100 | OVER |

**출력**:
```python
[
  {"cond": "Pace (L4) < 99.0", "met": True},
  {"cond": "Defensive Rating > Avg", "met": True},
  {"cond": "Star Usage Volatility Low", "met": True}
]
```

**특징**: IF-THEN 규칙 기반 게이트 검증

---

### 2.4 시장 증거 계층 (Institutional Evidence)

**위치**: `/g9_core_export/DATA/institutional_evidence.json`

**구조**:
```json
{
  "GRIND": {
    "sample_size": 379,
    "primary_market": "UNDER",
    "win_rate": 0.694,
    "avg_margin": "+6.8",
    "key_stat": "Grind_Win / Grind_Loss Under Rate > 67%"
  }
}
```

**용도**:
- Regime별 역사적 승률로 신뢰도 보정
- 리포트 생성 시 "Historical Evidence" 섹션 표시
- Edge Score와의 교차 검증

**특징**: 실증 기반 확률 앵커

---

### 2.5 실시간 계층 (Daily RData)

**위치**: `/g9_core_export/DATA/rdata_treasury.csv`

**필드**:
- `Pace_L4`, `NetRtg_L10`, `Edge`, `Flow`, `RestDays`
- 시간 윈도우 평균: `avg_V_4`, `avg_P_8`, `avg_diff_P_12`

**역할**:
- Regime 분류의 입력 데이터
- Edge Gate, Flow Gate의 판단 근거
- Team 현재 상태 스냅샷

**특징**: 매일 업데이트되는 팀별 메트릭 타임시리즈

---

## 3. Regime의 본질 - 데이터 vs 상태 vs 규칙

**결론**: Regime은 **세 가지가 동시에 작동하는 복합 구조**이다.

### 3.1 Regime as Data (Pattern Library)

**증거**:
- `nba_regime_index.json`: 6,000+ 과거 경기가 9개 클래스로 레이블링
- `/chroma_db/`: 벡터 DB로 유사 경기 검색 (Twin matching)
- `regime_builder.py`: LLM이 과거 패턴으로 새 경기 분류

**용도**:
- 유사도 검색의 기준점 ("이 경기는 2019-10-22 Clippers vs Lakers와 유사")
- Historical Evidence 통계 생성
- 스토리 임베딩의 참조 데이터베이스

**특징**: **구조화된 역사적 사례집**

---

### 3.2 Regime as State (Temporal Phase)

**증거**:
- `07_regime_engine.py`: SignalIntegrator가 시계열 트렌드 계산
- `quant_core.py`: Window Function으로 L5 Momentum, Volatility
- Phase Transitions: Stable → Ascending → Surging → Slumping

**상태 변수**:
- `momentum_phase`: 현재 추세 국면
- `health_phase`: 부상/컨디션 궤적
- `flow_state`: UP / DOWN / STABLE / STRONG_UP / STRONG_DOWN / COLLAPSE

**특징**: **시간에 따라 변화하는 동적 상태**

**예시**:
```
Game 1: momentum = Stable,     health = Managed
Game 5: momentum = Ascending,  health = Recovering
Game 10: momentum = Surging,   health = Deteriorating  ← REGIME 발생
Game 15: momentum = Slumping,  health = Deteriorating
```

---

### 3.3 Regime as Decision Rule (Classification Logic)

**증거**:
- `g9_pipeline.py`: IF base == "FAVORITE" AND "COLLAPSE" in tags → FADE_FAVORITE
- `generate_classification_gate()`: 조건부 검증 체크리스트
- ActionEngine: Regime → Bet Action 매핑

**의사결정 플로우**:
```
1. Base Direction (Edge > 75 → FAVORITE, Edge < 40 → UNDERDOG)
2. Regime Candidate (Tags + Flow + Pace)
3. Evidence Gate Check (조건 3/3 충족?)
4. Action Decision (BET / FADE / PASS)
```

**매핑 테이블**:
| Base | Tags | Action |
|------|------|--------|
| FAVORITE | COLLAPSE | FADE_FAVORITE |
| FAVORITE | DOMINANT | MONEYLINE_OK |
| UNDERDOG | RESILIENT | DOG_SPREAD |
| NEUTRAL | GRIND | UNDER |

**특징**: **IF-THEN 규칙 기반 의사결정 시스템**

---

## 4. 통합 개념 모델

### 4.1 Regime의 삼위일체 구조

```
┌─────────────────────────────────────────────────────┐
│                    REGIME                           │
│                                                     │
│  ┌───────────┐    ┌───────────┐    ┌───────────┐ │
│  │  PATTERN  │ ←→ │   STATE   │ ←→ │   RULE    │ │
│  │ (Data)    │    │ (Phase)   │    │ (Logic)   │ │
│  └───────────┘    └───────────┘    └───────────┘ │
│       ↑                ↑                 ↑         │
│       │                │                 │         │
│  Historical      Temporal          Conditional    │
│  Similarity      Trend             Gate           │
│  Matching        Tracking          Verification   │
└─────────────────────────────────────────────────────┘
```

### 4.2 Regime 발생의 3단계 검증

**Stage 1: Pattern Matching (데이터 계층)**
```
Query: 현재 경기의 Edge, Flow, Narrative
↓
Vector DB Search: 유사한 과거 경기 (Twin) 찾기
↓
Output: "2019-10-22 Clippers vs Lakers와 구조적 유사 (Cosine 0.92)"
```

**Stage 2: State Classification (상태 계층)**
```
Query: L5 Momentum, L10 NetRtg, Tag Scores
↓
SignalIntegrator: Trend 계산 (short window vs long window)
↓
Output: momentum_phase = "Surging", health_phase = "Deteriorating"
```

**Stage 3: Gate Verification (규칙 계층)**
```
Query: Regime Candidate = "COLLAPSE"
↓
Evidence Gate Check:
  - Flow = STRONG_DOWN? ✅
  - Fatigue/Injury Present? ✅
  - Public Bias > 60%? ✅
↓
Output: Regime = COLLAPSE (Confidence: High)
```

### 4.3 Regime의 시간적 진화

```
t-10: Stable State
  ↓ (Injury News)
t-5: momentum = Ascending, health = Deteriorating
  ↓ (Flow turns STRONG_DOWN)
t-0: ★ REGIME TRIGGER: COLLAPSE
  ↓ (게임 발생)
t+0: Reality Check (Headline matching?)
  ↓
t+1: Regime Label 확정 (nba_regime_index.json 저장)
  ↓
t+∞: Historical Evidence 업데이트
```

---

## 5. 핵심 통찰: Regime은 "언제" 발생하는가?

### 5.1 Regime 발생의 4가지 조건 (ALL must be true)

**① Structural Edge (구조적 우위)**
```
Edge < 40 (Underdog Zone) OR Edge > 75 (Favorite Zone)
→ 시장이 극단적 평가 → 오류 가능성 ↑
```

**② Temporal Momentum (시간적 추세)**
```
Trend > 0.3 (Surging) OR Trend < -0.2 (Slumping)
→ 상태가 급격히 변화 중 → Regime Transition
```

**③ Narrative Catalyst (스토리 촉매)**
```
Tags ∈ {Injury, Clutch, Revenge, Fatigue} 존재
→ 시장이 간과한 맥락 → 가격 부정합
```

**④ Evidence Gate (증거 검증)**
```
Regime-specific conditions 3/3 충족
→ False Positive 필터링 → 신뢰도 확보
```

### 5.2 Regime 비발생 (PASS) 조건

**Dead Zone**:
```
Edge ∈ [40, 60] AND |Trend| < 0.05 AND No Strong Tags
→ 시장 효율적 → 구조적 우위 없음
```

**Conflicting Signals**:
```
Edge > 75 (Favorite) BUT Flow = STRONG_DOWN
AND Tags = {Injury, Fatigue}
→ 방향성 불명확 → 베팅 회피
```

**Gate Failure**:
```
Regime = GRIND Candidate
BUT Pace = 102 (조건: Pace < 99 실패)
→ Regime 미성립 → PASS
```

---

## 6. 아키텍처 설계 원칙

### 6.1 Separation of Concerns (관심사 분리)

**Data Layer**: 패턴 저장 및 검색
- `nba_regime_index.json`, `/chroma_db/`

**Logic Layer**: 상태 추론 및 분류
- `07_regime_engine.py`, `quant_core.py`

**Decision Layer**: 베팅 의사결정
- `g9_pipeline.py`, `ActionEngine`

**Evidence Layer**: 통계적 검증
- `institutional_evidence.json`

### 6.2 Temporal Modularity (시간적 모듈성)

```
Pre-Game (D-1):
  → Narrative Parsing (stories_processed)
  → RData Snapshot (rdata_treasury.csv)

Game Day (D-0):
  → Regime Classification (07_regime_engine.py)
  → Evidence Gate Check (g9_pipeline.py)
  → Decision Output (g9_daily_intelligence.md)

Post-Game (D+0):
  → Result Collection (headlines)
  → Regime Labeling (regime_builder.py)
  → Evidence Update (institutional_evidence.json)
```

### 6.3 Fail-Safe Design (안전 설계)

**Multiple Verification Layers**:
```
Edge Gate → Flow Gate → Pace Gate → Narrative Gate
→ Evidence Gate → Market Overheat Check
```

**Conservative Defaults**:
```python
if not all_conditions_met: return ["PASS"]
if edge in [40, 60]: return ["PASS"]
if conflicting_signals: return ["PASS"]
```

**Historical Anchoring**:
```
Regime Confidence = f(Historical Win Rate, Sample Size, Similarity Score)
```

---

## 7. 시스템의 철학적 전제

### 7.1 Epistemology (인식론)

**Knowledge Source Hierarchy**:
1. **시장 가격** (Edge Score) ← 가장 신뢰
2. **통계 신호** (Pace, NetRtg) ← 객관적
3. **스토리 태그** (Injury, Revenge) ← 맥락적
4. **벡터 유사도** (Twin Matching) ← 구조적

**Truth Test**:
```
Prediction Validity = Historical Evidence (Win Rate > 60%)
                    + Gate Verification (All Conditions Met)
                    + Market Dislocation (Edge Extreme)
```

### 7.2 Ontology (존재론)

**Regime의 존재론적 지위**:
- Regime은 "경기에 내재된 속성"이 아님
- Regime은 **"시장 기대 vs 현실 구조"의 관계**임
- 같은 경기도 시장 가격에 따라 다른 Regime 가능

**예시**:
```
Game: Lakers vs Clippers
Market A (Edge 43.9): Underdog_Upset (Clippers 관점)
Market B (Edge 65.4): Favorite_Collapse (Lakers 관점)
→ 동일 게임, 다른 Regime (관점 의존적)
```

### 7.3 Causality (인과론)

**Regime은 원인인가, 결과인가?**
- **사전적**: Regime은 **구조적 조건의 결과**
  - Injury → Flow DOWN → COLLAPSE Regime
- **사후적**: Regime은 **시장 오류의 원인**
  - COLLAPSE Regime → Favorite 과대평가 → FADE 수익

**Causal Graph**:
```
Edge Extreme + Flow Shift + Narrative Catalyst
         ↓
    Regime Formation
         ↓
Market Mispricing + Structural Inefficiency
         ↓
    Betting Edge
```

---

## 8. 시스템의 한계와 가정의 취약점

### 8.1 Data Dependency

**가정**: 과거 패턴이 미래에 반복된다
**리스크**: Regime Drift (새로운 패턴 등장)

**완화 장치**:
- LLM 기반 동적 분류 (regime_builder.py)
- 시즌별 Evidence 재계산

### 8.2 Causality vs Correlation

**가정**: Regime이 시장 오류를 "야기"한다
**리스크**: 실제론 제3 변수의 상관관계일 수 있음

**완화 장치**:
- Evidence Gate로 조건부 검증
- Sample Size > 100 필터링

### 8.3 Lookback Bias

**가정**: 사후 헤드라인으로 분류한 Regime이 사전 예측 가능
**리스크**: Overfitting to narrative

**완화 장치**:
- Pre-game signals만 사용 (preview_text)
- Post-game headline은 validation용으로만

### 8.4 Market Adaptation

**가정**: 시장이 Regime 패턴을 학습하지 않음
**리스크**: Public이 G9 로직 학습 → Edge 소멸

**완화 장치**:
- Dead Zone 확대 (Edge 40-60 → 35-65)
- Evidence 주기적 재훈련

---

## 9. 결론: Regime의 정체

### Regime은 무엇인가?

**정답**: Regime은 **"데이터-상태-규칙"의 삼위일체**이다.

```
┌─────────────────────────────────────────────────────┐
│ REGIME = Pattern(Historical) ⊗ State(Temporal)     │
│          ⊗ Rule(Conditional) ⊗ Evidence(Empirical) │
└─────────────────────────────────────────────────────┘
```

**구성 요소**:
1. **패턴 (Data)**: 유사 과거 경기 검색 기준
2. **상태 (State)**: 시간적 추세 국면 (Surging, Slumping)
3. **규칙 (Rule)**: 조건부 의사결정 로직 (IF-THEN Gate)
4. **증거 (Evidence)**: 통계적 신뢰도 앵커 (Win Rate, Sample Size)

### Regime은 언제 발생하는가?

**4-Factor Conjunction** (모두 충족 필요):
```
① Edge Extreme (< 40 OR > 75)
② Temporal Shift (|Trend| > 0.2)
③ Narrative Catalyst (Strong Tags)
④ Gate Verification (Conditions Met)
```

### G9의 본질

G9는 **베이지안 시장 오류 탐지기**이다:
```
P(Regime | Signals) = P(Signals | Regime) × P(Regime) / P(Signals)
                       ↑                     ↑           ↑
                  Historical            Edge Zone    Market
                  Evidence              Prior        Efficiency
```

**최종 명제**:
> Regime은 "경기의 속성"이 아니라 **"시장 기대와 게임 구조의 부정합 패턴"**이다.
> G9는 이 부정합이 반복 가능한 조건 하에서 발생함을 전제하고,
> 과거 데이터 + 실시간 상태 + 조건부 검증을 통해 이를 탐지한다.

---

## 부록: 주요 파일별 Regime 정의 매핑

| 파일 | Regime 정의 방식 | 역할 |
|------|-----------------|------|
| `nba_regime_index.json` | LLM 사후 분류 (9개 클래스) | 패턴 라이브러리 |
| `07_regime_engine.py` | 시계열 Phase 분류 | 상태 추론 |
| `g9_pipeline.py` | Evidence Gate 검증 | 규칙 기반 결정 |
| `institutional_evidence.json` | 통계적 Win Rate | 신뢰도 보정 |
| `rdata_treasury.csv` | 팀별 실시간 메트릭 | 입력 데이터 |
| `quant_core.py` | Window Function 계산 | 시계열 변환 |
| `regime_builder.py` | LLM Expectation vs Reality | 라벨 생성 |
| `analyze_regime_patterns.py` | Edge Bucket 분석 | 패턴 발견 |

---

**문서 버전**: 1.0
**작성일**: 2025-12-18
**분석 대상**: G9 NBA Prediction System (nba_data/)
**방법론**: 코드 정적 분석 + 데이터 구조 역공학 + 개념적 추상화
