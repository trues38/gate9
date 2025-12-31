# G9 무료 데이터 수집 파이프라인 - 완전 가이드

## 개요

**월 $0 비용**으로 NBA + 경제 데이터를 수집하고 분석하는 시스템입니다.

### 핵심 철학

```
"API는 멍청하게, DB와 분석 엔진은 똑똑하게"
```

- ✅ API 호출 최소화 (월 500회 이내)
- ✅ Raw 데이터 저장 → 재처리 가능
- ✅ 무료 LLM으로 구조화
- ✅ Neo4j Graph DB로 관계 분석

---

## 비용 분석

| 항목 | 기존 (RapidAPI) | 신규 (무료) | 절감 |
|------|----------------|------------|------|
| Twitter API | $10-15/월 | **$0** | 100% |
| LLM 처리 | $5-10/월 | **$0** (MiMo-V2-Flash Free) | 100% |
| VPS | $6-12/월 | $6-12/월 | 0% |
| **합계** | **$21-37/월** | **$6-12/월** | **71% 절감** |

---

## 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│  LAYER 1: API Collection (Twttr API Free - 500/month)  │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  LAYER 2: Raw Storage (SQLite - Append-only)           │
│  - Deduplication                                        │
│  - Disaster recovery                                    │
│  - Reprocessing capability                              │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  LAYER 3: LLM Processing (MiMo-V2-Flash Free)          │
│  - Event type classification                            │
│  - Entity extraction                                    │
│  - Importance scoring                                   │
│  - Noise filtering                                      │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  LAYER 4: Graph Storage (Neo4j)                        │
│  - Event nodes                                          │
│  - Entity relationships                                 │
│  - Time-series analysis                                 │
└─────────────────────────────────────────────────────────┘
```

---

## 무료 API 설정

### 1. RapidAPI Twttr API (BASIC Plan)

1. **가입**: https://rapidapi.com/
2. **검색**: "Twttr API"
3. **플랜 선택**: BASIC ($0.00/mo)
4. **API Key 복사**

```bash
# .env 파일에 추가
RAPIDAPI_KEY=your_key_here
```

**제한:**
- 월 500 calls (우리는 300-400만 사용)
- Rate limit: 초당 5 calls (우리는 0.5s delay 사용)

---

### 2. OpenRouter (MiMo-V2-Flash Free)

1. **가입**: https://openrouter.ai/
2. **API Key 생성**
3. **모델 선택**: `xiaomi/mimo-v2-flash:free`

```bash
# .env 파일에 추가
OPENROUTER_API_KEY=your_key_here
```

**제한:**
- 무료 무제한 (Reasoning OFF)
- 목적: 데이터 정리/분류만

---

## 시간대 기반 수집 전략

### NBA (이벤트 기반)

**수집 시점:** 경기 전 4개 시간대

| 시간 | 목적 | 계정 수 | 예상 호출 |
|------|------|---------|-----------|
| T-2h | 심판 발표 | 2 | 2 |
| T-1h | 부상 확정 | 5 | 5 |
| T-30m | 라인업 확정 | 4 | 4 |
| T-0 | 최종 체크 | 3 | 3 |

**1경기당:** 14 calls
**하루 (8경기):** 112 calls
**월 (25일):** **280 calls** (NBA 예산 250 내)

---

### 경제 (세션 기반)

**수집 시점:** 시장 오픈 타임

| 시간 (KST) | 세션 | 계정 수 | 예상 호출 |
|-----------|------|---------|-----------|
| 08:00 | 아시아 오픈 | 7 | 7 |
| 16:00 | 유럽 오픈 | 7 | 7 |
| 22:30 | 미국 오픈 | 7 | 7 |
| 01:00 | 미장 중반 | 7 | 7 |
| 05:00 | 미장 마감 | 7 | 7 |

**하루:** 35 calls (주 5일)
**월 (20일):** **140 calls** (경제 예산 200 내)

---

## 데이터 흐름 상세

### Step 1: API Collection

```python
from sources.twttr_free_adapter import TwttrFreeAdapter

adapter = TwttrFreeAdapter()

# Batch fetch (효율적!)
tweets = adapter.fetch_accounts_batch(
    usernames=["ShamsCharania", "wojespn", "ChrisBHaynes"],
    since=datetime.now() - timedelta(hours=3),
    max_results_per_user=10,
    domain="nba"
)

# Budget tracking
print(adapter.get_budget_status())
# → {nba_used: 3, nba_remaining: 247, ...}
```

---

### Step 2: Raw Storage

```python
from storage.raw_storage import RawTweetStorage, convert_tweet_to_raw

storage = RawTweetStorage()

# Convert and save
raw_tweets = [convert_tweet_to_raw(t, domain="nba") for t in tweets]
saved_count = storage.save_tweets_batch(raw_tweets)

# Deduplication: text_hash로 자동 처리
# → 같은 내용이면 무시
```

---

### Step 3: LLM Processing

```python
from processing.llm_processor import LLMProcessor

processor = LLMProcessor()

# Get unprocessed tweets
unprocessed = storage.get_unprocessed_tweets(domain="nba", limit=50)

# Process with LLM
events = processor.process_tweets_batch(unprocessed, domain="nba")

# Output: Structured events
# {
#   event_type: "INJURY",
#   importance: 0.87,
#   entities: {player: "LeBron James", team: "LAL", status: "OUT"},
#   summary: "LeBron James ruled OUT with ankle injury"
# }
```

---

### Step 4: Neo4j Storage

```python
from adapters.neo4j_adapter import Neo4jAdapter

neo4j = Neo4jAdapter()

for event in events:
    neo4j.save_event({
        "event_id": f"evt_{event.tweet_id}",
        "event_type": event.event_type,
        "raw_text": event.raw_text,
        "entities": event.entities,
        ...
    })
```

---

## 전체 파이프라인 실행

```python
from main_pipeline import G9Pipeline

pipeline = G9Pipeline()

# NBA collection (자동으로 시간대 체크)
result = pipeline.run_nba_collection(game_times=[...])
# → {tweets_saved: 45, budget: {...}}

# LLM processing
result = pipeline.run_llm_processing(domain="nba", batch_size=50)
# → {events_extracted: 32, events_saved: 32}

# Economy collection
result = pipeline.run_economy_collection()
# → {tweets_saved: 28, budget: {...}}
```

---

## 스케줄러 사용

```python
from scheduling.time_based_scheduler import TimeBasedScheduler

scheduler = TimeBasedScheduler()

# NBA 수집 시점 체크
if scheduler.should_collect_nba(game_times):
    pipeline.run_nba_collection(game_times)

# 경제 수집 시점 체크
if scheduler.should_collect_economy():
    pipeline.run_economy_collection()

# 다음 수집 시간 확인
next_window = scheduler.get_next_collection_window(game_times)
# → ("nba", datetime(...), ["ShamsCharania", "wojespn"])
```

---

## 배포 및 자동화

### VPS 배포

```bash
# 1. 파일 업로드
scp -r vultr-g9-deploy root@YOUR_VPS_IP:~/

# 2. 환경변수 설정
ssh root@YOUR_VPS_IP
cd ~/vultr-g9-deploy
nano .env

# 추가:
RAPIDAPI_KEY=your_key_here
OPENROUTER_API_KEY=your_key_here

# 3. Docker 빌드
docker-compose up -d --build
```

---

### N8N 워크플로우

**NBA 수집 (경기 전 자동 실행):**

```
[Cron: 매시 정각]
    ↓
[HTTP: GET /games/today]  # ESPN에서 오늘 경기 조회
    ↓
[Function: 경기 시간 파싱]
    ↓
[HTTP: POST /collect/nba]  # NBA 수집 실행
    ↓
[Condition: tweets_saved > 0?]
    ↓
[HTTP: POST /process/llm]  # LLM 처리
```

**경제 수집 (세션 시간 자동 실행):**

```
[Cron: 08:00, 16:00, 22:30, 01:00, 05:00 KST]
    ↓
[HTTP: POST /collect/economy]
    ↓
[HTTP: POST /process/llm]
```

---

## 호출 수 모니터링

### API 사용량 확인

```bash
# Raw storage 확인
curl http://localhost:8001/storage/stats | jq .api_calls_today

# Budget 확인
curl http://localhost:8001/budget/status | jq .
# {
#   "nba_used": 142,
#   "nba_remaining": 108,
#   "economy_used": 85,
#   "economy_remaining": 115,
#   "percentage_used": 45.4
# }
```

---

## Neo4j 쿼리 예시

### 1. 오늘 부상 현황

```cypher
MATCH (e:NBAEvent)
WHERE e.event_type = "injury"
  AND date(e.collected_at) = date()
  AND e.status IN ["OUT", "QUESTIONABLE"]
RETURN e.entities.player as player,
       e.entities.team as team,
       e.status,
       e.raw_text,
       e.source_username
ORDER BY e.collected_at DESC
```

### 2. 소스별 신뢰도

```cypher
MATCH (e:NBAEvent)
WHERE date(e.collected_at) = date()
WITH e.source_username as source,
     AVG(e.importance) as avg_importance,
     COUNT(e) as total_events
RETURN source, avg_importance, total_events
ORDER BY avg_importance DESC
```

### 3. 이벤트 타임라인

```cypher
MATCH (e:NBAEvent)
WHERE date(e.collected_at) = date()
RETURN e.event_type as type,
       e.collected_at as time,
       e.summary
ORDER BY e.collected_at DESC
LIMIT 50
```

---

## 트러블슈팅

### API 호출 실패

```bash
# 로그 확인
docker logs g9-nba-collector | grep "API error"

# Budget 확인
# → nba_remaining < 0이면 예산 초과
```

### LLM 처리 에러

```bash
# Mock 모드인지 확인
docker exec g9-nba-collector python -c "
from processing.llm_processor import LLMProcessor
p = LLMProcessor()
print(p.mock_mode)
"

# OPENROUTER_API_KEY 확인
docker exec g9-nba-collector env | grep OPENROUTER
```

### Raw storage 가득 참

```bash
# DB 크기 확인
docker exec g9-nba-collector ls -lh data/raw_tweets.db

# 오래된 데이터 삭제 (7일 이상)
docker exec g9-nba-collector python -c "
from storage.raw_storage import RawTweetStorage
from datetime import datetime, timedelta
s = RawTweetStorage()
# Manual cleanup if needed
"
```

---

## 성능 최적화

### 1. Batch Processing

```python
# ❌ Bad: 1 tweet씩 처리
for tweet in tweets:
    process_single(tweet)

# ✅ Good: Batch 처리
process_batch(tweets, batch_size=50)
```

### 2. API Call Batching

```python
# ❌ Bad: 계정당 1 call
for account in accounts:
    fetch_tweets(account)

# ✅ Good: 한 번에 fetch
fetch_accounts_batch(accounts)
```

### 3. LLM 재처리 방지

```python
# Raw storage에 processed flag 사용
# → 이미 처리된 트윗은 스킵
unprocessed = storage.get_unprocessed_tweets(limit=100)
```

---

## 확장 전략

### 1단계: NBA + 경제 안정화
- 현재 설계대로 운영
- 월 500회 한도 내 안정적 수집

### 2단계: 축구 추가
- EPL/UCL 경기 시간 (한국 저녁)
- NBA와 시간대 겹치지 않음
- 추가 budget: +100 calls/month

### 3단계: 크립토 추가
- 24/7 구조 (별도 스케줄)
- Binance API (무료)
- Coingecko API (무료)

### 4단계: 실시간화
- 수익 나면 RapidAPI Pro 업그레이드
- Tier S 계정만 실시간 폴링
- 나머지는 시간대 기반 유지

---

## 파일 구조

```
vultr-g9-deploy/nba-collector/
├── sources/
│   ├── twttr_free_adapter.py      # 무료 API adapter
│   └── x_adapter.py                # (구) RapidAPI adapter
├── storage/
│   └── raw_storage.py              # SQLite raw storage
├── processing/
│   └── llm_processor.py            # MiMo-V2-Flash processor
├── scheduling/
│   └── time_based_scheduler.py     # 시간대 기반 스케줄러
├── adapters/
│   └── neo4j_adapter.py            # Neo4j connector
├── main_pipeline.py                # 통합 파이프라인
└── data/
    └── raw_tweets.db               # SQLite DB (자동 생성)
```

---

## 결론

**무료로 운영 가능한 데이터 수집 시스템 완성!**

- ✅ 월 $0 API 비용
- ✅ 월 500회 한도 내 안정적 운영
- ✅ NBA + 경제 데이터 커버
- ✅ 재처리 가능한 Raw storage
- ✅ 무료 LLM으로 구조화
- ✅ Neo4j Graph DB로 분석

**다음 단계:**
1. VPS 배포
2. N8N 워크플로우 설정
3. 1주일 테스트 (budget 모니터링)
4. 안정화 후 축구 추가

---

**작성일:** 2025-12-28
**버전:** v3.0 (Free Tier Edition)
**상태:** Production Ready
**월 비용:** $6-12 (VPS만)
