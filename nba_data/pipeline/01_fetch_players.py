import pandas as pd
from nba_api.stats.endpoints import commonallplayers
import json
import os
import time

# Step 1: Fetch Player Master
# Goal: Get list of active players for 2024-25 season and recent years
# We will fetch all players with IsOnlyCurrentSeason=0 to get everyone, 
# then filter for those who played in 2024-25 or are recent enough (2009-2025).

DATA_DIR = "/Users/js/g9/nba_data/players"

def fetch_active_players():
    print("Fetching player list from NBA API...")
    
    # IsOnlyCurrentSeason=0 returns all players in history. 
    # We need this to filter for our specific scope if needed, 
    # but for "Active Players" list, we can just check the active flag or roster.
    # However, commonallplayers with IsOnlyCurrentSeason=1 gives current roster.
    
    try:
        # Fetch current season active players
        active_players = commonallplayers.CommonAllPlayers(is_only_current_season=1)
        df_active = active_players.get_data_frames()[0]
        
        print(f"Found {len(df_active)} active players.")
        
        # Save raw roster
        os.makedirs(DATA_DIR, exist_ok=True)
        df_active.to_json(os.path.join(DATA_DIR, "roster_2025.json"), orient="records", indent=2)
        print(f"Saved roster_2025.json")

        # Create master list with basic info
        # Structure: player_id, full_name, team_id, team_slug
        # We might want to expand this to include 2009-2025 players later, 
        # but for now let's start with the current roster as the scope anchor.
        
        master_list = []
        for _, row in df_active.iterrows():
            master_list.append({
                "player_id": row['PERSON_ID'],
                "name": row['DISPLAY_FIRST_LAST'],
                "team_id": row['TEAM_ID'],
                "team_slug": row['TEAM_SLUG'],
                "from_year": row['FROM_YEAR'],
                "to_year": row['TO_YEAR']
            })
            
        with open(os.path.join(DATA_DIR, "master_list.json"), "w") as f:
            json.dump(master_list, f, indent=2)
            
        print(f"Saved master_list.json with {len(master_list)} players.")
        
    except Exception as e:
        print(f"Error fetching players: {e}")

if __name__ == "__main__":
    fetch_active_players()
