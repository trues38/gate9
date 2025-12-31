#!/usr/bin/env python3
"""
Manual Injury Data Updater
주요 스타 선수 부상 정보 수동 업데이트 시스템

사용법:
  python3 injury_manual_updater.py
"""

import json
import os
from datetime import datetime

class ManualInjuryUpdater:
    def __init__(self, filepath="processed/injury_data_manual.json"):
        self.filepath = filepath
        self.injuries = self.load_existing()

    def load_existing(self):
        """기존 데이터 로드"""
        if os.path.exists(self.filepath):
            with open(self.filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []

    def save(self):
        """저장"""
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(self.injuries, f, indent=2, ensure_ascii=False)
        print(f"✅ Saved to {self.filepath}")

    def add_injury(self, league, team, player, position, status, injury_type, expected_return, impact):
        """부상 추가"""
        injury = {
            "league": league,
            "team": team,
            "player": player,
            "position": position,
            "status": status,
            "injury_type": injury_type,
            "expected_return": expected_return,
            "impact": impact,
            "source": "Manual",
            "date": datetime.now().strftime("%Y-%m-%d")
        }

        # 기존 항목 제거 (같은 선수)
        self.injuries = [i for i in self.injuries if i['player'] != player]

        # 새 항목 추가
        self.injuries.append(injury)
        print(f"✅ Added: {player} ({team}) - {status}")

    def remove_injury(self, player):
        """부상에서 제거 (복귀)"""
        self.injuries = [i for i in self.injuries if i['player'] != player]
        print(f"✅ Removed: {player}")

    def update_status(self, player, new_status):
        """상태 업데이트"""
        for injury in self.injuries:
            if injury['player'] == player:
                injury['status'] = new_status
                injury['date'] = datetime.now().strftime("%Y-%m-%d")
                print(f"✅ Updated: {player} → {new_status}")
                return
        print(f"⚠️  Player not found: {player}")

    def list_all(self):
        """전체 리스트 출력"""
        if not self.injuries:
            print("No injuries recorded")
            return

        print("\n" + "=" * 80)
        print(f"📋 Total Injuries: {len(self.injuries)}")
        print("=" * 80)

        # 리그별 그룹화
        by_league = {}
        for injury in self.injuries:
            league = injury['league']
            if league not in by_league:
                by_league[league] = []
            by_league[league].append(injury)

        for league in sorted(by_league.keys()):
            print(f"\n🏆 {league}")
            print("-" * 80)
            for injury in by_league[league]:
                status_icon = "❌" if injury['status'] == "OUT" else "⚠️"
                impact_icon = "🔥" if injury['impact'] == "CRITICAL" else ("⚡" if injury['impact'] == "HIGH" else "")
                print(f"  {status_icon} {impact_icon} {injury['player']:30s} ({injury['team']:<25s}) {injury['injury_type']}")

    def interactive_mode(self):
        """대화형 모드"""
        print("\n" + "=" * 60)
        print("⚽ Interactive Injury Updater")
        print("=" * 60)

        while True:
            print("\n1. Add injury")
            print("2. Remove injury (player returned)")
            print("3. Update status")
            print("4. List all")
            print("5. Save & Exit")
            print("6. Exit without saving")

            choice = input("\nChoice: ").strip()

            if choice == "1":
                # Add injury
                print("\n--- Add Injury ---")
                league = input("League (EPL/La_liga/Bundesliga/Serie_A/Ligue_1): ").strip()
                team = input("Team: ").strip()
                player = input("Player: ").strip()
                position = input("Position (FW/MF/DF/GK): ").strip()
                status = input("Status (OUT/DOUBTFUL): ").strip().upper()
                injury_type = input("Injury type: ").strip()
                expected_return = input("Expected return (YYYY-MM-DD or description): ").strip()
                impact = input("Impact (CRITICAL/HIGH/MEDIUM): ").strip().upper()

                self.add_injury(league, team, player, position, status, injury_type, expected_return, impact)

            elif choice == "2":
                # Remove
                player = input("\nPlayer name to remove: ").strip()
                self.remove_injury(player)

            elif choice == "3":
                # Update status
                player = input("\nPlayer name: ").strip()
                new_status = input("New status (OUT/DOUBTFUL): ").strip().upper()
                self.update_status(player, new_status)

            elif choice == "4":
                # List
                self.list_all()

            elif choice == "5":
                # Save & Exit
                self.save()
                print("👋 Goodbye!")
                break

            elif choice == "6":
                # Exit without saving
                print("👋 Goodbye!")
                break

def quick_update():
    """빠른 업데이트 (코드로 직접 입력)"""
    updater = ManualInjuryUpdater()

    # 예시 데이터 - 실제 사용시 여기에 최신 정보 입력
    updates = [
        # (league, team, player, position, status, injury_type, expected_return, impact)
        ("EPL", "Manchester City", "Erling Haaland", "FW", "ACTIVE", None, None, "CRITICAL"),
        ("EPL", "Liverpool", "Mohamed Salah", "FW", "ACTIVE", None, None, "CRITICAL"),
        ("EPL", "Arsenal", "Bukayo Saka", "FW", "ACTIVE", None, None, "CRITICAL"),
        ("EPL", "Manchester United", "Bruno Fernandes", "MF", "ACTIVE", None, None, "HIGH"),
        ("EPL", "Tottenham", "Son Heung-min", "FW", "ACTIVE", None, None, "CRITICAL"),
        ("EPL", "Chelsea", "Cole Palmer", "MF", "ACTIVE", None, None, "HIGH"),

        # 부상 예시 (실제 부상시 여기에 추가)
        # ("EPL", "Manchester City", "Kevin De Bruyne", "MF", "OUT", "Hamstring", "2025-01-15", "CRITICAL"),
    ]

    for update in updates:
        league, team, player, position, status, injury_type, expected_return, impact = update
        updater.add_injury(league, team, player, position, status, injury_type or "", expected_return or "", impact)

    updater.save()
    updater.list_all()

def main():
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "quick":
        quick_update()
    else:
        updater = ManualInjuryUpdater()
        updater.interactive_mode()

if __name__ == "__main__":
    main()
