#!/bin/bash
# Grafana 대시보드 데이터소스 수정 및 재임포트

GRAFANA_URL="http://localhost:3000"
GRAFANA_USER="admin"
GRAFANA_PASS="g9admin2025"

echo "🔧 Grafana 대시보드 데이터소스 수정"
echo "=" * 70

# 1. Prometheus 데이터소스 UID 가져오기
echo "[1/3] Prometheus 데이터소스 UID 확인..."
DS_UID=$(curl -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
  "$GRAFANA_URL/api/datasources" | \
  jq -r '.[] | select(.type == "prometheus") | .uid')

echo "  Prometheus UID: $DS_UID"

# 2. 대시보드 JSON 수정
echo "[2/3] 대시보드 JSON 수정 중..."

# 원본 JSON 읽기
DASHBOARD_JSON=$(cat /opt/g9/monitoring/grafana_g9_dashboard.json)

# datasource를 UID로 변경
UPDATED_JSON=$(echo "$DASHBOARD_JSON" | jq --arg uid "$DS_UID" '
  .panels |= map(
    if .targets then
      .targets |= map(
        .datasource = {"type": "prometheus", "uid": $uid}
      )
    else
      .
    end
  )
')

# 3. 대시보드 재임포트
echo "[3/3] 대시보드 재임포트..."

curl -s -X POST \
  -H "Content-Type: application/json" \
  -u "$GRAFANA_USER:$GRAFANA_PASS" \
  -d "{
    \"dashboard\": $UPDATED_JSON,
    \"overwrite\": true,
    \"folderId\": 0
  }" \
  "$GRAFANA_URL/api/dashboards/db" | jq -r '.status, .url'

echo ""
echo "=" * 70
echo "✅ 대시보드 데이터소스 수정 완료!"
echo "=" * 70
echo ""
echo "📊 대시보드 URL:"
echo "   http://141.164.35.214:3000/d/g9-main-dashboard"
echo ""
