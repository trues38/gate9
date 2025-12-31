# xG 데이터 소스 테스트 결과 (2025-12-30)

## 테스트한 모든 소스

사용자님이 제안한 소스들을 실제로 접근하고 파싱 가능성을 테스트했습니다.

---

## 1. Understat.com

**현황**: ⚠️ JavaScript 렌더링 필요

### 테스트 결과
```
✅ 접근 가능 (HTTP 200)
❌ datesData 변수 없음
❌ teamsData 변수 없음
❌ JSON 데이터가 페이지에 내장되어 있지 않음
```

### 문제점
- 이전에는 `var datesData = JSON.parse('...')` 형태로 데이터가 HTML에 포함되었음
- 현재는 JavaScript로 동적 렌더링
- **Selenium 또는 Puppeteer 필요**

### 구현 난이도
- **중간-높음** (4-6시간)
- Chrome/ChromeDriver 설치 필요
- VPS 메모리 50-100MB 추가 사용

### 장점
- 고품질 xG 데이터
- 팀별 + 매치별 + 선수별 xG 모두 제공
- 5개 주요 리그 전부 커버

---

## 2. FBref.com

**현황**: ❌ 403 차단

### 테스트 결과
```
❌ HTTP 403 Forbidden
⚠️ Anti-bot 시스템 작동
```

### 문제점
- User-Agent만으로는 차단 우회 불가
- Cloudflare 또는 유사한 보안 시스템 사용
- **Selenium + 추가 우회 기술 필요**

### 구현 난이도
- **높음** (6-8시간)
- undetected-chromedriver 또는 playwright-stealth 필요
- 차단 위험 상존

### 장점
- Opta/StatsBomb 고품질 데이터
- xG, npxG, xAG 모두 제공
- 과거 시즌 데이터 풍부

---

## 3. FootyStats.org

**현황**: ✅ 접근 가능, ⚠️ 파싱 복잡

### 테스트 결과
```
✅ HTTP 200 OK
✅ xG 데이터 존재 확인
✅ HTML 테이블 형식
❌ 테이블 구조 매우 복잡 (50+ 셀/행)
❌ 헤더와 데이터 인덱스 불일치
```

### 문제점
- 테이블 하나에 Form, Stats, xG가 모두 혼재
- 셀 구조가 일관적이지 않음
- 팀명 파싱 어려움 (FC, League Position 등 혼재)

### 구현 난이도
- **중간** (3-4시간)
- BeautifulSoup로 가능하지만 복잡한 로직 필요

### 장점
- JavaScript 렌더링 불필요
- 100+ 리그 커버
- 팀별 평균 xG 제공

### 단점
- **매치별 xG는 확인 필요** (추가 페이지 크롤링 필요할 수 있음)

---

## 4. StatsHub.com

**현황**: ⚠️ JavaScript 렌더링 필요

### 테스트 결과
```
✅ HTTP 200 OK
✅ xG 데이터 언급 확인
❌ Next.js 기반 (클라이언트 렌더링)
❌ 정적 HTML에 데이터 없음
```

### 문제점
- Next.js SSR/CSR 앱
- 데이터가 API 호출로 로드됨
- **Selenium 또는 API 역공학 필요**

### 구현 난이도
- **높음** (6-8시간)
- Browser devtools로 API 엔드포인트 분석 필요
- 또는 Selenium 사용

---

## 5. FootballxG.com

**현황**: ✅ 접근 가능

### 테스트 결과
```
✅ HTTP 200 OK
✅ 50+ 리그 커버 명시
✅ xG League Tables 제공
```

### 미확인
- 실제 데이터 파싱은 미테스트
- Excel 스프레드시트 다운로드 가능 여부 불명

### 구현 난이도
- **미지수** (FootyStats와 유사할 가능성)

---

## 6. StatsBomb Open Data

**현황**: ✅ GitHub에서 무료 제공, ❌ EPL 없음

### 테스트 결과
```
✅ GitHub API 접근 가능
✅ JSON 형식 데이터
✅ 리그 확인:
   - La Liga (2020/2021, 2019/2020, ...)
   - Bundesliga (2023/2024, 2015/2016)
   - Ligue 1 (2022/2023, 2021/2022)
   - Champions League (다수 시즌)
   - World Cup (2022, 2018)

❌ Premier League (EPL) 데이터 없음
❌ Serie A 데이터 없음
```

### 문제점
- **EPL이 없음!** (가장 중요한 리그)
- 최신 시즌이 부족 (La Liga는 2020/2021까지)
- 토너먼트 중심 (World Cup, Champions League)

### 장점
- **완전 무료**
- **JSON 형식** (파싱 쉬움)
- **xG 계산 가능** (shot event 데이터 포함)
- 고품질 데이터 (StatsBomb 공식)

### 구현 난이도
- **낮음** (1-2시간)
- GitHub API로 직접 다운로드
- Python으로 간단히 파싱

---

## 종합 평가

| 소스 | 접근성 | EPL | 5대 리그 | 매치 xG | 구현 난이도 | 추천도 |
|------|--------|-----|----------|---------|------------|--------|
| **Understat** | ⚠️ Selenium | ✅ | ✅ | ✅ | 중간-높음 | ⭐⭐⭐⭐ |
| **FBref** | ❌ 403 | ✅ | ✅ | ✅ | 높음 | ⭐⭐ |
| **FootyStats** | ✅ | ✅ | ✅ | ❓ | 중간 | ⭐⭐⭐ |
| **StatsHub** | ⚠️ Selenium | ✅ | ✅ | ✅ | 높음 | ⭐⭐ |
| **FootballxG** | ✅ | ✅ | ✅ | ❓ | 미지수 | ⭐⭐⭐ |
| **StatsBomb** | ✅ 무료 | ❌ | ⚠️ 부분 | ✅ | 낮음 | ⭐⭐⭐ (EPL 없음) |

---

## 최종 권장 사항

### 옵션 A: Understat + Selenium ⭐⭐⭐⭐⭐ (추천)

**방법**:
```python
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

options = Options()
options.add_argument('--headless')
driver = webdriver.Chrome(options=options)

driver.get('https://understat.com/league/EPL/2024')
time.sleep(3)  # JavaScript 실행 대기

html = driver.page_source
# BeautifulSoup로 파싱
```

**장점**:
- ✅ EPL + 5대 리그 전부
- ✅ 매치별 xG, 팀별 xG, 선수별 xG
- ✅ 무료
- ✅ 과거 시즌 데이터 풍부

**단점**:
- ⚠️ 4-6시간 구현 시간
- ⚠️ VPS에 chromium 설치 필요 (50MB)
- ⚠️ Understat 구조 변경 시 깨질 수 있음

**구현 우선순위**: **1순위**

---

### 옵션 B: FootyStats 테이블 파싱 ⭐⭐⭐⭐

**방법**:
- BeautifulSoup로 복잡한 테이블 구조 파싱
- 팀별 평균 xG는 확인됨
- 매치별 xG는 추가 조사 필요

**장점**:
- ✅ Selenium 불필요
- ✅ 100+ 리그
- ✅ 무료

**단점**:
- ⚠️ 테이블 구조 복잡 (파싱 로직 복잡)
- ❓ 매치별 xG 제공 여부 불명확

**구현 우선순위**: **2순위** (Understat이 안 되면)

---

### 옵션 C: StatsBomb (La Liga, Bundesliga만) ⭐⭐⭐

**방법**:
```python
import requests

url = "https://raw.githubusercontent.com/statsbomb/open-data/master/data/matches/11/90.json"
data = requests.get(url).json()
# xG 데이터 추출
```

**장점**:
- ✅ 완전 무료
- ✅ 고품질 (StatsBomb 공식)
- ✅ JSON 형식 (파싱 쉬움)
- ✅ 구현 1-2시간

**단점**:
- ❌ **EPL 없음** (치명적)
- ⚠️ Serie A 없음
- ⚠️ 최신 시즌 부족

**구현 우선순위**: **3순위** (EPL이 필요 없다면 1순위)

---

### 옵션 D: 수동 CSV 다운로드 (임시 해결책)

- Understat 웹사이트 방문
- 리그 페이지에서 "Export CSV" 클릭 (제공 시)
- VPS 업로드

**장점**:
- 0시간 구현
- 무료

**단점**:
- 수동 작업
- 자동화 안 됨

---

## 결론

1. **무료 자동 xG 수집은 가능합니다** (제 이전 조사가 틀렸습니다)
2. **Understat + Selenium이 가장 현실적**
   - EPL 포함 5개 리그 전부
   - 4-6시간 구현
   - 완전 무료
3. **StatsBomb은 EPL이 없어서 사용 불가**
4. **FootyStats는 백업 옵션**

### 다음 단계

사용자님께서 선택하시면:
- **A**: Understat Selenium 크롤러 구현 (4-6시간 소요)
- **B**: FootyStats 파서 구현 및 매치 xG 확인 (3-4시간)
- **C**: StatsBomb으로 La Liga/Bundesliga만 수집 (1-2시간)
- **D**: xG 없이 진행 (Shot Quality 메트릭 사용 - 이미 구현 완료)

어떤 방향으로 진행하시겠습니까?
