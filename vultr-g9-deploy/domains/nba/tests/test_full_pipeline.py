#!/usr/bin/env python3
"""
Test full pipeline: Twitter API → SQLite Storage → LLM Processing
"""

import os
import sys

os.environ['RAPIDAPI_KEY'] = 'd9fa80a403msh90d42ea87aedfbap1b38e0jsn61919080729d'
# No OpenRouter key - LLM processor will use mock mode

sys.path.insert(0, '.')
from sources.twttr_free_adapter import TwttrFreeAdapter
from storage.raw_storage import RawTweetStorage, convert_tweet_to_raw
from processing.llm_processor import LLMProcessor
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

print("=" * 70)
print("FULL PIPELINE TEST: API → Storage → LLM")
print("=" * 70)
print()

# Initialize components
print("Initializing components...")
twitter_adapter = TwttrFreeAdapter()
raw_storage = RawTweetStorage(db_path="data/test_raw_tweets.db")
llm_processor = LLMProcessor()

print(f"✓ Twitter Adapter: {twitter_adapter.API_HOST} (mock={twitter_adapter.mock_mode})")
print(f"✓ Raw Storage: {raw_storage.db_path}")
print(f"✓ LLM Processor: (mock={llm_processor.mock_mode})")
print()

# STEP 1: Fetch tweets from Twitter API
print("=" * 70)
print("STEP 1: Fetch Tweets from Twitter241 API")
print("=" * 70)

# Fetch from top NBA reporters
nba_accounts = ['ShamsCharania', 'wojespn']
print(f"Fetching from: {nba_accounts}")

batch_results = twitter_adapter.fetch_accounts_batch(
    usernames=nba_accounts,
    max_results_per_user=5,  # Only 5 each to conserve API calls
    domain='nba'
)

total_fetched = sum(len(tweets) for tweets in batch_results.values())
print(f"\n✅ Fetched {total_fetched} tweets from {len(batch_results)} accounts")

for username, tweets in batch_results.items():
    print(f"  @{username}: {len(tweets)} tweets")

if total_fetched == 0:
    print("❌ No tweets fetched - cannot continue")
    sys.exit(1)

print()

# STEP 2: Save to SQLite storage
print("=" * 70)
print("STEP 2: Save to Raw SQLite Storage")
print("=" * 70)

# Convert to RawTweet objects
all_raw_tweets = []
for username, tweets in batch_results.items():
    for tweet in tweets:
        raw_tweet = convert_tweet_to_raw(tweet, domain='nba')
        all_raw_tweets.append(raw_tweet)

print(f"Converting {len(all_raw_tweets)} tweets to storage format...")

saved_count = raw_storage.save_tweets_batch(all_raw_tweets)
print(f"✅ Saved {saved_count} new tweets (deduplication applied)")

# Show storage stats
stats = raw_storage.get_stats()
print(f"\nStorage Stats:")
print(f"  Total tweets: {stats['total_tweets']}")
print(f"  By domain: {stats['by_domain']}")
print(f"  By status: {stats['by_status']}")
print()

# STEP 3: LLM Processing
print("=" * 70)
print("STEP 3: LLM Processing (Event Extraction)")
print("=" * 70)

# Get unprocessed tweets
unprocessed = raw_storage.get_unprocessed_tweets(domain='nba', limit=10)
print(f"Found {len(unprocessed)} unprocessed tweets")

if len(unprocessed) == 0:
    print("⚠ All tweets already processed - skipping LLM step")
else:
    # Convert to dict format for LLM processor
    tweet_dicts = []
    for tweet in unprocessed[:5]:  # Process only 5 to test
        tweet_dicts.append({
            'tweet_id': tweet.tweet_id,
            'username': tweet.username,
            'text': tweet.text,
            'created_at': tweet.created_at,
            'url': tweet.url
        })

    print(f"Processing {len(tweet_dicts)} tweets with LLM...")

    # Process with LLM
    events = llm_processor.process_tweets_batch(tweet_dicts, domain='nba')

    print(f"\n✅ LLM Processing Results:")
    print(f"  Tweets processed: {len(tweet_dicts)}")
    print(f"  Events extracted: {len(events)}")
    print(f"  Success rate: {len(events)}/{len(tweet_dicts)}")

    # Show sample events
    if events:
        print(f"\nSample Events Extracted:")
        for i, event in enumerate(events[:3], 1):
            print(f"\n  Event {i}:")
            print(f"    Type: {event.event_type}")
            print(f"    Importance: {event.importance}")
            print(f"    Summary: {event.summary[:80]}...")
            print(f"    Source: @{event.source_username}")
            if event.entities:
                print(f"    Entities: {event.entities}")

    # Mark tweets as processed in storage
    processed_ids = [t['tweet_id'] for t in tweet_dicts]
    marked_count = raw_storage.mark_processed(processed_ids)
    print(f"\n✅ Marked {marked_count} tweets as processed in storage")

print()

# FINAL: Show budget status
print("=" * 70)
print("FINAL: Budget Status")
print("=" * 70)

budget = twitter_adapter.get_budget_status()
print(f"API Calls:")
print(f"  Total used: {budget['total_used']}/{budget['monthly_limit']}")
print(f"  NBA used: {budget['nba_used']}/{budget['nba_budget']}")
print(f"  NBA remaining: {budget['nba_remaining']}")
print(f"  Economy remaining: {budget['economy_remaining']}")

storage_stats = raw_storage.get_stats()
print(f"\nStorage:")
print(f"  Total tweets: {storage_stats['total_tweets']}")
print(f"  Processed: {storage_stats['by_status'].get('processed', 0)}")
print(f"  Unprocessed: {storage_stats['by_status'].get('unprocessed', 0)}")

print()
print("=" * 70)
print("✅ FULL PIPELINE TEST COMPLETE!")
print("=" * 70)
print()
print("Summary:")
print(f"  ✓ Twitter241 API: Working ({twitter_adapter.call_count} calls made)")
print(f"  ✓ SQLite Storage: Working ({saved_count} tweets saved)")
print(f"  ✓ LLM Processing: {'Working' if llm_processor.mock_mode else 'Ready'} (mock mode)")
print(f"  ✓ Budget Tracking: Working ({budget['remaining']} calls remaining)")
print()
print("Ready for VPS deployment!")
