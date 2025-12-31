# 경제 이벤트 파이프라인 스크립트 모음

**생성일:** 2025-12-25
**목적:** 실시간 경제 이벤트 수집 및 분석 파이프라인 운영

---

## 📁 스크립트 목록

### 1. validate_event_pipeline.py
**용도:** 파이프라인 검증 및 문제 진단

```bash
# 실행
python3 /Users/js/g9/scripts/validate_event_pipeline.py

# 검증 항목:
# - Neo4j 연결 상태
# - Event 노드 생성 여부
# - AFFECTS 관계 확인
# - Tier 1 이벤트 유무
# - 평균 confidence 점수
```

**출력 예시:**
```
✓ Neo4j 연결 성공
✓ Event 노드: 23개 발견
✓ AFFECTS 관계: 18개 생성
✓ Tier 1 이벤트(24h): 4개
평균 Confidence: 0.78
고신뢰도 이벤트(>0.8): 9개
```

---

### 2. pipeline_health_check.py
**용도:** 일일 운영 헬스 체크 및 통계

```bash
# 실행
python3 /Users/js/g9/scripts/pipeline_health_check.py

# 모니터링 항목:
# - 오늘 생성된 이벤트 수
# - Tier별 분포
# - 이벤트 타입별 분포
# - Factor 영향 집계
# - 이상 징후 감지
```

**출력 예시:**
```
📅 2025-12-25 경제 이벤트 파이프라인 헬스 체크
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ 오늘 생성된 이벤트: 23개

Tier별 분포:
  Tier 1 (Central Banks): 4개 (17.4%)
  Tier 2 (Media): 12개 (52.2%)
  Tier 3 (Analysts): 7개 (30.4%)

Factor 영향 (오늘):
  Interest Rates: ↑ 1.2 (3개 이벤트)
  Liquidity: ↓ 0.8 (2개 이벤트)
```

**JSON 내보내기:**
- 자동으로 `/Users/js/g9/logs/pipeline_health_YYYYMMDD.json` 저장
- 대시보드 연동 가능

---

### 3. setup_economic_whitelist.py
**용도:** 화이트리스트 관리 및 n8n 코드 생성

```bash
# 실행
python3 /Users/js/g9/scripts/setup_economic_whitelist.py

# 메뉴:
# 1. 화이트리스트 요약 보기
# 2. n8n Switch 노드 코드 생성
# 3. Twitter List 생성 가이드
# 4. JSON 파일로 내보내기
# 5. 전체 실행
```

**주요 기능:**
- 3-Tier 화이트리스트 정의 (25개 계정)
- n8n 워크플로우용 JavaScript 자동 생성
- Twitter List 생성 가이드
- JSON 설정 파일 내보내기

**화이트리스트 구조:**
```
Tier 1: Central Banks & Government (9개)
  - @federalreserve, @ecb, @BIS_org, @USTreasury, etc.

Tier 2: Financial Media (8개)
  - @business, @ReutersMarkets, @FT, @WSJ, etc.

Tier 3: Analysts & Quants (8개)
  - @RaoulGMI, @LynAldenContact, @MacroAlf, etc.
```

---

## 🚀 워크플로우 실행 순서

### 초기 설정 (1회)

```bash
# 1. 화이트리스트 설정
python3 /Users/js/g9/scripts/setup_economic_whitelist.py

# 2. n8n Switch 노드에 생성된 코드 복사
# 3. n8n 워크플로우 임포트
#    파일: /Users/js/g9/n8n_workflows/economic_event_pipeline.json

# 4. 파이프라인 검증
python3 /Users/js/g9/scripts/validate_event_pipeline.py
```

### 일일 운영

```bash
# 아침: 헬스 체크
python3 /Users/js/g9/scripts/pipeline_health_check.py

# 저녁: 다시 헬스 체크 (하루 요약)
python3 /Users/js/g9/scripts/pipeline_health_check.py

# 주간: 검증 스크립트 실행 (이상 징후 확인)
python3 /Users/js/g9/scripts/validate_event_pipeline.py
```

---

## 📊 Neo4j 쿼리 모음

### 위치
```
/Users/js/g9/queries/economic_event_dashboard.cypher
```

### 카테고리
1. **실시간 모니터링** (최근 1시간, 고신뢰도 이벤트)
2. **통계 & 집계** (일별, Tier별, 타입별)
3. **Factor 영향 분석** (누적 영향, 상관관계)
4. **이벤트 체인** (인과관계 추적)
5. **레짐 전환 분석** (트리거 이벤트)
6. **이상 탐지** (비정상 confidence, 상반된 영향)
7. **성과 분석** (백테스팅 준비)
8. **데이터 품질** (누락 필드, 중복 탐지)
9. **유지보수** (아카이빙, 정리)

### 즐겨찾기 추천 쿼리

**매일 확인:**
```cypher
// 고신뢰도 Tier 1 이벤트
MATCH (e:Event)
WHERE e.source_tier = 1
  AND e.confidence > 0.8
  AND e.timestamp > datetime() - duration('P1D')
RETURN e.title, e.confidence, e.url
ORDER BY e.confidence DESC;
```

**주간 확인:**
```cypher
// Factor별 누적 영향
MATCH (e:Event)-[r:AFFECTS]->(f:InfluenceFactor)
WHERE e.timestamp > datetime() - duration('P7D')
RETURN f.name,
       sum(CASE WHEN r.impact_direction = 'increase' THEN r.impact_magnitude ELSE -r.impact_magnitude END) as net_impact
ORDER BY abs(net_impact) DESC;
```

---

## 🔧 문제 해결

### Neo4j 연결 실패

```bash
# Neo4j 상태 확인
docker ps | grep neo4j-economy

# Neo4j 재시작
docker restart neo4j-economy

# 로그 확인
docker logs neo4j-economy
```

### Event가 생성되지 않음

```bash
# n8n 워크플로우 상태 확인
# http://localhost:5678에서 Executions 탭 확인

# n8n 로그 확인
docker logs n8n

# Twitter API 테스트
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "https://api.twitter.com/2/users/by/username/federalreserve"
```

### Grok API 오류

```bash
# Rate limit 확인
# xAI Console에서 사용량 확인

# n8n 워크플로우 간격 조정
# Schedule Trigger: 5분 → 15분
```

---

## 📈 확장 가이드

### 화이트리스트 추가

1. `setup_economic_whitelist.py` 편집
2. `WHITELIST` 딕셔너리에 계정 추가
3. 스크립트 실행하여 n8n 코드 재생성
4. n8n Switch 노드 업데이트

### 새로운 이벤트 타입 추가

1. `economic_event_pipeline.json` 편집
2. Grok 프롬프트에 새로운 타입 정의 추가
3. Neo4j 쿼리 업데이트 (`economic_event_dashboard.cypher`)

### 새로운 Factor 추가

1. Neo4j에서 Factor 생성:
```cypher
MERGE (f:InfluenceFactor {name: 'Credit Spread'})
SET f.description = 'Corporate bond spreads over treasuries',
    f.typical_range = '1.0-5.0%'
```

2. Grok 프롬프트에 Factor 추가
3. 대시보드 쿼리 업데이트

---

## 💾 백업 & 유지보수

### 정기 백업 (권장)

```bash
# n8n 워크플로우 백업
cp /Users/js/g9/n8n_workflows/economic_event_pipeline.json \
   /Users/js/g9/backups/economic_event_pipeline_$(date +%Y%m%d).json

# 화이트리스트 백업
python3 /Users/js/g9/scripts/setup_economic_whitelist.py
# 메뉴에서 "4. JSON 파일로 내보내기" 선택

# Neo4j 이벤트 데이터 백업
# (Neo4j 자체 백업 기능 사용)
```

### 오래된 데이터 정리

```cypher
// 90일 이전 이벤트 아카이빙
MATCH (e:Event)
WHERE e.timestamp < datetime() - duration('P90D')
SET e:ArchivedEvent
REMOVE e:Event
RETURN count(e) as archived;
```

---

## 📞 관련 문서

- **배포 가이드:** `/Users/js/g9/docs/ECONOMIC_EVENT_PIPELINE_SETUP.md`
- **파이프라인 설계:** `/Users/js/g9/docs/REALTIME_ECONOMIC_EVENT_PIPELINE.md`
- **n8n 워크플로우:** `/Users/js/g9/n8n_workflows/economic_event_pipeline.json`
- **대시보드 쿼리:** `/Users/js/g9/queries/economic_event_dashboard.cypher`

---

**최종 업데이트:** 2025-12-25
**작성자:** Claude Sonnet 4.5
