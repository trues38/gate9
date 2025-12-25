# 완전 자동화 설정 가이드

## 매일 자동으로 최신 데이터 유지하기

### 방법 1: 수동 실행 (추천 - 처음 사용자)

매일 오후에 한 번만:
```bash
./daily_betting_report.sh
```

이게 자동으로:
1. 어제 경기 결과 Neo4j에 추가 (최신 패턴 유지)
2. 내일 경기 스케줄 가져오기
3. ESPN 프리뷰 수집
4. 컨텍스트 계산
5. 패턴 기반 예측 생성
6. 통합 보고서 작성

**실행 시간**: 약 20초

---

### 방법 2: Cron으로 자동화 (고급 사용자)

#### 매일 오후 3시 자동 실행 설정

```bash
# crontab 편집
crontab -e

# 다음 줄 추가 (매일 15:00에 실행)
0 15 * * * cd /Users/js/g9/nba_data/state_graph && ./daily_betting_report.sh > /tmp/nba_report.log 2>&1
```

#### 경기 시작 4시간 전에 한 번 더 실행 (심판 정보 업데이트)

대부분 경기가 저녁 7시-10시 시작이므로:

```bash
# 오후 3시: 첫 번째 분석
0 15 * * * cd /Users/js/g9/nba_data/state_graph && ./daily_betting_report.sh > /tmp/nba_report_pm.log 2>&1

# 저녁 6시: 심판 정보 업데이트된 최종 분석
0 18 * * * cd /Users/js/g9/nba_data/state_graph && ./daily_betting_report.sh > /tmp/nba_report_evening.log 2>&1
```

---

### 방법 3: macOS Automator (GUI)

1. **Automator 앱 열기**
2. **"Calendar Alarm" 선택**
3. **"Run Shell Script" 추가**:
   ```bash
   cd /Users/js/g9/nba_data/state_graph
   ./daily_betting_report.sh
   ```
4. **저장** → 매일 오후 3시로 설정

---

## 데이터 최신성 보장

### 자동 업데이트 흐름

```
Day 1 (12/25):
  09:00 - 어제(12/24) 경기 결과들이 Neo4j에 추가됨
  15:00 - 내일(12/26) 경기 분석 생성
          → 12/24까지의 최신 패턴 반영됨

Day 2 (12/26):
  09:00 - 어제(12/25) 경기 결과들이 Neo4j에 추가됨
  15:00 - 내일(12/27) 경기 분석 생성
          → 12/25까지의 최신 패턴 반영됨
```

### Neo4j 데이터 증가 추세

- 현재: 927게임
- 1개월 후: ~1,300게임 (매일 12게임 × 30일)
- 시즌 종료: ~2,200게임 (현재 + 82게임×30팀/2 = 1,230경기 추가)

**성능 영향**: 없음. Neo4j는 10,000+ 게임도 빠르게 쿼리 가능.

---

## 수동 업데이트가 필요한 경우

### 며칠 놓쳤을 때

```bash
# 특정 날짜 범위 업데이트 (예: 12/20-12/24)
python3 update_date_range.py 20251220 20251224
```

*(이 스크립트는 필요시 만들면 됨 - 현재는 매일 자동 실행하면 불필요)*

---

## 확인 방법

### Neo4j에 최신 데이터 있는지 확인

```bash
# Neo4j Browser에서 실행
MATCH (g:GameState)
RETURN g.date
ORDER BY g.date DESC
LIMIT 5
```

→ 어제 날짜가 나오면 정상

### 패턴이 최신인지 확인

```bash
# BOS의 최근 휴식일별 성적 확인
MATCH (g:GameState {home_team: 'BOS'})
WHERE g.date >= date('2024-12-01')
RETURN g.home_rest_days, count(*) AS games,
       round(sum(CASE WHEN g.home_win THEN 1 ELSE 0 END) * 100.0 / count(*), 1) AS win_pct
ORDER BY g.home_rest_days
```

---

## 문제 해결

### Neo4j 연결 실패

```bash
# Docker 컨테이너 확인
docker ps | grep neo4j

# 없으면 시작
docker start neo4j-nba
```

### 어제 경기가 없다고 나올 때

- 정상: 월요일(일요일 경기 없음)이나 올스타 브레이크 기간
- 경기가 있는데 안 가져와지면: ESPN API 확인 필요

### 패턴이 이상할 때

- Neo4j 데이터 정합성 확인
- 휴식일 계산 로직 디버깅: `calculate_game_context.py` 로그 확인

---

## 요약

✅ **최신성 유지 = 매일 어제 경기만 추가**
✅ **패턴은 자동 업데이트 (Neo4j가 실시간 계산)**
✅ **한 번 설정하면 계속 돌아감**

가장 간단한 방법:
```bash
# 매일 오후에 한 번만
./daily_betting_report.sh
```

이게 전부입니다!
