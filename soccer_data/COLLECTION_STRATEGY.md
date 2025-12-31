# Soccer Data Collection Strategy

## 현재 상태
- ✅ **오즈 데이터**: football-data.co.uk CSV (무료, 크론 동작중)
- ❌ **xG 데이터**: Understat (로컬 파일만, 자동 수집 없음)
- ❌ **부상 정보**: 없음
- ❌ **라인업**: 없음

---

## 데이터 소스별 방법

### 1. xG 데이터 - Understat
**방법**: 크롤링 (API 없음)
**난이도**: 쉬움
**신뢰도**: 높음

```python
# Understat은 페이지에 JSON을 임베드함
import requests
import json
import re

url = "https://understat.com/league/EPL/2024"
response = requests.get(url)

# JavaScript 변수에서 JSON 추출
matches = re.findall(r'datesData\s*=\s*JSON\.parse\(\'(.+?)\'\)', response.text)
data = json.loads(matches[0].encode().decode('unicode_escape'))

# 매치별 xG 추출
for match_id, match in data.items():
    home_xg = match['xG']['h']
    away_xg = match['xG']['a']
```

**장점**:
- 무료
- JSON 형식으로 깔끔
- 안정적

**단점**:
- 크롤링이므로 구조 변경 시 깨질 수 있음
- Rate limit 주의 필요

---

### 2. 부상 정보

#### 옵션 A: ESPN API (추천)
**방법**: 공식 API
**난이도**: 쉬움
**신뢰도**: 높음

```python
# ESPN Soccer API (무료, 공식)
import requests

url = "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/teams"
response = requests.get(url)

for team in response.json()['sports'][0]['leagues'][0]['teams']:
    injuries_url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/teams/{team['team']['id']}/injuries"
    injuries = requests.get(injuries_url).json()
```

**장점**:
- 공식 API (안정적)
- 무료
- JSON 형식

**단점**:
- EPL 중심, 다른 리그는 제한적

#### 옵션 B: Transfermarkt 크롤링
**방법**: 크롤링
**난이도**: 중간
**신뢰도**: 높음

```python
import requests
from bs4 import BeautifulSoup

url = "https://www.transfermarkt.com/premier-league/verletzungen/wettbewerb/GB1"
response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
soup = BeautifulSoup(response.text, 'html.parser')

# 테이블 파싱
injuries_table = soup.find('table', class_='items')
```

**장점**:
- 모든 리그 커버
- 상세한 부상 정보

**단점**:
- Anti-bot 대응 필요
- HTML 파싱 복잡

---

### 3. 라인업

#### 옵션 A: FotMob 비공식 API (추천)
**방법**: 비공식 API
**난이도**: 쉬움
**신뢰도**: 중간

```python
import requests

# FotMob는 비공식 API를 노출함
match_id = "4193142"  # 예시
url = f"https://www.fotmob.com/api/matchDetails?matchId={match_id}"
response = requests.get(url)

lineup = response.json()['content']['lineup']
home_lineup = lineup['homeTeam']['starters']
away_lineup = lineup['awayTeam']['starters']
```

**장점**:
- JSON 응답
- 실시간 업데이트
- 간단

**단점**:
- 비공식이므로 언제든 막힐 수 있음

#### 옵션 B: ESPN API
```python
url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/summary?event={event_id}"
lineup = requests.get(url).json()['boxscore']['players']
```

---

### 4. 실시간 오즈 (선택사항)

#### 옵션 A: The Odds API (유료, NBA랑 공유)
**방법**: API
**비용**: $100/월 (25,000 requests)

```python
# 이미 NBA에서 사용중
url = "https://api.the-odds-api.com/v4/sports/soccer_epl/odds"
params = {
    'apiKey': API_KEY,
    'regions': 'us',
    'markets': 'h2h,spreads,totals'
}
```

#### 옵션 B: football-data.co.uk (현재 사용중)
**방법**: CSV 다운로드
**비용**: 무료

---

## 추천 구성

| 데이터 | 방법 | 소스 | 주기 | 우선순위 |
|--------|------|------|------|----------|
| 오즈 (마감) | CSV | football-data.co.uk | 매일 | ✅ 동작중 |
| xG | 크롤링 | Understat | 매일 | 🔴 높음 |
| 부상 | API | ESPN | 매일 | 🔴 높음 |
| 라인업 | 비공식 API | FotMob | 경기일 | 🟡 중간 |
| 오즈 (실시간) | API | The Odds API | 경기일 | 🟢 낮음 |

---

## 단계별 구현 계획

### Phase 1: 필수 데이터 (즉시)
1. **Understat xG 크롤러** - 경기 후 xG 수집
2. **ESPN 부상 수집** - 매일 업데이트

### Phase 2: 보완 데이터 (1주일)
3. **FotMob 라인업** - 경기 전 확정 라인업

### Phase 3: 선택 데이터 (필요시)
4. **The Odds API** - 실시간 오즈 변동 (NBA 크레딧 공유)

---

## 코드 구조

```
/opt/g9/domains/soccer/
├── collectors/
│   ├── understat_collector.py    # xG 크롤링
│   ├── espn_injuries.py           # ESPN 부상 API
│   └── fotmob_lineups.py          # FotMob 라인업
├── scripts/
│   ├── daily_collect.sh           # ✅ 오즈 CSV (동작중)
│   ├── collect_xg.sh              # xG 수집 cron
│   └── collect_injuries.sh        # 부상 수집 cron
```

---

## Anti-Ban 전략

### 크롤링 시 주의사항
```python
import time
import random

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://www.google.com/'
}

# Rate limiting
time.sleep(random.uniform(2, 5))  # 2-5초 랜덤 딜레이
```

### Rate Limit
- Understat: 요청 간 3초 이상
- Transfermarkt: IP 차단 주의, VPN 고려
- FotMob: 비공식이므로 조심스럽게

---

## 비용 분석

| 소스 | 비용 | 제한 |
|------|------|------|
| football-data.co.uk | 무료 | 없음 |
| Understat | 무료 | Rate limit만 지키면 OK |
| ESPN API | 무료 | 공식 API, 안정적 |
| FotMob | 무료 | 비공식, 언제든 막힐 수 있음 |
| The Odds API | $100/월 | 25K requests (NBA랑 공유 가능) |
