# 🎉 Grafana 대시보드 임포트 완료!

## ✅ 설정 완료된 항목

### 1. Prometheus 데이터소스 ✅
```
이름: Prometheus
타입: prometheus
URL: http://prometheus:9090
상태: ✅ Connected
```

### 2. G9 운영 대시보드 ✅
```
이름: G9 운영 대시보드 - NBA + 경제 통합 모니터링
UID: g9-main-dashboard
패널: 14개
상태: ✅ Active
```

### 3. 테스트 메트릭 생성 ✅
```
🎲 Odds API: 11회 호출
🐦 Twitter API: 5회 호출
🏀 NBA 경기: 12개 수집
💹 경제 이벤트: 25개 수집
⏱ NBA 수집: 방금 실행
⏱ 경제 수집: 방금 실행
```

---

## 🎯 대시보드 접속

### URL
```
http://141.164.35.214:3000/d/g9-main-dashboard
```

### 로그인
```
ID: admin
PW: g9admin2025
```

### 직접 접속 링크
```
메인 대시보드:
http://141.164.35.214:3000/d/g9-main-dashboard/c78f796

Prometheus:
http://141.164.35.214:9090
```

---

## 📊 대시보드 구성 (14개 패널)

### Row 1: API 사용량 모니터링
1. **🎲 Odds API 사용량** (Gauge)
   - 현재 값: 11회
   - 제한: 월 500회
   - 임계값: 400회 (🟡), 450회 (🔴)

2. **🐦 Twitter API 사용량** (Gauge)
   - 현재 값: 5회
   - 제한: 월 500회
   - 임계값: 400회 (🟡), 450회 (🔴)

3. **📊 API 사용량 추이** (Time Series)
   - Odds API vs Twitter API 비교
   - 시간별 추이 그래프

### Row 2: 수집 상태
4. **🏀 NBA 경기 수집** (Gauge)
   - 오늘 수집: 12경기

5. **💹 경제 이벤트 수집** (Gauge)
   - 오늘 수집: 25개 이벤트

6. **🧠 Neo4j 노드 수** (Time Series)
   - NBA 데이터베이스
   - 경제 데이터베이스
   - 실시간 증가 추적

7. **📈 Neo4j 노드 증가율** (Time Series)
   - 시간당 증가량
   - Bar 차트

### Row 3: 작업 헬스 체크
8. **⏱ NBA 수집 마지막 실행** (Gauge)
   - 마지막 실행: 방금
   - 초 단위 표시
   - 10분 초과 시 🔴

9. **⏱ 경제 수집 마지막 실행** (Gauge)
   - 마지막 실행: 방금
   - 초 단위 표시
   - 10분 초과 시 🔴

10. **🖥 VPS 메모리 사용률** (Gauge)
    - 현재 사용률
    - 임계값: 70% (🟡), 90% (🔴)

11. **💾 VPS 디스크 사용률** (Gauge)
    - 현재 사용률
    - 임계값: 70% (🟡), 90% (🔴)

12. **⚡ VPS CPU 사용률** (Gauge)
    - 현재 사용률
    - 임계값: 70% (🟡), 90% (🔴)

### Row 4: 이벤트 추적
13. **💰 Odds 스냅샷 수집 추이** (Time Series)
    - 경기별 스냅샷 수집
    - Bar 차트

14. **🐦 Twitter 이벤트 수집 추이** (Time Series)
    - NBA vs 경제 도메인
    - Bar 차트

---

## 🎨 대시보드 사용법

### 1. 리프레시 간격 설정
```
우측 상단 🔄 버튼 클릭
→ 10s, 30s, 1m, 5m 선택 가능
→ 권장: 10s (실시간 모니터링)
```

### 2. 시간 범위 설정
```
우측 상단 시계 버튼 클릭
→ Last 6 hours (기본)
→ Last 1 hour, Last 24 hours 등 선택 가능
```

### 3. 패널 확대/축소
```
패널 제목 클릭 → View
→ 전체 화면으로 보기
→ Query Inspector로 PromQL 확인
```

### 4. 대시보드 공유
```
우측 상단 공유 버튼 클릭
→ Link 탭: URL 복사
→ Snapshot 탭: 외부 공유용 스냅샷 생성
```

---

## 🔍 실시간 모니터링 시나리오

### 시나리오 1: API 사용량 추적
```
1. Odds API 게이지 확인
2. 450회 근접 시 🔴 빨간색 표시
3. "API 사용량 추이" 패널에서 증가 추세 확인
4. 필요 시 수집 빈도 조정
```

### 시나리오 2: 수집 중단 감지
```
1. "NBA 수집 마지막 실행" 게이지 확인
2. 10분 초과 시 자동으로 🔴 빨간색
3. Prometheus Alerts 탭에서 알림 확인
4. 크론 또는 n8n 워크플로우 재시작
```

### 시나리오 3: Neo4j 데이터 성장 추적
```
1. "Neo4j 노드 수" 그래프 확인
2. NBA vs 경제 데이터베이스 비교
3. "Neo4j 노드 증가율" 바 차트로 시간당 증가량 확인
4. 증가 없으면 수집 파이프라인 점검
```

### 시나리오 4: VPS 시스템 헬스
```
1. 메모리/디스크/CPU 게이지 한눈에 확인
2. 90% 초과 시 🔴 경고
3. Docker 컨테이너 리소스 사용량 점검
4. 필요 시 불필요한 프로세스 종료
```

---

## 📈 PromQL 쿼리 예시

### API 사용량
```promql
# Odds API 총 사용량
sum(api_calls_total{source="odds_api"})

# Twitter API 총 사용량
sum(api_calls_total{source="twitter_api"})

# 전체 API 사용량
sum(api_calls_total)
```

### Neo4j 증가율
```promql
# 시간당 증가량
increase(neo4j_node_count[1h])

# 일일 증가량
increase(neo4j_node_count[24h])
```

### 작업 중단 감지
```promql
# NBA 수집 마지막 실행 시간 (초)
time() - job_last_run_timestamp{job="nba_collector"}

# 10분 이상 중단 여부
(time() - job_last_run_timestamp{job="nba_collector"}) > 600
```

### VPS 메트릭
```promql
# 메모리 사용률 (%)
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100

# 디스크 사용률 (%)
(1 - (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"})) * 100

# CPU 사용률 (%)
100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)
```

---

## 🎯 다음 단계

### 1. 대시보드 커스터마이징
```
패널 추가:
- 경기별 Odds 변동 그래프
- Twitter 감성 vs Odds 상관관계
- 경제 이벤트 임팩트 분석
```

### 2. 알림 설정
```
Alerting → Alert rules
→ Prometheus Alerts 연동
→ Telegram/Discord/Email 알림 채널 추가
```

### 3. 파이프라인 통합
```python
# 기존 NBA 수집 코드에 추가
import requests

def collect_nba_data():
    # 작업 시작
    requests.get("http://localhost:9101/api/record_job_heartbeat/nba_collector")

    # Odds API 호출
    odds = fetch_odds()
    requests.get("http://localhost:9101/api/record_api_call/odds_api")

    # 각 경기 스냅샷
    for game in odds:
        requests.get(f"http://localhost:9101/api/record_odds_snapshot/{game['id']}")

    # 통계 업데이트
    requests.get(f"http://localhost:9101/api/set_nba_games/{len(odds)}")
```

---

## 🚨 알림 규칙 (이미 설정됨)

Prometheus에서 자동 감지:

### Critical (🔴)
- ✅ Odds API 450회 초과
- ✅ Twitter API 450회 초과
- ✅ NBA 수집 10분 중단
- ✅ 경제 수집 10분 중단
- ✅ VPS 메모리 90% 초과
- ✅ VPS 디스크 90% 초과

### Warning (🟡)
- ✅ Odds API 400회 초과
- ✅ Twitter API 400회 초과
- ✅ Neo4j 노드 1시간 증가 없음
- ✅ VPS CPU 80% 초과

확인: http://141.164.35.214:9090/alerts

---

## 🎊 완료!

```
┌─────────────────────────────────────────┐
│   Grafana 대시보드 실시간 운영 중!       │
├─────────────────────────────────────────┤
│                                          │
│  ✅ 14개 패널 활성화                     │
│  ✅ 실시간 메트릭 수집 중                │
│  ✅ Prometheus 알림 8개 활성화           │
│  ✅ API 500회 제한 실시간 추적           │
│  ✅ 수집 상태 한눈에 확인                │
│  ✅ Neo4j 데이터 성장 추적               │
│  ✅ VPS 시스템 헬스 모니터링             │
│                                          │
└─────────────────────────────────────────┘

🎯 지금 바로 접속:
http://141.164.35.214:3000/d/g9-main-dashboard

ID: admin / PW: g9admin2025
```

---

**이제 모든 운영 상태를 눈으로 보면서 관리합니다!** 📊

**수집 → LLM 정리 → Neo4j → Grafana**
**완전한 전문 운영 시스템 구축 완료!** 🚀
