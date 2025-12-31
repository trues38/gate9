"""
Twitter API45 Adapter - 1000 free calls/month

Key Features:
- 1 API call = All whitelist accounts
- Search with OR query: "from:user1 OR from:user2 OR ..."
- Clean response structure
- 1000 calls/month budget

Strategy:
- NBA: 1 call per collection = 15 collections/day = 450 calls/month
- Economy: 1 call per collection = 7 collections/week = 120 calls/month
- Total: ~570 calls/month (well within 1000 limit!)
"""

import os
import requests
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Tweet:
    """Tweet data structure"""
    tweet_id: str
    username: str
    text: str
    created_at: datetime
    favorites: int = 0
    retweets: int = 0
    replies: int = 0
    media: Dict[str, Any] = None


class TwitterAPI45Adapter:
    """
    Twitter API45 Adapter for G9 Data Collection

    Philosophy:
    - 1 API call = ALL whitelist accounts
    - Use Search API with OR query
    - Track budget carefully (1000/month)
    """

    # API Configuration
    API_HOST = "twitter-api45.p.rapidapi.com"
    SEARCH_ENDPOINT = "/search.php"
    MONTHLY_LIMIT = 1000

    def __init__(self):
        self.api_key = os.getenv("RAPIDAPI_KEY")

        # Budget tracking
        self.monthly_calls = 0
        self.nba_used = 0
        self.economy_used = 0

        # Budget allocation
        self.nba_budget = 600  # 2x daily collection during game season
        self.economy_budget = 300  # Weekly 30 collections

        # Mock mode check
        self.mock_mode = not self.api_key or self.api_key == ""

        if self.mock_mode:
            logger.warning("RAPIDAPI_KEY not set - using mock mode")
        else:
            logger.info(f"Using API host: {self.API_HOST}")

        logger.info(f"TwitterAPI45Adapter initialized (mock={self.mock_mode})")
        logger.info(f"Budget: NBA={self.nba_budget}, Economy={self.economy_budget}")

    def _get_headers(self) -> Dict[str, str]:
        """Get API request headers"""
        return {
            "x-rapidapi-host": self.API_HOST,
            "x-rapidapi-key": self.api_key
        }

    def can_call(self, domain: str = "nba") -> bool:
        """Check if we can make a call within budget"""
        if self.mock_mode:
            return True

        if domain == "nba":
            return self.nba_used < self.nba_budget
        elif domain == "economy":
            return self.economy_used < self.economy_budget
        else:
            return self.monthly_calls < self.MONTHLY_LIMIT

    def fetch_whitelist_batch(
        self,
        accounts: List[str],
        since: datetime = None,
        domain: str = "nba",
        search_type: str = "Latest"
    ) -> List[Tweet]:
        """
        Fetch tweets from ALL whitelist accounts in 1 API call

        Args:
            accounts: List of Twitter usernames
            since: Only return tweets after this time
            domain: "nba" or "economy"
            search_type: "Latest" or "Top"

        Returns:
            List of Tweet objects
        """
        if self.mock_mode:
            logger.warning("Mock mode - returning empty list")
            return []

        if not self.can_call(domain):
            logger.warning(f"Budget exceeded for {domain} domain")
            return []

        try:
            # Build OR query: "from:user1 OR from:user2 OR ..."
            from_queries = [f"from:{acc}" for acc in accounts]
            query = " OR ".join(from_queries)

            # Add time filter if needed
            if since:
                # Twitter search supports since:YYYY-MM-DD
                since_str = since.strftime("%Y-%m-%d")
                query += f" since:{since_str}"

            logger.info(f"Search query: ({query[:100]}...)")

            # API Request
            url = f"https://{self.API_HOST}{self.SEARCH_ENDPOINT}"
            params = {
                "query": query,
                "search_type": search_type
            }

            response = requests.get(
                url,
                headers=self._get_headers(),
                params=params,
                timeout=30
            )

            # Track API call
            self.monthly_calls += 1
            if domain == "nba":
                self.nba_used += 1
            elif domain == "economy":
                self.economy_used += 1

            logger.info(f"API Call: {self.monthly_calls}/{self.MONTHLY_LIMIT} (NBA: {self.nba_used}, Economy: {self.economy_used})")

            if response.status_code == 429:
                logger.error("Rate limit exceeded!")
                return []

            if response.status_code != 200:
                logger.error(f"API error {response.status_code}: {response.text[:200]}")
                return []

            data = response.json()
            tweets = self._parse_response(data)

            # Additional time filtering (API since: is day-level, we need hour-level)
            if since:
                tweets = [t for t in tweets if t.created_at > since]

            logger.info(f"✅ Fetched {len(tweets)} tweets from {len(accounts)} accounts (1 API call)")
            return tweets

        except Exception as e:
            logger.error(f"Failed to fetch tweets: {e}")
            return []

    def _parse_response(self, data: Dict[str, Any]) -> List[Tweet]:
        """
        Parse API45 response into Tweet objects

        Response structure:
        {
          "timeline": [
            {
              "type": "tweet",
              "tweet_id": "...",
              "screen_name": "...",
              "created_at": "Sat Sep 16 18:08:33 +0000 2023",
              "text": "...",
              "favorites": 241,
              "retweets": 19,
              "replies": 42,
              "media": {...}
            }
          ],
          "next_cursor": "..."
        }
        """
        tweets = []

        if not isinstance(data, dict):
            logger.error("Invalid response format")
            return tweets

        timeline = data.get("timeline", [])

        for item in timeline:
            if item.get("type") != "tweet":
                continue

            # Skip promoted tweets
            if "promoted-" in item.get("tweet_id", ""):
                continue

            try:
                # Parse created_at: "Sat Sep 16 18:08:33 +0000 2023"
                created_at_str = item.get("created_at", "")
                created_at = datetime.strptime(created_at_str, "%a %b %d %H:%M:%S %z %Y")
                created_at_naive = created_at.replace(tzinfo=None)  # Remove timezone

                tweet = Tweet(
                    tweet_id=item.get("tweet_id", ""),
                    username=item.get("screen_name", ""),
                    text=item.get("text", ""),
                    created_at=created_at_naive,
                    favorites=item.get("favorites", 0),
                    retweets=item.get("retweets", 0),
                    replies=item.get("replies", 0),
                    media=item.get("media")
                )

                tweets.append(tweet)

            except Exception as e:
                logger.error(f"Failed to parse tweet: {e}")
                continue

        return tweets

    def get_stats(self) -> Dict[str, Any]:
        """Get adapter statistics"""
        return {
            "api_host": self.API_HOST,
            "mock_mode": self.mock_mode,
            "monthly_limit": self.MONTHLY_LIMIT,
            "monthly_calls": self.monthly_calls,
            "nba_budget": self.nba_budget,
            "nba_used": self.nba_used,
            "nba_remaining": self.nba_budget - self.nba_used,
            "economy_budget": self.economy_budget,
            "economy_used": self.economy_used,
            "economy_remaining": self.economy_budget - self.economy_used,
            "percentage_used": round((self.monthly_calls / self.MONTHLY_LIMIT) * 100, 1)
        }


def test_api45():
    """Test API45 adapter"""
    adapter = TwitterAPI45Adapter()

    # Test NBA whitelist
    nba_accounts = [
        "ShamsCharania", "wojespn", "ChrisBHaynes", "UnderdogNBA",
        "FantasyLabsNBA", "NBAInjuryR3p0rt"
    ]

    print("=" * 60)
    print("Testing Twitter API45 - NBA Whitelist")
    print("=" * 60)

    since = datetime.now() - timedelta(hours=24)
    tweets = adapter.fetch_whitelist_batch(
        accounts=nba_accounts,
        since=since,
        domain="nba"
    )

    print(f"\nResults: {len(tweets)} tweets")

    if tweets:
        print("\nSample tweets:")
        for i, tweet in enumerate(tweets[:5], 1):
            print(f"\n{i}. @{tweet.username} ({tweet.created_at.strftime('%Y-%m-%d %H:%M')})")
            print(f"   {tweet.text[:100]}...")
            print(f"   ❤️ {tweet.favorites}  🔁 {tweet.retweets}  💬 {tweet.replies}")

    print("\n" + "=" * 60)
    print("API Usage:")
    print("=" * 60)
    stats = adapter.get_stats()
    print(f"Total: {stats['monthly_calls']}/{stats['monthly_limit']}")
    print(f"NBA: {stats['nba_used']}/{stats['nba_budget']}")
    print(f"Economy: {stats['economy_used']}/{stats['economy_budget']}")


if __name__ == "__main__":
    test_api45()
