#!/usr/bin/env python3
"""
Soccer Full Season Backfill (Top 5 Leagues)
"""
import sys
sys.path.insert(0, '/Users/js/g9/scheduler')

from collectors.soccer_collector import SoccerCollector
import os
from dotenv import load_dotenv

load_dotenv()

db_path = '/Users/js/g9/scheduler/data/schedules.db'
api_key = os.getenv('FOOTBALL_API_KEY')

if not api_key:
    print("❌ FOOTBALL_API_KEY not found in .env")
    sys.exit(1)

collector = SoccerCollector(db_path, api_key)

# 2025-26 Soccer Season: Dec 2025 - May 2026 (미래 경기만)
print("⚽ 축구 5대 리그 미래 경기 백필 시작 (2025-12 ~ 2026-05)...")
print()

all_matches = []

# December 2025
print("📅 2025년 12월...")
matches = collector.fetch_month(2025, 12)
all_matches.extend(matches)

# January 2026
print("📅 2026년 1월...")
matches = collector.fetch_month(2026, 1)
all_matches.extend(matches)

# February 2026
print("📅 2026년 2월...")
matches = collector.fetch_month(2026, 2)
all_matches.extend(matches)

# March 2026
print("📅 2026년 3월...")
matches = collector.fetch_month(2026, 3)
all_matches.extend(matches)

# April 2026
print("📅 2026년 4월...")
matches = collector.fetch_month(2026, 4)
all_matches.extend(matches)

# May 2026
print("📅 2026년 5월...")
matches = collector.fetch_month(2026, 5)
all_matches.extend(matches)

print()
print(f"✅ 총 {len(all_matches)}개 경기 수집 완료!")
print()

# Save to DB
if all_matches:
    collector.save_to_db(all_matches)
    print("✅ DB 저장 완료!")
