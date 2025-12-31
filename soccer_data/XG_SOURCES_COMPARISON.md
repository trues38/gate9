# xG 데이터 소스 비교 (2025년 기준)

## 무료 옵션

### 1. API-Football (추천 ⭐)
**URL**: https://www.api-football.com/

**무료 플랜**:
- ✅ 모든 엔드포인트 접근
- ✅ 카드 등록 불필요
- ✅ 영구 무료
- ⚠️ 100 requests/day (제한적)
- ⚠️ 최신 시즌만

**xG 데이터**:
```bash
GET /fixtures/statistics?fixture={id}
Response includes: expected_goals (home/away)
```

**장점**:
- 완전 무료
- JSON 응답
- 안정적

**단점**:
- 100 requests/day = 하루 100경기만
- 과거 시즌 제한

**평가**: 5개 리그 × 주말 15경기 = 75 requests/주말 → **충분**

---

### 2. RapidAPI - Football xG Statistics
**URL**: https://rapidapi.com/Wolf1984/api/football-xg-statistics/

**무료 플랜**:
- ✅ BASIC: EPL만 무료
- ⚠️ 500 requests/month
- 💳 카드 등록 필요

**유료 플랜**:
- PRO: $9.99/month - 10 리그
- ULTRA: $49.99/month - 모든 리그

**평가**: EPL만 필요하면 OK, 5개 리그는 유료

---

### 3. Sportmonks
**URL**: https://www.sportmonks.com/football-api/xg-data/

**플랜**:
- Basic: xG available 12시간 후
- Standard: xG 경기 직후
- Advanced: Live xG

**비용**:
- Free tier 없음
- 가격 문의 필요

**평가**: 무료 아님

---

### 4. FBref (StatsBomb)
**URL**: https://fbref.com/en/

**방법**: 웹 스크래핑

```python
from bs4 import BeautifulSoup
import requests

url = "https://fbref.com/en/matches/{match_id}"
# Parse HTML tables for xG
```

**장점**:
- 완전 무료
- 고품질 데이터 (StatsBomb)

**단점**:
- 스크래핑 필요
- Anti-bot 대응 필요
- HTML 구조 변경 시 깨짐

**평가**: 백업 옵션

---

## 추천 솔루션

### 옵션 A: API-Football 무료 (추천)
```python
import requests

API_KEY = "your_free_key"  # 회원가입만 하면 받음
url = "https://v3.football.api-sports.io/fixtures/statistics"

headers = {"x-apisports-key": API_KEY}
params = {"fixture": fixture_id}

response = requests.get(url, headers=headers, params=params)
data = response.json()

home_xg = data['response'][0]['statistics'][0]['expected_goals']
away_xg = data['response'][1]['statistics'][0]['expected_goals']
```

**일일 사용량**:
- 5개 리그 × 주말 평균 15경기 = 75 requests
- 주중 평균 5경기 = 25 requests
- **총 100 requests/day 이내 충분**

---

### 옵션 B: RapidAPI EPL만
EPL에만 집중한다면 무료로 가능

---

### 옵션 C: 스크래핑 (FBref)
API quota 초과 시 백업

---

## 구현 계획

### Phase 1: API-Football 무료 사용
1. 회원가입 → API 키 발급
2. 매일 자정 크론 실행
3. 전날 경기 xG 수집
4. SQLite 업데이트

### Phase 2: 필요시 업그레이드
- API-Football Basic: $15/month → 3,000 requests/day
- 5개 리그 전 경기 + 실시간 업데이트 가능

---

## 비용 비교

| 옵션 | 비용 | 커버리지 | Requests/day |
|------|------|----------|--------------|
| API-Football Free | $0 | 5개 리그 (최신) | 100 |
| API-Football Basic | $15 | 모든 리그 | 3,000 |
| RapidAPI Basic | $0 | EPL만 | 500/month |
| RapidAPI PRO | $10 | 10개 리그 | Unlimited |

---

## 최종 결론

**지금 바로 시작**: API-Football 무료
- 회원가입만 하면 됨
- 100 requests/day 충분
- 5개 리그 커버
- 완전 무료

**다음 단계**:
API-Football 무료 구현해볼까요?
