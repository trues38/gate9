#!/usr/bin/env python3
"""
내일 경기의 실제 컨텍스트 계산
- 각 팀의 휴식일 계산 (마지막 경기로부터)
- 백투백 여부
- 부상자 수
- 심판 정보 (공개 시)
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from neo4j import GraphDatabase

class GameContextCalculator:
    def __init__(self, uri="bolt://localhost:7687", user="neo4j", password="password123"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def get_last_game_date(self, team: str, before_date: str) -> Optional[str]:
        """특정 날짜 이전의 팀의 마지막 경기 날짜"""
        query = """
        MATCH (game:GameState)
        WHERE (game.home_team = $team OR game.away_team = $team)
          AND game.date < date($before_date)
        RETURN game.date AS last_game_date
        ORDER BY game.date DESC
        LIMIT 1
        """

        with self.driver.session() as session:
            result = session.run(query, team=team, before_date=before_date)
            record = result.single()
            return record['last_game_date'] if record else None

    def calculate_rest_days(self, team: str, game_date: str) -> int:
        """휴식일 계산"""
        last_game = self.get_last_game_date(team, game_date)

        if not last_game:
            return 7  # 데이터 없으면 충분한 휴식으로 간주

        # 날짜 차이 계산
        game_dt = datetime.strptime(game_date, "%Y-%m-%d")
        last_dt = datetime.strptime(str(last_game), "%Y-%m-%d")

        rest_days = (game_dt - last_dt).days - 1  # 경기 당일 제외

        return max(0, rest_days)

    def calculate_game_context(self, game: Dict, preview: Dict) -> Dict:
        """경기의 전체 컨텍스트 계산"""
        home_team = game['home_team']['abbr']
        away_team = game['away_team']['abbr']
        game_date = game['date']

        # 휴식일 계산
        home_rest = self.calculate_rest_days(home_team, game_date)
        away_rest = self.calculate_rest_days(away_team, game_date)

        # 백투백 여부
        home_b2b = (home_rest == 0)
        away_b2b = (away_rest == 0)

        # 부상자 수
        injuries = preview.get('injuries', {'home': [], 'away': []})
        home_injuries_count = len([inj for inj in injuries['home'] + injuries['away']
                                   if inj.get('team') == home_team])
        away_injuries_count = len([inj for inj in injuries['home'] + injuries['away']
                                   if inj.get('team') == away_team])

        # 심판 정보
        officials = preview.get('officials', [])
        referee_name = officials[0]['name'] if officials else None

        context = {
            'game_date': game_date,
            'home_team': home_team,
            'away_team': away_team,
            'home_rest_days': home_rest,
            'away_rest_days': away_rest,
            'home_back_to_back': home_b2b,
            'away_back_to_back': away_b2b,
            'rest_advantage': home_rest - away_rest,
            'home_injuries_count': home_injuries_count,
            'away_injuries_count': away_injuries_count,
            'referee': referee_name,
            'has_referee': referee_name is not None
        }

        return context

    def calculate_all_contexts(self) -> List[Dict]:
        """모든 내일 경기의 컨텍스트 계산"""
        # 내일 경기 로드
        games_path = "/Users/js/g9/nba_data/state_graph/tomorrow_games.json"
        with open(games_path, 'r', encoding='utf-8') as f:
            games = json.load(f)

        # 프리뷰 로드
        preview_path = "/Users/js/g9/nba_data/state_graph/tomorrow_previews.json"
        try:
            with open(preview_path, 'r', encoding='utf-8') as f:
                previews = json.load(f)
        except FileNotFoundError:
            previews = []

        preview_map = {p['game_id']: p for p in previews}

        # 컨텍스트 계산
        contexts = []
        for game in games:
            game_id = game['game_id']
            preview = preview_map.get(game_id, {})

            context = self.calculate_game_context(game, preview)
            context['game_id'] = game_id

            contexts.append(context)

        return contexts

    def display_contexts(self, contexts: List[Dict]):
        """컨텍스트 출력"""
        print("=" * 80)
        print("내일 경기 컨텍스트 분석")
        print("=" * 80)

        for ctx in contexts:
            print(f"\n📋 {ctx['away_team']} @ {ctx['home_team']}")
            print(f"   날짜: {ctx['game_date']}")

            # 휴식일
            print(f"\n   휴식일:")
            rest_emoji_home = "🔴" if ctx['home_back_to_back'] else "🟢"
            rest_emoji_away = "🔴" if ctx['away_back_to_back'] else "🟢"

            print(f"   {rest_emoji_home} {ctx['home_team']}: {ctx['home_rest_days']}일" +
                  (" (백투백)" if ctx['home_back_to_back'] else ""))
            print(f"   {rest_emoji_away} {ctx['away_team']}: {ctx['away_rest_days']}일" +
                  (" (백투백)" if ctx['away_back_to_back'] else ""))

            # 휴식일 우위
            if ctx['rest_advantage'] >= 2:
                print(f"   ✅ {ctx['home_team']} 휴식 우위 (+{ctx['rest_advantage']}일)")
            elif ctx['rest_advantage'] <= -2:
                print(f"   ✅ {ctx['away_team']} 휴식 우위 (+{abs(ctx['rest_advantage'])}일)")

            # 부상자
            print(f"\n   부상자:")
            print(f"   🏥 {ctx['home_team']}: {ctx['home_injuries_count']}명")
            print(f"   🏥 {ctx['away_team']}: {ctx['away_injuries_count']}명")

            # 심판
            if ctx['has_referee']:
                print(f"\n   👨‍⚖️ 심판: {ctx['referee']}")
            else:
                print(f"\n   ⚠️  심판 정보 미공개")

        print("\n" + "=" * 80)

    def save_contexts(self, contexts: List[Dict], filename: str = "tomorrow_contexts.json"):
        """컨텍스트 저장"""
        filepath = f"/Users/js/g9/nba_data/state_graph/{filename}"

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(contexts, f, indent=2, ensure_ascii=False)

        print(f"✅ 컨텍스트 저장: {filepath}")

def main():
    calculator = GameContextCalculator()

    try:
        print("내일 경기 컨텍스트 계산 중...\n")

        contexts = calculator.calculate_all_contexts()

        calculator.display_contexts(contexts)
        calculator.save_contexts(contexts)

        # 통계
        b2b_count = sum(1 for c in contexts if c['home_back_to_back'] or c['away_back_to_back'])
        with_referee = sum(1 for c in contexts if c['has_referee'])

        print(f"\n📊 통계:")
        print(f"   총 경기: {len(contexts)}개")
        print(f"   백투백 포함 경기: {b2b_count}개")
        print(f"   심판 정보 공개: {with_referee}개")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        calculator.close()

if __name__ == "__main__":
    main()
