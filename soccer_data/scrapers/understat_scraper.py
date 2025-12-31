import json
import asyncio
import aiohttp
from understat import Understat
import pandas as pd
from datetime import datetime
import os

async def fetch_understat_data(leagues=['EPL', 'La_liga', 'Bundesliga', 'Serie_A', 'Ligue_1'], seasons=['2024']):
    """
    Scrapes match-level and shot-level data from Understat for the top 5 leagues.
    """
    async with aiohttp.ClientSession() as session:
        understat = Understat(session)
        
        for league in leagues:
            for season in seasons:
                print(f"Fetching data for {league} {season}...")
                
                # 1. Fetch League Results
                results = await understat.get_league_results(league, season)
                
                # Save results to local JSON
                output_dir = f"soccer_data/raw_data/understat/{league}/{season}"
                os.makedirs(output_dir, exist_ok=True)
                
                with open(f"{output_dir}/results.json", 'w') as f:
                    json.dump(results, f, indent=4)
                
                # 2. Extract Match IDs and fetch detailed lineups/referees
                print(f"Fetching detailed match data for {len(results)} matches...")
                match_details = []
                
                # Limit to recent matches or specific count to avoid rate limiting
                for match in results[:50]: # Example: Fetching details for first 50
                    match_id = match['id']
                    print(f"  Fetching match {match_id} details...")
                    
                    # fetch match players (lineups, subs, stats)
                    players = await understat.get_match_players(match_id)
                    
                    # Understat results already contain referee name in some versions, 
                    # but we can augment this here.
                    match_data = {
                        "match_id": match_id,
                        "lineups": players,
                        "referee": match.get('referee', 'Unknown'),
                        "h_xg": match.get('xG', {}).get('h'),
                        "a_xg": match.get('xG', {}).get('a')
                    }
                    match_details.append(match_data)
                    await asyncio.sleep(0.5) # Modest delay
                
                with open(f"{output_dir}/match_details.json", 'w') as f:
                    json.dump(match_details, f, indent=4)
                
                print(f"Saved {len(match_details)} detailed match reports for {league} {season}.")

if __name__ == "__main__":
    # Note: Requires 'understat' and 'aiohttp' packages
    # pip install understat aiohttp
    asyncio.run(fetch_understat_data())
