# 🔌 n8n에서 SSH 터널 사용하기

> **n8n의 내장 SSH Tunnel 기능으로 VPS Neo4j 안전하게 연결**

---

## 🎯 n8n SSH Tunnel의 장점

1. **자동 관리**: n8n이 터널을 자동으로 열고 닫음
2. **안정성**: 워크플로우 실행 시마다 연결 확인
3. **보안**: SSH 키 기반 인증 지원
4. **간편함**: 별도의 터널 관리 스크립트 불필요

---

## 📋 설정 방법

### 1단계: Neo4j Credential 생성

n8n UI에서:

```
Settings > Credentials > New Credential > Neo4j
```

#### 기본 정보

```
Name: VPS Neo4j (via SSH)
Host: localhost
Port: 7687
User: neo4j
Password: nba_vultr_2025
Database: neo4j
```

#### SSH Tunnel 활성화

```
☑️ Connect via SSH Tunnel

SSH Host: 141.164.35.214
SSH Port: 22
SSH User: root
```

#### SSH 인증 방법 선택

**Option 1: SSH 키 사용 (권장)**

```
SSH Authentication Method: Private Key

Private Key:
-----BEGIN OPENSSH PRIVATE KEY-----
(로컬의 ~/.ssh/id_rsa 또는 ~/.ssh/id_ed25519 내용 복사)
-----END OPENSSH PRIVATE KEY-----

Passphrase: (키에 비밀번호가 있으면 입력)
```

**Option 2: 비밀번호 사용**

```
SSH Authentication Method: Password
SSH Password: (VPS root 비밀번호)
```

#### Test & Save

```
[Test Connection] 클릭
✅ "Connection successful!" 확인
[Save] 클릭
```

---

### 2단계: Neo4j 노드에서 사용

워크플로우에 Neo4j 노드 추가:

```
1. Neo4j 노드 추가
2. Credential: "VPS Neo4j (via SSH)" 선택
3. Query 입력 예시:
   MATCH (n) RETURN count(n) as total
4. Execute Node
```

**n8n이 자동으로**:
1. SSH 터널 생성
2. Neo4j 쿼리 실행
3. 결과 반환
4. 터널 종료

---

## 🔧 SSH 키 생성 (처음 한 번만)

### macOS/Linux

```bash
# 1. SSH 키 생성
ssh-keygen -t ed25519 -C "n8n@g9-nba"

# 저장 위치: ~/.ssh/id_ed25519 (Enter)
# Passphrase: (비워두거나 입력)

# 2. 공개 키 VPS에 복사
ssh-copy-id root@141.164.35.214

# 3. 개인 키 확인
cat ~/.ssh/id_ed25519

# 이 내용을 n8n에 붙여넣기
```

### 확인

```bash
# 비밀번호 없이 연결되면 성공
ssh root@141.164.35.214

# 바로 접속됨!
```

---

## 📊 n8n Workflow 예시

### Workflow: 경기 후 Feedback Loop

```json
{
  "nodes": [
    {
      "name": "경기 종료 확인",
      "type": "n8n-nodes-base.cron",
      "parameters": {
        "rule": {
          "interval": [{"field": "hours", "hoursInterval": 1}]
        }
      }
    },
    {
      "name": "완료된 경기 조회",
      "type": "n8n-nodes-base.neo4j",
      "credentials": {
        "neo4j": {
          "name": "VPS Neo4j (via SSH)"
        }
      },
      "parameters": {
        "query": "MATCH (g:Game {status: 'COMPLETED'}) WHERE NOT (g)-[:RESULTED_IN]->(:BoxScore) RETURN g.game_id"
      }
    },
    {
      "name": "BoxScore 수집",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "url": "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={{$json.game_id}}"
      }
    },
    {
      "name": "BoxScore 저장",
      "type": "n8n-nodes-base.neo4j",
      "credentials": {
        "neo4j": {
          "name": "VPS Neo4j (via SSH)"
        }
      },
      "parameters": {
        "query": "CREATE (b:BoxScore {game_id: $game_id, home_score: $home_score, ...})"
      }
    },
    {
      "name": "State 업데이트",
      "type": "n8n-nodes-base.neo4j",
      "credentials": {
        "neo4j": {
          "name": "VPS Neo4j (via SSH)"
        }
      },
      "parameters": {
        "query": "MATCH (ts:TeamState {team_id: $team_id}) SET ts.regime_confidence = ..."
      }
    }
  ]
}
```

**n8n이 자동으로**:
- 매 시간마다 실행
- SSH 터널로 VPS Neo4j 연결
- 경기 결과 수집 → State 업데이트
- 터널 자동 종료

---

## 🔄 로컬 개발 vs n8n 운영

### 로컬 개발 (Python 코드)

```bash
# autossh로 터널 유지
./ssh_tunnel_stable.sh

# Python 코드 실행
python3 raw_data_pipeline.py

# 터널 종료
./stop_tunnel.sh
```

### n8n 운영 (프로덕션)

```
n8n이 내장 SSH Tunnel 사용
→ 터널 관리 불필요
→ 워크플로우만 설정
```

---

## 🛠️ 트러블슈팅

### 문제 1: "Connection failed"

```bash
# VPS Neo4j 실행 확인
ssh root@141.164.35.214 "docker ps | grep neo4j"

# Neo4j 포트 확인
ssh root@141.164.35.214 "netstat -tlnp | grep 7687"
```

### 문제 2: "SSH Authentication failed"

```bash
# SSH 키 재등록
ssh-copy-id root@141.164.35.214

# 수동 접속 테스트
ssh root@141.164.35.214
```

### 문제 3: "Timeout"

```
n8n Credential 설정에서:
☑️ Connect via SSH Tunnel
SSH Connection Timeout: 30000 (30초로 늘림)
```

---

## 💡 Best Practices

### 1. SSH 키 사용 (비밀번호 X)

```
✅ SSH Key: 안전하고 자동화 가능
❌ Password: 보안 위험, 매번 입력
```

### 2. Credential 분리

```
개발용: "Local Neo4j"
프로덕션용: "VPS Neo4j (via SSH)"
```

### 3. Error Handling

```json
{
  "onError": "continueErrorOutput",
  "retryOnFail": true,
  "maxTries": 3
}
```

### 4. 로깅

```
n8n Execution > Logs 에서
SSH 연결 상태 확인
```

---

## 🎯 정리

| 방법 | 사용 시기 | 장점 | 단점 |
|------|----------|------|------|
| **n8n 내장 SSH Tunnel** | n8n 워크플로우 | 자동 관리, 안정성 | n8n에서만 사용 |
| **autossh 스크립트** | 로컬 개발 | 유연성, 디버깅 용이 | 수동 관리 |
| **systemd 서비스** | 24/7 터널 | 완전 자동화 | 설정 복잡 |

---

## 🚀 추천 구성

```
로컬 개발: autossh 스크립트 (./ssh_tunnel_stable.sh)
n8n 프로덕션: n8n 내장 SSH Tunnel
VPS 백그라운드: systemd 서비스 (선택)
```

**n8n을 쓴다면 n8n 내장 SSH Tunnel이 최고!** 🎉
