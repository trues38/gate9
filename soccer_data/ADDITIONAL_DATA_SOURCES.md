# ⚽ Soccer 추가 데이터 소스 추천

**목적**: NBA 시스템과 동등한 수준의 인텔리전스를 위한 추가 Raw Data 수집
**우선순위**: 🔥 High | ⚡ Medium | 💡 Nice-to-Have

---

## 🔥 Priority 1: 즉시 수집 필요 (High Impact)

### 1️⃣ **실시간 부상 데이터** (Injury Reports)

**NBA 대응**: Injury Report (Player Availability)
**중요도**: 🔥🔥🔥 (Critical)

**데이터 소스**:

| 소스 | API/Scraping | 업데이트 주기 | 비용 |
|------|-------------|-------------|------|
| **PhysioRoom.com** | Scraping | 매일 | 무료 |
| **Transfermarkt** | Scraping | 매일 | 무료 |
| **FBref** | Scraping | 매일 | 무료 |
| **SofaScore API** | API (비공식) | 실시간 | $0 (Rate Limit 있음) |

**수집 항목**:
```json
{
  "player_id": "12345",
  "player_name": "Erling Haaland",
  "team": "Man City",
  "injury_type": "Muscle Strain",
  "severity": "Minor",
  "expected_return": "2025-01-05",
  "status": "Doubtful",
  "last_updated": "2025-01-02T10:30:00Z"
}
```

**구현 스크립트**:
```python
# scrapers/physioroom_scraper.py
import requests
from bs4 import BeautifulSoup

def scrape_injuries(league='EPL'):
    url = f"https://www.physioroom.com/news/{league.lower()}_injury_table.php"
    # Parse HTML and extract injury data
    # Store in raw_data/injuries/{league}_injuries.json
```

**Graph DB 활용**:
```cypher
MATCH (p:SoccerPlayer)-[:PLAYS_FOR]->(t:SoccerTeam)
WHERE p.name = 'Erling Haaland'
CREATE (i:Injury {type: 'Muscle Strain', severity: 'Minor', return_date: date('2025-01-05')})
CREATE (p)-[:SUFFERING]->(i)
```

**AI Council 프롬프트 영향**:
```
"Man City는 Haaland가 근육 부상으로 이번 경기 결장 예정.
과거 Haaland 없이 평균 xG 2.3 → 1.6으로 30% 하락.
Under 2.5 골 배팅 검토 필요."
```

---

### 2️⃣ **예상 라인업** (Predicted Lineups)

**NBA 대응**: Starting Lineup Confirmation
**중요도**: 🔥🔥🔥 (Critical)

**데이터 소스**:

| 소스 | API/Scraping | 업데이트 주기 | 정확도 |
|------|-------------|-------------|--------|
| **FootballLineups.com** | Scraping | 경기 2시간 전 | ~85% |
| **SofaScore** | Scraping | 경기 1시간 전 | ~90% |
| **Official Club Twitter** | Twitter API | 경기 1시간 전 | 100% |
| **ESPN Soccer** | Scraping | 경기 1시간 전 | ~95% |

**수집 항목**:
```json
{
  "match_id": "EPL_2425_380",
  "home_team": "Man City",
  "away_team": "Liverpool",
  "predicted_home_lineup": {
    "formation": "4-3-3",
    "starting_11": [
      {"name": "Ederson", "position": "GK", "confidence": 1.0},
      {"name": "Walker", "position": "RB", "confidence": 0.9},
      ...
    ]
  },
  "predicted_at": "2025-01-05T15:00:00Z",
  "match_kickoff": "2025-01-05T17:00:00Z"
}
```

**Graph DB 활용**:
```cypher
MATCH (m:SoccerMatch {id: 'EPL_2425_380'})
MATCH (p:SoccerPlayer {name: 'Haaland'})
CREATE (m)-[:EXPECTED_STARTER {confidence: 0.95, formation_position: 'ST'}]->(p)
```

**AI Council 프롬프트 영향**:
```
"예상 라인업: Man City는 4-3-3 포메이션에서 Haaland-Foden-Grealish 공격 트리오.
Liverpool은 4-4-2로 수비적 전환.
과거 4-4-2 vs 4-3-3 매치업에서 Liverpool 승률 62%."
```

---

### 3️⃣ **실시간 Odds API** (Live Betting Lines)

**NBA 대응**: The Odds API
**중요도**: 🔥🔥🔥 (Critical)

**현재 상태**: Historical Odds만 있음 (Football-Data CSV)
**필요**: 실시간 Odds Movement 추적

**데이터 소스**:

| 소스 | API | 업데이트 주기 | 비용 |
|------|-----|-------------|------|
| **The Odds API** | REST API | 5분 | $0 (500 calls/월) ✅ |
| **BetExplorer** | Scraping | 실시간 | 무료 |
| **OddsPortal** | Scraping | 실시간 | 무료 |
| **Pinnacle API** | REST API | 실시간 | 계정 필요 |

**추천**: The Odds API (NBA와 동일)

**API 엔드포인트**:
```bash
# EPL 경기 Odds 조회
curl "https://api.the-odds-api.com/v4/sports/soccer_epl/odds/?apiKey=YOUR_KEY&regions=eu&markets=h2h,spreads,totals"
```

**수집 항목**:
```json
{
  "match_id": "EPL_2425_380",
  "bookmaker": "Bet365",
  "market": "h2h",
  "home_odds": 1.85,
  "draw_odds": 3.60,
  "away_odds": 4.20,
  "timestamp": "2025-01-05T16:45:00Z"
}
```

**Graph DB 활용**:
```cypher
MATCH (m:SoccerMatch {id: 'EPL_2425_380'})
CREATE (o:OddsSnapshot {
  bookmaker: 'Bet365',
  home_odds: 1.85,
  draw_odds: 3.60,
  away_odds: 4.20,
  timestamp: datetime('2025-01-05T16:45:00Z')
})
CREATE (m)-[:HAS_ODDS]->(o)
```

**Grafana 대시보드**:
- Odds Movement Graph (Opening Line → Current Line)
- Asian Handicap 변동 추적
- Over/Under 2.5 골 배당 변화

---

### 4️⃣ **날씨 데이터** (Weather Conditions)

**NBA 대응**: 없음 (실내 경기)
**중요도**: 🔥🔥 (Soccer 전용, High Impact)

**이유**:
- 비/눈/바람이 Over/Under 골 수에 직접 영향
- 패스 성공률 하락 → xG 감소
- 특정 팀은 날씨에 취약 (Tiki-Taka 팀 vs 롱볼 팀)

**데이터 소스**:

| 소스 | API | 업데이트 주기 | 비용 |
|------|-----|-------------|------|
| **OpenWeatherMap** | REST API | 1시간 | $0 (1,000 calls/일) ✅ |
| **WeatherAPI** | REST API | 실시간 | $0 (1M calls/월) ✅ |
| **Visual Crossing** | REST API | 실시간 | $0 (1,000 calls/일) |

**추천**: OpenWeatherMap (무료, 안정적)

**API 엔드포인트**:
```bash
# Manchester 날씨 조회 (경기 3시간 전)
curl "https://api.openweathermap.org/data/2.5/forecast?lat=53.48&lon=-2.24&appid=YOUR_KEY"
```

**수집 항목**:
```json
{
  "match_id": "EPL_2425_380",
  "stadium": "Etihad Stadium",
  "city": "Manchester",
  "kickoff_time": "2025-01-05T17:00:00Z",
  "weather": {
    "condition": "Heavy Rain",
    "temperature": 8,
    "wind_speed": 35,
    "humidity": 85,
    "precipitation_probability": 80
  }
}
```

**Graph DB 활용**:
```cypher
MATCH (m:SoccerMatch {id: 'EPL_2425_380'})
CREATE (w:Weather {
  condition: 'Heavy Rain',
  wind_speed: 35,
  temperature: 8
})
CREATE (m)-[:PLAYED_IN]->(w)
```

**AI Council 프롬프트 영향**:
```
"경기 시작 시각 기온 8도, 폭우 예상 (강수 확률 80%).
과거 데이터: 비 올 때 Man City 평균 골 2.8 → 2.1 (25% 감소).
Under 2.5 골 배당 1.85 → 베팅 가치 있음."
```

---

### 5️⃣ **Twitter/Reddit Sentiment** (소셜 미디어 감성)

**NBA 대응**: Twitter (Shams, Woj)
**중요도**: 🔥🔥 (High)

**데이터 소스**:

| 소스 | API | 업데이트 주기 | 비용 |
|------|-----|-------------|------|
| **Twitter API v2** | REST API | 실시간 | $100/월 (Basic) |
| **Reddit API** | REST API | 실시간 | 무료 |
| **Pushshift** | REST API | 준실시간 | 무료 |

**추천**: Reddit API (무료) + Twitter (유료지만 가치 있음)

**수집 대상**:
- Twitter: @FabrizioRomano, @David_Ornstein (신뢰도 높은 기자)
- Reddit: r/soccer, r/PremierLeague, r/LiverpoolFC 등

**수집 항목**:
```json
{
  "platform": "Twitter",
  "author": "@FabrizioRomano",
  "text": "Haaland will NOT start vs Liverpool. Minor muscle issue. Here we go! 🔵",
  "timestamp": "2025-01-05T14:30:00Z",
  "sentiment": -0.7,
  "relevance": 0.95,
  "team": "Man City",
  "category": "injury"
}
```

**Graph DB 활용**:
```cypher
MATCH (m:SoccerMatch {id: 'EPL_2425_380'})
MATCH (t:SoccerTeam {name: 'Man City'})
CREATE (n:NewsEvent {
  source: '@FabrizioRomano',
  text: 'Haaland will NOT start...',
  sentiment: -0.7,
  category: 'injury',
  timestamp: datetime('2025-01-05T14:30:00Z')
})
CREATE (n)-[:ABOUT]->(t)
CREATE (n)-[:IMPACTS]->(m)
```

**AI Council 프롬프트 영향**:
```
"Twitter 속보 (Fabrizio Romano): Haaland 근육 부상으로 결장.
Reddit r/MCFC 감성 점수: -0.7 (매우 부정적).
팬들은 Foden의 False 9 역할 우려."
```

---

## ⚡ Priority 2: 중요하지만 나중에 가능 (Medium Impact)

### 6️⃣ **Head-to-Head 통계** (과거 맞대결)

**NBA 대응**: Team vs Team Historical Stats
**중요도**: ⚡⚡

**데이터 소스**:
- **11v11.com** (Scraping, 무료)
- **Transfermarkt** (Scraping, 무료)
- **FBref** (Scraping, 무료)

**수집 항목**:
```json
{
  "home_team": "Man City",
  "away_team": "Liverpool",
  "last_5_meetings": [
    {"date": "2024-11-10", "score": "1-1", "home_xg": 2.1, "away_xg": 1.8},
    {"date": "2024-03-15", "score": "3-1", "home_xg": 2.7, "away_xg": 1.2}
  ],
  "home_wins": 3,
  "draws": 1,
  "away_wins": 1
}
```

**AI Council 영향**:
```
"과거 5경기 맞대결: Man City 3승 1무 1패.
평균 총 골: 2.8골 → Over 2.5 경향."
```

---

### 7️⃣ **선수 시장가치** (Transfermarkt)

**NBA 대응**: Player Salary
**중요도**: ⚡⚡

**데이터 소스**:
- **Transfermarkt** (Scraping, 무료)

**수집 항목**:
```json
{
  "player": "Erling Haaland",
  "market_value": "€200M",
  "last_updated": "2025-01-01",
  "age": 24,
  "contract_until": "2027-06-30"
}
```

**Graph DB 활용**:
```cypher
MATCH (p:SoccerPlayer {name: 'Haaland'})
SET p.market_value = 200000000, p.contract_until = date('2027-06-30')
```

**AI Council 영향**:
```
"Haaland (시장가치 €200M) 결장 시 Man City 공격력 30% 하락 예상."
```

---

### 8️⃣ **ELO Rating / SPI** (전력 지수)

**NBA 대응**: Team Rating (Offensive/Defensive Rating)
**중요도**: ⚡⚡

**데이터 소스**:
- **FiveThirtyEight SPI** (무료, CSV 제공)
- **ClubELO** (무료, API 없음, Scraping)

**수집 항목**:
```json
{
  "team": "Man City",
  "elo_rating": 1895,
  "spi": 91.2,
  "offensive_rating": 3.1,
  "defensive_rating": 0.8,
  "last_updated": "2025-01-02"
}
```

**Graph DB 활용**:
```cypher
MATCH (t:SoccerTeam {name: 'Man City'})
SET t.elo_rating = 1895, t.spi = 91.2, t.off_rating = 3.1, t.def_rating = 0.8
```

**AI Council 영향**:
```
"Man City SPI 91.2 vs Liverpool SPI 88.5 → 우위 3%.
과거 SPI 격차 3% 이상 시 홈팀 승률 68%."
```

---

## 💡 Priority 3: Nice-to-Have (부가 가치)

### 9️⃣ **선수 체력 데이터** (Fatigue / Minutes Played)

**데이터 소스**: FBref, WhoScored
**중요도**: 💡

**수집 항목**:
```json
{
  "player": "Kevin De Bruyne",
  "last_7_days_minutes": 450,
  "avg_distance_per_game": 11.2,
  "fatigue_index": 0.75
}
```

**AI Council 영향**:
```
"De Bruyne 최근 7일간 450분 출전 (과부하).
과거 450분+ 주간 출전 시 어시스트 1.2 → 0.6 감소."
```

---

### 🔟 **코너킥/프리킥 통계**

**데이터 소스**: Understat, FBref
**중요도**: 💡

**수집 항목**:
```json
{
  "team": "Man City",
  "avg_corners_per_game": 7.2,
  "corners_to_goal_conversion": 0.08
}
```

**AI Council 영향**:
```
"Man City 평균 코너킥 7.2회/경기.
코너 → 골 전환율 8% (리그 평균 5%)."
```

---

## 🚀 수집 우선순위 요약

### **즉시 시작 (이번 주)**:
1. ✅ **The Odds API** - 실시간 배당 (NBA와 동일 API)
2. ✅ **OpenWeatherMap** - 날씨 데이터 (무료)
3. ✅ **PhysioRoom** - 부상 데이터 (Scraping)

### **다음 주**:
4. ✅ **Twitter API** - 소셜 미디어 감성 (유료)
5. ✅ **FootballLineups** - 예상 라인업 (Scraping)
6. ✅ **Reddit API** - 팬 반응 (무료)

### **2주 후**:
7. ✅ **FiveThirtyEight SPI** - 전력 지수 (무료 CSV)
8. ✅ **Transfermarkt** - 선수 시장가치 (Scraping)
9. ✅ **11v11** - Head-to-Head 통계 (Scraping)

---

## 📋 구현 체크리스트

### **스크래퍼 작성**:
- [ ] `scrapers/physioroom_scraper.py` - 부상 데이터
- [ ] `scrapers/lineups_scraper.py` - 예상 라인업
- [ ] `scrapers/weather_api.py` - 날씨 API
- [ ] `scrapers/twitter_soccer.py` - Twitter 감성
- [ ] `scrapers/reddit_soccer.py` - Reddit 감성
- [ ] `scrapers/h2h_scraper.py` - 과거 맞대결
- [ ] `scrapers/transfermarkt_scraper.py` - 시장가치
- [ ] `scrapers/spi_downloader.py` - FiveThirtyEight SPI

### **Graph DB Ingestion**:
- [ ] `ingest/ingest_injuries.py`
- [ ] `ingest/ingest_lineups.py`
- [ ] `ingest/ingest_weather.py`
- [ ] `ingest/ingest_social_sentiment.py`
- [ ] `ingest/ingest_h2h.py`
- [ ] `ingest/ingest_market_value.py`
- [ ] `ingest/ingest_spi.py`

### **N8N Workflow**:
- [ ] Daily 09:00 KST - Injury Update
- [ ] Pre-Match (2시간 전) - Lineup + Weather
- [ ] Real-time (5분) - Odds Movement
- [ ] Real-time (30분) - Twitter/Reddit Scraping

---

## 💰 비용 예상

| 데이터 소스 | 월 비용 | 필수도 |
|-----------|--------|--------|
| The Odds API | $0 (500 calls) | 🔥 필수 |
| OpenWeatherMap | $0 (1,000 calls/일) | 🔥 필수 |
| Twitter API v2 | $100/월 | ⚡ 권장 |
| PhysioRoom | $0 (Scraping) | 🔥 필수 |
| Reddit API | $0 | ⚡ 권장 |
| FiveThirtyEight | $0 (CSV) | 💡 선택 |
| **Total** | **$100/월** | |

**ROI**: 단 하나의 배팅 성공으로 월 비용 회수 가능 ✅

---

## 🎯 데이터 통합 후 예상 효과

### **Before** (현재):
```
- Understat xG
- Historical Odds (과거 배당만)
- Tactical RAG (전술 기사)
- Referee Stats
```

### **After** (전체 수집 후):
```
- ✅ Understat xG
- ✅ Real-time Odds (실시간 배당 변동)
- ✅ Tactical RAG
- ✅ Referee Stats
- ✅ Injury Reports (실시간 부상)
- ✅ Predicted Lineups (경기 2시간 전)
- ✅ Weather Data (강수, 바람, 온도)
- ✅ Twitter/Reddit Sentiment (팬 감성)
- ✅ Head-to-Head Stats (과거 맞대결)
- ✅ Player Market Value (시장가치)
- ✅ ELO / SPI Rating (전력 지수)
```

**결과**: **NBA 수준의 Complete Intelligence** ✅

---

## 🚀 즉시 실행 가능한 명령어

### **1. The Odds API 테스트**:
```bash
curl "https://api.the-odds-api.com/v4/sports/soccer_epl/odds/?apiKey=YOUR_KEY&regions=eu&markets=h2h"
```

### **2. OpenWeatherMap 테스트**:
```bash
curl "https://api.openweathermap.org/data/2.5/forecast?lat=53.48&lon=-2.24&appid=YOUR_KEY"
```

### **3. PhysioRoom Scraping 테스트**:
```python
import requests
from bs4 import BeautifulSoup

url = "https://www.physioroom.com/news/epl_injury_table.php"
response = requests.get(url)
soup = BeautifulSoup(response.text, 'html.parser')
print(soup.find_all('tr'))
```

---

**다음 단계**: Gemini가 스크래퍼 작성, Claude가 Graph Ingestion 작성 병렬 진행 🚀
