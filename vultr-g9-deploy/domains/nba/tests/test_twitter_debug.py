#!/usr/bin/env python3
"""
Debug script to test Twitter241 API and see actual response structure
"""

import os
import sys
import requests
import json

# Set API key
os.environ['RAPIDAPI_KEY'] = 'd9fa80a403msh90d42ea87aedfbap1b38e0jsn61919080729d'

print("=" * 60)
print("Testing Twitter241 API - Get User by Username")
print("=" * 60)

# API configuration
API_HOST = "twitter241.p.rapidapi.com"
ENDPOINT = "/user"

headers = {
    "X-RapidAPI-Key": os.environ['RAPIDAPI_KEY'],
    "X-RapidAPI-Host": API_HOST
}

# Test with ShamsCharania
username = "ShamsCharania"
url = f"https://{API_HOST}{ENDPOINT}"

print(f"\nURL: {url}")
print(f"Params: username={username}")
print(f"Headers: {json.dumps({k: v[:20]+'...' if len(v) > 20 else v for k, v in headers.items()}, indent=2)}")
print("\nSending request...")

try:
    response = requests.get(
        url,
        headers=headers,
        params={"username": username},
        timeout=10
    )

    print(f"\nStatus Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")

    if response.status_code == 200:
        data = response.json()
        print("\n" + "="*60)
        print("FULL RESPONSE JSON:")
        print("="*60)
        print(json.dumps(data, indent=2, ensure_ascii=False))

        # Try to extract user ID
        print("\n" + "="*60)
        print("EXTRACTING USER ID:")
        print("="*60)

        user_id = None

        # Method 1: user.result.rest_id
        if isinstance(data, dict) and "user" in data:
            print(f"✓ Found 'user' key")
            if "result" in data["user"]:
                print(f"✓ Found 'result' key")
                if "rest_id" in data["user"]["result"]:
                    user_id = data["user"]["result"]["rest_id"]
                    print(f"✓ Found 'rest_id': {user_id}")
                else:
                    print(f"✗ No 'rest_id' in result")
                    print(f"  Available keys: {list(data['user']['result'].keys())}")
            else:
                print(f"✗ No 'result' in user")
                print(f"  Available keys: {list(data['user'].keys())}")
        else:
            print(f"✗ No 'user' key in response")
            if isinstance(data, dict):
                print(f"  Top-level keys: {list(data.keys())}")

        # Method 2: Try other common paths
        if not user_id and isinstance(data, dict):
            print("\nTrying alternative paths...")

            alternatives = [
                ("id", lambda d: d.get("id")),
                ("user_id", lambda d: d.get("user_id")),
                ("rest_id", lambda d: d.get("rest_id")),
                ("user.id", lambda d: d.get("user", {}).get("id")),
                ("user.rest_id", lambda d: d.get("user", {}).get("rest_id")),
                ("user.user_id", lambda d: d.get("user", {}).get("user_id")),
                ("data.user.rest_id", lambda d: d.get("data", {}).get("user", {}).get("rest_id")),
            ]

            for path, extractor in alternatives:
                try:
                    value = extractor(data)
                    if value:
                        print(f"  {path}: {value}")
                        if not user_id:
                            user_id = value
                except:
                    pass

        if user_id:
            print(f"\n✅ EXTRACTED USER ID: {user_id}")
        else:
            print(f"\n❌ FAILED TO EXTRACT USER ID")

    else:
        print(f"\n❌ Error {response.status_code}")
        print(f"Response: {response.text}")

except Exception as e:
    print(f"\n❌ Exception: {e}")
    import traceback
    traceback.print_exc()
