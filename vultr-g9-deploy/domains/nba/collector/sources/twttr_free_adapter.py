"""
Twttr API Free Adapter (RapidAPI)

Uses RapidAPI's Twttr API BASIC plan ($0.00/mo)
Optimized for 500 calls/month limit

Strategy:
- 1 call = multiple accounts in batch
- NBA: Event-based timing (before games)
- Economy: Session-based timing (market hours)
"""

import requests
import hashlib
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import logging
import os
import time

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
    url: str = ""
    raw_data: Optional[Dict] = None

    @property
    def text_hash(self) -> str:
        """Generate hash for deduplication"""
        normalized = self.text.lower().strip()
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]


class TwttrFreeAdapter:
    """
    Twttr API Free Adapter (RapidAPI BASIC: $0.00/mo)

    Key Features:
    - Monthly limit tracking (500 calls/month)
    - Batch account fetching (1 call = N accounts)
    - Rate limit handling
    - Call budget allocation (NBA vs Economy)

    Usage:
        adapter = TwttrFreeAdapter()
        tweets = adapter.fetch_accounts_batch(["ShamsCharania", "wojespn"], since=yesterday)
    """

    # API configuration based on RapidAPI Twitter241
    API_HOST = "twitter241.p.rapidapi.com"
    MONTHLY_LIMIT = 500  # Free tier limit

    # Endpoints
    USER_BY_USERNAME_ENDPOINT = "/user"
    USER_TWEETS_ENDPOINT = "/user-tweets"

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("RAPIDAPI_KEY")

        if not self.api_key:
            logger.warning("RAPIDAPI_KEY not set - using mock mode")
            self.mock_mode = True
        else:
            self.mock_mode = False

        logger.info(f"Using API host: {self.API_HOST}")

        # Call tracking
        self.call_count = 0
        self.monthly_calls = 0

        # Username -> User ID cache (to save API calls)
        self.user_id_cache = {}  # {username: user_id}
        self.last_reset = datetime.now()

        # Budget allocation (NBA vs Economy)
        self.nba_budget = 250  # 50% for NBA
        self.economy_budget = 200  # 40% for Economy
        self.test_budget = 50  # 10% for testing/buffer

        self.nba_used = 0
        self.economy_used = 0

        logger.info(f"TwttrFreeAdapter initialized (mock={self.mock_mode})")
        logger.info(f"Budget: NBA={self.nba_budget}, Economy={self.economy_budget}, Test={self.test_budget}")

    def _get_headers(self) -> Dict[str, str]:
        """Get RapidAPI headers"""
        return {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": self.API_HOST
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

    def _get_user_id(self, username: str, domain: str = "nba") -> Optional[str]:
        """
        Get user ID from username (with caching)

        Args:
            username: Twitter username
            domain: Budget tracking domain

        Returns:
            User ID string or None
        """
        # Check cache first
        if username in self.user_id_cache:
            logger.debug(f"Using cached ID for @{username}")
            return self.user_id_cache[username]

        if not self.can_call(domain):
            logger.warning(f"Budget exceeded for {domain} domain")
            return None

        try:
            url = f"https://{self.API_HOST}{self.USER_BY_USERNAME_ENDPOINT}"
            params = {"username": username}

            response = requests.get(
                url,
                headers=self._get_headers(),
                params=params,
                timeout=10
            )

            # Track API call
            self.call_count += 1
            self.monthly_calls += 1
            if domain == "nba":
                self.nba_used += 1
            elif domain == "economy":
                self.economy_used += 1

            logger.info(f"API Call (Get User ID): {self.monthly_calls}/{self.MONTHLY_LIMIT}")

            if response.status_code != 200:
                logger.error(f"Failed to get user ID for @{username}: {response.status_code}")
                return None

            data = response.json()

            # Extract user ID from response (Twitter241 API structure)
            user_id = None
            if isinstance(data, dict):
                # Twitter241 actual structure: result.data.user.result.rest_id
                if "result" in data and "data" in data["result"]:
                    user_data = data["result"]["data"].get("user", {})
                    if "result" in user_data:
                        user_id = user_data["result"].get("rest_id")

                # Fallback: try other common structures
                if not user_id and "user" in data and "result" in data["user"]:
                    user_id = data["user"]["result"].get("rest_id")

                if not user_id:
                    user_id = data.get("id") or data.get("user_id") or data.get("rest_id")

                if not user_id and "user" in data:
                    user_id = data["user"].get("id") or data["user"].get("rest_id")

            if user_id:
                user_id = str(user_id)
                self.user_id_cache[username] = user_id
                logger.debug(f"Cached user ID for @{username}: {user_id}")
                return user_id
            else:
                logger.error(f"Could not extract user ID from response for @{username}")
                return None

        except Exception as e:
            logger.error(f"Error getting user ID for @{username}: {e}")
            return None

    def fetch_user_timeline(
        self,
        username: str,
        since: datetime = None,
        max_results: int = 20,
        domain: str = "nba"
    ) -> List[Tweet]:
        """
        Fetch recent tweets from a single user

        Two-step process:
        1. Get user ID from username (cached)
        2. Fetch tweets by user ID

        Args:
            username: Twitter username (without @)
            since: Only return tweets after this time
            max_results: Maximum tweets to return
            domain: "nba" or "economy" (for budget tracking)

        Returns:
            List of Tweet objects
        """
        if self.mock_mode:
            return self._mock_timeline(username)

        if not self.can_call(domain):
            logger.warning(f"Budget exceeded for {domain} domain")
            return []

        # Step 1: Get user ID
        user_id = self._get_user_id(username, domain)
        if not user_id:
            logger.error(f"Cannot fetch tweets without user ID for @{username}")
            return []

        # Step 2: Fetch tweets
        try:
            url = f"https://{self.API_HOST}{self.USER_TWEETS_ENDPOINT}"
            params = {
                "user": user_id,
                "count": max_results
            }

            logger.debug(f"Fetching tweets: {url} with user={user_id}")

            response = requests.get(
                url,
                headers=self._get_headers(),
                params=params,
                timeout=15
            )

            # Track API call
            self.call_count += 1
            self.monthly_calls += 1
            if domain == "nba":
                self.nba_used += 1
            elif domain == "economy":
                self.economy_used += 1

            logger.info(f"API Call (Get Tweets): {self.monthly_calls}/{self.MONTHLY_LIMIT} (NBA: {self.nba_used}, Econ: {self.economy_used})")

            if response.status_code == 429:
                logger.error("Rate limit exceeded!")
                return []

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

    def fetch_accounts_batch(
        self,
        usernames: List[str],
        since: datetime = None,
        max_results_per_user: int = 10,
        domain: str = "nba"
    ) -> Dict[str, List[Tweet]]:
        """
        Fetch tweets from multiple accounts in batch

        OPTIMIZATION: Use this for most efficient API usage
        1 call per account, but fetches all at once

        Args:
            usernames: List of Twitter usernames
            since: Only return tweets after this time
            max_results_per_user: Maximum tweets per user
            domain: "nba" or "economy"

        Returns:
            Dict mapping username -> List[Tweet]
        """
        results = {}

        for username in usernames:
            if not self.can_call(domain):
                logger.warning(f"Budget exceeded, stopping batch fetch")
                break

            tweets = self.fetch_user_timeline(
                username=username,
                since=since,
                max_results=max_results_per_user,
                domain=domain
            )
            results[username] = tweets

            # Rate limiting (be nice to free tier)
            time.sleep(0.5)

        total_tweets = sum(len(tweets) for tweets in results.values())
        logger.info(f"Batch fetch complete: {len(results)} accounts, {total_tweets} tweets")

        return results

    def _parse_response(self, data: Any, username: str) -> List[Tweet]:
        """Parse API response into Tweet objects (Twitter241 structure)"""
        tweets = []

        if not isinstance(data, dict):
            return tweets

        # Twitter241 structure: result.timeline.instructions[]
        result = data.get('result', {})
        timeline = result.get('timeline', {})
        instructions = timeline.get('instructions', [])

        for instruction in instructions:
            instr_type = instruction.get('type', '')

            # Handle pinned tweet
            if instr_type == 'TimelinePinEntry':
                entry = instruction.get('entry', {})
                tweet = self._extract_tweet_from_entry(entry, username)
                if tweet:
                    tweets.append(tweet)

            # Handle timeline entries
            elif instr_type == 'TimelineAddEntries':
                entries = instruction.get('entries', [])
                for entry in entries:
                    tweet = self._extract_tweet_from_entry(entry, username)
                    if tweet:
                        tweets.append(tweet)

        return tweets

    def _extract_tweet_from_entry(self, entry: Dict, default_username: str) -> Optional[Tweet]:
        """Extract Tweet object from a timeline entry"""
        try:
            content = entry.get('content', {})
            item_content = content.get('itemContent', {})

            # Check if this is a tweet
            if item_content.get('itemType') != 'TimelineTweet':
                return None

            tweet_results = item_content.get('tweet_results', {})
            result = tweet_results.get('result', {})

            if not result:
                return None

            # Extract tweet data
            tweet_id = result.get('rest_id', '')
            legacy = result.get('legacy', {})

            # Get text
            text = legacy.get('full_text', '') or legacy.get('text', '')
            if not text:
                return None

            # Get user info
            core = result.get('core', {})
            user_results = core.get('user_results', {})
            user = user_results.get('result', {})
            user_core = user.get('core', {})
            tweet_username = user_core.get('screen_name', default_username)

            # Get timestamp
            created_at = legacy.get('created_at', '')

            # Get engagement
            retweet_count = legacy.get('retweet_count', 0)
            favorite_count = legacy.get('favorite_count', 0)
            reply_count = legacy.get('reply_count', 0)

            return Tweet(
                tweet_id=tweet_id,
                username=tweet_username,
                text=text,
                created_at=self._parse_date(created_at),
                retweet_count=retweet_count,
                like_count=favorite_count,
                reply_count=reply_count,
                url=f"https://twitter.com/{tweet_username}/status/{tweet_id}",
                raw_data=result
            )

        except Exception as e:
            logger.warning(f"Failed to extract tweet from entry: {e}")
            return None

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

        mock_tweets = {
            "ShamsCharania": [
                Tweet(
                    tweet_id="mock_1",
                    username="ShamsCharania",
                    text="LeBron James (ankle) is questionable for tonight's game vs Warriors.",
                    created_at=datetime.now() - timedelta(minutes=30),
                    url="https://twitter.com/ShamsCharania/status/mock_1"
                ),
            ],
            "wojespn": [
                Tweet(
                    tweet_id="mock_2",
                    username="wojespn",
                    text="Stephen Curry will start tonight despite knee soreness.",
                    created_at=datetime.now() - timedelta(minutes=45),
                    url="https://twitter.com/wojespn/status/mock_2"
                ),
            ],
        }

        return mock_tweets.get(username, [])

    def get_budget_status(self) -> Dict[str, Any]:
        """Get current budget usage status"""
        return {
            "monthly_limit": self.MONTHLY_LIMIT,
            "total_used": self.monthly_calls,
            "remaining": self.MONTHLY_LIMIT - self.monthly_calls,
            "nba_budget": self.nba_budget,
            "nba_used": self.nba_used,
            "nba_remaining": self.nba_budget - self.nba_used,
            "economy_budget": self.economy_budget,
            "economy_used": self.economy_used,
            "economy_remaining": self.economy_budget - self.economy_used,
            "test_budget": self.test_budget
        }

    def reset_monthly_stats(self):
        """Reset monthly call counters (call at start of each month)"""
        self.monthly_calls = 0
        self.nba_used = 0
        self.economy_used = 0
        self.last_reset = datetime.now()
        logger.info("Monthly stats reset")

    def get_stats(self) -> Dict[str, Any]:
        """Get adapter statistics"""
        return {
            "provider": "twttr-api-free",
            "mock_mode": self.mock_mode,
            "calls_this_session": self.call_count,
            "budget_status": self.get_budget_status(),
            "last_reset": self.last_reset.isoformat()
        }
