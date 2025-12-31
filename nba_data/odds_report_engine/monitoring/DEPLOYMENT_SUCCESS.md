# 🎉 G9 운영 대시보드 배포 완료 - 2025-12-28

## ✅ 배포 완료된 시스템

### 1. Prometheus (메트릭 수집) ✅
```
컨테이너: g9-prometheus
포트: 9090
상태: ✅ Healthy
URL: http://141.164.35.214:9090
```

### 2. Grafana (대시보드 시각화) ✅
```
컨테이너: g9-grafana
포트: 3000
상태: ✅ Healthy
URL: http://141.164.35.214:3000
계정: admin / g9admin2025
```

### 3. Node Exporter (VPS 시스템 메트릭) ✅
```
컨테이너: g9-node-exporter
포트: 9100 (내부)
상태: ✅ Running
메트릭: CPU, 메모리, 디스크, 네트워크
```

### 4. Metrics API (G9 파이프라인 메트릭) ✅
```
컨테이너: g9-metrics-api
포트: 9101
상태: ✅ Healthy
URL: http://141.164.35.214:9101/health
Prometheus: http://141.164.35.214:9101/metrics
```

---

## 📊 구축된 모니터링 시스템

### API 사용량 관리 (월 500회 제한)
- 🎲 **Odds API**: 실시간 사용량 추적
  - 🟢 0-400회: 안전
  - 🟡 400-450회: 경고
  - 🔴 450-500회: 위험
- 🐦 **Twitter API**: 실시간 사용량 추적
  - 🟢 0-400회: 안전
  - 🟡 400-450회: 경고
  - 🔴 450-500회: 위험

### 수집 상태 모니터링
- 🏀 **NBA 경기 수집**: 오늘 수집된 경기 수
- 💹 **경제 이벤트 수집**: 오늘 수집된 이벤트 수
- 💰 **Odds 스냅샷**: 실시간 배당 스냅샷 수
- 🐦 **Twitter 이벤트**: 도메인별 트위터 이벤트 수

### Neo4j 데이터베이스 추적
- 🧠 **노드 수**: NBA / 경제 데이터베이스별 노드 수
- 📈 **노드 증가율**: 시간당 증가량 시각화
- 📊 **데이터 누적**: 실시간 그래프 RAG 성장 추적

### 작업 헬스 체크 (크론/n8n)
- ⏱ **NBA 수집**: 마지막 실행 시간 (10분 초과 시 알림)
- ⏱ **경제 수집**: 마지막 실행 시간 (10분 초과 시 알림)
- ⏱ **리포트 생성**: 마지막 실행 시간

### VPS 시스템 모니터링
- 🖥 **메모리 사용률**: 90% 초과 시 알림
- 💾 **디스크 사용률**: 90% 초과 시 알림
- ⚡ **CPU 사용률**: 80% 초과 시 알림

---

## 🎯 다음 단계

### 1단계: Grafana 설정 (필수)

```bash
# 브라우저로 접속
http://141.164.35.214:3000

# 로그인
ID: admin
PW: g9admin2025

# Prometheus 데이터소스 추가
Settings → Data Sources → Add data source
Type: Prometheus
URL: http://prometheus:9090  (컨테이너 이름으로 접근)
Save & Test

# G9 대시보드 임포트
Dashboards → Import → Upload JSON file
파일: /opt/g9/monitoring/grafana_g9_dashboard.json
또는
로컬: /Users/js/g9/nba_data/odds_report_engine/monitoring/grafana_g9_dashboard.json
```

### 2단계: 파이프라인 통합 (필수)

기존 파이프라인에 메트릭 기록 추가:

```python
import requests

# API 호출 후
requests.get("http://localhost:9101/api/record_api_call/odds_api")

# Odds 스냅샷 수집 후
requests.get(f"http://localhost:9101/api/record_odds_snapshot/{game_id}")

# Twitter 이벤트 수집 후
requests.get("http://localhost:9101/api/record_twitter_event/nba")

# 크론 작업 시작 시
requests.get("http://localhost:9101/api/record_job_heartbeat/nba_collector")

# NBA 경기 수 업데이트
requests.get(f"http://localhost:9101/api/set_nba_games/{game_count}")
```

**통합 예시 파일**: `/Users/js/g9/nba_data/odds_report_engine/monitoring/pipeline_integration_example.py`

### 3단계: Alert 확인 (선택)

```bash
# Prometheus 알림 규칙 확인
http://141.164.35.214:9090/alerts

# 알림 조건:
# - Odds API 450회 초과 (🔴 Critical)
# - Twitter API 450회 초과 (🔴 Critical)
# - NBA 수집 10분 이상 중단 (🔴 Critical)
# - 경제 수집 10분 이상 중단 (🔴 Critical)
# - Neo4j 노드 1시간 증가 없음 (🟡 Warning)
# - VPS 메모리 90% 초과 (🔴 Critical)
# - VPS 디스크 90% 초과 (🔴 Critical)
# - VPS CPU 80% 초과 (🟡 Warning)
```

---

## 🔧 운영 방법

### 메트릭 확인

```bash
# Prometheus 메트릭 직접 확인
curl http://141.164.35.214:9101/metrics

# API 사용량 확인
curl -s 'http://141.164.35.214:9090/api/v1/query?query=sum(api_calls_total{source="odds_api"})' | jq

# Neo4j 노드 수 확인
curl -s 'http://141.164.35.214:9090/api/v1/query?query=neo4j_node_count' | jq
```

### 컨테이너 관리

```bash
# 상태 확인
ssh root@141.164.35.214 "docker ps | grep g9-"

# 로그 확인
ssh root@141.164.35.214 "docker logs g9-prometheus"
ssh root@141.164.35.214 "docker logs g9-grafana"
ssh root@141.164.35.214 "docker logs g9-metrics-api"

# 재시작
ssh root@141.164.35.214 "cd /opt/g9/monitoring && docker compose restart"

# 중단
ssh root@141.164.35.214 "cd /opt/g9/monitoring && docker compose down"

# 시작
ssh root@141.164.35.214 "cd /opt/g9/monitoring && docker compose up -d"
```

---

## 📁 생성된 파일

### VPS (141.164.35.214)
```
/opt/g9/monitoring/
├── prometheus.yml              # Prometheus 설정
├── alerts.yml                  # Alert 규칙
├── docker-compose.yml          # Docker Compose 스택
├── metrics_api.py              # Flask 메트릭 API
├── Dockerfile.metrics          # Metrics API 이미지
├── grafana_g9_dashboard.json   # Grafana 대시보드 JSON
└── volumes/
    ├── prometheus-data/        # Prometheus 데이터
    └── grafana-data/           # Grafana 데이터
```

### 로컬
```
/Users/js/g9/nba_data/odds_report_engine/monitoring/
├── prometheus.yml
├── alerts.yml
├── docker-compose.yml
├── metrics_api.py
├── Dockerfile.metrics
├── grafana_g9_dashboard.json
├── deploy_monitoring.sh                  # 배포 스크립트
├── pipeline_integration_example.py       # 파이프라인 통합 예시
├── MONITORING_GUIDE.md                   # 완전 가이드
└── DEPLOYMENT_SUCCESS.md                 # 이 문서
```

---

## 🎯 핵심 장점

### 1. 무료 + 무가입
- ✅ 모든 컴포넌트 오픈소스
- ✅ VPS 로컬 실행 (외부 서비스 불필요)
- ✅ Grafana 가입 불필요

### 2. 실시간 운영
- ✅ API 500회 제한 실시간 추적
- ✅ 수집 중단 자동 감지 (10분)
- ✅ Neo4j 데이터 증가 추적
- ✅ VPS 시스템 헬스 모니터링

### 3. 확장 가능
- ✅ NBA → 축구 → 크립토 추가 용이
- ✅ 새로운 메트릭 추가 간단
- ✅ 알림 채널 확장 (Telegram, Discord)

### 4. 프로덕션 레디
- ✅ Docker Compose 자동 관리
- ✅ 데이터 영구 저장 (volumes)
- ✅ 자동 재시작 (restart: unless-stopped)

---

## 💡 실전 시나리오

### 시나리오 1: API 한계 도달
```
1. Grafana 대시보드에서 Odds API 480회 확인
2. Prometheus Alert 발생 (🟡 Warning)
3. API 사용 중단 또는 속도 제한
4. 다음 달 1일 리셋 대기
```

### 시나리오 2: 수집 중단 감지
```
1. NBA 수집 크론이 10분 이상 실행 안됨
2. Prometheus Alert 발생 (🔴 Critical)
3. Grafana 대시보드 ⏱ 패널 빨간색
4. 크론 재시작 또는 파이프라인 디버깅
```

### 시나리오 3: Neo4j 노드 증가 없음
```
1. 1시간 동안 노드 증가 0
2. Prometheus Alert 발생 (🟡 Warning)
3. 수집 파이프라인 문제 의심
4. API 연결 상태 및 로그 확인
```

### 시나리오 4: VPS 메모리 부족
```
1. VPS 메모리 사용률 90% 초과
2. Prometheus Alert 발생 (🔴 Critical)
3. 불필요한 프로세스 종료
4. 메모리 사용량 많은 컨테이너 재시작
```

---

## 🚀 다음 확장 옵션

### 옵션 1: 알림 자동화 ✉️
```bash
# Telegram 봇 연동
# Discord Webhook 연동
# 이메일 알림 (SMTP)
```

### 옵션 2: 고급 대시보드 📊
```bash
# NBA vs Odds 상관 그래프
# 트위터 감성 vs 배당 변동
# 경제 이벤트 임팩트 분석
```

### 옵션 3: 머신러닝 통합 🤖
```bash
# API 사용량 예측
# 수집 최적화 시간 추천
# 이상 감지 (Anomaly Detection)
```

---

## 🎊 최종 결과

```
┌─────────────────────────────────────────┐
│   G9 운영 대시보드 (완전 배포)            │
├─────────────────────────────────────────┤
│                                          │
│  ✅ Prometheus: API + 수집 + Neo4j      │
│  ✅ Grafana: 실시간 대시보드             │
│  ✅ Node Exporter: VPS 시스템            │
│  ✅ Metrics API: 파이프라인 통합         │
│  ✅ Alert Rules: 8개 자동 알림           │
│                                          │
└─────────────────────────────────────────┘

수집 → LLM 정리 → Neo4j → Grafana
이제 눈으로 보이는 운영 시스템! 🎯
```

---

**🎉 전문 운영 대시보드 배포 완료!**

**API 500회 관리 + 수집 상태 + Neo4j 추적 + VPS 헬스**
**모두 실시간으로 한눈에!** 📊
