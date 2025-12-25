# 경제레짐 State Graph 프로젝트 지침서

**Date**: 2024-12-24
**For**: 새로운 Claude Code 세션
**Context**: NBA State Graph 시스템 구축 경험을 바탕으로 경제레짐 분석 시스템 구축

---

## 🎯 프로젝트 목표

### 핵심 컨셉
**300만개 경제뉴스 헤드라인 → 2만개 레짐 → 19개 클러스터 → Neo4j State Graph**

### 왜 State Graph인가?
```
기존 정량 모델의 문제:
금리 4.5% → 블랙박스 → "S&P 5% 하락 예상"
→ WHY를 설명 못함, 맥락 소실

State Graph 접근:
현재 상태: "고금리 + 저유동성 + 불안심리"
  ↓ Graph RAG
유사 과거: "2018년 12월 파월 쇼크"
  ↓ 관계 탐색
당시 레짐: "수축 전환기"
  ↓ 섹터 상성
승자 섹터: 방어주 (+8%), 금 (+12%)
패자 섹터: 기술주 (-15%)
  ↓ 전환 확률
다음 레짐: "위기" (65%), "안정화" (35%)
```

**→ 맥락을 보존하고, WHY를 설명 가능**

---

## 📊 데이터 현황 (사용자 제공)

### 입력 데이터
1. **300만개 헤드라인** (2025년 경제뉴스)
2. **2만개 레짐** (헤드라인을 임베딩 → 레짐으로 압축)
3. **19개 클러스터** (2만 레짐을 19개 상태로 분류)

### 도메인 매핑 (사용자 제공 스크린샷 기반)
```
구성요소      보험기 CRM          NBA 분석              경제레짐
──────────────────────────────────────────────────────────
핵심 엔티티   고객                팀/선수               시장/섹터
현재 상태     가망→체결→계약      폼/피로/부상          확장/수축/전환
영향 요인     상담사,가격,보조금  일정,코치,심판        금리,유동성,심리
이벤트        반품,업그레이드      트레이드,부상         정책발표,충격
```

**→ 이 3개 도메인은 같은 State Graph 엔진을 공유**

---

## 🏗️ NBA 프로젝트에서 배운 핵심 원칙

### 1. "돌다리도 두들겨보고 설계한다음 폭발적으로 달려나가자"

**의미**:
- 자동화에 급하게 뛰어들지 말 것
- 작은 샘플로 먼저 검증
- Schema를 여러번 리팩토링 OK
- 품질 > 속도

**NBA에서의 실수**:
```python
# 통계 자동 감지 → Gap Defense 과감지 (10/11)
# 원인: 시그니처가 너무 관대
```

**교훈**:
- 자동 분류는 신중하게
- 처음엔 수동 Input으로 시작
- 수동 데이터로 자동화 검증

### 2. Schema 설계는 반복적 개선

**NBA Schema 변천**:
```
V1.0 → 피드백 7개 받음
  1. MatchupHistory 노드 → 관계로 변경
  2. team_abbr 제거
  3. lineups 배열 → 관계로 변경
  ...
V2.1 FINAL → Production Ready
```

**경제레짐 적용**:
- 처음부터 완벽한 Schema 기대하지 말것
- 핵심 노드/관계만 먼저 정의
- 사용하면서 개선

### 3. 데이터 희소성 처리

**문제**: "Scott Foster + Gap Defense = 샘플 5개"

**해결**:
```python
# 1. Wilson Score Interval (신뢰구간)
# 2. Bayesian Prior (과적합 방지)
# 3. Transfer Learning (유사 전술에서 지식 전이)
```

**경제레짐 적용**:
- 희귀 레짐 (샘플 적음) → 유사 레짐에서 전이
- 신뢰구간 명시
- 불확실성을 숨기지 말것

### 4. 품질 관리 자동화

**NBA 시스템**:
```python
# 일관성 체크: 같은 통계인데 다른 전술?
# Confidence 검증: 샘플 5개인데 confidence 0.9?
# 모순 감지: Gap Defense + Pace & Space 동시?
```

**경제레짐 적용**:
- 모순 레짐 감지 (예: "확장" + "수축" 동시)
- Confidence 과신 방지
- 자동 경고 시스템

### 5. Vector Search는 선택적

**NBA 경험**:
- 초기엔 GameState만 Vector 임베딩
- 나중에 확장 가능

**경제레짐 적용**:
- 300만 헤드라인 전부 임베딩 ✗
- 핵심 이벤트만 선별 임베딩 ✓
- MarketState만 임베딩으로 시작

---

## 🎨 경제레짐 Neo4j Schema (초안)

### 핵심 노드 (5개만)

```cypher
// 1. 시장/섹터
(:Sector {
  name: STRING,           // "기술주", "금융주", "에너지"
  classification: STRING  // "Cyclical", "Defensive", "Growth"
})

// 2. 레짐 (19개 클러스터)
(:Regime {
  id: INTEGER,            // 0~18
  name: STRING,           // "확장", "수축", "전환", "위기", ...
  description: STRING,

  occurrence_count: INTEGER,  // 2만 레짐 중 몇번 나왔나
  avg_duration_days: INTEGER
})

// 3. 상태 스냅샷 (2만개)
(:MarketState {
  state_id: STRING,
  date: DATE,

  regime_id: INTEGER,     // 0~18
  regime_confidence: FLOAT,

  // 주요 지표
  sp500: FLOAT,
  vix: FLOAT,
  fed_rate: FLOAT,

  // Vector (유사 상황 검색용)
  embedding: LIST<FLOAT>  // 선택적
})

// 4. 영향 요인
(:Factor {
  name: STRING,           // "금리", "유동성", "심리지수"
  category: STRING,       // "monetary", "sentiment", "fundamental"

  bullish_threshold: FLOAT,
  bearish_threshold: FLOAT
})

// 5. 이벤트 (핵심만)
(:Event {
  event_id: STRING,
  date: DATE,
  headline: STRING,       // 원본 헤드라인
  impact_score: FLOAT,    // -1.0 ~ 1.0

  embedding: LIST<FLOAT>  // 선택적
})
```

### 핵심 관계 (4개만)

```cypher
// 1. 레�im 전환
(Regime)-[:TRANSITIONS_TO {
  probability: FLOAT,     // 역사적 확률
  avg_duration: INTEGER,
  sample_size: INTEGER
}]->(Regime)

// 2. 섹터 상성 (NBA의 COUNTERS!)
(Sector)-[:OUTPERFORMS_IN {
  regime_id: INTEGER,
  avg_alpha: FLOAT,       // 초과 수익률
  win_rate: FLOAT,
  sample_size: INTEGER
}]->(Regime)

// 3. 레짐 영향 요인
(Regime)-[:INFLUENCED_BY {
  correlation: FLOAT,
  lag_days: INTEGER
}]-(Factor)

// 4. 유사 상황
(MarketState)-[:SIMILAR_TO {
  cosine_similarity: FLOAT
}]->(MarketState)
```

---

## 📋 Phase 1: 데이터 파악 및 검증

### Step 1: 데이터 확인
```bash
# 사용자에게 요청할 정보:
1. 2만 레짐 데이터 파일 위치? (CSV? JSON?)
2. 19개 클러스터 매핑? (어떤 레짐이 어떤 클러스터?)
3. 300만 헤드라인 필요? (아니면 2만 레짐만?)
4. 시장 지표 데이터? (S&P500, VIX, 금리 등)
```

### Step 2: 샘플 데이터 확인
```python
# 2만 레짐 중 100개만 먼저 로드
import pandas as pd

regimes = pd.read_csv('regimes.csv', nrows=100)
print(regimes.columns)
print(regimes.head())

# 필요한 컬럼:
# - date (날짜)
# - regime_id (0~18)
# - headline (원본 헤드라인, 선택적)
# - sp500, vix 등 (시장 지표)
```

### Step 3: 클러스터 매핑 확인
```python
# 19개 클러스터 이름 정의
REGIME_NAMES = {
    0: "확장",
    1: "수축",
    2: "전환",
    # ... 사용자에게 물어보기
}
```

---

## 📋 Phase 2: Neo4j 초기 설정

### Step 1: Docker로 Neo4j 설치
```bash
docker run -d \
  --name neo4j-economy \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password123 \
  -e NEO4J_PLUGINS='["apoc", "graph-data-science"]' \
  neo4j:5.15
```

### Step 2: Constraints & Indexes
```cypher
// Constraints
CREATE CONSTRAINT regime_id IF NOT EXISTS FOR (r:Regime) REQUIRE r.id IS UNIQUE;
CREATE CONSTRAINT state_id IF NOT EXISTS FOR (s:MarketState) REQUIRE s.state_id IS UNIQUE;
CREATE CONSTRAINT sector_name IF NOT EXISTS FOR (s:Sector) REQUIRE s.name IS UNIQUE;

// Indexes
CREATE INDEX state_date IF NOT EXISTS FOR (s:MarketState) ON (s.date);
CREATE INDEX state_regime IF NOT EXISTS FOR (s:MarketState) ON (s.regime_id);
```

### Step 3: 핵심 데이터 100개 임포트 (검증용)
```python
from neo4j import GraphDatabase

def import_sample_regimes(driver, regimes_df):
    """
    2만 레짐 중 100개만 먼저 임포트
    """
    with driver.session() as session:
        for _, row in regimes_df.iterrows():
            session.run("""
                MERGE (r:Regime {id: $regime_id})
                SET r.name = $name,
                    r.occurrence_count = 0

                CREATE (s:MarketState {
                    state_id: $state_id,
                    date: date($date),
                    regime_id: $regime_id,
                    sp500: $sp500,
                    vix: $vix
                })

                CREATE (s)-[:IN_REGIME]->(r)
            """,
                state_id=row['date'],
                date=row['date'],
                regime_id=row['regime_id'],
                name=REGIME_NAMES.get(row['regime_id'], f"Regime {row['regime_id']}"),
                sp500=row.get('sp500', 0),
                vix=row.get('vix', 0)
            )
```

---

## 📋 Phase 3: 핵심 쿼리 작성 (Graph Viewer)

### Query 1: 레짐 전환 네트워크
```cypher
// 19개 레짐이 어떻게 전환되는가?
MATCH (s1:MarketState)-[:IN_REGIME]->(r1:Regime)
MATCH (s2:MarketState)-[:IN_REGIME]->(r2:Regime)
WHERE s2.date = s1.date + duration({days: 1})  // 다음날

WITH r1, r2, count(*) as transition_count,
     avg(duration.between(s1.date, s2.date).days) as avg_days

MERGE (r1)-[t:TRANSITIONS_TO]->(r2)
SET t.probability = transition_count * 1.0 / r1.occurrence_count,
    t.sample_size = transition_count,
    t.avg_duration = avg_days

RETURN r1.name, r2.name, t.probability
ORDER BY t.probability DESC
```

### Query 2: 현재와 유사한 과거 상황
```cypher
// Vector 없이 단순 지표 유사도
MATCH (current:MarketState {date: date('2025-01-15')})
MATCH (past:MarketState)
WHERE past.date < current.date
  AND abs(past.sp500 - current.sp500) < 100
  AND abs(past.vix - current.vix) < 5

WITH current, past,
     abs(past.sp500 - current.sp500) +
     abs(past.vix - current.vix) * 10 as distance

ORDER BY distance ASC
LIMIT 10

MATCH (past)-[:IN_REGIME]->(regime:Regime)

RETURN past.date as 유사날짜,
       regime.name as 당시레짐,
       past.sp500, past.vix,
       distance
```

### Query 3: 섹터 상성 (수동 Input)
```cypher
// 사용자가 직접 입력:
// "확장 레짐에서 기술주가 평균 +5% alpha"

MATCH (sector:Sector {name: "기술주"})
MATCH (regime:Regime {name: "확장"})

MERGE (sector)-[p:OUTPERFORMS_IN]->(regime)
SET p.avg_alpha = 5.0,
    p.win_rate = 0.68,
    p.sample_size = 120,
    p.source = "manual_input"
```

---

## 📋 Phase 4: 점진적 확장

### 확장 우선순위
1. ✅ **100개 샘플 검증** (Phase 2-3 완료 후)
2. ✅ **2만 레짐 전체 임포트**
3. ✅ **레짐 전환 관계 자동 생성** (Query 1)
4. ⏳ **섹터 상성 수동 Input** (10개만)
5. ⏳ **Vector Search** (유사 상황 검색 고도화)
6. ⏳ **이벤트 임베딩** (핵심 헤드라인만)

---

## ⚠️ 중요: 하지 말아야 할 것

### 1. 자동 분류에 급하게 뛰어들지 말것
```python
# ✗ 나쁜 예
def auto_classify_regime(market_data):
    # 블랙박스 ML 모델
    return regime_id

# ✓ 좋은 예
# 2만 레짐은 이미 분류되어 있음 → 그냥 사용
# 새 데이터는 유사도 검색으로 매칭
```

### 2. 300만 헤드라인 전부 임베딩 ✗
- 비용: 300만 * $0.0001 = $300
- 필요성: 2만 레짐으로 이미 압축됨
- 대안: 핵심 이벤트 1000개만 선별

### 3. 완벽한 Schema 기대 ✗
- NBA도 2번 리팩토링함
- 처음엔 최소 노드/관계만
- 사용하면서 확장

### 4. 시간 추정 ✗
- "이건 2주 걸립니다" 같은 말 하지 말것
- 구체적 단계만 제시
- 사용자가 속도 결정

---

## 🎯 첫 세션 목표 (구체적)

### 새 Claude Code에게 요청할 것:

```
1. 데이터 파악
   - 2만 레짐 파일 읽기
   - 구조 확인 (columns, data types)
   - 19개 클러스터 분포 확인

2. Neo4j 설정
   - Docker 실행
   - Constraints 생성
   - 100개 샘플 임포트

3. 첫 쿼리 실행
   - 레짐별 발생 횟수
   - 전환 패턴 (간단한 버전)
   - 시각화 (Cypher 결과)

4. 검증
   - 데이터 정합성 체크
   - 관계가 제대로 생성되었나
   - 쿼리 속도 측정
```

---

## 📚 참고: NBA 프로젝트 구조

```
state_graph/
├── docs/
│   ├── NEO4J_SCHEMA_V2.1_FINAL.cypher
│   ├── PHASE3_SYSTEM_SUMMARY.md
│   └── CORE_GAMES_TAGGING_SUMMARY.md
│
├── tactic_extraction_llm.py       # 전술 추출 (경제: 레짐 분류)
├── sparsity_handler.py             # 희소성 처리
├── quality_monitor.py              # 품질 관리
├── tag_core_games.py               # 수동 태깅
│
├── raw/                            # 원본 데이터
├── snapshots/                      # State Snapshots
└── tactics_seed.json               # 시드 데이터
```

**경제레짐 프로젝트도 비슷하게**:
```
economic_regime/
├── docs/
│   └── NEO4J_SCHEMA_V1.cypher
│
├── regime_analysis.py              # 레짐 분석
├── sector_performance.py           # 섹터 상성
├── transition_probability.py       # 전환 확률
│
├── data/
│   ├── regimes_20k.csv             # 2만 레짐
│   ├── clusters_19.json            # 19개 클러스터 정의
│   └── market_indicators.csv       # 시장 지표
│
└── seed_data.json                  # 수동 입력 (섹터 상성 등)
```

---

## 🚀 시작 명령어 (새 Claude Code에게)

```
"NBA State Graph 프로젝트 경험을 바탕으로 경제레짐 분석 시스템을 구축하려고 합니다.

현재 상황:
- 300만 경제뉴스 헤드라인 → 2만 레짐 → 19개 클러스터 데이터 보유
- Neo4j State Graph로 레짐 전환, 섹터 상성 분석 목표

첫 단계:
1. 2만 레짐 데이터 구조 파악
2. Neo4j 초기 설정 (Docker)
3. 100개 샘플로 Schema 검증

지침서를 읽어주세요: ECONOMIC_REGIME_PROJECT_BRIEF.md

데이터 파일 위치를 알려주시면 시작하겠습니다."
```

---

## 📞 질문 리스트 (새 Claude에게 물어볼 것)

1. **데이터 위치**: 2만 레짐 파일은 어디에 있나요? (경로)
2. **파일 포맷**: CSV? JSON? Parquet?
3. **필수 컬럼**: date, regime_id 외에 뭐가 있나요?
4. **19개 클러스터**: 각 클러스터 이름이 정의되어 있나요?
5. **시장 지표**: S&P500, VIX, 금리 데이터도 같이 있나요?
6. **섹터 데이터**: 섹터별 수익률 데이터가 있나요?

---

## ✅ 성공 기준

### Phase 1 완료 기준
- [ ] 2만 레짐 데이터 로드 성공
- [ ] 19개 클러스터 분포 확인
- [ ] Neo4j에 100개 샘플 임포트
- [ ] 첫 쿼리 실행 성공

### Phase 2 완료 기준
- [ ] 2만 레짐 전체 임포트
- [ ] 레짐 전환 관계 자동 생성
- [ ] 유사 상황 검색 쿼리 작동

### Phase 3 완료 기준
- [ ] 섹터 상성 데이터 10개 입력
- [ ] Graph Viewer 시각화
- [ ] 실전 쿼리 5개 작성

---

**Made with ❤️ by NBA State Graph Team**
*"정량은 What, 전술은 How, Graph는 Why"*

**경제레짐에 적용하면**:
*"지표는 What, 레짐은 How, Graph는 Why"* 🚀
