# 🔔 G9 알림 자동화 설정 가이드

> **Telegram + Discord 멀티 채널 알림 완전 가이드**

---

## 📋 목차

1. [Telegram 봇 생성](#1-telegram-봇-생성)
2. [Discord Webhook 생성](#2-discord-webhook-생성)
3. [Alertmanager 설정](#3-alertmanager-설정)
4. [알림 테스트](#4-알림-테스트)

---

## 1. Telegram 봇 생성

### Step 1: BotFather와 대화

1. Telegram 앱 열기
2. **@BotFather** 검색
3. `/start` 입력
4. `/newbot` 입력

### Step 2: 봇 정보 입력

```
BotFather: Alright, a new bot. How are we going to call it?
You: G9 NBA Alerts Bot

BotFather: Good. Now let's choose a username for your bot.
You: g9_nba_alerts_bot

BotFather: Done! Here is your token:
123456789:ABCdefGHIjklMNOpqrsTUVwxyz
```

**✅ Bot Token 복사**: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`

### Step 3: Chat ID 가져오기

1. 봇에게 메시지 보내기 (아무거나)
2. 브라우저에서 접속:
   ```
   https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
   ```
3. 응답에서 `chat.id` 찾기:
   ```json
   {
     "message": {
       "chat": {
         "id": 1234567890  ← 이게 Chat ID
       }
     }
   }
   ```

**✅ Chat ID 복사**: `1234567890`

### Step 4: 그룹에 추가 (선택)

그룹 알림을 원하면:
1. Telegram 그룹 생성
2. 봇을 그룹에 초대
3. 그룹에서 메시지 보내기
4. getUpdates로 그룹 Chat ID 확인

---

## 2. Discord Webhook 생성

### Step 1: Discord 서버 생성 (없으면)

1. Discord 앱 열기
2. 좌측 하단 `+` 클릭
3. "서버 만들기" → "직접 만들기"
4. 서버 이름: `G9 NBA Monitoring`

### Step 2: Webhook 생성

1. 서버 설정 클릭 (톱니바퀴 아이콘)
2. 좌측 메뉴: **통합** (Integrations)
3. **Webhooks** 클릭
4. **새 Webhook** 클릭
5. 설정:
   - 이름: `G9 Alerts`
   - 채널: `#alerts` (없으면 생성)
6. **Webhook URL 복사** 클릭

**✅ Webhook URL 복사**:
```
https://discord.com/api/webhooks/1234567890/abcdefghijklmnopqrstuvwxyz
```

---

## 3. Alertmanager 설정

### Step 1: alertmanager.yml 수정

```bash
cd /opt/g9/monitoring
nano alertmanager.yml
```

### Step 2: Token/URL 입력

```yaml
receivers:
  - name: 'critical-multi'
    telegram_configs:
      - bot_token: '123456789:ABCdefGHIjklMNOpqrsTUVwxyz'  # ← 여기
        chat_id: 1234567890  # ← 여기

    webhook_configs:
      - url: 'https://discord.com/api/webhooks/1234567890/abcdefghijklmnopqrstuvwxyz'  # ← 여기
```

### Step 3: Prometheus 설정 업데이트

```bash
nano prometheus.yml
```

Alertmanager 추가:
```yaml
alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']
```

### Step 4: Docker Compose 재시작

```bash
docker compose up -d
```

---

## 4. 알림 테스트

### Telegram 테스트

```bash
curl -X POST \
  "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/sendMessage" \
  -d "chat_id=<YOUR_CHAT_ID>" \
  -d "text=🔴 테스트: G9 알림 시스템 작동 중!"
```

### Discord 테스트

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"content":"🔴 테스트: G9 알림 시스템 작동 중!"}' \
  YOUR_DISCORD_WEBHOOK_URL
```

### Prometheus Alert 트리거 테스트

수동으로 API 450회 초과시키기:
```bash
for i in {1..500}; do
  curl -s http://localhost:9101/api/record_api_call/odds_api > /dev/null
done

# 1분 후 Telegram + Discord에 알림 도착!
```

---

## 📊 알림 분류

### 🔴 Critical (Telegram + Discord 동시)

- Odds API 450회 초과
- Twitter API 450회 초과
- NBA 수집 10분 중단
- 경제 수집 10분 중단
- VPS 메모리 90% 초과
- VPS 디스크 90% 초과

### 🟡 Warning (Telegram만)

- Odds API 400회 초과
- Twitter API 400회 초과
- Neo4j 노드 1시간 증가 없음
- VPS CPU 80% 초과

---

## 🎯 알림 형식 예시

### Telegram 메시지

```
🔴 CRITICAL ALERT

OddsAPILimitApproaching

Summary: Odds API 사용량 90% 초과
Description: 450회 사용 (월 500회 제한)
Severity: critical
```

### Discord 메시지

```json
{
  "embeds": [{
    "title": "🔴 CRITICAL: OddsAPILimitApproaching",
    "description": "Odds API 사용량 90% 초과\n450회 사용 (월 500회 제한)",
    "color": 15158332,
    "timestamp": "2025-12-28T15:45:00Z"
  }]
}
```

---

## 🔧 고급 설정

### 알림 빈도 조절

```yaml
route:
  repeat_interval: 12h  # 12시간마다 반복 (기본)
  # repeat_interval: 1h  # 1시간마다
  # repeat_interval: 24h  # 24시간마다
```

### 특정 알림만 필터

```yaml
routes:
  # API 관련만 Discord로
  - match:
      category: api_budget
    receiver: 'discord-only'

  # 시스템 알림만 Telegram으로
  - match:
      category: system
    receiver: 'telegram-only'
```

### 이메일 추가 (선택)

```yaml
receivers:
  - name: 'email-critical'
    email_configs:
      - to: 'your-email@gmail.com'
        from: 'alerts@g9.com'
        smarthost: 'smtp.gmail.com:587'
        auth_username: 'your-email@gmail.com'
        auth_password: 'your-app-password'
        headers:
          Subject: '🔴 G9 Critical Alert'
```

---

## 📱 모바일 알림 설정

### Telegram
- ✅ 앱 설치만 하면 자동
- ✅ 푸시 알림 ON
- ✅ 방해 금지 모드 예외 추가 가능

### Discord
- ✅ 앱 설치
- ✅ 서버 알림 설정 → "모든 메시지"
- ✅ 모바일 푸시 활성화

---

## 🚨 트러블슈팅

### Telegram 메시지 안옴

1. 봇 Token 확인
   ```bash
   curl https://api.telegram.org/bot<TOKEN>/getMe
   ```

2. Chat ID 재확인
   ```bash
   curl https://api.telegram.org/bot<TOKEN>/getUpdates
   ```

3. 봇 차단 해제
   - Telegram에서 봇 검색
   - `/start` 재입력

### Discord Webhook 안됨

1. Webhook URL 유효성 확인
   ```bash
   curl -X GET <WEBHOOK_URL>
   ```

2. 채널 권한 확인
   - Webhook이 메시지 보낼 권한 있는지

### Alertmanager 로그 확인

```bash
docker logs g9-alertmanager
```

---

## 🎉 완료!

설정 완료 후:

1. ✅ Telegram 봇 생성
2. ✅ Discord Webhook 생성
3. ✅ alertmanager.yml 설정
4. ✅ 테스트 메시지 발송 성공

**이제 API 한계 도달, 수집 중단 등 모든 Critical 이벤트가 자동으로 알림됩니다!** 🔔

**다음: Alertmanager를 Docker Compose에 추가하고 배포**
