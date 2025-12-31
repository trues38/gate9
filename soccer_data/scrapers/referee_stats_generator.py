import pandas as pd
import glob
import json
import os

def generate_referee_stats():
    """
    Parses historical odds CSVs to extract referee names and calculate 
    their 'Strictness Score' (Cards per Foul).
    """
    csv_files = glob.glob("soccer_data/raw_data/historical_odds/*.csv")
    ref_data = {}
    
    for file in csv_files:
        try:
            # Note: Football-Data.co.uk CSVs use different encodings sometimes
            df = pd.read_csv(file, encoding='unicode_escape')
            if 'Referee' in df.columns:
                for index, row in df.iterrows():
                    ref = row['Referee']
                    if pd.isna(ref): continue
                    
                    if ref not in ref_data:
                        ref_data[ref] = {'games': 0, 'yellow': 0, 'red': 0, 'fouls': 0}
                    
                    ref_data[ref]['games'] += 1
                    ref_data[ref]['yellow'] += (row.get('HY', 0) + row.get('AY', 0))
                    ref_data[ref]['red'] += (row.get('HR', 0) + row.get('AR', 0))
                    ref_data[ref]['fouls'] += (row.get('HF', 0) + row.get('AF', 0))
        except Exception as e:
            print(f"Error parsing {file}: {e}")

    # Calculate strictness
    for ref, stats in ref_data.items():
        if stats['games'] > 0:
            stats['avg_yellow'] = round(stats['yellow'] / stats['games'], 2)
            stats['avg_red'] = round(stats['red'] / stats['games'], 2)
            stats['strictness_index'] = round((stats['yellow'] + stats['red']*3) / (stats['fouls'] or 1), 3)

    output_path = "soccer_data/processed/referee_stats.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(ref_data, f, indent=4)
    
    print(f"Generated stats for {len(ref_data)} referees.")

if __name__ == "__main__":
    generate_referee_stats()
