"""
Fetch Game Results from Raw Data
=================================
이미 수집한 Raw 데이터에서 경기 결과 추출
"""

import json
import os
from glob import glob
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(BASE_DIR, "raw")


def extract_results_from_raw():
    """Raw game 파일에서 결과 추출"""
    results = []

    pattern = os.path.join(RAW_DIR, "*_game_*.json")
    files = sorted(glob(pattern))

    for filepath in files:
        with open(filepath, 'r') as f:
            data = json.load(f)

        # Header에서 경기 정보
        header = data.get('header', {})
        game_id = header.get('id')
        comps = header.get('competitions', [{}])[0]
        competitors = comps.get('competitors', [])

        # 경기 날짜
        game_date = header.get('competitions', [{}])[0].get('date', '').split('T')[0]

        # 팀 정보
        home = next((c for c in competitors if c.get('homeAway') == 'home'), {})
        away = next((c for c in competitors if c.get('homeAway') == 'away'), {})

        home_abbr = home.get('team', {}).get('abbreviation', 'UNK')
        away_abbr = away.get('team', {}).get('abbreviation', 'UNK')

        # 점수
        home_score = int(home.get('score', 0))
        away_score = int(away.get('score', 0))

        # 승자
        home_win = 1 if home_score > away_score else 0

        # Status 확인 (경기 완료 여부)
        status = comps.get('status', {}).get('type', {}).get('state', '')

        if status == 'post' and home_score > 0:  # 완료된 경기만
            results.append({
                'game_id': game_id,
                'date': game_date,
                'home_team': home_abbr,
                'away_team': away_abbr,
                'home_score': home_score,
                'away_score': away_score,
                'home_win': home_win,
                'point_diff': home_score - away_score
            })

    return pd.DataFrame(results)


def main():
    print("Extracting results from raw data...")
    df = extract_results_from_raw()
    print(f"  Extracted {len(df)} completed games")

    # 저장
    output_file = os.path.join(BASE_DIR, "december_results.csv")
    df.to_csv(output_file, index=False)
    print(f"  Saved to: {output_file}")

    # 샘플 출력
    print("\nSample results:")
    print(df.head(10).to_string())


if __name__ == "__main__":
    main()
