# 🔌 VPS Neo4j SSH 터널 설정

> **목표**: 로컬에서 VPS Neo4j를 직접 사용 (데이터 덤프 불필요)

---

## 🎯 왜 SSH 터널?

### ❌ Before (로컬 Neo4j)

```
로컬에서 개발 → 로컬 Neo4j에 저장
→ Neo4j 덤프 → VPS로 업로드
→ VPS에서 복원
→ 너무 비효율!
```

### ✅ After (SSH 터널)

```
로컬에서 개발 → VPS Neo4j에 직접 저장
→ Python 코드만 git push
→ VPS에서 바로 실행
→ 효율적!
```

---

## 🚀 1단계: SSH 터널 연결

### 자동 스크립트 사용

```bash
# SSH 터널 시작
/tmp/connect_vps_neo4j.sh
```

**또는 수동으로**:

```bash
# 백그라운드로 SSH 터널 실행
ssh -L 7687:localhost:7687 -L 7474:localhost:7474 -N root@141.164.35.214 &

# PID 확인
echo $! > /tmp/neo4j_ssh_tunnel.pid
```

### 설명

```
-L 7687:localhost:7687  → 로컬 7687 포트를 VPS Neo4j 7687로 포워딩
-L 7474:localhost:7474  → 로컬 7474 포트를 VPS Neo4j Browser로 포워딩
-N                      → 명령 실행 안 함 (터널만)
&                       → 백그라운드 실행
```

---

## 🔍 2단계: 연결 확인

### Python으로 테스트

```bash
python3 << 'EOF'
from neo4j import GraphDatabase

# 로컬 포트로 연결하면 실제로는 VPS Neo4j에 연결됨!
driver = GraphDatabase.driver(
    "bolt://localhost:7687",
    auth=("neo4j", "test123")  # VPS Neo4j 비밀번호
)

with driver.session() as session:
    result = session.run("MATCH (n) RETURN count(n) as total")
    total = result.single()["total"]
    print(f"✅ VPS Neo4j 연결 성공!")
    print(f"   총 노드: {total:,}개")

driver.close()
EOF
```

**예상 출력**:
```
✅ VPS Neo4j 연결 성공!
   총 노드: 20,137개
```

### Neo4j Browser 확인

```
http://localhost:7474
```

- Connect URL: `bolt://localhost:7687`
- Username: `neo4j`
- Password: `test123`

---

## 📦 3단계: 모든 코드 업데이트

이제 모든 Python 코드에서 로컬 포트로 연결하면 VPS Neo4j에 저장됨!

### Before (로컬 Neo4j)

```python
driver = GraphDatabase.driver(
    "bolt://localhost:7687",
    auth=("neo4j", "quickpass123")  # 로컬 Neo4j
)
```

### After (SSH 터널로 VPS Neo4j)

```python
# 코드는 똑같음! 단지 터널만 켜면 됨
driver = GraphDatabase.driver(
    "bolt://localhost:7687",  # 로컬 포트
    auth=("neo4j", "test123")  # VPS 비밀번호
)
# 실제로는 VPS Neo4j에 저장됨!
```

---

## 🛠️ 4단계: 환경 변수 설정

### .env 파일 생성

```bash
cat > /Users/js/g9/nba_data/odds_report_engine/.env << 'EOF'
# Neo4j 연결 (SSH 터널 사용)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=test123

# Odds API
ODDS_API_KEY=b01049f1f29d61c53189799c40d66f69

# OpenRouter
OPENROUTER_API_KEY=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
EOF
```

### Python에서 사용

```python
from dotenv import load_dotenv
import os

load_dotenv()

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
)
```

---

## 🔄 5단계: 워크플로우

### 매일 작업 흐름

```bash
# 1. SSH 터널 시작
/tmp/connect_vps_neo4j.sh

# 2. 로컬에서 개발
cd /Users/js/g9/nba_data/odds_report_engine
python3 raw_data_pipeline.py  # VPS Neo4j에 직접 저장됨!

# 3. 코드만 VPS에 업로드
git add .
git commit -m "Update pipeline"
git push

# 4. VPS에서 바로 실행
ssh root@141.164.35.214 "cd /opt/g9/nba-collector && git pull && python3 pipeline.py"
```

---

## 🧹 터널 관리

### 터널 상태 확인

```bash
# SSH 터널 프로세스 확인
ps aux | grep "ssh -L 7687"

# 또는
if [ -f /tmp/neo4j_ssh_tunnel.pid ]; then
    PID=$(cat /tmp/neo4j_ssh_tunnel.pid)
    if ps -p $PID > /dev/null; then
        echo "✅ SSH 터널 실행 중 (PID: $PID)"
    else
        echo "❌ SSH 터널 종료됨"
    fi
fi
```

### 터널 종료

```bash
# PID로 종료
kill $(cat /tmp/neo4j_ssh_tunnel.pid)

# 또는 직접 찾아서 종료
pkill -f "ssh -L 7687"
```

### 터널 재시작

```bash
# 기존 터널 종료
kill $(cat /tmp/neo4j_ssh_tunnel.pid) 2>/dev/null

# 새 터널 시작
/tmp/connect_vps_neo4j.sh
```

---

## 🎯 장점

### 1. 데이터 일관성 ✅

```
로컬 개발 → VPS Neo4j
백테스트 → VPS Neo4j
프로덕션 → VPS Neo4j

모두 같은 DB 사용!
```

### 2. 덤프 불필요 ✅

```
❌ Before: 로컬 → 덤프 → VPS 복원 (30분)
✅ After: 로컬 → VPS 직접 저장 (즉시)
```

### 3. 백테스트 자유 ✅

```
로컬에서 언제든:
python3 backtest_2024_season.py

→ VPS Neo4j에 직접 저장
→ 즉시 확인 가능
```

### 4. 로직만 배포 ✅

```
git push
→ VPS에서 git pull
→ 데이터는 이미 Neo4j에 있음
→ 즉시 실행
```

---

## ⚠️ 주의사항

### SSH 터널 유지

```bash
# 터널이 끊어질 수 있음 (네트워크 이슈)
# 자동 재연결 스크립트

cat > /tmp/keep_neo4j_tunnel_alive.sh << 'EOF'
#!/bin/bash
while true; do
    if ! ps -p $(cat /tmp/neo4j_ssh_tunnel.pid 2>/dev/null) > /dev/null 2>&1; then
        echo "⚠️ SSH 터널 끊김, 재연결 중..."
        /tmp/connect_vps_neo4j.sh
    fi
    sleep 30
done
EOF

chmod +x /tmp/keep_neo4j_tunnel_alive.sh

# 백그라운드로 실행
/tmp/keep_neo4j_tunnel_alive.sh &
```

### VPS Neo4j 비밀번호

```
로컬 Neo4j: quickpass123 (테스트용, 지금 안 씀)
VPS Neo4j: test123 (실제 사용)
```

---

## 🚀 실전 사용 예시

### 백테스트 (로컬 → VPS Neo4j)

```bash
# 1. SSH 터널 연결
/tmp/connect_vps_neo4j.sh

# 2. 백테스트 실행 (로컬)
cd /Users/js/g9/nba_data/odds_report_engine
python3 << 'EOF'
from neo4j import GraphDatabase
import json

driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "test123"))

# VPS Neo4j에 직접 저장됨!
with driver.session() as session:
    # 2024 시즌 백테스트 데이터 저장
    session.run("""
        CREATE (g:Game {
          game_id: "backtest_2024_001",
          season: "2024-25",
          backtest: true
        })
    """)
    print("✅ VPS Neo4j에 백테스트 데이터 저장 완료!")

driver.close()
EOF

# 3. VPS에서 즉시 확인
ssh root@141.164.35.214 "echo 'MATCH (g:Game {backtest: true}) RETURN count(g);' | cypher-shell -u neo4j -p test123"
```

---

## 💡 핵심 포인트

> **SSH 터널로 VPS Neo4j를 쓰면,**
> **로컬 개발이지만 데이터는 VPS에 쌓인다!**

```
로컬 코드 → bolt://localhost:7687 (SSH 터널) → VPS Neo4j
                                                  ↓
                                          데이터 영구 저장
```

**장점**:
- ✅ 로컬에서 빠르게 개발
- ✅ VPS에 데이터 직접 저장
- ✅ 덤프/복원 불필요
- ✅ 백테스트 언제든 실행
- ✅ 로직만 git push

---

**이제 로컬 Neo4j는 안 씁니다. VPS Neo4j만 씁니다!** 🚀
