# 🔄 로컬 Neo4j → VPS 동기화 계획

## 현재 상태

### 로컬
- ✅ **neo4j-economy** (7475:7474, 7688:7687) - 실행중
- ❌ **neo4j-nba** - 비밀번호 이슈로 시작 실패
- ❌ **neo4j-regime** (7474 포트 충돌)

### VPS (141.164.35.214)
- ✅ **Neo4j NBA** (7474, 7687) - 실행중 (비어있음)
- ⚠️ **Neo4j Economy** (7475, 7688) - 상태 미확인

---

## 동기화 방법

### Option 1: Neo4j Dump/Restore (권장)

```bash
# 1. 로컬에서 덤프
docker exec neo4j-economy neo4j-admin database dump neo4j \
  --to-path=/tmp --overwrite-destination=true

# 2. 덤프 파일 복사
docker cp neo4j-economy:/tmp/neo4j.dump ./neo4j-economy.dump

# 3. VPS로 전송
scp neo4j-economy.dump root@141.164.35.214:/tmp/

# 4. VPS에서 복원
ssh root@141.164.35.214 << 'REMOTE'
cd /opt/g9
docker compose stop neo4j-economy
docker cp /tmp/neo4j-economy.dump g9-neo4j-economy:/tmp/
docker exec g9-neo4j-economy neo4j-admin database load neo4j \
  --from-path=/tmp --overwrite-destination=true
docker compose start neo4j-economy
REMOTE
```

### Option 2: Cypher 스크립트 Export

```bash
# APOC 플러그인 사용
CALL apoc.export.cypher.all("export.cypher", {
  format: "cypher-shell",
  useOptimizations: {type: "UNWIND_BATCH", unwindBatchSize: 20}
})
```

---

## 실시간 데이터 연동

### NBA Collector → Neo4j 연결

현재: SQLite만 사용
```python
# domains/nba/collector/storage/sqlite_storage.py
class SQLiteStorage:
    def save_tweet(self, tweet):
        # SQLite에만 저장
```

필요: Neo4j 동시 저장
```python
# domains/nba/collector/storage/neo4j_storage.py
from neo4j import GraphDatabase

class Neo4jStorage:
    def save_tweet(self, tweet):
        with self.driver.session() as session:
            session.run("""
                MERGE (t:Tweet {id: $id})
                SET t.text = $text,
                    t.created_at = datetime($created_at),
                    t.domain = $domain
                
                // 선수 언급 추출 후 연결
                FOREACH (player IN $players |
                    MERGE (p:Player {name: player})
                    MERGE (t)-[:MENTIONS]->(p)
                )
            """, **tweet)
```

### 분석 엔진 → Neo4j 그래프 RAG

```python
# domains/nba/analysis/graph_rag.py
class GraphRAG:
    def analyze_player_trend(self, player_name):
        query = """
        MATCH (p:Player {name: $player})<-[:MENTIONS]-(t:Tweet)
        WHERE t.created_at > datetime() - duration('P7D')
        RETURN t.text, t.created_at
        ORDER BY t.created_at DESC
        """
        # LLM으로 분석
```

---

## 다음 단계

1. ✅ neo4j-economy 데이터 덤프
2. ⬜ VPS Economy Neo4j 복원
3. ⬜ neo4j-nba 문제 해결 및 덤프
4. ⬜ VPS NBA Neo4j 복원
5. ⬜ Collector Neo4j 저장 로직 추가
6. ⬜ 분석 엔진 개발
7. ⬜ VPS 배포

