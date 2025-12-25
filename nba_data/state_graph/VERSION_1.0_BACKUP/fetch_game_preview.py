#!/usr/bin/env python3
"""
ESPN 게임 프리뷰 정보 가져오기
- 배당 정보
- 예상/분석
- 부상자 명단
- 심판 정보 (있을 경우)
"""

import requests
import json
from typing import Dict, List, Optional
from datetime import datetime

def fetch_game_summary(game_id: str) -> Optional[Dict]:
    """ESPN API에서 게임 상세 정보 가져오기"""
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={game_id}"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ API 호출 실패 ({game_id}): {e}")
        return None

def parse_odds(data: Dict) -> Optional[Dict]:
    """배당 정보 파싱"""
    try:
        if 'pickcenter' not in data:
            return None

        pickcenter = data['pickcenter'][0] if data['pickcenter'] else {}

        # 배당사별 정보
        odds_providers = pickcenter.get('provider', {})

        # 주요 배당 정보
        details = pickcenter.get('details', '')
        over_under = pickcenter.get('overUnder', 0)
        spread = pickcenter.get('spread', 0)

        # 승패 예측
        home_team_odds = pickcenter.get('homeTeamOdds', {})
        away_team_odds = pickcenter.get('awayTeamOdds', {})

        return {
            'spread': spread,  # 핸디캡
            'over_under': over_under,  # 오버언더
            'details': details,
            'home_moneyline': home_team_odds.get('moneyLine', None),
            'away_moneyline': away_team_odds.get('moneyLine', None),
            'home_spread_odds': home_team_odds.get('spreadOdds', None),
            'away_spread_odds': away_team_odds.get('spreadOdds', None),
            'provider': odds_providers.get('name', 'Unknown')
        }
    except Exception as e:
        print(f"⚠️  배당 정보 파싱 실패: {e}")
        return None

def parse_predictions(data: Dict) -> Optional[Dict]:
    """예측 정보 파싱"""
    try:
        if 'predictor' not in data:
            return None

        predictor = data['predictor']

        home_team = predictor.get('homeTeam', {})
        away_team = predictor.get('awayTeam', {})

        return {
            'home_win_probability': home_team.get('gameProjection', 0),
            'away_win_probability': away_team.get('gameProjection', 0),
            'home_projected_score': home_team.get('score', {}).get('value', 0),
            'away_projected_score': away_team.get('score', {}).get('value', 0),
        }
    except Exception as e:
        print(f"⚠️  예측 정보 파싱 실패: {e}")
        return None

def parse_injuries(data: Dict) -> Dict[str, List[Dict]]:
    """부상자 명단 파싱"""
    injuries = {'home': [], 'away': []}

    try:
        if 'injuries' not in data:
            return injuries

        for injury_list in data['injuries']:
            team_id = injury_list.get('team', {}).get('id')
            team_abbr = injury_list.get('team', {}).get('abbreviation', 'Unknown')

            for injury in injury_list.get('injuries', []):
                athlete = injury.get('athlete', {})

                injuries_info = {
                    'name': athlete.get('displayName', 'Unknown'),
                    'position': athlete.get('position', {}).get('abbreviation', ''),
                    'status': injury.get('status', 'Unknown'),
                    'type': injury.get('type', 'Unknown'),
                    'details': injury.get('details', {}).get('detail', ''),
                    'team': team_abbr
                }

                # 홈/원정 구분 (header에서 확인 필요)
                # 임시로 team_abbr로 구분
                injuries['home'].append(injuries_info)  # 나중에 매칭 필요

        return injuries
    except Exception as e:
        print(f"⚠️  부상자 정보 파싱 실패: {e}")
        return injuries

def parse_officials(data: Dict) -> Optional[List[Dict]]:
    """심판 정보 파싱"""
    try:
        if 'gameInfo' not in data or 'officials' not in data['gameInfo']:
            return None

        officials = []
        for official in data['gameInfo']['officials']:
            officials.append({
                'name': official.get('displayName', 'Unknown'),
                'position': official.get('position', {}).get('name', 'Unknown'),
                'order': official.get('order', 0)
            })

        return officials if officials else None
    except Exception as e:
        print(f"⚠️  심판 정보 파싱 실패: {e}")
        return None

def parse_preview_notes(data: Dict) -> Optional[str]:
    """프리뷰 노트/분석 파싱"""
    try:
        if 'article' in data:
            article = data['article']
            headline = article.get('headline', '')
            description = article.get('description', '')

            return f"{headline}\n{description}" if headline or description else None

        if 'notes' in data:
            notes = data['notes']
            if notes:
                return notes[0].get('text', None)

        return None
    except Exception as e:
        print(f"⚠️  프리뷰 노트 파싱 실패: {e}")
        return None

def get_game_preview(game_id: str) -> Dict:
    """게임 프리뷰 종합 정보"""
    print(f"🔍 프리뷰 가져오는 중: {game_id}")

    data = fetch_game_summary(game_id)
    if not data:
        return {}

    # 기본 정보
    header = data.get('header', {}).get('competitions', [{}])[0]
    home_team = None
    away_team = None

    for team in header.get('competitors', []):
        if team.get('homeAway') == 'home':
            home_team = team.get('team', {}).get('abbreviation', 'Unknown')
        else:
            away_team = team.get('team', {}).get('abbreviation', 'Unknown')

    preview = {
        'game_id': game_id,
        'home_team': home_team,
        'away_team': away_team,
        'odds': parse_odds(data),
        'predictions': parse_predictions(data),
        'injuries': parse_injuries(data),
        'officials': parse_officials(data),
        'preview_notes': parse_preview_notes(data),
        'has_officials': parse_officials(data) is not None,
        'fetched_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    return preview

def fetch_all_previews(games_file: str = "tomorrow_games.json") -> List[Dict]:
    """모든 내일 경기의 프리뷰 가져오기"""
    filepath = f"/Users/js/g9/nba_data/state_graph/{games_file}"

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            games = json.load(f)
    except FileNotFoundError:
        print(f"❌ {games_file} 파일이 없습니다.")
        return []

    previews = []
    for game in games:
        game_id = game['game_id']
        preview = get_game_preview(game_id)

        if preview:
            previews.append(preview)

            # 심판 정보 있는지 표시
            if preview['has_officials']:
                print(f"  ✅ 심판 정보 있음")
            else:
                print(f"  ⚠️  심판 정보 없음 (경기 전 공개 예정)")

    return previews

def display_preview(preview: Dict):
    """프리뷰 정보 출력"""
    print("\n" + "=" * 80)
    print(f"📋 프리뷰: {preview['away_team']} @ {preview['home_team']}")
    print("=" * 80)

    # 배당 정보
    if preview['odds']:
        odds = preview['odds']
        print(f"\n💰 배당 정보 ({odds['provider']}):")
        print(f"  스프레드: {odds['spread']}")
        print(f"  오버언더: {odds['over_under']}")
        print(f"  홈 머니라인: {odds['home_moneyline']}")
        print(f"  원정 머니라인: {odds['away_moneyline']}")
        if odds['details']:
            print(f"  상세: {odds['details']}")

    # 예측 정보
    if preview['predictions']:
        pred = preview['predictions']
        try:
            home_prob = float(pred.get('home_win_probability', 0))
            away_prob = float(pred.get('away_win_probability', 0))
            home_score = float(pred.get('home_projected_score', 0))
            away_score = float(pred.get('away_projected_score', 0))

            print(f"\n📊 ESPN 예측:")
            print(f"  {preview['home_team']} 승률: {home_prob:.1f}% (예상 {home_score:.0f}점)")
            print(f"  {preview['away_team']} 승률: {away_prob:.1f}% (예상 {away_score:.0f}점)")
        except (ValueError, TypeError):
            print(f"\n📊 ESPN 예측: 정보 없음")

    # 부상자 정보
    injuries = preview['injuries']
    if injuries['home'] or injuries['away']:
        print(f"\n🏥 부상자 명단:")
        for injury in injuries['home'] + injuries['away']:
            print(f"  [{injury['team']}] {injury['name']} ({injury['position']}) - {injury['status']}: {injury['details']}")

    # 심판 정보
    if preview['officials']:
        print(f"\n👨‍⚖️ 심판진:")
        for official in preview['officials']:
            print(f"  {official['position']}: {official['name']}")
    else:
        print(f"\n⚠️  심판 정보 아직 공개 안됨")

    # 프리뷰 노트
    if preview['preview_notes']:
        print(f"\n📝 프리뷰 노트:")
        print(f"  {preview['preview_notes'][:200]}...")

    print(f"\n조회 시각: {preview['fetched_at']}")

def save_previews(previews: List[Dict], filename: str = "tomorrow_previews.json"):
    """프리뷰 정보 저장"""
    filepath = f"/Users/js/g9/nba_data/state_graph/{filename}"

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(previews, f, indent=2, ensure_ascii=False)

    print(f"\n✅ 프리뷰 저장: {filepath}")

def main():
    """메인 함수"""
    print("=" * 80)
    print("ESPN 게임 프리뷰 정보 수집")
    print("=" * 80)

    previews = fetch_all_previews()

    if not previews:
        print("❌ 프리뷰 정보를 가져올 수 없습니다.")
        return

    # 출력
    for preview in previews:
        display_preview(preview)

    # 저장
    save_previews(previews)

    # 통계
    with_officials = sum(1 for p in previews if p['has_officials'])
    print("\n" + "=" * 80)
    print(f"✅ 총 {len(previews)}경기 프리뷰 수집 완료")
    print(f"   심판 정보 있음: {with_officials}경기")
    print(f"   심판 정보 없음: {len(previews) - with_officials}경기")
    print("=" * 80)

if __name__ == "__main__":
    main()
