#!/usr/bin/env python3
"""
2023-24 시즌 전체 경기 데이터 크롤링
날짜 범위: 2023-10-24 ~ 2024-06-17
"""

import requests
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

class SeasonCrawler:
    def __init__(self):
        self.base_url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
        self.output_dir = Path("/Users/js/g9/nba_data/state_graph/season_2023_24")
        self.output_dir.mkdir(exist_ok=True)

    def get_date_range(self) -> List[str]:
        """2023-24 시즌 날짜 범위 생성"""
        start_date = datetime(2023, 10, 24)  # 시즌 시작
        end_date = datetime(2024, 6, 17)     # 파이널 종료

        dates = []
        current = start_date
        while current <= end_date:
            dates.append(current.strftime("%Y%m%d"))
            current += timedelta(days=1)

        return dates

    def fetch_games_for_date(self, date: str) -> Optional[Dict]:
        """특정 날짜의 경기 데이터 가져오기"""
        url = f"{self.base_url}?dates={date}"

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            # 경기가 있는지 확인
            if not data.get('events'):
                return None

            return data

        except Exception as e:
            print(f"  ❌ {date} 가져오기 실패: {e}")
            return None

    def save_daily_data(self, date: str, data: Dict):
        """일별 데이터 저장"""
        filepath = self.output_dir / f"games_{date}.json"

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def crawl_season(self):
        """시즌 전체 크롤링"""
        dates = self.get_date_range()
        total_dates = len(dates)

        print("=" * 80)
        print("2023-24 시즌 경기 데이터 크롤링")
        print("=" * 80)
        print(f"\n기간: 2023-10-24 ~ 2024-06-17")
        print(f"총 {total_dates}일 크롤링 예정\n")

        total_games = 0
        successful_dates = 0
        failed_dates = []

        for i, date in enumerate(dates, 1):
            print(f"[{i}/{total_dates}] {date[:4]}-{date[4:6]}-{date[6:8]}", end=" ")

            data = self.fetch_games_for_date(date)

            if data:
                games_count = len(data.get('events', []))
                if games_count > 0:
                    self.save_daily_data(date, data)
                    total_games += games_count
                    successful_dates += 1
                    print(f"✅ {games_count}경기")
                else:
                    print("⚪ 경기 없음")
            else:
                failed_dates.append(date)
                print("❌ 실패")

            # API Rate Limiting 방지
            time.sleep(0.5)

            # 진행률 표시
            if i % 30 == 0:
                print(f"\n진행률: {i/total_dates*100:.1f}% | 경기 수: {total_games}개\n")

        # 결과 요약
        print("\n" + "=" * 80)
        print("크롤링 완료!")
        print("=" * 80)
        print(f"\n총 크롤링 날짜: {total_dates}일")
        print(f"경기 있는 날짜: {successful_dates}일")
        print(f"총 경기 수: {total_games}개")

        if failed_dates:
            print(f"\n⚠️  실패한 날짜: {len(failed_dates)}개")
            print("재시도 권장:")
            for date in failed_dates[:5]:
                print(f"  - {date}")

        print(f"\n📁 저장 위치: {self.output_dir}")
        print(f"\n💡 다음 단계: python3 import_season_2023_24.py")

def main():
    crawler = SeasonCrawler()

    try:
        crawler.crawl_season()
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자가 중단했습니다.")
        print("진행된 데이터는 저장되었습니다.")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
