# NBA State Graph - Quick Start

**5분 안에 Neo4j로 927게임 임포트**

---

## Step 1: Neo4j 실행 (2분)

```bash
# Docker로 Neo4j 실행
docker run -d \
  --name neo4j-nba \
  -p 7474:7474 \
  -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password123 \
  neo4j:5.15

# 실행 확인
docker logs neo4j-nba
# "Started." 메시지 확인
```

---

## Step 2: Python 패키지 설치 (30초)

```bash
pip install neo4j
```

---

## Step 3: 마이그레이션 실행 (2분)

### 옵션 A: 테스트 (10개 게임만)
```bash
python3 migrate_clean.py --limit 10
```

### 옵션 B: 전체 (927개 게임)
```bash
python3 migrate_clean.py
```

**예상 출력**:
```
======================================================================
깨끗한 Neo4j 마이그레이션 시작
======================================================================

Step 1: Constraints & Indexes
======================================================================
  ✅ team_abbr
  ✅ player_name
  ✅ referee_name
  ✅ venue_id
  ✅ game_id
  ✅ game_date
  ✅ game_season

======================================================================
Step 2: 게임 데이터 로드
======================================================================
  ✅ 927개 게임 로드

  snapshots에서 컨텍스트 로드 중...
  ✅ 927개 컨텍스트 로드

======================================================================
Step 3: Neo4j 임포트
======================================================================
  [50/927] ✅ 진행 중...
  [100/927] ✅ 진행 중...
  ...

  ✅ 927개 게임 임포트 완료

======================================================================
✅ 마이그레이션 완료!
======================================================================

통계:
  게임: 927개
  선수: 15,000명 (중복 포함)
  심판: 2,700명 (중복 포함)
  경기장: 900개 (중복 포함)
```

---

## Step 4: Neo4j Browser 열기 (30초)

```bash
open http://localhost:7474

# 로그인:
# Username: neo4j
# Password: password123
```

### 첫 쿼리:
```cypher
// 전체 그래프 미리보기
MATCH (n)
RETURN n
LIMIT 50
```

---

## 유의미한 쿼리 예시

### 1. 심판별 홈 승률
```cypher
MATCH (ref:Referee)<-[:OFFICIATED_BY]-(game:GameState)
WITH ref,
     count(game) as total_games,
     sum(CASE WHEN game.home_win THEN 1 ELSE 0 END) as home_wins
WHERE total_games >= 10
RETURN ref.name as 심판,
       total_games as 경기수,
       round(home_wins * 100.0 / total_games, 1) as 홈승률
ORDER BY 홈승률 DESC;
```

### 2. 휴식일 영향
```cypher
MATCH (game:GameState)
WITH game.home_rest_days - game.away_rest_days as rest_advantage,
     CASE WHEN game.home_win THEN 1 ELSE 0 END as home_win
RETURN rest_advantage as 휴식일차,
       count(*) as 경기수,
       round(avg(home_win) * 100, 1) as 홈승률
ORDER BY 휴식일차;
```

### 3. 선수별 평균 득점 (Top 20)
```cypher
MATCH (player:Player)<-[played:PLAYED]-(game:GameState)
WHERE played.minutes >= 20
WITH player,
     count(game) as games,
     avg(played.points) as avg_pts
WHERE games >= 5
RETURN player.name as 선수,
       games as 경기수,
       round(avg_pts, 1) as 평균득점
ORDER BY avg_pts DESC
LIMIT 20;
```

### 4. B2B (Back-to-Back) 효과
```cypher
MATCH (game:GameState)
WHERE game.home_rest_days = 0
WITH count(game) as b2b_games,
     sum(CASE WHEN game.home_win THEN 1 ELSE 0 END) as b2b_wins
RETURN b2b_games as B2B경기수,
       round(b2b_wins * 100.0 / b2b_games, 1) as B2B승률;
```

---

## 문제 해결

### "Connection refused"
```bash
# Neo4j 재시작
docker restart neo4j-nba
```

### "Out of memory"
```bash
# 메모리 증가
docker stop neo4j-nba
docker rm neo4j-nba

docker run -d \
  --name neo4j-nba \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password123 \
  -e NEO4J_server_memory_heap_max__size=4G \
  neo4j:5.15
```

---

## 성공 기준

- [ ] Neo4j Browser 접속
- [ ] 노드 927개 이상 (GameState)
- [ ] 선수 500명 이상
- [ ] 심판 50명 이상
- [ ] 쿼리 실행 성공

---

**다음**: docs/NEO4J_SCHEMA_CLEAN.cypher (10개 추가 쿼리)
