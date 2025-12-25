# NBA State Graph - Phase 1 Complete

## 🎯 프로젝트 목적

승패 예측이 아닌 **"상태(State) 중심 데이터 구조"** 구축
- 특정 날짜의 NBA 경기/팀/선수 **상태 스냅샷** 생성
- Back-to-back, 부상자, 심판 등 **맥락 정보** 통합
- Graph DB 이전 가능한 구조 설계

---

## 📊 현재 수집 데이터

### 2024-25 시즌
- **2024년 10-12월:** 수집 중
- **2025년 12월:** 145경기 완료

### 2023-24 시즌 (비교용)
- **2024년 10-12월:** 192경기 완료

---

## 🗂️ 디렉토리 구조

```
state_graph/
├── docs/
│   ├── ESPN_API_ENDPOINTS.md      # ESPN API 문서
│   └── SUPABASE_SCHEMA.sql        # DB 스키마
│
├── raw/                            # 원본 데이터
│   ├── 20241201_scoreboard.json
│   ├── 20241201_game_*.json
│   └── 20241201_roster_*.json
│
├── snapshots/                      # State Snapshots
│   └── 20241201_snapshots.json
│
├── december_2025_results.csv       # 경기 결과
│
├── fetch_raw.py                    # 데이터 수집
├── build_snapshot.py               # 스냅샷 생성
├── analyze_state_impact.py         # 상태-결과 분석
├── deep_analysis.py                # 심화 분석
├── pattern_discovery.py            # 패턴 발견
├── season_analysis.py              # 시즌 전체 분석
└── year_comparison.py              # 작년 vs 올해 비교
```

---

## 🚀 사용법

### 1. 데이터 수집

```bash
# 12월 전체 수집
python fetch_raw.py --date 20251201 --days 31

# 특정 기간 수집
python fetch_raw.py --date 20251201 --days 7
```

### 2. 스냅샷 생성

```bash
python build_snapshot.py --date 20251201 --days 31
```

### 3. 분석 실행

```bash
# 기본 분석 (휴식일, 부상, 심판)
python analyze_state_impact.py

# 심화 분석 (팀별, 조합)
python deep_analysis.py

# 패턴 발견 (업셋, 클러치, 리벤지)
python pattern_discovery.py

# 시즌 전체 분석 (월별 트렌드)
python season_analysis.py

# 작년 vs 올해 비교
python year_comparison.py
```

---

## 💡 핵심 발견 (2025-12)

### 1. 휴식일 영향
```
Back-to-back: 47.4% 승률
2일 휴식:     69.6% 승률 🔥 (최강!)
```

### 2. Back-to-back 극과 극
```
강철 멘탈: SA (3-0, 100%), BOS, PHI, DET, DAL
무너지는: UTAH, TOR, MIA, HOU, OKC (0-2, 0%)
```

### 3. 심판 효과
```
James Williams: 75.0% 홈 승률
Nick Buchert:   25.0% 홈 승률 (원정 유리!)
```

### 4. 홈코트 무적/저주
```
무적: DET, HOU, SA, DAL (100% 홈 승률)
저주: ATL, TOR (16.7% 홈 승률)
```

### 5. 원정 강팀
```
DEN, CHI: 80% 원정 승률
SA: 75% 원정 승률
```

---

## 📈 배팅 전략 (즉시 적용 가능)

1. **SA의 B2B 경기 → 무조건 SA 배팅**
2. **UTAH/TOR/MIA의 B2B → 상대팀 배팅**
3. **휴식일 차이 3일+ → 더 쉰 팀 배팅**
4. **2일 휴식 팀 → 배팅 (70% 승률)**
5. **TOR+Sean Wright 조합 → 상대팀**
6. **ATL/TOR 홈 경기 → 상대팀**
7. **DEN/CHI 원정 경기 → 배팅**
8. **크리스마스 주간 → 홈팀 배팅 (63%)**

---

## 🔮 Phase 2 계획

1. **2025년 10-11월 수집** (샘플 확대)
2. **전체 시즌 패턴 분석** (월별 트렌드)
3. **작년 vs 올해 비교** (시스템 변화 감지)
4. **팀별 폼 지수 계산**
5. **선수 개별 영향도 분리**
6. **Neo4j Graph DB 이전**

---

## 📝 State Snapshot 예시

```json
{
  "date": "2025-12-16",
  "game_id": "401810220",
  "matchup": "PHX @ MIN",
  "home_team": {
    "team_id": "MIN",
    "record": "15-14",
    "rest_days": 1,
    "injuries": ["Mike Conley - Day-To-Day"],
    "lineup": ["Anthony Edwards", "Rudy Gobert", ...]
  },
  "away_team": {
    "team_id": "PHX",
    "record": "15-14",
    "rest_days": 2,
    "injuries": ["Kevin Durant - Out"],
    "lineup": ["Devin Booker", "Bradley Beal", ...]
  },
  "referees": ["Scott Foster", "Tony Brothers", "..."],
  "state_notes": ["Kevin Durant - Out"]
}
```

---

## 🎉 성과

- **337경기** State Snapshot 생성 (2024-25)
- **192경기** 분석 완료 (2024년 12월)
- **145경기** 분석 완료 (2025년 12월)
- **유의미한 패턴 다수 발견**
- **즉시 활용 가능한 배팅 전략 도출**

---

## 📚 참고

- ESPN API: `http://site.api.espn.com/apis/site/v2/sports/basketball/nba/`
- 데이터 기간: 2024-10-22 (시즌 개막) ~ 현재
- 업데이트 주기: 일일 (자동화 예정)

---

**Made with ❤️ by State Graph Engine**
