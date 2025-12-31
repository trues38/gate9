# 🚀 완전 배포 가이드

> **Feedback Loop 시스템 + SSH 터널 안정화 + VPS 배포**

---

## 📋 목차

1. [SSH 터널 안정화](#1-ssh-터널-안정화)
2. [Feedback Loop VPS 배포](#2-feedback-loop-vps-배포)
3. [n8n 설정](#3-n8n-설정)
4. [운영 시작](#4-운영-시작)

---

## 1. SSH 터널 안정화

### 로컬 개발용 (3가지 방법)

#### 방법 1: autossh (권장)

```bash
cd /Users/js/g9/nba_data/odds_report_engine

# 터널 시작
./ssh_tunnel_stable.sh

# 결과:
# ✅ autossh가 터널을 자동 관리
# ✅ 끊기면 자동 재연결
# ✅ 30초마다 생존 신호
```

**장점**:
- ✅ 네트워크 끊겨도 자동 재연결
- ✅ 카페/집 이동해도 OK
- ✅ 안정적

#### 방법 2: systemd 서비스 (Linux/완벽 자동화)

```bash
# 서비스 설치
sudo cp neo4j-tunnel.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable neo4j-tunnel
sudo systemctl start neo4j-tunnel

# 상태 확인
sudo systemctl status neo4j-tunnel

# 로그 확인
sudo journalctl -u neo4j-tunnel -f
```

**장점**:
- ✅ 시스템 부팅 시 자동 시작
- ✅ 죽으면 자동 재시작
- ✅ 완벽한 자동화

#### 방법 3: 일반 SSH (테스트용)

```bash
ssh -f -L 7687:localhost:7687 -L 7474:localhost:7474 -N root@141.164.35.214
```

**단점**:
- ❌ 끊기면 수동 재연결
- ❌ 안정성 낮음

### 터널 관리

```bash
# 터널 상태 확인
ps aux | grep "ssh.*7687"

# 터널 종료
./stop_tunnel.sh
```

---

## 2. Feedback Loop VPS 배포

### 자동 배포 스크립트

```bash
cd /Users/js/g9/nba_data/odds_report_engine

# 한 번에 배포
./deploy_feedback_loop_to_vps.sh
```

**배포 내용**:
1. VPS에 디렉토리 생성 (`/opt/g9/nba-feedback-loop`)
2. 스키마 파일 업로드
3. Python 파이프라인 업로드
4. Neo4j 스키마 적용
5. 환경 변수 설정
6. 연결 테스트

### 수동 배포 (세부 제어)

```bash
# 1. 파일 업로드
scp FEEDBACK_LOOP_SCHEMA.cypher root@141.164.35.214:/opt/g9/nba-feedback-loop/
scp raw_data_pipeline.py root@141.164.35.214:/opt/g9/nba-feedback-loop/

# 2. VPS 접속
ssh root@141.164.35.214

# 3. 디렉토리 이동
cd /opt/g9/nba-feedback-loop

# 4. 스키마 적용
docker exec -i $(docker ps | grep neo4j | awk '{print $1}') \
    cypher-shell -u neo4j -p nba_vultr_2025 < FEEDBACK_LOOP_SCHEMA.cypher

# 5. 테스트
python3 feedback_loop_example.py
```

---

## 3. n8n 설정

### n8n SSH Tunnel 설정 (권장)

```
n8n UI > Settings > Credentials > New > Neo4j

Name: VPS Neo4j (via SSH)

Database Info:
  Host: localhost
  Port: 7687
  User: neo4j
  Password: nba_vultr_2025

☑️ Connect via SSH Tunnel
  SSH Host: 141.164.35.214
  SSH Port: 22
  SSH User: root
  SSH Auth: Private Key
  Private Key: (로컬 ~/.ssh/id_ed25519 내용)

[Test Connection] → ✅ Success
[Save]
```

### n8n Workflow Import

```bash
# n8n UI에서
Workflows > Import from File > n8n_post_game_workflow.json
```

**워크플로우 구성**:
1. Cron: 매 시간 실행
2. Neo4j: 완료된 경기 조회 (SSH Tunnel 사용)
3. HTTP: BoxScore API 호출
4. Neo4j: BoxScore 저장 (SSH Tunnel 사용)
5. Neo4j: State 업데이트 (SSH Tunnel 사용)

---

## 4. 운영 시작

### 일일 워크플로우

#### 로컬 개발

```bash
# 1. SSH 터널 시작
cd /Users/js/g9/nba_data/odds_report_engine
./ssh_tunnel_stable.sh

# 2. 로컬에서 개발
python3 raw_data_pipeline.py  # VPS Neo4j에 직접 저장!

# 3. 코드만 VPS에 업로드
git add .
git commit -m "Update pipeline"
git push

# 4. VPS에서 git pull
ssh root@141.164.35.214 "cd /opt/g9/nba-feedback-loop && git pull"

# 5. 터널 종료 (선택)
./stop_tunnel.sh
```

#### VPS n8n 자동 실행

```
n8n이 매 시간:
1. 완료된 경기 확인
2. BoxScore 수집
3. Event 검증
4. State 업데이트
→ 자동으로 돌아감!
```

### 백테스트

```bash
# 로컬에서 VPS Neo4j에 백테스트 데이터 저장
./ssh_tunnel_stable.sh

python3 << 'EOF'
from raw_data_pipeline import RawDataPipeline

pipeline = RawDataPipeline(
    base_dir="/Users/js/g9/nba_data/raw_events",
    neo4j_uri="bolt://localhost:7687",  # SSH 터널로 VPS 연결
    neo4j_password="nba_vultr_2025"
)

# 2024 시즌 백테스트 데이터
# ...

pipeline.close()
EOF

# VPS Neo4j에 바로 저장됨!
# 덤프/복원 불필요!
```

---

## 🔍 상태 확인

### 로컬

```bash
# SSH 터널 상태
ps aux | grep "autossh.*7687"

# Neo4j 연결 테스트
python3 -c "
from neo4j import GraphDatabase
driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'nba_vultr_2025'))
with driver.session() as s:
    print(f'Nodes: {s.run(\"MATCH (n) RETURN count(n)\").single()[0]:,}')
driver.close()
"
```

### VPS

```bash
ssh root@141.164.35.214

# Neo4j 실행 확인
docker ps | grep neo4j

# 노드 수 확인
docker exec $(docker ps | grep neo4j | awk '{print $1}') \
    cypher-shell -u neo4j -p nba_vultr_2025 \
    "MATCH (n) RETURN count(n);"

# 최근 State 업데이트
docker exec $(docker ps | grep neo4j | awk '{print $1}') \
    cypher-shell -u neo4j -p nba_vultr_2025 \
    "MATCH (ts:TeamState) RETURN ts.team_id, ts.updated_at ORDER BY ts.updated_at DESC LIMIT 5;"
```

---

## 📊 시스템 구성도

```
┌─────────────────────────────────────────┐
│         로컬 개발 (MacBook)              │
├─────────────────────────────────────────┤
│                                          │
│  1. Python 코드 작성                      │
│  2. ./ssh_tunnel_stable.sh (autossh)   │
│  3. bolt://localhost:7687               │
│     └─→ SSH Tunnel ─────────────┐       │
│                                  │       │
│  4. git push                     │       │
│                                  │       │
└──────────────────────────────────┼───────┘
                                   │
                                   ↓
┌──────────────────────────────────┼───────┐
│         VPS (141.164.35.214)     │       │
├──────────────────────────────────┼───────┤
│                                  │       │
│  ┌────────────────────────────┐ │       │
│  │ Neo4j (bolt://localhost:7687)◄┘      │
│  │ - 15,433 nodes               │       │
│  │ - Feedback Loop State        │       │
│  └────────────────────────────┘        │
│                                          │
│  ┌────────────────────────────┐        │
│  │ n8n (내장 SSH Tunnel)       │        │
│  │ - 매 시간 실행              │        │
│  │ - BoxScore 수집              │        │
│  │ - State 업데이트             │        │
│  └────────────────────────────┘        │
│                                          │
│  ┌────────────────────────────┐        │
│  │ /opt/g9/nba-feedback-loop   │        │
│  │ - raw_data_pipeline.py      │        │
│  │ - FEEDBACK_LOOP_*.cypher    │        │
│  └────────────────────────────┘        │
│                                          │
└─────────────────────────────────────────┘
```

---

## 🎯 핵심 장점

### Before (로컬 Neo4j)

```
로컬 개발 → 로컬 Neo4j → 덤프 → VPS 업로드 → 복원
                          ↑
                    30분 소요, 비효율
```

### After (SSH 터널)

```
로컬 개발 → SSH 터널 → VPS Neo4j
           (즉시)      ↓
                  데이터 영구 저장

코드만 git push → VPS git pull → 바로 실행
```

**장점**:
- ✅ 덤프/복원 불필요
- ✅ 백테스트 자유
- ✅ 데이터 일관성
- ✅ 로직만 배포
- ✅ n8n 자동화

---

## 🚀 빠른 시작 (5분)

```bash
cd /Users/js/g9/nba_data/odds_report_engine

# 1. SSH 터널 시작
./ssh_tunnel_stable.sh

# 2. Feedback Loop 배포
./deploy_feedback_loop_to_vps.sh

# 3. n8n 설정
# - N8N_SSH_TUNNEL_SETUP.md 참조

# 4. 완료! 🎉
```

---

## 📝 생성된 파일

```
/Users/js/g9/nba_data/odds_report_engine/
├── ssh_tunnel_stable.sh            # autossh 터널 (로컬 개발)
├── stop_tunnel.sh                  # 터널 종료
├── neo4j-tunnel.service            # systemd 서비스 (완벽 자동화)
├── deploy_feedback_loop_to_vps.sh  # VPS 자동 배포
├── N8N_SSH_TUNNEL_SETUP.md         # n8n 설정 가이드
├── FEEDBACK_LOOP_SCHEMA.cypher     # Neo4j 스키마
├── FEEDBACK_LOOP_QUERIES.cypher    # 경기 후 쿼리
├── raw_data_pipeline.py            # RAW 데이터 저장
├── feedback_loop_example.py        # 사용 예시
└── DEPLOY_COMPLETE_GUIDE.md        # 이 문서
```

---

**이제 완벽하게 준비되었습니다!** 🚀

1. ✅ SSH 터널 안정화 (autossh/systemd/n8n)
2. ✅ Feedback Loop VPS 배포
3. ✅ n8n 자동화
4. ✅ 로컬 개발 → VPS 저장 (즉시)

**남은 것**: 실행!
