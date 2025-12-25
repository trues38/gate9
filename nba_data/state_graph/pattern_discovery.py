"""
Pattern Discovery Engine
=========================
12월 데이터에서 숨겨진 패턴 발견
"""

import json
import pandas as pd
import os
from glob import glob
from collections import defaultdict

BASE_DIR = '/Users/js/g9/nba_data/state_graph'


def load_dec_data():
    """12월 데이터 로드"""
    pattern = os.path.join(BASE_DIR, 'snapshots', '2025*_snapshots.json')
    games = []
    for f in glob(pattern):
        with open(f) as fp:
            games.extend(json.load(fp))

    df = pd.read_csv(os.path.join(BASE_DIR, 'december_2025_results.csv'))
    df['game_id'] = df['game_id'].astype(str)

    enriched = []
    for g in games:
        match = df[df['game_id'] == g['game_id']]
        if not match.empty:
            g['result'] = {
                'home_points': int(match.iloc[0]['home_score']),
                'away_points': int(match.iloc[0]['away_score']),
                'home_win': int(match.iloc[0]['home_win']),
                'point_diff': int(match.iloc[0]['point_diff'])
            }
            enriched.append(g)

    return enriched


def find_upset_patterns(games):
    """업셋 패턴 발견 (부상자 많은데 이긴 경우)"""
    print("="*70)
    print("🎯 업셋 패턴 발견 (Underdog Wins)")
    print("="*70)

    upsets = []
    for g in games:
        home_inj = len(g['home_team']['injuries'])
        away_inj = len(g['away_team']['injuries'])

        # 부상자 더 많은데 이긴 경우
        if home_inj >= 3 and g['result']['home_win']:
            upsets.append({
                'team': g['home_team']['team_id'],
                'opponent': g['away_team']['team_id'],
                'injuries': home_inj,
                'diff': g['result']['point_diff'],
                'date': g['date'],
                'refs': g['referees'][:2]
            })

    upsets.sort(key=lambda x: x['injuries'], reverse=True)

    print(f"\n부상자 3명+ 승리 ({len(upsets)} games):\n")
    for u in upsets[:10]:
        print(f"{u['date']} | {u['team']:4s} vs {u['opponent']:4s} | "
              f"{u['injuries']}명 부상 | {u['diff']:+3d}점 승 | "
              f"심판: {', '.join(u['refs'])}")


def find_road_warrior_patterns(games):
    """원정 강팀 패턴"""
    print("\n" + "="*70)
    print("✈️  Road Warrior 패턴 (원정 강팀)")
    print("="*70)

    team_road_stats = defaultdict(lambda: {'wins': 0, 'games': 0})

    for g in games:
        away_team = g['away_team']['team_id']
        team_road_stats[away_team]['games'] += 1

        if not g['result']['home_win']:  # away win
            team_road_stats[away_team]['wins'] += 1

    filtered = {k: v for k, v in team_road_stats.items() if v['games'] >= 5}
    sorted_teams = sorted(filtered.items(),
                         key=lambda x: x[1]['wins'] / x[1]['games'],
                         reverse=True)

    print("\n원정 승률 Top 5:")
    for team, stats in sorted_teams[:5]:
        pct = stats['wins'] / stats['games'] * 100
        print(f"{team:4s}: {stats['wins']:2d}W - {stats['games']-stats['wins']:2d}L ({pct:5.1f}%)")


def find_clutch_patterns(games):
    """접전 패턴 (점수차 5점 이내)"""
    print("\n" + "="*70)
    print("🔥 클러치 게임 패턴 (5점 차 이내)")
    print("="*70)

    clutch_games = [g for g in games if abs(g['result']['point_diff']) <= 5]

    print(f"\n총 {len(clutch_games)} 클러치 게임 ({len(clutch_games)/len(games)*100:.1f}%)\n")

    # 클러치 게임에서 강한 팀
    team_clutch = defaultdict(lambda: {'wins': 0, 'games': 0})

    for g in clutch_games:
        home = g['home_team']['team_id']
        away = g['away_team']['team_id']

        team_clutch[home]['games'] += 1
        team_clutch[away]['games'] += 1

        if g['result']['home_win']:
            team_clutch[home]['wins'] += 1
        else:
            team_clutch[away]['wins'] += 1

    filtered = {k: v for k, v in team_clutch.items() if v['games'] >= 3}
    sorted_teams = sorted(filtered.items(),
                         key=lambda x: x[1]['wins'] / x[1]['games'],
                         reverse=True)

    print("클러치 승률 Top 5:")
    for team, stats in sorted_teams[:5]:
        pct = stats['wins'] / stats['games'] * 100
        print(f"{team:4s}: {stats['wins']:2d}W - {stats['games']-stats['wins']:2d}L ({pct:5.1f}%)")


def find_revenge_patterns(games):
    """리벤지 매치 패턴 (같은 팀 재대결)"""
    print("\n" + "="*70)
    print("⚡ 리벤지 매치 패턴")
    print("="*70)

    # 매치업별 그룹화
    matchups = defaultdict(list)

    for g in games:
        home = g['home_team']['team_id']
        away = g['away_team']['team_id']
        matchup = tuple(sorted([home, away]))
        matchups[matchup].append(g)

    # 2회 이상 대결
    rematches = {k: v for k, v in matchups.items() if len(v) >= 2}

    print(f"\n재대결 매치업: {len(rematches)}개\n")

    revenge_wins = 0
    total_rematches = 0

    for matchup, games_list in sorted(rematches.items(), key=lambda x: len(x[1]), reverse=True)[:10]:
        print(f"{matchup[0]} vs {matchup[1]} ({len(games_list)} games):")

        for i, g in enumerate(games_list, 1):
            winner = g['home_team']['team_id'] if g['result']['home_win'] else g['away_team']['team_id']
            diff = g['result']['point_diff']
            print(f"  {i}. {g['date']}: {winner} wins ({diff:+d})")

        # 리벤지 성공 체크 (첫 경기 패자가 다음 경기 승리)
        if len(games_list) >= 2:
            first_loser = games_list[0]['away_team']['team_id'] if games_list[0]['result']['home_win'] else games_list[0]['home_team']['team_id']
            second_winner = games_list[1]['home_team']['team_id'] if games_list[1]['result']['home_win'] else games_list[1]['away_team']['team_id']

            if first_loser == second_winner:
                revenge_wins += 1
            total_rematches += 1

        print()

    if total_rematches > 0:
        print(f"리벤지 성공률: {revenge_wins}/{total_rematches} ({revenge_wins/total_rematches*100:.1f}%)")


def find_home_court_anomalies(games):
    """홈코트 이상 패턴"""
    print("\n" + "="*70)
    print("🏠 홈코트 이상 현상")
    print("="*70)

    team_home_stats = defaultdict(lambda: {'wins': 0, 'games': 0, 'diffs': []})

    for g in games:
        home = g['home_team']['team_id']
        team_home_stats[home]['games'] += 1
        team_home_stats[home]['diffs'].append(g['result']['point_diff'])

        if g['result']['home_win']:
            team_home_stats[home]['wins'] += 1

    filtered = {k: v for k, v in team_home_stats.items() if v['games'] >= 3}

    # 홈코트 최강
    sorted_best = sorted(filtered.items(),
                        key=lambda x: x[1]['wins'] / x[1]['games'],
                        reverse=True)

    # 홈코트 최약
    sorted_worst = sorted(filtered.items(),
                         key=lambda x: x[1]['wins'] / x[1]['games'])

    print("\n홈코트 최강:")
    for team, stats in sorted_best[:5]:
        pct = stats['wins'] / stats['games'] * 100
        avg_diff = sum(stats['diffs']) / len(stats['diffs'])
        print(f"{team:4s}: {stats['wins']:2d}W - {stats['games']-stats['wins']:2d}L ({pct:5.1f}%) | Avg {avg_diff:+.1f}점")

    print("\n홈코트 최약 (홈에서도 약함):")
    for team, stats in sorted_worst[:5]:
        pct = stats['wins'] / stats['games'] * 100
        avg_diff = sum(stats['diffs']) / len(stats['diffs'])
        print(f"{team:4s}: {stats['wins']:2d}W - {stats['games']-stats['wins']:2d}L ({pct:5.1f}%) | Avg {avg_diff:+.1f}점")


def main():
    print("Loading December 2025 data...\n")
    games = load_dec_data()
    print(f"Loaded {len(games)} games\n")

    find_upset_patterns(games)
    find_road_warrior_patterns(games)
    find_clutch_patterns(games)
    find_revenge_patterns(games)
    find_home_court_anomalies(games)

    print("\n" + "="*70)
    print("✅ Pattern Discovery Complete!")
    print("="*70)


if __name__ == "__main__":
    main()
