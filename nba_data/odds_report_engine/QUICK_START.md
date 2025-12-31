# 🚀 VPS Neo4j 빠른 시작 (5분 완료)

## 📋 준비 완료!

스크립트 3개 생성됨:
- `setup_ssh_key.sh` - SSH 키 등록 (한 번만)
- `start_vps_tunnel.sh` - 수동 연결 (비밀번호 입력)
- `start_vps_tunnel_auto.sh` - 자동 연결 (SSH 키 후)

---

## 🔌 지금 바로 연결

### Option 1: 자동 연결 (추천)

```bash
cd /Users/js/g9/nba_data/odds_report_engine

# 1. SSH 키 등록 (한 번만)
./setup_ssh_key.sh

# 2. 자동 연결
./start_vps_tunnel_auto.sh
```

### Option 2: 수동 연결

```bash
./start_vps_tunnel.sh
# VPS root 비밀번호 입력
```

### Option 3: 직접 명령어

```bash
ssh -f -L 7687:localhost:7687 -L 7474:localhost:7474 -N root@141.164.35.214
```

---

## ✅ 연결 확인

```bash
python3 << 'EOF'
from neo4j import GraphDatabase

driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "test123"))
with driver.session() as session:
    result = session.run("MATCH (n) RETURN count(n) as total")
    print(f"✅ VPS Neo4j: {result.single()['total']:,}개 노드")
driver.close()
EOF
```

---

## 🎯 이제 할 일

### 1. 모든 코드가 VPS Neo4j 사용

```python
# 코드 변경 불필요! 이대로만 쓰면 VPS에 저장됨
driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "test123"))
```

### 2. 로컬 개발 → VPS 배포

```bash
# 로컬에서 개발 (VPS Neo4j에 직접 저장)
python3 raw_data_pipeline.py

# 코드만 git push
git push

# VPS에서 바로 실행 (데이터는 이미 Neo4j에)
ssh root@141.164.35.214 "cd /opt/g9/nba-collector && git pull && python3 pipeline.py"
```

---

## 💡 핵심

> **SSH 터널 = 로컬 개발, VPS 저장**

```
로컬 코드 → bolt://localhost:7687 → SSH 터널 → VPS Neo4j
                                                  ↓
                                          실제 데이터 저장
```

**장점**:
- ✅ 덤프 불필요
- ✅ 백테스트 자유
- ✅ 로직만 배포
- ✅ 데이터 일관성

---

**지금 바로**: `./start_vps_tunnel_auto.sh` 실행! 🚀
