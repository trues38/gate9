#!/usr/bin/env python3
"""
NBA Full Season Backfill with Real Game Times
"""
import sys
sys.path.insert(0, '/Users/js/g9/scheduler')

from collectors.nba_collector import NBACollector
from datetime import datetime

db_path = '/Users/js/g9/scheduler/data/schedules.db'
collector = NBACollector(db_path)

# 2025-26 NBA Season: Oct 2025 - Jun 2026
print("🏀 NBA 2025-26 시즌 백필 시작...")
print()

all_games = []

# October 2025
print("📅 2025년 10월...")
games = collector.fetch_month(2025, 10)
all_games.extend(games)

# November 2025
print("📅 2025년 11월...")
games = collector.fetch_month(2025, 11)
all_games.extend(games)

# December 2025
print("📅 2025년 12월...")
games = collector.fetch_month(2025, 12)
all_games.extend(games)

# January 2026
print("📅 2026년 1월...")
games = collector.fetch_month(2026, 1)
all_games.extend(games)

# February 2026
print("📅 2026년 2월...")
games = collector.fetch_month(2026, 2)
all_games.extend(games)

# March 2026
print("📅 2026년 3월...")
games = collector.fetch_month(2026, 3)
all_games.extend(games)

# April 2026
print("📅 2026년 4월...")
games = collector.fetch_month(2026, 4)
all_games.extend(games)

# May 2026
print("📅 2026년 5월...")
games = collector.fetch_month(2026, 5)
all_games.extend(games)

# June 2026
print("📅 2026년 6월...")
games = collector.fetch_month(2026, 6)
all_games.extend(games)

print()
print(f"✅ 총 {len(all_games)}개 경기 수집 완료!")
print()

# Save to DB
if all_games:
    collector.save_to_db(all_games)
    print("✅ DB 저장 완료!")
