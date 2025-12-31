# 🎯 G9 운영 대시보드 - 완전 가이드

> **API 500회 관리 + NBA/경제 수집 상태 + Neo4j 추적 + 크론 모니터링**

---

## 🚀 빠른 시작

```bash
cd /Users/js/g9/nba_data/odds_report_engine/monitoring

# VPS에 배포
chmod +x deploy_monitoring.sh
./deploy_monitoring.sh

# 접속
# Grafana: http://141.164.35.214:3000 (admin / g9admin2025)
# Prometheus: http://141.164.35.214:9090
```

---

## 📊 대시보드 구성

### 🎲 API 사용량 모니터링 (월 500회 제한)

**Odds API**:
- 🟢 0-400회: 안전
- 🟡 400-450회: 경고
- 🔴 450-500회: 위험

**Twitter API**:
- 🟢 0-400회: 안전
- 🟡 400-450회: 경고
- 🔴 450-500회: 위험

### 🏀 수집 상태

- **NBA 경기 수집**: 오늘 수집된 경기 수
- **경제 이벤트 수집**: 오늘 수집된 이벤트 수
- **Odds 스냅샷**: 실시간 배당 스냅샷 수
- **Twitter 이벤트**: 도메인별 트위터 이벤트 수

### 🧠 Neo4j 모니터링

- **노드 수**: NBA / 경제 데이터베이스별
- **노드 증가율**: 시간당 증가량
- **데이터 누적**: 실시간 그래프 RAG 성장 추적

### ⏱ 작업 헬스 체크

- **NBA 수집**: 마지막 실행 시간 (10분 초과 시 알림)
- **경제 수집**: 마지막 실행 시간 (10분 초과 시 알림)
- **리포트 생성**: 마지막 실행 시간

### 🖥 VPS 시스템

- **메모리 사용률**: 90% 초과 시 알림
- **디스크 사용률**: 90% 초과 시 알림
- **CPU 사용률**: 80% 초과 시 알림

---

## 🔧 파이프라인 통합

### 1. API 호출 기록

```python
import requests

# Odds API 호출 후
requests.get("http://localhost:9101/api/record_api_call/odds_api")

# Twitter API 호출 후
requests.get("http://localhost:9101/api/record_api_call/twitter_api")
```

### 2. Odds 스냅샷 기록

```python
# 각 경기 스냅샷 수집 후
requests.get(f"http://localhost:9101/api/record_odds_snapshot/{game_id}")
```

### 3. Twitter 이벤트 기록

```python
# NBA 트윗 수집 후
requests.get("http://localhost:9101/api/record_twitter_event/nba")

# 경제 트윗 수집 후
requests.get("http://localhost:9101/api/record_twitter_event/economy")
```

### 4. 크론/작업 실행 기록

```python
# NBA 수집 크론 시작 시
requests.get("http://localhost:9101/api/record_job_heartbeat/nba_collector")

# 경제 수집 크론 시작 시
requests.get("http://localhost:9101/api/record_job_heartbeat/economic_collector")

# 리포트 생성 시작 시
requests.get("http://localhost:9101/api/record_job_heartbeat/report_generator")
```

### 5. 수집 통계 업데이트

```python
# NBA 경기 수 업데이트
requests.get(f"http://localhost:9101/api/set_nba_games/{game_count}")

# 경제 이벤트 수 업데이트
requests.get(f"http://localhost:9101/api/set_econ_events/{event_count}")
```

---

## 📝 실전 예시: NBA 수집 파이프라인

```python
import requests
from datetime import datetime

class NBACollectorWithMonitoring:
    def __init__(self):
        self.metrics_url = "http://localhost:9101"

    def collect_today_games(self):
        # 크론 시작 기록
        requests.get(f"{self.metrics_url}/api/record_job_heartbeat/nba_collector")

        # Odds API 호출
        odds_data = self.fetch_odds()
        requests.get(f"{self.metrics_url}/api/record_api_call/odds_api")

        # 각 경기 스냅샷 기록
        for game in odds_data:
            game_id = game["id"]
            requests.get(f"{self.metrics_url}/api/record_odds_snapshot/{game_id}")

        # Twitter API 호출
        tweets = self.fetch_nba_tweets()
        requests.get(f"{self.metrics_url}/api/record_api_call/twitter_api")

        # Twitter 이벤트 기록
        for tweet in tweets:
            requests.get(f"{self.metrics_url}/api/record_twitter_event/nba")

        # NBA 경기 수 업데이트
        requests.get(f"{self.metrics_url}/api/set_nba_games/{len(odds_data)}")

        print(f"✅ NBA 수집 완료: {len(odds_data)}경기, {len(tweets)}트윗")
```

---

## 🔔 알림 설정

### Prometheus Alerts

**자동 알림 조건**:
- 🔴 Odds API 450회 초과
- 🔴 Twitter API 450회 초과
- 🔴 NBA 수집 10분 이상 중단
- 🔴 경제 수집 10분 이상 중단
- 🔴 Neo4j 노드 1시간 증가 없음
- 🔴 VPS 메모리 90% 초과
- 🔴 VPS 디스크 90% 초과
- 🟡 VPS CPU 80% 초과

### 알림 확장 (옵션)

**Telegram 알림**:
```bash
# Alertmanager 설정
alertmanagers:
  - static_configs:
      - targets: ['localhost:9093']
```

**Discord 알림**:
```bash
# Webhook 설정
discord_configs:
  - webhook_url: 'YOUR_DISCORD_WEBHOOK'
```

---

## 🎯 PromQL 쿼리 예시

### API 사용량 추적

```promql
# Odds API 총 사용량
sum(api_calls_total{source="odds_api"})

# Twitter API 총 사용량
sum(api_calls_total{source="twitter_api"})

# 오늘 사용량 (UTC 기준)
sum(increase(api_calls_total[24h]))
```

### Neo4j 증가율

```promql
# 시간당 노드 증가량
increase(neo4j_node_count[1h])

# 일일 노드 증가량
increase(neo4j_node_count[24h])
```

### 작업 중단 감지

```promql
# NBA 수집 중단 (10분 초과)
time() - job_last_run_timestamp{job="nba_collector"} > 600

# 경제 수집 중단 (10분 초과)
time() - job_last_run_timestamp{job="economic_collector"} > 600
```

---

## 🔍 트러블슈팅

### 1. Grafana 접속 안됨

```bash
ssh root@141.164.35.214
docker ps | grep g9-grafana
docker logs g9-grafana
docker restart g9-grafana
```

### 2. Prometheus 메트릭 수집 안됨

```bash
# Prometheus 로그 확인
docker logs g9-prometheus

# Target 상태 확인
curl http://localhost:9090/api/v1/targets
```

### 3. Metrics API 응답 없음

```bash
# API 상태 확인
curl http://localhost:9101/health

# 로그 확인
docker logs g9-metrics-api

# 재시작
docker restart g9-metrics-api
```

### 4. Neo4j 노드 수가 0으로 표시됨

```bash
# SSH 터널 확인 (로컬)
ps aux | grep "ssh.*7687"

# Neo4j 연결 테스트
python3 -c "
from neo4j import GraphDatabase
d = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'nba_vultr_2025'))
print('OK')
d.close()
"
```

---

## 💡 Best Practices

### 1. API 사용량 관리

```python
# 수집 전 API 사용량 확인
def check_api_budget():
    r = requests.get("http://localhost:9090/api/v1/query?query=sum(api_calls_total{source='odds_api'})")
    current_usage = int(r.json()["data"]["result"][0]["value"][1])

    if current_usage >= 480:
        print("🔴 API 한계 도달! 수집 중단")
        return False
    elif current_usage >= 400:
        print("🟡 API 80% 사용! 주의")
    return True

# 수집 전 체크
if not check_api_budget():
    exit(1)
```

### 2. 작업 헬스 체크

```bash
# 크론 작업 시작 시 무조건 heartbeat 기록
*/10 * * * * curl http://localhost:9101/api/record_job_heartbeat/nba_collector
```

### 3. 데이터 검증

```python
# Neo4j 노드 증가 확인
def verify_data_growth():
    r = requests.get("http://localhost:9090/api/v1/query?query=increase(neo4j_node_count[1h])")
    growth = int(r.json()["data"]["result"][0]["value"][1])

    if growth == 0:
        print("⚠️ Neo4j 노드 증가 없음! 수집 문제?")
```

---

## 📊 시스템 구성도

```
┌─────────────────────────────────────────┐
│         파이프라인 (Python)              │
│  - NBA 수집                              │
│  - 경제 수집                             │
│  - 리포트 생성                           │
└──────────┬──────────────────────────────┘
           │ HTTP GET 메트릭 기록
           ↓
┌─────────────────────────────────────────┐
│     Metrics API (Flask:9101)            │
│  - API 호출 카운터                       │
│  - 작업 heartbeat                        │
│  - Neo4j 노드 수                         │
└──────────┬──────────────────────────────┘
           │ Prometheus 스크랩
           ↓
┌─────────────────────────────────────────┐
│     Prometheus (9090)                   │
│  - 메트릭 수집                           │
│  - 알림 규칙 평가                        │
│  - 데이터 저장 (시계열)                  │
└──────────┬──────────────────────────────┘
           │ 데이터소스
           ↓
┌─────────────────────────────────────────┐
│     Grafana (3000)                      │
│  - 대시보드 시각화                       │
│  - 실시간 그래프                         │
│  - 알림 패널                             │
└─────────────────────────────────────────┘

추가:
Node Exporter (9100) → VPS 시스템 메트릭
```

---

## 🎉 결과

### 가능해진 것

✅ **API 예산 관리**: 500회 제한 실시간 추적
✅ **수집 중단 감지**: 10분 이상 중단 시 자동 알림
✅ **데이터 성장 추적**: Neo4j 노드 증가율 시각화
✅ **시스템 헬스**: VPS CPU/메모리/디스크 모니터링
✅ **타임라인 분석**: Odds/트윗/경제 이벤트 상관관계
✅ **완전 무료**: OSS 스택, 가입 불필요
✅ **확장 가능**: NBA → 축구 → 크립토 추가 용이

### 운영 시나리오

**시나리오 1: API 한계 도달**
```
Grafana 대시보드에서 Odds API 480회 확인
→ 알림 발생 (Slack/Telegram)
→ 수집 크론 일시 중단
→ 다음 달 1일까지 대기
```

**시나리오 2: 수집 중단 감지**
```
NBA 수집이 10분 이상 실행 안됨
→ Prometheus Alert 발생
→ Grafana 대시보드 🔴 표시
→ 크론/n8n 상태 확인
→ 재시작
```

**시나리오 3: Neo4j 노드 증가 없음**
```
1시간 동안 노드 증가 0
→ 수집 파이프라인 문제 의심
→ 로그 확인
→ API 연결 상태 확인
```

---

## 🚀 다음 단계

### 옵션 1: 알림 자동화
- Telegram 봇 연동
- Discord Webhook 연동
- 이메일 알림

### 옵션 2: 고급 대시보드
- NBA vs Odds 상관 그래프
- 트위터 감성 vs 배당 변동
- 경제 이벤트 임팩트 분석

### 옵션 3: 머신러닝 통합
- API 사용량 예측
- 수집 최적화 시간 추천
- 이상 감지 (Anomaly Detection)

---

**"수집 → LLM 정리 → Neo4j → Grafana"**
**이제 눈으로 보이는 운영 시스템!** 🎯
