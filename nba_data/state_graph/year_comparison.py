"""
Year-over-Year Comparison Engine
=================================
2024-25 vs 2023-24 시즌 비교 분석
- 같은 월 비교 (10월, 11월, 12월)
- 팀별 성장/하락
- 심판 패턴 변화
- 시스템 변화 감지
"""

import json
import pandas as pd
import os
from glob import glob
from collections import defaultdict

BASE_DIR = '/Users/js/g9/nba_data/state_graph'


def load_year_data(year_prefix):
    """특정 연도 데이터 로드 (2024 or 2025)"""
    pattern = os.path.join(BASE_DIR, 'snapshots', f'{year_prefix}*_snapshots.json')
    games = []

    for f in sorted(glob(pattern)):
        with open(f) as fp:
            games.extend(json.load(fp))

    # Results 로드
    results_pattern = os.path.join(BASE_DIR, 'raw', f'{year_prefix}*_game_*.json')
    results_files = glob(results_pattern)

    all_results = []
    for filepath in results_files:
        with open(filepath) as f:
            data = json.load(f)

        header = data.get('header', {})
        game_id = header.get('id')
        comps = header.get('competitions', [{}])[0]
        competitors = comps.get('competitors', [])
        game_date = comps.get('date', '').split('T')[0]

        home = next((c for c in competitors if c.get('homeAway') == 'home'), {})
        away = next((c for c in competitors if c.get('homeAway') == 'away'), {})

        home_score = int(home.get('score', 0))
        away_score = int(away.get('score', 0))
        status = comps.get('status', {}).get('type', {}).get('state', '')

        if status == 'post' and home_score > 0:
            all_results.append({
                'game_id': str(game_id),
                'home_score': home_score,
                'away_score': away_score,
                'home_win': 1 if home_score > away_score else 0,
                'point_diff': home_score - away_score
            })

    results_df = pd.DataFrame(all_results)

    # Enrich
    enriched = []
    for g in games:
        match = results_df[results_df['game_id'] == g['game_id']]
        if not match.empty:
            g['result'] = {
                'home_points': int(match.iloc[0]['home_score']),
                'away_points': int(match.iloc[0]['away_score']),
                'home_win': int(match.iloc[0]['home_win']),
                'point_diff': int(match.iloc[0]['point_diff'])
            }
            enriched.append(g)

    return enriched


def compare_monthly_patterns(games_2024, games_2025):
    """월별 패턴 비교"""
    print("="*70)
    print("📅 월별 패턴 비교 (2024 vs 2025)")
    print("="*70)

    def get_monthly_stats(games):
        monthly = defaultdict(lambda: {
            'games': 0, 'home_wins': 0, 'b2b_games': 0, 'b2b_wins': 0, 'total_diff': 0
        })

        for g in games:
            month = g['date'][5:7]  # MM
            stats = monthly[month]

            stats['games'] += 1
            stats['total_diff'] += g['result']['point_diff']

            if g['result']['home_win']:
                stats['home_wins'] += 1

            if g['home_team']['rest_days'] == 0:
                stats['b2b_games'] += 1
                if g['result']['home_win']:
                    stats['b2b_wins'] += 1

        return monthly

    stats_2024 = get_monthly_stats(games_2024)
    stats_2025 = get_monthly_stats(games_2025)

    months = ['10', '11', '12']
    month_names = {'10': 'Oct', '11': 'Nov', '12': 'Dec'}

    print(f"\n{'Month':<6} {'Year':<5} {'Games':>6} {'Home%':>7} {'B2B%':>7} {'AvgDiff':>9}")
    print("-" * 70)

    for month in months:
        for year, stats_dict in [('2024', stats_2024), ('2025', stats_2025)]:
            if month in stats_dict:
                stats = stats_dict[month]
                home_pct = stats['home_wins'] / stats['games'] * 100
                b2b_pct = stats['b2b_wins'] / stats['b2b_games'] * 100 if stats['b2b_games'] > 0 else 0
                avg_diff = stats['total_diff'] / stats['games']

                print(f"{month_names[month]:<6} {year:<5} {stats['games']:>6} "
                      f"{home_pct:>6.1f}% {b2b_pct:>6.1f}% {avg_diff:>+8.1f}")
        print()


def compare_team_evolution(games_2024, games_2025):
    """팀별 성장/하락 비교"""
    print("="*70)
    print("📊 팀별 성장/하락 (2024 → 2025)")
    print("="*70)

    def get_team_records(games):
        records = defaultdict(lambda: {'wins': 0, 'games': 0})
        for g in games:
            home = g['home_team']['team_id']
            away = g['away_team']['team_id']

            records[home]['games'] += 1
            records[away]['games'] += 1

            if g['result']['home_win']:
                records[home]['wins'] += 1
            else:
                records[away]['wins'] += 1

        return {team: stats['wins'] / stats['games'] * 100
                for team, stats in records.items() if stats['games'] >= 10}

    pcts_2024 = get_team_records(games_2024)
    pcts_2025 = get_team_records(games_2025)

    changes = []
    for team in set(pcts_2024.keys()) & set(pcts_2025.keys()):
        change = pcts_2025[team] - pcts_2024[team]
        changes.append({
            'team': team,
            'pct_2024': pcts_2024[team],
            'pct_2025': pcts_2025[team],
            'change': change
        })

    sorted_changes = sorted(changes, key=lambda x: x['change'], reverse=True)

    print("\n🚀 가장 성장한 팀 (Top 10):")
    for i, tc in enumerate(sorted_changes[:10], 1):
        print(f"{i:2d}. {tc['team']:4s}: {tc['pct_2024']:5.1f}% → "
              f"{tc['pct_2025']:5.1f}% ({tc['change']:+5.1f}%)")

    print("\n📉 가장 하락한 팀 (Bottom 10):")
    for i, tc in enumerate(sorted_changes[-10:], 1):
        print(f"{i:2d}. {tc['team']:4s}: {tc['pct_2024']:5.1f}% → "
              f"{tc['pct_2025']:5.1f}% ({tc['change']:+5.1f}%)")


def compare_referee_patterns(games_2024, games_2025):
    """심판 패턴 변화"""
    print("\n" + "="*70)
    print("👔 심판 패턴 변화")
    print("="*70)

    def get_ref_stats(games):
        ref_stats = defaultdict(lambda: {'games': 0, 'home_wins': 0})

        for g in games:
            for ref in g['referees']:
                ref_stats[ref]['games'] += 1
                if g['result']['home_win']:
                    ref_stats[ref]['home_wins'] += 1

        return {ref: stats['home_wins'] / stats['games'] * 100
                for ref, stats in ref_stats.items() if stats['games'] >= 15}

    pcts_2024 = get_ref_stats(games_2024)
    pcts_2025 = get_ref_stats(games_2025)

    # 공통 심판
    common_refs = set(pcts_2024.keys()) & set(pcts_2025.keys())

    changes = []
    for ref in common_refs:
        change = pcts_2025[ref] - pcts_2024[ref]
        changes.append({
            'ref': ref,
            'pct_2024': pcts_2024[ref],
            'pct_2025': pcts_2025[ref],
            'change': change
        })

    sorted_changes = sorted(changes, key=lambda x: abs(x['change']), reverse=True)

    print("\n가장 많이 변한 심판 (Top 10):")
    print(f"{'Referee':<30} {'2024':>7} {'2025':>7} {'Change':>8}")
    print("-" * 70)

    for rc in sorted_changes[:10]:
        print(f"{rc['ref']:<30} {rc['pct_2024']:>6.1f}% {rc['pct_2025']:>6.1f}% "
              f"{rc['change']:>+7.1f}%")


def compare_rest_impact(games_2024, games_2025):
    """휴식일 영향 변화"""
    print("\n" + "="*70)
    print("💤 휴식일 영향 변화")
    print("="*70)

    def get_rest_stats(games):
        rest_stats = {0: {'w': 0, 'g': 0}, 1: {'w': 0, 'g': 0},
                     2: {'w': 0, 'g': 0}, 3: {'w': 0, 'g': 0}}

        for g in games:
            r = min(g['home_team']['rest_days'], 3)
            rest_stats[r]['g'] += 1
            if g['result']['home_win']:
                rest_stats[r]['w'] += 1

        return {r: stats['w'] / stats['g'] * 100 if stats['g'] > 0 else 0
                for r, stats in rest_stats.items()}

    pcts_2024 = get_rest_stats(games_2024)
    pcts_2025 = get_rest_stats(games_2025)

    print(f"\n{'Rest Days':<12} {'2024':>8} {'2025':>8} {'Change':>8}")
    print("-" * 70)

    labels = {0: 'B2B', 1: '1 day', 2: '2 days', 3: '3+ days'}
    for r in [0, 1, 2, 3]:
        change = pcts_2025[r] - pcts_2024[r]
        print(f"{labels[r]:<12} {pcts_2024[r]:>7.1f}% {pcts_2025[r]:>7.1f}% {change:>+7.1f}%")


def main():
    print("Loading 2024 season data...")
    games_2024 = load_year_data('2024')
    print(f"  Loaded {len(games_2024)} games from 2024")

    print("Loading 2025 season data...")
    games_2025 = load_year_data('2025')
    print(f"  Loaded {len(games_2025)} games from 2025\n")

    if not games_2024 or not games_2025:
        print("⚠️  Insufficient data for comparison")
        return

    compare_monthly_patterns(games_2024, games_2025)
    compare_team_evolution(games_2024, games_2025)
    compare_referee_patterns(games_2024, games_2025)
    compare_rest_impact(games_2024, games_2025)

    print("\n" + "="*70)
    print("✅ Year-over-Year Comparison Complete!")
    print("="*70)


if __name__ == "__main__":
    main()
