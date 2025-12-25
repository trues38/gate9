#!/usr/bin/env python3
"""
심판 정보 공개 시점 확인
내일 경기의 심판 정보가 언제 공개되는지 체크
"""

import json
from datetime import datetime
from fetch_game_preview import get_game_preview

def check_officials_availability():
    """현재 시점에 심판 정보가 있는지 확인"""
    print("=" * 80)
    print(f"심판 정보 확인 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # 내일 경기 로드
    games_path = "/Users/js/g9/nba_data/state_graph/tomorrow_games.json"
    try:
        with open(games_path, 'r', encoding='utf-8') as f:
            games = json.load(f)
    except FileNotFoundError:
        print("❌ tomorrow_games.json이 없습니다.")
        return

    results = []
    for game in games:
        game_id = game['game_id']
        matchup = f"{game['away_team']['abbr']} @ {game['home_team']['abbr']}"
        game_time = game['time']

        # 프리뷰 가져오기
        preview = get_game_preview(game_id)

        has_officials = preview.get('has_officials', False)
        officials_names = []

        if has_officials:
            officials_names = [o['name'] for o in preview['officials']]

        results.append({
            'game_id': game_id,
            'matchup': matchup,
            'game_time': game_time,
            'has_officials': has_officials,
            'officials': officials_names,
            'checked_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

        status = "✅" if has_officials else "❌"
        print(f"{status} {matchup} ({game_time})")
        if has_officials:
            print(f"   심판: {', '.join(officials_names)}")
        else:
            print(f"   심판 정보 없음")

    # 통계
    with_officials = sum(1 for r in results if r['has_officials'])
    total = len(results)

    print("\n" + "=" * 80)
    print(f"총 {total}경기 중 {with_officials}경기 심판 정보 공개")
    print(f"공개율: {with_officials/total*100:.1f}%")
    print("=" * 80)

    # 로그 저장
    log_path = "/Users/js/g9/nba_data/state_graph/referee_timing_log.json"
    try:
        with open(log_path, 'r') as f:
            log = json.load(f)
    except FileNotFoundError:
        log = []

    log.append({
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total_games': total,
        'with_officials': with_officials,
        'results': results
    })

    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump(log, f, indent=2, ensure_ascii=False)

    print(f"\n✅ 로그 저장: {log_path}")

    # 권장 사항
    if with_officials == 0:
        print("\n💡 권장: 경기 시작 4-6시간 전에 다시 확인하세요")
    elif with_officials < total:
        print(f"\n💡 권장: 아직 {total - with_officials}경기 심판 정보 미공개. 경기 시작 2-4시간 전에 다시 확인하세요")
    else:
        print("\n✅ 모든 경기 심판 정보 공개. 최종 보고서 생성 가능!")

def main():
    check_officials_availability()

if __name__ == "__main__":
    main()
