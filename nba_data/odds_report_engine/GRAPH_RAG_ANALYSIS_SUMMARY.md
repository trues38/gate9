# G9 NBA Graph RAG 분석 엔진 완성

## ✅ 완료된 작업

### 1. VPS Neo4j 데이터 동기화
- **문제**: VPS에 2024-25 시즌 데이터만 존재 (1,887 games)
- **해결**: `/Users/js/g9/nba_data/state_graph/season_2023_24/` 에서 1,322개 과거 경기 로드
- **결과**: 총 3,209 경기 데이터 확보 (2시즌)

### 2. 코드 기반 Graph RAG 분석 구현
LLM API 없이 순수 코드 로직으로 분석 인사이트 자동 생성

#### 분석 항목:

**A. Head-to-Head Edge 분석**
```
- H2H 전적 계산 (홈/어웨이 무관 전체 승수)
- 예: "Los Angeles Lakers dominates H2H (3-1 in last 4)"
```

**B. Recent Form 비교**
```
- 최근 5경기 승패 비교
- 예: "Sacramento Kings hotter (2-3 vs 1-4 L5)"
```

**C. Spread Value 분석**
```
- H2H 평균 승차 vs 현재 스프레드 라인 비교
- 예: "Spread -13.0 looks HIGH (H2H avg margin: 5.0)"
- 기준: avg_margin이 spread보다 3점 이상 작으면 HIGH
```

**D. Total Value 분석**
```
- H2H 평균 총점 vs 현재 Over/Under 라인 비교
- 예: "LEAN Under 232 (H2H avg: 218.5)"
- 기준: avg_total이 line보다 10점 이상 차이나면 추천
```

**E. Win Streak 감지**
```
- 3연승 이상 팀 자동 감지
- 예: "LA Clippers on 3-game win streak"
```

**F. Betting Recommendation**
```
- H2H + Form 모두 같은 팀 선호 시 → Moneyline 추천
- Spread/Total value 발견 시 → 해당 베팅 추천
- 데이터 불충분 시 → "Monitor lineups 30 min before tipoff"
```

### 3. 데이터 소스 통합

✅ **VPS Neo4j Graph**
- 3,209 games across 2 seasons
- Team, Player, Game nodes with relationships
- H2H history queries
- Recent form tracking

✅ **The Odds API**
- Moneyline (h2h)
- Point Spreads
- Over/Under Totals
- Real-time odds from 30+ bookmakers
- Credits: 389/500 remaining

✅ **NBA Stats API**
- Expected lineups (3-stage fallback)
- Player information
- Recent game starters

✅ **Referee Stats DB**
- Officials assignments
- Strictness index
- Betting impact analysis

### 4. 버그 수정

**❌ Before**: H2H 계산 오류
```python
# 홈팀이 홈에서 이긴 경기만 카운트 → 틀린 로직
home_wins = sum(1 for g in h2h if home_score > away_score and is_home)
away_wins = total_games - home_wins  # N/A 게임 포함
```

**✅ After**: 정확한 전체 승수 계산
```python
# 홈/어웨이 무관하게 각 팀의 총 승수 계산
for game in h2h:
    if no_score: continue  # N/A 제외
    winner = determine_winner(game, current_home_team)
    if winner == home_team: home_wins++
    else: away_wins++
```

**결과 비교**:
- Before: "Sacramento Kings dominates H2H (4-1)" ❌
- After: "Los Angeles Lakers dominates H2H (3-1)" ✅

### 5. 리포트 구조

```markdown
# G9 NBA Graph RAG Analysis Report

## 📊 Team Analysis
## 📜 Head-to-Head History (2 seasons)
## 🔥 Recent Form (L5)
## 👥 Key Players
## 🏃 Expected Lineups (3-stage fallback)
## 👨‍⚖️ Officials & Referee Analysis
## 💰 Betting Odds & Lines
   - Moneyline
   - Point Spread
   - Over/Under
## 🧠 Matchup Analysis & Betting Insights ⭐ NEW
   - H2H Edge
   - Form Edge
   - Spread Analysis
   - Total Analysis
   - Key Factors
   - Betting Recommendation
## 💡 Graph RAG Insights
```

## 🎯 핵심 성과

### Before (데이터 나열)
```
H2H History: 최근 5경기 맞대결
- 20250305: DET 115 @ LAC 123
- 20250224: LAC 97 @ DET 106
...
```

### After (Graph RAG 분석)
```
H2H History: 최근 5경기 맞대결
- 20250305: DET 115 @ LAC 123
- 20250224: LAC 97 @ DET 106
...

🧠 Matchup Analysis:
- H2H Edge: LA Clippers dominates H2H (3-1 in last 4)
- Form Edge: Similar form (3-2 vs 3-2)
- Spread Analysis: Current line matches historical data
- Betting Recommendation: Monitor lineups before tipoff
```

## 📁 파일 위치

- **메인 엔진**: `/Users/js/g9/nba_data/odds_report_engine/generate_graph_rag_reports.py`
- **리포트 출력**: `/Users/js/g9/nba_data/odds_reports/graphrag_*.md`
- **분석 로직**: `analyze_matchup_insights()` 함수 (lines 165-296)

## 🚀 실행 방법

```bash
cd /Users/js/g9/nba_data/odds_report_engine
python3 generate_graph_rag_reports.py
```

## 💡 Graph RAG 특징

1. **No LLM API Calls** - 순수 코드 로직으로 분석
2. **Neo4j Graph Queries** - 관계형 데이터 활용
3. **Historical Context** - 2시즌 데이터 기반
4. **Real-time Odds** - The Odds API 통합
5. **Actionable Insights** - 배팅 추천 자동 생성

---

**© 2025 G9 Regime Zero - Graph RAG Based Analysis**
**Generated: 2025-12-29**
