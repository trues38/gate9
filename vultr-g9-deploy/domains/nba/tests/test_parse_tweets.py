#!/usr/bin/env python3
"""
Test parsing Twitter241 API response structure
"""

import json
from datetime import datetime

# Load the response
with open('/tmp/tweets_response.json', 'r') as f:
    data = json.load(f)

print("=" * 60)
print("Parsing Twitter241 /user-tweets Response")
print("=" * 60)

def extract_tweets_from_response(data):
    """Extract tweets from Twitter241 API response"""
    tweets = []

    # Navigate to instructions
    if not isinstance(data, dict):
        return tweets

    result = data.get('result', {})
    timeline = result.get('timeline', {})
    instructions = timeline.get('instructions', [])

    print(f"Found {len(instructions)} instructions")

    for instruction in instructions:
        instr_type = instruction.get('type', '')
        print(f"\nInstruction type: {instr_type}")

        # Check for pinned tweet (TimelinePinEntry)
        if instr_type == 'TimelinePinEntry':
            entry = instruction.get('entry', {})
            tweet = extract_tweet_from_entry(entry)
            if tweet:
                tweets.append(tweet)
                print(f"  ✓ Found pinned tweet")

        # Check for timeline entries (TimelineAddEntries)
        elif instr_type == 'TimelineAddEntries':
            entries = instruction.get('entries', [])
            print(f"  Found {len(entries)} entries")
            for entry in entries:
                tweet = extract_tweet_from_entry(entry)
                if tweet:
                    tweets.append(tweet)

        # Check for other types that might have entries
        elif 'entries' in instruction:
            entries = instruction.get('entries', [])
            for entry in entries:
                tweet = extract_tweet_from_entry(entry)
                if tweet:
                    tweets.append(tweet)

    return tweets

def extract_tweet_from_entry(entry):
    """Extract tweet data from an entry"""
    if not isinstance(entry, dict):
        return None

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
    username = user_core.get('screen_name', 'unknown')

    # Get timestamp
    created_at = legacy.get('created_at', '')

    # Get engagement
    retweet_count = legacy.get('retweet_count', 0)
    favorite_count = legacy.get('favorite_count', 0)
    reply_count = legacy.get('reply_count', 0)

    return {
        'tweet_id': tweet_id,
        'username': username,
        'text': text,
        'created_at': created_at,
        'retweet_count': retweet_count,
        'favorite_count': favorite_count,
        'reply_count': reply_count,
        'url': f"https://twitter.com/{username}/status/{tweet_id}"
    }

# Parse tweets
tweets = extract_tweets_from_response(data)

print("\n" + "=" * 60)
print(f"EXTRACTED {len(tweets)} TWEETS:")
print("=" * 60)

for i, tweet in enumerate(tweets, 1):
    print(f"\n{i}. @{tweet['username']} (ID: {tweet['tweet_id']})")
    print(f"   Time: {tweet['created_at']}")
    print(f"   Text: {tweet['text'][:100]}...")
    print(f"   Engagement: {tweet['retweet_count']} RTs, {tweet['favorite_count']} likes, {tweet['reply_count']} replies")
    print(f"   URL: {tweet['url']}")

if tweets:
    print(f"\n✅ SUCCESS: Parsed {len(tweets)} tweets")
else:
    print(f"\n❌ FAILED: No tweets parsed")
