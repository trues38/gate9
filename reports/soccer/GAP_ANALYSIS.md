# Soccer vs NBA 시스템 갭 분석

**작성일**: 2025-12-30 23:59 KST
**결론**: ❌ **축구는 아직 RAG 리포트 시스템이 없음**

---

## 🔍 현실 체크

### 현재 Soccer 시스템의 한계

**있는 것**:
- ✅ xG 통계 데이터 (3,504 경기)
- ✅ 간단한 수치 요약 (Crystal Palace -31골 등)
- ✅ Neo4j 기본 구조 (팀, 심판, 전술)
- ✅ V5 백테스트 ROI 검증

**없는 것**:
- ❌ Graph RAG 쿼리
- ❌ AI Council (5명 전문가 분석)
- ❌ 컨텍스트 기반 서술형 리포트
- ❌ 실시간 부상/라인업 수집
- ❌ 감독 전술 분석
- ❌ 심판-팀 상성 분석
- ❌ 자동 리포트 생성 파이프라인

---

## 📊 NBA vs Soccer 비교

### NBA 리포트 (완성)

```markdown
# Boston Celtics at Utah Jazz - Premium Analysis

## Executive Summary
The Celtics enter as 9.5-point favorites...

## Regime Analysis (AI Agent 1)
Boston operates in "Pace-Push Regime" with 102.3 possessions...
Recent 5-game stretch shows IMPROVING trend...

## Injury Impact (AI Agent 2)
Utah missing Lauri Markkanen (OUT - hamstring)...
Historical data: Jazz -8.2 pts without Markkanen...

## Referee Analysis (AI Agent 3)
Scott Foster officiating (14-year veteran)...
Boston's record with Foster: 12-3 (80% win rate)...

## Odds Movement (AI Agent 4)
Line opened -8.5, moved to -9.5...
Sharp money on Celtics (72% of handle)...

## Final Synthesis (AI Agent 5)
RECOMMENDATION: Celtics -9.5 (3u)
Confidence: 82%
Expected ROI: +14.2%
```

**특징**:
- Graph RAG로 컨텍스트 추출
- 5명의 전문가가 각자 영역 분석
- 서술형 문장 (LLM 생성)
- 신뢰도 및 예상 ROI 제시

---

### Soccer 리포트 (현재)

```markdown
# xG Betting Analysis - EPL

Top Value Bets:
- Crystal Palace: -31.15 xG diff 🔥
- Liverpool: -19.31 xG diff 🔥

Strongest Attack:
- Liverpool: 4.16 xG per game
```

**특징**:
- 단순 통계 나열
- 해석 없음
- AI 분석 없음
- "왜"에 대한 답 없음

---

## 🏗️ 필요한 작업 (NBA 수준 달성)

### Phase 1: Graph RAG 구축 (2-3일)

#### 1.1 Neo4j 데이터 완성
```cypher
// 현재: Team, Referee, Tactic만
// 필요: Match, Manager, Player, Injury

// Match 노드 (3,504개)
LOAD CSV FROM 'matches.csv' AS row
CREATE (m:Match {
  match_id: row.match_id,
  date: row.date,
  home_team: row.home_team,
  away_team: row.away_team,
  home_xG: row.home_xG,
  away_xG: row.away_xG,
  result: row.result
})

// Manager 노드
CREATE (m:Manager {
  manager_id: 'pep_guardiola',
  name: 'Pep Guardiola',
  team: 'Man City',
  preferred_formation: '4-3-3',
  style: 'Possession-based'
})

// Injury 노드
CREATE (i:Injury {
  player: 'Erling Haaland',
  team: 'Man City',
  status: 'OUT',
  impact: 'HIGH'
})
```

**소요 시간**: 1일
**담당**: Python 스크립트 작성 + 실행

---

#### 1.2 Cypher 쿼리 템플릿 작성
```cypher
// Liverpool vs Arsenal 컨텍스트 추출

// 1. 최근 폼
MATCH (t:Team {name: 'Liverpool'})-[:PLAYED_IN]->(m:Match)
WHERE m.date >= date() - duration({days: 30})
RETURN AVG(m.xG) as recent_form,
       COUNT(CASE WHEN m.result = 'W' THEN 1 END) as wins

// 2. Head-to-Head
MATCH (t1:Team {name: 'Liverpool'})-[:PLAYED_HOME]->(m:Match)
      <-[:PLAYED_AWAY]-(t2:Team {name: 'Arsenal'})
RETURN m.date, m.home_xG, m.away_xG, m.result
ORDER BY m.date DESC LIMIT 5

// 3. 감독 전술
MATCH (t:Team {name: 'Liverpool'})<-[:MANAGES]-(m:Manager)
MATCH (m)-[:PREFERS]->(tac:Tactic)
RETURN m.name, tac.name, m.preferred_formation

// 4. 심판 영향
MATCH (r:Referee {name: 'Michael Oliver'})-[:OFFICIATED]->(m:Match)
      <-[:PLAYED_IN]-(t:Team {name: 'Liverpool'})
RETURN AVG(m.cards) as avg_cards,
       AVG(m.fouls) as avg_fouls
```

**소요 시간**: 4시간
**결과**: `graph_queries.py` (쿼리 모음)

---

### Phase 2: AI Council 구축 (2-3일)

#### 2.1 5명의 전문가 정의

**Agent 1: Tactical Analyst**
```python
PROMPT_TACTICAL = """
You are a tactical analyst for European football.
Analyze the following match context:

Teams: {home_team} vs {away_team}
Recent form: {home_form} vs {away_form}
Managers: {home_manager} ({home_formation}) vs {away_manager} ({away_formation})

Provide tactical analysis:
1. Formation matchup (4-3-3 vs 4-4-2)
2. Key battles (midfield dominance)
3. Expected game state
"""
```

**Agent 2: xG Specialist**
```python
PROMPT_XG = """
You are an Expected Goals (xG) specialist.

Data:
- {home_team} recent xG: {home_xG_avg}
- {away_team} recent xG: {away_xG_avg}
- Historical matchup xG: {h2h_xG}

Analyze:
1. xG overperformance/underperformance
2. Regression potential
3. Goal expectation
"""
```

**Agent 3: Injury & Lineup Scout**
```python
PROMPT_INJURY = """
You are a team news and injury analyst.

Injuries:
{injuries_list}

Squad depth:
{squad_rotation}

Assess impact on match outcome.
"""
```

**Agent 4: Referee Analyst**
```python
PROMPT_REFEREE = """
You are a referee analysis specialist.

Referee: {referee_name}
Style: {strictness_level}
Team records with this ref:
- {home_team}: {home_record}
- {away_team}: {away_record}

Analyze potential impact.
"""
```

**Agent 5: Betting Synthesizer**
```python
PROMPT_SYNTHESIS = """
You are a betting recommendations synthesizer.

Agent 1 (Tactical): {tactical_analysis}
Agent 2 (xG): {xg_analysis}
Agent 3 (Injury): {injury_analysis}
Agent 4 (Referee): {referee_analysis}

Current odds:
- Home win: {home_odds}
- Draw: {draw_odds}
- Away win: {away_odds}

Provide:
1. Top 3 betting recommendations
2. Confidence level (0-100%)
3. Expected ROI
"""
```

**소요 시간**: 2일 (NBA 코드 참고)
**결과**: `soccer_ai_council.py`

---

#### 2.2 리포트 생성기
```python
# soccer_report_generator.py

def generate_premium_report(match_id):
    # 1. Graph RAG - 컨텍스트 추출
    context = extract_graph_context(match_id)

    # 2. AI Council - 5명 분석
    tactical = agent_tactical(context)
    xg_analysis = agent_xg(context)
    injury = agent_injury(context)
    referee = agent_referee(context)
    synthesis = agent_synthesizer([tactical, xg_analysis, injury, referee])

    # 3. Markdown 리포트 생성
    report = f"""
# {context['home_team']} vs {context['away_team']}
**Date**: {context['date']}
**Competition**: {context['league']}

## Executive Summary
{synthesis['summary']}

## Tactical Analysis
{tactical['analysis']}

## xG Analysis
{xg_analysis['analysis']}

## Injury Impact
{injury['analysis']}

## Referee Analysis
{referee['analysis']}

## Betting Recommendations
{synthesis['recommendations']}

**Confidence**: {synthesis['confidence']}%
**Expected ROI**: {synthesis['roi']}%
"""

    return report
```

**소요 시간**: 1일
**결과**: NBA 스타일 프리미엄 리포트

---

### Phase 3: 자동화 (1일)

#### 3.1 일일 파이프라인
```bash
#!/bin/bash
# /opt/g9/domains/soccer/daily_report.sh

# 1. 내일 경기 리스트 가져오기
tomorrow_matches=$(python3 get_tomorrow_matches.py)

# 2. 각 경기에 대해 리포트 생성
for match_id in $tomorrow_matches; do
  python3 soccer_report_generator.py --match_id=$match_id
done

# 3. Slack/Telegram 알림
python3 send_reports.py
```

#### 3.2 크론 설정
```bash
# 매일 20:00 KST - 다음날 경기 리포트 생성
0 11 * * * cd /opt/g9/domains/soccer && ./daily_report.sh
```

---

## 📊 완성 후 모습

### 완성된 Soccer 리포트 예시

```markdown
# Liverpool vs Arsenal - Premium Betting Analysis
**Date**: 2025-01-05 15:00 GMT
**Venue**: Anfield
**Competition**: Premier League

---

## Executive Summary

Liverpool enters as strong favorites (-180) against Arsenal in
this top-of-the-table clash. Our Graph RAG analysis reveals
Liverpool's attack (4.16 xG/game) is significantly underperforming
(-19 goals vs xG), suggesting imminent regression. Arsenal's
recent form shows DECLINING trajectory (2.16 xG down from 2.8).

**KEY EDGE**: Liverpool at home with Michael Oliver (12-3 record)
officiating. Arsenal missing Saka (OUT) reduces their xG by 0.8.

**RECOMMENDATION**: Liverpool -1.5 AH @ 2.05 (3 units)
**CONFIDENCE**: 78%
**EXPECTED ROI**: +12.4%

---

## Tactical Analysis (Agent 1)

### Formation Matchup
Liverpool's 4-3-3 vs Arsenal's 4-4-2 creates a midfield overload
for the home side. Klopp's gegenpressing regime thrives against
Arteta's build-up play, historically forcing 3.2 turnovers per game.

### Key Battles
- Salah (IMPROVING, 1.8 xG/90) vs Zinchenko (DECLINING, 1.2 xGA/90)
- Liverpool's press (18.2 PPDA) vs Arsenal's build-up (82% pass accuracy)

### Expected Game State
Liverpool to dominate possession (58-42) and create 2.8x more
high-quality chances (xG 2.4 vs 0.9).

---

## xG Analysis (Agent 2)

### Regression Potential: HIGH

Liverpool has underperformed xG by 19.3 goals this season -
the 2nd highest in EPL. Their recent 5-game stretch shows:
- Actual goals: 8
- Expected goals (xG): 15.4
- **Regression due**: +7.4 goals

Arsenal shows opposite pattern (slight overperformance +2.1 goals).

### Historical H2H xG
Last 3 meetings:
1. Dec 2023: Liverpool 5.66 xG vs Arsenal 1.73 xG (1-1 draw)
2. Oct 2024: Arsenal 1.09 xG vs Liverpool 1.35 xG (2-2 draw)

**Pattern**: Liverpool xG dominance not converting to wins.
**Today**: High probability of conversion given regression.

---

## Injury & Lineup Impact (Agent 3)

### Arsenal Absences (Critical)
- **Bukayo Saka (OUT)** - hamstring
  * Impact: -0.8 xG per game
  * Replacement: Nelson (-0.4 xG vs Saka)

### Liverpool Injury Report
- All starters AVAILABLE
- Núñez (FIT) returns from knock

**Net Impact**: Liverpool +0.8 xG advantage from lineup quality.

---

## Referee Analysis (Agent 4)

### Michael Oliver
- Experience: 16 seasons
- Style: Lenient (3.2 cards/game, 12th percentile)
- Home advantage: +0.3 cards to away team

### Team Records with Oliver
- Liverpool: 12-3-2 (71% win rate, +0.4 xG boost)
- Arsenal: 8-7-3 (44% win rate, -0.2 xG)

**Significance**: Oliver's lenient style favors Liverpool's
physical pressing. Arsenal's build-up disrupted by allowed contact.

---

## Betting Recommendations (Agent 5)

### Primary Bet: Liverpool -1.5 AH @ 2.05
**Stake**: 3 units
**Reasoning**:
1. xG regression (+7.4 goals due)
2. Arsenal missing Saka (-0.8 xG)
3. Referee Oliver (12-3 record)
4. Home dominance (Anfield: 2.8 xG avg)

**Confidence**: 78%
**Expected ROI**: +12.4%

### Secondary Bet: Over 2.5 Goals @ 1.85
**Stake**: 2 units
**Reasoning**:
1. Combined xG: 3.3 (Liverpool 2.4 + Arsenal 0.9)
2. H2H history: 4/5 games over 2.5
3. Both teams attack-minded

**Confidence**: 65%
**Expected ROI**: +8.2%

### Avoid: Arsenal +1.5 AH
**Reasoning**:
1. Missing key creator (Saka)
2. Poor recent form (DECLINING)
3. Historical xG disadvantage at Anfield

---

## Risk Factors

⚠️ **Weather**: Rain forecasted (reduces passing accuracy)
⚠️ **Variance**: xG regression not guaranteed in single match
⚠️ **Motivation**: Arsenal fighting for title (extra effort)

---

## Model Output

**Predicted Score**: Liverpool 2.4 - Arsenal 1.1 (xG-based)
**Most Likely Result**: Liverpool 2-1 (28% probability)
**Win Probabilities**:
- Liverpool: 62%
- Draw: 23%
- Arsenal: 15%

---

**Generated**: 2025-01-04 20:00 UTC
**Model**: Soccer Graph RAG v1.0 + AI Council
**Validation**: V5 Backtest ROI +10.5% (511 games)
```

---

## ⏱️ 작업 시간 예상

| Phase | 작업 | 소요 시간 |
|-------|------|----------|
| **Phase 1** | Graph RAG 구축 | 2-3일 |
| - Neo4j 데이터 로드 | | 1일 |
| - Cypher 쿼리 작성 | | 4시간 |
| - Python 통합 | | 4시간 |
| **Phase 2** | AI Council 구축 | 2-3일 |
| - 5개 Agent 프롬프트 | | 1일 |
| - 리포트 생성기 | | 1일 |
| - 테스트 및 조정 | | 4시간 |
| **Phase 3** | 자동화 | 1일 |
| - 일일 파이프라인 | | 4시간 |
| - 크론 설정 | | 1시간 |
| - VPS 배포 | | 3시간 |
| **Total** | | **5-7일** |

---

## 🎯 우선순위 결정 필요

### 옵션 A: NBA 수준 완성 (5-7일)
- Graph RAG + AI Council
- 프리미엄 리포트
- 완전 자동화

### 옵션 B: 현재 V5로 시작 (즉시)
- Ligue1 ROI +10.5% 활용
- 단순 수동 베팅
- 리포트 나중에

### 옵션 C: 하이브리드 (2-3일)
- V5 베팅 시작
- Graph RAG만 먼저 구축
- AI Council은 나중에

---

## 결론

**현실**: Soccer는 xG 통계만 있고 RAG 리포트 없음
**목표**: NBA 수준 Graph RAG + AI Council
**격차**: 5-7일 작업 필요

**추천**: 옵션 B (V5로 먼저 시작) + 병렬로 Phase 1 진행

---

**작성**: 2025-12-30 23:59 KST
**다음**: 사용자 방향 결정 대기
