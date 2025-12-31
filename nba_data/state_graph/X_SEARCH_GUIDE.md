# X(Twitter) 검색으로 실시간 NBA 정보 수집 가이드

## 핵심 개념

Grok의 X 검색 기능처럼, **Claude의 WebSearch**를 사용하여 X(트위터)에서 실시간 NBA 정보를 수집할 수 있습니다.

---

## 1. 심판 배정 (Referee Assignments)

### 타이밍
- **매일 9:00-10:00 AM ET** (@OfficialNBARefs가 게시)

### 검색 방법

**방법 A: WebSearch 사용**
```python
# Claude Code에서 WebSearch 도구 사용
query = "site:twitter.com from:OfficialNBARefs referee assignments"
# 또는
query = "site:x.com @OfficialNBARefs referee assignments today"
```

**방법 B: 직접 웹 요청**
```python
import requests
from bs4 import BeautifulSoup

url = "https://official.nba.com/referee-assignments/"
response = requests.get(url)
soup = BeautifulSoup(response.text, 'html.parser')
# 파싱: 경기별 심판 이름 추출
```

### 예상 포맷
```
Tonight's Referee Assignments:

HOU @ OKC (8:00 PM ET)
Crew Chief: Scott Foster
Referee: Tony Brothers
Umpire: Eric Lewis
Alternate: Derrick Collins
```

### 파싱 전략
- 키워드: "Crew Chief", "Referee", "Umpire"
- 경기 매칭: "팀명 @ 팀명" 또는 "vs"
- 시간: "PM ET", "Eastern"

---

## 2. 라인업 발표 (Starting Lineups)

### 타이밍
- **경기 30-60분 전** (팀 공식 계정에서)
- **경기 24-30시간 전** (Projected Lineups - RotoWire 등)

### 검색 방법

**팀 공식 계정**:
```python
# HOU 라인업 검색
query = "site:twitter.com from:HoustonRockets starting lineup OR starters"

# 여러 팀 동시 검색
for team in ["HOU", "OKC", "BOS"]:
    account = team_accounts[team]  # "HoustonRockets", "okcthunder", "celtics"
    query = f"site:twitter.com from:{account} starting lineup"
```

**집계 계정 (백업)**:
```python
# RotoWire (가장 빠르고 정확)
query = "site:twitter.com from:RotoWireNBA HOU starting lineup"

# FantasyLabs
query = "site:twitter.com from:FantasyLabsNBA starting five"

# Underdog
query = "site:twitter.com from:Underdog__NBA lineup"
```

### 예상 포맷

**텍스트 트윗**:
```
Starting lineup vs OKC:

PG: Fred VanVleet
SG: Jalen Green
SF: Dillon Brooks
PF: Jabari Smith Jr.
C: Alperen Sengun

#RocketUp
```

**이미지 포스트**:
- 대부분 팀은 그래픽 이미지로 게시
- OCR 필요 (Tesseract, Google Vision API)
- 또는 alt text 확인

### 파싱 전략
- 키워드: "Starting lineup", "starters", "starting five"
- 위치: "PG:", "SG:", "SF:", "PF:", "C:"
- 또는 단순 5명 이름 나열
- 해시태그: #RocketUp, #ThunderUp 등

---

## 3. 부상/가용성 업데이트 (Injury Updates)

### 타이밍
- **실시간** (하루 종일, 특히 경기 60-90분 전 집중)

### 검색 방법

**TOP 기자들**:
```python
# Shams Charania (현재 #1 NBA 인사이더)
query = "site:twitter.com from:ShamsCharania (out tonight OR available tonight)"

# Chris Haynes
query = "site:twitter.com from:ChrisBHaynes (#haynesbriefs OR ruled out)"

# 최근 24시간만
query += " after:2025-12-24"
```

**집계 계정**:
```python
# RotoWire (실시간 업데이트)
query = "site:twitter.com from:RotoWireNBA (out OR questionable OR doubtful)"

# FantasyLabs
query = "site:twitter.com from:FantasyLabsNBA injury update"
```

### 예상 포맷

**Shams**:
```
BREAKING: Houston Rockets' Steven Adams (ankle) will miss
tonight's game vs OKC, sources tell ESPN's Shams Charania.
```

**Haynes**:
```
Sources: OKC's Chet Holmgren is available tonight vs HOU
after missing last game with hip injury. #haynesbriefs
```

**RotoWire**:
```
#Rockets C Steven Adams (ankle) ruled OUT Wednesday.
```

### 파싱 전략
- 키워드: "BREAKING", "Sources:", "ruled out", "available", "will miss"
- 선수 이름 추출: 대문자 + 따옴표 패턴
- 상태: "OUT", "QUESTIONABLE", "DOUBTFUL", "AVAILABLE"
- 팀명: #Rockets, @HoustonRockets 등

---

## 4. 실전 구현 예시

### Python + WebSearch 통합

```python
#!/usr/bin/env python3
"""
실시간 NBA 정보 수집 (WebSearch 사용)
"""

def search_referee_assignments(date: str):
    """심판 배정 검색"""
    # Claude Code WebSearch 도구 사용
    query = f"site:twitter.com from:OfficialNBARefs referee assignments {date}"

    # 또는 직접 스크래핑
    import requests
    url = "https://official.nba.com/referee-assignments/"
    response = requests.get(url)

    # HTML 파싱
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(response.text, 'html.parser')

    # 오늘 경기 찾기
    games = soup.find_all('div', class_='game')
    referees = {}

    for game in games:
        matchup = game.find('span', class_='matchup').text
        crew_chief = game.find('span', class_='crew-chief').text
        referees[matchup] = crew_chief

    return referees

def search_team_lineup(team: str):
    """팀 라인업 검색"""
    team_accounts = {
        "HOU": "HoustonRockets",
        "OKC": "okcthunder",
        "BOS": "celtics"
    }

    account = team_accounts.get(team)
    if not account:
        return None

    # WebSearch로 최근 트윗 검색
    query = f"site:twitter.com from:{account} starting lineup"

    # Claude의 WebSearch 도구 사용
    # results = WebSearch(query)

    # 결과 파싱
    # 선수 이름 추출

    return {
        "team": team,
        "source": f"@{account}",
        "lineup": ["Player1", "Player2", "Player3", "Player4", "Player5"]
    }

def search_injury_updates():
    """부상 업데이트 검색"""
    reporters = ["ShamsCharania", "ChrisBHaynes"]
    keywords = ["out tonight", "available tonight", "ruled out"]

    updates = []

    for reporter in reporters:
        for keyword in keywords:
            query = f'site:twitter.com from:{reporter} "{keyword}"'

            # WebSearch 실행
            # results = WebSearch(query)

            # 파싱
            # updates.append({...})

    return updates
```

### Claude Code에서 직접 사용

```python
# Claude Code 세션에서
from calculate_team_strength import GameContext

# 1. 심판 정보 수집
referees = search_referee_assignments("2025-12-25")
# → HOU @ OKC: Scott Foster (Crew Chief)

# 2. 라인업 확인
hou_lineup = search_team_lineup("HOU")
okc_lineup = search_team_lineup("OKC")

# 3. 부상자 확인
injuries = search_injury_updates()
# → Steven Adams OUT (ankle)

# 4. GameContext 생성
context = GameContext(
    home_team="OKC",
    away_team="HOU",
    home_injuries=[],
    away_injuries=["Steven Adams"],  # ← X 검색으로 실시간 수집!
    referee_home_bias=0.58  # ← Scott Foster 홈 편향도
)

# 5. 팀 강도 계산
calculator = TeamStrengthCalculator()
matchup = calculator.calculate_matchup(context)
```

---

## 5. 자동화 전략

### 타이밍 스케줄

**오전 (9:00-10:00 AM ET)**:
```bash
# 심판 배정 수집
python fetch_realtime_lineups.py --referees
```

**오후 (경기 2-3시간 전)**:
```bash
# 부상 업데이트 확인
python fetch_realtime_lineups.py --injuries
```

**경기 1시간 전**:
```bash
# 라인업 최종 확인
for team in today_teams:
    python fetch_realtime_lineups.py --lineups $team
```

### Cron Job 설정

```bash
# /etc/crontab 또는 cron -e

# 매일 9:15 AM - 심판
15 9 * * * cd /Users/js/g9/nba_data/state_graph && python3 fetch_realtime_lineups.py --referees

# 경기일 오후 3시 - 부상
0 15 * * * cd /Users/js/g9/nba_data/state_graph && python3 fetch_realtime_lineups.py --injuries

# 경기 전 실시간 체크 (오후 5-11시, 30분마다)
*/30 17-23 * * * cd /Users/js/g9/nba_data/state_graph && python3 fetch_realtime_lineups.py --all
```

---

## 6. 데이터 통합 워크플로우

### 최종 파이프라인

```
1. 아침 9시: 심판 배정 수집
   → Neo4j GameContext 업데이트

2. 오후 3-5시: 부상자 뉴스 모니터링
   → lineup.json 수정 또는 GameContext.injuries 업데이트

3. 경기 1-2시간 전: 라인업 최종 확인
   → 예상 라인업 vs 실제 발표 비교
   → 변경사항 있으면 재계산

4. 경기 30분 전: 최종 베팅 분석
   → calculate_team_strength() 실행
   → v2.0 예측 + 실시간 정보 통합
```

### 코드 예시

```python
from datetime import datetime
from calculate_team_strength import TeamStrengthCalculator, GameContext

def prepare_game_analysis(home_team: str, away_team: str):
    """경기 분석 준비 (실시간 정보 통합)"""

    # 1. 심판 정보
    referees = fetch_referee_assignments(datetime.now())
    ref_bias = get_referee_home_bias(referees[f"{away_team} @ {home_team}"])

    # 2. 부상자 확인
    injury_updates = fetch_injury_updates()
    home_injuries = [u['player'] for u in injury_updates if u['team'] == home_team and u['status'] == 'OUT']
    away_injuries = [u['player'] for u in injury_updates if u['team'] == away_team and u['status'] == 'OUT']

    # 3. 라인업 확인
    home_lineup = fetch_team_lineup(home_team)
    away_lineup = fetch_team_lineup(away_team)

    # 4. GameContext 생성
    context = GameContext(
        home_team=home_team,
        away_team=away_team,
        home_injuries=home_injuries,
        away_injuries=away_injuries,
        referee_home_bias=ref_bias
    )

    # 5. 매치업 분석
    calculator = TeamStrengthCalculator()
    result = calculator.calculate_matchup(
        context,
        home_lineup=home_lineup['name'] if home_lineup else None,
        away_lineup=away_lineup['name'] if away_lineup else None
    )

    return result
```

---

## 7. 장점 vs 한계

### ✅ 장점

1. **실시간성**: ESPN 프리뷰보다 30-60분 빠름
2. **신뢰도**: 공식 계정 + TOP 기자 (Shams, Haynes)
3. **무료**: WebSearch 사용 (Twitter API 불필요)
4. **자동화**: Cron job으로 완전 자동화 가능

### ⚠️ 한계

1. **파싱 복잡도**: 트윗 포맷이 일정하지 않음
2. **이미지 처리**: 대부분 라인업은 그래픽 이미지
3. **Rate Limit**: WebSearch 과다 사용 시 제한 가능
4. **X API 변경**: Twitter/X 정책 변경 시 영향

### 💡 해결책

- **이미지 → 텍스트**: 집계 계정(@RotoWireNBA) 사용 (텍스트로 게시)
- **파싱 안정화**: 키워드 기반 유연한 파싱
- **백업 소스**: NBA.com 공식 페이지 스크래핑
- **캐싱**: 하루 1회만 검색, 결과 저장

---

## 8. 즉시 시작 가능한 단계

### Phase 1: 심판 배정 (가장 쉬움)
```bash
# 매일 9시에 자동 실행
python fetch_realtime_lineups.py --referees
```

**예상 결과**:
```json
{
  "date": "2025-12-25",
  "games": [
    {
      "matchup": "HOU @ OKC",
      "time": "8:00 PM ET",
      "crew_chief": "Scott Foster",
      "referees": ["Tony Brothers", "Eric Lewis"],
      "home_bias": 0.58
    }
  ]
}
```

### Phase 2: 부상 모니터링
```bash
# 실시간 체크
python fetch_realtime_lineups.py --injuries
```

**예상 결과**:
```json
{
  "updates": [
    {
      "player": "Steven Adams",
      "team": "HOU",
      "status": "OUT",
      "reason": "ankle",
      "source": "@ShamsCharania",
      "timestamp": "2025-12-25 15:30:00"
    }
  ]
}
```

### Phase 3: 라인업 수집
```bash
# 경기 1시간 전
python fetch_realtime_lineups.py --lineups HOU
```

**예상 결과**:
```json
{
  "team": "HOU",
  "lineup": [
    "Alperen Sengun",
    "Jabari Smith Jr.",
    "Amen Thompson",
    "Kevin Durant",
    "Reed Sheppard"
  ],
  "source": "@HoustonRockets",
  "timestamp": "2025-12-25 19:30:00"
}
```

---

## 요약

**X 검색 전략 = ESPN보다 빠른 실시간 정보**

1. **심판**: @OfficialNBARefs (9 AM)
2. **라인업**: 팀 계정 + @RotoWireNBA (30분 전)
3. **부상**: @ShamsCharania + @ChrisBHaynes (실시간)

→ **v2.0 동적 계산 엔진과 완벽한 조합!**
