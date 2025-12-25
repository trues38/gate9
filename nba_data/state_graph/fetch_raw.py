"""
ESPN NBA Raw Data Fetcher
=========================
Phase 1: ESPN API에서 Raw 데이터를 수집하여 JSON으로 저장

Usage:
    python fetch_raw.py --date 20241216
    python fetch_raw.py --date 20241201 --days 30
"""

import requests
import json
import os
import time
import argparse
from datetime import datetime, timedelta
from typing import Optional, Dict, List

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(BASE_DIR, "raw")
os.makedirs(RAW_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}

# ESPN Team ID Mapping
TEAM_IDS = {
    "ATL": 1, "BOS": 2, "NOP": 3, "CHI": 4, "CLE": 5,
    "DAL": 6, "DEN": 7, "DET": 8, "GSW": 9, "HOU": 10,
    "IND": 11, "LAC": 12, "LAL": 13, "MIA": 14, "MIL": 15,
    "MIN": 16, "BKN": 17, "NYK": 18, "ORL": 19, "PHI": 20,
    "PHX": 21, "POR": 22, "SAC": 23, "SAS": 24, "OKC": 25,
    "UTA": 26, "WAS": 27, "TOR": 28, "MEM": 29, "CHA": 30
}


def fetch_scoreboard(date_str: str) -> Optional[Dict]:
    """날짜별 경기 일정 조회"""
    url = f"http://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date_str}"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"  [ERROR] Scoreboard fetch failed: {e}")
        return None


def fetch_summary(game_id: str) -> Optional[Dict]:
    """경기 상세 정보 조회 (심판, 부상, 스탯)"""
    url = f"http://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={game_id}"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"  [ERROR] Summary fetch failed for {game_id}: {e}")
        return None


def fetch_roster(team_id: int) -> Optional[Dict]:
    """팀 로스터 조회"""
    url = f"http://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{team_id}/roster"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"  [ERROR] Roster fetch failed for team {team_id}: {e}")
        return None


def save_raw(data: Dict, filename: str) -> str:
    """Raw JSON 저장"""
    filepath = os.path.join(RAW_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return filepath


def collect_date(date_str: str) -> List[Dict]:
    """특정 날짜의 모든 경기 데이터 수집"""
    print(f"\n{'='*50}")
    print(f"Collecting: {date_str}")
    print(f"{'='*50}")

    games_collected = []

    # 1. Scoreboard (경기 목록)
    scoreboard = fetch_scoreboard(date_str)
    if not scoreboard:
        print("  No scoreboard data")
        return []

    events = scoreboard.get("events", [])
    print(f"  Found {len(events)} games")

    if not events:
        return []

    # Save scoreboard
    save_raw(scoreboard, f"{date_str}_scoreboard.json")

    # 2. 각 경기별 Summary
    teams_to_fetch = set()

    for event in events:
        game_id = event.get("id")
        name = event.get("shortName", "Unknown")
        status = event.get("status", {}).get("type", {}).get("state", "unknown")

        print(f"  > Game {game_id}: {name} [{status}]")

        # Summary 조회
        time.sleep(0.2)  # Rate limiting
        summary = fetch_summary(game_id)

        if summary:
            save_raw(summary, f"{date_str}_game_{game_id}.json")

            # 참여 팀 추출
            comps = event.get("competitions", [{}])[0].get("competitors", [])
            for comp in comps:
                team_abbr = comp.get("team", {}).get("abbreviation")
                if team_abbr and team_abbr in TEAM_IDS:
                    teams_to_fetch.add(team_abbr)

            games_collected.append({
                "game_id": game_id,
                "date": date_str,
                "matchup": name,
                "status": status
            })

    # 3. 관련 팀 Roster (부상 정보 보완)
    print(f"  > Fetching rosters for {len(teams_to_fetch)} teams...")

    for team_abbr in teams_to_fetch:
        team_id = TEAM_IDS.get(team_abbr)
        if team_id:
            time.sleep(0.2)
            roster = fetch_roster(team_id)
            if roster:
                save_raw(roster, f"{date_str}_roster_{team_abbr}.json")

    print(f"  Collected {len(games_collected)} games successfully")
    return games_collected


def main():
    parser = argparse.ArgumentParser(description="ESPN NBA Raw Data Fetcher")
    parser.add_argument("--date", type=str, required=True, help="Start date (YYYYMMDD)")
    parser.add_argument("--days", type=int, default=1, help="Number of days to collect")

    args = parser.parse_args()

    start_date = datetime.strptime(args.date, "%Y%m%d")

    all_games = []
    for i in range(args.days):
        current_date = start_date + timedelta(days=i)
        date_str = current_date.strftime("%Y%m%d")
        games = collect_date(date_str)
        all_games.extend(games)

    print(f"\n{'='*50}")
    print(f"TOTAL: Collected {len(all_games)} games across {args.days} days")
    print(f"{'='*50}")

    # 수집 결과 요약 저장
    summary_file = os.path.join(RAW_DIR, f"collection_summary_{args.date}.json")
    with open(summary_file, "w") as f:
        json.dump({
            "start_date": args.date,
            "days": args.days,
            "total_games": len(all_games),
            "games": all_games
        }, f, indent=2)

    print(f"Summary saved to: {summary_file}")


if __name__ == "__main__":
    main()
