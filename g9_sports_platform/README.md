# G9 Sports Intelligence Platform

**도메인 전문가의 DATA + 빠른 X + 깊은 Reddit + 기억하는 Graph**

Multi-sport intelligence platform combining expert datasets, real-time events, qualitative analysis, and graph memory.

## Architecture

```
Layer 0: Domain Experts (Kaggle + GitHub)
├── 심판 배정 (2016-2025, 9,562경기) → 최근 2시즌만 (2,090경기)
├── NBA 게임 통계
└── 선수 시즌 통계

Layer 1: Real-time Events (X Search)
├── xAI Agent Tools API
├── Tier 1/2/3 소스별 신뢰도
└── 부상/라인업/트레이드 실시간 감지

Layer 2: Qualitative Analysis (Reddit)
├── r/nba (Hot/Top/New/Controversial)
├── r/nbadiscussion (심층 분석)
└── 3-Tier 저장 전략
    ├── Tier 1: Core Intelligence (43개)
    │   └── 심층 분석, 저널리즘, 휴먼 스토리 → Neo4j
    ├── Tier 2: Sentiment Summary
    │   └── 선수/팀 여론, 이슈 트렌드 → Neo4j 집계
    └── Tier 3: Raw Archive (224개) → JSON 보관

Layer 3: Memory (Neo4j Graph RAG)
├── 모든 레이어 연결
├── 선수/팀/경기 컨텍스트
└── Cross-validation (Expert ↔ Community)
```

## 수집된 데이터 (12월 2025 기준)

**Layer 0 (Expert):**
- Kaggle 심판 배정: 2,090 경기 (23-24, 24-25 시즌)

**Layer 2 (Reddit):**
- r/nba: 189개 포스트, 3,996 댓글
- r/nbadiscussion: 35개 심층 분석
- 총 1.5MB

**분류:**
- Tier 1 Core: 43개 (Neo4j 저장)
- Tier 2 Sentiment: 7명 선수, 4팀 추적
- Tier 3 Raw: 224개 원본 보관

## Quick Start

### 1. 환경 설정

```bash
cp .env.example .env
# Edit .env with your API keys
```

### 2. Docker Compose

```bash
docker-compose up -d
```

### 3. Reddit 데이터 Neo4j 로드

```bash
python3 layer2_qualitative/load_reddit_to_neo4j.py \
  --tier1 data/nba/reddit/december_2025/tier1_core_intelligence.json \
  --tier2 data/nba/reddit/december_2025/tier2_sentiment_summary.json
```

### 4. API 서버 실행

```bash
uvicorn api:app --host 0.0.0.0 --port 8000
```

## API Endpoints

```bash
# Real-time events
GET /api/nba/events
GET /api/nba/events/{team}

# Post-game analysis
POST /api/nba/postgame

# Player context (includes Reddit sentiment)
GET /api/nba/player/{name}/context

# Pre-game context
GET /api/nba/pregame/{game_id}?teams=LAL,GSW
```

## Reddit 수집 (수동)

```bash
# Top posts
python3 layer2_qualitative/reddit_collector.py nba \
  --game-id 0022400123 \
  --teams LAL,GSW

# 또는 직접 스크립트 실행 (data/nba/reddit/ 폴더)
```

## Neo4j 쿼리 예시

```cypher
// 12월 LeBron 여론
MATCH (p:Player {name: "LeBron"})-[:HAS_SENTIMENT]->(s:SentimentSummary {period: "2025-12"})
RETURN s.mentions, s.avg_score, s.sentiment_keywords

// LeBron 관련 심층 분석 포스트
MATCH (post:RedditPost)-[:MENTIONS]->(p:Player {name: "LeBron"})
WHERE post.tier1_reason = "DEEP_ANALYSIS"
RETURN post.title, post.selftext

// Clippers 여론
MATCH (t:Team {name: "Clippers"})-[:HAS_SENTIMENT]->(s:TeamSentiment {period: "2025-12"})
RETURN s.keywords
```

## Cost Estimate

- Kaggle: Free
- Reddit: Free (rate limit only)
- xAI (X Search): $5/month
- OpenRouter (Reddit LLM): $5/month
- Neo4j: Self-hosted (free)

**Total: ~$10/month per sport**

## Sports Expansion

각 스포츠별 `sports/{sport}/config.yaml` 추가로 확장 가능:

```yaml
sport:
  name: "National Football League"
  code: "NFL"
  enabled: true

layer1_realtime:
  x_accounts:
    tier1:
      - handle: "AdamSchefter"
      - handle: "RapSheet"
```

## File Structure

```
g9_sports_platform/
├── data/
│   └── nba/
│       ├── kaggle/              # Kaggle datasets
│       └── reddit/              # Reddit JSON files
├── layer0_experts/
│   └── kaggle_fetcher.py
├── layer1_realtime/
│   └── x_search_monitor.py
├── layer2_qualitative/
│   ├── reddit_collector.py
│   └── load_reddit_to_neo4j.py  # ← Reddit → Neo4j
├── layer3_memory/
│   └── schema.cypher
├── orchestrator.py              # 4-Layer 통합
├── api.py                       # FastAPI server
└── docker-compose.yml
```

## License

MIT
