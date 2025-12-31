#!/usr/bin/env python3
"""
RapidAPI Twitter Scraper Test Script

Tests connection to RapidAPI Twitter scraper and verifies NBA data collection.
"""

import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from sources.x_adapter import XAdapter
from core.whitelist import WhitelistManager, Tier


def main():
    print("=" * 70)
    print("RapidAPI Twitter Scraper - NBA Collection Test")
    print("=" * 70)

    # Check API key
    api_key = os.getenv("RAPIDAPI_KEY")
    if not api_key or api_key == "your_rapidapi_key_here":
        print("\n❌ ERROR: RAPIDAPI_KEY not set!")
        print("Please set it in your .env file or export it:")
        print("  export RAPIDAPI_KEY='your_key_here'")
        sys.exit(1)

    print(f"\n✓ API Key: {api_key[:10]}...{api_key[-4:]}")

    # Initialize adapter
    provider = os.getenv("RAPIDAPI_PROVIDER", "twitter-api45")
    print(f"✓ Provider: {provider}")

    x_adapter = XAdapter(api_key=api_key, provider=provider)

    if x_adapter.mock_mode:
        print("\n⚠️  WARNING: Running in MOCK mode (no real API calls)")
    else:
        print("\n✓ Live mode - will make real API calls")

    # Load whitelist
    whitelist = WhitelistManager()
    print(f"✓ Whitelist loaded: {len(whitelist.accounts)} accounts")

    # Test with Tier S accounts (top priority)
    tier_s_accounts = whitelist.get_accounts_by_tier(Tier.S)
    print(f"\n{'='*70}")
    print(f"Testing {len(tier_s_accounts)} Tier S accounts (Top Insiders)")
    print(f"{'='*70}\n")

    total_tweets = 0
    total_calls = 0

    for account in tier_s_accounts[:3]:  # Test first 3 only
        print(f"\n>>> @{account.username} ({account.account_type.value})")
        print(f"    Priority: {account.priority} | Credibility: {account.credibility}")

        try:
            tweets = x_adapter.fetch_user_timeline(
                username=account.username,
                max_results=5
            )
            total_calls += 1

            if tweets:
                print(f"    ✓ {len(tweets)} tweets fetched")
                total_tweets += len(tweets)

                for i, tweet in enumerate(tweets[:3], 1):
                    print(f"\n    [{i}] {tweet.created_at.strftime('%m/%d %H:%M')}")
                    print(f"        {tweet.text[:150]}...")
                    print(f"        ♥ {tweet.like_count} | ⟲ {tweet.retweet_count}")
            else:
                print(f"    ⚠️  No tweets found")

        except Exception as e:
            print(f"    ❌ Error: {e}")

    # Summary
    print(f"\n{'='*70}")
    print("Test Summary")
    print(f"{'='*70}")
    print(f"API Calls:     {total_calls}")
    print(f"Tweets Found:  {total_tweets}")
    print(f"Adapter Stats: {x_adapter.get_stats()}")

    if not x_adapter.mock_mode and total_tweets > 0:
        print("\n✓ SUCCESS: RapidAPI connection verified!")
        print("✓ NBA data collection is working correctly.")
    elif x_adapter.mock_mode:
        print("\n⚠️  MOCK MODE: No real API calls made")
        print("   Set RAPIDAPI_KEY to test live connection")
    else:
        print("\n⚠️  WARNING: No tweets collected")
        print("   This might be normal if accounts haven't posted recently")

    print(f"\n{'='*70}\n")


if __name__ == "__main__":
    main()
