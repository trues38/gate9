
import duckdb
from datetime import datetime, timedelta
import pandas as pd

# Layer 6: Schedule Stress
# Logic: Back-to-Back, 3-in-4, 5-in-7, Travel

def calculate_schedule_stress(game_date, team_id, con):
    # Get last 7 days of games
    g_date = datetime.strptime(game_date, "%Y-%m-%d").date()
    start_date = g_date - timedelta(days=7)
    
    query = f"""
        SELECT DISTINCT game_date, matchup
        FROM fact_gamelogs
        WHERE team_id = {team_id}
          AND game_date >= '{start_date}'
          AND game_date < '{game_date}'
        ORDER BY game_date DESC
    """
    recent_games = con.execute(query).df()
    
    dates = pd.to_datetime(recent_games['game_date']).dt.date.tolist()
    
    score = 0
    
    # 1. Back to Back
    is_b2b = False
    if dates and dates[0] == (g_date - timedelta(days=1)):
        is_b2b = True
        score += 30 # Significant penalty/stress
        
    # 2. 3 in 4
    # Check games in [Day-3, Day-2, Day-1]
    # We have Today(0). 
    # If we played Day-1, Day-2, Day-3? (3 games in 3 days impossible usually)
    # 3 in 4 means: Today is 4th day. Played 2 games in prev 3 days. 
    # Total games in last 4 days (including today) = 3?
    # Actually, usually "3 games in 4 nights" means playing on Day 1, 2, (rest), 4.
    # Let's count games in window [game_date - 3 days].
    
    window_4d = [d for d in dates if d >= (g_date - timedelta(days=3))]
    if len(window_4d) >= 2: # Already played 2, today is 3rd?
        # Actually logic: 
        # If today is played, and we played 2 in last 3 days -> 3rd in 4 nights.
        score += 20 * (len(window_4d) - 1)
        
    # 3. 5 in 7
    if len(dates) >= 4: # Played 4 in last 7 days, today is 5th
        score += 25
        
    # 4. Travel (Simple)
    # Check location of last game (vs/at) vs Today's location (Home/Away).
    # Since we are calculating for 'team_id', we need to check if 'home_id' is us or not in Master Script.
    # But layer function doesn't know context.
    # We assume Master Script passes Home/Away context? 
    # Actually, we can check recent game's matchup vs Expected Today.
    # But this function only knows 'team_id'.
    # We will return Stress Score purely based on density first.
    
    # Normalized Score: 0 (Fresh) to 100 (Dead tired)
    # Inverse for "Advantage"? 
    # Let's return Stress Level (0-100).
    # Higher = Worse.
    
    return min(score, 100)
