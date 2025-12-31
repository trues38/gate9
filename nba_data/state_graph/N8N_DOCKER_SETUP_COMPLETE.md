# ✅ n8n Docker 구성 완료

## 📦 생성된 파일

| 파일 | 크기 | 용도 |
|------|------|------|
| `docker-compose-n8n.yml` | 1.7KB | n8n Docker Compose 설정 |
| `.env.n8n.example` | 421B | 환경변수 템플릿 |
| `deploy_n8n.sh` | 2.6KB | 자동 배포 스크립트 |
| `cleanup_n8n.sh` | 1.9KB | 정리 스크립트 |
| `test_neo4j_connection.py` | 8.6KB | Neo4j 연결 테스트 |
| `N8N_QUICKSTART.md` | 11KB | 빠른 시작 가이드 |

---

## 🏗️ 시스템 아키텍처

### 현재 상태

```
┌────────────────────────────────────────────────┐
│  기존 Neo4j (건드리지 않음)                     │
│  ┌──────────────┐                              │
│  │              │                              │
│  │  neo4j-nba   │  ✅ 16시간 실행 중            │
│  │              │  ✅ NBA 데이터 임포트 완료     │
│  │  :7474       │                              │
│  │  :7687       │                              │
│  └──────────────┘                              │
└────────────────────────────────────────────────┘

┌────────────────────────────────────────────────┐
│  신규 추가 (이제 배포할 것)                     │
│  ┌──────────────┐                              │
│  │              │                              │
│  │   n8n-nba    │  🆕 새로 추가                │
│  │              │                              │
│  │  :5678       │                              │
│  └──────────────┘                              │
└────────────────────────────────────────────────┘

┌────────────────────────────────────────────────┐
│  네트워크 연결 (자동)                           │
│                                                │
│         nba-network (bridge)                   │
│              │                                 │
│    ┌─────────┴─────────┐                      │
│    │                   │                      │
│  neo4j-nba         n8n-nba                    │
│    │                   │                      │
│    └───────────────────┘                      │
│                                                │
│  컨테이너 간 통신:                              │
│  bolt://neo4j-nba:7687                        │
└────────────────────────────────────────────────┘
```

### 네트워크 구조

**Before** (배포 전):
```
neo4j-nba: bridge (기본 네트워크)
n8n-nba: 없음
```

**After** (배포 후):
```
neo4j-nba: bridge + nba-network
n8n-nba: nba-network

→ 같은 네트워크에서 컨테이너 이름으로 통신 가능
```

---

## 🚀 즉시 배포 (3단계)

### Step 1: 환경변수 설정 (2분)

```bash
# 템플릿 복사
cp .env.n8n.example .env.n8n

# 편집
vim .env.n8n
```

**필수 항목**:
- `NEO4J_PASSWORD`: Neo4j 비밀번호
- `OPENROUTER_API_KEY`: Grok API Key
- `ANTHROPIC_API_KEY`: Claude API Key
- `TELEGRAM_BOT_TOKEN`: Telegram Bot Token
- `TELEGRAM_CHAT_ID`: Telegram Chat ID

### Step 2: 배포 실행 (3분)

```bash
./deploy_n8n.sh
```

**자동으로 수행하는 작업**:
1. ✅ 환경변수 파일 확인
2. ✅ Neo4j 컨테이너 실행 확인
3. ✅ nba-network 생성
4. ✅ neo4j-nba를 nba-network에 연결
5. ✅ n8n 컨테이너 시작
6. ✅ 헬스체크 대기

**출력**:
```
✅ 배포 완료!

📌 n8n 웹 UI:
   http://localhost:5678

📌 로그인 정보:
   Username: admin
   Password: n8n_nba_2025
```

### Step 3: Neo4j 연결 확인 (1분)

```bash
# 환경변수 로드
source .env.n8n

# 테스트 실행
python3 test_neo4j_connection.py
```

**테스트 항목**:
- ✅ 호스트 → Neo4j 연결
- ✅ NBA 데이터 확인 (Player, Team, Game 노드)
- ✅ n8n 쿼리 테스트 (Event 노드 CRUD)
- ✅ n8n 컨테이너 → Neo4j 연결

---

## 🌐 n8n 웹 UI 설정 (5분)

### 1. 접속

http://localhost:5678

### 2. Credentials 설정

**Neo4j** (가장 중요):
- URI: `bolt://neo4j-nba:7687` ← **컨테이너 이름**
- Username: `neo4j`
- Password: (환경변수 값)

**OpenRouter** (Grok):
- Type: HTTP Header Auth
- Header Name: `Authorization`
- Header Value: `Bearer ${OPENROUTER_API_KEY}`

**Anthropic** (Claude):
- Type: HTTP Header Auth
- Header Name: `x-api-key`
- Header Value: `${ANTHROPIC_API_KEY}`

**Telegram**:
- Access Token: `${TELEGRAM_BOT_TOKEN}`

### 3. 워크플로우 Import

1. Workflows → Import from File
2. 파일: `n8n_nba_realtime_workflow.json`
3. Credentials 연결
4. 수동 실행 테스트
5. Active 토글 → 활성화

---

## 🔑 핵심 포인트

### 1. Neo4j 연결 방법

**❌ 잘못된 방법** (작동 안 함):
```
URI: bolt://localhost:7687
```

**✅ 올바른 방법** (n8n에서):
```
URI: bolt://neo4j-nba:7687
```

**이유**: n8n 컨테이너 내부에서는 `localhost`가 n8n 자신을 가리킴. Neo4j에 접근하려면 **컨테이너 이름**을 사용해야 함.

### 2. 네트워크 구조

```
호스트 (macOS)
  ↓ localhost:7687
neo4j-nba (컨테이너)
  ↑ neo4j-nba:7687
n8n-nba (컨테이너)
```

- **호스트 → Neo4j**: `localhost:7687` (포트 매핑)
- **n8n → Neo4j**: `neo4j-nba:7687` (컨테이너 이름)

### 3. 기존 Neo4j 보존

**배포 스크립트가 하는 일**:
- ✅ 기존 neo4j-nba 컨테이너는 그대로 유지
- ✅ 네트워크만 추가로 연결 (`docker network connect`)
- ✅ 데이터 손실 없음

**확인**:
```bash
# 배포 전
docker inspect neo4j-nba --format '{{range .NetworkSettings.Networks}}{{.NetworkID}}{{end}}'
# → bridge

# 배포 후
docker inspect neo4j-nba --format '{{range .NetworkSettings.Networks}}{{.NetworkID}}{{end}}'
# → bridge, nba-network
```

---

## 📊 테스트 체크리스트

배포 후 확인:

- [ ] `docker ps | grep neo4j-nba` → 실행 중
- [ ] `docker ps | grep n8n-nba` → 실행 중
- [ ] `docker network inspect nba-network` → 두 컨테이너 포함
- [ ] `python3 test_neo4j_connection.py` → 모든 테스트 통과
- [ ] http://localhost:5678 → n8n 웹 UI 접속 가능
- [ ] Neo4j Credential Test → ✅ Connection successful
- [ ] 워크플로우 수동 실행 → 성공
- [ ] Telegram 알림 → 수신 확인

---

## 🐛 트러블슈팅

### n8n → Neo4j 연결 실패

**증상**:
```
Connection refused: bolt://neo4j-nba:7687
```

**해결**:
```bash
# 1. 네트워크 확인
docker network inspect nba-network | grep neo4j-nba

# 2. 네트워크 연결 (수동)
docker network connect nba-network neo4j-nba

# 3. n8n 재시작
docker restart n8n-nba
```

### 환경변수 인식 안 됨

**증상**:
```
NEO4J_PASSWORD가 빈 값
```

**해결**:
```bash
# 1. .env.n8n 파일 확인
cat .env.n8n | grep NEO4J_PASSWORD

# 2. 재배포 (환경변수 다시 로드)
docker-compose -f docker-compose-n8n.yml --env-file .env.n8n down
docker-compose -f docker-compose-n8n.yml --env-file .env.n8n up -d
```

### 포트 충돌

**증상**:
```
Error: port 5678 is already in use
```

**해결**:
```bash
# 1. 포트 사용 프로세스 확인
lsof -i :5678

# 2. docker-compose-n8n.yml 편집
ports:
  - "5679:5678"  # 다른 포트로 변경
```

---

## 🧹 정리

### n8n만 삭제 (데이터 보존)

```bash
./cleanup_n8n.sh
```

**삭제되는 것**:
- n8n 컨테이너
- nba-network

**보존되는 것**:
- n8n 데이터 볼륨 (워크플로우 포함)
- Neo4j 컨테이너 및 데이터

### 완전 삭제 (데이터 포함)

```bash
./cleanup_n8n.sh --full
```

**삭제되는 것**:
- n8n 컨테이너
- nba-network
- n8n 데이터 볼륨

---

## 📚 관련 문서

| 문서 | 용도 |
|------|------|
| `N8N_QUICKSTART.md` | 빠른 시작 가이드 (상세) |
| `N8N_DEPLOYMENT_GUIDE.md` | 전체 배포 가이드 (n8n 일반) |
| `GROK_OPENROUTER_SETUP.md` | Grok API 설정 |
| `NBA_REALTIME_PIPELINE_README.md` | 전체 시스템 개요 |

---

## 🎯 다음 단계

### 즉시 실행 가능

1. **환경변수 설정**:
   ```bash
   cp .env.n8n.example .env.n8n
   vim .env.n8n
   ```

2. **배포**:
   ```bash
   ./deploy_n8n.sh
   ```

3. **테스트**:
   ```bash
   source .env.n8n
   python3 test_neo4j_connection.py
   ```

4. **n8n 접속**:
   ```
   http://localhost:5678
   ```

5. **워크플로우 Import**:
   ```
   n8n_nba_realtime_workflow.json
   ```

### 프로덕션 준비

- [ ] HTTPS 설정 (Let's Encrypt)
- [ ] 비밀번호 강화
- [ ] 자동 백업 설정
- [ ] 모니터링 대시보드
- [ ] 에러 알림 (Slack/Discord)

---

## 🎉 요약

✅ **Docker 기반 n8n + Neo4j 통합 완료**

**특징**:
- ✅ 기존 Neo4j 컨테이너 보존
- ✅ 자동 네트워크 연결
- ✅ 완전 자동화된 배포 스크립트
- ✅ 포괄적인 연결 테스트
- ✅ 한 번의 명령으로 배포 가능

**배포 시간**: 5분

**명령어**:
```bash
# 1. 환경변수 설정
cp .env.n8n.example .env.n8n && vim .env.n8n

# 2. 배포
./deploy_n8n.sh

# 3. 테스트
source .env.n8n && python3 test_neo4j_connection.py

# 4. 접속
open http://localhost:5678
```

**즉시 사용 가능!** 🚀
