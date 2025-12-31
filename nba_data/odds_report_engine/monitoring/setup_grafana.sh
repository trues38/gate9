#!/bin/bash
# Grafana 자동 설정 스크립트
# 1. Prometheus 데이터소스 추가
# 2. G9 대시보드 임포트

GRAFANA_URL="http://localhost:3000"
GRAFANA_USER="admin"
GRAFANA_PASS="g9admin2025"

echo "🎨 Grafana 자동 설정 시작"
echo "=" * 70
echo ""

# 1. Grafana 헬스 체크
echo "[1/3] Grafana 헬스 체크..."
if curl -s "$GRAFANA_URL/api/health" | grep -q "ok"; then
    echo "  ✅ Grafana 실행 중"
else
    echo "  ❌ Grafana 실행 안됨"
    exit 1
fi

# 2. Prometheus 데이터소스 추가
echo "[2/3] Prometheus 데이터소스 추가..."

curl -s -X POST \
  -H "Content-Type: application/json" \
  -u "$GRAFANA_USER:$GRAFANA_PASS" \
  -d '{
    "name": "Prometheus",
    "type": "prometheus",
    "url": "http://prometheus:9090",
    "access": "proxy",
    "isDefault": true,
    "jsonData": {
      "httpMethod": "POST"
    }
  }' \
  "$GRAFANA_URL/api/datasources" > /tmp/grafana_datasource_result.json

if grep -q "error" /tmp/grafana_datasource_result.json; then
    # 이미 존재할 수 있음
    if grep -q "already exists" /tmp/grafana_datasource_result.json; then
        echo "  ℹ️ Prometheus 데이터소스 이미 존재"
    else
        echo "  ⚠️ 데이터소스 추가 실패"
        cat /tmp/grafana_datasource_result.json
    fi
else
    echo "  ✅ Prometheus 데이터소스 추가 완료"
fi

# 3. G9 대시보드 임포트
echo "[3/3] G9 대시보드 임포트..."

# 대시보드 JSON 읽기
DASHBOARD_JSON=$(cat /opt/g9/monitoring/grafana_g9_dashboard.json)

# 대시보드 임포트 페이로드 생성
curl -s -X POST \
  -H "Content-Type: application/json" \
  -u "$GRAFANA_USER:$GRAFANA_PASS" \
  -d "{
    \"dashboard\": $DASHBOARD_JSON,
    \"overwrite\": true,
    \"inputs\": [],
    \"folderId\": 0
  }" \
  "$GRAFANA_URL/api/dashboards/db" > /tmp/grafana_dashboard_result.json

if grep -q "success\|Imported" /tmp/grafana_dashboard_result.json; then
    echo "  ✅ G9 대시보드 임포트 완료"

    # 대시보드 URL 추출
    DASHBOARD_URL=$(cat /tmp/grafana_dashboard_result.json | grep -o '"url":"[^"]*"' | cut -d'"' -f4)
    echo ""
    echo "📊 대시보드 URL:"
    echo "   http://141.164.35.214:3000$DASHBOARD_URL"
else
    echo "  ⚠️ 대시보드 임포트 실패"
    cat /tmp/grafana_dashboard_result.json
fi

echo ""
echo "=" * 70
echo "✅ Grafana 설정 완료!"
echo "=" * 70
echo ""
echo "📊 접속 정보:"
echo "   URL: http://141.164.35.214:3000"
echo "   ID: admin"
echo "   PW: g9admin2025"
echo ""
echo "📋 메인 대시보드:"
echo "   G9 운영 대시보드 - NBA + 경제 통합 모니터링"
echo ""
