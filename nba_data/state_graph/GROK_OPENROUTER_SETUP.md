# Grok 4.1 Fast via OpenRouter - NBA 실시간 이벤트 정규화

## 개요

**경제 레짐 분석에 사용하던 Grok 4 FAST 모델을 NBA 실시간 이벤트 처리에 활용**

### 왜 Grok인가?

1. **X Search 네이티브 통합** (Grok 고유 기능)
   - X 플랫폼 실시간 데이터 직접 접근
   - 공식 계정 트윗 즉시 파싱

2. **FAST 모델 특징**
   - 저지연 응답 (< 1초)
   - 비용 효율적 ($0.20/1M input, $0.50/1M output)
   - 2M context window

3. **Agentic Tool Calling**
   - 구조화된 출력 (JSON)
   - 함수 호출 지원

---

## OpenRouter를 통한 접근

### 장점

- ✅ **통합 인터페이스**: 한 곳에서 여러 모델 접근
- ✅ **표준 API**: OpenAI 호환 엔드포인트
- ✅ **투명한 가격**: 마크업 없음
- ✅ **사용량 추적**: 대시보드 제공

### 가격 (2025년 12월 기준)

**Grok 4.1 Fast**:
- Input: $0.20 / 1M tokens
- Output: $0.50 / 1M tokens
- Cached input: $0.05 / 1M tokens

**예상 비용 (NBA 일일 업데이트)**:
- 트윗 100개/일 × 200 tokens = 20K tokens/일
- 응답 100개 × 100 tokens = 10K tokens/일
- **월 비용: ~$0.50** (30일 기준)

→ **경제 레짐 분석 대비 극도로 저렴**

---

## 설정 방법

### 1. OpenRouter API Key 발급

**URL**: https://openrouter.ai/keys

1. OpenRouter 계정 생성
2. API Keys 페이지 이동
3. "Create Key" 클릭
4. Key 복사

### 2. 환경변수 설정

```bash
# .env 파일에 추가
echo 'OPENROUTER_API_KEY="sk-or-v1-..."' >> .env

# 또는 터미널에 직접 export
export OPENROUTER_API_KEY="sk-or-v1-..."
```

### 3. 크레딧 충전

**URL**: https://openrouter.ai/credits

- 최소 충전: $5
- 자동 충전 설정 가능
- Pay-as-you-go (사용한 만큼만)

---

## 사용법

### 기본 테스트

```bash
# 환경변수 확인
echo $OPENROUTER_API_KEY

# 테스트 실행
python3 test_grok_openrouter.py
```

### 출력 예시

```
🧪 Grok 4.1 Fast - NBA 이벤트 정규화 테스트
================================================================================

[1/10] 원본 트윗:
  Luka Doncic is OUT tonight vs Warriors due to ankle injury

✅ 정규화 결과:
{
  "event_type": "lineup_change",
  "player": "Luka Doncic",
  "team": "DAL",
  "status": "OUT",
  "reason": "ankle",
  "game": "DAL vs GSW",
  "referee_crew": null,
  "confidence": 0.95,
  "raw_text": "Luka Doncic is OUT tonight vs Warriors due to ankle injury"
}
```

---

## 핵심 기능

### 1. 라인업 변경 감지

**입력 (다양한 표현)**:
- "Luka OUT vs Warriors"
- "Kawhi ruled out for rest"
- "Jimmy Butler (ankle) - INACTIVE"

**출력 (정규화)**:
```json
{
  "event_type": "lineup_change",
  "player": "Player Name",
  "team": "TEAM_ABBR",
  "status": "OUT",
  "reason": "injury/rest/personal",
  "game": "TEAM1 vs TEAM2",
  "confidence": 0.95
}
```

### 2. 부상 리포트 파싱

**입력**:
- "AD QUESTIONABLE (back)"
- "Steph PROBABLE vs Rockets"
- "Giannis DOUBTFUL (knee)"

**출력**:
```json
{
  "event_type": "injury_report",
  "player": "Anthony Davis",
  "team": "LAL",
  "status": "QUESTIONABLE",
  "reason": "back",
  "confidence": 0.90
}
```

### 3. 심판 배정 추출

**입력**:
```
Crew Chief: Scott Foster
Referees: Tony Brothers, Marc Davis
Game: MIA @ LAL
```

**출력**:
```json
{
  "event_type": "referee_assignment",
  "game": "MIA vs LAL",
  "referee_crew": ["Scott Foster", "Tony Brothers", "Marc Davis"],
  "confidence": 0.98
}
```

---

## n8n 워크플로우 통합

### 전체 파이프라인

```
① X (공식 계정)
      ↓
② n8n Trigger
   - Twitter Watch Timeline
   - 계정 화이트리스트 필터
      ↓
③ 1차 필터 (n8n)
   - 키워드: OUT, LINEUP, REF, INACTIVE
   - 정규식: injury|rest|ruled out
      ↓
④ 의미 판단 (n8n Function)
   - 스팸 제거
   - 중복 제거
      ↓
⑤ Grok 4.1 Fast 호출
   - 트윗 정규화
   - 구조화된 데이터 추출
      ↓
⑥ Event 저장 (Neo4j)
   - Event 노드 생성
   - 경기/선수와 연결
      ↓
⑦ Context 재계산
   - 과거 유사 상황 검색
   - 영향도 계산
      ↓
⑧ 리포트 생성 (Claude/GPT)
   - 베팅 시그널
   - 설명 생성
```

### n8n 노드 구성

```json
{
  "nodes": [
    {
      "name": "Twitter Watch",
      "type": "n8n-nodes-base.twitter",
      "parameters": {
        "resource": "tweet",
        "operation": "search",
        "searchText": "from:@OfficialNBARefs OR from:@ShamsCharania"
      }
    },
    {
      "name": "Keyword Filter",
      "type": "n8n-nodes-base.filter",
      "parameters": {
        "conditions": {
          "string": [
            {
              "value1": "={{ $json.text }}",
              "operation": "contains",
              "value2": "OUT|LINEUP|REF|INACTIVE"
            }
          ]
        }
      }
    },
    {
      "name": "Grok Normalize",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "method": "POST",
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "authentication": "headerAuth",
        "headerParameters": {
          "parameters": [
            {
              "name": "Authorization",
              "value": "Bearer {{ $env.OPENROUTER_API_KEY }}"
            }
          ]
        },
        "body": {
          "model": "x-ai/grok-4.1-fast",
          "messages": [
            {
              "role": "system",
              "content": "Normalize NBA event tweets to JSON..."
            },
            {
              "role": "user",
              "content": "={{ $json.text }}"
            }
          ],
          "temperature": 0.1
        }
      }
    },
    {
      "name": "Save to Neo4j",
      "type": "n8n-nodes-base.neo4j",
      "parameters": {
        "query": "CREATE (e:Event {...}) ..."
      }
    }
  ]
}
```

---

## 모니터링

### API 사용량 확인

**OpenRouter Dashboard**: https://openrouter.ai/activity

실시간 확인 가능:
- 요청 수
- 토큰 사용량
- 비용
- 에러율

### 로그 저장

모든 요청/응답을 로그로 저장:

```python
# test_grok_openrouter.py에 자동 포함
output_file = "grok_test_results.json"
```

---

## 비용 최적화

### 1. Prompt Caching (OpenRouter)

반복되는 system prompt를 캐싱:

```python
# 캐싱된 입력: $0.05/1M tokens (75% 할인)
payload = {
    "model": "x-ai/grok-4.1-fast",
    "messages": [
        {
            "role": "system",
            "content": "...",  # 이 부분이 캐싱됨
            "cache_control": {"type": "ephemeral"}
        }
    ]
}
```

**절감 효과**:
- System prompt: 500 tokens
- 하루 100회 호출
- 일반: $0.01 → 캐싱: $0.0025
- **월 75% 절감**

### 2. Batch Processing

여러 트윗을 한 번에 처리:

```python
# 개별 호출 (비효율)
for tweet in tweets:
    normalize(tweet)  # 100 calls

# 배치 호출 (효율)
normalize_batch(tweets)  # 1 call with longer context
```

### 3. 조건부 호출

n8n에서 1차 필터링으로 불필요한 API 호출 제거:

```
100개 트윗 → 키워드 필터 → 10개 관련 트윗 → Grok 호출
→ 90% API 비용 절감
```

---

## 트러블슈팅

### API Key 오류

```
❌ OPENROUTER_API_KEY 환경변수를 설정하세요
```

**해결**:
```bash
export OPENROUTER_API_KEY="sk-or-v1-..."
```

### Rate Limit

OpenRouter 기본 제한:
- 무료: 20 requests/minute
- 유료: 200 requests/minute

**해결**: 크레딧 충전 후 자동 상향

### JSON 파싱 오류

Grok이 가끔 설명을 포함해서 응답:

```python
# 코드에 이미 포함됨
if "```json" in content:
    content = content.split("```json")[1].split("```")[0].strip()
```

---

## 경제 레짐 → NBA 적용 사례

### 경제 레짐 분석에서의 사용

사용자가 Grok 4 FAST를 주력으로 사용한 이유:
1. **실시간 뉴스 파싱** (경제 지표, 중앙은행 발표)
2. **표현 정규화** (Fed hawkish/dovish 구분)
3. **신속한 분류** (저지연 필수)

### NBA 실시간 분석 적용

동일한 패턴:
1. **실시간 X 트윗** (라인업, 부상)
2. **표현 정규화** (OUT/ruled out/inactive → OUT)
3. **신속한 분류** (경기 시작 전 처리 필수)

→ **완벽한 use case 매칭**

---

## 다음 단계

### 1. n8n 워크플로우 구축
- Twitter OAuth 연결
- Grok API 노드 설정
- Neo4j 저장 로직

### 2. 프로덕션 배포
- 환경변수 관리
- 에러 핸들링
- 모니터링 설정

### 3. 고도화
- Reasoning 모드 활용
- Multi-turn conversation (애매한 경우)
- Confidence threshold 조정

---

## 참고 자료

### OpenRouter
- 모델 정보: https://openrouter.ai/x-ai/grok-4.1-fast
- API 문서: https://openrouter.ai/docs
- 가격 계산기: https://invertedstone.com/calculators/openrouter-pricing

### Grok
- xAI 공식: https://x.ai/news/grok-4-1-fast
- Agent Tools: https://x.ai/news/agent-tools

### n8n
- Twitter 노드: https://docs.n8n.io/integrations/builtin/app-nodes/n8n-nodes-base.twitter/
- HTTP Request: https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/

---

## 요약

✅ **Grok 4.1 Fast via OpenRouter**
- Model ID: `x-ai/grok-4.1-fast`
- 가격: $0.20 input, $0.50 output / 1M tokens
- Context: 2M tokens

✅ **NBA 실시간 이벤트 정규화**
- Lineup changes → 구조화된 JSON
- Injury reports → 표준 상태 코드
- Referee assignments → 배열 추출

✅ **경제 레짐 분석 경험 활용**
- 실시간 뉴스 파싱 패턴 동일
- FAST 모델 저지연 특성 활용
- 비용 효율적 ($0.50/월 예상)

✅ **n8n 파이프라인 준비 완료**
- X Trigger → Filter → Grok → Neo4j → Report

**즉시 테스트 가능**:
```bash
export OPENROUTER_API_KEY="sk-or-v1-..."
python3 test_grok_openrouter.py
```
