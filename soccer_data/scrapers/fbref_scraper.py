import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import os

def scrape_fbref_league_stats(league_url, league_name, season="2024-2025"):
    """
    Scrapes team/player metrics from FBRef league pages.
    Note: FBRef has strict rate limiting (Bot detection). 
    This script implements basic scraping for demonstration.
    """
    print(f"Scraping FBRef for {league_name}...")
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(league_url, headers=headers)
    
    if response.status_code != 200:
        print(f"Failed to fetch {league_url}")
        return

    # FBRef tables are easily parsed by pandas read_html if they are standard tables
    # For advanced stats (passing, defense), specific table IDs are needed
    tables = pd.read_html(response.text)
    
    output_dir = f"soccer_data/raw_data/fbref/{league_name}/{season}"
    os.makedirs(output_dir, exist_ok=True)
    
    # Save the main league table
    if tables:
        tables[0].to_csv(f"{output_dir}/league_table.csv")
        print(f"Saved league table to {output_dir}")

if __name__ == "__main__":
    # Example: EPL 24-25 Season
    epl_url = "https://fbref.com/en/comps/9/stats/Premier-League-Stats"
    scrape_fbref_league_stats(epl_url, "EPL")
    # Respect robots.txt - sleep between requests
    time.sleep(3)
