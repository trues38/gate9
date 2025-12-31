# 📊 N8N Economy Collector 설정 가이드

## 🚀 빠른 설정 (5분)

### 1. N8N 접속
```
URL: http://141.164.35.214:5678
ID: admin
PW: CHANGE_THIS_STRONG_PASSWORD
```

### 2. 새 Workflow 생성

좌측 메뉴 "Workflows" → 우측 상단 "+" 버튼 클릭

### 3. Workflow 이름 설정
상단에서 "My workflow" → **"Economy Collector (5x Daily)"**로 변경

---

## 📅 노드 구성

### Node 1-6: Schedule Triggers (총 6개 시간대)

**공통 설정**:
- 좌측 노드 패널에서 **"Schedule Trigger"** 드래그

#### Trigger 1: 평일 아침 (08:30, 09:30)
```
Name: Weekday Morning (08:30, 09:30)
Mode: Custom (Cron Expression)
Expression: 30 8,9 * * 1-5
```

#### Trigger 2: 평일 중간 (11:00)
```
Name: Weekday Mid (11:00)
Mode: Custom (Cron Expression)
Expression: 0 11 * * 1-5
```

#### Trigger 3: FOMC 시간 (14:15)
```
Name: FOMC Time (14:15)
Mode: Custom (Cron Expression)
Expression: 15 14 * * 1-5
```

#### Trigger 4: 장 마감 전 (15:50)
```
Name: Market Close (15:50)
Mode: Custom (Cron Expression)
Expression: 50 15 * * 1-5
```

#### Trigger 5: 토요일 (12:00)
```
Name: Weekend Saturday
Mode: Custom (Cron Expression)
Expression: 0 12 * * 6
```

#### Trigger 6: 일요일 (18:00)
```
Name: Weekend Sunday
Mode: Custom (Cron Expression)
Expression: 0 18 * * 0
```

---

### Node 7: HTTP Request - Collect Economy

**설정**:
```
Name: Call Economy Collector API
Method: POST
URL: http://nba-collector:8001/collect/economy
```

**Headers**:
```
Content-Type: application/json
```

**6개 Schedule Trigger 모두 이 노드에 연결**

---

### Node 8: IF - Check Success

**설정**:
```
Name: Check Success
Condition: String
Value 1: {{$json.status}}
Operation: Equal
Value 2: success
```

**이전 노드 (Call Economy Collector API) 연결**

---

### Node 9: HTTP Request - Process LLM

**설정**:
```
Name: Process with LLM
Method: POST
URL: http://nba-collector:8001/process/llm
```

**Headers**:
```
Content-Type: application/json
```

**Body (JSON)**:
```json
{
  "domain": "economy",
  "batch_size": 50
}
```

**이전 노드 (Check Success의 "true" 분기) 연결**

---

## ✅ 완료 및 활성화

1. 우측 상단 **"Save"** 버튼 클릭
2. 우측 상단 **"Active" 토글 ON** (중요!)
3. 초록색 체크마크 확인

---

## 🧪 테스트

### 수동 실행 테스트
1. Schedule Trigger 하나 선택
2. "Execute Node" 클릭
3. 하단 "Executions" 패널에서 결과 확인

### 예상 결과
```json
{
  "status": "success",
  "accounts_fetched": 7,
  "tweets_saved": 10
}
```

---

## 📊 모니터링

### Workflow 실행 내역 확인
- 좌측 메뉴 "Executions" 클릭
- 최근 실행 내역 및 성공/실패 확인

### API 사용량 확인
```bash
curl http://141.164.35.214:8001/budget/status
```

예상 출력:
```json
{
  "economy_used": 5,  // 1회 수집 후
  "economy_remaining": 195,
  "nba_used": 0
}
```

---

## 🎯 스케줄 요약

| 시간 (EST) | 빈도 | 목적 |
|-----------|------|------|
| 08:30 | 평일 | NFP, CPI 발표 |
| 09:30 | 평일 | 시장 오픈 |
| 11:00 | 평일 | 중간 체크 |
| 14:15 | 평일 | FOMC 직후 |
| 15:50 | 평일 | 장 마감 전 |
| 12:00 | 토요일 | 주말 체크 |
| 18:00 | 일요일 | 주말 체크 |

**월 사용량**: ~121회 / 200회 예산

---

## 📝 체크리스트

- [ ] N8N 접속 확인
- [ ] Workflow 생성
- [ ] 6개 Schedule Trigger 설정
- [ ] HTTP Request (Collect) 설정
- [ ] IF 조건문 설정
- [ ] HTTP Request (LLM) 설정
- [ ] 모든 노드 연결
- [ ] Save
- [ ] **Active ON** ✅
- [ ] 수동 테스트 실행
