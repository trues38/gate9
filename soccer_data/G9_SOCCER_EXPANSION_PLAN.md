# ⚽ G9 Soccer 5대 리그 확장 계획

**날짜**: 2025-12-29
**목표**: NBA 시스템과 동일한 Graph RAG + Realtime Odds 엔진을 축구 5대 리그에 확장
**현재 상태**: 데이터 수집 완료, Graph DB 스키마 설계 완료

---

## 📊 현황 분석

### ✅ 수집 완료된 데이터

| 데이터 소스 | 리그 | 기간 | 상태 |
|-----------|------|------|------|
| **Understat** (xG) | EPL, La Liga, Bundesliga, Serie A, Ligue 1 | 2024 시즌 | ✅ 완료 |
| **Historical Odds** | 5대 리그 | 2024-25 시즌 (~380경기/리그) | ✅ 완료 |
| **Tactical RAG** | 전체 | 실시간 (Spielverlagerung) | ✅ 완료 |
| **Referee Stats** | 5대 리그 | 2024-25 시즌 | ✅ 완료 |

**총 데이터량**:
- EPL results: 10,641 lines (경기 상세 데이터)
- Odds CSV: ~380 경기 × 5개 리그 = 1,900 경기
- Referee Stats: 100+ 심판 분석
- Tactical Articles: 실시간 업데이트

---

## 🏗️ NBA vs Soccer 구조 매핑

### 1️⃣ Graph Schema 비교

| NBA | Soccer | 매핑 난이도 |
|-----|--------|-----------|
| `Player` | `Player` | ✅ 동일 |
| `Team` | `Team` (Club) | ✅ 동일 |
| `Game` | `Match` | ✅ 동일 |
| `Referee` | `Referee` | ✅ 동일 |
| `Coach` | `Manager` | ✅ 동일 |
| `Injury` | `Injury` | ✅ 동일 |
| `TeamState` | `TeamState` | ✅ 동일 |
| `PlayerState` | `PlayerState` | ✅ 동일 |
| - | `TacticalArchetype` | ⚠️ 새로운 개념 |

**핵심 차이점**:
- ✅ 구조는 거의 동일 (90% 재사용 가능)
- ⚠️ Soccer 전용: `TacticalArchetype` (Gegenpressing, Tiki-Taka, Low Block 등)
- ⚠️ Soccer 전용: Formation (4-3-3, 3-5-2 등)

### 2️⃣ 데이터 파이프라인 비교

| 단계 | NBA | Soccer | 구현 상태 |
|------|-----|--------|----------|
| **Raw Data** | ESPN API, NBA Stats | Understat API, Football-Data | ✅ 완료 |
| **Odds** | The Odds API | Football-Data CSV | ✅ 완료 |
| **News/Sentiment** | Twitter (Shams, Woj) | Tactical RAG (Spielverlagerung) | ✅ 완료 |
| **Graph Ingest** | Neo4j Cypher | Neo4j Cypher | 🔄 진행 필요 |
| **Realtime Updates** | N8N Workflow | N8N Workflow | 🔄 복제 필요 |
| **Report Generation** | 5-Person AI Council | 5-Person AI Council | 🔄 복제 필요 |

---

## 🚀 3단계 확장 계획

### **Phase 1: Graph DB 구축** (Claude 메인, 3일 목표)

**목표**: Soccer 데이터를 Neo4j Graph DB로 ingestion

#### 1.1 Neo4j 스키마 생성
```cypher
// Nodes
CREATE CONSTRAINT player_id IF NOT EXISTS FOR (p:SoccerPlayer) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT team_id IF NOT EXISTS FOR (t:SoccerTeam) REQUIRE t.id IS UNIQUE;
CREATE CONSTRAINT match_id IF NOT EXISTS FOR (m:SoccerMatch) REQUIRE m.id IS UNIQUE;
CREATE CONSTRAINT manager_id IF NOT EXISTS FOR (m:SoccerManager) REQUIRE m.id IS UNIQUE;
CREATE CONSTRAINT ref_id IF NOT EXISTS FOR (r:SoccerReferee) REQUIRE r.name IS UNIQUE;
CREATE CONSTRAINT tactic_id IF NOT EXISTS FOR (t:TacticalArchetype) REQUIRE t.name IS UNIQUE;

// Indexes
CREATE INDEX match_date IF NOT EXISTS FOR (m:SoccerMatch) ON (m.date);
CREATE INDEX player_name IF NOT EXISTS FOR (p:SoccerPlayer) ON (p.name);
```

#### 1.2 데이터 Ingestion 스크립트 작성
- `ingest_teams.py` - 5대 리그 20개 팀 × 5 = 100개 팀
- `ingest_players.py` - Understat 선수 데이터 (라인업 기반)
- `ingest_matches.py` - results.json → SoccerMatch 노드
- `ingest_odds.py` - historical_odds CSV → Odds relationship
- `ingest_referees.py` - referee_stats.json → SoccerReferee 노드
- `ingest_tactical_archetypes.py` - Tactical RAG → TacticalArchetype

**출력**: Neo4j에 ~50,000 노드 생성 예상
- 100 Teams
- 2,500 Players (평균 25명/팀)
- 1,900 Matches
- 100+ Referees
- 10+ TacticalArchetypes
- 45,000+ Relationships

---

### **Phase 2: Realtime Pipeline 복제** (Gemini 백업, 2일 목표)

**목표**: NBA N8N Workflow를 Soccer용으로 복제

#### 2.1 N8N Workflow 복제
- `n8n_soccer_realtime_workflow.json` 생성
- Trigger: 매일 09:00 KST (유럽 경기 후)
- Data Sources:
  * Understat API (최신 경기 결과)
  * Football-Data Odds (실시간 배당)
  * Tactical RAG (최신 기사)

#### 2.2 Metrics API 확장
- `/Users/js/g9/nba_data/odds_report_engine/monitoring/metrics_api.py` 수정
- Soccer 메트릭 추가:
  ```python
  SOCCER_MATCHES_COLLECTED = Gauge("soccer_matches_collected", "Soccer matches collected today")
  TACTICAL_ARTICLES_COLLECTED = Gauge("tactical_articles_collected", "Tactical articles ingested")
  SOCCER_ODDS_SNAPSHOTS = Counter("soccer_odds_snapshots_total", "Soccer odds snapshots", ["league"])
  ```

#### 2.3 Grafana 대시보드 추가
- `grafana_soccer_dashboard.json` 생성
- 패널:
  * EPL/La Liga/Bundesliga/Serie A/Ligue 1 수집 상태
  * Tactical RAG 기사 수
  * 심판 통계 업데이트
  * Neo4j 노드 증가 (Soccer 전용)

---

### **Phase 3: Report Engine 통합** (Claude 메인, 2일 목표)

**목표**: 5-Person AI Council을 Soccer 경기 분석에 적용

#### 3.1 Prompt Templates 작성
- `regime_analyst_soccer.txt` - 전술 레짐 분석 (4-3-3 vs 3-5-2 등)
- `odds_specialist_soccer.txt` - Asian Handicap, Over/Under 특화
- `news_analyst_soccer.txt` - Tactical RAG 기사 분석
- `scout_soccer.txt` - 부상/라인업 변화 추적
- `synthesizer_soccer.txt` - 최종 베팅 리포트

#### 3.2 Graph RAG Query 작성
```cypher
// Soccer 전용 쿼리 예시
MATCH (m:SoccerMatch {id: $match_id})<-[:PARTICIPATED_IN]-(home:SoccerTeam)
MATCH (m)<-[:PARTICIPATED_IN]-(away:SoccerTeam)
MATCH (home)-[:APPLIES]->(tactic_home:TacticalArchetype)
MATCH (away)-[:APPLIES]->(tactic_away:TacticalArchetype)
MATCH (home)-[:MANAGED_BY]->(manager_home:SoccerManager)
MATCH (away)-[:MANAGED_BY]->(manager_away:SoccerManager)
OPTIONAL MATCH (m)<-[:OFFICIATES]-(ref:SoccerReferee)
RETURN
  home.name AS home_team,
  away.name AS away_team,
  tactic_home.name AS home_tactics,
  tactic_away.name AS away_tactics,
  manager_home.preferred_formation AS home_formation,
  manager_away.preferred_formation AS away_formation,
  ref.strictness_index AS referee_strictness,
  m.home_xg AS home_xG,
  m.away_xg AS away_xG
```

#### 3.3 Report Generation 자동화
- `generate_soccer_report.py` 작성
- Input: `match_id` (예: EPL_2425_380)
- Output: `reports/soccer_EPL_ManCity_vs_Liverpool_20250115.md`

**Report 구조** (NBA와 동일):
1. **Regime Analysis** - 전술 레짐 (4-3-3 vs 4-4-2)
2. **Odds Movement** - Asian Handicap 변동
3. **Tactical News** - Spielverlagerung 기사 요약
4. **Injury/Lineup** - 스타팅 11 변화
5. **Final Synthesis** - 베팅 추천

---

## 👥 역할 분담: Claude vs Gemini

### **Claude (메인 책임자)** - 복잡한 Graph 로직 및 AI Council

| 작업 | 이유 | 예상 시간 |
|------|------|----------|
| Neo4j Schema 설계 | 복잡한 관계 설계 필요 | 4시간 |
| Graph Ingestion Scripts | Cypher 쿼리 최적화 | 1일 |
| Graph RAG Query 작성 | 컨텍스트 이해 필요 | 4시간 |
| AI Council Prompts | 전술 도메인 지식 필요 | 1일 |
| Report Generation | 통합 로직 복잡 | 8시간 |
| **Total** | | **3일** |

### **Gemini 3.0 Pro (백업)** - 데이터 파이프라인 및 자동화

| 작업 | 이유 | 예상 시간 |
|------|------|----------|
| N8N Workflow 복제 | 기존 패턴 복사 | 4시간 |
| Metrics API 확장 | 단순 코드 추가 | 2시간 |
| Grafana Dashboard | JSON 템플릿 수정 | 2시간 |
| 데이터 검증 스크립트 | 반복 작업 | 4시간 |
| 문서 작성 | 마크다운 생성 | 2시간 |
| **Total** | | **2일** |

---

## 📋 우선순위 및 타임라인

### **Week 1: Core Infrastructure** (12/29 - 1/4)

| 날짜 | Claude 작업 | Gemini 작업 | 마일스톤 |
|------|------------|-------------|----------|
| **Day 1** (12/29) | Neo4j Schema 생성 | N8N Workflow 복제 | ✅ Schema Ready |
| **Day 2** (12/30) | Teams + Players Ingestion | Metrics API 확장 | ✅ 100 Teams in Neo4j |
| **Day 3** (12/31) | Matches + Odds Ingestion | Grafana Dashboard | ✅ 1,900 Matches in Neo4j |
| **Day 4** (1/1) | Referees + Tactics Ingestion | 데이터 검증 | ✅ Graph 완성 |
| **Day 5** (1/2) | Graph RAG Query 작성 | Monitoring 대시보드 | ✅ Query 테스트 |
| **Day 6** (1/3) | AI Council Prompts | 문서 작성 | ✅ Prompts Ready |
| **Day 7** (1/4) | Report Generation 통합 | End-to-End 테스트 | ✅ **첫 Soccer Report** |

---

## 🎯 성공 기준

### **Phase 1 완료 기준**:
- ✅ Neo4j에 50,000+ 노드 존재
- ✅ 5대 리그 모든 팀/선수 매핑 완료
- ✅ Cypher 쿼리 응답 시간 < 500ms

### **Phase 2 완료 기준**:
- ✅ N8N Workflow 매일 09:00 자동 실행
- ✅ Grafana에서 Soccer 메트릭 표시
- ✅ Alertmanager에 Soccer 알림 규칙 추가

### **Phase 3 완료 기준**:
- ✅ 5-Person AI Council이 Soccer 경기 분석
- ✅ Graph RAG Query가 전술/라인업/Odds 통합
- ✅ 첫 Soccer Report 생성 (Man City vs Liverpool)

---

## ⚠️ 리스크 및 주의사항

### **1. 데이터 품질 리스크**

| 리스크 | 영향 | 완화 방안 |
|-------|------|----------|
| Understat API Rate Limit | 수집 실패 | 하루 50경기만 상세 조회 |
| Football-Data 인코딩 문제 | CSV 파싱 오류 | `encoding='unicode_escape'` 사용 |
| Tactical RAG 기사 부족 | News 분석 빈약 | RSS Feed 다변화 (The Athletic, FBref) |
| 심판 데이터 누락 | Referee 노드 부족 | Historical Odds CSV에서 추출 (완료) |

### **2. Graph DB 성능 리스크**

| 문제 | 영향 | 해결책 |
|------|------|--------|
| 50,000 노드 조회 느림 | Report 생성 지연 | Index 추가 (match_date, player_name) |
| Relationship 폭발 | 메모리 부족 | VPS 메모리 8GB로 업그레이드 권장 |
| Cypher Query 복잡도 | 타임아웃 | APOC 플러그인 사용 |

### **3. AI Council 적응 리스크**

| 문제 | 영향 | 해결책 |
|------|------|--------|
| 전술 용어 이해 부족 | 잘못된 분석 | Prompt에 전술 용어 사전 추가 |
| xG 해석 오류 | 잘못된 예측 | "xG > 2.0 = 공격 우세" 명시 |
| Asian Handicap 혼동 | 배당 오독 | AH 계산 예시 포함 |

---

## 🔧 기술 스택

### **기존 NBA 시스템 재사용**:
- ✅ Neo4j (Graph DB)
- ✅ N8N (Workflow Automation)
- ✅ Prometheus + Grafana (Monitoring)
- ✅ OpenRouter (AI Council)
- ✅ Python + Flask (Metrics API)

### **Soccer 전용 추가**:
- ✅ Understat Library (Python)
- ✅ Football-Data.co.uk (Historical Odds)
- ✅ Spielverlagerung RSS Feed (Tactical RAG)

---

## 📁 디렉토리 구조 (최종)

```
/Users/js/g9/
├── nba_data/                    # NBA 시스템 (기존)
│   ├── state_graph/
│   ├── odds_report_engine/
│   └── monitoring/
│
├── soccer_data/                 # Soccer 시스템 (확장)
│   ├── raw_data/
│   │   ├── understat/           # ✅ 완료
│   │   ├── historical_odds/     # ✅ 완료
│   │   └── tactical_rag/        # ✅ 완료
│   ├── processed/
│   │   └── referee_stats.json   # ✅ 완료
│   ├── schema/
│   │   └── soccer_graph_schema.md # ✅ 완료
│   ├── scrapers/                # ✅ 완료
│   ├── ingest/                  # 🔄 생성 필요 (Claude)
│   │   ├── ingest_teams.py
│   │   ├── ingest_players.py
│   │   ├── ingest_matches.py
│   │   └── ingest_odds.py
│   ├── queries/                 # 🔄 생성 필요 (Claude)
│   │   ├── match_context_query.cypher
│   │   └── tactical_query.cypher
│   ├── prompts/                 # 🔄 생성 필요 (Claude)
│   │   ├── regime_analyst_soccer.txt
│   │   └── odds_specialist_soccer.txt
│   ├── reports/                 # 🔄 생성 필요 (Claude)
│   │   └── soccer_EPL_ManCity_vs_Liverpool_20250115.md
│   └── n8n/                     # 🔄 생성 필요 (Gemini)
│       └── soccer_realtime_workflow.json
│
└── unified_monitoring/          # NBA + Soccer 통합 모니터링
    └── grafana_unified_dashboard.json
```

---

## 🚀 즉시 시작 가능한 작업

### **Claude (지금 바로)**:
1. Neo4j Schema 생성 (30분)
2. `ingest_teams.py` 작성 (1시간)
3. EPL 20개 팀 Ingestion 테스트 (30분)

### **Gemini (백그라운드)**:
1. N8N Workflow JSON 복사 및 수정 (1시간)
2. Metrics API에 Soccer 메트릭 추가 (30분)
3. Grafana Dashboard JSON 생성 (1시간)

---

## 📊 예상 성과

### **1주일 후**:
- ✅ 5대 리그 모두 Neo4j에 Ingestion 완료
- ✅ Realtime Pipeline 자동화 (매일 09:00 KST)
- ✅ 첫 Soccer Report 생성 (EPL 경기)

### **2주일 후**:
- ✅ 5대 리그 모든 경기에 대해 Report 생성 가능
- ✅ Grafana에서 NBA + Soccer 통합 모니터링
- ✅ Alertmanager로 Tactical RAG 기사 알림

### **1개월 후**:
- ✅ NBA + Soccer 통합 웹사이트 론칭
- ✅ 사용자가 "Man City vs Liverpool" 검색 → 즉시 Report 조회
- ✅ 구독 결제 시스템 통합

---

## 🎯 최종 목표

**G9 = NBA + Soccer 통합 베팅 인텔리전스 플랫폼**

```
[NBA 30팀 × 82경기] + [Soccer 100팀 × 38경기] = 연간 10,000+ 경기 분석
[실시간 Graph RAG] + [5-Person AI Council] + [Odds Movement Tracking]
↓
프로 베터를 위한 Ultimate Intelligence Platform
```

---

**다음 단계**: Claude가 Neo4j Schema 생성부터 시작 → Gemini가 N8N Workflow 복제 병렬 진행

**예상 완료일**: 2025년 1월 4일 (7일 후)

**질문/수정사항**: 즉시 피드백 반영 🚀
