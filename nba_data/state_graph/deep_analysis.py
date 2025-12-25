"""
Deep State Analysis - 2025 December NBA
========================================
팀별, 심판별, 조합별 심화 분석
"""

import json
import pandas as pd
import os
from glob import glob
from collections import defaultdict

BASE_DIR = '/Users/js/g9/nba_data/state_graph'
SNAPSHOT_DIR = os.path.join(BASE_DIR, 'snapshots')
RESULTS_PATH = os.path.join(BASE_DIR, 'december_2025_results.csv')


def load_enriched_games():
    """2025년 12월 enriched games 로드"""
    pattern = os.path.join(SNAPSHOT_DIR, '2025*_snapshots.json')
    all_games = []
    for filepath in sorted(glob(pattern)):
        with open(filepath, 'r') as f:
            games = json.load(f)
            all_games.extend(games)

    df = pd.read_csv(RESULTS_PATH)
    df['game_id'] = df['game_id'].astype(str)

    enriched = []
    for game in all_games:
        game_id = game['game_id']
        match = df[df['game_id'] == game_id]
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


def analyze_2day_rest_teams(games):
    """2일 휴식 승률이 높은 팀 TOP 10"""
    print("\n" + "="*60)
    print("🔥 2일 휴식 대응력 - 팀별 순위")
    print("="*60)

    team_stats = defaultdict(lambda: {'wins': 0, 'games': 0})

    for g in games:
        if g['home_team']['rest_days'] == 2:
            team = g['home_team']['team_id']
            team_stats[team]['games'] += 1
            if g['result']['home_win']:
                team_stats[team]['wins'] += 1

        if g['away_team']['rest_days'] == 2:
            team = g['away_team']['team_id']
            team_stats[team]['games'] += 1
            if not g['result']['home_win']:  # away win
                team_stats[team]['wins'] += 1

    # 3경기 이상만
    filtered = {k: v for k, v in team_stats.items() if v['games'] >= 3}
    sorted_teams = sorted(filtered.items(),
                         key=lambda x: x[1]['wins'] / x[1]['games'],
                         reverse=True)

    for i, (team, stats) in enumerate(sorted_teams[:10], 1):
        pct = stats['wins'] / stats['games'] * 100
        print(f"{i:2d}. {team:4s}: {stats['wins']:2d}W - {stats['games']-stats['wins']:2d}L ({pct:5.1f}%) | {stats['games']} games")


def analyze_b2b_teams(games):
    """Back-to-back 대응력 - 팀별 순위"""
    print("\n" + "="*60)
    print("⚡ Back-to-back 생존율 - 팀별 순위")
    print("="*60)

    team_stats = defaultdict(lambda: {'wins': 0, 'games': 0})

    for g in games:
        if g['home_team']['rest_days'] == 0:
            team = g['home_team']['team_id']
            team_stats[team]['games'] += 1
            if g['result']['home_win']:
                team_stats[team]['wins'] += 1

        if g['away_team']['rest_days'] == 0:
            team = g['away_team']['team_id']
            team_stats[team]['games'] += 1
            if not g['result']['home_win']:
                team_stats[team]['wins'] += 1

    filtered = {k: v for k, v in team_stats.items() if v['games'] >= 2}
    sorted_teams = sorted(filtered.items(),
                         key=lambda x: x[1]['wins'] / x[1]['games'],
                         reverse=True)

    print("강철 멘탈 (승률 높음):")
    for i, (team, stats) in enumerate(sorted_teams[:5], 1):
        pct = stats['wins'] / stats['games'] * 100
        print(f"{i}. {team:4s}: {stats['wins']}W - {stats['games']-stats['wins']}L ({pct:5.1f}%)")

    print("\n피로 누적 (승률 낮음):")
    for i, (team, stats) in enumerate(sorted_teams[-5:], 1):
        pct = stats['wins'] / stats['games'] * 100
        print(f"{i}. {team:4s}: {stats['wins']}W - {stats['games']-stats['wins']}L ({pct:5.1f}%)")


def analyze_referee_team_combo(games):
    """심판-팀 조합 분석 (특정 심판이 특정 팀에게 유리?)"""
    print("\n" + "="*60)
    print("👔 심판-팀 조합 분석 (위험/유리한 조합)")
    print("="*60)

    # 심판별로 팀 홈 승률 추적
    ref_team_stats = defaultdict(lambda: defaultdict(lambda: {'wins': 0, 'games': 0}))

    for g in games:
        home_team = g['home_team']['team_id']
        for ref in g['referees']:
            ref_team_stats[ref][home_team]['games'] += 1
            if g['result']['home_win']:
                ref_team_stats[ref][home_team]['wins'] += 1

    # 가장 극단적인 조합 찾기
    extreme_combos = []
    for ref, teams in ref_team_stats.items():
        for team, stats in teams.items():
            if stats['games'] >= 2:  # 최소 2경기
                pct = stats['wins'] / stats['games'] * 100
                extreme_combos.append({
                    'ref': ref,
                    'team': team,
                    'wins': stats['wins'],
                    'games': stats['games'],
                    'pct': pct
                })

    # 정렬
    sorted_combos = sorted(extreme_combos, key=lambda x: x['pct'], reverse=True)

    print("\n🏆 황금 조합 (홈팀 최고 승률):")
    for combo in sorted_combos[:5]:
        print(f"{combo['team']:4s} + {combo['ref']:25s}: {combo['wins']}W-{combo['games']-combo['wins']}L ({combo['pct']:.1f}%)")

    print("\n💀 위험 조합 (홈팀 최저 승률):")
    for combo in sorted_combos[-5:]:
        print(f"{combo['team']:4s} + {combo['ref']:25s}: {combo['wins']}W-{combo['games']-combo['wins']}L ({combo['pct']:.1f}%)")


def analyze_injury_depth(games):
    """부상자 수별 점수 차이 분석"""
    print("\n" + "="*60)
    print("🚑 부상자 수 vs 점수 차이 분석")
    print("="*60)

    injury_buckets = defaultdict(lambda: {'diffs': [], 'wins': 0, 'games': 0})

    for g in games:
        inj_count = len(g['home_team']['injuries'])
        bucket = min(inj_count, 5)  # 0~5+

        injury_buckets[bucket]['diffs'].append(g['result']['point_diff'])
        injury_buckets[bucket]['games'] += 1
        if g['result']['home_win']:
            injury_buckets[bucket]['wins'] += 1

    for count in sorted(injury_buckets.keys()):
        stats = injury_buckets[count]
        avg_diff = sum(stats['diffs']) / len(stats['diffs'])
        win_pct = stats['wins'] / stats['games'] * 100
        label = f"{count}+" if count == 5 else f"{count}"
        print(f"{label} injuries: Win {win_pct:5.1f}% | Avg Point Diff: {avg_diff:+5.1f}")


def analyze_rest_advantage(games):
    """휴식일 차이가 승부에 미치는 영향"""
    print("\n" + "="*60)
    print("⚖️  휴식일 차이 영향 (홈팀 기준)")
    print("="*60)

    rest_diff_stats = defaultdict(lambda: {'wins': 0, 'games': 0, 'diffs': []})

    for g in games:
        home_rest = g['home_team']['rest_days']
        away_rest = g['away_team']['rest_days']
        rest_diff = home_rest - away_rest  # 양수면 홈팀이 더 쉼

        # -3 ~ +3 범위로 제한
        rest_diff = max(-3, min(3, rest_diff))

        rest_diff_stats[rest_diff]['games'] += 1
        rest_diff_stats[rest_diff]['diffs'].append(g['result']['point_diff'])
        if g['result']['home_win']:
            rest_diff_stats[rest_diff]['wins'] += 1

    for diff in sorted(rest_diff_stats.keys()):
        stats = rest_diff_stats[diff]
        if stats['games'] > 0:
            win_pct = stats['wins'] / stats['games'] * 100
            avg_margin = sum(stats['diffs']) / len(stats['diffs'])

            if diff > 0:
                label = f"홈팀 +{diff}일"
            elif diff < 0:
                label = f"원정팀 +{abs(diff)}일"
            else:
                label = "동일 휴식"

            print(f"{label:15s}: Win {win_pct:5.1f}% | Avg Margin {avg_margin:+5.1f} | {stats['games']} games")


def analyze_combo_killer(games):
    """치명적 조합 발견 (복합 요인)"""
    print("\n" + "="*60)
    print("💀 치명적 조합 발견")
    print("="*60)

    # 1. 원정 + B2B + 부상자 2명+
    killer_combo = [g for g in games
                   if g['away_team']['rest_days'] == 0
                   and len(g['away_team']['injuries']) >= 2]

    if killer_combo:
        home_wins = sum(1 for g in killer_combo if g['result']['home_win'])
        total = len(killer_combo)
        avg_margin = sum(g['result']['point_diff'] for g in killer_combo) / total
        print(f"원정 B2B + 부상자 2명+: 홈팀 {home_wins}W-{total-home_wins}L ({home_wins/total*100:.1f}%)")
        print(f"  → 평균 점수차: {avg_margin:+.1f}점 (홈팀 유리)")

    # 2. 홈 + 2일 휴식 + 부상자 0명
    golden_combo = [g for g in games
                    if g['home_team']['rest_days'] == 2
                    and len(g['home_team']['injuries']) == 0]

    if golden_combo:
        home_wins = sum(1 for g in golden_combo if g['result']['home_win'])
        total = len(golden_combo)
        print(f"\n홈 + 2일 휴식 + 부상 0: {home_wins}W-{total-home_wins}L ({home_wins/total*100:.1f}%)")

    # 3. 특정 심판 + 홈팀 B2B
    scott_foster_b2b = [g for g in games
                        if any('Foster' in ref for ref in g['referees'])
                        and g['home_team']['rest_days'] == 0]

    if scott_foster_b2b:
        home_wins = sum(1 for g in scott_foster_b2b if g['result']['home_win'])
        total = len(scott_foster_b2b)
        print(f"\nFoster 심판 + 홈팀 B2B: {home_wins}W-{total-home_wins}L ({home_wins/total*100:.1f}%)")


def analyze_time_trend(games):
    """시즌 진행에 따른 트렌드"""
    print("\n" + "="*60)
    print("📈 시즌 트렌드 (12월 초 vs 중순 vs 말)")
    print("="*60)

    early = [g for g in games if g['date'] <= '2025-12-10']
    mid = [g for g in games if '2025-12-11' <= g['date'] <= '2025-12-20']
    late = [g for g in games if g['date'] >= '2025-12-21']

    for period_games, label in [(early, '12/1-10'), (mid, '12/11-20'), (late, '12/21-23')]:
        if not period_games:
            continue

        home_wins = sum(1 for g in period_games if g['result']['home_win'])
        total = len(period_games)
        avg_margin = sum(g['result']['point_diff'] for g in period_games) / total

        # 평균 휴식일
        avg_home_rest = sum(g['home_team']['rest_days'] for g in period_games) / total

        print(f"\n{label} ({total} games):")
        print(f"  홈팀 승률: {home_wins/total*100:.1f}%")
        print(f"  평균 점수차: {avg_margin:+.1f}")
        print(f"  평균 휴식일: {avg_home_rest:.1f}일")


def main():
    print("Loading enriched games...")
    games = load_enriched_games()
    print(f"  Loaded {len(games)} games from 2025-12\n")

    # 심화 분석 실행
    analyze_2day_rest_teams(games)
    analyze_b2b_teams(games)
    analyze_rest_advantage(games)
    analyze_injury_depth(games)
    analyze_referee_team_combo(games)
    analyze_combo_killer(games)
    analyze_time_trend(games)

    print("\n" + "="*60)
    print("🎉 Deep Analysis Complete!")
    print("="*60)


if __name__ == "__main__":
    main()
