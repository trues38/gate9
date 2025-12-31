"""
G9 Data Collection Pipeline - Main Orchestrator

Flow:
1. Scheduler decides when to collect
2. API adapter fetches raw tweets (1 call for ALL whitelist!)
3. Raw storage saves tweets
4. LLM processor structures tweets
5. Neo4j stores structured events

Budget: 1000 calls/month (FREE) - Twitter API45
"""

import sys
from pathlib import Path

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent))

from sources.twitter_api45_adapter import TwitterAPI45Adapter
from sources.odds_api_adapter import OddsAPIAdapter
from storage.raw_storage import RawTweetStorage, convert_tweet_to_raw
from processing.llm_processor import LLMProcessor
from scheduling.time_based_scheduler import TimeBasedScheduler
from adapters.neo4j_adapter import Neo4jAdapter
from datetime import datetime, timedelta
import logging
import time
import requests

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class G9Pipeline:
    """
    Main data collection pipeline

    Philosophy:
    - API calls are precious (1000/month limit)
    - 1 API call = ALL whitelist accounts (Search API with OR query)
    - Collect only when timing matters
    - Store raw, process later
    - LLM structures, Graph analyzes
    """

    def __init__(self):
        # Components
        self.twitter_adapter = TwitterAPI45Adapter()
        self.odds_adapter = OddsAPIAdapter()
        self.raw_storage = RawTweetStorage()
        self.llm_processor = LLMProcessor()
        self.scheduler = TimeBasedScheduler()
        self.neo4j = Neo4jAdapter()

        # Whitelist accounts
        self.nba_accounts = [
            "ShamsCharania", "wojespn", "ChrisBHaynes", "UnderdogNBA",
            "FantasyLabsNBA", "NBAInjuryR3p0rt", "FantasyLabsDFS",
            "RotoGrinders", "Rotoworld_BK", "NBAFantasy",
            "OfficialNBARefs", "NBARefStats"
        ]

        self.economy_accounts = [
            "federalreserve", "ECB", "BoJOfficial",
            "markets", "FT", "WSJ", "Bloomberg"
        ]

        logger.info("=" * 60)
        logger.info("G9 Pipeline Initialized")
        logger.info(f"NBA accounts: {len(self.nba_accounts)}")
        logger.info(f"Economy accounts: {len(self.economy_accounts)}")
        logger.info(f"Monthly budget: {self.scheduler.monthly_budget} calls")
        logger.info("=" * 60)

    def _fetch_today_schedule(self) -> list:
        """
        Fetch today's NBA game schedule from ESPN API

        Returns:
            List of datetime objects for today's games
        """
        try:
            today = datetime.now().strftime('%Y%m%d')
            url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
            params = {"dates": today}

            logger.info(f"Fetching today's NBA schedule from ESPN API (date={today})")
            response = requests.get(url, params=params, timeout=10)

            if response.status_code != 200:
                logger.error(f"ESPN API error: {response.status_code}")
                return []

            data = response.json()
            events = data.get('events', [])

            if not events:
                logger.info("No NBA games scheduled for today")
                return []

            game_times = []
            for event in events:
                # Parse game time
                date_str = event.get('date')  # ISO format: "2025-12-28T19:00Z"
                if date_str:
                    # Parse as UTC and convert to naive datetime (remove timezone info)
                    game_time = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    game_time_naive = game_time.replace(tzinfo=None)
                    game_times.append(game_time_naive)

                    # Log game info
                    home_team = event.get('competitions', [{}])[0].get('competitors', [{}])[0].get('team', {}).get('abbreviation', 'UNK')
                    away_team = event.get('competitions', [{}])[0].get('competitors', [{}])[1].get('team', {}).get('abbreviation', 'UNK')
                    logger.info(f"  Game found: {away_team} @ {home_team} at {game_time_naive.strftime('%H:%M')}")

            logger.info(f"Found {len(game_times)} games scheduled for today")
            return game_times

        except Exception as e:
            logger.error(f"Failed to fetch today's schedule: {e}")
            return []

    def run_nba_collection(self, game_times: list = None) -> dict:
        """
        Run NBA collection cycle

        Args:
            game_times: List of datetime objects for upcoming games

        Returns:
            Collection summary
        """
        logger.info("=" * 60)
        logger.info("NBA COLLECTION CYCLE")
        logger.info("=" * 60)

        # Auto-fetch today's schedule if not provided
        if not game_times:
            logger.info("No game_times provided - fetching today's schedule")
            game_times = self._fetch_today_schedule()

        # Check if we should collect
        if not self.scheduler.should_collect_nba(game_times or []):
            logger.info("Not in NBA collection window - skipping")
            return {"status": "skipped", "reason": "not in window"}

        # Check budget
        if not self.twitter_adapter.can_call("nba"):
            logger.warning("NBA budget exceeded - skipping")
            return {"status": "skipped", "reason": "budget exceeded"}

        # Fetch tweets (1 API call for ALL accounts!)
        logger.info(f"Fetching from {len(self.nba_accounts)} NBA accounts (1 API call)...")
        since = datetime.now() - timedelta(hours=3)  # Last 3 hours

        tweets = self.twitter_adapter.fetch_whitelist_batch(
            accounts=self.nba_accounts,
            since=since,
            domain="nba"
        )

        # Convert to RawTweet and save
        all_raw_tweets = []
        for tweet in tweets:
            raw_tweet = convert_tweet_to_raw(tweet, domain="nba")
            all_raw_tweets.append(raw_tweet)

        saved_count = self.raw_storage.save_tweets_batch(all_raw_tweets)
        logger.info(f"Saved {saved_count} new tweets to raw storage")

        # Update budget (1 API call only!)
        self.scheduler.increment_usage("nba", 1)

        # Log API call
        self.raw_storage.log_api_call(
            domain="nba",
            success=True,
            tweets_fetched=saved_count
        )

        return {
            "status": "success",
            "accounts_fetched": len(self.nba_accounts),
            "tweets_found": len(all_raw_tweets),
            "tweets_saved": saved_count,
            "budget": self.scheduler.get_budget_status()
        }

    def run_economy_collection(self) -> dict:
        """
        Run Economy collection cycle

        Returns:
            Collection summary
        """
        logger.info("=" * 60)
        logger.info("ECONOMY COLLECTION CYCLE")
        logger.info("=" * 60)

        # Check if we should collect
        if not self.scheduler.should_collect_economy():
            logger.info("Not in Economy collection window - skipping")
            return {"status": "skipped", "reason": "not in window"}

        # Check budget
        if not self.twitter_adapter.can_call("economy"):
            logger.warning("Economy budget exceeded - skipping")
            return {"status": "skipped", "reason": "budget exceeded"}

        # Fetch tweets (1 API call for ALL accounts!)
        logger.info(f"Fetching from {len(self.economy_accounts)} Economy accounts (1 API call)...")
        since = datetime.now() - timedelta(hours=6)  # Last 6 hours

        tweets = self.twitter_adapter.fetch_whitelist_batch(
            accounts=self.economy_accounts,
            since=since,
            domain="economy"
        )

        # Convert and save
        all_raw_tweets = []
        for tweet in tweets:
            raw_tweet = convert_tweet_to_raw(tweet, domain="economy")
            all_raw_tweets.append(raw_tweet)

        saved_count = self.raw_storage.save_tweets_batch(all_raw_tweets)
        logger.info(f"Saved {saved_count} new tweets to raw storage")

        # Update budget (1 API call only!)
        self.scheduler.increment_usage("economy", 1)

        # Log API call
        self.raw_storage.log_api_call(
            domain="economy",
            success=True,
            tweets_fetched=saved_count
        )

        return {
            "status": "success",
            "accounts_fetched": len(self.economy_accounts),
            "tweets_found": len(all_raw_tweets),
            "tweets_saved": saved_count,
            "budget": self.scheduler.get_budget_status()
        }

    def run_llm_processing(self, domain: str = "nba", batch_size: int = 50) -> dict:
        """
        Process unprocessed tweets with LLM

        Args:
            domain: "nba" or "economy"
            batch_size: Number of tweets to process at once

        Returns:
            Processing summary
        """
        logger.info("=" * 60)
        logger.info(f"LLM PROCESSING: {domain.upper()}")
        logger.info("=" * 60)

        # Get unprocessed tweets
        unprocessed = self.raw_storage.get_unprocessed_tweets(
            domain=domain,
            limit=batch_size
        )

        if not unprocessed:
            logger.info("No unprocessed tweets")
            return {"status": "idle", "processed": 0}

        # Convert to dict for LLM
        tweets_data = [
            {
                "tweet_id": t.tweet_id,
                "username": t.username,
                "text": t.text,
                "created_at": t.created_at
            }
            for t in unprocessed
        ]

        # Process with LLM
        start_time = time.time()
        events = self.llm_processor.process_tweets_batch(tweets_data, domain=domain)
        processing_time = time.time() - start_time

        logger.info(f"LLM processed {len(tweets_data)} tweets → {len(events)} events")

        # Save events to Neo4j
        saved_count = 0
        for event in events:
            event_data = {
                "event_id": f"evt_{event.tweet_id}",
                "game_id": "",  # To be linked later
                "source_username": event.source_username,
                "source_credibility": 1.0,  # From whitelist
                "event_type": event.event_type.lower(),
                "raw_text": event.raw_text,
                "text_hash": event.tweet_id,  # Use tweet_id as hash
                "collected_at": event.timestamp,
                "player": event.entities.get("player"),
                "team": event.entities.get("team"),
                "status": event.entities.get("status")
            }

            if self.neo4j.save_event(event_data):
                saved_count += 1

        # Mark as processed
        tweet_ids = [t.tweet_id for t in unprocessed]
        self.raw_storage.mark_processed(tweet_ids)

        # Log processing
        self.raw_storage.log_processing_batch(
            batch_id=f"{domain}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            tweet_count=len(tweets_data),
            success_count=saved_count,
            error_count=len(tweets_data) - saved_count,
            llm_model="MiMo-V2-Flash",
            processing_time=processing_time
        )

        return {
            "status": "success",
            "tweets_processed": len(tweets_data),
            "events_extracted": len(events),
            "events_saved": saved_count,
            "processing_time": round(processing_time, 2)
        }

    def run_odds_collection(self, tier: str = "tier1", snapshot_type: str = "close") -> dict:
        """
        Collect odds data from The Odds API

        Args:
            tier: "tier1" (all games) or "tier2" (top games only)
            snapshot_type: "open" (T-24h), "mid" (T-3h), or "close" (T-1h)

        Returns:
            Collection summary
        """
        logger.info("=" * 60)
        logger.info(f"ODDS COLLECTION: {tier.upper()} - {snapshot_type.upper()}")
        logger.info("=" * 60)

        # Check budget
        if not self.odds_adapter.can_call(tier):
            logger.warning(f"{tier} budget exceeded - skipping")
            return {"status": "skipped", "reason": "budget exceeded"}

        # Fetch odds
        logger.info(f"Fetching NBA odds from The Odds API ({tier})...")
        snapshots = self.odds_adapter.fetch_current_odds(
            tier=tier,
            snapshot_type=snapshot_type
        )

        if not snapshots:
            logger.info("No odds data available")
            return {"status": "idle", "snapshots": 0}

        # Save to Neo4j
        saved_count = 0
        for snapshot in snapshots:
            # Convert OddsSnapshot to dict
            odds_dict = {
                "odds_id": snapshot.odds_id,
                "game_id": snapshot.game_id,
                "collected_at": snapshot.collected_at.isoformat(),
                "time_to_game_minutes": snapshot.time_to_game_minutes,
                "snapshot_type": snapshot.snapshot_type,
                "home_team": snapshot.home_team,
                "away_team": snapshot.away_team,
                "commence_time": snapshot.commence_time.isoformat(),
                "home_ml": snapshot.home_ml,
                "away_ml": snapshot.away_ml,
                "home_spread": snapshot.home_spread,
                "home_spread_odds": snapshot.home_spread_odds,
                "away_spread": snapshot.away_spread,
                "away_spread_odds": snapshot.away_spread_odds,
                "total_line": snapshot.total_line,
                "over_odds": snapshot.over_odds,
                "under_odds": snapshot.under_odds,
                "bookmaker": snapshot.bookmaker,
                "source_api": snapshot.source_api
            }

            if self.neo4j.save_odds(odds_dict):
                saved_count += 1

        logger.info(f"Saved {saved_count} odds snapshots to Neo4j")

        return {
            "status": "success",
            "tier": tier,
            "snapshot_type": snapshot_type,
            "snapshots_fetched": len(snapshots),
            "snapshots_saved": saved_count,
            "budget": self.odds_adapter.get_stats()
        }

    def get_status(self) -> dict:
        """Get pipeline status"""
        return {
            "twitter_adapter": self.twitter_adapter.get_stats(),
            "odds_adapter": self.odds_adapter.get_stats(),
            "raw_storage": self.raw_storage.get_stats(),
            "llm_processor": self.llm_processor.get_stats(),
            "scheduler": self.scheduler.get_budget_status(),
            "neo4j": self.neo4j.get_stats()
        }


def main():
    """Main entry point for testing"""
    pipeline = G9Pipeline()

    # Test NBA collection (mock mode if no API key)
    logger.info("\n" + "=" * 60)
    logger.info("TESTING NBA COLLECTION")
    logger.info("=" * 60)

    # Simulate game in 1 hour
    game_time = datetime.now() + timedelta(hours=1)
    result = pipeline.run_nba_collection([game_time])
    logger.info(f"Result: {result}")

    # Test LLM processing
    logger.info("\n" + "=" * 60)
    logger.info("TESTING LLM PROCESSING")
    logger.info("=" * 60)

    result = pipeline.run_llm_processing(domain="nba", batch_size=10)
    logger.info(f"Result: {result}")

    # Print status
    logger.info("\n" + "=" * 60)
    logger.info("PIPELINE STATUS")
    logger.info("=" * 60)

    status = pipeline.get_status()
    import json
    logger.info(json.dumps(status, indent=2))


if __name__ == "__main__":
    main()
