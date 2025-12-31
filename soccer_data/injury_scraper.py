#!/usr/bin/env python3
"""
Transfermarkt Injury Data Scraper
부상 데이터 자동 수집 스크립트
"""

import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
import time

class InjuryScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        self.base_url = "https://www.transfermarkt.com"

        # 주요 리그 URL
        self.leagues = {
            "EPL": "/premier-league/verletztespieler/wettbewerb/GB1",
            "La_liga": "/laliga/verletztespieler/wettbewerb/ES1",
            "Bundesliga": "/bundesliga/verletztespieler/wettbewerb/L1",
            "Serie_A": "/serie-a/verletztespieler/wettbewerb/IT1",
            "Ligue_1": "/ligue-1/verletztespieler/wettbewerb/FR1"
        }

    def scrape_league_injuries(self, league_name, league_url):
        """특정 리그의 부상 데이터 스크래핑"""
        url = self.base_url + league_url

        try:
            print(f"📥 Scraping {league_name}...")
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            injuries = []

            # Transfermarkt 부상 테이블 파싱
            table = soup.find('table', {'class': 'items'})
            if not table:
                print(f"⚠️  No injury table found for {league_name}")
                return []

            rows = table.find_all('tr', {'class': ['odd', 'even']})

            for row in rows:
                try:
                    # 선수 이름
                    player_cell = row.find('td', {'class': 'hauptlink'})
                    if not player_cell:
                        continue

                    player_name = player_cell.find('a').text.strip()

                    # 팀 이름
                    team_cell = row.find_all('td')[3]
                    team_link = team_cell.find('a')
                    team_name = team_link.get('title', '').strip() if team_link else 'Unknown'

                    # 부상 종류
                    injury_cell = row.find_all('td')[4]
                    injury_type = injury_cell.text.strip()

                    # 복귀 예정일
                    return_cell = row.find_all('td')[5]
                    expected_return = return_cell.text.strip()

                    # 포지션 (선수 이미지 옆)
                    position_td = row.find_all('td')[1]
                    position = position_td.find('tr')
                    position_text = position.find_all('td')[1].text.strip() if position else 'Unknown'

                    # 상태 판단
                    status = "OUT"
                    if "?" in expected_return or "doubt" in injury_type.lower():
                        status = "DOUBTFUL"

                    # 영향도 판단 (포지션 기반)
                    impact = self._determine_impact(position_text, injury_type)

                    injuries.append({
                        "league": league_name,
                        "team": team_name,
                        "player": player_name,
                        "position": position_text,
                        "status": status,
                        "injury_type": injury_type,
                        "expected_return": expected_return,
                        "impact": impact,
                        "source": "Transfermarkt",
                        "date": datetime.now().strftime("%Y-%m-%d")
                    })

                except Exception as e:
                    print(f"   ⚠️  Error parsing row: {e}")
                    continue

            print(f"   ✅ Found {len(injuries)} injuries")
            return injuries

        except Exception as e:
            print(f"   ❌ Error scraping {league_name}: {e}")
            return []

    def _determine_impact(self, position, injury_type):
        """부상 영향도 판단"""
        # 공격수/공격형 미드필더는 CRITICAL
        if any(pos in position for pos in ['Forward', 'Striker', 'Winger', 'Attacking']):
            return "CRITICAL"

        # 중앙 미드필더 또는 중앙 수비수
        elif any(pos in position for pos in ['Central', 'Defensive', 'Goalkeeper']):
            return "HIGH"

        # 측면 수비수 또는 보조 역할
        else:
            return "MEDIUM"

    def scrape_all_leagues(self):
        """모든 리그 스크래핑"""
        all_injuries = []

        for league_name, league_url in self.leagues.items():
            injuries = self.scrape_league_injuries(league_name, league_url)
            all_injuries.extend(injuries)

            # Rate limiting (서버 부하 방지)
            time.sleep(2)

        return all_injuries

    def save_to_file(self, injuries, filepath="processed/injury_data.json"):
        """JSON 파일로 저장"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(injuries, f, indent=2, ensure_ascii=False)

        print(f"\n💾 Saved {len(injuries)} injuries to {filepath}")

    def get_summary(self, injuries):
        """부상 요약 통계"""
        summary = {
            "total": len(injuries),
            "by_league": {},
            "by_status": {"OUT": 0, "DOUBTFUL": 0},
            "by_impact": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0},
            "critical_players": []
        }

        for injury in injuries:
            # 리그별
            league = injury['league']
            summary['by_league'][league] = summary['by_league'].get(league, 0) + 1

            # 상태별
            summary['by_status'][injury['status']] = summary['by_status'].get(injury['status'], 0) + 1

            # 영향도별
            summary['by_impact'][injury['impact']] = summary['by_impact'].get(injury['impact'], 0) + 1

            # Critical 선수 리스트
            if injury['impact'] == 'CRITICAL':
                summary['critical_players'].append({
                    "player": injury['player'],
                    "team": injury['team'],
                    "league": injury['league'],
                    "status": injury['status']
                })

        return summary

def main():
    print("=" * 60)
    print("⚽ Soccer Injury Data Scraper - Transfermarkt")
    print("=" * 60)

    scraper = InjuryScraper()

    # 스크래핑 실행
    injuries = scraper.scrape_all_leagues()

    if not injuries:
        print("\n❌ No injuries found!")
        return

    # 저장
    scraper.save_to_file(injuries)

    # 요약
    summary = scraper.get_summary(injuries)

    print("\n" + "=" * 60)
    print("📊 Injury Summary")
    print("=" * 60)
    print(f"\nTotal Injuries: {summary['total']}")

    print(f"\n📍 By League:")
    for league, count in summary['by_league'].items():
        print(f"   {league:15s} {count:3d} injuries")

    print(f"\n🚨 By Status:")
    for status, count in summary['by_status'].items():
        print(f"   {status:15s} {count:3d}")

    print(f"\n💥 By Impact:")
    for impact, count in summary['by_impact'].items():
        print(f"   {impact:15s} {count:3d}")

    print(f"\n🔥 Critical Players OUT ({len(summary['critical_players'])}):")
    for player in summary['critical_players'][:10]:
        print(f"   {player['player']:30s} ({player['team']}, {player['league']}) - {player['status']}")

    print("\n✅ Scraping complete!")

if __name__ == "__main__":
    main()
