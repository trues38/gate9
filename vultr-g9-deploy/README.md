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
