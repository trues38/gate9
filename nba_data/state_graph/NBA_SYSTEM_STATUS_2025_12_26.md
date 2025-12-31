# NBA 분석 시스템 현황 (2025-12-26)

## ✅ 완료된 레이어

### 1. **정량 데이터 레이어** (100% 완료)

#### Player 노드 (641명)
- 속성 자동 계산: ppg, rpg, apg, plus_minus
- Impact percentile, injury_prone, stamina
- Style tags (oreb-specialist, playmaker 등)
- **출처**: `expand_player_attributes.py`

#### Coach 노드 (24팀)
- 로테이션 깊이 (rotation_depth)
- 주전/벤치 출전 시간
- 템포 (pace)
- 전적 (win_pct)
- **출처**: `calculate_coach_stats.py`

#### Team Strength 계산 엔진
- 동적 팀 강도 계산
- 매치업 분석
- 부상자 시뮬레이션
- **출처**: `calculate_team_strength.py`

#### **Box Score 레이어 (v1.1) ⭐**
- **PlayerBoxScore 노드: 14,114개**
- **최신 데이터: 2025-12-23까지**
- 경기별 선수 스탯: PTS, REB, AST, FG%, 3PT%, +/- 등
- **크롤러**: `crawl_current_season_boxscores.py`
- **임포터**: `import_player_boxscores.py`
- **데이터**: `player_boxscores_2025_26/` (80개 파일)

**Box Score 스키마:**
```cypher
(:PlayerBoxScore {
  game_id: STRING,
  player_id: STRING,
  player_name: STRING,
  team: STRING,
  minutes: INT,
  points: INT,
  rebounds: INT,
  assists: INT,
  fg_made: INT,
  fg_attempted: INT,
  three_pt_made: INT,
  three_pt_attempted: INT,
  plus_minus: INT,
  ...
})

(:GameState)-[:HAS_BOXSCORE]->(:PlayerBoxScore)
(:Player)-[:PLAYED_IN]->(:PlayerBoxScore)
```

---

### 2. **Lineup 시스템** (완료)
- 30팀 템플릿: `lineups_template.json`
- 예시 데이터: `lineups_example.json` (HOU, BOS, OKC)
- 임포터: `import_lineups.py`

---

## ❌ 미구현 레이어

### Reddit 정성 분석 (KICK Layer 2)
- **상태**: 설계만 완료, 구현 안됨
- **설계 문서**: `KICK_ARCHITECTURE.md`
- **기능**:
  - Post-Game Thread 수집
  - 선수 평가 변화 추적
  - 코치 전술 평가
  - 팀 분위기 분석

**설계된 스키마:**
```cypher
(:RedditThread) - 0개 (미구현)
(:PlayerEvaluation) - 0개 (미구현)
(:CoachingAnalysis) - 0개 (미구현)
```

**필요 작업:**
1. Reddit API 설정 (REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET)
2. `reddit_post_game_collector.py` 스크립트 작성
3. n8n 워크플로우 연결 (경기 후 1시간 트리거)

---

## 🔧 실시간 수집 시스템 (미구현)

### 현재 수집 방식
- **수동 실행**: `python3 crawl_current_season_boxscores.py`
- **최신 데이터**: 2025-12-23 (3일 전)

### 필요한 실시간 시스템

#### Option 1: n8n 자동화 (추천)
```javascript
// n8n Cron Trigger: 매일 새벽 2시
// NBA 경기는 보통 자정 전에 종료

// Node 1: Check today's games
const today = new Date().toISOString().split('T')[0].replace(/-/g, '');

// Node 2: Crawl box scores
await $exec(`python3 /Users/js/g9/nba_data/state_graph/crawl_current_season_boxscores.py --date ${today}`);

// Node 3: Import to Neo4j
await $exec(`python3 /Users/js/g9/nba_data/state_graph/import_player_boxscores.py --date ${today}`);

// Node 4: Notify completion
await $http.post('http://localhost:3000/api/notify', {
  type: 'boxscore_updated',
  date: today
});
```

**스케줄:**
- 매일 02:00 (전날 경기 종료 후)
- 경기일에만 실행 (월~일)

#### Option 2: GitHub Actions (무료)
```yaml
name: Daily Box Score Collection
on:
  schedule:
    - cron: '0 2 * * *'  # 매일 02:00 UTC
jobs:
  collect:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - run: python3 crawl_current_season_boxscores.py
      - run: python3 import_player_boxscores.py
```

#### Option 3: Cron (로컬)
```bash
# crontab -e
0 2 * * * cd /Users/js/g9/nba_data/state_graph && python3 crawl_current_season_boxscores.py && python3 import_player_boxscores.py >> boxscore_crawl.log 2>&1
```

---

## 🚀 완성형까지 남은 작업

### 필수 (실시간성)
- [ ] **n8n 자동 Box Score 수집** (30분 작업)
  - Cron Trigger 설정
  - Python 스크립트 실행
  - 완료 알림

### 선택 (고도화)
- [ ] **Reddit 정성 분석 구현** (2-3시간)
  - Reddit API 설정
  - `reddit_post_game_collector.py` 작성
  - n8n 워크플로우 연결

- [ ] **실시간 부상 알림** (KICK Layer 1, 1-2시간)
  - X Search 연동 (Grok API)
  - 웹 알림 (Pusher/WebSocket)

---

## 📊 시스템 완성도

### 데이터 레이어
| 레이어 | 상태 | 데이터 수 | 최신성 |
|--------|------|-----------|--------|
| Player | ✅ 완료 | 641명 | 2025-26 시즌 |
| Coach | ✅ 완료 | 24팀 | 2025-26 시즌 |
| **Box Score** | ✅ 완료 | **14,114개** | **2025-12-23** |
| Lineup | ✅ 완료 | 3팀 (예시) | 수동 입력 |
| Reddit | ❌ 미구현 | 0개 | - |

### 분석 엔진
- ✅ Team Strength Calculator
- ✅ Matchup Analyzer
- ✅ Injury Simulator
- ✅ Context-based Analysis

### 실시간성
- ❌ 자동 Box Score 수집
- ❌ 실시간 부상 알림
- ❌ Reddit 자동 분석

---

## 🎯 추천 다음 단계

### Phase 1: 실시간 Box Score (최우선, 30분)
```bash
# 1. n8n 워크플로우 생성
# 2. Cron: 매일 02:00
# 3. 스크립트:
#    - crawl_current_season_boxscores.py
#    - import_player_boxscores.py
# 4. 알림: Slack/Telegram
```

**효과:**
- Box Score 항상 최신 유지
- 수동 작업 제거
- 베팅 분석 정확도 ↑

### Phase 2: Reddit 정성 분석 (선택, 2-3시간)
```bash
# 1. Reddit API 설정
# 2. reddit_post_game_collector.py 작성
# 3. n8n 워크플로우 연결
# 4. Neo4j 스키마 생성
```

**효과:**
- 팬들의 실제 평가 수집
- 선수 컨디션 변화 추적
- 코치 전술 인사이트

### Phase 3: 실시간 부상 알림 (선택, 1-2시간)
```bash
# 1. Grok API 또는 더미 데이터
# 2. n8n 워크플로우
# 3. 웹 알림 (Pusher)
```

**효과:**
- 부상 정보 즉시 인지
- 베팅 타이밍 개선

---

## 💡 결론

**현재 상태:**
- ✅ 정량 분석 시스템: **95% 완성**
- ✅ Box Score Layer: **완료** (14,114개 경기 스탯)
- ❌ 실시간 수집: **미구현**
- ❌ Reddit 정성 분석: **미구현**

**완성형까지:**
- **필수**: 실시간 Box Score 수집 (30분)
- **선택**: Reddit 분석 + 부상 알림 (3-5시간)

**우선순위:**
1. **n8n으로 Box Score 자동 수집** ← 가장 중요!
2. Reddit 정성 분석 (장기적 차별화)
3. 실시간 부상 알림 (Nice to have)

---

**작성일**: 2025-12-26
**다음 작업**: n8n Box Score 자동 수집 워크플로우 구현
