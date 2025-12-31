#!/bin/bash
# G9 알림 빠른 설정 스크립트
# Telegram + Discord 자동 설정

echo "🔔 G9 알림 자동화 설정"
echo "=" * 70
echo ""

# 1. Telegram 봇 정보 입력
echo "[1/4] Telegram 봇 설정"
echo ""
echo "Telegram 봇 Token을 입력하세요:"
echo "(BotFather에서 받은 Token, 예: 123456789:ABCdefGHIjkl...)"
read -p "Bot Token: " TELEGRAM_TOKEN

echo ""
echo "Telegram Chat ID를 입력하세요:"
echo "(https://api.telegram.org/bot<TOKEN>/getUpdates 에서 확인)"
read -p "Chat ID: " TELEGRAM_CHAT_ID

# 2. Discord Webhook 입력
echo ""
echo "[2/4] Discord Webhook 설정"
echo ""
echo "Discord Webhook URL을 입력하세요:"
echo "(Discord 서버 설정 → 통합 → Webhooks)"
read -p "Webhook URL: " DISCORD_WEBHOOK

# 3. alertmanager.yml 자동 생성
echo ""
echo "[3/4] Alertmanager 설정 파일 생성 중..."

cat > /opt/g9/monitoring/alertmanager.yml << EOF
global:
  resolve_timeout: 5m

route:
  group_by: ['alertname', 'severity']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'default'

  routes:
    - match:
        severity: critical
      receiver: 'critical-multi'
      continue: true
    - match:
        severity: warning
      receiver: 'warning-telegram'

receivers:
  - name: 'default'

  - name: 'critical-multi'
    telegram_configs:
      - bot_token: '$TELEGRAM_TOKEN'
        chat_id: $TELEGRAM_CHAT_ID
        parse_mode: 'HTML'
        message: |
          🔴 <b>CRITICAL ALERT</b>

          <b>{{ .GroupLabels.alertname }}</b>

          {{ range .Alerts }}
          <b>Summary:</b> {{ .Annotations.summary }}
          <b>Description:</b> {{ .Annotations.description }}
          <b>Severity:</b> {{ .Labels.severity }}
          {{ end }}

    webhook_configs:
      - url: '$DISCORD_WEBHOOK'
        send_resolved: true

  - name: 'warning-telegram'
    telegram_configs:
      - bot_token: '$TELEGRAM_TOKEN'
        chat_id: $TELEGRAM_CHAT_ID
        parse_mode: 'HTML'
        message: |
          🟡 <b>Warning</b>

          <b>{{ .GroupLabels.alertname }}</b>

          {{ range .Alerts }}
          {{ .Annotations.summary }}
          {{ end }}

inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname']
EOF

echo "  ✅ alertmanager.yml 생성 완료"

# 4. Prometheus 설정 업데이트
echo ""
echo "[4/4] Prometheus 설정 업데이트 중..."

# prometheus.yml에 alertmanager 추가
if ! grep -q "alertmanagers:" /opt/g9/monitoring/prometheus.yml; then
    sed -i '/^alerting:/a\  alertmanagers:\n    - static_configs:\n        - targets: ["alertmanager:9093"]' /opt/g9/monitoring/prometheus.yml
    echo "  ✅ Prometheus 설정 업데이트 완료"
else
    echo "  ℹ️ Alertmanager 이미 설정됨"
fi

# 5. 테스트
echo ""
echo "=" * 70
echo "✅ 설정 완료!"
echo "=" * 70
echo ""
echo "🧪 알림 테스트:"
echo ""
echo "1. Telegram 테스트:"
echo "   curl -X POST \\"
echo "     'https://api.telegram.org/bot$TELEGRAM_TOKEN/sendMessage' \\"
echo "     -d 'chat_id=$TELEGRAM_CHAT_ID' \\"
echo "     -d 'text=🔴 테스트: G9 알림 시스템 작동 중!'"
echo ""
echo "2. Discord 테스트:"
echo "   curl -X POST \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"content\":\"🔴 테스트: G9 알림 시스템 작동 중!\"}' \\"
echo "     '$DISCORD_WEBHOOK'"
echo ""
echo "📋 다음 단계:"
echo "   cd /opt/g9/monitoring"
echo "   docker compose up -d  # Alertmanager 시작"
echo ""
