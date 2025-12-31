# G9 Platform - Vultr 완전 자동 배포

**구성:**
- n8n (워크플로우 자동화)
- Neo4j NBA (NBA 실시간 이벤트 + 박스스코어)
- Neo4j Economy (경제 레짐 분석)
- Flask NBA API (박스스코어 자동 수집)

**비용:** $0.90/월 (LLM) + VPS 비용

---

## 🚀 빠른 시작 (3단계, 10분)

### 1. VPS에 파일 업로드

```bash
# 로컬 (맥북)
cd /Users/js/g9
scp -r vultr-g9-deploy root@YOUR_VULTR_IP:~/

# VPS 접속
ssh root@YOUR_VULTR_IP
cd ~/vultr-g9-deploy
```

### 2. 자동 설치 실행

```bash
chmod +x setup.sh
./setup.sh
```

**스크립트가 자동으로:**
- ✅ Docker 설치
- ✅ Docker Compose 설치
- ✅ 메모리 자동 설정 (RAM 크기에 맞춰)
- ✅ 방화벽 설정
- ✅ 모든 서비스 시작

### 3. 접속 확인

```
n8n:           http://YOUR_IP:5678
Neo4j NBA:     http://YOUR_IP:7474
Neo4j Economy: http://YOUR_IP:7475
Flask NBA API: http://YOUR_IP:8000/health
```

---

## 📦 서비스 구성

| 서비스 | 포트 | 설명 |
|--------|------|------|
| n8n | 5678 | 워크플로우 (Nitter RSS + Grok X Search) |
| Neo4j NBA | 7474, 7687 | NBA 실시간 이벤트 + 박스스코어 저장 |
| Neo4j Economy | 7475, 7688 | 경제 레짐 분석 |
| Flask NBA API | 8000 | ESPN 박스스코어 자동 수집 |

---

## 🔐 로그인 정보

**n8n:**
- URL: http://YOUR_IP:5678
- ID: admin
- PW: (`.env` 파일의 `N8N_PASSWORD`)

**Neo4j NBA:**
- URL: http://YOUR_IP:7474
- Username: neo4j
- Password: (`.env` 파일의 `NEO4J_NBA_PASSWORD`)

**Neo4j Economy:**
- URL: http://YOUR_IP:7475
- Username: neo4j
- Password: (`.env` 파일의 `NEO4J_ECONOMY_PASSWORD`)

**비밀번호 확인:**
```bash
cat .env | grep PASSWORD
```

---

## 🏀 Flask NBA API 사용법

### 헬스 체크
```bash
curl http://YOUR_IP:8000/health
```

### 어제 경기 수동 수집
```bash
curl -X POST http://YOUR_IP:8000/collect/yesterday
```

### 특정 날짜 경기 수집
```bash
curl -X POST http://YOUR_IP:8000/collect/date \
  -H "Content-Type: application/json" \
  -d '{"date": "20251225"}'
```

### 자동 수집
- **매일 오전 9시** 자동으로 어제 경기 수집
- 별도 설정 불필요

---

## 📋 Neo4j Economy 초기화

Neo4j Economy Browser (http://YOUR_IP:7475) 접속 후:

```cypher
CREATE (f:InfluenceFactor {
  name: 'Interest Rate',
  category: 'Monetary Policy',
  impact_sectors: ['Tech', 'Real Estate', 'Financials'],
  current_regime: 'High Rate',
  updated_at: datetime()
})

CREATE (f:InfluenceFactor {
  name: 'Liquidity',
  category: 'Monetary Policy',
  impact_sectors: ['Growth Stocks', 'Crypto', 'Small Cap'],
  current_regime: 'Tight',
  updated_at: datetime()
})

CREATE (f:InfluenceFactor {
  name: 'Market Sentiment',
  category: 'Psychology',
  impact_sectors: ['All'],
  current_regime: 'Neutral',
  updated_at: datetime()
})

CREATE (f:InfluenceFactor {
  name: 'Dollar Strength',
  category: 'Currency',
  impact_sectors: ['Commodities', 'Emerging Markets', 'Exporters'],
  current_regime: 'Strong',
  updated_at: datetime()
})

CREATE (f:InfluenceFactor {
  name: 'Geopolitical Risk',
  category: 'Politics',
  impact_sectors: ['Energy', 'Defense', 'Safe Haven'],
  current_regime: 'Elevated',
  updated_at: datetime()
})
```

---

## 🔍 데이터 확인

### Neo4j NBA - 박스스코어 확인
```cypher
MATCH (g:Game)
RETURN g
ORDER BY g.updated_at DESC
LIMIT 10
```

### Neo4j NBA - 실시간 이벤트 확인
```cypher
MATCH (e:NBAEvent)
RETURN e.player, e.status, e.reason, e.created_at
ORDER BY e.created_at DESC
LIMIT 10
```

### Neo4j Economy - 경제 이벤트 확인
```cypher
MATCH (e:Event)-[r:AFFECTS]->(f:InfluenceFactor)
RETURN e.title, e.narrative, f.name, r.magnitude
ORDER BY e.created_at DESC
LIMIT 10
```

---

## 🔧 유용한 명령어

### 서비스 관리
```bash
# 전체 로그 확인
docker-compose logs -f

# 특정 서비스 로그
docker-compose logs -f flask-nba

# 서비스 재시작
docker-compose restart

# 서비스 중지
docker-compose down

# 서비스 시작
docker-compose up -d

# 상태 확인
docker-compose ps
```

### 리소스 확인
```bash
# 메모리/CPU 사용량
docker stats

# 디스크 사용량
df -h
```

---

## 📊 폴더 구조

```
vultr-g9-deploy/
├── setup.sh                    # 자동 설치 스크립트
├── docker-compose.yml          # 4개 서비스 정의
├── .env.example                # 환경변수 템플릿
├── .env                        # 실제 환경변수 (자동 생성)
├── README.md                   # 이 파일
└── flask-nba/                  # NBA 박스스코어 API
    ├── Dockerfile
    ├── requirements.txt
    └── app.py                  # Flask API 메인
```

---

## 💡 다음 단계

### 1. n8n 워크플로우 임포트
```
1. n8n 접속 (http://YOUR_IP:5678)
2. Import from File
3. 파일: g9_deploy_ready_final.json (별도 제공)
4. Credentials 설정 (Neo4j NBA, Neo4j Economy)
5. Active 켜기
```

### 2. 테스트
```bash
# Flask API 테스트
curl -X POST http://YOUR_IP:8000/collect/yesterday

# Neo4j에 데이터 들어왔는지 확인
# http://YOUR_IP:7474 접속 후:
MATCH (g:Game) RETURN count(g)
```

### 3. 모니터링
```bash
# 일일 비용 확인 (Neo4j Economy)
MATCH (e)
WHERE date(e.created_at) = date()
RETURN labels(e)[0] as domain, count(e) as count, sum(e.cost_usd) as cost
```

---

## ⚠️ 트러블슈팅

### Flask NBA API가 시작 안됨
```bash
docker-compose logs flask-nba
# Neo4j NBA가 먼저 시작되어야 함 (healthcheck)
```

### Neo4j 비밀번호 잠김
```bash
# 재시작 (데이터 유지)
docker-compose restart neo4j-nba

# 10초 대기 후 재접속
```

### 메모리 부족
```bash
# .env 파일에서 메모리 줄이기
nano .env
# NEO4J_NBA_HEAP_MAX=2G → 1G로 변경
docker-compose restart
```

---

## 💰 월간 비용

| 항목 | 비용 |
|------|------|
| NBA (Nitter RSS + 로직) | $0/월 |
| Economy (Grok X Search) | $0.90/월 |
| Flask NBA API (ESPN) | $0/월 |
| VPS (Vultr) | $6-12/월 |
| **합계** | **~$7-13/월** |

---

**Contact:** js@g9platform.com
**Status:** 프로덕션 준비 완료
**Last Updated:** 2025-12-26
