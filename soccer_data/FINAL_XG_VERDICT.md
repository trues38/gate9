# 축구 xG 데이터 수집 - 최종 결론

## 조사한 모든 옵션

### 무료 API ❌
| 소스 | 결과 | 이유 |
|------|------|------|
| API-Football | ❌ | 무료 플랜에 데이터 없음 |
| Sofascore API | ❌ | 403 차단 |
| FotMob API | ❌ | 404 차단 |
| ESPN API | ❌ | xG 데이터 미포함 |
| Football-Data.org | ❓ | 토큰 필요, xG 포함 여부 불확실 |

### X (Twitter) ❌
| 계정/방법 | 결과 | 이유 |
|----------|------|------|
| @xGscore | ❌ | X API 로그인 필요 |
| X API v2 | 💰 | 유료 ($100/월 Basic) |
| 스크래핑 | ❌ | 로그인 벽 |

### 화이트리스트 (공개 데이터) ❌
| 소스 | 결과 | 이유 |
|------|------|------|
| StatsBomb Open Data | ❌ | 리그 데이터 없음 (월드컵만) |
| Kaggle 데이터셋 | ❌ | 과거 데이터만, 실시간 없음 |
| Reddit r/soccer | ❌ | API 403 차단 |
| GitHub soccerdata | ❌ | 설치 에러 (의존성 문제) |

### 스크래핑 ⚠️
| 소스 | 난이도 | 결과 |
|------|--------|------|
| Understat | 높음 | JavaScript 렌더링 (Selenium 필요) |
| FBref | 중간 | Anti-bot, 불안정 |
| WhoScored | 높음 | 403 차단 |

---

## 현실적인 옵션

### 옵션 1: xG 없이 진행 ⭐ 추천
**우리가 이미 가진 데이터**:
```
✅ 슛 (HS, AS)
✅ 타겟 슛 (HST, AST)
✅ 점유율
✅ 코너킥
✅ 파울
✅ 카드
✅ 오즈 (1X2, AH, O/U)
```

**대체 지표 생성**:
- Shot Quality = (Shots on Target / Total Shots)
- Conversion Rate = (Goals / Shots on Target)
- Shot Efficiency = (Goals / Total Shots)

**장점**:
- 무료
- 이미 구현됨
- 안정적

**단점**:
- xG만큼 정교하지 않음

---

### 옵션 2: 수동 CSV 다운로드
**방법**:
1. Understat 웹사이트 방문
2. 리그 페이지에서 "Export CSV" 클릭
3. VPS에 업로드
4. SQLite 업데이트

**주기**: 주 1회

**장점**:
- 무료
- 정확한 데이터
- 간단

**단점**:
- 수동 작업 필요
- 자동화 안됨

---

### 옵션 3: Selenium 크롤링
**구현**:
```python
from selenium import webdriver

options = webdriver.ChromeOptions()
options.add_argument('--headless')

driver = webdriver.Chrome(options=options)
driver.get('https://understat.com/league/EPL/2024')

# Wait for JavaScript
time.sleep(5)

# Extract data
html = driver.page_source
# Parse and extract xG
```

**VPS 요구사항**:
- chromium-chromedriver 설치
- 메모리 50-100MB 추가

**장점**:
- 자동화 가능
- 무료

**단점**:
- 복잡한 구현
- 메모리 사용
- Understat 구조 변경 시 깨짐
- 차단 위험

---

### 옵션 4: 유료 API
**가격**:
- API-Football Basic: $15/월
- RapidAPI PRO: $10/월
- Sportmonks: 문의 필요

**장점**:
- 안정적
- 자동화
- 모든 통계 포함

**단점**:
- 비용

---

## 비용 분석

| 옵션 | 비용 | 시간 투자 | 안정성 |
|------|------|-----------|--------|
| xG 없이 | $0 | 0시간 (완료) | 높음 |
| 수동 CSV | $0 | 5분/주 | 높음 |
| Selenium | $0 | 4-6시간 구현 | 중간 |
| 유료 API | $10-15/월 | 1시간 구현 | 높음 |

---

## 최종 권장

### 현재 (Phase 1): xG 없이 시작
**이유**:
1. 이미 충분한 데이터 있음
2. 추가 비용/시간 불필요
3. 슛 효율성 지표로 대체 가능

**구현**:
```python
# Shot Quality Score 생성
shot_quality = shots_on_target / total_shots
conversion = goals / shots_on_target

# xG 대신 사용
if shot_quality > 0.4 and conversion > 0.3:
    # High quality attack
```

### 필요시 (Phase 2): 수동 CSV
**시나리오**: xG가 정말 필요하다고 판단되면
- 주 1회 Understat CSV 다운로드
- 5분 투자
- 완전 무료

### 장기 (Phase 3): 유료 API
**시나리오**: 수익 발생 후
- API-Football $15/월 구독
- 완전 자동화
- 모든 리그 커버

---

## 실제 사용 예시

### 현재 데이터로 판단
```sql
SELECT
    m.home_team_id,
    m.away_team_id,
    ms_h.shots_on_target * 1.0 / ms_h.shots as home_shot_quality,
    ms_a.shots_on_target * 1.0 / ms_a.shots as away_shot_quality,
    oc.home_win as odds
FROM matches m
JOIN match_stats ms_h ON m.match_id = ms_h.match_id AND ms_h.is_home = 1
JOIN match_stats ms_a ON m.match_id = ms_a.match_id AND ms_a.is_home = 0
JOIN odds_closing oc ON m.match_id = oc.match_id
WHERE m.league = 'EPL'
```

### LLM 판단 레이어
```python
context = {
    "home_shot_quality": 0.42,
    "away_shot_quality": 0.31,
    "home_shots": 15,
    "away_shots": 8,
    "odds": {"home": 1.85, "draw": 3.60, "away": 4.20}
}

# LLM이 xG 없이도 판단 가능
prompt = f"""
홈팀은 15슛 중 42%가 타겟 (6.3개),
어웨이는 8슛 중 31%가 타겟 (2.5개).
홈팀이 공격력이 훨씬 우세함.
배당은 홈 1.85로 overvalued.
"""
```

---

## 결론

**xG 데이터는 무료로 자동 수집 불가능합니다.**

**하지만 우리 시스템에는 필요 없습니다**:
- ✅ 슛 통계로 충분
- ✅ 배당 데이터로 시장 의견 반영
- ✅ LLM이 맥락 판단

**권장**: **xG 없이 시작** → 필요하면 수동 CSV → 수익 나면 유료 API
