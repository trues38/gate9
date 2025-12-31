# 🚀 G9 NBA Feedback Loop - 배포 완료

## ✅ 완성된 시스템

### 1. SSH 터널 안정화 ✅

**3가지 방법 제공**:

```bash
# 방법 1: autossh (권장 - 자동 재연결)
./ssh_tunnel_stable.sh

# 방법 2: systemd (Linux 완벽 자동화)
sudo cp neo4j-tunnel.service /etc/systemd/system/
sudo systemctl enable --now neo4j-tunnel

# 방법 3: n8n 내장 (프로덕션)
# N8N_SSH_TUNNEL_SETUP.md 참조
```

**종료**:
```bash
./stop_tunnel.sh
```

---

### 2. Feedback Loop VPS 배포 ✅

```bash
# 자동 배포
./deploy_feedback_loop_to_vps.sh

# 결과:
# ✅ VPS에 /opt/g9/nba-feedback-loop 생성
# ✅ 스키마 적용
# ✅ Python 파이프라인 설치
# ✅ .env 설정
```

---

### 3. 운영 방법 ✅

#### 로컬 개발

```bash
# 1. 터널 시작
./ssh_tunnel_stable.sh

# 2. 개발
python3 raw_data_pipeline.py  # VPS Neo4j에 저장!

# 3. 배포
git push
ssh root@141.164.35.214 "cd /opt/g9/nba-feedback-loop && git pull"
```

#### n8n 자동 실행

```
매 시간 자동:
- 완료된 경기 확인
- BoxScore 수집
- Event 검증
- State 업데이트
```

---

## 📂 핵심 파일

| 파일 | 용도 |
|------|------|
| `ssh_tunnel_stable.sh` | SSH 터널 시작 (autossh) |
| `stop_tunnel.sh` | 터널 종료 |
| `deploy_feedback_loop_to_vps.sh` | VPS 배포 |
| `DEPLOY_COMPLETE_GUIDE.md` | 전체 가이드 |
| `N8N_SSH_TUNNEL_SETUP.md` | n8n 설정 |
| `FEEDBACK_LOOP_SCHEMA.cypher` | Neo4j 스키마 |
| `raw_data_pipeline.py` | 데이터 저장 파이프라인 |

---

## 🎯 Quick Start

```bash
# 1. SSH 터널
./ssh_tunnel_stable.sh

# 2. Feedback Loop 배포
./deploy_feedback_loop_to_vps.sh

# 3. n8n 설정
# N8N_SSH_TUNNEL_SETUP.md 참조

# 완료! 🎉
```

---

## 💡 핵심 개념

```
로컬 개발 → SSH Tunnel → VPS Neo4j
                          ↓
                    데이터 영구 저장

Event (일회용) → State (누적)
BoxScore (정답) → 학습 → 다음 예측 개선
```

**"예측을 학습하는 게 아니라, 틀린 이유를 학습한다"** 🎯

---

## 📊 시스템 상태

```bash
# 로컬 터널 확인
ps aux | grep "autossh.*7687"

# VPS Neo4j 확인
ssh root@141.164.35.214 "docker ps | grep neo4j"

# 데이터 확인
python3 -c "
from neo4j import GraphDatabase
d = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'nba_vultr_2025'))
with d.session() as s:
    print(f'{s.run(\"MATCH (n) RETURN count(n)\").single()[0]:,} nodes')
d.close()
"
```

---

## 🚨 문제 해결

### SSH 터널 끊김

```bash
# autossh 재시작
./stop_tunnel.sh
./ssh_tunnel_stable.sh

# 또는 systemd 사용 (자동 재시작)
```

### VPS Neo4j 접속 불가

```bash
ssh root@141.164.35.214
docker ps | grep neo4j
docker restart <neo4j-container>
```

---

**모든 준비 완료!** 🚀

1. ✅ SSH 터널 안정화
2. ✅ Feedback Loop VPS 배포
3. ✅ 로컬 개발 → VPS 저장
4. ✅ n8n 자동화 준비

**이제 실행만 하면 됩니다!**
