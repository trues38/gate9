#!/usr/bin/env python3
"""
Test TwttrFreeAdapter with real Twitter241 API
"""

import os
import sys

os.environ['RAPIDAPI_KEY'] = 'd9fa80a403msh90d42ea87aedfbap1b38e0jsn61919080729d'

sys.path.insert(0, '.')
from sources.twttr_free_adapter import TwttrFreeAdapter
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.DEBUG)

print("=" * 60)
print("Testing Twttr API with REAL endpoint")
print("=" * 60)

adapter = TwttrFreeAdapter()
print(f"API Host: {adapter.API_HOST}")
print(f"Mock mode: {adapter.mock_mode}")
print()

# Test 1: Get user ID
print("TEST 1: Get User ID")
print("-" * 60)
user_id = adapter._get_user_id('ShamsCharania', domain='nba')
if user_id:
    print(f"✅ SUCCESS: User ID = {user_id}")
else:
    print(f"❌ FAILED: Could not get user ID")
    sys.exit(1)

print()

# Test 2: Fetch user timeline
print("TEST 2: Fetch User Timeline")
print("-" * 60)
tweets = adapter.fetch_user_timeline(
    username='ShamsCharania',
    max_results=3,
    domain='nba'
)

print(f"Result: {len(tweets)} tweets")
if tweets:
    print()
    for i, tweet in enumerate(tweets, 1):
        print(f"{i}. [{tweet.created_at.strftime('%m/%d %H:%M')}] {tweet.text[:100]}...")
        print(f"   URL: {tweet.url}")
        print(f"   Engagement: {tweet.retweet_count} RTs, {tweet.like_count} likes")
        print()
    print(f"✅ SUCCESS: Fetched {len(tweets)} tweets")
else:
    print("❌ FAILED: No tweets returned")
    sys.exit(1)

print()

# Test 3: Batch fetch
print("TEST 3: Batch Fetch Multiple Accounts")
print("-" * 60)
batch_results = adapter.fetch_accounts_batch(
    usernames=['wojespn'],
    max_results_per_user=2,
    domain='nba'
)

total_tweets = sum(len(tweets) for tweets in batch_results.values())
print(f"Result: {len(batch_results)} accounts, {total_tweets} tweets total")

for username, tweets in batch_results.items():
    print(f"\n@{username}: {len(tweets)} tweets")
    for tweet in tweets:
        print(f"  - {tweet.text[:80]}...")

if total_tweets > 0:
    print(f"\n✅ SUCCESS: Batch fetch working")
else:
    print(f"\n❌ FAILED: No tweets in batch")
    sys.exit(1)

print()
print("=" * 60)
print("Budget Status")
print("=" * 60)
budget = adapter.get_budget_status()
print(f"Total used: {budget['total_used']}/{budget['monthly_limit']}")
print(f"NBA: {budget['nba_used']}/{budget['nba_budget']}")
print(f"Remaining: {budget['remaining']}")
print()

print("✅ ALL TESTS PASSED!")
print(f"Total API calls made: {adapter.call_count}")
