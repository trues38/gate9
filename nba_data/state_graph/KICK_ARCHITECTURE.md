# NBA KICK 아키텍처: "빠른 X + 깊은 Reddit + 기억하는 Graph"

**작성일**: 2025-12-25
**핵심**: 실시간 알림(X) + 정성 분석(Reddit) + 맥락 기억(Graph)

---

## 🎯 핵심 전략

### "우리의 모든 우려를 불식시키는 방법"

#### ❌ 기존 접근의 문제
```
공식 트윗만으로 충분 → 표면적 데이터만
부상 정보 = 텍스트   → 맥락 부족
AI 분석으로 추론     → 실제 팬들의 인사이트 무시
```

#### ✅ 새로운 접근 (KICK)
```
Layer 1 (Real-time):
  X Search → 부상/결장 즉시 감지
  → 웹 알림 (분석 없음, 속도 우선)
  → "LeBron OUT tonight" → 즉시 알림

Layer 2 (Deep):
  경기 후 Reddit Post-Game Thread
  → 팬들의 실제 평가 수집
  → "AD was clearly limping in Q4"
  → "Coach Ham's rotations were terrible"
  → "Reaves is playing like a starter"

Layer 3 (Memory):
  Neo4j Graph에 시간순 저장
  → 선수 평가 변화 추적
  → 코치 전술 변화 감지
  → 팀 분위기 변화 파악
```

---

## 📊 3-Layer 파이프라인 상세

### Layer 1: Real-time Alert (X Search)

**목적**: 부상/결장 정보를 **즉시** 웹에 알림

**데이터 소스**:
- X Search: `injury OR out OR doubtful OR questionable`
- 공식 계정: @ShamsCharania, @wojespn, @OfficialNBARefs

**처리 로직**:
```javascript
// n8n Workflow: X Search Real-time Monitor

// 1. X Search 실행 (xAI Native API)
const xSearchQuery = `
  (injury OR out OR doubtful OR questionable OR lineup)
  (from:ShamsCharania OR from:wojespn OR from:OfficialNBARefs)
  -is:retweet
`;

const xaiResponse = await xai.agents.create({
  model: "grok-beta",
  tools: [
    {
      type: "function",
      function: {
        name: "x_search",
        description: "Search X for real-time NBA injury news",
        parameters: {
          query: xSearchQuery,
          max_results: 10,
          search_type: "latest"
        }
      }
    }
  ]
});

// 2. 간단한 파싱 (LLM 분석 없음!)
const parsed = tweets.map(tweet => {
  // 정규식으로 빠르게 파싱
  const playerMatch = tweet.text.match(/(\w+ \w+)'s? (OUT|DOUBTFUL|QUESTIONABLE)/i);
  const teamMatch = tweet.text.match(/(Lakers|Warriors|Celtics)/i);

  return {
    player: playerMatch?.[1],
    status: playerMatch?.[2],
    team: teamMatch?.[1],
    source: tweet.author,
    timestamp: tweet.created_at,
    text: tweet.text
  };
});

// 3. 즉시 웹 알림 (Next.js API Route)
await fetch('http://localhost:3000/api/alerts/injury', {
  method: 'POST',
  body: JSON.stringify({
    type: 'REAL_TIME_INJURY',
    data: parsed,
    priority: 'HIGH'
  })
});

// 4. Neo4j에 간단히 저장 (분석은 나중)
await neo4j.run(`
  MERGE (p:Player {name: $player})
  CREATE (i:InjuryAlert {
    status: $status,
    source: $source,
    timestamp: datetime($timestamp),
    text: $text
  })
  MERGE (p)-[:HAS_ALERT]->(i)
`, parsed);
```

**웹 알림 UI**:
```typescript
// app/api/alerts/injury/route.ts
export async function POST(req: Request) {
  const { data } = await req.json();

  // Pusher 또는 WebSocket으로 즉시 전송
  await pusher.trigger('nba-alerts', 'injury-alert', {
    player: data.player,
    status: data.status,
    team: data.team,
    timestamp: new Date().toISOString()
  });

  return Response.json({ success: true });
}

// 클라이언트 (실시간 토스트 알림)
pusher.subscribe('nba-alerts').bind('injury-alert', (data) => {
  toast.error(`🚨 ${data.player} ${data.status} - ${data.team}`);
});
```

**특징**:
- ✅ **속도 우선**: LLM 분석 없음 (1-2초 이내)
- ✅ **단순 파싱**: 정규식으로 핵심만 추출
- ✅ **즉시 알림**: 웹소켓/Pusher로 실시간 전송

---

### Layer 2: Deep Analysis (Reddit Post-Game)

**목적**: 경기 후 **정성 데이터** 수집 및 분석

**데이터 소스**:
- r/nba - Post Game Thread (메인)
- r/lakers, r/warriors 등 팀별 서브레딧
- Top comments (500+ upvotes)

**수집 타이밍**:
```
경기 종료 → 1시간 대기 → Reddit 수집 시작
(팬들이 분석 댓글을 작성할 시간 필요)
```

**Reddit API 연동**:
```python
# scripts/reddit_post_game_collector.py
import praw
import os
from datetime import datetime, timedelta

# Reddit API 설정
reddit = praw.Reddit(
    client_id=os.getenv('REDDIT_CLIENT_ID'),
    client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
    user_agent='NBA-Analysis-Bot/1.0'
)

def collect_post_game_threads(game_id: str, teams: list[str]):
    """
    경기 후 Post-Game Thread 수집

    Args:
        game_id: NBA 게임 ID (예: "0022400123")
        teams: 팀 약자 리스트 (예: ["LAL", "GSW"])
    """

    # 1. r/nba에서 Post Game Thread 찾기
    subreddit = reddit.subreddit('nba')
    search_query = f"Post Game Thread {teams[0]} {teams[1]}"

    threads = subreddit.search(
        search_query,
        time_filter='day',
        sort='relevance',
        limit=5
    )

    for thread in threads:
        # Post Game Thread인지 확인
        if 'post game thread' not in thread.title.lower():
            continue

        # 2. Top Comments 수집 (500+ upvotes)
        thread.comment_sort = 'top'
        thread.comments.replace_more(limit=0)  # "load more" 확장

        top_comments = [
            {
                'author': comment.author.name if comment.author else '[deleted]',
                'body': comment.body,
                'score': comment.score,
                'created_utc': comment.created_utc,
                'permalink': comment.permalink
            }
            for comment in thread.comments.list()
            if comment.score >= 500  # 500+ upvotes만
        ]

        # 3. LLM으로 분석
        analysis = analyze_reddit_comments(top_comments, game_id)

        # 4. Neo4j에 저장
        store_reddit_analysis(game_id, thread.id, analysis)

        return {
            'thread_id': thread.id,
            'thread_title': thread.title,
            'thread_url': thread.url,
            'total_comments': thread.num_comments,
            'top_comments_count': len(top_comments),
            'analysis': analysis
        }

def analyze_reddit_comments(comments: list[dict], game_id: str):
    """
    Reddit 댓글을 LLM으로 분석

    카테고리:
    1. 선수 평가 (Player Performance)
    2. 코치 분석 (Coaching Decisions)
    3. 전술 평가 (Tactical Analysis)
    4. 팀 분위기 (Team Chemistry)
    """

    # 댓글을 하나의 텍스트로 결합
    combined_text = "\n\n---\n\n".join([
        f"[Score: {c['score']}] {c['body']}"
        for c in comments
    ])

    # OpenRouter로 분석 (Qwen 2.5 VL 72B - 저렴하고 강력)
    prompt = f"""Analyze these Reddit Post-Game Thread comments and extract insights.

Game ID: {game_id}

Comments:
{combined_text}

Extract the following:

1. **Player Evaluations** (positive/negative/neutral):
   - Which players were praised? Why?
   - Which players were criticized? Why?
   - Any injury concerns mentioned?

2. **Coaching Analysis**:
   - Rotations (good/bad decisions)
   - Timeout usage
   - Defensive/Offensive schemes

3. **Tactical Insights**:
   - What worked? (specific plays/strategies)
   - What didn't work?
   - Matchup advantages/disadvantages

4. **Team Chemistry**:
   - Teamwork observations
   - Leadership moments
   - Conflicts or issues

5. **Sentiment Summary**:
   - Overall fan mood (positive/negative/mixed)
   - Key controversies

Format as JSON:
{{
  "player_evaluations": [
    {{"player": "LeBron James", "sentiment": "positive", "key_points": ["..."], "sample_quote": "..."}},
    ...
  ],
  "coaching_analysis": {{
    "rotations": {{"sentiment": "negative", "key_points": [...]}},
    "schemes": {{"sentiment": "positive", "key_points": [...]}}
  }},
  "tactical_insights": [...],
  "team_chemistry": {...},
  "sentiment_summary": {{
    "overall": "mixed",
    "controversies": [...]
  }}
}}
"""

    response = requests.post(
        'https://openrouter.ai/api/v1/chat/completions',
        headers={
            'Authorization': f'Bearer {os.getenv("OPENROUTER_API_KEY")}',
            'Content-Type': 'application/json'
        },
        json={
            'model': 'qwen/qwen2.5-vl-72b-instruct',
            'messages': [{'role': 'user', 'content': prompt}],
            'temperature': 0.3,
            'max_tokens': 2000
        }
    )

    return response.json()['choices'][0]['message']['content']

def store_reddit_analysis(game_id: str, thread_id: str, analysis: dict):
    """Neo4j에 Reddit 분석 저장"""

    from neo4j import GraphDatabase

    driver = GraphDatabase.driver(
        'bolt://neo4j-nba:7687',
        auth=('neo4j', os.getenv('NEO4J_NBA_PASSWORD'))
    )

    with driver.session() as session:
        # 1. RedditThread 노드 생성
        session.run("""
            MERGE (g:Game {game_id: $game_id})
            CREATE (rt:RedditThread {
                thread_id: $thread_id,
                analyzed_at: datetime(),
                sentiment_overall: $sentiment
            })
            MERGE (g)-[:HAS_REDDIT_THREAD]->(rt)
        """, game_id=game_id, thread_id=thread_id,
             sentiment=analysis['sentiment_summary']['overall'])

        # 2. 선수 평가 저장
        for eval in analysis['player_evaluations']:
            session.run("""
                MERGE (p:Player {name: $player})
                CREATE (pe:PlayerEvaluation {
                    sentiment: $sentiment,
                    key_points: $key_points,
                    sample_quote: $sample_quote,
                    source: 'reddit',
                    timestamp: datetime()
                })
                MERGE (p)-[:HAS_EVALUATION]->(pe)

                MATCH (rt:RedditThread {thread_id: $thread_id})
                MERGE (pe)-[:FROM_THREAD]->(rt)
            """, player=eval['player'], sentiment=eval['sentiment'],
                 key_points=eval['key_points'], sample_quote=eval['sample_quote'],
                 thread_id=thread_id)

        # 3. 코치 분석 저장
        session.run("""
            MATCH (g:Game {game_id: $game_id})-[:HOME_TEAM|AWAY_TEAM]->(t:Team)
            MATCH (t)-[:COACHED_BY]->(c:Coach)
            CREATE (ca:CoachingAnalysis {
                rotations_sentiment: $rotations_sentiment,
                rotations_points: $rotations_points,
                schemes_sentiment: $schemes_sentiment,
                schemes_points: $schemes_points,
                timestamp: datetime()
            })
            MERGE (c)-[:HAS_ANALYSIS]->(ca)

            MATCH (rt:RedditThread {thread_id: $thread_id})
            MERGE (ca)-[:FROM_THREAD]->(rt)
        """, game_id=game_id, thread_id=thread_id,
             rotations_sentiment=analysis['coaching_analysis']['rotations']['sentiment'],
             rotations_points=analysis['coaching_analysis']['rotations']['key_points'],
             schemes_sentiment=analysis['coaching_analysis']['schemes']['sentiment'],
             schemes_points=analysis['coaching_analysis']['schemes']['key_points'])

    driver.close()
```

**n8n 워크플로우 통합**:
```javascript
// n8n Cron Trigger: 매일 자정 + 경기 후 1시간
// Schedule: "0 1,2,3,4 * * *" (새벽 1-4시, 경기 종료 후)

const today_games = await neo4j.run(`
  MATCH (g:Game)
  WHERE date(g.game_date) = date()
    AND g.status = 'Final'
    AND NOT EXISTS((g)-[:HAS_REDDIT_THREAD]->())
  RETURN g.game_id, g.home_team, g.away_team
`);

for (const game of today_games) {
  // Python 스크립트 실행
  await $exec(`python3 /Users/js/g9/nba_data/state_graph/scripts/reddit_post_game_collector.py \
    --game_id ${game.game_id} \
    --teams ${game.home_team},${game.away_team}`);
}
```

**특징**:
- ✅ **깊이**: 팬들의 실제 분석 및 인사이트
- ✅ **정성 데이터**: 숫자로 나타나지 않는 팀 분위기, 코칭 평가
- ✅ **신뢰성**: 500+ upvotes = 커뮤니티 검증된 의견

---

### Layer 3: Memory (Neo4j Graph)

**목적**: 시간에 따른 **맥락 보존** 및 **패턴 발견**

**Graph 스키마**:
```cypher
// 노드 타입
(:Player)           - 선수
(:Coach)            - 코치
(:Team)             - 팀
(:Game)             - 경기
(:InjuryAlert)      - 실시간 부상 알림 (Layer 1)
(:RedditThread)     - Reddit Post-Game Thread (Layer 2)
(:PlayerEvaluation) - 선수 평가 (Reddit 분석 결과)
(:CoachingAnalysis) - 코치 분석 (Reddit 분석 결과)

// 관계
(:Player)-[:HAS_ALERT]->(:InjuryAlert)
(:Player)-[:HAS_EVALUATION]->(:PlayerEvaluation)
(:Coach)-[:HAS_ANALYSIS]->(:CoachingAnalysis)
(:Game)-[:HAS_REDDIT_THREAD]->(:RedditThread)
(:PlayerEvaluation)-[:FROM_THREAD]->(:RedditThread)
(:CoachingAnalysis)-[:FROM_THREAD]->(:RedditThread)
```

**시계열 쿼리 예시**:

```cypher
// 1. 선수 평가 변화 추적 (최근 10경기)
MATCH (p:Player {name: 'Anthony Davis'})-[:HAS_EVALUATION]->(pe:PlayerEvaluation)
  -[:FROM_THREAD]->(rt:RedditThread)<-[:HAS_REDDIT_THREAD]-(g:Game)
WHERE g.game_date >= date() - duration({days: 30})
RETURN g.game_date, pe.sentiment, pe.key_points, pe.sample_quote
ORDER BY g.game_date DESC
LIMIT 10

// 결과:
// 2025-12-24: positive - ["Dominant in the paint", "12 rebounds"]
// 2025-12-22: negative - ["Limping in Q4", "Only 8 points"]
// 2025-12-20: positive - ["Triple-double threat", "Great defense"]
// → AD의 컨디션 변화 추적 가능!

// 2. 코치 전술 평가 변화
MATCH (c:Coach {name: 'Darvin Ham'})-[:HAS_ANALYSIS]->(ca:CoachingAnalysis)
  -[:FROM_THREAD]->(rt:RedditThread)<-[:HAS_REDDIT_THREAD]-(g:Game)
WHERE g.game_date >= date() - duration({days: 60})
WITH g.game_date,
     ca.rotations_sentiment AS rotations,
     ca.schemes_sentiment AS schemes
ORDER BY g.game_date DESC
RETURN
  date_trunc('week', g.game_date) AS week,
  count(*) AS games,
  sum(CASE WHEN rotations = 'positive' THEN 1 ELSE 0 END) AS good_rotations,
  sum(CASE WHEN rotations = 'negative' THEN 1 ELSE 0 END) AS bad_rotations,
  sum(CASE WHEN schemes = 'positive' THEN 1 ELSE 0 END) AS good_schemes

// 결과:
// Week 51: 3 games, 1 good rotation, 2 bad rotations → 팬들 불만 증가
// Week 50: 4 games, 3 good rotations, 1 bad rotation  → 개선 중

// 3. 부상 알림과 Reddit 평가 연결
MATCH (p:Player)-[:HAS_ALERT]->(ia:InjuryAlert)
WHERE ia.timestamp >= datetime() - duration({days: 7})
WITH p, ia
OPTIONAL MATCH (p)-[:HAS_EVALUATION]->(pe:PlayerEvaluation)
  -[:FROM_THREAD]->(rt:RedditThread)<-[:HAS_REDDIT_THREAD]-(g:Game)
WHERE g.game_date >= date(ia.timestamp)
RETURN p.name, ia.status, ia.timestamp,
       collect({
         game_date: g.game_date,
         sentiment: pe.sentiment,
         quote: pe.sample_quote
       }) AS post_injury_reactions

// 결과:
// LeBron James, OUT, 2025-12-23
// → Post-injury reactions:
//   [2025-12-24: negative, "Team looked lost without LeBron"]
//   [2025-12-25: positive, "AD stepped up as a leader"]
```

**특징**:
- ✅ **맥락 보존**: 시간순 평가 변화
- ✅ **패턴 발견**: 선수 컨디션 추세, 코치 전술 효과
- ✅ **인과 관계**: 부상 → 팀 성적 → 팬 평가

---

## 🔧 환경변수 업데이트

**`.env.unified` 추가 필요**:
```bash
# ============================================
# Reddit API (Layer 2)
# ============================================
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=NBA-Analysis-Bot/1.0

# ============================================
# X Search (Layer 1 - xAI Native)
# ============================================
XAI_API_KEY=xai-...

# ============================================
# Web Alert (Layer 1)
# ============================================
PUSHER_APP_ID=...
PUSHER_KEY=...
PUSHER_SECRET=...
PUSHER_CLUSTER=us2

# (또는 WebSocket 사용)
WEB_ALERT_WEBHOOK_URL=http://localhost:3000/api/alerts/injury
```

---

## 📈 데이터 흐름 예시

### 시나리오: LeBron 부상 → 경기 → Reddit 분석

#### **1. 실시간 알림 (Layer 1)**
```
15:30 - @ShamsCharania 트윗:
"Lakers' LeBron James (ankle) ruled OUT for tonight vs Warriors"

15:30:05 - X Search 감지
15:30:07 - 정규식 파싱 완료
15:30:09 - 웹 알림 전송
15:30:10 - Neo4j InjuryAlert 노드 생성

→ 사용자 화면에 토스트 알림 표시:
  "🚨 LeBron James OUT - Lakers vs Warriors"
```

#### **2. 경기 진행**
```
19:00 - 경기 시작 (Lakers vs Warriors)
21:30 - 경기 종료 (Lakers 98 - Warriors 110)
```

#### **3. Reddit 수집 (Layer 2)**
```
22:30 - n8n Cron 실행 (경기 후 1시간)
22:31 - Reddit Post-Game Thread 찾기
22:32 - Top 500+ upvotes 댓글 수집 (23개)
22:35 - Qwen 2.5 VL 72B로 분석
22:37 - Neo4j에 저장 완료

분석 결과:
{
  "player_evaluations": [
    {
      "player": "Anthony Davis",
      "sentiment": "positive",
      "key_points": [
        "Carried the team without LeBron",
        "34 points, 12 rebounds",
        "Showed leadership"
      ],
      "sample_quote": "AD was incredible tonight. This is the AD we need in the playoffs."
    },
    {
      "player": "D'Angelo Russell",
      "sentiment": "negative",
      "key_points": [
        "Poor shot selection",
        "3-14 from the field",
        "Defensive lapses"
      ],
      "sample_quote": "DLo was a liability on both ends. Trade him already."
    }
  ],
  "coaching_analysis": {
    "rotations": {
      "sentiment": "negative",
      "key_points": [
        "Reaves played only 22 minutes (should be more)",
        "Rui benched in Q4 despite hot hand",
        "No adjustments to Warriors' zone"
      ]
    },
    "schemes": {
      "sentiment": "neutral",
      "key_points": [
        "Defensive effort was there",
        "Offense stagnated without LeBron"
      ]
    }
  },
  "sentiment_summary": {
    "overall": "negative",
    "controversies": [
      "Coach Ham's rotations",
      "D'Angelo Russell trade talk"
    ]
  }
}
```

#### **4. Graph 쿼리 (Layer 3)**
```cypher
// 다음 날, LeBron 복귀 여부 판단을 위한 맥락 조회
MATCH (p:Player {name: 'LeBron James'})-[:HAS_ALERT]->(ia:InjuryAlert)
WHERE ia.timestamp >= datetime() - duration({days: 7})
WITH p, ia
MATCH (t:Team {abbreviation: 'LAL'})<-[:PLAYS_FOR]-(p)
MATCH (t)-[:PLAYED_GAME]->(g:Game)-[:HAS_REDDIT_THREAD]->(rt:RedditThread)
WHERE g.game_date >= date(ia.timestamp)
OPTIONAL MATCH (ad:Player {name: 'Anthony Davis'})-[:HAS_EVALUATION]->(pe:PlayerEvaluation)
  -[:FROM_THREAD]->(rt)
RETURN
  ia.status AS lebron_status,
  ia.timestamp AS injury_time,
  g.game_date AS game_without_lebron,
  g.result AS game_result,
  pe.sentiment AS ad_performance,
  pe.key_points AS ad_highlights

결과:
lebron_status: "OUT"
injury_time: 2025-12-23 15:30:00
game_without_lebron: 2025-12-23
game_result: "Loss (98-110)"
ad_performance: "positive"
ad_highlights: ["34 points", "Showed leadership"]

→ 분석: LeBron 없이 AD가 선전했지만 패배
→ 베팅 인사이트: LeBron 복귀 시 라인업 강화됨
```

---

## 💰 비용 분석 (업데이트)

### Layer 1: Real-time Alert (X Search)
```
xAI Native API:
- 하루 20-30개 부상/라인업 트윗
- 1 트윗 = 1 X Search call
- 월 600-900 calls
- 비용: ~$0.50/월 (X Search는 저렴)
```

### Layer 2: Reddit Analysis
```
OpenRouter (Qwen 2.5 VL 72B):
- 하루 10-15 경기 (NBA 시즌)
- 1 경기 = 1 Reddit 분석 (2000 tokens output)
- Input: ~1500 tokens (댓글)
- Output: ~2000 tokens (분석)
- 월 300-450 경기
- 비용:
  Input:  300 * 1500 * $0.07/1M = $0.03
  Output: 300 * 2000 * $0.26/1M = $0.16
  합계: ~$0.19/월
```

### Layer 3: Graph Storage
```
Neo4j: 무료 (Self-hosted)
```

### 총 비용
```
Layer 1 (X Search):        $0.50/월
Layer 2 (Reddit Analysis): $0.19/월
Layer 3 (Graph):           $0.00/월
────────────────────────────────
합계:                      $0.69/월

기존 Economy 통합 시:
NBA:     $0.69/월
Economy: $0.44/월
────────────────────────────────
총합:    $1.13/월 (여전히 매우 저렴!)
```

---

## 🚀 구현 순서

### Phase 1: Layer 1 구현 (Real-time Alert)
**예상 소요**: 2-3시간

```bash
# 1. xAI API Key 발급
# https://console.x.ai/

# 2. Pusher 계정 생성 (무료)
# https://dashboard.pusher.com/

# 3. Next.js API Route 생성
touch app/api/alerts/injury/route.ts

# 4. n8n 워크플로우 생성
# - Webhook Trigger (15분마다)
# - X Search Function (xAI Native)
# - HTTP Request (Next.js API)
# - Neo4j 저장

# 5. 테스트
# → @ShamsCharania 트윗 모니터링
# → 웹 알림 확인
```

### Phase 2: Layer 2 구현 (Reddit Analysis)
**예상 소요**: 4-5시간

```bash
# 1. Reddit API 앱 생성
# https://www.reddit.com/prefs/apps

# 2. Python 스크립트 작성
touch scripts/reddit_post_game_collector.py

# 3. n8n Cron 워크플로우 추가
# - Cron Trigger (새벽 1-4시)
# - Python Script Execute
# - Slack/Telegram 완료 알림

# 4. 테스트
# → 어제 경기 수동 수집
# → Neo4j 데이터 확인
```

### Phase 3: Layer 3 구현 (Graph Queries)
**예상 소요**: 2-3시간

```bash
# 1. Cypher 쿼리 작성
touch cypher/player_evaluation_timeline.cypher
touch cypher/coaching_analysis_trends.cypher
touch cypher/injury_impact_analysis.cypher

# 2. Next.js API Route 추가
touch app/api/graph/player-timeline/route.ts
touch app/api/graph/coaching-trends/route.ts

# 3. 대시보드 컴포넌트 추가
touch components/PlayerEvaluationChart.tsx
touch components/CoachingTrendsChart.tsx

# 4. 테스트
# → Recharts로 시계열 시각화
# → 선수/코치 평가 변화 확인
```

---

## 📊 예상 효과

### "우리의 모든 우려를 불식"하는 이유

#### ✅ 실시간성
```
기존: 공식 트윗 → 수동 확인 → 늦은 반응
새로: X Search → 즉시 웹 알림 → 1-2초 이내 인지
```

#### ✅ 깊이
```
기존: 숫자 데이터 (득점, 리바운드)
새로: 정성 데이터 (팬 평가, 코칭 분석, 팀 분위기)
      "AD limping in Q4" ← 부상 위험 조기 감지
      "Coach Ham rotations terrible" ← 전술 문제 파악
```

#### ✅ 맥락
```
기존: 경기 결과만 저장
새로: 시간순 평가 변화 추적
      → 선수 컨디션 추세
      → 코치 전술 효과
      → 팀 케미스트리 변화
```

#### ✅ 신뢰성
```
기존: AI 추론 (환각 가능성)
새로: 팬들의 실제 평가 (500+ upvotes = 검증됨)
```

---

## 🎯 최종 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                    Twitter/X Stream                      │
│          (@ShamsCharania, @wojespn, etc.)               │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              Layer 1: Real-time Alert                   │
│                  (X Search - xAI Native)                │
│                                                          │
│  X Search → Injury/Lineup → 즉시 웹 알림 (1-2초)         │
│  (분석 없음, 속도 우선, 정규식 파싱)                      │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              Layer 2: Deep Analysis                     │
│              (Reddit - OpenRouter Qwen 72B)             │
│                                                          │
│  경기 후 1시간 → Reddit Post-Game Thread                │
│  → 팬 평가 (선수/코치/전술/분위기)                        │
│  → LLM 분석 → JSON 구조화                               │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              Layer 3: Memory                            │
│              (Neo4j Graph)                              │
│                                                          │
│  시간순 저장 → 맥락 보존 → 패턴 발견                      │
│  - 선수 평가 변화                                        │
│  - 코치 전술 효과                                        │
│  - 부상 영향 분석                                        │
└─────────────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              Dashboard (Next.js)                        │
│                                                          │
│  - Real-time Alerts (Pusher 토스트)                     │
│  - Player Timeline (Recharts)                           │
│  - Coaching Trends (시계열 차트)                         │
│  - Reddit Insights (카드 뷰)                            │
└─────────────────────────────────────────────────────────┘
```

---

**작성자**: Claude Code
**검토**: User (KICK 전략 제시자)
**버전**: v1.0
**다음 단계**: Phase 1 구현 (Real-time Alert)
