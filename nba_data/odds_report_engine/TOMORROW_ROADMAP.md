# 🚀 내일까지 완성 로드맵

**목표**: Graph RAG + 실시간 5종 데이터 융합 리포트 완성

**현재 상태**: 2025-12-28 21:51

---

## ✅ 현재 완료 상태

### 1. Odds (실시간) ✅
- **소스**: The Odds API
- **상태**: 100% 작동
- **데이터**: Moneyline, Spreads, Totals
- **크레딧**: 462/500 남음

### 2. Injuries (부상자) ✅
- **소스**: ESPN Roster API
- **상태**: 100% 작동
- **예시**: TOR vs GSW → 7명 부상자 발견
  - TOR: RJ Barrett (OUT), Poeltl (OUT)
  - GSW: Seth Curry (OUT), Melton (OUT)

### 3. Graph RAG (샘플) ⚠️
- **소스**: Neo4j (샘플 데이터)
- **상태**: 50% 완료
- **필요**: VPS/로컬 Neo4j 실제 연결

### 4. Referees (심판) ⚠️
- **소스**: Basketball Reference
- **상태**: 70% 완료
- **이슈**: Parsing 에러 (수정 필요)

### 5. Lineups (라인업) ❌
- **소스**: Twitter API / 팀 공식
- **상태**: 0% (미구현)
- **대안**: 경기 30분 전 수동 확인 권장

---

## 📋 내일 (2025-12-29) 작업 계획

### 오늘 밤 (23:00~01:00) - 2시간

**Task 1**: Neo4j 연결 수정 ✅
```bash
# 1. 로컬 Neo4j 재시작
docker start neo4j-nba
docker exec neo4j-nba cypher-shell -u neo4j -p test123 "MATCH (n) RETURN count(n);"

# 2. Graph RAG 연결 테스트
python3 << EOF
from neo4j import GraphDatabase
driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "test123"))
with driver.session() as session:
    result = session.run("MATCH (t:Team) RETURN t.name LIMIT 5")
    print([r["t.name"] for r in result])
EOF

# 3. graph_odds_report_generator.py 업데이트
```

**Task 2**: Referees 파싱 수정 ✅
```python
# realtime_data_collector.py 수정
def _collect_referees(self):
    # BeautifulSoup 파싱 로직 개선
    # tbody가 없을 경우 fallback 추가
```

**예상 결과**: Graph RAG + Odds + Injuries 완전 작동

---

### 내일 새벽 (09:00~11:00) - 2시간

**Task 3**: 완전체 리포트 생성기 통합 ✅
```python
# File: generate_ultimate_report.py

class UltimateReportGenerator:
    def __init__(self):
        self.neo4j_connector = Neo4jConnector()
        self.realtime_collector = RealtimeDataCollector()
        self.ai_council = AIBettingCouncil()

    def generate(self, home_team, away_team):
        # 1. Neo4j Graph RAG
        graph_data = self.neo4j_connector.get_matchup_data(home, away)

        # 2. Realtime Data (Odds + Injuries)
        realtime_data = self.realtime_collector.collect_all_data(home, away)

        # 3. Fusion Report
        full_report = self.fusion_analysis(graph_data, realtime_data)

        # 4. AI Council
        ai_analysis = self.ai_council.analyze(full_report)

        # 5. Final Report
        return self.format_ultimate_report(full_report, ai_analysis)
```

**Task 4**: 테스트 리포트 생성 ✅
```bash
./generate_ultimate_report.sh TOR GSW

# 예상 출력:
# ✅ Graph RAG: Regime 패턴 (실제 Neo4j 데이터)
# ✅ Odds: -4.5 스프레드
# ✅ Injuries: 7명 부상자 (실시간)
# ✅ Referees: Top 10 심판 통계
# ✅ AI Council: 5/5 합의
```

**예상 결과**: 완전체 리포트 1차 완성

---

### 내일 오후 (14:00~16:00) - 2시간

**Task 5**: Lineups 수집 추가 (선택)
```python
# Option 1: Twitter API (유료)
# Option 2: 팀 공식 사이트 크롤링
# Option 3: NBA Stats API

# 간단한 대안: 경기 30분 전 수동 확인
def _collect_lineups(self):
    return {
        "note": "경기 30분 전 팀 공식 발표 확인 필요",
        "sources": [
            "Twitter: @warriors, @Raptors",
            "NBA.com Official Lineup"
        ]
    }
```

**Task 6**: 최종 테스트 & 문서화 ✅
```bash
# 오늘 모든 경기 리포트 생성
for game in PHI_OKC BOS_POR MEM_WSH; do
    ./generate_ultimate_report.sh ${game/_/ }
done

# 성공률 확인
ls -lh /Users/js/g9/nba_data/odds_reports/ultimate_*.md
```

**예상 결과**: 완전체 시스템 완성 🎉

---

## 📊 완성 시 리포트 구조

### Ultimate Report ($3-5 판매 가격)

```markdown
# 🏀 G9 Ultimate NBA Betting Report
## Golden State Warriors @ Toronto Raptors

---

## 📊 EXECUTIVE SUMMARY

**AI Council Consensus**: 5/5 (만장일치 BET)
**Recommended Play**: Warriors -4.5 @ 2 units
**Confidence**: HIGH (Graph + Realtime 데이터 완전 융합)

---

## 🎯 GRAPH RAG ANALYSIS (Neo4j)

### Regime Analysis
- **Warriors**: ROAD_DOMINANCE (8 games, 91% confidence)
  - 최근 10경기: 8-2
  - 원정 기록: 9-8
  - 평균 마진: +6.8

- **Raptors**: DECLINE (12 games, 87% confidence)
  - 최근 10경기: 3-7
  - 홈 기록: 8-12
  - 평균 마진: -5.1

### Head-to-Head (실제 DB)
- 최근 3경기: Warriors 3-0
- 평균 스코어: 115-102 (Warriors)
- 스프레드 커버: 3/3 (100%)

---

## 💰 REALTIME ODDS (The Odds API)

**수집 시간**: 2025-12-28 21:51 (경기 23시간 전)

### Moneyline
- Warriors: -170 (lowvig)
- Raptors: +160 (bovada)

### Spreads
- Warriors: -4.5 @ -110 (fanduel)
- Raptors: +4.5 @ -101 (lowvig)

**Line Movement**: 안정적 (지난 6시간 변동 없음)

---

## 🚑 INJURY REPORT (ESPN - 실시간)

**수집 시간**: 2025-12-28 21:51

### Toronto Raptors (3명)
- ❌ **RJ Barrett** (OUT) - 핵심 선수
- ❌ **Jakob Poeltl** (OUT) - 센터
- ⚠️ **Collin Murray-Boyles** (Day-to-Day)

### Golden State Warriors (4명)
- ❌ **Seth Curry** (OUT)
- ❌ **De'Anthony Melton** (OUT)
- ⚠️ **Brandin Podziemski** (Day-to-Day)
- ⚠️ **L.J. Cryer** (Day-to-Day)

**Impact Analysis**:
- Raptors 주력 2명 OUT → 공격력 20% 감소 예상
- Warriors 백업 선수 OUT → 영향 미미

---

## 👔 REFEREE ANALYSIS

**오늘 배정**: (경기 당일 확인 필요)

**Top Referees Stats** (2024-25 시즌):
1. Scott Foster - 45 games
2. Tony Brothers - 42 games
3. Marc Davis - 40 games

**Note**: 경기 당일 아침 9시(ET) 확인 (@OfficialNBARefs)

---

## 👥 STARTING LINEUPS

**Status**: 경기 30분 전 확인 필요

**Expected Starters**:
- Raptors: Barnes, Dick, Agbaji, Olynyk, Battle (Barrett OUT)
- Warriors: Curry, Wiggins, Kuminga, Green, Looney

**Confirmation**:
- Twitter: @Raptors, @warriors
- NBA.com Official

---

## 🤖 AI COUNCIL ANALYSIS (5인 위원회)

### Consensus: 5/5 (만장일치 BET)

**Key Factors**:
1. ✅ Regime Alignment (ROAD_DOMINANCE vs DECLINE)
2. ✅ H2H Pattern (3연승, 100% 스프레드 커버)
3. ✅ Injury Impact (Raptors 주력 2명 OUT)
4. ✅ Odds Value (-4.5는 합리적 라인)
5. ✅ Line Stability (대중 과열 없음)

**Individual Votes**:
- DeepSeek V3.2: BET (HIGH) - "통계적 우위 명확"
- Qwen 72B: BET (HIGH) - "H2H 패턴 강력"
- Grok 4.1 Fast: BET (MEDIUM) - "부상자 임팩트 크다"
- Gemini 2.5 Flash: BET (MEDIUM) - "실시간 데이터 긍정적"
- GPT-4o-mini: BET (HIGH) - "모든 지표 일치"

---

## 💡 INVESTMENT GUIDE

**Final Recommendation**: Warriors -4.5 @ -110
**Bet Size**: 2-3 units (Strong Confidence)
**Expected ROI**: +12% (Graph + Realtime 융합 분석)

**Risk Factors**:
- ⚠️ Curry 컨디션 (경기 전 확인)
- ⚠️ Raptors 홈 desperation

**Next Steps**:
1. 경기 30분 전: 라인업 확인
2. 경기 전: Curry 워밍업 체크
3. Live: 1Q 모니터링

---

## ⚠️ DISCLAIMER

This report combines:
- Graph RAG (Neo4j 20,000+ nodes)
- Realtime Odds (The Odds API)
- Injury Data (ESPN API)
- AI Council (5 models)

투자 권유가 아닙니다. 모든 베팅은 본인 책임입니다.

---

*Generated by G9 Regime Zero Ultimate Betting Engine*
*Graph RAG + Realtime Fusion + AI Council*
```

---

## 🎯 완성 시 차별점

### 일반 베팅 리포트
```
"Warriors가 이길 것 같아요"
```

### G9 Ultimate Report
```
"Warriors -4.5 추천합니다 (5/5 만장일치)

근거:
1. Graph RAG: ROAD_DOMINANCE 레짐 (91% 신뢰도)
2. H2H: 최근 3경기 100% 스프레드 커버
3. 실시간 부상: Raptors 주력 2명 OUT (21:51 확인)
4. Odds: -170 ML, -4.5 스프레드 (라인 안정)
5. AI 5인 위원회: 만장일치 BET

기댓값: +12% ROI
리스크: Curry 컨디션만 확인
"
```

**차이**: 정성 → 정량, 추측 → 데이터, 단일 AI → 5인 합의

---

## 💰 가격 전략 (최종)

| Tier | 내용 | 비용 | 판매가 | 마진 |
|------|------|------|--------|------|
| Free | Odds만 | $0.01 | 무료 | - |
| Standard | Odds + Injuries | $0.02 | $1 | 98% |
| Premium | + Graph RAG + AI Council | $0.10 | $3 | 96.7% |
| **Ultimate** | + 실시간 5종 융합 | $0.15 | **$5** | **97%** |

**Ultimate 특징**:
- Graph RAG (20,000+ 노드)
- 실시간 Odds
- 실시간 Injuries (ESPN)
- Referee Stats
- Lineup 체크리스트
- AI 5인 위원회

**월 수익 예상** (하루 5경기):
- 비용: $0.15 × 150경기 = $22.5
- 수익: $5 × 150경기 = $750
- 순익: **$727.5** (97% 마진!)

---

## ✅ 체크리스트 (내일 완료 목표)

### 오늘 밤
- [ ] Neo4j 로컬 연결 수정
- [ ] Referees 파싱 수정
- [ ] 통합 테스트 (TOR vs GSW)

### 내일 새벽
- [ ] Ultimate Report Generator 작성
- [ ] 전체 파이프라인 통합
- [ ] 테스트 리포트 3개 생성

### 내일 오후
- [ ] Lineups 체크리스트 추가
- [ ] 최종 문서화
- [ ] VPS 배포 준비

---

**Status**: 80% 완료 (내일 100% 달성 가능!)
**Next**: 오늘 밤 Neo4j 연결 → 내일 새벽 통합 → 내일 오후 완성
**Goal**: Graph RAG + 실시간 5종 융합 리포트 🚀
