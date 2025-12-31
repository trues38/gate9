# NBA v2.0 작업 분담

## 자동 수집/계산 (AI) vs 수동 입력 (사용자)

---

## 1️⃣ 자동 수집/계산 (AI가 할 수 있는 것)

### A. Coach 노드 - 100% 자동 계산

**데이터 소스**: PlayerBoxScore (25-26 시즌)

```python
# 자동 계산 항목:
- rotation_depth          # 평균 20분+ 선수 수
- avg_starter_minutes     # 주전(30분+) 평균 출전
- avg_bench_minutes       # 벤치 평균 출전
- tempo                   # 팀 템포 (possessions/game)
- pace_rank               # 리그 순위
- games_coached           # 코칭 경기 수
- win_pct                 # 승률
```

**계산 방법**:
```
1. PlayerBoxScore에서 팀별로 경기 그룹화
2. 각 경기마다 20분+ 선수 수 → rotation_depth
3. 30분+ 선수 평균 출전 → avg_starter_minutes
4. 20분 미만 선수 평균 → avg_bench_minutes
5. 팀 페이스 통계 → tempo (ESPN API에서)
```

**스크립트**: `calculate_coach_stats.py` (구현 예정)

---

### B. Player 노드 - 80% 자동 계산

**데이터 소스**: PlayerBoxScore (25-26 시즌)

```python
# 자동 계산 항목:
- avg_plus_minus          # 평균 +/-
- impact_percentile       # 리그 내 순위
- avg_minutes             # 평균 출전
- games_played            # 출전 경기
- games_missed            # 결장 경기
- injury_prone            # 결장 비율

# 스탯 기반:
- ppg                     # 평균 득점
- rpg                     # 평균 리바운드
- apg                     # 평균 어시스트
- oreb_pg                 # 평균 오펜스 리바운드
- spg                     # 평균 스틸
- bpg                     # 평균 블락

# 백투백 체력:
- stamina                 # 백투백 +/- 하락폭으로 계산
                          # stamina = 1 - (abs(b2b_drop) / 10)

# 스타일 태그 (자동 분류):
- style_tags: []
  * oreb_pg > 3.0 → "oreb-specialist"
  * bpg > 1.5 → "rim-protector"
  * apg > 6.0 → "playmaker"
  * spg > 1.5 → "perimeter-defender"
  * ppg > 20 → "primary-scorer"
  * minutes > 30 → "workhorse"
```

**계산 방법**:
```
1. PlayerBoxScore에서 선수별 집계
2. avg(), count() 등으로 평균 계산
3. 백투백 경기 찾아서 +/- 변화 계산
4. 스탯 기준으로 style_tags 자동 부여
```

**스크립트**: `expand_player_attributes.py` (구현 예정)

---

### C. GameContext 노드 - 100% 자동 생성

**데이터 소스**: ESPN API + Neo4j 기존 데이터

```python
# 자동 계산/수집 항목:
- date                    # 경기 날짜
- home_team, away_team    # 팀
- home_rest_days          # Neo4j에서 계산 (이미 구현됨)
- away_rest_days
- home_back_to_back       # rest_days == 0
- away_back_to_back
- referee_home_bias       # 심판별 홈 편향 (역사적 통계)
- home_injuries: []       # ESPN 프리뷰에서
- away_injuries: []
```

**이미 구현됨**: `calculate_game_context.py`, `fetch_game_preview.py`

---

## 2️⃣ 수동 입력 (사용자가 제공)

### A. Lineup 노드 - 100% 수동 입력

**왜 수동인가?**
- NBA Stats API 불안정 (타임아웃, rate limit)
- 정확한 라인업 사용 빈도는 시청 필요
- 핵심 3-5개만 입력하면 충분

**필요한 정보**:

```json
{
  "HOU": {
    "coach": "Ime Udoka",
    "season": "2025-26",
    "lineups": [
      {
        "name": "Starting 5",
        "players": [
          "Kevin Durant",
          "Alperen Sengun",
          "Klay Thompson",
          "Fred VanVleet",
          "Dillon Brooks"
        ],
        "usage_pct": 35,
        "style": "balanced",
        "tempo_boost": 1.0,
        "defense_rating": 0.9,
        "offense_rating": 1.1,
        "notes": "주력 라인업, 밸런스형"
      },
      {
        "name": "Big Lineup",
        "players": [
          "Kevin Durant",
          "Alperen Sengun",
          "Steven Adams",
          "Fred VanVleet",
          "Dillon Brooks"
        ],
        "usage_pct": 15,
        "style": "defensive",
        "tempo_boost": 0.95,
        "defense_rating": 1.2,
        "offense_rating": 0.9,
        "notes": "수비 중심, Adams 스크린 활용"
      },
      {
        "name": "Small Ball",
        "players": [
          "Kevin Durant",
          "Alperen Sengun",
          "Klay Thompson",
          "Fred VanVleet",
          "Jae'Sean Tate"
        ],
        "usage_pct": 10,
        "style": "uptempo",
        "tempo_boost": 1.10,
        "defense_rating": 0.8,
        "offense_rating": 1.15,
        "notes": "스피드 중심, 작은 팀 상대"
      }
    ]
  }
}
```

**필수 입력 항목**:
- `name`: 라인업 이름 (예: "Starting 5", "Big Lineup")
- `players`: [5명] 선수 리스트
- `usage_pct`: 전체 시간 중 사용 비율 (%)
- `style`: "balanced", "defensive", "offensive", "uptempo" 등
- `tempo_boost`: 템포 조정 (1.0 = 중립, >1.0 = 빠름, <1.0 = 느림)
- `defense_rating`: 수비 강도 (1.0 = 보통, >1.0 = 강함)
- `offense_rating`: 공격 강도 (1.0 = 보통, >1.0 = 강함)
- `notes`: 메모

**템플릿 파일 제공**: `lineups_template.json`

---

### B. 선택적 수동 보정

사용자가 원하면 자동 계산된 값을 수동으로 보정 가능:

```json
{
  "player_overrides": {
    "Steven Adams": {
      "style_tags": ["rim-protector", "screen-setter", "oreb-specialist"],
      "notes": "스크린 작업이 핵심, 수치로 안 나오는 기여도 높음"
    },
    "Draymond Green": {
      "impact_percentile": 0.85,
      "notes": "수비 IQ가 높아 +/-보다 실제 영향력 큼"
    }
  }
}
```

**선택 사항**: 자동 계산으로 충분하면 생략 가능

---

## 3️⃣ 포기하는 것 (명시)

### A. FrontOffice 전략
- **이유**: 정성적, 자동화 불가
- **ROI**: 낮음 (실제 승부 예측에 미미)

### B. 모든 Lineup 조합
- **이유**: NBA API 불안정, 데이터 수집 어려움
- **대안**: 핵심 3-5개만 수동 입력

### C. 선수 간 정밀 시너지
- **이유**: NBA Stats API 필요, 복잡도 높음
- **대안**: +/- 비교로 근사치 계산

### D. 코치 철학/성향
- **이유**: 주관적
- **대안**: 통계로 유추 가능한 것만 (템포, 로테이션)

---

## 4️⃣ 작업 순서

### Phase 1: 자동 계산 (AI) - 2일
```
Day 1:
  ✅ calculate_coach_stats.py 작성
  ✅ 모든 팀의 Coach 노드 자동 생성
  ✅ Neo4j에 임포트

Day 2:
  ✅ expand_player_attributes.py 작성
  ✅ 모든 선수의 속성 확장 (impact, style, stamina)
  ✅ Neo4j 업데이트
```

### Phase 2: 수동 입력 준비 (AI) - 1일
```
Day 3:
  ✅ lineups_template.json 생성 (30개 팀 빈 템플릿)
  ✅ lineups_example.json 생성 (HOU, NYK 예시)
  ✅ import_lineups.py 작성 (JSON → Neo4j)
```

### Phase 3: 수동 입력 (사용자) - 시간 있을 때
```
사용자 작업:
  ⏳ lineups.json 작성 (팀당 3-5개 라인업)
  ⏳ 핵심 팀부터 입력 (HOU, BOS, NYK, LAL 등)
  ⏳ 나머지는 시간 있을 때
```

### Phase 4: 동적 엔진 (AI) - 1일
```
Day 4:
  ✅ calculate_team_strength.py 작성
  ✅ 실시간 팀 강도 계산 함수
  ✅ 테스트 (Adams 부상 시뮬레이션)
```

### Phase 5: 통합 (AI) - 1일
```
Day 5:
  ✅ daily_betting_report.sh v2.0 업데이트
  ✅ 일일 보고서에 v2.0 예측 통합
  ✅ v1.1 vs v2.0 비교 출력
```

---

## 5️⃣ 사용자 작업 가이드

### 우선순위 1: 핵심 팀 (10개)
```
동부: BOS, NYK, MIL, PHI, CLE
서부: HOU, LAL, DEN, GSW, OKC
```

### 우선순위 2: 플레이오프 경쟁팀 (10개)
```
동부: MIA, ORL, IND, ATL, CHI
서부: PHX, MIN, DAL, SAC, NOP
```

### 우선순위 3: 나머지 (10개)
```
필요하면 추가
```

### 작업 시간 예상
- 팀당 10분 (라인업 3-5개 입력)
- 20개 팀 = 약 3-4시간
- 한 번에 다 하지 않아도 됨 (점진적 추가 가능)

---

## 6️⃣ 자동 vs 수동 비율

```
📊 전체 데이터 구성:

Coach: 100% 자동 ✅
  - 30개 팀 × 10개 속성
  - 완전 자동 계산

Player: 95% 자동 ✅
  - ~450명 × 15개 속성
  - 대부분 자동 계산
  - 5%만 선택적 수동 보정

Lineup: 100% 수동 ⏳
  - 30개 팀 × 3-5개 라인업
  - 핵심만 입력
  - 점진적 추가 가능

GameContext: 100% 자동 ✅
  - 매일 자동 생성
  - 이미 구현됨

---
전체: ~85% 자동, ~15% 수동
```

---

## 7️⃣ 즉시 시작 가능

### AI가 지금 바로 할 수 있는 것:
1. Coach 자동 계산 스크립트 작성
2. Player 속성 확장 스크립트 작성
3. 템플릿 JSON 파일 생성
4. 임포터 스크립트 작성
5. 동적 계산 엔진 작성

### 사용자 대기 없이 진행:
```
Day 1-2: 자동 계산 구현 + 실행
Day 3: 템플릿 제공
→ 사용자에게 lineups.json 전달

사용자가 입력하는 동안:
Day 4-5: 동적 엔진 + 통합 구현

사용자 완료 후:
→ import_lineups.py 실행
→ v2.0 시스템 가동
```

---

## 8️⃣ 요약

| 항목 | 담당 | 비율 | 상태 |
|------|------|------|------|
| Coach 노드 | AI 자동 | 100% | 구현 대기 |
| Player 확장 | AI 자동 | 95% | 구현 대기 |
| Lineup 입력 | 사용자 | 100% | 템플릿 제공 예정 |
| GameContext | AI 자동 | 100% | ✅ 완료 |
| 동적 엔진 | AI 자동 | 100% | 구현 대기 |

**결론**: AI가 85% 자동 구축, 사용자는 핵심 라인업 15%만 입력하면 v2.0 완성!
