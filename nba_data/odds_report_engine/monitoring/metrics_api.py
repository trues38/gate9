#!/usr/bin/env python3
"""
G9 Monitoring API - Prometheus Metrics Exporter
API 500회 관리 + NBA/경제 수집 상태 실시간 추적 + 상관 분석
"""

from flask import Flask, Response, request
from prometheus_client import Counter, Gauge, Histogram, generate_latest, REGISTRY
from neo4j import GraphDatabase
import time
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# ============================================================
# Prometheus Metrics 정의
# ============================================================

# API 호출 카운터 (월 500회 제한 관리)
API_CALLS = Counter(
    "api_calls_total",
    "Total external API calls",
    ["source"]  # odds_api, twitter_api
)

# Odds API 스냅샷 카운터
ODDS_SNAPSHOTS = Counter(
    "odds_snapshots_total",
    "Odds snapshots collected",
    ["game_id"]
)

# Twitter 이벤트 카운터
TWITTER_EVENTS = Counter(
    "twitter_events_total",
    "Twitter events collected",
    ["domain"]  # nba, economy
)

# NBA 수집 상태
NBA_GAMES_COLLECTED = Gauge(
    "nba_games_collected",
    "NBA games collected today"
)

# 경제 이벤트 수집 상태
ECON_EVENTS_COLLECTED = Gauge(
    "econ_events_collected",
    "Economic events collected today"
)

# Neo4j 노드 수
NEO4J_NODES = Gauge(
    "neo4j_node_count",
    "Total Neo4j nodes",
    ["database"]  # nba, economy
)

# 크론/작업 실행 타임스탬프
JOB_HEARTBEAT = Gauge(
    "job_last_run_timestamp",
    "Last job run timestamp (unix)",
    ["job"]  # nba_collector, economic_collector, report_generator
)

# 리포트 생성 시간
REPORT_GENERATION_TIME = Histogram(
    "report_generation_seconds",
    "Time to generate reports",
    ["report_type"]  # ultimate, regime, matchup
)

# ============================================================
# 고급 메트릭 (상관 분석용)
# ============================================================

# Odds 변동 추적
ODDS_MOVEMENT = Gauge(
    "odds_movement",
    "Odds movement from opening line",
    ["game_id", "market", "team"]
)

# Twitter 감성 분석
TWITTER_SENTIMENT = Gauge(
    "twitter_sentiment_score",
    "Twitter sentiment score (-1 to 1)",
    ["domain", "team"]
)

# Twitter 이벤트 카테고리
TWITTER_EVENT_CATEGORY = Counter(
    "twitter_event_category_total",
    "Twitter events by category",
    ["domain", "category"]
)

# NBA 이벤트 임팩트
NBA_EVENT_IMPACT = Gauge(
    "nba_event_impact",
    "Estimated impact of NBA event (-10 to 10)",
    ["game_id", "event_type", "team"]
)

# Odds vs Twitter 상관계수
ODDS_TWITTER_CORRELATION = Gauge(
    "odds_twitter_correlation",
    "Correlation between odds movement and Twitter sentiment",
    ["game_id"]
)

# 경기별 Twitter 언급
GAME_TWITTER_MENTIONS = Gauge(
    "game_twitter_mentions",
    "Twitter mentions for game",
    ["game_id", "team"]
)

# ============================================================
# Neo4j 연결
# ============================================================

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "nba_vultr_2025")

def get_neo4j_stats():
    """VPS Neo4j 노드 수 조회"""
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=("neo4j", NEO4J_PASSWORD))
        with driver.session() as session:
            # 전체 노드 수
            result = session.run("MATCH (n) RETURN count(n) as total")
            total = result.single()["total"]

            # NBA 노드 수 (Game, Team, Player 등)
            result = session.run("""
                MATCH (n)
                WHERE n:Game OR n:Team OR n:Player OR n:TeamState OR n:PlayerState
                RETURN count(n) as nba_total
            """)
            nba_total = result.single()["nba_total"]

            # 경제 노드 수 (Event, Regime 등)
            result = session.run("""
                MATCH (n)
                WHERE n:EconomicEvent OR n:Regime
                RETURN count(n) as econ_total
            """)
            econ_total = result.single()["econ_total"]

            driver.close()
            return {
                "total": total,
                "nba": nba_total,
                "economy": econ_total
            }
    except Exception as e:
        print(f"Neo4j 연결 실패: {e}")
        return {"total": 0, "nba": 0, "economy": 0}

# ============================================================
# API 엔드포인트
# ============================================================

@app.route("/metrics")
def metrics():
    """Prometheus가 스크랩할 메트릭 엔드포인트"""
    # Neo4j 실시간 노드 수 업데이트
    stats = get_neo4j_stats()
    NEO4J_NODES.labels(database="nba").set(stats["nba"])
    NEO4J_NODES.labels(database="economy").set(stats["economy"])

    return Response(generate_latest(REGISTRY), mimetype="text/plain")

@app.route("/health")
def health():
    """헬스 체크"""
    return {"status": "ok", "timestamp": time.time()}

@app.route("/api/record_api_call/<source>")
def record_api_call(source):
    """API 호출 기록 (odds_api, twitter_api)"""
    API_CALLS.labels(source=source).inc()
    return {"status": "recorded", "source": source}

@app.route("/api/record_odds_snapshot/<game_id>")
def record_odds_snapshot(game_id):
    """Odds 스냅샷 기록"""
    ODDS_SNAPSHOTS.labels(game_id=game_id).inc()
    return {"status": "recorded", "game_id": game_id}

@app.route("/api/record_twitter_event/<domain>")
def record_twitter_event(domain):
    """Twitter 이벤트 기록 (nba, economy)"""
    TWITTER_EVENTS.labels(domain=domain).inc()
    return {"status": "recorded", "domain": domain}

@app.route("/api/record_job_heartbeat/<job>")
def record_job_heartbeat(job):
    """크론/작업 실행 기록 (nba_collector, economic_collector)"""
    JOB_HEARTBEAT.labels(job=job).set(time.time())
    return {"status": "recorded", "job": job, "timestamp": time.time()}

@app.route("/api/set_nba_games/<int:count>")
def set_nba_games(count):
    """NBA 경기 수 기록"""
    NBA_GAMES_COLLECTED.set(count)
    return {"status": "recorded", "count": count}

@app.route("/api/set_econ_events/<int:count>")
def set_econ_events(count):
    """경제 이벤트 수 기록"""
    ECON_EVENTS_COLLECTED.set(count)
    return {"status": "recorded", "count": count}

# ============================================================
# 고급 메트릭 API (상관 분석용)
# ============================================================

@app.route("/api/record_odds_movement")
def record_odds_movement_api():
    """Odds 변동 기록 ?game_id=X&market=h2h&team=LAL&movement=0.15"""
    game_id = request.args.get('game_id')
    market = request.args.get('market', 'h2h')
    team = request.args.get('team')
    movement = float(request.args.get('movement', 0))

    ODDS_MOVEMENT.labels(game_id=game_id, market=market, team=team).set(movement)
    return {"status": "recorded", "game_id": game_id, "movement": movement}

@app.route("/api/record_twitter_sentiment")
def record_twitter_sentiment_api():
    """Twitter 감성 기록 ?domain=nba&team=LAL&score=0.7"""
    domain = request.args.get('domain', 'nba')
    team = request.args.get('team')
    score = float(request.args.get('score', 0))

    TWITTER_SENTIMENT.labels(domain=domain, team=team).set(score)
    return {"status": "recorded", "domain": domain, "team": team, "score": score}

@app.route("/api/record_twitter_category")
def record_twitter_category_api():
    """Twitter 카테고리 기록 ?domain=nba&category=injury"""
    domain = request.args.get('domain', 'nba')
    category = request.args.get('category')

    TWITTER_EVENT_CATEGORY.labels(domain=domain, category=category).inc()
    return {"status": "recorded", "domain": domain, "category": category}

@app.route("/api/record_nba_event_impact")
def record_nba_event_impact_api():
    """NBA 이벤트 임팩트 ?game_id=X&event_type=injury&team=LAL&impact=-8.5"""
    game_id = request.args.get('game_id')
    event_type = request.args.get('event_type')
    team = request.args.get('team')
    impact = float(request.args.get('impact', 0))

    NBA_EVENT_IMPACT.labels(game_id=game_id, event_type=event_type, team=team).set(impact)
    return {"status": "recorded", "game_id": game_id, "impact": impact}

@app.route("/api/record_correlation")
def record_correlation_api():
    """Odds vs Twitter 상관계수 ?game_id=X&correlation=0.85"""
    game_id = request.args.get('game_id')
    correlation = float(request.args.get('correlation', 0))

    ODDS_TWITTER_CORRELATION.labels(game_id=game_id).set(correlation)
    return {"status": "recorded", "game_id": game_id, "correlation": correlation}

@app.route("/api/record_game_mentions")
def record_game_mentions_api():
    """Twitter 언급 횟수 ?game_id=X&team=LAL&count=1523"""
    game_id = request.args.get('game_id')
    team = request.args.get('team')
    count = int(request.args.get('count', 0))

    GAME_TWITTER_MENTIONS.labels(game_id=game_id, team=team).set(count)
    return {"status": "recorded", "game_id": game_id, "team": team, "count": count}

# ============================================================
# 사용 예시 (다른 파이프라인에서 호출)
# ============================================================

def example_usage():
    """
    다른 Python 파이프라인에서 이렇게 사용:

    import requests

    # API 호출 기록
    requests.get("http://localhost:9101/api/record_api_call/odds_api")

    # Odds 스냅샷 기록
    requests.get("http://localhost:9101/api/record_odds_snapshot/401810214")

    # Twitter 이벤트 기록
    requests.get("http://localhost:9101/api/record_twitter_event/nba")

    # 크론 실행 기록
    requests.get("http://localhost:9101/api/record_job_heartbeat/nba_collector")

    # NBA 경기 수 업데이트
    requests.get("http://localhost:9101/api/set_nba_games/10")
    """
    pass

if __name__ == "__main__":
    print("🚀 G9 Monitoring API 시작")
    print("=" * 70)
    print("")
    print("Prometheus 메트릭: http://localhost:9101/metrics")
    print("헬스 체크: http://localhost:9101/health")
    print("")
    print("API 엔드포인트:")
    print("  - /api/record_api_call/<source>")
    print("  - /api/record_odds_snapshot/<game_id>")
    print("  - /api/record_twitter_event/<domain>")
    print("  - /api/record_job_heartbeat/<job>")
    print("  - /api/set_nba_games/<count>")
    print("  - /api/set_econ_events/<count>")
    print("")

    # Flask 실행
    app.run(host="0.0.0.0", port=9101, debug=False)
