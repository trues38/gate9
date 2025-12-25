"""
State-Result Analysis Engine
============================
State Snapshot + Rdata를 결합하여 상태가 결과에 미치는 영향 분석

Usage:
    python analyze_state_impact.py --month 202412
"""

import json
import pandas as pd
import os
from glob import glob
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SNAPSHOT_DIR = os.path.join(BASE_DIR, "snapshots")
RESULTS_PATH = os.path.join(BASE_DIR, "december_results.csv")


def load_snapshots(month_str: str = "202412"):
    """특정 월의 모든 스냅샷 로드"""
    pattern = os.path.join(SNAPSHOT_DIR, f"{month_str}*_snapshots.json")
    all_games = []

    for filepath in sorted(glob(pattern)):
        with open(filepath, 'r') as f:
            games = json.load(f)
            all_games.extend(games)

    return all_games


def load_results():
    """12월 경기 결과 로드"""
    df = pd.read_csv(RESULTS_PATH)
    df['game_id'] = df['game_id'].astype(str)  # String으로 변환
    return df


def normalize_team_name(name: str) -> str:
    """팀명 정규화 (Rdata ↔ Snapshot 매칭용)"""
    # Rdata: "Atlanta Hawks", Snapshot: "ATL"
    mapping = {
        "ATL": "Atlanta Hawks",
        "BOS": "Boston Celtics",
        "BKN": "Brooklyn Nets",
        "CHA": "Charlotte Hornets",
        "CHI": "Chicago Bulls",
        "CLE": "Cleveland Cavaliers",
        "DAL": "Dallas Mavericks",
        "DEN": "Denver Nuggets",
        "DET": "Detroit Pistons",
        "GSW": "Golden State Warriors",
        "GS": "Golden State Warriors",
        "HOU": "Houston Rockets",
        "IND": "Indiana Pacers",
        "LAC": "Los Angeles Clippers",
        "LAL": "Los Angeles Lakers",
        "MEM": "Memphis Grizzlies",
        "MIA": "Miami Heat",
        "MIL": "Milwaukee Bucks",
        "MIN": "Minnesota Timberwolves",
        "NOP": "New Orleans Pelicans",
        "NO": "New Orleans Pelicans",
        "NYK": "New York Knicks",
        "NY": "New York Knicks",
        "OKC": "Oklahoma City Thunder",
        "ORL": "Orlando Magic",
        "PHI": "Philadelphia 76ers",
        "PHX": "Phoenix Suns",
        "POR": "Portland Trail Blazers",
        "SAC": "Sacramento Kings",
        "SAS": "San Antonio Spurs",
        "SA": "San Antonio Spurs",
        "TOR": "Toronto Raptors",
        "UTA": "Utah Jazz",
        "UTAH": "Utah Jazz",
        "WAS": "Washington Wizards",
        "WSH": "Washington Wizards",
    }
    return mapping.get(name, name)


def enrich_snapshots_with_results(snapshots, results_df):
    """스냅샷에 경기 결과 추가"""
    enriched = []

    for game in snapshots:
        game_id = game['game_id']

        # 결과 매칭
        match = results_df[results_df['game_id'] == game_id]

        if not match.empty:
            result = match.iloc[0]
            game['result'] = {
                'home_points': int(result['home_score']),
                'away_points': int(result['away_score']),
                'home_win': int(result['home_win']),
                'point_diff': int(result['point_diff'])
            }
            enriched.append(game)

    return enriched


def analyze_rest_impact(enriched_games):
    """휴식일이 승률에 미치는 영향"""
    print("\n" + "="*60)
    print("📊 휴식일 영향 분석 (Rest Days Impact)")
    print("="*60)

    rest_stats = {
        0: {'games': 0, 'wins': 0},  # Back-to-back
        1: {'games': 0, 'wins': 0},
        2: {'games': 0, 'wins': 0},
        3: {'games': 0, 'wins': 0},  # 3+ days
    }

    for game in enriched_games:
        home_rest = game['home_team']['rest_days']
        away_rest = game['away_team']['rest_days']
        home_win = game['result']['home_win']

        # 홈팀 휴식일
        rest_key = min(home_rest, 3)
        rest_stats[rest_key]['games'] += 1
        if home_win:
            rest_stats[rest_key]['wins'] += 1

    for rest_days, stats in sorted(rest_stats.items()):
        if stats['games'] > 0:
            win_pct = stats['wins'] / stats['games'] * 100
            label = "Back-to-back" if rest_days == 0 else f"{rest_days} day(s) rest"
            print(f"{label:20s}: {stats['wins']:3d}W - {stats['games']-stats['wins']:3d}L ({win_pct:5.1f}%)")


def analyze_injury_impact(enriched_games):
    """부상자 수가 승률에 미치는 영향"""
    print("\n" + "="*60)
    print("🚑 부상자 영향 분석 (Injury Impact)")
    print("="*60)

    injury_buckets = {
        0: {'games': 0, 'wins': 0},
        1: {'games': 0, 'wins': 0},
        2: {'games': 0, 'wins': 0},
        3: {'games': 0, 'wins': 0},  # 3+ injuries
    }

    for game in enriched_games:
        inj_count = len(game['home_team']['injuries'])
        bucket = min(inj_count, 3)
        injury_buckets[bucket]['games'] += 1

        if game['result']['home_win']:
            injury_buckets[bucket]['wins'] += 1

    for count, stats in sorted(injury_buckets.items()):
        if stats['games'] > 0:
            win_pct = stats['wins'] / stats['games'] * 100
            label = f"{count}+ injuries" if count == 3 else f"{count} injuries"
            print(f"{label:20s}: {stats['wins']:3d}W - {stats['games']-stats['wins']:3d}L ({win_pct:5.1f}%)")


def analyze_referee_impact(enriched_games):
    """심판별 홈팀 승률"""
    print("\n" + "="*60)
    print("👔 심판 영향 분석 (Referee Impact - Top 10)")
    print("="*60)

    ref_stats = {}

    for game in enriched_games:
        for ref in game['referees']:
            if ref not in ref_stats:
                ref_stats[ref] = {'games': 0, 'home_wins': 0}

            ref_stats[ref]['games'] += 1
            if game['result']['home_win']:
                ref_stats[ref]['home_wins'] += 1

    # 경기 수 5개 이상만
    filtered = {k: v for k, v in ref_stats.items() if v['games'] >= 5}

    # 정렬
    sorted_refs = sorted(filtered.items(), key=lambda x: x[1]['games'], reverse=True)

    for ref, stats in sorted_refs[:10]:
        win_pct = stats['home_wins'] / stats['games'] * 100
        print(f"{ref:25s}: {stats['games']:2d} games | Home win: {win_pct:5.1f}%")


def analyze_combined_factors(enriched_games):
    """복합 요인 분석"""
    print("\n" + "="*60)
    print("⚡ 복합 요인 분석 (Combined Factors)")
    print("="*60)

    # Back-to-back + 부상자 2명 이상
    b2b_injured = [g for g in enriched_games
                   if g['home_team']['rest_days'] == 0
                   and len(g['home_team']['injuries']) >= 2]

    if b2b_injured:
        wins = sum(1 for g in b2b_injured if g['result']['home_win'])
        total = len(b2b_injured)
        print(f"Back-to-back + 2+ injuries: {wins}W - {total-wins}L ({wins/total*100:.1f}%)")

    # 원정 + back-to-back
    away_b2b = [g for g in enriched_games
                if g['away_team']['rest_days'] == 0]

    if away_b2b:
        # 원정팀이 져야 홈팀이 이김
        away_losses = sum(1 for g in away_b2b if g['result']['home_win'])
        total = len(away_b2b)
        print(f"Away team back-to-back: {away_losses}W (home) - {total-away_losses}L ({away_losses/total*100:.1f}%)")


def main():
    print("Loading snapshots...")
    snapshots = load_snapshots("202412")
    print(f"  Loaded {len(snapshots)} games from December 2024")

    print("Loading results...")
    results = load_results()
    print(f"  Loaded {len(results)} game results")

    print("Enriching snapshots with results...")
    enriched = enrich_snapshots_with_results(snapshots, results)
    print(f"  Matched {len(enriched)} games with results")

    if not enriched:
        print("\n⚠️ No matches found. Check team name mapping or date range.")
        return

    # 분석 실행
    analyze_rest_impact(enriched)
    analyze_injury_impact(enriched)
    analyze_referee_impact(enriched)
    analyze_combined_factors(enriched)

    print("\n" + "="*60)
    print(f"✅ Analysis complete ({len(enriched)} games analyzed)")
    print("="*60)


if __name__ == "__main__":
    main()
