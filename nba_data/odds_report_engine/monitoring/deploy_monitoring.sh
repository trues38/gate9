#!/bin/bash
# G9 모니터링 스택 VPS 배포 스크립트
# Prometheus + Grafana + Node Exporter + Metrics API

VPS_HOST="141.164.35.214"
VPS_USER="root"
VPS_DIR="/opt/g9/monitoring"
LOCAL_DIR="/Users/js/g9/nba_data/odds_report_engine/monitoring"

echo "🚀 G9 모니터링 스택 VPS 배포"
echo "=" * 70
echo ""
echo "VPS: $VPS_USER@$VPS_HOST"
echo "배포 위치: $VPS_DIR"
echo ""

# 1. VPS 디렉토리 생성
echo "[1/6] VPS 디렉토리 생성..."
ssh $VPS_USER@$VPS_HOST "mkdir -p $VPS_DIR"

# 2. 파일 업로드
echo "[2/6] 설정 파일 업로드 중..."
scp $LOCAL_DIR/prometheus.yml $VPS_USER@$VPS_HOST:$VPS_DIR/
scp $LOCAL_DIR/alerts.yml $VPS_USER@$VPS_HOST:$VPS_DIR/
scp $LOCAL_DIR/docker-compose.yml $VPS_USER@$VPS_HOST:$VPS_DIR/
scp $LOCAL_DIR/metrics_api.py $VPS_USER@$VPS_HOST:$VPS_DIR/
scp $LOCAL_DIR/Dockerfile.metrics $VPS_USER@$VPS_HOST:$VPS_DIR/
scp $LOCAL_DIR/grafana_g9_dashboard.json $VPS_USER@$VPS_HOST:$VPS_DIR/

echo "  ✅ 파일 업로드 완료"

# 3. Docker Compose 실행
echo "[3/6] Docker Compose 스택 시작 중..."

ssh $VPS_USER@$VPS_HOST << 'EOFSSH'
cd /opt/g9/monitoring

# 기존 컨테이너 정리 (있다면)
docker-compose down 2>/dev/null

# 새로 시작
docker-compose up -d

echo "  ✅ 모니터링 스택 실행 완료"
EOFSSH

# 4. 실행 상태 확인
echo "[4/6] 컨테이너 상태 확인..."
ssh $VPS_USER@$VPS_HOST "docker ps | grep -E 'g9-prometheus|g9-grafana|g9-node-exporter|g9-metrics-api'"

# 5. 헬스 체크
echo "[5/6] 헬스 체크 중..."
sleep 10

ssh $VPS_USER@$VPS_HOST << 'EOFSSH'
echo ""
echo "🧪 Prometheus 헬스 체크..."
curl -s http://localhost:9090/-/healthy && echo "  ✅ Prometheus: OK" || echo "  ❌ Prometheus: FAIL"

echo ""
echo "🧪 Grafana 헬스 체크..."
curl -s http://localhost:3000/api/health && echo "  ✅ Grafana: OK" || echo "  ❌ Grafana: FAIL"

echo ""
echo "🧪 Metrics API 헬스 체크..."
curl -s http://localhost:9101/health && echo "  ✅ Metrics API: OK" || echo "  ❌ Metrics API: FAIL"
EOFSSH

# 6. 완료 메시지
echo ""
echo "=" * 70
echo "✅ 배포 완료!"
echo "=" * 70
echo ""
echo "📊 접속 정보:"
echo ""
echo "Grafana:"
echo "  URL: http://$VPS_HOST:3000"
echo "  ID: admin"
echo "  PW: g9admin2025"
echo ""
echo "Prometheus:"
echo "  URL: http://$VPS_HOST:9090"
echo ""
echo "Metrics API:"
echo "  URL: http://$VPS_HOST:9101/metrics"
echo "  Health: http://$VPS_HOST:9101/health"
echo ""
echo "📋 다음 단계:"
echo "  1. Grafana에서 Prometheus 데이터소스 추가"
echo "  2. G9 대시보드 JSON 임포트"
echo "  3. 파이프라인에 메트릭 기록 추가"
echo ""
echo "🎯 메트릭 기록 예시:"
echo "  curl http://localhost:9101/api/record_api_call/odds_api"
echo "  curl http://localhost:9101/api/record_odds_snapshot/401810214"
echo "  curl http://localhost:9101/api/record_job_heartbeat/nba_collector"
echo ""

echo "🎉 G9 모니터링 스택 배포 완료!"
