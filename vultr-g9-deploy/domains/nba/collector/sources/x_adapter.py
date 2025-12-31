"""
X (Twitter) Adapter - RapidAPI based

Uses RapidAPI Twitter scrapers for cost-efficient data collection.
NO global search - only whitelist account timelines.
"""

import requests
import hashlib
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import logging
import os

logger = logging.getLogger(__name__)


@dataclass
class Tweet:
    """Parsed tweet data"""
    tweet_id: str
    username: str
    text: str
    created_at: datetime
    retweet_count: int = 0
    like_count: int = 0
    reply_count: int = 0
    raw_data: Optional[Dict] = None

    @property
    def text_hash(self) -> str:
        """Generate hash for deduplication"""
        normalized = self.text.lower().strip()
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]


class XAdapter:
    """
    X/Twitter data adapter using RapidAPI

    Supported providers (configure via RAPIDAPI_PROVIDER env):
    - twitter-api45: Good rate limits, $10/mo for 10k calls
    - twttrapi: Alternative option
    - twitter154: Another alternative

    Set RAPIDAPI_KEY environment variable.
    """

    # RapidAPI endpoints by provider
    PROVIDERS = {
        "twitter-api45": {
            "host": "twitter-api45.p.rapidapi.com",
            "timeline_endpoint": "/timeline.php",
            "user_param": "screenname"
        },
        "twttrapi": {
            "host": "twttrapi.p.rapidapi.com",
            "timeline_endpoint": "/user-tweets",
            "user_param": "username"
        },
        "twitter154": {
            "host": "twitter154.p.rapidapi.com",
            "timeline_endpoint": "/user/tweets",
            "user_param": "username"
        }
    }

    def __init__(self, api_key: str = None, provider: str = None):
        self.api_key = api_key or os.getenv("RAPIDAPI_KEY")
        self.provider = provider or os.getenv("RAPIDAPI_PROVIDER", "twitter-api45")

        if not self.api_key:
            logger.warning("RAPIDAPI_KEY not set - using mock mode")
            self.mock_mode = True
        else:
            self.mock_mode = False

        self.config = self.PROVIDERS.get(self.provider, self.PROVIDERS["twitter-api45"])
        self.call_count = 0
        self.last_reset = datetime.now()

    def _get_headers(self) -> Dict[str, str]:
        """Get RapidAPI headers"""
        return {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": self.config["host"]
        }

    def fetch_user_timeline(
        self,
        username: str,
        since: datetime = None,
        max_results: int = 20
    ) -> List[Tweet]:
        """
        Fetch recent tweets from user timeline

        Args:
            username: Twitter username (without @)
            since: Only return tweets after this time
            max_results: Maximum tweets to return

        Returns:
            List of Tweet objects
        """
        if self.mock_mode:
            return self._mock_timeline(username)

        try:
            url = f"https://{self.config['host']}{self.config['timeline_endpoint']}"
            params = {
                self.config["user_param"]: username,
                "count": max_results
            }

            response = requests.get(
                url,
                headers=self._get_headers(),
                params=params,
                timeout=10
            )

            self.call_count += 1

            if response.status_code != 200:
                logger.error(f"API error {response.status_code}: {response.text[:200]}")
                return []

            data = response.json()
            tweets = self._parse_response(data, username)

            # Filter by time if specified
            if since:
                tweets = [t for t in tweets if t.created_at > since]

            logger.info(f"@{username}: {len(tweets)} tweets fetched")
            return tweets

        except Exception as e:
            logger.error(f"Failed to fetch @{username}: {e}")
            return []

    def _parse_response(self, data: Any, username: str) -> List[Tweet]:
        """Parse API response into Tweet objects"""
        tweets = []

        # Handle different response formats
        tweet_list = []
        if isinstance(data, list):
            tweet_list = data
        elif isinstance(data, dict):
            tweet_list = data.get("timeline", data.get("tweets", data.get("data", [])))

        for item in tweet_list:
            try:
                # Flexible parsing for different providers
                tweet = Tweet(
                    tweet_id=str(item.get("id", item.get("tweet_id", ""))),
                    username=username,
                    text=item.get("text", item.get("full_text", item.get("content", ""))),
                    created_at=self._parse_date(item.get("created_at", "")),
                    retweet_count=item.get("retweet_count", 0),
                    like_count=item.get("favorite_count", item.get("like_count", 0)),
                    reply_count=item.get("reply_count", 0),
                    raw_data=item
                )
                if tweet.text:  # Only add if has content
                    tweets.append(tweet)
            except Exception as e:
                logger.warning(f"Failed to parse tweet: {e}")
                continue

        return tweets

    def _parse_date(self, date_str: str) -> datetime:
        """Parse various date formats"""
        if not date_str:
            return datetime.now()

        formats = [
            "%a %b %d %H:%M:%S %z %Y",  # Twitter format
            "%Y-%m-%dT%H:%M:%S.%fZ",     # ISO format
            "%Y-%m-%dT%H:%M:%SZ",         # ISO without ms
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).replace(tzinfo=None)
            except ValueError:
                continue

        return datetime.now()

    def _mock_timeline(self, username: str) -> List[Tweet]:
        """Return mock data for testing"""
        logger.info(f"[MOCK] Fetching @{username}")

        # Simulate realistic mock data
        mock_tweets = {
            "ShamsCharania": [
                Tweet(
                    tweet_id="mock_1",
                    username="ShamsCharania",
                    text="LeBron James (ankle) is questionable for tonight's game vs Warriors.",
                    created_at=datetime.now() - timedelta(minutes=30)
                ),
            ],
            "wojespn": [
                Tweet(
                    tweet_id="mock_2",
                    username="wojespn",
                    text="Stephen Curry will start tonight despite knee soreness.",
                    created_at=datetime.now() - timedelta(minutes=45)
                ),
            ],
            "FantasyLabsNBA": [
                Tweet(
                    tweet_id="mock_3",
                    username="FantasyLabsNBA",
                    text="INJURY: Anthony Davis (back) - OUT tonight vs Celtics",
                    created_at=datetime.now() - timedelta(minutes=15)
                ),
            ],
        }

        return mock_tweets.get(username, [])

    def get_stats(self) -> Dict[str, Any]:
        """Get adapter statistics"""
        return {
            "provider": self.provider,
            "mock_mode": self.mock_mode,
            "calls_since_reset": self.call_count,
            "last_reset": self.last_reset.isoformat()
        }

    def reset_stats(self):
        """Reset call counter"""
        self.call_count = 0
        self.last_reset = datetime.now()


class ESPNAdapter:
    """
    ESPN API adapter for official injury/lineup data

    Free, no API key needed. Good for verification.
    """

    BASE_URL = "http://site.api.espn.com/apis/site/v2/sports/basketball/nba"

    def fetch_injuries(self) -> List[Dict]:
        """Fetch current injury report"""
        try:
            url = f"{self.BASE_URL}/injuries"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                return data.get("injuries", [])
            return []
        except Exception as e:
            logger.error(f"ESPN injuries fetch failed: {e}")
            return []

    def fetch_scoreboard(self, date_str: str = None) -> Dict:
        """Fetch today's scoreboard"""
        try:
            url = f"{self.BASE_URL}/scoreboard"
            params = {"dates": date_str} if date_str else {}
            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                return response.json()
            return {}
        except Exception as e:
            logger.error(f"ESPN scoreboard fetch failed: {e}")
            return {}

    def get_today_games(self) -> List[Dict]:
        """Get list of today's games"""
        scoreboard = self.fetch_scoreboard()
        return scoreboard.get("events", [])
