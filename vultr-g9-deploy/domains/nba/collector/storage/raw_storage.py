"""
Raw Tweet Storage (SQLite)

Purpose:
- Store raw tweets before LLM processing
- Enable reprocessing if LLM logic changes
- Deduplication
- Disaster recovery

Storage Philosophy:
"API calls are expensive, storage is cheap"
→ Store everything raw, filter later
"""

import sqlite3
import json
import hashlib
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class RawTweet:
    """Raw tweet record"""
    tweet_id: str
    username: str
    text: str
    created_at: str  # ISO format
    fetched_at: str  # ISO format
    domain: str  # "nba" or "economy"
    text_hash: str
    url: str = ""
    retweet_count: int = 0
    like_count: int = 0
    reply_count: int = 0
    raw_json: str = "{}"  # Full API response
    processed: bool = False  # Has LLM processed this?
    llm_processed_at: Optional[str] = None


class RawTweetStorage:
    """
    SQLite storage for raw tweets

    Features:
    - Append-only writes (never delete raw data)
    - Deduplication by text_hash
    - Domain-based filtering (NBA vs Economy)
    - Processing status tracking
    - Efficient queries for LLM batch processing
    """

    def __init__(self, db_path: str = "data/raw_tweets.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

        logger.info(f"RawTweetStorage initialized: {self.db_path}")

    def _init_schema(self):
        """Create database schema"""
        schema = """
        CREATE TABLE IF NOT EXISTS raw_tweets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tweet_id TEXT NOT NULL,
            username TEXT NOT NULL,
            text TEXT NOT NULL,
            created_at TEXT NOT NULL,
            fetched_at TEXT NOT NULL,
            domain TEXT NOT NULL,
            text_hash TEXT NOT NULL UNIQUE,
            url TEXT,
            retweet_count INTEGER DEFAULT 0,
            like_count INTEGER DEFAULT 0,
            reply_count INTEGER DEFAULT 0,
            raw_json TEXT,
            processed BOOLEAN DEFAULT 0,
            llm_processed_at TEXT,
            UNIQUE(text_hash)
        );

        CREATE INDEX IF NOT EXISTS idx_username ON raw_tweets(username);
        CREATE INDEX IF NOT EXISTS idx_created_at ON raw_tweets(created_at);
        CREATE INDEX IF NOT EXISTS idx_domain ON raw_tweets(domain);
        CREATE INDEX IF NOT EXISTS idx_processed ON raw_tweets(processed);
        CREATE INDEX IF NOT EXISTS idx_text_hash ON raw_tweets(text_hash);

        -- Processing log
        CREATE TABLE IF NOT EXISTS processing_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id TEXT NOT NULL,
            processed_at TEXT NOT NULL,
            tweet_count INTEGER NOT NULL,
            success_count INTEGER NOT NULL,
            error_count INTEGER NOT NULL,
            llm_model TEXT,
            processing_time_seconds REAL
        );

        -- API call tracking
        CREATE TABLE IF NOT EXISTS api_calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            called_at TEXT NOT NULL,
            domain TEXT NOT NULL,
            endpoint TEXT,
            success BOOLEAN,
            tweets_fetched INTEGER DEFAULT 0
        );
        """

        self.conn.executescript(schema)
        self.conn.commit()
        logger.info("Database schema initialized")

    def save_tweet(self, tweet: RawTweet) -> bool:
        """
        Save a raw tweet (deduplication by text_hash)

        Returns:
            True if saved (new), False if duplicate
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO raw_tweets (
                    tweet_id, username, text, created_at, fetched_at,
                    domain, text_hash, url, retweet_count, like_count,
                    reply_count, raw_json, processed
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                tweet.tweet_id,
                tweet.username,
                tweet.text,
                tweet.created_at,
                tweet.fetched_at,
                tweet.domain,
                tweet.text_hash,
                tweet.url,
                tweet.retweet_count,
                tweet.like_count,
                tweet.reply_count,
                tweet.raw_json,
                tweet.processed
            ))

            self.conn.commit()

            # Check if actually inserted (not duplicate)
            if cursor.rowcount > 0:
                logger.debug(f"Saved: @{tweet.username} - {tweet.text[:50]}")
                return True
            else:
                logger.debug(f"Duplicate skipped: {tweet.text_hash}")
                return False

        except Exception as e:
            logger.error(f"Failed to save tweet: {e}")
            return False

    def save_tweets_batch(self, tweets: List[RawTweet]) -> int:
        """
        Save multiple tweets in batch

        Returns:
            Number of new tweets saved (excluding duplicates)
        """
        saved_count = 0
        for tweet in tweets:
            if self.save_tweet(tweet):
                saved_count += 1

        logger.info(f"Batch save: {saved_count}/{len(tweets)} new tweets")
        return saved_count

    def get_unprocessed_tweets(
        self,
        domain: Optional[str] = None,
        limit: int = 100
    ) -> List[RawTweet]:
        """
        Get tweets that haven't been processed by LLM yet

        Args:
            domain: Filter by domain ("nba" or "economy")
            limit: Maximum tweets to return

        Returns:
            List of RawTweet objects
        """
        query = "SELECT * FROM raw_tweets WHERE processed = 0"
        params = []

        if domain:
            query += " AND domain = ?"
            params.append(domain)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cursor = self.conn.cursor()
        cursor.execute(query, params)

        tweets = []
        for row in cursor.fetchall():
            row_dict = dict(row)
            # Remove 'id' field (SQLite auto-increment) before creating RawTweet
            row_dict.pop('id', None)
            tweets.append(RawTweet(**row_dict))

        logger.info(f"Found {len(tweets)} unprocessed tweets")
        return tweets

    def mark_processed(self, tweet_ids: List[str]) -> int:
        """
        Mark tweets as processed by LLM

        Args:
            tweet_ids: List of tweet IDs that were processed

        Returns:
            Number of tweets marked as processed
        """
        if not tweet_ids:
            return 0

        placeholders = ",".join("?" * len(tweet_ids))
        query = f"""
            UPDATE raw_tweets
            SET processed = 1,
                llm_processed_at = ?
            WHERE tweet_id IN ({placeholders})
        """

        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute(query, [now] + tweet_ids)
        self.conn.commit()

        logger.info(f"Marked {cursor.rowcount} tweets as processed")
        return cursor.rowcount

    def log_api_call(
        self,
        domain: str,
        endpoint: str = "user-tweets",
        success: bool = True,
        tweets_fetched: int = 0
    ):
        """Log API call for tracking"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO api_calls (called_at, domain, endpoint, success, tweets_fetched)
            VALUES (?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            domain,
            endpoint,
            success,
            tweets_fetched
        ))
        self.conn.commit()

    def log_processing_batch(
        self,
        batch_id: str,
        tweet_count: int,
        success_count: int,
        error_count: int,
        llm_model: str = "MiMo-V2-Flash",
        processing_time: float = 0.0
    ):
        """Log LLM processing batch"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO processing_log (
                batch_id, processed_at, tweet_count, success_count,
                error_count, llm_model, processing_time_seconds
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            batch_id,
            datetime.now().isoformat(),
            tweet_count,
            success_count,
            error_count,
            llm_model,
            processing_time
        ))
        self.conn.commit()

    def get_recent_tweets(
        self,
        domain: Optional[str] = None,
        limit: int = 10,
        include_processed: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get recent tweets (for debugging/inspection)

        Args:
            domain: Filter by domain ("nba" or "economy")
            limit: Maximum tweets to return
            include_processed: Include already processed tweets

        Returns:
            List of tweet dicts with all fields
        """
        query = "SELECT * FROM raw_tweets WHERE 1=1"
        params = []

        if domain:
            query += " AND domain = ?"
            params.append(domain)

        if not include_processed:
            query += " AND processed = 0"

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cursor = self.conn.cursor()
        cursor.execute(query, params)

        tweets = []
        for row in cursor.fetchall():
            tweets.append(dict(row))

        logger.info(f"Retrieved {len(tweets)} recent tweets")
        return tweets

    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        cursor = self.conn.cursor()

        # Total tweets
        cursor.execute("SELECT COUNT(*) as total FROM raw_tweets")
        total = cursor.fetchone()["total"]

        # By domain
        cursor.execute("""
            SELECT domain, COUNT(*) as count
            FROM raw_tweets
            GROUP BY domain
        """)
        by_domain = {row["domain"]: row["count"] for row in cursor.fetchall()}

        # Processed vs unprocessed
        cursor.execute("""
            SELECT processed, COUNT(*) as count
            FROM raw_tweets
            GROUP BY processed
        """)
        by_status = {}
        for row in cursor.fetchall():
            status = "processed" if row["processed"] else "unprocessed"
            by_status[status] = row["count"]

        # API calls today
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM api_calls
            WHERE DATE(called_at) = DATE('now')
        """)
        api_calls_today = cursor.fetchone()["count"]

        # Recent tweets
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM raw_tweets
            WHERE DATE(created_at) = DATE('now')
        """)
        tweets_today = cursor.fetchone()["count"]

        return {
            "total_tweets": total,
            "by_domain": by_domain,
            "by_status": by_status,
            "api_calls_today": api_calls_today,
            "tweets_today": tweets_today,
            "db_path": str(self.db_path)
        }

    def close(self):
        """Close database connection"""
        self.conn.close()
        logger.info("Database connection closed")


def convert_tweet_to_raw(
    tweet_obj: Any,
    domain: str = "nba"
) -> RawTweet:
    """
    Convert Tweet object from adapter to RawTweet for storage

    Args:
        tweet_obj: Tweet object from TwttrFreeAdapter
        domain: "nba" or "economy"

    Returns:
        RawTweet ready for storage
    """
    return RawTweet(
        tweet_id=tweet_obj.tweet_id,
        username=tweet_obj.username,
        text=tweet_obj.text,
        created_at=tweet_obj.created_at.isoformat(),
        fetched_at=datetime.now().isoformat(),
        domain=domain,
        text_hash=tweet_obj.text_hash,
        url=tweet_obj.url,
        retweet_count=tweet_obj.retweet_count,
        like_count=tweet_obj.like_count,
        reply_count=tweet_obj.reply_count,
        raw_json=json.dumps(tweet_obj.raw_data) if tweet_obj.raw_data else "{}",
        processed=False
    )
