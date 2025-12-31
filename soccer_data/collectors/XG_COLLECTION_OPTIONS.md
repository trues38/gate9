# xG 데이터 수집 문제 및 해결책

## 문제
Understat이 웹 구조를 변경하여 간단한 크롤링이 불가능합니다.
- `datesData` 변수가 더 이상 페이지에 없음
- JavaScript로 동적 렌더링
- ESPN API에도 xG 데이터 없음
- FotMob API도 접근 불가

## 해결 옵션

### 옵션 1: Selenium 사용 (추천)
**방법**: Headless Chrome으로 JavaScript 렌더링 후 추출

```python
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

options = Options()
options.add_argument('--headless')
driver = webdriver.Chrome(options=options)

driver.get('https://understat.com/league/EPL/2024')
# JavaScript 실행 대기
time.sleep(3)

# 페이지 소스에서 데이터 추출
html = driver.page_source
driver.quit()
```

**장점**:
- 확실하게 작동
- Understat 데이터 100% 활용

**단점**:
- Chrome/ChromeDriver 설치 필요
- 메모리 사용 증가 (50-100MB)
- 느림 (리그당 5-10초)

**VPS 설치**:
```bash
apt-get install chromium-chromedriver
pip3 install selenium
```

---

### 옵션 2: API-Football 유료 API
**방법**: 공식 API 사용

```python
url = "https://v3.football.api-sports.io/fixtures/statistics"
headers = {'x-apisports-key': API_KEY}
params = {'fixture': fixture_id}

response = requests.get(url, headers=headers, params=params)
# xG included in response
```

**비용**:
- Free tier: 100 requests/day (불충분)
- Basic: $15/month, 3,000 requests/day (충분)

**장점**:
- 안정적
- xG + 모든 통계 포함
- 라인업, 부상 정보도 포함

**단점**:
- 월 $15 비용

---

### 옵션 3: 수동 CSV 업데이트
**방법**: Understat에서 주기적으로 CSV 다운로드

Understat 제공 CSV:
- https://understat.com/league/EPL/2024 → Export CSV

**장점**:
- 무료
- 간단

**단점**:
- 수동 작업
- 실시간성 없음

---

### 옵션 4: xG 없이 진행
**방법**: xG를 선택 데이터로 간주

football-data.co.uk CSV에는 다음이 포함됨:
- 슛 (HS, AS)
- 타겟 슛 (HST, AST)
- 코너킥, 파울 등

xG 없이도 분석 가능:
- 타겟 슛 / 슛 비율
- 슛 효율성
- Expected Goals 대신 "Shot Quality" 지표 생성

**장점**:
- 무료
- 추가 구현 불필요

**단점**:
- xG만큼 정교하지 않음

---

## 추천 선택

### 단기 (지금 당장)
**옵션 4**: xG 없이 진행
- 이미 충분한 통계 있음 (슛, 타겟 슛, 점유율)
- 배당 + 기본 스탯만으로도 분석 가능

### 중기 (필요하면)
**옵션 1**: Selenium 구현
- VPS에 Chromium 설치
- 주 1회 배치 실행 (빠른 업데이트 불필요)

### 장기 (수익 나면)
**옵션 2**: API-Football 구독
- $15/month = 매일 커피 한 잔
- xG + 모든 데이터 + 안정성

---

## 현재 우리가 가진 데이터

| 데이터 | 소스 | 상태 |
|--------|------|------|
| 경기 결과 | football-data.co.uk | ✅ |
| 오즈 (1X2, AH, O/U) | football-data.co.uk | ✅ |
| 슛 통계 | football-data.co.uk | ✅ |
| 타겟 슛 | football-data.co.uk | ✅ |
| 코너킥 | football-data.co.uk | ✅ |
| 파울 | football-data.co.uk | ✅ |
| 카드 | football-data.co.uk | ✅ |
| 심판 | football-data.co.uk | ✅ |

**이것만으로도 충분합니다.**
