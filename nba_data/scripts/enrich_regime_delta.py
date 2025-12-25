
import pandas as pd
import numpy as np

INPUT_PATH = "processed/regime_delta_dataset.csv"
OUTPUT_PATH = "processed/regime_directional_dataset.csv"

def enrich_data():
    print("🔄 Loading Regime Delta Dataset...")
    df = pd.read_csv(INPUT_PATH)
    
    # Ensure numeric columns
    cols = ['edge_score', 'spread', 'total', 'id_spread', 'id_total', 'team_score', 'opp_score']
    for c in cols:
        df[c] = pd.to_numeric(df[c], errors='coerce')
        
    print("➕ Deriching Directional Data...")
    
    # 1. Determine Is_Home
    # Note: 'whos_favored' is 'home' or 'away' (or 'void'?)
    # merged dataset has 'team_score', 'opp_score', and we assume original 'score_home' column might exist?
    # Wait, in merge script we selected: 'date', 'team', 'spread', 'total', 'id_spread', 'id_total', 'team_score', 'opp_score', 'whos_favored'
    # We did NOT select 'score_home' separately?
    # Ah, checking merge script again: 
    # merged = pd.merge(..., combined_hist[['date', 'team', ..., 'team_score', 'opp_score', 'whos_favored']])
    # We lost 'is_home' flag.
    # BUT, we can derive it? 
    # "whos_favored" tells us who is favored.
    # "spread" value usually corresponds to the favorite? Or Home?
    # In 'nba_2008-2025.csv', 'spread' column is NOT always Home spread.
    # Often it is "Spread Line". If negative -> Home is Fav?
    # This is ambiguous without 'is_home'.
    
    # Pivot: We need to re-run merge script to include 'is_home'?
    # Or can we use logic?
    # Edge Score logic assumes Team stats.
    # Let's assume we can't perfectly know 'is_home' easily without re-merge.
    # HOWEVER, we can know 'is_favorite' directly if we trust 'spread' + 'id_spread'?
    # Let's rely on 'id_spread'.
    # If id_spread = 1, Team Covered.
    # Who is the Team? 'team'.
    # Who is Favored? 'whos_favored'.
    # Does 'whos_favored' match 'team'?
    # We need to normalize 'whos_favored' (abbrev like 'por') to Full Name ('Portland...').
    # We used TEAM_MAP in merge script.
    
    # Import map here? Or just include it.
    TEAM_MAP = {
        "atl": "Atlanta Hawks", "bos": "Boston Celtics", "bkn": "Brooklyn Nets", "nj": "New Jersey Nets",
        "cha": "Charlotte Hornets", "chho": "Charlotte Hornets", "chi": "Chicago Bulls", "cle": "Cleveland Cavaliers",
        "dal": "Dallas Mavericks", "den": "Denver Nuggets", "det": "Detroit Pistons", "gs": "Golden State Warriors",
        "gsw": "Golden State Warriors", "hou": "Houston Rockets", "ind": "Indiana Pacers", "lac": "Los Angeles Clippers",
        "lal": "Los Angeles Lakers", "mem": "Memphis Grizzlies", "mia": "Miami Heat", "mil": "Milwaukee Bucks",
        "min": "Minnesota Timberwolves", "no": "New Orleans Pelicans", "nop": "New Orleans Pelicans",
        "noh": "New Orleans Hornets", "ny": "New York Knicks", "nyk": "New York Knicks", "okc": "Oklahoma City Thunder",
        "orl": "Orlando Magic", "phi": "Philadelphia 76ers", "pho": "Phoenix Suns", "phx": "Phoenix Suns",
        "por": "Portland Trail Blazers", "sac": "Sacramento Kings", "sa": "San Antonio Spurs", "sas": "San Antonio Spurs",
        "tor": "Toronto Raptors", "uta": "Utah Jazz", "utah": "Utah Jazz", "was": "Washington Wizards", "wsh": "Washington Wizards"
    }
    
    def normalize(code):
        return TEAM_MAP.get(str(code).lower(), str(code))
        
    df['fav_team_full'] = df['whos_favored'].apply(normalize)
    
    # Is Team Favorite?
    # Check if 'team' string matches 'fav_team_full' string?
    # Be careful of partial matches? Ideally fuzzy or exact if normalized.
    # Both should be normalized full names now.
    
    df['is_favorite'] = df['team'] == df['fav_team_full']
    
    # 2. Spread Side
    # Logic:
    # If Team is Favorite AND it Covered (id_spread=1) -> FAVORITE_COVER
    # If Team is Favorite AND it Failed (id_spread=0) -> UNDERDOG_COVER
    # If Team is Underdog AND it Covered (id_spread=1) -> UNDERDOG_COVER
    # If Team is Underdog AND it Failed (id_spread=0) -> FAVORITE_COVER
    
    conditions = [
        (df['is_favorite'] & (df['id_spread'] == 1)),
        (df['is_favorite'] & (df['id_spread'] == 0)),
        (~df['is_favorite'] & (df['id_spread'] == 1)),
        (~df['is_favorite'] & (df['id_spread'] == 0))
    ]
    choices = ['FAVORITE_COVER', 'UNDERDOG_COVER', 'UNDERDOG_COVER', 'FAVORITE_COVER']
    
    df['spread_side'] = np.select(conditions, choices, default='PUSH/UNKNOWN')
    
    # 3. Total Side
    # id_total=1 -> Over, 0 -> Under.
    df['total_side'] = np.where(df['id_total'] == 1, 'OVER', 'UNDER')
    
    # 4. Bucketing
    # Spread Bucket (Size of line). 'spread' column.
    # Spread is usually positive in this csv? e.g. 13 in sample.
    # If 'whos_favored' == home, spread is home spread line?
    # Sample row: por vs sa (Fav=home/sa). Spread=13.
    # Usually means SA -13? Or just "Line is 13".
    # Let's bucket solely on Magnitude.
    df['spread_mag'] = df['spread'].abs()
    # Buckets: Small (0-4), Med (4.5-8), Large (8.5-12), Huge (12.5+)
    bins = [-0.1, 4.0, 8.0, 12.0, 100.0]
    labels = ['Small (0-4)', 'Med (4-8)', 'Large (8-12)', 'Huge (12+)']
    df['spread_bucket'] = pd.cut(df['spread_mag'], bins=bins, labels=labels)

    # Edge Bucket (Standard)
    # 0-50, 50-60, 60-70, 70-80, 80+
    edge_bins = [0, 50, 60, 70, 80, 100]
    edge_labels = ['Weak <50', 'Tossup 50-60', 'Value 60-70', 'Strong 70-80', 'Extreme 80+']
    df['edge_bucket'] = pd.cut(df['edge_score'], bins=edge_bins, labels=edge_labels)
    
    # Save
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"💾 Enrichment Complete. Saved to {OUTPUT_PATH}")
    print(f"Sample Spread Side Dist:\n{df['spread_side'].value_counts(normalize=True)}")

if __name__ == "__main__":
    enrich_data()
