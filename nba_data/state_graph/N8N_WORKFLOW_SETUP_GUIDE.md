# n8n Box Score 워크플로우 설정 가이드

## 🎯 목표
매일 새벽 2시에 자동으로 Box Score를 수집하고 Neo4j에 저장

---

## 📋 워크플로우 구조

```
1. Schedule Trigger (매일 02:00)
   ↓
2. HTTP Request (Flask API 호출)
   ↓
3. Code (결과 포맷팅)
   ↓
4. HTTP Request (알림 - 선택사항)
```

---

## 🔧 Node 설정

### Node 1: Schedule Trigger
- **Type**: Schedule Trigger
- **Name**: `Daily 02:00 Trigger`
- **Cron Expression**: `0 2 * * *`
- **설명**: 매일 새벽 2시 실행

---

### Node 2: HTTP Request
- **Type**: HTTP Request
- **Name**: `Collect Box Scores`
- **Method**: POST
- **URL**: `http://localhost:5001/api/boxscore/collect`
- **Options**:
  - Timeout: `600000` (10분)

**응답 예시**:
```json
{
  "status": "success",
  "message": "✅ Box Score 수집 및 임포트 완료",
  "crawl_output": "...",
  "import_output": "...",
  "timestamp": "2025-12-26T..."
}
```

---

### Node 3: Code (결과 포맷팅)
- **Type**: Code
- **Name**: `Format Result`
- **Code**:

```javascript
const result = $input.item.json;
const success = result.status === 'success';

return [{
  json: {
    status: result.status,
    message: result.message,
    timestamp: result.timestamp,
    icon: success ? '✅' : '❌'
  }
}];
```

---

### Node 4: HTTP Request (알림 - 선택사항)
- **Type**: HTTP Request
- **Name**: `Notify (Optional)`
- **Method**: POST
- **URL**: `http://localhost:3000/api/notify` (또는 Slack/Telegram webhook)
- **Body**:

```json
{
  "type": "boxscore_updated",
  "status": "{{ $json.status }}",
  "message": "{{ $json.message }}",
  "timestamp": "{{ $json.timestamp }}"
}
```

- **Options**:
  - Continue on Fail: ✅ (체크)

---

## 🧪 테스트 방법

### 1. 수동 실행
1. n8n에서 워크플로우 열기
2. 우측 상단 **"Execute Workflow"** 클릭
3. 각 노드 결과 확인

**예상 결과**:
- Node 2: `{"status": "success", ...}`
- Node 3: `{"status": "success", "message": "✅ Box Score...", "icon": "✅"}`

### 2. Neo4j 확인
```cypher
MATCH (pb:PlayerBoxScore)
WHERE pb.date >= date('2025-12-25')
RETURN pb.date, count(*) as total
ORDER BY pb.date DESC
```

---

## ⏰ 자동화 활성화

1. 워크플로우 열기
2. 우측 상단 **"Active"** 토글 켜기
3. ✅ 완료!

**작동 시간**:
- 매일 새벽 2시 (cron: `0 2 * * *`)
- 전날 NBA 경기의 Box Score 자동 수집

---

## 📊 모니터링

### n8n Executions
- n8n UI → "Executions" 탭
- 성공/실패 이력 확인
- 에러 로그 보기

### Flask API 로그
```bash
tail -f /Users/js/g9/nba_data/state_graph/boxscore_api.log
```

### Neo4j 데이터
```cypher
// 최근 7일 Box Score
MATCH (pb:PlayerBoxScore)
WHERE pb.date >= date() - duration({days: 7})
RETURN pb.date, count(*) as total
ORDER BY pb.date DESC
```

---

## ❌ 트러블슈팅

### 문제 1: Flask API 연결 안됨
**증상**: `Connection refused`

**해결**:
```bash
# Flask API 상태 확인
curl http://localhost:5001/health

# 로그 확인
tail -20 /Users/js/g9/nba_data/state_graph/boxscore_api.log

# 재시작
launchctl unload ~/Library/LaunchAgents/com.nba.boxscore.api.plist
launchctl load ~/Library/LaunchAgents/com.nba.boxscore.api.plist
```

---

### 문제 2: 타임아웃
**증상**: `Request timeout`

**해결**:
- HTTP Request 노드에서 Timeout 늘리기 (600000ms → 900000ms)
- Flask API의 timeout도 늘리기 (`boxscore_api.py`)

---

### 문제 3: 중복 데이터
**증상**: 같은 날짜 데이터가 여러 번 임포트됨

**해결**:
Neo4j에 Constraint가 있으므로 자동으로 중복 방지됨:
```cypher
SHOW CONSTRAINTS
// player_boxscore_unique: (game_id, player_id) IS UNIQUE
```

---

## 🎯 완료 체크리스트

- [ ] Flask API 자동 시작 설정 완료
- [ ] n8n 워크플로우 임포트 완료
- [ ] 수동 테스트 성공
- [ ] Neo4j에 데이터 확인됨
- [ ] Active 상태로 설정
- [ ] (선택) 알림 엔드포인트 설정

---

**작성일**: 2025-12-26
**버전**: v3 (HTTP Request 방식)
**유지보수**: Flask API는 launchd로 자동 시작, n8n은 docker로 실행
