"""
State Snapshot Builder
======================
Raw ESPN 데이터를 통합된 State Snapshot JSON으로 변환

Usage:
    python build_snapshot.py --date 20241216
    python build_snapshot.py --date 20241201 --days 31
"""

import json
import os
import glob
import argparse
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(BASE_DIR, "raw")
SNAPSHOT_DIR = os.path.join(BASE_DIR, "snapshots")
os.makedirs(SNAPSHOT_DIR, exist_ok=True)


def load_json(filepath: str) -> Optional[Dict]:
    """JSON 파일 로드"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"  [WARN] Failed to load {filepath}: {e}")
        return None


def extract_officials(game_data: Dict) -> List[str]:
    """심판 정보 추출"""
    officials = []
    game_info = game_data.get("gameInfo", {})
    for official in game_info.get("officials", []):
        officials.append(official.get("fullName", "Unknown"))
    return officials


def extract_injuries(game_data: Dict, team_abbr: str) -> List[str]:
    """팀별 부상자 추출"""
    injuries_list = []
    for team_inj in game_data.get("injuries", []):
        team_name = team_inj.get("team", {}).get("abbreviation", "")
        if team_name == team_abbr or team_abbr in team_inj.get("team", {}).get("displayName", ""):
            for inj in team_inj.get("injuries", []):
                player = inj.get("athlete", {}).get("displayName", "Unknown")
                status = inj.get("status", "Unknown")
                injuries_list.append(f"{player} - {status}")
    return injuries_list


def extract_roster_injuries(roster_data: Dict) -> List[str]:
    """로스터에서 부상자 추출 (보완용)"""
    injuries = []
    for athlete in roster_data.get("athletes", []):
        player_injuries = athlete.get("injuries", [])
        if player_injuries:
            name = athlete.get("displayName", "Unknown")
            status = player_injuries[0].get("status", "Unknown")
            if status.lower() not in ["healthy", ""]:
                injuries.append(f"{name} - {status}")
    return injuries


def extract_record(game_data: Dict, team_abbr: str) -> str:
    """팀 전적 추출 (header.competitions.competitors.record에서)"""
    header = game_data.get("header", {})
    competitions = header.get("competitions", [{}])[0]
    competitors = competitions.get("competitors", [])

    for comp in competitors:
        abbr = comp.get("team", {}).get("abbreviation", "")
        if abbr == team_abbr:
            records = comp.get("record", [])
            for rec in records:
                if rec.get("type") == "total":
                    return rec.get("summary", "N/A")
    return "N/A"


def extract_lineup(roster_data: Dict, limit: int = 8) -> List[str]:
    """주요 선수 추출 (로스터 기준)"""
    lineup = []
    for athlete in roster_data.get("athletes", []):
        if len(lineup) >= limit:
            break
        # 부상자 제외
        injuries = athlete.get("injuries", [])
        is_out = any(i.get("status", "").lower() in ["out", "out for season"] for i in injuries)
        if not is_out:
            lineup.append(athlete.get("displayName", "Unknown"))
    return lineup


def calculate_rest_days(date_str: str, team_abbr: str, all_games: Dict[str, List]) -> int:
    """휴식일 계산 (간단 버전: 전날 경기 여부만 체크)"""
    target_date = datetime.strptime(date_str, "%Y%m%d")

    # 최근 3일 체크
    for days_back in range(1, 4):
        prev_date = target_date - timedelta(days=days_back)
        prev_str = prev_date.strftime("%Y%m%d")

        if prev_str in all_games:
            for game in all_games[prev_str]:
                if team_abbr in game.get("matchup", ""):
                    return days_back - 1  # 0 = back-to-back, 1 = 1일 휴식

    return 3  # 3일 이상 휴식


def generate_state_notes(home_state: Dict, away_state: Dict) -> List[str]:
    """상태 기반 주요 노트 생성"""
    notes = []

    # Back-to-back 체크
    if away_state.get("rest_days", 0) == 0:
        notes.append(f"{away_state['team_id']} back-to-back")
    if home_state.get("rest_days", 0) == 0:
        notes.append(f"{home_state['team_id']} back-to-back")

    # 주요 부상자
    for inj in away_state.get("injuries", [])[:2]:
        if "OUT" in inj.upper() or "Out" in inj:
            notes.append(inj)
    for inj in home_state.get("injuries", [])[:2]:
        if "OUT" in inj.upper() or "Out" in inj:
            notes.append(inj)

    return notes


def build_game_snapshot(date_str: str, game_id: str, all_games: Dict[str, List]) -> Optional[Dict]:
    """단일 경기 State Snapshot 생성"""

    # Load game summary
    game_file = os.path.join(RAW_DIR, f"{date_str}_game_{game_id}.json")
    game_data = load_json(game_file)

    if not game_data:
        return None

    # Extract header info
    header = game_data.get("header", {})
    competitions = header.get("competitions", [{}])[0]
    competitors = competitions.get("competitors", [])

    home_comp = next((c for c in competitors if c.get("homeAway") == "home"), {})
    away_comp = next((c for c in competitors if c.get("homeAway") == "away"), {})

    home_abbr = home_comp.get("team", {}).get("abbreviation", "UNK")
    away_abbr = away_comp.get("team", {}).get("abbreviation", "UNK")

    matchup = f"{away_abbr} @ {home_abbr}"

    # Load rosters
    home_roster_file = os.path.join(RAW_DIR, f"{date_str}_roster_{home_abbr}.json")
    away_roster_file = os.path.join(RAW_DIR, f"{date_str}_roster_{away_abbr}.json")

    home_roster = load_json(home_roster_file) or {}
    away_roster = load_json(away_roster_file) or {}

    # Build team states
    home_injuries = extract_injuries(game_data, home_abbr)
    if not home_injuries:
        home_injuries = extract_roster_injuries(home_roster)

    away_injuries = extract_injuries(game_data, away_abbr)
    if not away_injuries:
        away_injuries = extract_roster_injuries(away_roster)

    home_state = {
        "team_id": home_abbr,
        "record": extract_record(game_data, home_abbr),
        "rest_days": calculate_rest_days(date_str, home_abbr, all_games),
        "injuries": home_injuries[:5],  # 상위 5명만
        "lineup": extract_lineup(home_roster)
    }

    away_state = {
        "team_id": away_abbr,
        "record": extract_record(game_data, away_abbr),
        "rest_days": calculate_rest_days(date_str, away_abbr, all_games),
        "injuries": away_injuries[:5],
        "lineup": extract_lineup(away_roster)
    }

    # Build snapshot
    snapshot = {
        "date": f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}",
        "game_id": game_id,
        "matchup": matchup,
        "home_team": home_state,
        "away_team": away_state,
        "referees": extract_officials(game_data),
        "state_notes": generate_state_notes(home_state, away_state)
    }

    return snapshot


def build_date_snapshots(date_str: str, all_games: Dict[str, List]) -> List[Dict]:
    """날짜별 모든 경기 Snapshot 생성"""
    print(f"\nBuilding snapshots for {date_str}...")

    # Scoreboard에서 경기 목록 추출
    scoreboard_file = os.path.join(RAW_DIR, f"{date_str}_scoreboard.json")
    scoreboard = load_json(scoreboard_file)

    if not scoreboard:
        print(f"  No scoreboard found for {date_str}")
        return []

    events = scoreboard.get("events", [])
    snapshots = []

    for event in events:
        game_id = event.get("id")
        snapshot = build_game_snapshot(date_str, game_id, all_games)
        if snapshot:
            snapshots.append(snapshot)
            print(f"  > {snapshot['matchup']}: OK")

    return snapshots


def build_games_index(start_date: str, days: int) -> Dict[str, List]:
    """전체 기간 경기 인덱스 구축 (휴식일 계산용)"""
    all_games = {}
    start = datetime.strptime(start_date, "%Y%m%d")

    for i in range(days + 7):  # 앞뒤 여유
        current = start + timedelta(days=i - 3)
        date_str = current.strftime("%Y%m%d")

        scoreboard_file = os.path.join(RAW_DIR, f"{date_str}_scoreboard.json")
        scoreboard = load_json(scoreboard_file)

        if scoreboard:
            games = []
            for event in scoreboard.get("events", []):
                games.append({
                    "game_id": event.get("id"),
                    "matchup": event.get("shortName", "")
                })
            all_games[date_str] = games

    return all_games


def main():
    parser = argparse.ArgumentParser(description="State Snapshot Builder")
    parser.add_argument("--date", type=str, required=True, help="Start date (YYYYMMDD)")
    parser.add_argument("--days", type=int, default=1, help="Number of days")

    args = parser.parse_args()

    # 경기 인덱스 구축
    print("Building games index for rest day calculation...")
    all_games = build_games_index(args.date, args.days)
    print(f"  Indexed {sum(len(g) for g in all_games.values())} games")

    # 날짜별 스냅샷 생성
    start_date = datetime.strptime(args.date, "%Y%m%d")
    all_snapshots = []

    for i in range(args.days):
        current = start_date + timedelta(days=i)
        date_str = current.strftime("%Y%m%d")
        snapshots = build_date_snapshots(date_str, all_games)
        all_snapshots.extend(snapshots)

        # 날짜별 저장
        if snapshots:
            output_file = os.path.join(SNAPSHOT_DIR, f"{date_str}_snapshots.json")
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(snapshots, f, indent=2, ensure_ascii=False)

    # 전체 요약
    print(f"\n{'='*50}")
    print(f"TOTAL: Built {len(all_snapshots)} game snapshots")
    print(f"Output: {SNAPSHOT_DIR}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
