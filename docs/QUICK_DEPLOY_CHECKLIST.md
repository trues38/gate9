# 경제 이벤트 파이프라인 빠른 배포 체크리스트

**목적:** 30분 이내에 파이프라인 배포 및 테스트
**생성일:** 2025-12-25

---

## ✅ 체크리스트

### Phase 1: 준비 (5분)

- [ ] **Neo4j 실행 확인**
  ```bash
  docker ps | grep neo4j-economy
  # 없으면: docker start neo4j-economy
  # 브라우저: http://localhost:7475
  ```

- [ ] **n8n 설치 확인**
  ```bash
  docker ps | grep n8n
  # 없으면: docker run -d --name n8n -p 5678:5678 -v ~/.n8n:/home/node/.n8n n8nio/n8n
  # 브라우저: http://localhost:5678
  ```

- [ ] **API 키 준비**
  - [ ] Twitter Bearer Token: `___________________`
  - [ ] xAI Grok API Key: `___________________`
  - [ ] Slack Webhook (선택): `___________________`

---

### Phase 2: n8n 워크플로우 임포트 (10분)

- [ ] **워크플로우 파일 임포트**
  1. n8n 웹UI → Workflows → Import from File
  2. 파일: `/Users/js/g9/n8n_workflows/economic_event_pipeline.json`
  3. Import 클릭

- [ ] **Twitter Credentials 설정**
  1. **Twitter OAuth2 API** 노드 클릭
  2. Credentials → Create New
  3. Bearer Token 입력
  4. Save

- [ ] **Grok API Credentials 설정**
  1. **HTTP Request (Grok)** 노드 클릭
  2. Authentication → Header Auth
  3. Name: `Authorization`
  4. Value: `Bearer YOUR_XAI_API_KEY`
  5. Save

- [ ] **Neo4j Credentials 설정**
  1. **Neo4j** 노드 클릭
  2. Credentials → Create New
  3. Host: `localhost`, Port: `7688`
  4. User: `neo4j`, Password: `regime2025`
  5. Save

---

### Phase 3: 화이트리스트 설정 (5분)

- [ ] **화이트리스트 생성**
  ```bash
  python3 /Users/js/g9/scripts/setup_economic_whitelist.py
  # 메뉴에서 "2" 선택 (n8n 코드 생성)
  ```

- [ ] **n8n Switch 노드 업데이트**
  1. n8n에서 **Switch (Whitelist Check)** 노드 클릭
  2. 생성된 JavaScript 코드 복사
  3. 노드에 붙여넣기
  4. Save

---

### Phase 4: 테스트 (5분)

- [ ] **수동 테스트 실행**
  1. n8n에서 워크플로우 "Active" 토글 ON
  2. **Test Workflow** 버튼 클릭
  3. 결과 확인:
     - [ ] Twitter에서 트윗 가져옴
     - [ ] Keyword Filter 통과
     - [ ] Whitelist 확인
     - [ ] Grok 분석 완료
     - [ ] Neo4j Event 생성

- [ ] **Neo4j에서 이벤트 확인**
  ```cypher
  // Neo4j Browser (http://localhost:7475)에서 실행
  MATCH (e:Event)
  RETURN e.title, e.type, e.confidence, e.timestamp
  ORDER BY e.timestamp DESC
  LIMIT 5;
  ```

- [ ] **검증 스크립트 실행**
  ```bash
  python3 /Users/js/g9/scripts/validate_event_pipeline.py
  # ✓ Neo4j 연결 성공
  # ✓ Event 노드: X개 발견
  # ✓ AFFECTS 관계: Y개 생성
  ```

---

### Phase 5: 운영 시작 (5분)

- [ ] **워크플로우 활성화**
  1. n8n에서 워크플로우 "Active" 상태 확인
  2. Schedule Trigger 간격 확인: 5분 (초기 테스트) 또는 15분 (운영)

- [ ] **헬스 체크 설정**
  ```bash
  # crontab 등록 (매일 오전 9시, 오후 6시)
  crontab -e

  # 추가:
  0 9 * * * python3 /Users/js/g9/scripts/pipeline_health_check.py > /Users/js/g9/logs/health_$(date +\%Y\%m\%d)_am.log
  0 18 * * * python3 /Users/js/g9/scripts/pipeline_health_check.py > /Users/js/g9/logs/health_$(date +\%Y\%m\%d)_pm.log
  ```

- [ ] **대시보드 쿼리 즐겨찾기**
  - Neo4j Browser에서 `/Users/js/g9/queries/economic_event_dashboard.cypher` 열기
  - "고신뢰도 Tier 1 이벤트" 쿼리 즐겨찾기 추가

---

## 🚨 문제 해결

### Twitter 노드가 작동하지 않음
```bash
# API 키 테스트
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "https://api.twitter.com/2/users/by/username/federalreserve"

# 200 OK + JSON 응답 확인
```

### Grok API 오류 (429 Too Many Requests)
- n8n Schedule Trigger 간격 늘리기: 5분 → 15분 → 30분
- xAI Console에서 rate limit 확인

### Neo4j에 Event 생성 안됨
```cypher
// 수동 테스트
MERGE (e:Event {id: 'test-001', title: 'Test Event'})
SET e.timestamp = datetime()
RETURN e;

// 삭제
MATCH (e:Event {id: 'test-001'}) DELETE e;
```

---

## 📊 1시간 후 확인 사항

- [ ] **이벤트 생성 확인**
  ```bash
  python3 /Users/js/g9/scripts/pipeline_health_check.py
  # 오늘 생성된 이벤트: X개 (최소 5개 이상 예상)
  ```

- [ ] **Tier 분포 확인**
  - Tier 1: 중앙은행 발표 있으면 1-2개
  - Tier 2: 금융 뉴스 5-10개
  - Tier 3: 분석가 트윗 3-5개

- [ ] **Factor 연결 확인**
  ```cypher
  MATCH (e:Event)-[r:AFFECTS]->(f:InfluenceFactor)
  RETURN f.name, count(e) as event_count
  ORDER BY event_count DESC;
  ```

---

## 🎯 24시간 후 검증

- [ ] **안정성 확인**
  - 총 이벤트 수: 50-100개 예상
  - 고신뢰도(>0.8): 10-20개 예상
  - n8n Executions에서 오류율 < 10%

- [ ] **데이터 품질 확인**
  ```bash
  python3 /Users/js/g9/scripts/validate_event_pipeline.py
  # 이슈 0개 목표
  ```

- [ ] **성과 보고**
  ```cypher
  // 최근 24시간 요약
  MATCH (e:Event)
  WHERE e.timestamp > datetime() - duration('P1D')
  RETURN e.type as type,
         count(*) as count,
         avg(e.confidence) as avg_conf
  ORDER BY count DESC;
  ```

---

## ✅ 완료!

배포 완료 시:
- [ ] 이 체크리스트를 `/Users/js/g9/logs/deployment_YYYYMMDD.md`로 저장
- [ ] 대화 로그에 마일스톤 기록
  ```bash
  echo '{"timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%S)'", "type": "milestone", "content": "경제 이벤트 파이프라인 배포 완료", "details": {"events_24h": X}}' >> /Users/js/g9/claude_logs/conversation_$(date +%Y-%m-%d).jsonl
  ```

---

**예상 소요 시간:** 30분
**난이도:** 중급
**필수 스킬:** Docker, Neo4j, n8n 기본 사용법

**다음 단계:** `/Users/js/g9/docs/ECONOMIC_EVENT_PIPELINE_SETUP.md` 참조
