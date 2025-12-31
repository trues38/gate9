#!/usr/bin/env python3
"""
Debug script to test Twitter241 API user-tweets endpoint
"""

import os
import requests
import json

os.environ['RAPIDAPI_KEY'] = 'd9fa80a403msh90d42ea87aedfbap1b38e0jsn61919080729d'

print("=" * 60)
print("Testing Twitter241 API - Get User Tweets")
print("=" * 60)

API_HOST = "twitter241.p.rapidapi.com"
ENDPOINT = "/user-tweets"

headers = {
    "X-RapidAPI-Key": os.environ['RAPIDAPI_KEY'],
    "X-RapidAPI-Host": API_HOST
}

# Use Shams' user ID from previous test
user_id = "178580925"
url = f"https://{API_HOST}{ENDPOINT}"

print(f"\nURL: {url}")
print(f"Params: user={user_id}, count=3")
print("\nSending request...")

try:
    response = requests.get(
        url,
        headers=headers,
        params={"user": user_id, "count": 3},
        timeout=15
    )

    print(f"\nStatus Code: {response.status_code}")
    print(f"Content-Length: {len(response.text)} bytes")

    if response.status_code == 200:
        data = response.json()

        # Show structure overview
        print("\n" + "="*60)
        print("RESPONSE STRUCTURE:")
        print("="*60)

        if isinstance(data, dict):
            print(f"Type: dict")
            print(f"Top-level keys: {list(data.keys())}")

            # Navigate to tweets
            if "timeline" in data:
                print(f"\n'timeline' found, type: {type(data['timeline'])}")
                if isinstance(data['timeline'], list):
                    print(f"Timeline length: {len(data['timeline'])}")
                    if len(data['timeline']) > 0:
                        print(f"First item keys: {list(data['timeline'][0].keys())}")
                elif isinstance(data['timeline'], dict):
                    print(f"Timeline keys: {list(data['timeline'].keys())}")

            if "tweets" in data:
                print(f"\n'tweets' found, type: {type(data['tweets'])}")
                if isinstance(data['tweets'], list):
                    print(f"Tweets length: {len(data['tweets'])}")

            if "data" in data:
                print(f"\n'data' found, type: {type(data['data'])}")
                if isinstance(data['data'], dict):
                    print(f"Data keys: {list(data['data'].keys())}")

            # Check nested structures
            for key in ['result', 'user', 'timeline', 'tweets', 'data']:
                if key in data:
                    nested = data[key]
                    if isinstance(nested, dict):
                        for subkey in ['timeline', 'tweets', 'data', 'instructions']:
                            if subkey in nested:
                                print(f"\n'{key}.{subkey}' found, type: {type(nested[subkey])}")
                                if isinstance(nested[subkey], list):
                                    print(f"  Length: {len(nested[subkey])}")
                                    if len(nested[subkey]) > 0:
                                        print(f"  First item type: {type(nested[subkey][0])}")
                                        if isinstance(nested[subkey][0], dict):
                                            print(f"  First item keys: {list(nested[subkey][0].keys())[:10]}")

        elif isinstance(data, list):
            print(f"Type: list")
            print(f"Length: {len(data)}")
            if len(data) > 0:
                print(f"First item type: {type(data[0])}")
                if isinstance(data[0], dict):
                    print(f"First item keys: {list(data[0].keys())}")

        # Show first tweet if we can find it
        print("\n" + "="*60)
        print("TRYING TO FIND A TWEET:")
        print("="*60)

        # Save full response to file for inspection
        with open('/tmp/tweets_response.json', 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Full response saved to: /tmp/tweets_response.json")

        # Try common paths
        tweet_found = False
        paths_to_try = [
            ("data (root)", lambda: data if isinstance(data, list) else None),
            ("timeline", lambda: data.get('timeline') if isinstance(data, dict) else None),
            ("tweets", lambda: data.get('tweets') if isinstance(data, dict) else None),
            ("data.timeline", lambda: data.get('data', {}).get('timeline') if isinstance(data, dict) else None),
            ("data.tweets", lambda: data.get('data', {}).get('tweets') if isinstance(data, dict) else None),
            ("result.timeline", lambda: data.get('result', {}).get('timeline') if isinstance(data, dict) else None),
        ]

        for path_name, extractor in paths_to_try:
            try:
                tweet_list = extractor()
                if tweet_list and isinstance(tweet_list, list) and len(tweet_list) > 0:
                    print(f"\n✓ Found tweets at: {path_name}")
                    print(f"  Count: {len(tweet_list)}")
                    first_tweet = tweet_list[0]
                    if isinstance(first_tweet, dict):
                        print(f"  First tweet keys: {list(first_tweet.keys())[:15]}")
                        # Try to extract text
                        text = first_tweet.get('text') or first_tweet.get('full_text') or first_tweet.get('content')
                        if text:
                            print(f"  Text: {text[:100]}...")
                            tweet_found = True
                            break
            except:
                pass

        if not tweet_found:
            print("\n❌ Could not find tweets in standard locations")
            print("Please check /tmp/tweets_response.json manually")

    else:
        print(f"\n❌ Error {response.status_code}")
        print(f"Response: {response.text[:500]}")

except Exception as e:
    print(f"\n❌ Exception: {e}")
    import traceback
    traceback.print_exc()
