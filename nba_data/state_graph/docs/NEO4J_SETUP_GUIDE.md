# Neo4j 설치 및 실행 가이드

**목표**: Docker로 Neo4j 설치 → 마이그레이션 → Graph Viewer 실행

---

## Step 1: Neo4j Docker 설치 (5분)

### 1.1 Docker 설치 확인
```bash
docker --version
# Docker version 24.0.0 이상이면 OK
```

### 1.2 Neo4j 컨테이너 실행
```bash
docker run -d \
  --name neo4j-nba \
  -p 7474:7474 \
  -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password123 \
  -e NEO4J_PLUGINS='["apoc", "graph-data-science"]' \
  -e NEO4J_server_memory_heap_initial__size=2G \
  -e NEO4J_server_memory_heap_max__size=4G \
  -v $(pwd)/neo4j_data:/data \
  neo4j:5.15
```

**설명**:
- `-p 7474`: Browser UI
- `-p 7687`: Bolt 연결 (Python)
- `NEO4J_AUTH`: 사용자명/비밀번호
- `APOC, GDS`: 플러그인 (필수)
- `heap size`: 메모리 설정

### 1.3 실행 확인
```bash
# 로그 확인
docker logs neo4j-nba

# "Started." 메시지 확인되면 성공
```

### 1.4 Browser 접속
```
http://localhost:7474

Username: neo4j
Password: password123
```

---

## Step 2: Python 패키지 설치 (1분)

```bash
pip install neo4j
```

---

## Step 3: 마이그레이션 실행 (2분)

### 3.1 시드 데이터 확인
```bash
ls -la tactics_seed.json

# 파일이 있어야 함 (10개 경기 태그)
```

### 3.2 마이그레이션 실행
```bash
python3 migrate_to_neo4j.py \
  --uri bolt://localhost:7687 \
  --user neo4j \
  --password password123 \
  --seed-file tactics_seed.json
```

**예상 출력**:
```
======================================================================
Neo4j 마이그레이션 시작
======================================================================

로드된 데이터:
  - 경기 수: 10개
  - 전술 태그: 11개

======================================================================
Step 1: Constraints & Indexes 생성
======================================================================
✅ team_abbr
✅ player_name
✅ tactic_name
✅ game_id
✅ game_date

======================================================================
Step 2: 전술 노드 생성
======================================================================
✅ Gap Defense (defense, effectiveness: 0.49)
✅ Pace & Space (offense, effectiveness: 0.44)

======================================================================
Step 3: 팀 노드 생성
======================================================================
✅ ORL
✅ DAL
✅ DEN
...

======================================================================
Step 4: GameState 노드 생성
======================================================================
✅ 401704631: ORL @ MIA (2024-10-23)
✅ 401704640: SA @ DAL (2024-10-24)
...

======================================================================
Step 5: 관계 생성 (USES_TACTIC)
======================================================================
✅ 11개 관계 생성 완료

======================================================================
Step 6: 샘플 전술 상성 생성
======================================================================
✅ No-Pick Roll Play → Gap Defense (0.72 승률)
⚠️  Pace & Space → Inside Spacing: Tactic not found

======================================================================
✅ 마이그레이션 완료!
======================================================================

데이터베이스 통계:
노드 수:
  Team: 8개
  Tactic: 2개
  GameState: 10개

관계 수:
  USES_TACTIC: 11개
  FEATURED_TACTIC: 11개
  COUNTERS: 1개
```

---

## Step 4: Graph Viewer 쿼리 실행 (5분)

### 4.1 Neo4j Browser에서 쿼리 실행

**Browser 열기**: http://localhost:7474

#### 쿼리 1: 전체 그래프 보기
```cypher
MATCH (n)
RETURN n
LIMIT 50
```

**결과**: 노드 네트워크 시각화

#### 쿼리 2: 팀별 전술 사용
```cypher
MATCH (team:Team)-[u:USES_TACTIC]->(tactic:Tactic)
RETURN
  team.abbr AS 팀,
  tactic.name AS 전술,
  u.usage_count AS 사용횟수,
  u.avg_confidence AS 평균Confidence
ORDER BY u.usage_count DESC
```

**결과**:
```
팀    전술              사용횟수  평균Confidence
OKC   Gap Defense      2         0.53
DEN   Gap Defense      2         0.44
...
```

#### 쿼리 3: 전술 상성 네트워크
```cypher
MATCH (t1:Tactic)-[c:COUNTERS]->(t2:Tactic)
RETURN t1, c, t2
```

**결과**: 전술 상성 화살표 시각화

#### 쿼리 4: 특정 경기 상세
```cypher
MATCH (game:GameState {game_id: "401704631"})
MATCH (game)-[:FEATURED_TACTIC]->(tactic:Tactic)
RETURN
  game.matchup AS 매치업,
  game.date AS 날짜,
  collect(tactic.name) AS 전술
```

**결과**:
```
매치업        날짜         전술
ORL @ MIA    2024-10-23   ["Pace & Space"]
```

---

## Step 5: 추가 데이터 입력 (선택)

### 5.1 수동으로 전술 상성 추가
```cypher
// No-Pick Roll Play가 Gap Defense를 카운터
MATCH (counter:Tactic {name: "No-Pick Roll Play"})
MATCH (target:Tactic {name: "Gap Defense"})

MERGE (counter)-[c:COUNTERS]->(target)
SET c.win_rate = 0.72,
    c.avg_point_diff = 8.5,
    c.sample_size = 8,
    c.mechanism = "갭 디펜스의 스크린 예상을 역이용",
    c.source = "manual_expert_input"

RETURN counter.name, target.name, c.win_rate
```

### 5.2 팀 정보 업데이트
```cypher
MATCH (team:Team {abbr: "OKC"})
SET team.name = "Oklahoma City Thunder",
    team.conference = "West",
    team.division = "Northwest"

RETURN team
```

---

## 문제 해결

### 문제 1: "Connection refused"
```bash
# Neo4j가 실행 중인지 확인
docker ps

# 재시작
docker restart neo4j-nba
```

### 문제 2: "Authentication failed"
```bash
# 비밀번호 재설정
docker exec -it neo4j-nba cypher-shell -u neo4j -p neo4j

# 첫 로그인 후 비밀번호 변경 프롬프트
```

### 문제 3: "Out of memory"
```bash
# 메모리 늘리기 (8GB로)
docker stop neo4j-nba
docker rm neo4j-nba

# 다시 실행 (heap_max_size=8G)
docker run -d \
  --name neo4j-nba \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password123 \
  -e NEO4J_server_memory_heap_max__size=8G \
  neo4j:5.15
```

---

## 다음 단계

### Option 1: 더 많은 데이터 추가
```bash
# 20개 경기 태깅
python3 tag_core_games.py --count 20

# 재마이그레이션
python3 migrate_to_neo4j.py
```

### Option 2: 고급 쿼리 실행
```bash
# GRAPH_VIEWER_QUERIES.cypher의 Query 7-10 실행
```

### Option 3: Graph Viewer UI 구축
```bash
# React + D3.js (선택)
# Neo4j Browser만으로도 충분
```

---

## 성공 기준

- [ ] Neo4j Browser 접속 성공
- [ ] 노드 20개 이상 생성 (Team 8 + Tactic 2 + GameState 10)
- [ ] 관계 22개 이상 (USES_TACTIC 11 + FEATURED_TACTIC 11)
- [ ] 쿼리 실행 성공
- [ ] 그래프 시각화 확인

---

**다음 문서**: `GRAPH_VIEWER_QUERIES.cypher` (쿼리 10개)
