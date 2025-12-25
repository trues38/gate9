"""
NBA 2024-25 Season Analysis Engine
===================================
10월 개막부터 현재까지 전체 시즌 분석
- 월별 트렌드
- 심판 전체 통계
- 특정 매치업 패턴
- 팀별 상태 변화
"""

import json
import pandas as pd
import os
from glob import glob
from collections import defaultdict
from datetime import datetime

BASE_DIR = '/Users/js/g9/nba_data/state_graph'
SNAPSHOT_DIR = os.path.join(BASE_DIR, 'snapshots')


def load_all_snapshots():
    """전체 시즌 스냅샷 로드 (2024-10 ~ 현재)"""
    pattern = os.path.join(SNAPSHOT_DIR, '2024*_snapshots.json')
    all_games = []

    for filepath in sorted(glob(pattern)):
        with open(filepath, 'r') as f:
            games = json.load(f)
            all_games.extend(games)

    return all_games


def load_all_results():
    """전체 시즌 결과 로드"""
    results_files = glob(os.path.join(BASE_DIR, 'raw', '2024*_game_*.json'))

    all_results = []
    for filepath in sorted(results_files):
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
                'date': game_date,
                'home_team': home.get('team', {}).get('abbreviation', 'UNK'),
                'away_team': away.get('team', {}).get('abbreviation', 'UNK'),
                'home_score': home_score,
                'away_score': away_score,
                'home_win': 1 if home_score > away_score else 0,
                'point_diff': home_score - away_score
            })

    return pd.DataFrame(all_results)


def enrich_games(snapshots, results_df):
    """스냅샷에 결과 추가"""
    enriched = []
    for game in snapshots:
        match = results_df[results_df['game_id'] == game['game_id']]
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


def analyze_monthly_trends(games):
    """월별 트렌드 분석"""
    print("\n" + "="*70)
    print("📅 월별 트렌드 분석 (2024-25 Season)")
    print("="*70)

    monthly_stats = defaultdict(lambda: {
        'games': 0, 'home_wins': 0,
        'b2b_games': 0, 'b2b_wins': 0,
        'total_diff': 0, 'total_rest': 0
    })

    for g in games:
        month = g['date'][:7]  # YYYY-MM
        stats = monthly_stats[month]

        stats['games'] += 1
        stats['total_diff'] += g['result']['point_diff']
        stats['total_rest'] += g['home_team']['rest_days']

        if g['result']['home_win']:
            stats['home_wins'] += 1

        if g['home_team']['rest_days'] == 0:
            stats['b2b_games'] += 1
            if g['result']['home_win']:
                stats['b2b_wins'] += 1

    print(f"{'Month':<10} {'Games':>6} {'Home%':>7} {'B2B%':>7} {'AvgDiff':>9} {'AvgRest':>9}")
    print("-" * 70)

    for month in sorted(monthly_stats.keys()):
        stats = monthly_stats[month]
        home_pct = stats['home_wins'] / stats['games'] * 100
        b2b_pct = stats['b2b_wins'] / stats['b2b_games'] * 100 if stats['b2b_games'] > 0 else 0
        avg_diff = stats['total_diff'] / stats['games']
        avg_rest = stats['total_rest'] / stats['games']

        month_name = datetime.strptime(month, '%Y-%m').strftime('%Y-%b')
        print(f"{month_name:<10} {stats['games']:>6} {home_pct:>6.1f}% {b2b_pct:>6.1f}% {avg_diff:>+8.1f} {avg_rest:>8.1f}d")


def analyze_referee_full_stats(games):
    """심판 전체 통계 (시즌 누적)"""
    print("\n" + "="*70)
    print("👔 심판 전체 통계 (2024-25 Season)")
    print("="*70)

    ref_stats = defaultdict(lambda: {
        'games': 0, 'home_wins': 0,
        'total_diff': 0, 'b2b_home': 0, 'b2b_home_wins': 0
    })

    for g in games:
        for ref in g['referees']:
            stats = ref_stats[ref]
            stats['games'] += 1
            stats['total_diff'] += g['result']['point_diff']

            if g['result']['home_win']:
                stats['home_wins'] += 1

            if g['home_team']['rest_days'] == 0:
                stats['b2b_home'] += 1
                if g['result']['home_win']:
                    stats['b2b_home_wins'] += 1

    # 최소 20경기 이상
    filtered = {k: v for k, v in ref_stats.items() if v['games'] >= 20}
    sorted_refs = sorted(filtered.items(),
                        key=lambda x: x[1]['home_wins'] / x[1]['games'],
                        reverse=True)

    print(f"{'Referee':<30} {'Games':>6} {'Home%':>7} {'AvgDiff':>9} {'B2B-Home':>10}")
    print("-" * 70)

    for ref, stats in sorted_refs[:15]:
        home_pct = stats['home_wins'] / stats['games'] * 100
        avg_diff = stats['total_diff'] / stats['games']
        b2b_info = f"{stats['b2b_home_wins']}/{stats['b2b_home']}" if stats['b2b_home'] > 0 else "N/A"

        print(f"{ref:<30} {stats['games']:>6} {home_pct:>6.1f}% {avg_diff:>+8.1f} {b2b_info:>10}")

    print("\n" + "-" * 70)
    print("원정팀 유리 심판 (Home% 낮음):")
    print("-" * 70)

    for ref, stats in sorted_refs[-10:]:
        home_pct = stats['home_wins'] / stats['games'] * 100
        avg_diff = stats['total_diff'] / stats['games']
        print(f"{ref:<30} {stats['games']:>6} {home_pct:>6.1f}% {avg_diff:>+8.1f}")


def analyze_team_evolution(games):
    """팀별 시즌 진행에 따른 변화"""
    print("\n" + "="*70)
    print("📈 팀 성장/하락 추이 (개막 vs 최근)")
    print("="*70)

    # 개막 2주 vs 최근 2주
    early = [g for g in games if g['date'] <= '2024-11-05']
    recent = [g for g in games if g['date'] >= '2024-12-10']

    team_early = defaultdict(lambda: {'wins': 0, 'games': 0})
    team_recent = defaultdict(lambda: {'wins': 0, 'games': 0})

    for g in early:
        home = g['home_team']['team_id']
        away = g['away_team']['team_id']

        team_early[home]['games'] += 1
        team_early[away]['games'] += 1

        if g['result']['home_win']:
            team_early[home]['wins'] += 1
        else:
            team_early[away]['wins'] += 1

    for g in recent:
        home = g['home_team']['team_id']
        away = g['away_team']['team_id']

        team_recent[home]['games'] += 1
        team_recent[away]['games'] += 1

        if g['result']['home_win']:
            team_recent[home]['wins'] += 1
        else:
            team_recent[away]['wins'] += 1

    # 변화 계산
    team_changes = []
    for team in team_early.keys():
        if team in team_recent and team_early[team]['games'] >= 5 and team_recent[team]['games'] >= 5:
            early_pct = team_early[team]['wins'] / team_early[team]['games'] * 100
            recent_pct = team_recent[team]['wins'] / team_recent[team]['games'] * 100
            change = recent_pct - early_pct

            team_changes.append({
                'team': team,
                'early_pct': early_pct,
                'recent_pct': recent_pct,
                'change': change
            })

    sorted_changes = sorted(team_changes, key=lambda x: x['change'], reverse=True)

    print("\n🚀 급상승 팀:")
    for tc in sorted_changes[:5]:
        print(f"{tc['team']:4s}: {tc['early_pct']:5.1f}% → {tc['recent_pct']:5.1f}% ({tc['change']:+5.1f}%)")

    print("\n📉 급하락 팀:")
    for tc in sorted_changes[-5:]:
        print(f"{tc['team']:4s}: {tc['early_pct']:5.1f}% → {tc['recent_pct']:5.1f}% ({tc['change']:+5.1f}%)")


def analyze_specific_matchups(games):
    """특정 매치업 분석 (강팀 vs 약팀)"""
    print("\n" + "="*70)
    print("⚔️  특정 매치업 패턴")
    print("="*70)

    # 팀 승률 계산
    team_records = defaultdict(lambda: {'wins': 0, 'games': 0})

    for g in games:
        home = g['home_team']['team_id']
        away = g['away_team']['team_id']

        team_records[home]['games'] += 1
        team_records[away]['games'] += 1

        if g['result']['home_win']:
            team_records[home]['wins'] += 1
        else:
            team_records[away]['wins'] += 1

    # 승률 순위
    team_pcts = {team: stats['wins'] / stats['games'] * 100
                 for team, stats in team_records.items() if stats['games'] >= 10}

    top_teams = sorted(team_pcts.items(), key=lambda x: x[1], reverse=True)[:5]
    bottom_teams = sorted(team_pcts.items(), key=lambda x: x[1])[:5]

    top_team_ids = [t[0] for t in top_teams]
    bottom_team_ids = [t[0] for t in bottom_teams]

    # 강팀 vs 약팀 경기
    elite_vs_weak = [g for g in games
                     if ((g['home_team']['team_id'] in top_team_ids and g['away_team']['team_id'] in bottom_team_ids) or
                         (g['away_team']['team_id'] in top_team_ids and g['home_team']['team_id'] in bottom_team_ids))]

    if elite_vs_weak:
        favorite_wins = 0
        total = len(elite_vs_weak)
        avg_margin = 0

        for g in elite_vs_weak:
            is_home_favorite = g['home_team']['team_id'] in top_team_ids

            if is_home_favorite:
                if g['result']['home_win']:
                    favorite_wins += 1
                    avg_margin += g['result']['point_diff']
                else:
                    avg_margin -= g['result']['point_diff']
            else:
                if not g['result']['home_win']:
                    favorite_wins += 1
                    avg_margin -= g['result']['point_diff']
                else:
                    avg_margin += g['result']['point_diff']

        avg_margin = avg_margin / total

        print(f"\n강팀 vs 약팀 매치업 ({total} games):")
        print(f"  강팀 승률: {favorite_wins/total*100:.1f}%")
        print(f"  평균 점수차: {avg_margin:+.1f}점")
        print(f"\n강팀 Top 5: {', '.join([t[0] for t in top_teams])}")
        print(f"약팀 Bot 5: {', '.join([t[0] for t in bottom_teams])}")


def main():
    print("Loading all snapshots...")
    snapshots = load_all_snapshots()
    print(f"  Loaded {len(snapshots)} snapshots")

    print("Loading all results...")
    results = load_all_results()
    print(f"  Loaded {len(results)} results")

    print("Enriching games...")
    games = enrich_games(snapshots, results)
    print(f"  Matched {len(games)} games")

    if not games:
        print("\n⚠️  No enriched games found. Please run data collection first.")
        return

    # 분석 실행
    analyze_monthly_trends(games)
    analyze_referee_full_stats(games)
    analyze_team_evolution(games)
    analyze_specific_matchups(games)

    print("\n" + "="*70)
    print(f"✅ Full Season Analysis Complete ({len(games)} games)")
    print("="*70)


if __name__ == "__main__":
    main()
