#!/bin/bash
#
# G9 프로젝트 정리 - 안전 마이그레이션
# 삭제 대상은 _deprecated/ 폴더에 모아두고, 핵심만 새 구조로 이동
#

set -e

echo "======================================================================"
echo "🏗️  G9 프로젝트 안전 정리 시작"
echo "======================================================================"
echo ""
echo "전략:"
echo "  ✅ 핵심 파일 → 새 구조로 복사"
echo "  📦 삭제 대상 → _deprecated/ 폴더로 이동"
echo "  🧹 나중에 _deprecated/ 폴더만 삭제"
echo ""

read -p "계속하시겠습니까? (y/n): " CONFIRM
if [ "$CONFIRM" != "y" ]; then
    echo "취소되었습니다."
    exit 0
fi

echo ""

# 0단계: 삭제 대상 폴더 생성
echo "[0/6] 삭제 대상 폴더 생성..."
mkdir -p _deprecated/{scripts,docs,temp}
echo "✅ _deprecated/ 폴더 생성 완료"
echo ""

# 1단계: 새 디렉토리 구조 생성
echo "[1/6] 새 디렉토리 구조 생성 중..."
mkdir -p domains/nba/{collector,api,analysis,tests,neo4j,docs}
mkdir -p domains/economy/{collector,api,analysis,tests,neo4j,docs}
mkdir -p shared/{adapters,utils,models}
mkdir -p deploy/{vps,docker,monitoring}
mkdir -p docs/{setup,architecture,api}
mkdir -p scripts
echo "✅ 디렉토리 생성 완료"
echo ""

# 2단계: NBA 핵심 코드 이동 (복사)
echo "[2/6] NBA 핵심 코드 이동 중..."

if [ -d "nba-collector" ]; then
    # 핵심 디렉토리 복사
    echo "  - nba-collector/sources → domains/nba/collector/sources"
    cp -r nba-collector/sources domains/nba/collector/

    echo "  - nba-collector/storage → domains/nba/collector/storage"
    cp -r nba-collector/storage domains/nba/collector/

    echo "  - nba-collector/processing → domains/nba/collector/processing"
    cp -r nba-collector/processing domains/nba/collector/

    echo "  - nba-collector/scheduling → domains/nba/collector/scheduling"
    cp -r nba-collector/scheduling domains/nba/collector/

    echo "  - nba-collector/adapters → domains/nba/collector/adapters"
    cp -r nba-collector/adapters domains/nba/collector/ 2>/dev/null || true

    echo "  - nba-collector/core → domains/nba/collector/core"
    cp -r nba-collector/core domains/nba/collector/ 2>/dev/null || true

    # 핵심 파일 복사
    echo "  - 핵심 파일 복사..."
    cp nba-collector/app_api.py domains/nba/collector/ 2>/dev/null || true
    cp nba-collector/main_pipeline.py domains/nba/collector/ 2>/dev/null || true
    cp nba-collector/Dockerfile domains/nba/collector/
    cp nba-collector/requirements.txt domains/nba/collector/

    # 테스트 파일
    echo "  - 테스트 파일 → domains/nba/tests/"
    mkdir -p domains/nba/tests
    cp nba-collector/test_*.py domains/nba/tests/ 2>/dev/null || true

    # Neo4j 스키마
    echo "  - Neo4j 스키마 → domains/nba/neo4j/"
    cp nba-collector/*.cypher domains/nba/neo4j/ 2>/dev/null || true

    # 문서
    echo "  - 문서 → domains/nba/docs/"
    cp nba-collector/*.md domains/nba/docs/ 2>/dev/null || true

    echo "✅ NBA 핵심 코드 복사 완료"
fi
echo ""

# flask-nba
if [ -d "flask-nba" ]; then
    echo "  - flask-nba → domains/nba/api"
    cp -r flask-nba/* domains/nba/api/
    echo "✅ flask-nba 복사 완료"
fi
echo ""

# 3단계: 배포 스크립트 정리
echo "[3/6] 배포 스크립트 정리 중..."

# 유지할 배포 스크립트만 deploy/로 복사
echo "  - 핵심 배포 스크립트 → deploy/vps/"
cp update_to_opt_g9.sh deploy/vps/ 2>/dev/null || true
cp check_vps_status.sh deploy/monitoring/ 2>/dev/null || true
cp monitor_dashboard.html deploy/monitoring/ 2>/dev/null || true

# Docker 설정
echo "  - Docker 설정 → deploy/docker/"
cp docker-compose.yml deploy/docker/docker-compose.nba.yml 2>/dev/null || true
cp .env deploy/docker/.env.example 2>/dev/null || true
cp .env.example deploy/docker/ 2>/dev/null || true

# 나머지 배포 스크립트는 deprecated로
echo "  - 구 배포 스크립트 → _deprecated/scripts/"
mv deploy_*.sh _deprecated/scripts/ 2>/dev/null || true
mv setup*.sh _deprecated/scripts/ 2>/dev/null || true
mv add_cors.sh _deprecated/scripts/ 2>/dev/null || true
mv install_*.sh _deprecated/scripts/ 2>/dev/null || true
mv remote_*.sh _deprecated/scripts/ 2>/dev/null || true
mv manual_*.sh _deprecated/scripts/ 2>/dev/null || true
mv vps_*.sh _deprecated/scripts/ 2>/dev/null || true
mv update_nba_collector.sh _deprecated/scripts/ 2>/dev/null || true

echo "✅ 배포 스크립트 정리 완료"
echo ""

# 4단계: 문서 정리
echo "[4/6] 문서 정리 중..."

# 핵심 문서만 docs/로 복사
echo "  - 핵심 문서 → docs/"
cp README.md docs/README_OLD.md 2>/dev/null || true
cp VPS_DEPLOYMENT_GUIDE_NBA.md docs/setup/ 2>/dev/null || true
cp NBA_COLLECTOR_QUICKSTART.md docs/setup/ 2>/dev/null || true
cp FREE_PIPELINE_GUIDE.md docs/architecture/ 2>/dev/null || true

# 나머지 문서는 deprecated로
echo "  - 구 문서 → _deprecated/docs/"
mv *.md _deprecated/docs/ 2>/dev/null || true
mv CLEANUP_PROPOSAL.md . 2>/dev/null || true  # 이건 유지

echo "✅ 문서 정리 완료"
echo ""

# 5단계: 임시/테스트 파일 정리
echo "[5/6] 임시/테스트 파일 정리 중..."

echo "  - 압축 파일 → _deprecated/temp/"
mv *.tar.gz _deprecated/temp/ 2>/dev/null || true

echo "  - JSON 파일 → _deprecated/temp/"
mv *.json _deprecated/temp/ 2>/dev/null || true

echo "✅ 임시 파일 정리 완료"
echo ""

# 6단계: 루트 README 및 docker-compose 생성
echo "[6/6] 새 프로젝트 파일 생성 중..."

# 루트 README
cat > README.md << 'EOF'
# 🏀💰 G9 Sports Intelligence Platform

NBA 분석 + 경제 분석 통합 플랫폼

## 📁 프로젝트 구조

```
g9-sports-intelligence/
├── domains/
│   ├── nba/              # 🏀 NBA 분석 시스템
│   │   ├── collector/    # 데이터 수집 (Twitter241 API)
│   │   ├── api/          # Flask REST API
│   │   ├── analysis/     # 분석 엔진
│   │   ├── tests/        # 테스트
│   │   └── neo4j/        # 그래프 DB 스키마
│   │
│   └── economy/          # 💰 경제 분석 시스템 (준비중)
│       ├── collector/
│       ├── api/
│       └── analysis/
│
├── shared/               # 🔧 공통 라이브러리
│   ├── adapters/
│   ├── utils/
│   └── models/
│
├── deploy/               # 🚀 배포 도구
│   ├── vps/             # VPS 배포 스크립트
│   ├── docker/          # Docker 설정
│   └── monitoring/      # 모니터링 도구
│
├── docs/                 # 📚 문서
│   ├── setup/
│   ├── architecture/
│   └── api/
│
└── _deprecated/          # 🗑️ 삭제 예정 (확인 후 삭제)
    ├── scripts/
    ├── docs/
    └── temp/
```

## 🚀 빠른 시작

### NBA 분석 시스템
```bash
cd domains/nba/collector
docker-compose up -d
```

### 경제 분석 시스템 (준비중)
```bash
cd domains/economy/collector
docker-compose up -d
```

### 전체 시스템
```bash
docker-compose up -d
```

## 📊 서비스 URL

- **NBA Collector API**: http://localhost:8001
- **NBA Neo4j**: http://localhost:7474
- **Economy API**: http://localhost:8002 (준비중)
- **N8N Workflows**: http://localhost:5678
- **모니터링**: `open deploy/monitoring/monitor_dashboard.html`

## 📚 문서

- [빠른 시작](docs/setup/NBA_COLLECTOR_QUICKSTART.md)
- [VPS 배포](docs/setup/VPS_DEPLOYMENT_GUIDE_NBA.md)
- [시스템 아키텍처](docs/architecture/FREE_PIPELINE_GUIDE.md)

## 🛠 개발

### NBA Collector 테스트
```bash
cd domains/nba/tests
python test_real_api.py
```

### 배포
```bash
cd deploy/vps
./update_to_opt_g9.sh
```

## 🧹 정리

현재 `_deprecated/` 폴더에 구 파일들이 있습니다.

**확인 후 삭제:**
```bash
# 새 구조가 정상 작동하면
rm -rf _deprecated/
rm -rf nba-collector/
rm -rf flask-nba/
```

## 📝 변경사항

- ✅ NBA / 경제 도메인 분리
- ✅ 배포 스크립트 정리
- ✅ 문서 체계화
- ✅ 테스트 파일 분리
- 🔜 공통 라이브러리 추출 (shared/)
- 🔜 경제 분석 시스템 개발

---

**버전**: 3.0.0 (Clean Architecture)
**마지막 정리**: $(date +%Y-%m-%d)
EOF

# 루트 docker-compose (통합)
cat > docker-compose.yml << 'EOF'
version: '3.8'

# NBA + Economy 통합 시스템
# 개별 실행: cd domains/nba && docker-compose up -d

services:
  # NBA 시스템은 domains/nba/docker-compose.yml 참조
  # Economy 시스템은 domains/economy/docker-compose.yml 참조

  # 통합 실행하려면:
  # docker-compose -f domains/nba/docker-compose.yml -f domains/economy/docker-compose.yml up -d

  # 모니터링
  monitoring:
    image: nginx:alpine
    container_name: g9-monitoring
    ports:
      - "8080:80"
    volumes:
      - ./deploy/monitoring:/usr/share/nginx/html
    restart: unless-stopped

networks:
  g9_network:
    driver: bridge

# 상세 설정은 deploy/docker/ 참조
EOF

echo "✅ 새 프로젝트 파일 생성 완료"
echo ""

# 완료 메시지
echo "======================================================================"
echo "✅ 안전 마이그레이션 완료!"
echo "======================================================================"
echo ""
echo "📁 새 구조:"
echo "  ✅ domains/nba/          - NBA 분석 시스템 (이동 완료)"
echo "  📦 domains/economy/      - 경제 분석 시스템 (준비됨)"
echo "  🔧 shared/               - 공통 라이브러리 (준비됨)"
echo "  🚀 deploy/               - 배포 도구 (정리됨)"
echo "  📚 docs/                 - 문서 (정리됨)"
echo ""
echo "🗑️  삭제 대상:"
echo "  📦 _deprecated/scripts/  - 구 배포 스크립트 (15개)"
echo "  📦 _deprecated/docs/     - 구 문서 (8개)"
echo "  📦 _deprecated/temp/     - 임시 파일"
echo ""
echo "⚠️  아직 남아있는 폴더 (확인 후 수동 삭제):"
echo "  - nba-collector/         (백업용)"
echo "  - flask-nba/             (백업용)"
echo ""
echo "🎯 다음 단계:"
echo "  1. 새 구조 확인:"
echo "     cd domains/nba/collector && ls -la"
echo ""
echo "  2. NBA 시스템 테스트:"
echo "     cd domains/nba/tests"
echo "     python test_real_api.py"
echo ""
echo "  3. 정상 작동 확인 후 정리:"
echo "     rm -rf _deprecated/"
echo "     rm -rf nba-collector/"
echo "     rm -rf flask-nba/"
echo ""
echo "  4. 경제 분석 시스템 개발 시작!"
echo ""
