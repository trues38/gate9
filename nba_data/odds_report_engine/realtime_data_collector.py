#!/usr/bin/env python3
"""
실시간 NBA 데이터 통합 수집기
- Odds (The Odds API)
- Injuries (ESPN API)
- Referees (Basketball Reference)
- Lineups (Twitter/팀 공식)
"""

import sys
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

# Add parent paths
sys.path.append('/Users/js/g9/nba_data/quant_engine')
sys.path.append('/Users/js/g9/nba_data/state_graph')

from odds_api_adapter import OddsAPIAdapter


class RealtimeDataCollector:
    """실시간 NBA 데이터 통합 수집"""

    def __init__(self):
        self.odds_adapter = OddsAPIAdapter()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }

    def collect_all_data(self, home_team: str, away_team: str) -> Dict:
        """
        특정 경기의 모든 실시간 데이터 수집

        Returns:
            {
                "odds": {...},
                "injuries": [...],
                "referees": [...],
                "lineups": {...}
            }
        """
        print(f"\n{'='*60}")
        print(f"🔄 실시간 데이터 수집: {away_team} @ {home_team}")
        print(f"{'='*60}\n")

        # 1. Odds
        print("💰 Odds 수집 중...")
        odds_data = self._collect_odds(home_team, away_team)

        # 2. Injuries
        print("\n🚑 부상자 정보 수집 중...")
        injury_data = self._collect_injuries([home_team, away_team])

        # 3. Referees
        print("\n👔 심판 정보 수집 중...")
        referee_data = self._collect_referees()

        # 4. Lineups (placeholder for now)
        print("\n👥 라인업 정보 수집 중...")
        lineup_data = self._collect_lineups(home_team, away_team)

        result = {
            "collected_at": datetime.now().isoformat(),
            "game": {
                "home_team": home_team,
                "away_team": away_team
            },
            "odds": odds_data,
            "injuries": injury_data,
            "referees": referee_data,
            "lineups": lineup_data
        }

        print(f"\n{'='*60}")
        print("✅ 실시간 데이터 수집 완료!")
        print(f"{'='*60}\n")

        return result

    def _collect_odds(self, home_team: str, away_team: str) -> Dict:
        """Odds 수집"""
        try:
            all_odds = self.odds_adapter.get_nba_odds()

            if not all_odds['success']:
                return {"error": "Failed to fetch odds"}

            # Find matching game
            for game in all_odds['games']:
                if self._team_matches(home_team, game['home_team']) and \
                   self._team_matches(away_team, game['away_team']):
                    best_odds = self.odds_adapter.extract_best_odds(game)
                    return {
                        "success": True,
                        "game_time": game['commence_time'],
                        "moneyline": best_odds.get('h2h', {}),
                        "spreads": best_odds.get('spreads', {}),
                        "totals": best_odds.get('totals', {})
                    }

            return {"error": "Game not found in odds"}

        except Exception as e:
            return {"error": str(e)}

    def _collect_injuries(self, teams: List[str]) -> List[Dict]:
        """부상자 정보 수집 (ESPN API)"""
        injuries = []

        team_ids_map = {
            "ATL": 1, "BOS": 2, "BKN": 17, "CHA": 30, "CHI": 4,
            "CLE": 5, "DAL": 6, "DEN": 7, "DET": 8, "GSW": 9,
            "HOU": 10, "IND": 11, "LAC": 12, "LAL": 13, "MEM": 29,
            "MIA": 14, "MIL": 15, "MIN": 16, "NOP": 3, "NYK": 18,
            "OKC": 25, "ORL": 19, "PHI": 20, "PHX": 21, "POR": 22,
            "SAC": 23, "SAS": 24, "TOR": 28, "UTA": 26, "WAS": 27
        }

        for team in teams:
            team_abbr = self._get_team_abbr(team)
            team_id = team_ids_map.get(team_abbr)

            if not team_id:
                continue

            try:
                url = f"http://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{team_id}/roster"
                resp = requests.get(url, headers=self.headers, timeout=10)

                if resp.status_code == 200:
                    data = resp.json()
                    team_name = data.get('team', {}).get('displayName', team)
                    athletes = data.get('athletes', [])

                    for player in athletes:
                        player_injuries = player.get('injuries', [])
                        if player_injuries:
                            for inj in player_injuries:
                                injuries.append({
                                    "team": team_name,
                                    "player": player.get('displayName'),
                                    "status": inj.get('status', 'Unknown'),
                                    "type": inj.get('type', 'Unknown'),
                                    "date": inj.get('date')
                                })

            except Exception as e:
                print(f"  ⚠️ {team} 부상자 수집 실패: {e}")

        if injuries:
            print(f"  ✓ {len(injuries)}명 부상자 발견")
        else:
            print(f"  ✓ 부상자 없음")

        return injuries

    def _collect_referees(self) -> List[Dict]:
        """
        심판 정보 수집 (Basketball Reference)

        Note: 실제로는 경기별 심판 배정이 필요하지만,
        현재는 시즌 통계 수집
        """
        try:
            url = "https://www.basketball-reference.com/referees/"
            resp = requests.get(url, headers=self.headers, timeout=15)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.content, "html.parser")
            table = soup.find("table", {"id": "referees"})

            if not table:
                return []

            referees = []
            tbody = table.find("tbody")
            rows = tbody.find_all("tr")[:10]  # Top 10 referees

            for row in rows:
                cols = row.find_all(["th", "td"])
                if len(cols) >= 3:
                    name_tag = cols[0].find("a")
                    if name_tag:
                        referees.append({
                            "name": name_tag.text.strip(),
                            "games": cols[1].text.strip() if len(cols) > 1 else "N/A"
                        })

            print(f"  ✓ {len(referees)}명 심판 정보 수집")
            return referees

        except Exception as e:
            print(f"  ⚠️ 심판 정보 수집 실패: {e}")
            return []

    def _collect_lineups(self, home_team: str, away_team: str) -> Dict:
        """
        라인업 정보 수집

        Note: 실제로는 Twitter API 또는 팀 공식 사이트에서 수집
        현재는 placeholder
        """
        # TODO: Twitter API 또는 NBA Stats API 연동
        print(f"  ⚠️ 라인업 수집 미구현 (경기 30분 전 팀 공식 발표)")

        return {
            "home": {
                "team": home_team,
                "starters": [],
                "available": False,
                "note": "경기 30분 전 확인 필요"
            },
            "away": {
                "team": away_team,
                "starters": [],
                "available": False,
                "note": "경기 30분 전 확인 필요"
            }
        }

    def _team_matches(self, search_term: str, team_name: str) -> bool:
        """팀 이름 매칭 (약어 지원)"""
        search = search_term.upper()
        team = team_name.upper()

        if search in team or team in search:
            return True

        if len(search) <= 5:
            words = team.split()
            initials = ''.join([w[0] for w in words if w])
            if search == initials:
                return True
            if any(search in word for word in words):
                return True

        return False

    def _get_team_abbr(self, team_name: str) -> str:
        """팀 이름 → 약어 변환"""
        abbr_map = {
            "ATLANTA": "ATL", "BOSTON": "BOS", "BROOKLYN": "BKN",
            "CHARLOTTE": "CHA", "CHICAGO": "CHI", "CLEVELAND": "CLE",
            "DALLAS": "DAL", "DENVER": "DEN", "DETROIT": "DET",
            "GOLDEN STATE": "GSW", "WARRIORS": "GSW",
            "HOUSTON": "HOU", "INDIANA": "IND",
            "CLIPPERS": "LAC", "LAKERS": "LAL", "MEMPHIS": "MEM",
            "MIAMI": "MIA", "MILWAUKEE": "MIL", "MINNESOTA": "MIN",
            "NEW ORLEANS": "NOP", "PELICANS": "NOP",
            "NEW YORK": "NYK", "KNICKS": "NYK",
            "OKLAHOMA": "OKC", "THUNDER": "OKC",
            "ORLANDO": "ORL", "PHILADELPHIA": "PHI", "PHOENIX": "PHX",
            "PORTLAND": "POR", "SACRAMENTO": "SAC",
            "SAN ANTONIO": "SAS", "SPURS": "SAS",
            "TORONTO": "TOR", "RAPTORS": "TOR",
            "UTAH": "UTA", "WASHINGTON": "WAS"
        }

        team_upper = team_name.upper()
        for key, abbr in abbr_map.items():
            if key in team_upper:
                return abbr

        # Fallback: 이미 약어면 그대로 반환
        if len(team_name) <= 3:
            return team_name.upper()

        return team_name[:3].upper()


def main():
    import argparse

    parser = argparse.ArgumentParser(description='실시간 NBA 데이터 수집')
    parser.add_argument('home_team', help='홈 팀 (예: TOR, Toronto)')
    parser.add_argument('away_team', help='원정 팀 (예: GSW, Warriors)')
    parser.add_argument('--output', '-o', help='출력 파일 경로')

    args = parser.parse_args()

    collector = RealtimeDataCollector()
    data = collector.collect_all_data(args.home_team, args.away_team)

    # Save to file
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\n💾 저장 완료: {args.output}")
    else:
        print("\n" + "="*60)
        print("📊 수집 결과:")
        print("="*60)
        print(json.dumps(data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
