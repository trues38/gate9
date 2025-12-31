#!/bin/bash
#
# G9 프로젝트 정리 - 자동 마이그레이션
# NBA / 경제 분리 구조로 재구성
#

set -e

echo "======================================================================"
echo "🏗️  G9 프로젝트 구조 정리 시작"
echo "======================================================================"
echo ""

# 백업 확인
read -p "현재 폴더를 백업하시겠습니까? (y/n): " BACKUP
if [ "$BACKUP" = "y" ]; then
    echo "백업 생성 중..."
    BACKUP_DIR="../vultr-g9-deploy-backup-$(date +%Y%m%d_%H%M%S)"
    cp -r . "$BACKUP_DIR"
    echo "✅ 백업 완료: $BACKUP_DIR"
    echo ""
fi

# 1단계: 새 디렉토리 구조 생성
echo "[1/5] 새 디렉토리 구조 생성 중..."
mkdir -p domains/nba/{collector,api,analysis,tests,neo4j}
mkdir -p domains/economy/{collector,api,analysis,tests,neo4j}
mkdir -p shared/{adapters,utils,models}
mkdir -p deploy/{vps,docker,monitoring}
mkdir -p docs/{setup,architecture/nba,architecture/economy,api}
mkdir -p scripts
echo "✅ 디렉토리 생성 완료"
echo ""

# 2단계: NBA 코드 이동
echo "[2/5] NBA 코드 이동 중..."

# nba-collector → domains/nba/collector
if [ -d "nba-collector" ]; then
    cp -r nba-collector/sources domains/nba/collector/
    cp -r nba-collector/storage domains/nba/collector/
    cp -r nba-collector/processing domains/nba/collector/
    cp -r nba-collector/scheduling domains/nba/collector/
    cp -r nba-collector/adapters domains/nba/collector/
    cp -r nba-collector/core domains/nba/collector/

    cp nba-collector/app_api.py domains/nba/collector/
    cp nba-collector/main_pipeline.py domains/nba/collector/
    cp nba-collector/Dockerfile domains/nba/collector/
    cp nba-collector/requirements.txt domains/nba/collector/

    # 테스트 파일 이동
    mkdir -p domains/nba/tests
    cp nba-collector/test_*.py domains/nba/tests/ 2>/dev/null || true

    # Neo4j 스키마
    cp nba-collector/neo4j_event_schema.cypher domains/nba/neo4j/ 2>/dev/null || true

    echo "  ✅ nba-collector 이동 완료"
fi

# flask-nba → domains/nba/api
if [ -d "flask-nba" ]; then
    cp -r flask-nba/* domains/nba/api/
    echo "  ✅ flask-nba 이동 완료"
fi

echo "✅ NBA 코드 이동 완료"
echo ""

# 3단계: 배포 스크립트 이동
echo "[3/5] 배포 스크립트 이동 중..."
mv deploy_*.sh deploy/vps/ 2>/dev/null || true
mv update_*.sh deploy/vps/ 2>/dev/null || true
mv setup*.sh deploy/vps/ 2>/dev/null || true
mv add_cors.sh deploy/vps/ 2>/dev/null || true
mv monitor_dashboard.html deploy/monitoring/ 2>/dev/null || true
mv check_vps_status.sh deploy/monitoring/ 2>/dev/null || true

# Docker 설정
cp docker-compose.yml deploy/docker/docker-compose.nba.yml 2>/dev/null || true
cp .env deploy/docker/.env.example 2>/dev/null || true

echo "✅ 배포 스크립트 이동 완료"
echo ""

# 4단계: 문서 이동
echo "[4/5] 문서 정리 중..."
mv QUICKSTART.md docs/setup/ 2>/dev/null || true
mv VPS_DEPLOYMENT*.md docs/setup/ 2>/dev/null || true
mv EASY_DEPLOY.md docs/setup/ 2>/dev/null || true

mv FREE_*.md docs/architecture/ 2>/dev/null || true
mv NBA_*.md docs/architecture/nba/ 2>/dev/null || true

mv nba-collector/README.md docs/architecture/nba/ 2>/dev/null || true
mv nba-collector/IMPLEMENTATION_COMPLETE.md docs/architecture/nba/ 2>/dev/null || true

echo "✅ 문서 정리 완료"
echo ""

# 5단계: 루트 README 생성
echo "[5/5] 새 README 생성 중..."
cat > README.md << 'EOF'
# 🏀 G9 Sports Intelligence Platform

NBA 분석 + 경제 분석 통합 플랫폼

## 📁 프로젝트 구조

- `domains/nba/` - NBA 분석 시스템
- `domains/economy/` - 경제 분석 시스템 (개발 예정)
- `shared/` - 공통 라이브러리
- `deploy/` - 배포 스크립트 및 모니터링
- `docs/` - 문서

## 🚀 빠른 시작

### NBA 분석 시작
```bash
cd domains/nba
docker-compose up -d
```

### 경제 분석 시작
```bash
cd domains/economy
docker-compose up -d
```

### 전체 시스템 시작
```bash
docker-compose up -d
```

## 📚 문서

- [빠른 시작](docs/setup/QUICKSTART.md)
- [VPS 배포](docs/setup/VPS_DEPLOYMENT_GUIDE_NBA.md)
- [NBA 시스템](docs/architecture/nba/)
- [경제 시스템](docs/architecture/economy/)

## 🔗 서비스 URL

- NBA API: http://localhost:8001
- Economy API: http://localhost:8002
- Neo4j NBA: http://localhost:7474
- Neo4j Economy: http://localhost:7475
- N8N: http://localhost:5678
EOF

echo "✅ README 생성 완료"
echo ""

# 정리 - 불필요한 파일 삭제
echo "[정리] 임시 파일 삭제 중..."
rm -f nba-deploy.tar.gz 2>/dev/null || true
rm -f *.tar.gz 2>/dev/null || true
echo "✅ 정리 완료"
echo ""

echo "======================================================================"
echo "✅ 마이그레이션 완료!"
echo "======================================================================"
echo ""
echo "새 구조:"
echo "  - domains/nba/          NBA 분석 시스템"
echo "  - domains/economy/      경제 분석 시스템 (준비됨)"
echo "  - shared/               공통 라이브러리"
echo "  - deploy/               배포 도구"
echo "  - docs/                 문서"
echo ""
echo "다음 단계:"
echo "  1. domains/nba/ 확인"
echo "  2. 경제 분석 시스템 개발 시작"
echo "  3. 공통 라이브러리 추출 (선택)"
echo ""
echo "기존 폴더는 그대로 유지됩니다."
echo "새 구조 확인 후 만족하면 기존 폴더 삭제:"
echo "  rm -rf nba-collector flask-nba"
echo ""
