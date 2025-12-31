# Hybrid SQLite + Neo4J Architecture

## 시스템 개요

축구 베팅 분석을 위한 하이브리드 데이터베이스 아키텍처:
- **SQLite**: 정량 데이터 (xG, 점수, 통계)
- **Neo4J**: 그래프 패턴 (관계, 시퀀스, 컨텍스트)

---

## 아키텍처 다이어그램

```
┌─────────────────────────────────────────────────────────────┐
│                  데이터 수집 레이어                          │
├─────────────────────────────────────────────────────────────┤
│  Understat Selenium Collector (주 1회 크론)                  │
│  → xG, 점수, 팀, 날짜 등 정량 데이터                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                 SQLite (정량 데이터)                         │
├─────────────────────────────────────────────────────────────┤
│  Tables:                                                    │
│  - matches (경기 정보)                                       │
│  - match_stats (xG 통계)                                    │
│  - teams (팀 정보)                                          │
│                                                              │
│  특징:                                                       │
│  - 빠른 집계 쿼리                                            │
│  - 수치 분석 (평균, 합계, 차이)                              │
│  - 시간대별 필터링                                           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              Neo4J (그래프 패턴)                             │
├─────────────────────────────────────────────────────────────┤
│  Nodes:                                                     │
│  - Team (팀)                                                │
│  - Match (경기)                                             │
│  - League (리그)                                            │
│  - Season (시즌)                                            │
│                                                              │
│  Relationships:                                             │
│  - (Team)-[:PLAYED_HOME]->(Match)                          │
│  - (Team)-[:PLAYED_AWAY]->(Match)                          │
│  - (Match)-[:FOLLOWED_BY]->(Match)                         │
│  - (Match)-[:IN_LEAGUE]->(League)                          │
│                                                              │
│  특징:                                                       │
│  - 관계 패턴 분석                                            │
│  - 시퀀스 추적 (연속 경기)                                   │
│  - 컨텍스트 인식 (상대전적, 폼 추세)                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│            Hybrid Analysis Engine                           │
├─────────────────────────────────────────────────────────────┤
│  1. SQLite에서 정량 데이터 추출                              │
│     - xG 통계, 점수, 팀 성적                                │
│                                                              │
│  2. Neo4J에서 그래프 패턴 추출                               │
│     - 최근 폼 시퀀스 (last 5 matches)                        │
│     - 상대전적 (head-to-head)                               │
│     - 트렌드 분석 (improving/declining)                     │
│                                                              │
│  3. 하이브리드 인사이트 생성                                 │
│     - 공격력 vs 수비력 매칭                                  │
│     - 폼 + 역사적 데이터                                     │
│     - 다중 요인 신뢰도 점수                                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                베팅 리포트 출력                              │
├─────────────────────────────────────────────────────────────┤
│  - Markdown 리포트                                          │
│  - JSON 데이터                                              │
│  - 베팅 추천 + 신뢰도                                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 데이터 흐름

### 1. 수집 단계 (주 1회)

```bash
# 크론 실행
0 0 * * 0 python3 scripts/understat_selenium_collector.py
```

**수집 데이터:**
- 날짜, 리그, 팀명
- 홈/원정 점수
- 홈/원정 xG, xGA

**저장 위치:** SQLite (`data/soccer.db`)

---

### 2. 검증 단계 (수동)

```bash
python3 analysis/validate_xg_data.py
```

**검증 항목:**
- 데이터 존재 확인
- 커버리지 확인 (리그별)
- 품질 확인 (이상치, NULL)

---

### 3. 하이브리드 분석 단계

```bash
python3 analysis/hybrid_report_generator.py
```

**프로세스:**

#### 3.1 SQLite 쿼리 (정량)
```sql
SELECT
    m.match_id, m.date, m.home_team_id, m.away_team_id,
    m.home_score, m.away_score,
    ms_h.xg as home_xg, ms_a.xg as away_xg
FROM matches m
JOIN match_stats ms ON m.match_id = ms.match_id
WHERE m.league = 'EPL'
AND ms.xg IS NOT NULL
```

→ **결과:** 매치별 xG 통계

#### 3.2 그래프 패턴 분석 (Neo4J)
```cypher
// 최근 폼 (last 5 matches)
MATCH (t:Team)-[p:PLAYED_HOME|PLAYED_AWAY]->(m:Match)
WHERE m.date >= date() - duration({days: 30})
WITH t, AVG(p.xg) as recent_xg, COUNT(m) as matches
WHERE matches >= 5
RETURN t.name, recent_xg
ORDER BY recent_xg DESC
```

→ **결과:** 팀별 최근 xG 평균

```cypher
// 상대전적 (Head-to-Head)
MATCH (t1:Team)-[:PLAYED_HOME]->(m:Match)<-[:PLAYED_AWAY]-(t2:Team)
WHERE t1.team_id = 'liverpool' AND t2.team_id = 'arsenal'
RETURN m.date, m.home_score, m.away_score, m.home_xg, m.away_xg
ORDER BY m.date DESC
```

→ **결과:** 두 팀의 최근 대결 기록

#### 3.3 하이브리드 인사이트

**데이터 결합:**
- SQLite: Liverpool 최근 5경기 평균 xG = 3.29
- Neo4J: Liverpool 폼 트렌드 = IMPROVING
- Neo4J: Liverpool vs Arsenal 상대전적 = 2경기 (무승부)

**인사이트 생성:**
```python
# 공격력 vs 수비력 매칭
team1_attack = 3.29  # Liverpool xG
team2_defense = 0.69  # Arsenal xGA

if team1_attack > 1.8 and team2_defense < 1.0:
    prediction = "Liverpool likely to score"
    confidence = "HIGH"
```

---

## 하이브리드 분석의 장점

### SQLite만 사용할 때

```sql
-- 단순 평균만 가능
SELECT AVG(xg) FROM match_stats
WHERE team_id = 'liverpool'
```

**한계:**
- 순서 무시 (최근 vs 과거 구분 안 됨)
- 관계 무시 (상대팀, 연속성)
- 컨텍스트 없음

### Neo4J 추가 시

```cypher
// 시퀀스 인식
MATCH (t:Team)-[:PLAYED_HOME|PLAYED_AWAY]->(m1:Match)
      -[:FOLLOWED_BY]->(m2:Match)
      <-[:PLAYED_HOME|PLAYED_AWAY]-(t)
RETURN t.name, AVG(m2.xg) as xg_after_previous_match
```

**장점:**
- ✅ 시간 순서 인식
- ✅ 경기 간 관계
- ✅ 연속 경기 영향
- ✅ 상대전적 컨텍스트

---

## 실제 예제: Liverpool vs Arsenal

### SQLite 데이터

```
Liverpool (최근 5경기):
- 평균 xG: 3.29
- 평균 득점: 2.8
- 평균 xGA: 1.3

Arsenal (최근 5경기):
- 평균 xG: 2.16
- 평균 득점: 2.2
- 평균 xGA: 0.69
```

### Neo4J 그래프 패턴

```
Liverpool 폼 시퀀스:
Match1 → Match2 → Match3 → Match4 → Match5
xG: 2.1 → 3.5 → 3.8 → 4.2 → 2.8
→ Trend: IMPROVING (초반 2.1 → 후반 4.2)

Head-to-Head:
2023-12-23: Liverpool 1-1 Arsenal (xG: 5.66-1.73)
2024-10-27: Arsenal 2-2 Liverpool (xG: 1.09-1.35)
→ Pattern: 무승부 경향, Liverpool xG 우세
```

### 하이브리드 인사이트

```markdown
🎯 Betting Predictions

⚡ Match Result (MEDIUM)
- Liverpool favored based on xG differential (1.13)
- Recent trend: IMPROVING vs DECLINING
- Historical: Liverpool xG dominant

⚡ Over 2.5 Goals (MEDIUM)
- Combined xG: 5.46
- Both teams scoring record in H2H
```

**왜 하이브리드가 더 나은가?**
1. SQLite: 3.29 vs 2.16 (정량 비교)
2. Neo4J: IMPROVING vs DECLINING (트렌드)
3. Neo4J: 상대전적 무승부 패턴
4. **결합: Liverpool 우세하지만 무승부 가능성, 다득점 예상**

---

## 구현 파일

### 코어 파일

1. **neo4j_schema.cypher**
   - Neo4J 스키마 정의
   - 제약조건, 인덱스
   - 샘플 Cypher 쿼리

2. **hybrid_report_generator.py**
   - SQLite 데이터 추출
   - 그래프 패턴 시뮬레이션
   - 하이브리드 인사이트 생성
   - Markdown 리포트 출력

3. **validate_xg_data.py**
   - 데이터 품질 검증
   - 리포트 생성 전 필수

### 실행 방법

```bash
# VPS에서
ssh root@141.164.35.214
cd /opt/g9/domains/soccer

# 1. 데이터 검증
python3 analysis/validate_xg_data.py

# 2. 하이브리드 리포트 생성
python3 analysis/hybrid_report_generator.py

# 3. 리포트 확인
cat analysis/reports/hybrid_report_*.md
```

---

## 샘플 리포트 구조

```markdown
# Hybrid SQLite + Neo4J Betting Analysis

## Data Sources
- SQLite (Quantitative): xG, scores, stats
- Neo4J (Graph Patterns): sequences, relationships

## Liverpool Vs Arsenal

### Liverpool
- Recent xG: 3.29 (avg last 5 matches)
- Trend: IMPROVING

### Arsenal
- Recent xG: 2.16 (avg last 5 matches)
- Trend: DECLINING

### Head-to-Head (Graph Pattern)
- 2023-12-23: Liverpool 1-1 Arsenal (xG: 5.66-1.73)
- 2024-10-27: Arsenal 2-2 Liverpool (xG: 1.09-1.35)

### 🎯 Betting Predictions
⚡ Match Result (MEDIUM)
- Liverpool favored based on xG differential

⚡ Over 2.5 Goals (MEDIUM)
- Combined xG: 5.46
```

---

## 향후 확장 계획

### Phase 1: 실제 Neo4J 연동
```python
from neo4j import GraphDatabase

driver = GraphDatabase.driver("bolt://localhost:7687")

def run_cypher_query(query):
    with driver.session() as session:
        result = session.run(query)
        return result.data()
```

### Phase 2: 고급 그래프 패턴

```cypher
// 연속 홈/원정 경기 패턴
MATCH (t:Team)-[:PLAYED_HOME]->(m1:Match)-[:FOLLOWED_BY]->(m2:Match)
      <-[:PLAYED_HOME]-(t)
WHERE m1.days_gap <= 3
RETURN t.name, AVG(m2.xg) as xg_back_to_back_home

// 특정 상대 이후 폼
MATCH (t:Team)-[:PLAYED_AWAY]->(m1:Match)<-[:PLAYED_HOME]-(strong:Team)
      (t)-[:PLAYED_HOME]->(m2:Match)
WHERE strong.team_id IN ['man_city', 'liverpool']
AND m1.date < m2.date
RETURN t.name, AVG(m2.xg) as xg_after_strong_opponent
```

### Phase 3: 머신러닝 통합
- SQLite 정량 데이터 → Feature Engineering
- Neo4J 그래프 패턴 → Graph Embeddings
- 결합 → Gradient Boosting Model

---

## 결론

**현재 시스템:**
- ✅ SQLite에서 정량 데이터 수집 (자동화)
- ✅ 그래프 패턴 시뮬레이션 (Python)
- ✅ 하이브리드 인사이트 생성

**다음 단계:**
- 🔲 실제 Neo4J 데이터베이스 구축
- 🔲 실시간 Cypher 쿼리 실행
- 🔲 고급 그래프 알고리즘 (PageRank, Community Detection)
- 🔲 자동화된 베팅 추천 시스템

하이브리드 아키텍처는 **정량 데이터의 정확성**과 **그래프의 컨텍스트 인식**을 결합하여 더 나은 베팅 인사이트를 제공합니다.
