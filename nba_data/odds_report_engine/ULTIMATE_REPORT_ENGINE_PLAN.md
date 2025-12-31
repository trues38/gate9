# 🏀 G9 Ultimate NBA Report Engine - 최상급 업그레이드 계획

**날짜**: 2025-12-29
**목표**: Production-Ready 프리미엄 베팅 리포트 엔진 완성
**현재 상태**: 85% 완료 → 100% 완성 + 자동화

---

## 📊 현재 시스템 분석

### ✅ 이미 완료된 것 (85%)

| 컴포넌트 | 상태 | 세부 사항 |
|----------|------|-----------|
| **Graph RAG** | ✅ 100% | Neo4j (15,433 노드), Regime Analysis, H2H |
| **Realtime Odds** | ✅ 100% | The Odds API (452/500 calls), Spread/ML |
| **Realtime Injuries** | ✅ 100% | ESPN API, OUT/Day-to-Day tracking |
| **AI 5-Person Council** | ✅ 100% | DeepSeek, Qwen, Grok, Gemini, GPT + 3 fallbacks |
| **3-Tier System** | ✅ 100% | $1 (Odds) / $2 (Graph RAG) / $3 (AI Council) |
| **Sample Reports** | ✅ 100% | Full/Premium reports generated |
| **VPS SSH Tunnel** | ✅ 100% | Neo4j SSH connection stable |
| **Monitoring** | ✅ 100% | Prometheus + Grafana + Alertmanager |

### ⚠️ 개선 필요 (15%)

| 컴포넌트 | 현재 | 목표 | 우선순위 |
|----------|------|------|----------|
| **Referee Stats** | 70% | 100% | 🔥 High |
| **Lineup Sources** | 50% | 100% | 🔥 High |
| **VPS Automation** | 0% | 100% | 🔥 High |
| **Real Neo4j Data** | Samples | 15,433 nodes | ⚡ Medium |
| **Web UI** | 0% | Basic MVP | 💡 Low (Next phase) |

---

## 🎯 업그레이드 목표

### **Phase 1: 데이터 완성** (오늘, 4시간)
1. Referee Stats 파싱 수정 (70% → 100%)
2. Lineup Sources 구현 (50% → 100%)
3. VPS Neo4j 실제 데이터 연결

### **Phase 2: 자동화** (내일, 6시간)
4. N8N Workflow 구축 (일일 자동 생성)
5. Monitoring 통합 (Grafana에 Report 메트릭)
6. Alertmanager 알림 (Report 생성 실패 시)

### **Phase 3: 웹 개발** (다음 주)
7. Next.js 웹 UI/UX
8. 결제 시스템 (Stripe)
9. 운영/판매 시작

---

## 🔥 Phase 1: 데이터 완성 (오늘 4시간)

### 1️⃣ Referee Stats 수정 (1시간)

**문제**: Basketball Reference 파싱 오류
**해결**: FBref 또는 NBA Stats API로 전환

**Before**:
```python
# basketball_reference_scraper.py (실패)
url = "https://www.basketball-reference.com/referees/"
# BeautifulSoup 파싱 오류
```

**After**:
```python
# referee_stats_collector.py (신규)
from nba_api.stats.endpoints import LeagueGameLog

def get_referee_stats(game_id):
    """
    NBA Stats API에서 심판 정보 조회
    또는 경기 당일 @OfficialNBARefs Twitter 확인
    """
    # Option 1: NBA Stats API
    game_log = LeagueGameLog(game_id=game_id).get_data_frames()[0]
    referee = game_log['REFEREE'].iloc[0]

    # Option 2: Twitter API (@OfficialNBARefs)
    # "Tonight's officials: Scott Foster (TOR vs GSW)"

    return {
        "name": referee,
        "games_this_season": 45,
        "avg_fouls_called": 21.3,
        "strictness_index": 0.72  # 0-1 scale
    }
```

**구현**:
```bash
cd /Users/js/g9/nba_data/odds_report_engine
# 새 파일 생성
touch referee_stats_collector.py
# realtime_data_collector.py에 통합
```

---

### 2️⃣ Lineup Sources 구현 (2시간)

**문제**: 예상 라인업 미구현
**해결**: NBA Stats API + Twitter 조합

**데이터 소스 3단계**:

| 우선순위 | 소스 | 정확도 | 시간 |
|---------|------|--------|------|
| 1️⃣ **NBA Stats API** | `LeagueGameLog` | 90% | 경기 1시간 전 |
| 2️⃣ **Twitter Official** | @Raptors, @warriors | 100% | 경기 30분 전 |
| 3️⃣ **Rotowire** | Scraping | 85% | 경기 2시간 전 |

**구현**:
```python
# lineup_collector.py (신규)
from nba_api.stats.endpoints import CommonTeamRoster
import tweepy

class LineupCollector:
    def __init__(self):
        self.twitter_api = tweepy.Client(bearer_token=TWITTER_TOKEN)

    def get_predicted_lineup(self, team_abbr, game_date):
        """
        3단계 Fallback으로 예상 라인업 조회
        """
        # Step 1: NBA Stats API (최근 스타팅 5)
        roster = CommonTeamRoster(team_id=self.get_team_id(team_abbr))
        recent_starters = roster.get_data_frames()[0].head(5)

        # Step 2: Twitter 확인 (경기 30분 전)
        tweets = self.twitter_api.search_recent_tweets(
            query=f"from:@{team_abbr} lineup",
            max_results=5
        )
        if tweets.data:
            # "Tonight's starters: Curry, Wiggins, Green..."
            return self.parse_lineup_tweet(tweets.data[0].text)

        # Step 3: Fallback (예상 라인업)
        return {
            "starters": recent_starters['PLAYER'].tolist(),
            "confidence": "MEDIUM",
            "source": "NBA Stats API (최근 5경기 평균)"
        }
```

**realtime_data_collector.py 통합**:
```python
# 기존 코드에 추가
def collect_all_data(self, home_team, away_team):
    data = {
        'odds': self.get_odds(...),
        'injuries': self.get_injuries(...),
        'referees': self.get_referees(...),  # 새로 추가
        'lineups': self.get_lineups(...)     # 새로 추가
    }
    return data
```

---

### 3️⃣ VPS Neo4j 실제 데이터 연결 (1시간)

**현재**: 로컬 샘플 데이터 (37 nodes)
**목표**: VPS Neo4j (15,433 nodes) 연결

**SSH Tunnel 활용**:
```bash
# 이미 구축된 SSH Tunnel 사용
# VPS: 141.164.35.214 (Neo4j 7687)
# Tunnel: bolt://172.17.0.1:7687

# graph_odds_report_generator.py 수정
NEO4J_URI = "bolt://172.17.0.1:7687"  # VPS via SSH tunnel
NEO4J_PASSWORD = "nba_vultr_2025"
```

**테스트**:
```bash
python3 << 'EOF'
from neo4j import GraphDatabase

driver = GraphDatabase.driver(
    "bolt://172.17.0.1:7687",
    auth=("neo4j", "nba_vultr_2025")
)

with driver.session() as session:
    result = session.run("MATCH (n) RETURN count(n) as total")
    print(f"Total nodes: {result.single()['total']}")  # 15,433
EOF
```

---

## ⚡ Phase 2: 자동화 (내일 6시간)

### 4️⃣ N8N Workflow 구축 (3시간)

**목표**: 매일 오전 9시 자동으로 모든 경기 리포트 생성

**Workflow 단계**:
```
09:00 - Trigger (Daily)
   ↓
09:05 - Fetch Today's Games (ESPN API)
   ↓
09:10 - For Each Game:
   ├─ Collect Realtime Data (Odds, Injuries, Referees, Lineups)
   ├─ Query Graph RAG (Neo4j)
   └─ Generate Reports (Tier 1, 2, 3)
   ↓
10:00 - Upload to S3 / Send Email
   ↓
10:05 - Update Metrics API
```

**N8N JSON**:
```json
{
  "name": "G9 Daily NBA Reports",
  "nodes": [
    {
      "name": "Daily Trigger",
      "type": "n8n-nodes-base.cron",
      "parameters": {
        "triggerTimes": {
          "item": [{"hour": 9, "minute": 0}]
        }
      }
    },
    {
      "name": "Fetch Today's Games",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "url": "http://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
      }
    },
    {
      "name": "Generate Reports",
      "type": "n8n-nodes-base.executeCommand",
      "parameters": {
        "command": "cd /opt/g9/nba_data/odds_report_engine && ./generate_all_reports.sh"
      }
    },
    {
      "name": "Record Metrics",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "url": "http://g9-metrics-api:9101/api/record_job_heartbeat/report_generator"
      }
    }
  ]
}
```

**스크립트 작성**:
```bash
# generate_all_reports.sh (신규)
#!/bin/bash

echo "🏀 G9 Daily Report Generation"
echo "==================================="

# 1. Fetch today's games
GAMES=$(curl -s "http://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard" | \
  jq -r '.events[] | "\(.competitions[0].competitors[0].team.abbreviation) \(.competitions[0].competitors[1].team.abbreviation)"')

# 2. Generate reports for each game
while read -r game; do
  HOME=$(echo $game | cut -d' ' -f1)
  AWAY=$(echo $game | cut -d' ' -f2)

  echo "Generating report: $AWAY @ $HOME"

  # Tier 1: Odds Only ($1)
  python3 generate_report.py $HOME $AWAY --tier 1

  # Tier 2: Graph RAG + Odds ($2)
  python3 generate_report.py $HOME $AWAY --tier 2

  # Tier 3: AI Council ($3)
  python3 generate_report.py $HOME $AWAY --tier 3

  sleep 5  # Rate limit
done <<< "$GAMES"

echo "✅ All reports generated!"
```

---

### 5️⃣ Monitoring 통합 (2시간)

**Metrics API 확장**:
```python
# monitoring/metrics_api.py에 추가

REPORTS_GENERATED = Counter(
    "reports_generated_total",
    "Total reports generated",
    ["tier"]  # tier1, tier2, tier3
)

REPORT_GENERATION_TIME = Histogram(
    "report_generation_seconds",
    "Time to generate report",
    ["tier"]
)

AI_COUNCIL_CONSENSUS = Gauge(
    "ai_council_consensus_score",
    "AI Council consensus score (0-5)",
    ["game_id"]
)

@app.route("/api/record_report/<tier>")
def record_report(tier):
    REPORTS_GENERATED.labels(tier=tier).inc()
    return {"status": "recorded", "tier": tier}
```

**Grafana Dashboard**:
- Panel 1: 일일 리포트 생성 수 (Tier별)
- Panel 2: AI Council Consensus 평균 (2/5, 3/5, 4/5, 5/5)
- Panel 3: Report Generation Time (평균 45초)
- Panel 4: 실패한 리포트 (0개 목표)

---

### 6️⃣ Alertmanager 알림 (1시간)

**알림 규칙**:
```yaml
# monitoring/alerts.yml에 추가

- alert: ReportGenerationFailed
  expr: increase(reports_generated_total[10m]) == 0
  for: 10m
  labels:
    severity: critical
  annotations:
    summary: "리포트 생성 실패"
    description: "10분간 리포트 생성 없음"

- alert: AICouncilLowConsensus
  expr: avg(ai_council_consensus_score) < 2.5
  for: 1h
  labels:
    severity: warning
  annotations:
    summary: "AI Council 합의 점수 낮음"
    description: "평균 Consensus < 2.5 (불확실성 높음)"

- alert: OddsAPILimitApproaching
  expr: api_calls_total{source="odds_api"} > 450
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "Odds API 한계 도달"
    description: "450/500 calls 사용 (90%)"
```

---

## 💡 Phase 3: 웹 개발 (다음 주)

### 7️⃣ Next.js 웹 UI/UX (3일)

**기능**:
- 오늘 경기 목록
- 리포트 미리보기 (Free)
- 결제 후 Full Report 다운로드
- 과거 리포트 아카이브

**기술 스택**:
```
Frontend: Next.js 14 + TailwindCSS
Backend: Next.js API Routes
DB: Supabase (사용자 관리)
Storage: S3 (리포트 PDF)
Payment: Stripe
```

---

### 8️⃣ 결제 시스템 (2일)

**Tier별 가격**:
| Tier | 가격 | 내용 |
|------|------|------|
| Free | $0 | Odds 요약 |
| Standard | $2 | Tier 2 (Graph RAG) |
| Premium | $3 | Tier 3 (AI Council) |
| Monthly | $50/월 | 무제한 리포트 |

**Stripe 통합**:
```typescript
// pages/api/checkout.ts
import Stripe from 'stripe';

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!);

export default async function handler(req, res) {
  const { tier, game_id } = req.body;

  const session = await stripe.checkout.sessions.create({
    payment_method_types: ['card'],
    line_items: [{
      price_data: {
        currency: 'usd',
        product_data: {
          name: `G9 NBA Report - ${tier}`,
        },
        unit_amount: tier === 'standard' ? 200 : 300,  // cents
      },
      quantity: 1,
    }],
    mode: 'payment',
    success_url: `${req.headers.origin}/report/${game_id}?session_id={CHECKOUT_SESSION_ID}`,
    cancel_url: `${req.headers.origin}/`,
  });

  res.status(200).json({ url: session.url });
}
```

---

### 9️⃣ 운영/판매 시작 (1일)

**런칭 체크리스트**:
- [ ] 7일간 실전 테스트 (모든 리포트 생성)
- [ ] ROI 추적 (Consensus vs 실제 결과)
- [ ] 웹사이트 배포 (Vercel)
- [ ] Stripe 프로덕션 모드
- [ ] 마케팅 자료 (샘플 리포트, 비디오)
- [ ] Twitter/Discord 홍보
- [ ] 첫 고객 확보!

---

## 📋 실행 계획 (타임라인)

### **Day 1 (오늘)**: 데이터 완성
| 시간 | 작업 | 담당 |
|------|------|------|
| 10:00-11:00 | Referee Stats 수정 | Claude |
| 11:00-13:00 | Lineup Sources 구현 | Claude |
| 13:00-14:00 | VPS Neo4j 연결 테스트 | Claude |
| 14:00-15:00 | End-to-End 테스트 | Claude |

**목표**: Referee 100%, Lineup 100%, 실제 Neo4j 연결

---

### **Day 2 (내일)**: 자동화
| 시간 | 작업 | 담당 |
|------|------|------|
| 09:00-12:00 | N8N Workflow 구축 | Gemini (백업) |
| 12:00-14:00 | Monitoring 통합 | Claude |
| 14:00-15:00 | Alertmanager 알림 | Claude |
| 15:00-16:00 | 자동화 테스트 | 모두 |

**목표**: 매일 09:00 자동 리포트 생성

---

### **Week 1 (다음 주)**: 웹 개발
| 날짜 | 작업 |
|------|------|
| Day 3-5 | Next.js UI/UX 개발 |
| Day 6-7 | Stripe 결제 통합 |

**목표**: 판매 가능한 웹사이트

---

## 🎯 성공 기준

### **Phase 1 완료 기준**:
- ✅ Referee Stats 100% 정확도
- ✅ Lineup Sources 3단계 Fallback 작동
- ✅ VPS Neo4j 15,433 노드 연결
- ✅ End-to-End 리포트 생성 성공

### **Phase 2 완료 기준**:
- ✅ N8N Workflow 매일 09:00 자동 실행
- ✅ Grafana에 Report 메트릭 표시
- ✅ Alertmanager 알림 테스트 성공
- ✅ 7일 연속 자동 생성 무사고

### **Phase 3 완료 기준**:
- ✅ 웹사이트 Vercel 배포
- ✅ Stripe 결제 테스트 성공
- ✅ 첫 유료 고객 획득
- ✅ 월 $1,000+ 매출 달성

---

## 💰 비용 vs 수익 예상

### **Phase 1-2 완료 후**:
- **비용**: $0.15/리포트 × 10경기/일 = $1.50/일
- **판매**: $3/리포트 × 10경기 × 10% 판매율 = $30/일
- **월 수익**: $30 × 30 = $900/월
- **순이익**: $900 - $45 = $855/월 (95% 마진)

### **Phase 3 완료 후** (웹 론칭):
- **판매율**: 10% → 30% (웹 UI 효과)
- **월 수익**: $30 × 30 × 3 = $2,700/월
- **순이익**: $2,700 - $45 = $2,655/월

### **6개월 후** (구독 고객 확보):
- **구독**: 50명 × $50/월 = $2,500/월
- **개별 판매**: $900/월
- **총 수익**: $3,400/월
- **순이익**: $3,355/월 ($40K/년)

---

## 🚀 즉시 시작 가능한 작업

### **Claude (메인 책임자)**:
1. `referee_stats_collector.py` 작성 (NBA Stats API)
2. `lineup_collector.py` 작성 (NBA API + Twitter)
3. `realtime_data_collector.py` 통합
4. VPS Neo4j 연결 테스트

### **Gemini (백업)**:
1. N8N Workflow JSON 작성
2. `generate_all_reports.sh` 스크립트
3. Monitoring 메트릭 추가
4. 문서 업데이트

---

## 📁 파일 구조 (최종)

```
/Users/js/g9/nba_data/odds_report_engine/
├── graph_odds_report_generator.py       # 기존 (Graph RAG)
├── realtime_data_collector.py           # 기존 (Odds, Injuries)
├── ai_betting_council.py                # 기존 (5-Person Council)
│
├── referee_stats_collector.py           # 🆕 신규 (Phase 1)
├── lineup_collector.py                  # 🆕 신규 (Phase 1)
├── generate_all_reports.sh              # 🆕 신규 (Phase 2)
│
├── monitoring/
│   ├── metrics_api.py                   # 수정 (Report 메트릭 추가)
│   ├── alerts.yml                       # 수정 (Report 알림 추가)
│   └── grafana_report_dashboard.json    # 🆕 신규 (Phase 2)
│
├── n8n/
│   └── nba_daily_reports_workflow.json  # 🆕 신규 (Phase 2)
│
└── ULTIMATE_REPORT_ENGINE_PLAN.md       # 🆕 신규 (이 파일)
```

---

## 🎉 Summary

**현재**: 85% 완료 (훌륭한 기반)
**목표**: 100% 완성 + 자동화 + 웹 판매

**Timeline**:
- **오늘** (4시간): 데이터 완성 (Referee, Lineup, Neo4j)
- **내일** (6시간): 자동화 (N8N, Monitoring, Alerts)
- **다음 주** (5일): 웹 개발 + 결제 + 런칭

**예상 수익**:
- **1개월 후**: $900/월
- **6개월 후**: $3,400/월 ($40K/년)

**다음 액션**: Referee Stats 수정부터 시작! 🚀

---

**Built with**: Graph RAG + Realtime Data + AI Council + Monitoring + Automation
**© 2025 G9 Regime Zero - World's First AI Council-Based Betting Intelligence**
