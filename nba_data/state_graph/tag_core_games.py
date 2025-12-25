"""
핵심 경기 10개 전술 태깅 스크립트
====================================
목표: 수작업으로 핵심 경기를 선택하고 전술 태깅 검증

Made with ❤️ by State Graph Engine
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from tactic_extraction_llm import (
    detect_tactic_by_stats,
    extract_tactics,
    TACTIC_SIGNATURES
)
from quality_monitor import QualityMonitor, generate_quality_report, monitor_new_tag
from sparsity_handler import handle_sparsity


# ============================================================================
# 핵심 경기 선정 기준
# ============================================================================

CORE_GAME_CRITERIA = {
    "okc_vs_mia": {
        "description": "OKC Gap Defense vs MIA No-Pick Roll Play",
        "teams": ["OKC", "MIA"],
        "expected_tactics": ["Gap Defense", "No-Pick Roll Play"],
        "priority": 1
    },
    "hou_vs_den": {
        "description": "HOU Inside Spacing vs DEN 3-Point Heavy",
        "teams": ["HOU", "DEN"],
        "expected_tactics": ["Inside Spacing"],
        "priority": 1
    },
    "sa_rotation": {
        "description": "SA 20-30min Rotation 효과 검증",
        "teams": ["SA"],
        "expected_tactics": ["20-30min Rotation"],
        "priority": 1,
        "count": 3  # SA 경기 3개
    },
    "pace_and_space": {
        "description": "Golden State / Phoenix Pace & Space",
        "teams": ["GS", "PHX"],
        "expected_tactics": ["Pace & Space"],
        "priority": 2
    }
}


# ============================================================================
# 1. 경기 데이터 로드
# ============================================================================

def load_game_snapshots(raw_dir: str = "raw") -> Dict[str, Dict]:
    """
    raw/ 디렉토리에서 경기 데이터 로드

    Returns:
        {game_id: game_data}
    """
    raw_path = Path(raw_dir)

    if not raw_path.exists():
        print(f"⚠️  경고: {raw_dir} 디렉토리가 없습니다.")
        return {}

    games = {}

    # raw 디렉토리의 game 파일들 로드
    for file_path in raw_path.glob("*_game_*.json"):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

                # game_id 추출 (파일명에서)
                filename = file_path.stem  # e.g., "20241022_game_401704627"
                parts = filename.split('_game_')
                if len(parts) == 2:
                    game_id = parts[1]
                    games[game_id] = data
        except Exception as e:
            print(f"⚠️  {file_path.name} 로드 실패: {e}")

    print(f"✅ {len(games)}개 경기 데이터 로드 완료")
    return games


# ============================================================================
# 2. 핵심 경기 찾기
# ============================================================================

def find_core_games(games: Dict[str, Dict], criteria: Dict) -> List[Dict]:
    """
    핵심 경기 선정 기준에 맞는 경기 찾기

    Returns:
        [{'game_id': ..., 'matchup': ..., 'reason': ..., 'priority': ...}]
    """
    candidates = []

    for game_id, game_data in games.items():
        try:
            # 경기 기본 정보 추출 (raw 포맷)
            header = game_data.get('header', {})
            competitions = header.get('competitions', [])
            if not competitions:
                continue

            competition = competitions[0]
            competitors = competition.get('competitors', [])

            # 홈/어웨이 팀 찾기
            home_team = None
            away_team = None
            for comp in competitors:
                team_info = comp.get('team', {})
                team_abbr = team_info.get('abbreviation', '')
                if comp.get('homeAway') == 'home':
                    home_team = team_abbr
                elif comp.get('homeAway') == 'away':
                    away_team = team_abbr

            if not home_team or not away_team:
                continue

            # 날짜 추출
            game_date = competition.get('date', 'Unknown')[:10]  # YYYY-MM-DD

            # 각 기준과 매칭
            for criterion_name, criterion in criteria.items():
                required_teams = criterion['teams']

                # 팀 매칭 체크
                if home_team in required_teams or away_team in required_teams:
                    matchup = f"{away_team} @ {home_team}"

                    candidates.append({
                        'game_id': game_id,
                        'matchup': matchup,
                        'home_team': home_team,
                        'away_team': away_team,
                        'date': game_date,
                        'criterion': criterion_name,
                        'description': criterion['description'],
                        'priority': criterion['priority'],
                        'game_data': game_data
                    })

        except Exception as e:
            print(f"⚠️  경기 {game_id} 파싱 실패: {e}")
            continue

    # Priority로 정렬
    candidates.sort(key=lambda x: (x['priority'], x['date']))

    return candidates


# ============================================================================
# 3. 경기 통계 추출
# ============================================================================

def extract_team_stats(game_data: Dict, team_abbr: str) -> Dict:
    """
    경기 데이터에서 팀 통계 추출 (raw 포맷)

    Args:
        game_data: raw game data
        team_abbr: 팀 약자 (예: 'OKC', 'MIA')

    Returns:
        통계 딕셔너리
    """
    try:
        boxscore = game_data.get('boxscore', {})
        teams = boxscore.get('teams', [])

        # 팀과 상대 팀 찾기
        team_data = None
        opponent_data = None

        for team in teams:
            abbr = team.get('team', {}).get('abbreviation', '')
            if abbr == team_abbr:
                team_data = team
            else:
                opponent_data = team

        if not team_data or not opponent_data:
            print(f"⚠️  팀 {team_abbr} 통계를 찾을 수 없습니다.")
            return {}

        # 통계 배열을 딕셔너리로 변환
        def stats_array_to_dict(stats_array):
            stats_dict = {}
            for stat in stats_array:
                name = stat.get('name', '')
                value_str = stat.get('displayValue', '0')

                # 숫자 추출 (예: "43-78" → 43)
                if '-' in value_str:
                    value_str = value_str.split('-')[0]

                try:
                    # 정수 또는 실수로 변환
                    if '.' in value_str:
                        stats_dict[name] = float(value_str)
                    else:
                        stats_dict[name] = int(value_str)
                except ValueError:
                    stats_dict[name] = 0

            return stats_dict

        team_stats = stats_array_to_dict(team_data.get('statistics', []))
        opponent_stats = stats_array_to_dict(opponent_data.get('statistics', []))

        # 전술 시그니처에 필요한 통계 추출
        # ESPN 통계 필드명에 맞춤
        extracted = {
            # Defense stats
            'opponent_paint_points': opponent_stats.get('pointsInThePaint', 0),
            'opponent_fg_pct_paint': opponent_stats.get('fieldGoalPct', 50) / 100.0,  # %를 소수로
            'opponent_turnovers': opponent_stats.get('turnovers', 0),
            'steals': team_stats.get('steals', 0),
            'blocks': team_stats.get('blocks', 0),

            # Offense stats
            'assists': team_stats.get('assists', 0),
            'points_in_paint': team_stats.get('pointsInThePaint', 0),
            'turnovers': team_stats.get('turnovers', 0),
            'fast_break_points': team_stats.get('fastBreakPoints', 0),
            'second_chance_points': team_stats.get('secondChancePoints', 0),

            # 3점 비율 계산
            'three_point_rate': 0.0,
            'three_point_pct': team_stats.get('threePointFieldGoalPct', 0) / 100.0,

            # 기타
            'offensive_rating': 110.0,  # Placeholder
            'pace': 100,  # Placeholder
            'bench_points': 0,  # Placeholder
            'minutes_variance': 6,
            'fourth_quarter_point_diff': 0,
            'fatigue_index': 0.5
        }

        # 3점 비율 계산 (시도/전체슛)
        fg_attempts = team_stats.get('fieldGoalsAttempted', 1)
        if fg_attempts > 0:
            # 3점 시도 추출 (예: "11-30" → 30)
            three_pt_str = str(team_data.get('statistics', [{}])[2].get('displayValue', '0-0'))
            if '-' in three_pt_str:
                three_pt_attempts = int(three_pt_str.split('-')[1])
                extracted['three_point_rate'] = three_pt_attempts / fg_attempts

        return extracted

    except Exception as e:
        print(f"⚠️  통계 추출 오류: {e}")
        return {}


# ============================================================================
# 4. 수동 태깅 인터페이스
# ============================================================================

def manual_tagging_session(candidates: List[Dict], output_file: str = "tactics_seed.json"):
    """
    수동으로 10개 경기 선택하고 태깅
    """
    print("\n" + "=" * 80)
    print("핵심 경기 10개 전술 태깅 세션")
    print("=" * 80)

    print(f"\n발견된 후보 경기: {len(candidates)}개")
    print("\n상위 15개 후보:\n")

    for i, candidate in enumerate(candidates[:15], 1):
        print(f"{i:2d}. [{candidate['priority']}] {candidate['date']} - {candidate['matchup']}")
        print(f"    → {candidate['description']}")

    print("\n" + "=" * 80)
    print("추천: 위 리스트에서 다양한 전술을 커버하도록 10개 선택")
    print("=" * 80)

    # 자동 선택 (우선순위 기반)
    selected_games = select_diverse_games(candidates, target_count=10)

    print(f"\n✅ 자동 선택된 10개 경기:")
    for i, game in enumerate(selected_games, 1):
        print(f"{i:2d}. {game['matchup']} - {game['description']}")

    # 태깅 실행
    print("\n" + "=" * 80)
    print("전술 태깅 시작...")
    print("=" * 80)

    all_tactic_tags = []
    monitor = QualityMonitor()

    for i, game in enumerate(selected_games, 1):
        print(f"\n[{i}/10] 처리 중: {game['matchup']} ({game['date']})")

        # 홈/어웨이 양쪽 팀 태깅
        for team_abbr in [game['home_team'], game['away_team']]:
            # 통계 추출
            team_stats = extract_team_stats(game['game_data'], team_abbr)

            # 전술 자동 감지
            detected = detect_tactic_by_stats(team_stats, TACTIC_SIGNATURES)

            if detected:
                print(f"  {team_abbr}: {len(detected)}개 전술 감지")

                for tactic in detected:
                    # 샘플 크기 페널티 적용 (초기 시드 데이터이므로)
                    sample_penalty = min(1 / 20, 1.0)  # 1/20 = 0.05
                    adjusted_confidence = tactic['confidence'] * (0.5 + 0.5 * sample_penalty)
                    adjusted_confidence = round(adjusted_confidence, 2)

                    tag = {
                        'game_id': game['game_id'],
                        'date': game['date'],
                        'team': team_abbr,
                        'tactic_name': tactic['name'],
                        'category': tactic['category'],
                        'confidence': adjusted_confidence,  # 페널티 적용된 confidence
                        'raw_confidence': tactic['confidence'],  # 원본 보존
                        'sample_size': 1,
                        'team_stats': team_stats,
                        'source': 'core_games_manual_validation'
                    }

                    # 실시간 품질 체크 (페널티 적용 후이므로 더 관대)
                    validation = monitor_new_tag(tag, all_tactic_tags)

                    if validation['approved']:
                        all_tactic_tags.append(tag)
                        print(f"    ✅ {tactic['name']} (raw: {tactic['confidence']}, adjusted: {adjusted_confidence})")
                    else:
                        print(f"    ⚠️  {tactic['name']} (raw: {tactic['confidence']}, adjusted: {adjusted_confidence}) - 품질 체크 실패")
                        for issue in validation['issues']:
                            print(f"        {issue.get('explanation', 'Unknown issue')}")
            else:
                print(f"  {team_abbr}: 감지된 전술 없음")

    # 저장
    output_data = {
        'metadata': {
            'created_at': datetime.now().isoformat(),
            'total_games': len(selected_games),
            'total_tags': len(all_tactic_tags),
            'source': 'core_games_manual_tagging'
        },
        'games': [
            {
                'game_id': game['game_id'],
                'matchup': game['matchup'],
                'date': game['date'],
                'criterion': game['criterion']
            }
            for game in selected_games
        ],
        'tactic_tags': all_tactic_tags
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\n✅ 태깅 결과 저장: {output_file}")

    # 품질 리포트 생성
    print("\n" + "=" * 80)
    print("품질 리포트")
    print("=" * 80)
    report = generate_quality_report(all_tactic_tags)
    print(report)

    return output_data


def select_diverse_games(candidates: List[Dict], target_count: int = 10) -> List[Dict]:
    """
    다양한 전술을 커버하도록 경기 선택
    """
    selected = []
    criterion_counts = {}

    # Priority 1 먼저
    for candidate in candidates:
        if candidate['priority'] == 1:
            criterion = candidate['criterion']

            # 기준별 목표 개수
            if criterion == 'sa_rotation':
                max_count = 3
            else:
                max_count = 2

            if criterion_counts.get(criterion, 0) < max_count:
                selected.append(candidate)
                criterion_counts[criterion] = criterion_counts.get(criterion, 0) + 1

            if len(selected) >= target_count:
                break

    # 부족하면 Priority 2에서 채우기
    if len(selected) < target_count:
        for candidate in candidates:
            if candidate['priority'] == 2 and candidate not in selected:
                selected.append(candidate)
                if len(selected) >= target_count:
                    break

    return selected[:target_count]


# ============================================================================
# 5. 요약 통계
# ============================================================================

def print_summary_stats(output_data: Dict):
    """태깅 결과 요약"""

    print("\n" + "=" * 80)
    print("태깅 요약 통계")
    print("=" * 80)

    tags = output_data['tactic_tags']

    if not tags:
        print("\n⚠️  태깅된 전술이 없습니다.")
        print("   - 통계 시그니처를 만족하는 경기가 적거나")
        print("   - 품질 기준이 너무 엄격할 수 있습니다.")
        print("\n" + "=" * 80)
        return

    # 전술별 카운트
    tactic_counts = {}
    for tag in tags:
        tactic = tag['tactic_name']
        tactic_counts[tactic] = tactic_counts.get(tactic, 0) + 1

    print(f"\n전술별 태그 수:")
    for tactic, count in sorted(tactic_counts.items(), key=lambda x: -x[1]):
        print(f"  {tactic}: {count}개")

    # 팀별 카운트
    team_counts = {}
    for tag in tags:
        team = tag['team']
        team_counts[team] = team_counts.get(team, 0) + 1

    print(f"\n팀별 태그 수 (Top 10):")
    for team, count in sorted(team_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"  {team}: {count}개")

    # 평균 Confidence
    avg_confidence = sum(tag['confidence'] for tag in tags) / len(tags)
    print(f"\n평균 Confidence: {avg_confidence:.2f}")

    print("\n" + "=" * 80)


# ============================================================================
# 메인 실행
# ============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("핵심 경기 10개 전술 태깅 시작")
    print("=" * 80)

    # 1. 경기 데이터 로드
    games = load_game_snapshots("raw")

    if not games:
        print("❌ 경기 데이터가 없습니다. raw/ 디렉토리를 확인하세요.")
        exit(1)

    # 2. 핵심 경기 찾기
    candidates = find_core_games(games, CORE_GAME_CRITERIA)

    if not candidates:
        print("❌ 기준에 맞는 경기를 찾을 수 없습니다.")
        exit(1)

    # 3. 수동 태깅 세션
    output_data = manual_tagging_session(candidates, "tactics_seed.json")

    # 4. 요약 통계
    print_summary_stats(output_data)

    print("\n" + "=" * 80)
    print("✅ 완료!")
    print("=" * 80)
    print("\n다음 단계:")
    print("  1. tactics_seed.json 검토")
    print("  2. Neo4j 마이그레이션 준비")
    print("  3. Graph Viewer MVP 개발")
    print("=" * 80)
