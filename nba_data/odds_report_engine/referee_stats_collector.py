#!/usr/bin/env python3
"""
G9 Referee Stats Collector
NBA Stats API를 사용하여 심판 정보 수집
"""

import requests
from datetime import datetime
import json

class RefereeStatsCollector:
    """심판 통계 수집기"""

    def __init__(self):
        self.base_url = "https://stats.nba.com/stats"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Referer': 'https://www.nba.com/',
        }

        # 심판 데이터 캐시 (시즌별)
        self.referee_cache = {}

    def get_todays_officials(self, game_date=None):
        """
        오늘 경기의 심판 정보 조회

        Args:
            game_date: YYYY-MM-DD 형식 (기본값: 오늘)

        Returns:
            dict: 경기별 심판 정보
        """
        if game_date is None:
            game_date = datetime.now().strftime('%Y-%m-%d')

        try:
            # NBA scoreboard API로 오늘 경기 조회
            url = f"https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json"
            response = requests.get(url, headers=self.headers, timeout=10)

            if response.status_code != 200:
                print(f"⚠️ NBA API 오류: {response.status_code}")
                return self._get_fallback_officials()

            data = response.json()
            officials_data = {}

            # 각 경기의 심판 정보 추출
            for game in data.get('scoreboard', {}).get('games', []):
                game_id = game.get('gameId')
                officials = game.get('gameLeaders', {}).get('officials', [])

                if officials:
                    officials_data[game_id] = {
                        'referees': [off.get('name', 'Unknown') for off in officials],
                        'crew_chief': officials[0].get('name', 'Unknown') if officials else 'Unknown'
                    }

            return officials_data

        except Exception as e:
            print(f"⚠️ 심판 정보 조회 실패: {e}")
            return self._get_fallback_officials()

    def get_referee_stats(self, referee_name):
        """
        특정 심판의 시즌 통계 조회

        Args:
            referee_name: 심판 이름

        Returns:
            dict: 심판 통계 (경기 수, 평균 파울, Strictness Index 등)
        """
        # 캐시 확인
        if referee_name in self.referee_cache:
            return self.referee_cache[referee_name]

        try:
            # 실제 API 호출 (구현 시)
            # 현재는 기본값 반환
            stats = {
                'name': referee_name,
                'games_this_season': 45,
                'avg_fouls_called': 21.3,
                'avg_technical_fouls': 0.8,
                'strictness_index': self._calculate_strictness(referee_name),
                'home_advantage': 0.52  # 홈팀 승률
            }

            self.referee_cache[referee_name] = stats
            return stats

        except Exception as e:
            print(f"⚠️ 심판 통계 조회 실패: {e}")
            return self._get_default_referee_stats(referee_name)

    def _calculate_strictness(self, referee_name):
        """
        심판의 Strictness Index 계산 (0-1 scale)
        1에 가까울수록 엄격함
        """
        # 실제로는 Historical data 기반 계산
        # 현재는 알려진 심판들에 대해 기본값 제공

        strict_refs = {
            'Scott Foster': 0.85,
            'Tony Brothers': 0.82,
            'Kane Fitzgerald': 0.78,
            'Marc Davis': 0.75,
            'Ed Malloy': 0.73,
        }

        lenient_refs = {
            'Zach Zarba': 0.45,
            'James Capers': 0.48,
            'Derrick Stafford': 0.50,
        }

        if referee_name in strict_refs:
            return strict_refs[referee_name]
        elif referee_name in lenient_refs:
            return lenient_refs[referee_name]
        else:
            return 0.65  # 평균값

    def _get_fallback_officials(self):
        """
        Fallback: 기본 심판 정보 반환
        """
        return {
            'default': {
                'referees': ['TBD', 'TBD', 'TBD'],
                'crew_chief': 'TBD',
                'note': '경기 30분 전 @OfficialNBARefs 확인'
            }
        }

    def _get_default_referee_stats(self, referee_name):
        """
        기본 심판 통계 반환
        """
        return {
            'name': referee_name,
            'games_this_season': 'N/A',
            'avg_fouls_called': 'N/A',
            'avg_technical_fouls': 'N/A',
            'strictness_index': 0.65,
            'home_advantage': 0.50
        }

    def get_referee_impact_analysis(self, referee_name, home_team, away_team):
        """
        심판이 특정 경기에 미치는 영향 분석

        Args:
            referee_name: 심판 이름
            home_team: 홈팀 약자
            away_team: 원정팀 약자

        Returns:
            dict: 영향 분석 결과
        """
        stats = self.get_referee_stats(referee_name)

        analysis = {
            'referee': referee_name,
            'strictness': stats['strictness_index'],
            'expected_fouls': stats['avg_fouls_called'],
            'impact': 'NEUTRAL'
        }

        # Strictness에 따른 영향 판단
        if stats['strictness_index'] > 0.75:
            analysis['impact'] = 'HIGH_FOULS'
            analysis['note'] = f"{referee_name}은 엄격한 심판 (Strictness {stats['strictness_index']:.2f})"
            analysis['betting_impact'] = "Under 베팅 유리 (게임 템포 느려짐)"
        elif stats['strictness_index'] < 0.55:
            analysis['impact'] = 'LOW_FOULS'
            analysis['note'] = f"{referee_name}은 관대한 심판 (Strictness {stats['strictness_index']:.2f})"
            analysis['betting_impact'] = "Over 베팅 유리 (게임 템포 빠름)"
        else:
            analysis['impact'] = 'NEUTRAL'
            analysis['note'] = f"{referee_name}은 평균적인 심판 (Strictness {stats['strictness_index']:.2f})"
            analysis['betting_impact'] = "심판 영향 중립"

        return analysis


def main():
    """테스트"""
    collector = RefereeStatsCollector()

    print("=== G9 Referee Stats Collector ===\n")

    # 오늘 경기 심판 조회
    print("오늘 경기 심판:")
    officials = collector.get_todays_officials()
    print(json.dumps(officials, indent=2, ensure_ascii=False))

    print("\n" + "="*50 + "\n")

    # 특정 심판 통계
    test_refs = ['Scott Foster', 'Tony Brothers', 'Zach Zarba']
    for ref in test_refs:
        stats = collector.get_referee_stats(ref)
        print(f"{ref}:")
        print(f"  - Games: {stats['games_this_season']}")
        print(f"  - Avg Fouls: {stats['avg_fouls_called']}")
        print(f"  - Strictness: {stats['strictness_index']:.2f}")
        print()

    print("="*50 + "\n")

    # 영향 분석
    analysis = collector.get_referee_impact_analysis('Scott Foster', 'GSW', 'TOR')
    print("영향 분석 (Scott Foster):")
    print(json.dumps(analysis, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
