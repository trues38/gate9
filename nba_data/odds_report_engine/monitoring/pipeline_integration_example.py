#!/usr/bin/env python3
"""
기존 파이프라인에 G9 모니터링 통합 예시
realtime_data_collector.py, odds_api_adapter.py 등에 적용
"""

import requests
import sys
import os

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from realtime_data_collector import RealtimeDataCollector
from odds_api_adapter import OddsAPIAdapter


class MonitoringClient:
    """Prometheus 메트릭 기록 클라이언트"""

    def __init__(self, metrics_url="http://localhost:9101"):
        self.metrics_url = metrics_url

    def record_api_call(self, source: str):
        """API 호출 기록 (odds_api, twitter_api)"""
        try:
            requests.get(f"{self.metrics_url}/api/record_api_call/{source}", timeout=1)
        except:
            pass  # 모니터링 실패해도 파이프라인은 계속

    def record_odds_snapshot(self, game_id: str):
        """Odds 스냅샷 기록"""
        try:
            requests.get(f"{self.metrics_url}/api/record_odds_snapshot/{game_id}", timeout=1)
        except:
            pass

    def record_twitter_event(self, domain: str):
        """Twitter 이벤트 기록 (nba, economy)"""
        try:
            requests.get(f"{self.metrics_url}/api/record_twitter_event/{domain}", timeout=1)
        except:
            pass

    def record_job_heartbeat(self, job: str):
        """작업 heartbeat 기록"""
        try:
            requests.get(f"{self.metrics_url}/api/record_job_heartbeat/{job}", timeout=1)
        except:
            pass

    def set_nba_games(self, count: int):
        """NBA 경기 수 업데이트"""
        try:
            requests.get(f"{self.metrics_url}/api/set_nba_games/{count}", timeout=1)
        except:
            pass

    def set_econ_events(self, count: int):
        """경제 이벤트 수 업데이트"""
        try:
            requests.get(f"{self.metrics_url}/api/set_econ_events/{count}", timeout=1)
        except:
            pass


# ============================================================
# 1. Odds API Adapter에 모니터링 추가
# ============================================================

class MonitoredOddsAPIAdapter(OddsAPIAdapter):
    """Odds API + Prometheus 모니터링"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.monitor = MonitoringClient()

    def get_odds(self, sport="basketball_nba", region="us", markets="h2h"):
        """Odds API 호출 + 메트릭 기록"""
        # API 호출
        result = super().get_odds(sport, region, markets)

        # 메트릭 기록
        self.monitor.record_api_call("odds_api")

        # 각 경기 스냅샷 기록
        if result:
            for game in result:
                game_id = game.get("id")
                if game_id:
                    self.monitor.record_odds_snapshot(game_id)

        return result


# ============================================================
# 2. Realtime Data Collector에 모니터링 추가
# ============================================================

class MonitoredRealtimeDataCollector(RealtimeDataCollector):
    """Realtime Data Collector + Prometheus 모니터링"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.monitor = MonitoringClient()

    def collect_all_data(self, home_team, away_team, game_id=None):
        """전체 데이터 수집 + 메트릭 기록"""
        # 작업 시작 heartbeat
        self.monitor.record_job_heartbeat("nba_collector")

        # 데이터 수집
        result = super().collect_all_data(home_team, away_team, game_id)

        # Odds API 호출 기록
        if result.get("odds"):
            self.monitor.record_api_call("odds_api")
            if game_id:
                self.monitor.record_odds_snapshot(game_id)

        # Twitter 이벤트 기록
        if result.get("injuries"):
            # ESPN API는 무료이므로 기록 안함
            pass

        return result


# ============================================================
# 3. 크론 작업에 모니터링 추가
# ============================================================

def nba_collection_cron_with_monitoring():
    """NBA 수집 크론 작업 (모니터링 포함)"""
    monitor = MonitoringClient()

    # 작업 시작 heartbeat
    monitor.record_job_heartbeat("nba_collector")

    print("🏀 NBA 데이터 수집 시작 (with Monitoring)")

    # 오늘 경기 조회
    from datetime import datetime
    today = datetime.now().strftime("%Y%m%d")

    # Odds API로 경기 목록 조회
    odds_adapter = MonitoredOddsAPIAdapter()
    games = odds_adapter.get_odds()

    if not games:
        print("오늘 경기 없음")
        monitor.set_nba_games(0)
        return

    print(f"오늘 경기: {len(games)}개")

    # 각 경기 데이터 수집
    collector = MonitoredRealtimeDataCollector()
    for game in games:
        home_team = game["home_team"]
        away_team = game["away_team"]
        game_id = game["id"]

        print(f"수집 중: {away_team} @ {home_team}")
        collector.collect_all_data(home_team, away_team, game_id)

    # 통계 업데이트
    monitor.set_nba_games(len(games))

    print(f"✅ NBA 수집 완료: {len(games)}경기")


# ============================================================
# 4. Twitter 수집에 모니터링 추가
# ============================================================

def twitter_collection_with_monitoring(domain="nba"):
    """Twitter 수집 (모니터링 포함)"""
    monitor = MonitoringClient()

    # Twitter API 호출 (가정)
    # tweets = fetch_tweets(domain)
    tweets = []  # 실제 구현 필요

    # API 호출 기록
    monitor.record_api_call("twitter_api")

    # 각 트윗 이벤트 기록
    for tweet in tweets:
        monitor.record_twitter_event(domain)

    print(f"✅ Twitter 수집 완료: {len(tweets)}개 트윗 ({domain})")


# ============================================================
# 5. 경제 수집에 모니터링 추가
# ============================================================

def economic_collection_with_monitoring():
    """경제 이벤트 수집 (모니터링 포함)"""
    monitor = MonitoringClient()

    # 작업 시작 heartbeat
    monitor.record_job_heartbeat("economic_collector")

    # 경제 이벤트 수집 (가정)
    # events = fetch_economic_events()
    events = []  # 실제 구현 필요

    # Twitter 경제 이벤트 기록
    for event in events:
        monitor.record_twitter_event("economy")

    # 통계 업데이트
    monitor.set_econ_events(len(events))

    print(f"✅ 경제 수집 완료: {len(events)}개 이벤트")


# ============================================================
# 6. 통합 실행 예시
# ============================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="G9 모니터링 통합 파이프라인")
    parser.add_argument("--job", choices=["nba", "twitter", "economy"], required=True)
    args = parser.parse_args()

    if args.job == "nba":
        nba_collection_cron_with_monitoring()
    elif args.job == "twitter":
        twitter_collection_with_monitoring(domain="nba")
    elif args.job == "economy":
        economic_collection_with_monitoring()
