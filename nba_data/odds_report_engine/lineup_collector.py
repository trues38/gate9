#!/usr/bin/env python3
"""
G9 Lineup Collector
예상 라인업 수집 (3단계 Fallback)
"""

import requests
from datetime import datetime
import json

class LineupCollector:
    """라인업 수집기 (3단계 Fallback)"""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Referer': 'https://www.nba.com/',
        }

        # NBA 팀 ID 매핑
        self.team_ids = {
            'ATL': 1610612737, 'BOS': 1610612738, 'BKN': 1610612751,
            'CHA': 1610612766, 'CHI': 1610612741, 'CLE': 1610612739,
            'DAL': 1610612742, 'DEN': 1610612743, 'DET': 1610612765,
            'GSW': 1610612744, 'HOU': 1610612745, 'IND': 1610612754,
            'LAC': 1610612746, 'LAL': 1610612747, 'MEM': 1610612763,
            'MIA': 1610612748, 'MIL': 1610612749, 'MIN': 1610612750,
            'NOP': 1610612740, 'NYK': 1610612752, 'OKC': 1610612760,
            'ORL': 1610612753, 'PHI': 1610612755, 'PHX': 1610612756,
            'POR': 1610612757, 'SAC': 1610612758, 'SAS': 1610612759,
            'TOR': 1610612761, 'UTA': 1610612762, 'WAS': 1610612764
        }

    def get_predicted_lineup(self, team_abbr, game_date=None):
        """
        예상 라인업 조회 (3단계 Fallback)

        Args:
            team_abbr: 팀 약자 (예: 'GSW', 'TOR')
            game_date: YYYY-MM-DD 형식 (기본값: 오늘)

        Returns:
            dict: 예상 라인업 정보
        """
        if game_date is None:
            game_date = datetime.now().strftime('%Y-%m-%d')

        # Step 1: NBA API (최근 경기 스타팅 라인업)
        lineup = self._get_from_nba_api(team_abbr)
        if lineup:
            lineup['source'] = 'NBA API (최근 경기 평균)'
            lineup['confidence'] = 'MEDIUM'
            return lineup

        # Step 2: Fallback - 기본 로스터
        lineup = self._get_from_roster(team_abbr)
        if lineup:
            lineup['source'] = 'Team Roster (기본 스타터 예상)'
            lineup['confidence'] = 'LOW'
            return lineup

        # Step 3: 최종 Fallback
        return self._get_default_lineup(team_abbr)

    def _get_from_nba_api(self, team_abbr):
        """
        Step 1: NBA Stats API에서 최근 경기 스타팅 라인업 조회
        """
        try:
            team_id = self.team_ids.get(team_abbr)
            if not team_id:
                return None

            # CommonTeamRoster 엔드포인트 사용
            url = f"https://stats.nba.com/stats/commonteamroster"
            params = {
                'Season': '2024-25',
                'TeamID': team_id
            }

            response = requests.get(
                url,
                headers=self.headers,
                params=params,
                timeout=10
            )

            if response.status_code != 200:
                return None

            data = response.json()
            players = data.get('resultSets', [{}])[0].get('rowSet', [])

            if not players:
                return None

            # 최근 스타팅 5 (간단히 처음 5명으로 가정)
            starters = []
            for player in players[:5]:
                starters.append({
                    'name': player[3],  # PLAYER
                    'position': player[5],  # POSITION
                    'number': player[4]  # NUM
                })

            return {
                'starters': starters,
                'total_players': len(players)
            }

        except Exception as e:
            print(f"⚠️ NBA API 조회 실패: {e}")
            return None

    def _get_from_roster(self, team_abbr):
        """
        Step 2: 팀 로스터에서 예상 스타터 반환
        (실제로는 더 정교한 로직 필요)
        """
        # 주요 팀들의 알려진 스타터 (2024-25 시즌)
        known_starters = {
            'GSW': [
                {'name': 'Stephen Curry', 'position': 'PG'},
                {'name': 'Andrew Wiggins', 'position': 'SG'},
                {'name': 'Jonathan Kuminga', 'position': 'SF'},
                {'name': 'Draymond Green', 'position': 'PF'},
                {'name': 'Kevon Looney', 'position': 'C'}
            ],
            'LAL': [
                {'name': 'D\'Angelo Russell', 'position': 'PG'},
                {'name': 'Austin Reaves', 'position': 'SG'},
                {'name': 'LeBron James', 'position': 'SF'},
                {'name': 'Anthony Davis', 'position': 'PF'},
                {'name': 'Jarred Vanderbilt', 'position': 'C'}
            ],
            'BOS': [
                {'name': 'Jrue Holiday', 'position': 'PG'},
                {'name': 'Derrick White', 'position': 'SG'},
                {'name': 'Jaylen Brown', 'position': 'SF'},
                {'name': 'Jayson Tatum', 'position': 'PF'},
                {'name': 'Kristaps Porzingis', 'position': 'C'}
            ],
            'MIL': [
                {'name': 'Damian Lillard', 'position': 'PG'},
                {'name': 'Khris Middleton', 'position': 'SG'},
                {'name': 'Giannis Antetokounmpo', 'position': 'PF'},
                {'name': 'Brook Lopez', 'position': 'C'}
            ],
            'DEN': [
                {'name': 'Jamal Murray', 'position': 'PG'},
                {'name': 'Kentavious Caldwell-Pope', 'position': 'SG'},
                {'name': 'Michael Porter Jr.', 'position': 'SF'},
                {'name': 'Aaron Gordon', 'position': 'PF'},
                {'name': 'Nikola Jokic', 'position': 'C'}
            ],
            'PHX': [
                {'name': 'Bradley Beal', 'position': 'PG'},
                {'name': 'Devin Booker', 'position': 'SG'},
                {'name': 'Kevin Durant', 'position': 'SF'},
                {'name': 'Jusuf Nurkic', 'position': 'C'}
            ]
        }

        starters = known_starters.get(team_abbr)
        if starters:
            return {
                'starters': starters,
                'note': '알려진 스타팅 라인업 (시즌 평균)'
            }

        return None

    def _get_default_lineup(self, team_abbr):
        """
        Step 3: 최종 Fallback (기본값)
        """
        return {
            'starters': [
                {'name': 'TBD', 'position': 'PG'},
                {'name': 'TBD', 'position': 'SG'},
                {'name': 'TBD', 'position': 'SF'},
                {'name': 'TBD', 'position': 'PF'},
                {'name': 'TBD', 'position': 'C'}
            ],
            'source': 'Default (경기 30분 전 확인 필요)',
            'confidence': 'VERY_LOW',
            'note': f'{team_abbr} 공식 Twitter 또는 NBA.com 확인'
        }

    def get_lineup_comparison(self, home_team, away_team):
        """
        양 팀 라인업 비교

        Args:
            home_team: 홈팀 약자
            away_team: 원정팀 약자

        Returns:
            dict: 라인업 비교 결과
        """
        home_lineup = self.get_predicted_lineup(home_team)
        away_lineup = self.get_predicted_lineup(away_team)

        return {
            'home': {
                'team': home_team,
                'lineup': home_lineup
            },
            'away': {
                'team': away_team,
                'lineup': away_lineup
            },
            'comparison': {
                'home_confidence': home_lineup.get('confidence', 'LOW'),
                'away_confidence': away_lineup.get('confidence', 'LOW'),
                'note': '경기 시작 30분 전 최종 확인 권장'
            }
        }


def main():
    """테스트"""
    collector = LineupCollector()

    print("=== G9 Lineup Collector ===\n")

    # 단일 팀 라인업
    print("Golden State Warriors 예상 라인업:")
    gsw_lineup = collector.get_predicted_lineup('GSW')
    print(json.dumps(gsw_lineup, indent=2, ensure_ascii=False))

    print("\n" + "="*50 + "\n")

    # 양 팀 비교
    print("GSW vs LAL 라인업 비교:")
    comparison = collector.get_lineup_comparison('GSW', 'LAL')
    print(json.dumps(comparison, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
