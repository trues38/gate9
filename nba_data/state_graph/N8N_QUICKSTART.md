# n8n NBA 실시간 파이프라인 - 빠른 시작

## 🎯 목표

기존 Neo4j (neo4j-nba) 컨테이너에 n8n을 연결하여 실시간 NBA 이벤트 파이프라인 구축

---

## 📋 사전 확인

### 1. Neo4j 컨테이너 실행 중인지 확인

```bash
docker ps | grep neo4j-nba
```

**출력 예시**:
```
051d1cf0f37c   neo4j-nba   Up 16 hours   0.0.0.0:7474->7474/tcp, 0.0.0.0:7687->7687/tcp
```

만약 실행 중이 아니면:
```bash
docker start neo4j-nba
```

### 2. Neo4j 비밀번호 확인

Neo4j 웹 UI에 접속하여 비밀번호를 확인:
- URL: http://localhost:7474
- Username: `neo4j`
- Password: (설정한 비밀번호)

---

## 🚀 배포 (5분)

### Step 1: 환경변수 설정

```bash
# 1. .env.n8n 파일 생성
cp .env.n8n.example .env.n8n

# 2. 편집
vim .env.n8n
```

**필수 설정**:
```bash
# Neo4j (필수)
NEO4J_PASSWORD=your-actual-password

# OpenRouter (필수 - Grok 사용)
OPENROUTER_API_KEY=sk-or-v1-...

# Anthropic (필수 - Claude 리포트)
ANTHROPIC_API_KEY=sk-ant-...

# Telegram (필수 - 알림)
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_CHAT_ID=123456789
```

**선택 설정**:
```bash
# n8n 로그인
N8N_USER=admin
N8N_PASSWORD=n8n_nba_2025

# Twitter API (RSS 사용 시 불필요)
TWITTER_CLIENT_ID=
TWITTER_CLIENT_SECRET=
```

### Step 2: 배포 스크립트 실행

```bash
chmod +x deploy_n8n.sh
./deploy_n8n.sh
```

**출력**:
```
🚀 n8n NBA 실시간 파이프라인 배포
==================================

✅ 환경변수 파일 확인
✅ Neo4j 컨테이너 실행 확인 (neo4j-nba)
📡 nba-network 생성 중...
✅ nba-network 생성 완료
🔗 neo4j-nba를 nba-network에 연결 중...
✅ Neo4j 네트워크 연결 완료
🐳 n8n 컨테이너 시작 중...
⏳ n8n 시작 대기 중...
✅ n8n 정상 시작 완료!

==================================
✅ 배포 완료!
==================================

📌 n8n 웹 UI:
   http://localhost:5678
```

### Step 3: Neo4j 연결 테스트

```bash
# 환경변수 로드
source .env.n8n

# 테스트 실행
python3 test_neo4j_connection.py
```

**출력**:
```
████████████████████████████████████████████████████████████████████████████████
█                                                                              █
█                    Neo4j Bolt 연결 테스트                                     █
█                                                                              █
████████████████████████████████████████████████████████████████████████████████

1️⃣ 호스트 → Neo4j (localhost:7687)
================================================================================

✅ 연결 성공!
   Message: Connected!
   Time: 2025-12-25T16:50:00Z

2️⃣ NBA 데이터 확인
================================================================================

📊 노드 통계:
------------------------------------------------------------
   Player                     12,345 nodes
   Team                           30 nodes
   Game                        1,230 nodes
   ...

✅ NBA 데이터 확인 완료

3️⃣ n8n 쿼리 테스트
================================================================================

🧪 테스트 Event 노드 생성...
✅ TestEvent 생성 성공
🧹 테스트 노드 정리...
✅ 정리 완료

4️⃣ n8n 컨테이너 → Neo4j (neo4j-nba:7687)
================================================================================

🐳 n8n 컨테이너에서 연결 테스트 중...
✅ n8n → Neo4j 연결 성공!

📋 테스트 결과 요약
================================================================================

   ✅ PASS - 호스트 → Neo4j
   ✅ PASS - NBA 데이터 확인
   ✅ PASS - n8n 쿼리 테스트
   ✅ PASS - n8n → Neo4j

🎉 모든 테스트 통과!
```

---

## 🌐 n8n 웹 UI 설정

### Step 1: 로그인

1. 브라우저에서 http://localhost:5678 접속
2. 로그인:
   - Username: `admin` (또는 .env.n8n 설정값)
   - Password: `n8n_nba_2025` (또는 .env.n8n 설정값)

### Step 2: Neo4j Credential 추가

1. 좌측 메뉴 → **Settings** → **Credentials**
2. **New** 클릭
3. **Neo4j** 선택
4. 설정:
   - **Name**: `Neo4j NBA`
   - **URI**: `bolt://neo4j-nba:7687` ← **컨테이너 이름 사용**
   - **Username**: `neo4j`
   - **Password**: (환경변수 NEO4J_PASSWORD 값)
5. **Test** 클릭 → ✅ Connection successful
6. **Save** 클릭

### Step 3: OpenRouter Credential 추가

1. **Credentials** → **New**
2. **HTTP Header Auth** 선택
3. 설정:
   - **Name**: `OpenRouter Grok`
   - **Header Name**: `Authorization`
   - **Header Value**: `Bearer ${환경변수 OPENROUTER_API_KEY}`
4. **Save**

### Step 4: Telegram Credential 추가

1. **Credentials** → **New**
2. **Telegram API** 선택
3. 설정:
   - **Name**: `Telegram NBA`
   - **Access Token**: (환경변수 TELEGRAM_BOT_TOKEN)
4. **Save**

### Step 5: Anthropic Credential 추가

1. **Credentials** → **New**
2. **HTTP Header Auth** 선택
3. 설정:
   - **Name**: `Anthropic Claude`
   - **Header Name**: `x-api-key`
   - **Header Value**: `${환경변수 ANTHROPIC_API_KEY}`
4. **Save**

---

## 📥 워크플로우 Import

### Step 1: Import

1. n8n 좌측 메뉴 → **Workflows**
2. 우측 상단 **...** → **Import from File**
3. 파일 선택: `n8n_nba_realtime_workflow.json`
4. **Import** 클릭

### Step 2: Credentials 연결

Import된 워크플로우의 각 노드를 클릭하여 Credential 연결:

| 노드 이름 | Credential |
|-----------|-----------|
| Neo4j - Event 저장 | Neo4j NBA |
| Neo4j - Context 계산 | Neo4j NBA |
| Grok 정규화 | OpenRouter Grok |
| Claude - 리포트 생성 | Anthropic Claude |
| Telegram - 알림 발송 | Telegram NBA |

### Step 3: 수동 테스트

1. 워크플로우 상단 **Execute Workflow** 클릭
2. 각 노드 출력 확인
3. Telegram 알림 수신 확인

### Step 4: 활성화

1. 워크플로우 상단 **Inactive** 토글 → **Active**
2. 1분마다 자동 실행 시작

---

## 🧪 테스트

### 수동 Grok 테스트 (로컬)

```bash
# API Key 설정
export OPENROUTER_API_KEY="sk-or-v1-..."

# 테스트 실행
python3 test_grok_openrouter.py
```

### n8n 워크플로우 로그 확인

1. n8n 웹 UI → **Executions** (좌측 메뉴)
2. 최근 실행 내역 확인
3. 실패한 실행 클릭 → 에러 메시지 확인

### Neo4j 데이터 확인

```bash
# Neo4j Browser 접속
open http://localhost:7474

# 쿼리 실행
MATCH (e:Event)
RETURN e
ORDER BY e.processed_at DESC
LIMIT 10
```

---

## 📊 아키텍처

### 네트워크 구조

```
┌─────────────────────────────────────────────────┐
│  Docker Host (macOS)                            │
│                                                 │
│  ┌─────────────┐        ┌─────────────┐        │
│  │             │        │             │        │
│  │  neo4j-nba  │◄──────►│   n8n-nba   │        │
│  │             │        │             │        │
│  │  :7474      │        │  :5678      │        │
│  │  :7687      │        │             │        │
│  └─────────────┘        └─────────────┘        │
│        │                      │                 │
│        │   nba-network        │                 │
│        └──────────────────────┘                 │
│                                                 │
│  접속:                                          │
│  - Neo4j: localhost:7474, localhost:7687       │
│  - n8n:   localhost:5678                       │
└─────────────────────────────────────────────────┘
```

### 컨테이너 간 통신

- **n8n → Neo4j**: `bolt://neo4j-nba:7687` (컨테이너 이름)
- **Host → Neo4j**: `bolt://localhost:7687` (포트 매핑)
- **Host → n8n**: `http://localhost:5678` (포트 매핑)

---

## 🔧 관리 명령어

### 로그 확인

```bash
# n8n 로그
docker logs -f n8n-nba

# Neo4j 로그
docker logs -f neo4j-nba
```

### 재시작

```bash
# n8n만 재시작
docker restart n8n-nba

# 전체 재배포
./cleanup_n8n.sh
./deploy_n8n.sh
```

### 정리

```bash
# n8n만 삭제 (데이터 보존)
./cleanup_n8n.sh

# n8n + 데이터 전체 삭제
./cleanup_n8n.sh --full
```

### 볼륨 확인

```bash
# n8n 데이터 볼륨
docker volume ls | grep n8n
docker volume inspect n8n_nba_data
```

---

## 🐛 트러블슈팅

### n8n이 Neo4j에 연결 안 됨

**증상**: "Connection refused" 또는 "Unable to connect"

**해결**:
1. 네트워크 확인:
   ```bash
   docker network inspect nba-network | grep neo4j-nba
   ```

2. Neo4j 컨테이너가 같은 네트워크에 있는지 확인:
   ```bash
   docker network connect nba-network neo4j-nba
   ```

3. URI 확인: `bolt://neo4j-nba:7687` (컨테이너 이름, localhost 아님!)

### n8n 웹 UI 접속 안 됨

**증상**: "This site can't be reached"

**해결**:
1. 컨테이너 상태 확인:
   ```bash
   docker ps | grep n8n-nba
   ```

2. 헬스체크 확인:
   ```bash
   docker exec n8n-nba wget --spider http://localhost:5678/healthz
   ```

3. 포트 확인:
   ```bash
   lsof -i :5678
   ```

### Credential 테스트 실패

**증상**: Neo4j Credential Test 실패

**해결**:
1. URI 확인: `bolt://neo4j-nba:7687` (http:// 아님!)
2. 비밀번호 확인: Neo4j 웹 UI (http://localhost:7474)에서 로그인 테스트
3. Neo4j 실행 확인: `docker ps | grep neo4j-nba`

### 환경변수 인식 안 됨

**증상**: API Key가 빈 값으로 전달됨

**해결**:
1. .env.n8n 파일 확인:
   ```bash
   cat .env.n8n | grep API_KEY
   ```

2. 컨테이너 재시작:
   ```bash
   docker-compose -f docker-compose-n8n.yml --env-file .env.n8n down
   docker-compose -f docker-compose-n8n.yml --env-file .env.n8n up -d
   ```

---

## 📚 다음 단계

### 1. 워크플로우 커스터마이징

- 화이트리스트 계정 추가/제거
- 신뢰도 임계값 조정
- 리포트 포맷 변경

### 2. 모니터링 설정

- n8n Executions 자동 알림
- 에러 로그 Slack/Discord 전송
- 비용 추적 대시보드

### 3. 프로덕션 배포

- HTTPS 설정 (Let's Encrypt)
- n8n Cloud 마이그레이션
- 백업 자동화

---

## 📝 요약

✅ **배포 완료 체크리스트**

- [x] Neo4j 컨테이너 실행 중
- [x] .env.n8n 파일 생성 및 API Keys 설정
- [x] `./deploy_n8n.sh` 실행
- [x] `python3 test_neo4j_connection.py` 통과
- [x] n8n 웹 UI 접속 (http://localhost:5678)
- [x] Neo4j Credential 추가 및 테스트
- [x] OpenRouter, Anthropic, Telegram Credentials 추가
- [x] 워크플로우 Import
- [x] Credentials 연결
- [x] 수동 실행 테스트
- [x] 워크플로우 활성화

**접속 정보**:
- n8n: http://localhost:5678
- Neo4j: http://localhost:7474
- Telegram Bot: @YourBotName

**즉시 사용 가능!** 🎉
