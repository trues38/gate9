import pandas as pd
import os
import requests

def download_historical_odds():
    """
    Downloads historical results and odds for the Top 5 leagues from Football-Data.co.uk.
    This provides 'Closing Lines' which are essential for Edge Analysis.
    """
    LEAGUES = {
        "E0": "EPL",
        "SP1": "LaLiga",
        "D1": "Bundesliga",
        "I1": "SerieA",
        "F1": "Ligue1"
    }
    SEASON = "2425" # 2024-2025
    BASE_URL = "https://www.football-data.co.uk/mmz4281"
    
    output_dir = "soccer_data/raw_data/historical_odds"
    os.makedirs(output_dir, exist_ok=True)
    
    for league_code, league_name in LEAGUES.items():
        url = f"{BASE_URL}/{SEASON}/{league_code}.csv"
        print(f"Downloading odds for {league_name}...")
        
        try:
            response = requests.get(url)
            if response.status_code == 200:
                with open(f"{output_dir}/{league_name}_{SEASON}.csv", 'wb') as f:
                    f.write(response.content)
                print(f"  Saved {league_name} odds.")
            else:
                print(f"  Failed for {league_name} (Status: {response.status_code})")
        except Exception as e:
            print(f"  Error downloading {league_name}: {e}")

if __name__ == "__main__":
    download_historical_odds()
