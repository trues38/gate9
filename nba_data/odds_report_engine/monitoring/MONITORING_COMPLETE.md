# ✅ G9 모니터링 시스템 구축 완료

**배포 날짜**: 2025-12-28
**VPS**: 141.164.35.214

---

## 📊 완료된 기능

### 1️⃣ NBA vs Odds vs Twitter 상관 분석 대시보드 ✅

**접속 URL**: http://141.164.35.214:3000/d/g9-correlation-dashboard

**포함된 분석**:
- 🔥 **Odds Movement vs Twitter Sentiment** (실시간 오버레이)
  * 배팅 라인 변동과 트위터 감성 변화를 동시에 추적
  * 상관관계를 시각적으로 확인 가능

- 📊 **Odds-Twitter 상관계수** (경기별 게이지)
  * -1 ~ +1 범위의 상관계수
  * 0.8 이상: 강한 양의 상관관계 (녹색)
  * 0.5 미만: 낮은 상관관계 (빨간색)

- ⚡ **NBA 이벤트 임팩트 점수** (-10 ~ +10)
  * injury (부상): -8.5 (매우 부정적)
  * lineup (라인업 변경): -2.0 (부정적)
  * news (뉴스): +0.5 (중립)

- 🐦 **Twitter 감성 분석 추이**
  * 실시간 팀별 감성 점수 (-1: 매우부정 ~ +1: 매우긍정)

- 📢 **경기별 Twitter 언급 횟수**
  * 화제성 측정

- 📋 **Twitter 이벤트 카테고리**
  * injury, lineup, news, rumor 분류

**메트릭 기록 방법**:
```bash
# Odds 변동 기록
curl "http://141.164.35.214:9101/api/record_odds_movement?game_id=401810214&market=h2h&team=LAL&movement=0.15"

# Twitter 감성 기록
curl "http://141.164.35.214:9101/api/record_twitter_sentiment?domain=nba&team=LAL&score=0.7"

# NBA 이벤트 임팩트 기록
curl "http://141.164.35.214:9101/api/record_nba_event_impact?game_id=401810214&event_type=injury&team=LAL&impact=-8.5"

# 상관계수 기록
curl "http://141.164.35.214:9101/api/record_correlation?game_id=401810214&correlation=0.85"

# Twitter 언급 횟수 기록
curl "http://141.164.35.214:9101/api/record_game_mentions?game_id=401810214&team=LAL&count=1523"

# 카테고리별 이벤트 기록
curl "http://141.164.35.214:9101/api/record_twitter_category?domain=nba&category=injury"
```

---

### 2️⃣ 알림 자동화 시스템 ✅

**Alertmanager URL**: http://141.164.35.214:9093

**상태**:
- ✅ Alertmanager 컨테이너 실행 중
- ✅ Prometheus 연동 완료
- ✅ 8개 알림 규칙 활성화
- ⚠️ **Telegram/Discord 알림 비활성화** (자격 증명 필요)

**활성화된 알림 규칙**:

| 알림 이름 | 조건 | 심각도 |
|----------|------|--------|
| OddsAPILimitApproaching | API 사용 450회 이상 | 🔴 critical |
| TwitterAPILimitApproaching | API 사용 450회 이상 | 🔴 critical |
| OddsAPILimitWarning | API 사용 400회 이상 | 🟡 warning |
| TwitterAPILimitWarning | API 사용 400회 이상 | 🟡 warning |
| NBACollectionStalled | 10분간 수집 없음 | 🔴 critical |
| EconomicCollectionStalled | 10분간 수집 없음 | 🔴 critical |
| HighMemoryUsage | 메모리 90% 이상 | 🔴 critical |
| HighDiskUsage | 디스크 90% 이상 | 🔴 critical |

---

## 🔔 알림 활성화 방법

현재 알림은 **로그에만 기록**되고 있습니다. 실제 Telegram/Discord 알림을 받으려면:

### Step 1: 자격 증명 생성

**Telegram Bot**:
1. Telegram에서 `@BotFather` 검색
2. `/newbot` 입력
3. Bot Token 복사: `123456789:ABCdefGHI...`
4. Chat ID 확인:
   ```bash
   # 봇에게 아무 메시지 보낸 후
   curl https://api.telegram.org/bot<TOKEN>/getUpdates
   ```

**Discord Webhook**:
1. Discord 서버 설정 → 통합 → Webhooks
2. 새 Webhook 생성
3. Webhook URL 복사: `https://discord.com/api/webhooks/...`

### Step 2: VPS에서 설정 파일 수정

```bash
ssh root@141.164.35.214
cd /opt/g9/monitoring
nano alertmanager.yml
```

### Step 3: 알림 설정 활성화

`alertmanager.yml` 파일에서:

1. **routes 섹션 주석 해제**:
```yaml
route:
  receiver: 'default'
  routes:  # ← 이 줄부터 주석 해제
    - match:
        severity: critical
      receiver: 'critical-multi'
      continue: true
    - match:
        severity: warning
      receiver: 'warning-telegram'
```

2. **receivers 섹션 주석 해제 및 자격 증명 입력**:
```yaml
receivers:
  - name: 'default'

  - name: 'critical-multi'  # ← 이 줄부터 주석 해제
    telegram_configs:
      - bot_token: '123456789:ABCdefGHI...'  # ← 실제 Token
        chat_id: 1234567890  # ← 실제 Chat ID
    webhook_configs:
      - url: 'https://discord.com/api/webhooks/...'  # ← 실제 Webhook URL

  - name: 'warning-telegram'  # ← 이 줄부터 주석 해제
    telegram_configs:
      - bot_token: '123456789:ABCdefGHI...'
        chat_id: 1234567890
```

### Step 4: Alertmanager 재시작

```bash
docker restart g9-alertmanager
```

### Step 5: 테스트

**Telegram 테스트**:
```bash
curl -X POST \
  "https://api.telegram.org/bot<TOKEN>/sendMessage" \
  -d "chat_id=<CHAT_ID>" \
  -d "text=🔴 테스트: G9 알림 시스템 작동 중!"
```

**Discord 테스트**:
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"content":"🔴 테스트: G9 알림 시스템 작동 중!"}' \
  <WEBHOOK_URL>
```

**실제 알림 트리거 테스트**:
```bash
# API 호출 450회 초과시키기
for i in {1..500}; do
  curl -s http://141.164.35.214:9101/api/record_api_call/odds_api > /dev/null
done

# 1분 후 Telegram + Discord에 알림 도착 확인
```

---

## 📁 관련 파일

| 파일 | 설명 |
|------|------|
| `alertmanager.yml` | Alertmanager 설정 (자격 증명 입력 필요) |
| `ALERT_SETUP_GUIDE.md` | 상세한 알림 설정 가이드 |
| `setup_alerts_quick.sh` | 자동 설정 스크립트 |
| `grafana_correlation_dashboard.json` | 상관 분석 대시보드 JSON |
| `metrics_api.py` | 고급 메트릭 API (포트 9101) |

---

## 🎯 모니터링 시스템 구조

```
VPS (141.164.35.214)
├── Prometheus (9090) ─┐
│   ├─ 메트릭 수집      │
│   ├─ 알림 규칙 평가   │
│   └─ Alertmanager 연동├─> Grafana (3000)
│                        │   ├─ 메인 대시보드
├── Alertmanager (9093) │   └─ 상관 분석 대시보드
│   ├─ 알림 라우팅      │
│   ├─ Telegram 발송 ───┘
│   └─ Discord 발송
│
├── Metrics API (9101)
│   ├─ API 호출 기록
│   ├─ Odds 변동 추적
│   └─ Twitter 감성 분석
│
├── Node Exporter (9100)
│   └─ VPS 시스템 메트릭
│
└── Neo4j (7687)
    └─ 15,433 nodes
```

---

## 🚀 다음 단계

### 즉시 가능:
1. ✅ 대시보드 확인: http://141.164.35.214:3000
2. ✅ 상관 분석 확인: http://141.164.35.214:3000/d/g9-correlation-dashboard
3. ⚠️ 알림 활성화 (위 가이드 참고)

### 향후 계획 (사용자 로드맵):
1. 레포트 엔진 연동
2. 웹사이트 UI/UX 개발
3. 결제 시스템 통합
4. 운영/판매 시작

---

## 📊 시스템 상태 확인

```bash
# 모든 컨테이너 확인
ssh root@141.164.35.214 "docker ps"

# Prometheus targets 확인
curl http://141.164.35.214:9090/targets

# Alertmanager 상태 확인
curl http://141.164.35.214:9093/-/healthy

# 메트릭 API 상태 확인
curl http://141.164.35.214:9101/health
```

---

## 🔐 접속 정보

| 서비스 | URL | 자격 증명 |
|--------|-----|----------|
| Grafana | http://141.164.35.214:3000 | admin / g9admin2025 |
| Prometheus | http://141.164.35.214:9090 | (인증 없음) |
| Alertmanager | http://141.164.35.214:9093 | (인증 없음) |
| Metrics API | http://141.164.35.214:9101 | (인증 없음) |

---

## 💡 참고 사항

- **영구 작동**: 모든 컨테이너는 `restart: unless-stopped` 정책으로 VPS 재부팅 후에도 자동 시작
- **데이터 보존**: Grafana 대시보드, Prometheus 메트릭, Alertmanager 알림 히스토리 모두 영구 볼륨에 저장
- **확장성**: 추가 데이터 소스 (경제 지표, 날씨 등) 쉽게 추가 가능
- **보안**: 현재 인증 없음 - 프로덕션 배포 시 nginx reverse proxy + SSL 추천

---

**모든 기능 정상 작동 중** ✅

문의사항: `ALERT_SETUP_GUIDE.md` 참고
