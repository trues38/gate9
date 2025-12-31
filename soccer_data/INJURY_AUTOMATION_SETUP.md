# ⚽ 축구 부상 데이터 자동화 시스템

**날짜**: 2025-12-29
**목표**: Transfermarkt에서 부상 데이터를 자동으로 수집하고 n8n으로 스케줄링

---

## 🎯 시스템 구조

```
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│              │      │              │      │              │
│   n8n        │─────▶│  Flask API   │─────▶│ Transfermarkt│
│  (Schedule)  │      │  (Port 8002) │      │  (Scraping)  │
│              │      │              │      │              │
└──────────────┘      └──────────────┘      └──────────────┘
       │                     │
       │                     ▼
       │              ┌──────────────┐
       │              │              │
       └─────────────▶│ JSON Files   │
                      │ (processed/) │
                      │              │
                      └──────────────┘
```

### 구성 요소

1. **injury_scraper.py** - Transfermarkt 스크래핑 엔진
2. **injury_api.py** - Flask REST API 서버 (Port 8002)
3. **n8n_injury_collection_workflow.json** - n8n 워크플로우
4. **Docker Compose** - 컨테이너 배포

---

## 📋 수집 데이터

### 리그
- ✅ EPL (Premier League)
- ✅ La Liga
- ✅ Bundesliga
- ✅ Serie A
- ✅ Ligue 1

### 데이터 필드

```json
{
  "league": "EPL",
  "team": "Manchester City",
  "player": "Erling Haaland",
  "position": "Centre-Forward",
  "status": "OUT",                    // OUT | DOUBTFUL
  "injury_type": "Ankle injury",
  "expected_return": "Jan 15, 2024",
  "impact": "CRITICAL",                // CRITICAL | HIGH | MEDIUM
  "source": "Transfermarkt",
  "date": "2025-12-29"
}
```

### 영향도 판단 기준

**CRITICAL:**
- Forward, Striker, Winger
- Attacking Midfielder
- 주전 골잡이

**HIGH:**
- Central Midfielder
- Central Defender
- Goalkeeper

**MEDIUM:**
- Full-back, Wing-back
- 보조 역할

---

## 🚀 로컬 테스트 (1분)

### Step 1: 스크래핑 테스트

```bash
cd /Users/js/g9/soccer_data

# 의존성 설치
pip3 install requests beautifulsoup4 lxml flask

# 스크래핑 실행
python3 injury_scraper.py
```

**예상 출력:**
```
⚽ Soccer Injury Data Scraper - Transfermarkt
============================================================
📥 Scraping EPL...
   ✅ Found 23 injuries
📥 Scraping La_liga...
   ✅ Found 18 injuries
📥 Scraping Bundesliga...
   ✅ Found 15 injuries
📥 Scraping Serie_A...
   ✅ Found 20 injuries
📥 Scraping Ligue_1...
   ✅ Found 16 injuries

💾 Saved 92 injuries to processed/injury_data.json

📊 Injury Summary
============================================================
Total Injuries: 92

📍 By League:
   EPL             23 injuries
   La_liga         18 injuries
   Bundesliga      15 injuries
   Serie_A         20 injuries
   Ligue_1         16 injuries

🚨 By Status:
   OUT             78
   DOUBTFUL        14

💥 By Impact:
   CRITICAL        25
   HIGH            40
   MEDIUM          27

🔥 Critical Players OUT (25):
   Erling Haaland                 (Manchester City, EPL) - OUT
   Mohamed Salah                  (Liverpool, EPL) - DOUBTFUL
   ...

✅ Scraping complete!
```

### Step 2: API 서버 테스트

```bash
# 터미널 1: API 서버 실행
python3 injury_api.py

# 터미널 2: API 테스트
# Health check
curl http://localhost:8002/health

# 데이터 수집
curl -X POST http://localhost:8002/collect/injuries \
  -H "Content-Type: application/json" \
  -d '{"save": true}'

# 최신 데이터 조회
curl http://localhost:8002/injuries/latest

# Critical만 조회
curl http://localhost:8002/injuries/critical

# 특정 리그만 조회
curl "http://localhost:8002/injuries/latest?league=EPL"
```

---

## 🐳 VPS 배포 (5분)

### Step 1: 파일 업로드

```bash
# 로컬에서
cd /Users/js/g9/soccer_data

# VPS로 전송
scp injury_scraper.py root@YOUR_VPS_IP:/root/soccer_data/
scp injury_api.py root@YOUR_VPS_IP:/root/soccer_data/
scp requirements-injury.txt root@YOUR_VPS_IP:/root/soccer_data/
scp Dockerfile.injury root@YOUR_VPS_IP:/root/soccer_data/
scp docker-compose-injury.yml root@YOUR_VPS_IP:/root/soccer_data/
scp n8n_injury_collection_workflow.json root@YOUR_VPS_IP:/root/soccer_data/
```

### Step 2: Docker 네트워크 설정 (VPS)

```bash
# VPS 접속
ssh root@YOUR_VPS_IP

cd /root/soccer_data

# g9-network 존재 확인
docker network ls | grep g9-network

# 없으면 생성
docker network create g9-network
```

### Step 3: 컨테이너 실행

```bash
# 빌드 및 실행
docker-compose -f docker-compose-injury.yml up -d --build

# 로그 확인
docker logs -f soccer-injury-api

# Health check
curl http://localhost:8002/health
```

**예상 출력:**
```json
{
  "status": "healthy",
  "service": "soccer-injury-api",
  "timestamp": "2025-12-29T21:00:00"
}
```

### Step 4: n8n에 워크플로우 추가

```bash
# n8n 웹 UI 접속
http://YOUR_VPS_IP:5678

# 로그인 후:
1. 좌측 "Workflows" 클릭
2. "+ New workflow" 클릭
3. 우측 상단 "..." → "Import from file" 클릭
4. n8n_injury_collection_workflow.json 업로드
5. "Save" 클릭
6. "Activate" 토글 ON
```

### Step 5: 수동 테스트

```bash
# n8n UI에서:
1. "Execute Workflow" 클릭
2. 결과 확인 (약 30-60초 소요)

# 또는 API 직접 호출:
curl -X POST http://localhost:8002/collect/injuries \
  -H "Content-Type: application/json" \
  -d '{"save": true}'
```

---

## ⏰ 스케줄링

### n8n 스케줄 (기본)

**현재 설정:** 매일 저녁 9시 (21:00)

```
Cron: 0 21 * * *
```

**변경 방법:**
1. n8n UI에서 "Daily at 9 PM" 노드 클릭
2. "Cron Expression" 수정
3. Save

**추천 스케줄:**

| 시간 | Cron | 용도 |
|------|------|------|
| 09:00 | `0 9 * * *` | 아침 업데이트 |
| 21:00 | `0 21 * * *` | 저녁 업데이트 (추천) |
| 09:00, 21:00 | `0 9,21 * * *` | 하루 2회 |

### Cron 대안 (시스템 crontab)

```bash
# VPS에서
crontab -e

# 추가:
0 21 * * * curl -X POST http://localhost:8002/collect/injuries -H "Content-Type: application/json" -d '{"save": true}' >> /root/logs/injury_collection.log 2>&1
```

---

## 📊 데이터 활용

### 1. 예측 모델에 통합

```python
import json

# 부상 데이터 로드
with open('processed/injury_data.json', 'r') as f:
    injuries = json.load(f)

# 특정 경기의 부상 영향 확인
def get_injuries_for_match(home_team, away_team):
    home_injuries = [i for i in injuries if i['team'] == home_team and i['impact'] == 'CRITICAL']
    away_injuries = [i for i in injuries if i['team'] == away_team and i['impact'] == 'CRITICAL']

    return {
        "home_out": len([i for i in home_injuries if i['status'] == 'OUT']),
        "away_out": len([i for i in away_injuries if i['status'] == 'OUT']),
        "home_doubtful": len([i for i in home_injuries if i['status'] == 'DOUBTFUL']),
        "away_doubtful": len([i for i in away_injuries if i['status'] == 'DOUBTFUL'])
    }

# 예시
match_injuries = get_injuries_for_match("Manchester City", "Liverpool")
print(match_injuries)
# {"home_out": 1, "away_out": 0, "home_doubtful": 0, "away_doubtful": 1}
```

### 2. 확률 조정

```python
def adjust_for_injuries(p_h, p_d, p_a, home_team, away_team, injuries):
    """부상 영향 반영"""
    home_critical = len([i for i in injuries if i['team'] == home_team and i['impact'] == 'CRITICAL' and i['status'] == 'OUT'])
    away_critical = len([i for i in injuries if i['team'] == away_team and i['impact'] == 'CRITICAL' and i['status'] == 'OUT'])

    # 각 Critical 부상당 -5% 승률
    adjustment_per_injury = 0.05

    p_h -= home_critical * adjustment_per_injury
    p_a -= away_critical * adjustment_per_injury

    # 무승부로 확률 재분배
    p_d += (home_critical + away_critical) * adjustment_per_injury

    # 정규화
    total = p_h + p_d + p_a
    return p_h/total, p_d/total, p_a/total
```

---

## 🔍 모니터링

### API 헬스체크

```bash
# Health check
curl http://localhost:8002/health

# 최근 수집 통계
curl http://localhost:8002/injuries/latest | jq '.summary'
```

### Docker 로그

```bash
# 실시간 로그
docker logs -f soccer-injury-api

# 최근 100줄
docker logs --tail 100 soccer-injury-api
```

### n8n 실행 기록

```
n8n UI → Executions → "Soccer Injury Auto Collection" 확인
```

---

## 🛠️ 문제 해결

### 1. Transfermarkt 접근 차단

**증상:** HTTP 403 또는 빈 결과

**해결:**
```python
# injury_scraper.py에서 User-Agent 변경
self.headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

# Rate limiting 추가 (이미 구현됨)
time.sleep(2)  # 리그당 2초 대기
```

### 2. API 타임아웃

**증상:** n8n에서 "Request timeout"

**해결:**
```json
// n8n workflow에서 timeout 증가 (이미 60초로 설정됨)
"options": {
  "timeout": 120000  // 120초
}
```

### 3. 컨테이너 재시작

```bash
docker-compose -f docker-compose-injury.yml restart
```

---

## 📈 다음 단계

### 즉시 실행 가능

1. ✅ **로컬 테스트** (지금 가능)
   ```bash
   python3 injury_scraper.py
   ```

2. ✅ **VPS 배포** (5분)
   - Docker 빌드
   - n8n 워크플로우 임포트
   - 스케줄 활성화

3. ✅ **예측 모델 통합** (30분)
   - `backtest_v4_with_graph.py`에 부상 조정 추가
   - ROI 개선 측정

### 확장 기능 (선택사항)

1. **Slack/Discord 알림**
   - Critical 부상 발생시 알림
   - n8n에 알림 노드 추가

2. **히스토리 추적**
   - 부상 기록 DB 저장
   - 복귀 후 퍼포먼스 분석

3. **다른 소스 추가**
   - ESPN API
   - Official team websites

---

## ✅ 체크리스트

### 로컬 테스트
- [ ] injury_scraper.py 실행 성공
- [ ] injury_api.py 실행 성공
- [ ] processed/injury_data.json 생성 확인
- [ ] API 엔드포인트 테스트 완료

### VPS 배포
- [ ] 파일 업로드 완료
- [ ] Docker 빌드 성공
- [ ] 컨테이너 실행 중
- [ ] Health check 통과
- [ ] n8n 워크플로우 임포트 완료
- [ ] n8n 워크플로우 활성화

### 자동화
- [ ] 스케줄 설정 (매일 21:00)
- [ ] 첫 자동 실행 성공
- [ ] 로그 확인

---

## 📞 지원

**문제 발생시:**
1. 로그 확인: `docker logs soccer-injury-api`
2. Health check: `curl http://localhost:8002/health`
3. 수동 실행: `python3 injury_scraper.py`

**예상 작업 시간:**
- 로컬 테스트: 1분
- VPS 배포: 5분
- n8n 설정: 2분
- **총합: 약 10분** ✅

---

**작성일**: 2025-12-29
**작성자**: Soccer Data Automation Team
**상태**: 테스트 준비 완료 ✅
