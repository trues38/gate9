# n8n Box Score 자동 수집 설정 가이드

## 📋 워크플로우 개요

**파일**: `n8n_boxscore_auto_collection.json`

**기능**: 매일 새벽 2시, 전날 NBA 경기의 Box Score를 자동으로 수집하고 Neo4j에 저장

**노드 구성**:
```
1. Daily 02:00 Trigger    → 매일 02:00 실행
2. Calculate Yesterday    → 어제 날짜 계산 (20251225)
3. Crawl Box Scores       → ESPN API에서 수집
4. Import to Neo4j        → Neo4j에 저장
5. Success Message        → 완료 메시지 생성
6. Notify (Optional)      → 웹 알림 (선택)
```

---

## 🚀 설치 방법

### 1. n8n 접속
```bash
# n8n이 실행 중인지 확인
docker ps | grep n8n

# 브라우저에서 접속
open http://localhost:5678
```

### 2. 워크플로우 임포트

**방법 A: 웹 UI 사용**
1. n8n 열기 (http://localhost:5678)
2. 좌측 상단 메뉴 → "Import from file"
3. 파일 선택: `/Users/js/g9/nba_data/state_graph/n8n_boxscore_auto_collection.json`
4. "Import" 클릭

**방법 B: CLI 사용**
```bash
# n8n 컨테이너에 복사
docker cp n8n_boxscore_auto_collection.json n8n:/home/node/.n8n/

# n8n 재시작
docker restart n8n
```

### 3. 환경 확인

워크플로우가 제대로 실행되려면 다음이 필요합니다:

```bash
# ✅ Python 스크립트 존재
ls -la /Users/js/g9/nba_data/state_graph/crawl_current_season_boxscores.py
ls -la /Users/js/g9/nba_data/state_graph/import_player_boxscores.py

# ✅ Python 가상환경 (venv)
ls -la /Users/js/g9/.venv/bin/python3

# ✅ Neo4j 실행 중
curl -u neo4j:password123 http://localhost:7474/db/neo4j/tx/commit

# ✅ 출력 디렉토리
mkdir -p /Users/js/g9/nba_data/state_graph/player_boxscores_2025_26
```

---

## 🧪 테스트 방법

### 수동 테스트 (즉시 실행)

n8n UI에서:
1. 워크플로우 열기
2. 우측 상단 "Execute Workflow" 클릭
3. 결과 확인

**예상 출력**:
```json
{
  "status": "success",
  "date": "2025-12-25",
  "message": "✅ Box Score 수집 완료: 2025-12-25",
  "timestamp": "2025-12-26T02:00:00.000Z"
}
```

### CLI에서 직접 테스트

```bash
cd /Users/js/g9/nba_data/state_graph

# 1. Box Score 크롤링
/Users/js/g9/.venv/bin/python3 crawl_current_season_boxscores.py

# 2. Neo4j 임포트
/Users/js/g9/.venv/bin/python3 import_player_boxscores.py

# 3. Neo4j 확인
python3 -c "
from neo4j import GraphDatabase
driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'password123'))
with driver.session() as session:
    result = session.run('MATCH (pb:PlayerBoxScore) RETURN count(pb) as total')
    print(f'PlayerBoxScore 총 {result.single()[\"total\"]}개')
driver.close()
"
```

---

## ⏰ 스케줄 설정

### 기본 스케줄: 매일 02:00

```json
{
  "cronExpression": "0 2 * * *"
}
```

### 스케줄 변경하려면:

n8n UI에서:
1. "Daily 02:00 Trigger" 노드 클릭
2. "Cron Expression" 수정
3. "Save" 클릭

**Cron 예시**:
- `0 2 * * *` - 매일 02:00
- `0 3 * * *` - 매일 03:00
- `0 2 * * 1-5` - 평일만 02:00
- `0 1,13 * * *` - 매일 01:00, 13:00 (2회)

---

## 🔔 알림 설정 (선택사항)

### Slack 알림

1. n8n에서 "Notify (Optional)" 노드 클릭
2. URL 변경:
```javascript
{
  "method": "POST",
  "url": "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK",
  "body": {
    "text": "{{ $json.message }}"
  }
}
```

### Telegram 알림

```javascript
{
  "method": "POST",
  "url": "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/sendMessage",
  "body": {
    "chat_id": "YOUR_CHAT_ID",
    "text": "{{ $json.message }}"
  }
}
```

### 알림 불필요하면

"Notify (Optional)" 노드를 삭제하거나 비활성화

---

## 📊 모니터링

### n8n 실행 이력 확인

n8n UI → "Executions" 탭
- 성공/실패 확인
- 에러 로그 보기
- 실행 시간 확인

### Neo4j 데이터 확인

```cypher
// Neo4j Browser (http://localhost:7474)

// 최근 추가된 Box Score
MATCH (pb:PlayerBoxScore)
WHERE pb.date >= date('2025-12-20')
RETURN pb.date, count(*) as games
ORDER BY pb.date DESC

// 특정 선수 성적
MATCH (pb:PlayerBoxScore {player_name: 'LeBron James'})
WHERE pb.date >= date('2025-12-01')
RETURN pb.date, pb.points, pb.rebounds, pb.assists, pb.plus_minus
ORDER BY pb.date DESC
```

### 로그 파일

```bash
# 크롤러 로그
tail -f /Users/js/g9/nba_data/state_graph/boxscore_crawl.log

# n8n 로그 (Docker)
docker logs -f n8n
```

---

## ❌ 트러블슈팅

### 문제 1: 스크립트 실행 안됨

**증상**: "Command not found" 에러

**해결**:
```bash
# Python 경로 확인
which python3
/Users/js/g9/.venv/bin/python3

# n8n 노드에서 절대 경로 사용
/Users/js/g9/.venv/bin/python3 crawl_current_season_boxscores.py
```

### 문제 2: Neo4j 연결 실패

**증상**: "Could not connect to Neo4j"

**해결**:
```bash
# Neo4j 실행 중인지 확인
docker ps | grep neo4j-nba

# 포트 확인
netstat -an | grep 7687

# 비밀번호 확인
# import_player_boxscores.py 에서:
# password="password123"
```

### 문제 3: 중복 데이터

**증상**: "Duplicate key error"

**해결**:
```cypher
// Neo4j에 Constraint가 있는지 확인
SHOW CONSTRAINTS

// PlayerBoxScore Constraint 재생성
DROP CONSTRAINT player_boxscore_unique IF EXISTS;

CREATE CONSTRAINT player_boxscore_unique IF NOT EXISTS
FOR (pb:PlayerBoxScore)
REQUIRE (pb.game_id, pb.player_id) IS UNIQUE
```

### 문제 4: 데이터가 없음

**증상**: 워크플로우는 성공하지만 데이터 0개

**원인**: 해당 날짜에 경기가 없었을 수 있음

**확인**:
```bash
# ESPN API 직접 확인
curl "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates=20251225"
```

---

## 🔧 고급 설정

### 여러 날짜 한번에 수집

n8n에서 "Calculate Yesterday" 노드를 수정:

```javascript
// 최근 3일 데이터 수집
const dates = [];
for (let i = 1; i <= 3; i++) {
  const date = new Date();
  date.setDate(date.getDate() - i);

  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');

  dates.push({
    date_arg: `${year}${month}${day}`,
    date_display: `${year}-${month}-${day}`
  });
}

return dates.map(d => ({ json: d }));
```

### 조건부 실행 (경기일만)

```javascript
// 경기가 있는지 먼저 확인
const response = await fetch(
  `https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates=${dateStr}`
);
const data = await response.json();

if (!data.events || data.events.length === 0) {
  console.log('경기 없음, 스킵');
  return [];
}

return [{ json: { date_arg: dateStr } }];
```

---

## 📈 성능 최적화

### 병렬 처리

여러 날짜를 동시에 수집:
- "Calculate Yesterday" → 3일치 날짜 배열
- "Crawl Box Scores" → 병렬 실행
- "Import to Neo4j" → 병렬 실행

### 캐싱

이미 수집한 데이터는 스킵:

```python
# crawl_current_season_boxscores.py 수정
output_file = output_dir / f"boxscores_{date_str}.json"
if output_file.exists():
    print(f"Already exists: {output_file}")
    return
```

---

## ✅ 완료 체크리스트

설치 완료 확인:
- [ ] n8n에 워크플로우 임포트 완료
- [ ] 수동 테스트 성공
- [ ] Neo4j에 데이터 확인됨
- [ ] Cron 스케줄 활성화
- [ ] (선택) 알림 설정 완료

---

## 🎯 기대 효과

**자동화 전**:
- 수동 실행: `python3 crawl_current_season_boxscores.py`
- 매일 잊어버림
- 데이터 갭 발생

**자동화 후**:
- ✅ 매일 자동 수집
- ✅ 항상 최신 데이터
- ✅ Neo4j에 14,000+ Box Scores
- ✅ 베팅 분석 정확도 ↑

---

**작성일**: 2025-12-26
**다음 단계**: n8n에 워크플로우 임포트 및 테스트
