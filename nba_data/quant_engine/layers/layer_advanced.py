
import duckdb
import pandas as pd
import numpy as np

# Grouping simpler advanced logic layers here

def calculate_clutch(game_date, team_id, con):
    # Layer 10
    # Clutch: NetRtg in Close Games (Margin <= 5 in last 5 min? Hard to check without PBP)
    # Proxy: Win% in games decided by <= 5 points (Last 20)
    
    # Proxy: Recent Win % (Last 20 Games) - General "Winning Culture" proxy
    # Since we lack PBP data for true clutch.
    
    q_clutch = f"""
        SELECT 
            game_date, wl
        FROM fact_gamelogs
        WHERE team_id = {team_id} AND game_date < '{game_date}'
        GROUP BY game_date, wl
        ORDER BY game_date DESC
        LIMIT 20
    """
    df = con.execute(q_clutch).df()
    if len(df) == 0: return 0.5
    
    wins = df[df['wl'] == 'W']
    win_rate = len(wins) / len(df)
    return round(win_rate, 2)

def calculate_defense(game_date, team_id, con):
    # Layer 11
    # Defensive Breakdown: Paint Pts / Open 3s (Proxies)
    # Proxy: Opponent FG% and PTS Allowed (Last 5)
    
    # We get opponents stats again.
    q_def = f"""
        WITH my_games AS (
            SELECT game_id FROM fact_gamelogs WHERE team_id = {team_id} AND game_date < '{game_date}'
            ORDER BY game_date DESC LIMIT 5
        )
        SELECT 
            SUM(pts) as pts_allowed,
            SUM(fga) as fga_allowed,
            SUM(fgm) as fgm_allowed
        FROM fact_gamelogs
        WHERE game_id IN (SELECT game_id FROM my_games)
          AND team_id != {team_id}
    """
    df = con.execute(q_def).df()
    if len(df) == 0 or df['fga_allowed'].iloc[0] == 0: return 0.5
    
    opp_fg_pct = df['fgm_allowed'].iloc[0] / df['fga_allowed'].iloc[0]
    # Lower is better.
    # Score: 1.0 - OppFG% (Higher score = Better Defense)
    return round(1.0 - opp_fg_pct, 2)

def calculate_variance(game_date, team_id, con):
    # Layer 12
    # Volatility of results (Std Dev of Margin)
    q_var = f"""
        SELECT 
            SUM(plus_minus) / 5 as margin
        FROM fact_gamelogs
        WHERE team_id = {team_id} AND game_date < '{game_date}'
        GROUP BY game_date
        ORDER BY game_date DESC
        LIMIT 10
    """
    df = con.execute(q_var).df()
    if len(df) < 5: return 0
    
    std_dev = df['margin'].std()
    return round(std_dev, 2)

def calculate_psych(game_date, team_id, con):
    # Layer 14
    # Streaks (W/L)
    # Check current streak
    
    q_streak = f"""
        SELECT wl
        FROM (
            SELECT DISTINCT game_date, wl -- Need game-level WL.
            -- Actually fact_gamelogs WL might vary by player? Should be consistent.
            -- Just take one player's WL per game.
            -- Or group by.
             SELECT wl FROM fact_gamelogs WHERE team_id = {team_id} AND game_date < '{game_date}'
             GROUP BY game_date, wl
             ORDER BY game_date DESC
             LIMIT 10
        )
    """
    # Simply:
    q_wl = f"""
        SELECT wl
        FROM fact_gamelogs
        WHERE team_id = {team_id} AND game_date < '{game_date}'
        GROUP BY game_date, wl
        ORDER BY game_date DESC
        LIMIT 10
    """
    df = con.execute(q_wl).df()
    if len(df) == 0: return 0
    
    results = df['wl'].tolist()
    if not results: return 0
    
    current_wl = results[0]
    streak = 0
    for res in results:
        if res == current_wl:
            streak += 1
        else:
            break
            
    # Positive for Win Streak, Negative for Loss
    score = streak if current_wl == 'W' else -streak
    return score
