
import duckdb
import pandas as pd
import numpy as np

# Layer 1: Team Momentum
# Formula: Recent NetRating (L5) + OffRating Trend + DefRating Trend

def calculate_momentum(game_date, team_id, con):
    # Fetch last 5 games BEFORE game_date
    query = f"""
        SELECT 
            game_date, 
            pts, 
            plus_minus,
            matchup,
            wl
        FROM fact_gamelogs
        WHERE team_id = {team_id} 
          AND game_date < '{game_date}'
        ORDER BY game_date DESC
        LIMIT 5
    """
    df = con.execute(query).df()
    
    if len(df) < 5:
        return 0.5 # Neutral if insufficient data
        
    # Calculate Momentum based on Win Rate (L5)
    # W=1, L=0
    df['win_val'] = df['wl'].apply(lambda x: 1 if x.strip() == 'W' else 0)
    
    avg_win_rate = df['win_val'].mean() # 0.0 to 1.0
    
    # Trend: Last 2 Wins vs First 3 Wins
    recent_2 = df.head(2)['win_val'].mean()
    older_3 = df.tail(3)['win_val'].mean()
    trend = recent_2 - older_3
    
    # Score: Base Win Rate + Trend Bonus
    # Scale: 0-1 range.
    score = avg_win_rate + (trend * 0.2)
    
    # Clip to 0-1
    score = max(0.0, min(1.0, score))
    
    return round(score, 2)
