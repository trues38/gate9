#!/usr/bin/env python3
"""
G9 고급 메트릭 API - 상관 분석용
NBA 이벤트 vs Odds 변동 vs Twitter 감성 추적
"""

from prometheus_client import Gauge, Histogram, Counter
from datetime import datetime
import time

# ============================================================
# 고급 메트릭 정의
# ============================================================

# Odds 변동 추적 (게임별)
ODDS_MOVEMENT = Gauge(
    "odds_movement",
    "Odds movement from opening line",
    ["game_id", "market", "team"]  # h2h, spread, totals
)

# Twitter 감성 분석
TWITTER_SENTIMENT = Gauge(
    "twitter_sentiment_score",
    "Twitter sentiment score (-1 to 1)",
    ["domain", "team"]  # nba, economy
)

# Twitter 이벤트 카테고리별
TWITTER_EVENT_CATEGORY = Counter(
    "twitter_event_category_total",
    "Twitter events by category",
    ["domain", "category"]  # injury, lineup, news, rumor
)

# NBA 이벤트 임팩트
NBA_EVENT_IMPACT = Gauge(
    "nba_event_impact",
    "Estimated impact of NBA event on game (-10 to 10)",
    ["game_id", "event_type", "team"]  # injury, lineup_change, hot_hand
)

# Odds vs Twitter 상관계수
ODDS_TWITTER_CORRELATION = Gauge(
    "odds_twitter_correlation",
    "Correlation between odds movement and Twitter sentiment",
    ["game_id"]
)

# 경기별 Twitter 언급 횟수
GAME_TWITTER_MENTIONS = Gauge(
    "game_twitter_mentions",
    "Number of Twitter mentions for game",
    ["game_id", "team"]
)

# 배당 스냅샷 시간별 변동
ODDS_SNAPSHOT_TIME = Histogram(
    "odds_snapshot_interval_seconds",
    "Time between odds snapshots",
    ["game_id"]
)

# 경제 이벤트 임팩트 on NBA
ECONOMIC_NBA_IMPACT = Gauge(
    "economic_nba_impact",
    "Economic event impact on NBA betting",
    ["event_type"]  # fed_rate, inflation, market_crash
)

# ============================================================
# 사용 예시
# ============================================================

def record_odds_movement(game_id: str, market: str, team: str, movement: float):
    """
    Odds 변동 기록

    Args:
        game_id: 게임 ID
        market: h2h, spread, totals
        team: 팀명
        movement: 변동폭 (+는 상승, -는 하락)
    """
    ODDS_MOVEMENT.labels(
        game_id=game_id,
        market=market,
        team=team
    ).set(movement)

def record_twitter_sentiment(domain: str, team: str, score: float):
    """
    Twitter 감성 점수 기록

    Args:
        domain: nba, economy
        team: 팀명
        score: -1 (매우 부정) ~ 1 (매우 긍정)
    """
    TWITTER_SENTIMENT.labels(
        domain=domain,
        team=team
    ).set(score)

def record_twitter_event(domain: str, category: str):
    """
    Twitter 이벤트 카테고리 기록

    Args:
        domain: nba, economy
        category: injury, lineup, news, rumor
    """
    TWITTER_EVENT_CATEGORY.labels(
        domain=domain,
        category=category
    ).inc()

def record_nba_event_impact(game_id: str, event_type: str, team: str, impact: float):
    """
    NBA 이벤트 임팩트 기록

    Args:
        game_id: 게임 ID
        event_type: injury, lineup_change, hot_hand
        team: 팀명
        impact: -10 (매우 부정) ~ 10 (매우 긍정)
    """
    NBA_EVENT_IMPACT.labels(
        game_id=game_id,
        event_type=event_type,
        team=team
    ).set(impact)

def record_odds_twitter_correlation(game_id: str, correlation: float):
    """
    Odds vs Twitter 상관계수 기록

    Args:
        game_id: 게임 ID
        correlation: -1 ~ 1
    """
    ODDS_TWITTER_CORRELATION.labels(game_id=game_id).set(correlation)

def record_game_twitter_mentions(game_id: str, team: str, count: int):
    """
    경기별 Twitter 언급 횟수

    Args:
        game_id: 게임 ID
        team: 팀명
        count: 언급 횟수
    """
    GAME_TWITTER_MENTIONS.labels(
        game_id=game_id,
        team=team
    ).set(count)

def record_odds_snapshot_interval(game_id: str, interval: float):
    """
    배당 스냅샷 시간 간격

    Args:
        game_id: 게임 ID
        interval: 초 단위
    """
    ODDS_SNAPSHOT_TIME.labels(game_id=game_id).observe(interval)

def record_economic_nba_impact(event_type: str, impact: float):
    """
    경제 이벤트의 NBA 베팅 임팩트

    Args:
        event_type: fed_rate, inflation, market_crash
        impact: -10 ~ 10
    """
    ECONOMIC_NBA_IMPACT.labels(event_type=event_type).set(impact)

# ============================================================
# 실전 예시
# ============================================================

def example_correlation_analysis():
    """상관 분석 실전 예시"""

    # 1. Odds 변동 기록
    record_odds_movement(
        game_id="401810214",
        market="h2h",
        team="LAL",
        movement=+0.15  # +15센트 상승
    )

    # 2. Twitter 감성 기록
    record_twitter_sentiment(
        domain="nba",
        team="LAL",
        score=0.7  # 긍정적
    )

    # 3. Twitter 이벤트
    record_twitter_event(domain="nba", category="injury")

    # 4. NBA 이벤트 임팩트
    record_nba_event_impact(
        game_id="401810214",
        event_type="injury",
        team="LAL",
        impact=-8.5  # AD 부상으로 큰 악재
    )

    # 5. 상관계수 계산 (예시)
    # 실제로는 시계열 데이터로 계산
    correlation = 0.85  # 높은 상관관계
    record_odds_twitter_correlation("401810214", correlation)

    # 6. Twitter 언급 횟수
    record_game_twitter_mentions("401810214", "LAL", 1523)

    # 7. 경제 이벤트 임팩트
    record_economic_nba_impact("fed_rate", -2.3)

if __name__ == "__main__":
    print("📊 고급 메트릭 예시 생성...")
    example_correlation_analysis()
    print("✅ 완료")
