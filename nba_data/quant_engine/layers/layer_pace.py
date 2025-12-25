
import duckdb
import pandas as pd

# Layer 2: Team Pace
# Formula: Estimated Pace + Trend

def calculate_pace(game_date, team_id, con):
    # Fetch last 5 games
    query = f"""
        SELECT 
            min, fga, reb, tov, fta
        FROM fact_gamelogs
        WHERE team_id = {team_id} 
          AND game_date < '{game_date}'
        ORDER BY game_date DESC
        LIMIT 5
    """
    df = con.execute(query).df()
    
    if len(df) < 1:
        return 98.0 # League average fallback
        
    # Simple Pace Estimation Formula (Possessions)
    # Poss = 0.96 * (FGA + 0.44*FTA - ORB + TOV)
    # We don't have ORB specifically in our basic schema (we have REB).
    # Estimate ORB as 25% of REB approx? Or just use FGA + TOV as rough proxy.
    # Let's use: FGA + 0.44*FTA + TOV (Ignoring ORB correction for speed, or assume ORB is captured in efficiency)
    
    # Better: Poss = FGA - ORB + TOV + 0.44*FTA
    # Without ORB, Pace is slightly overestimated.
    # Let's just use the raw metrics we have.
    
    possessions = 0.96 * (df['fga'] + 0.44 * df['fta'] + df['tov'])
    # Normalize per 48 mins (in case of OT)
    minutes = df['min'] / 5 # Sum of 5 players? 
    # Wait, fact_gamelogs is PLAYER level?
    # YES.
    # We need TEAM aggregated stats.
    # The query above fetches PLAYER logs. 
    # We need to sum them by GAME first.
    
    # RE-QUERYING correctly
    game_query = f"""
        SELECT 
            game_date,
            SUM(fga) as team_fga,
            SUM(fta) as team_fta,
            SUM(tov) as team_tov,
            SUM(min) as team_min
        FROM fact_gamelogs
        WHERE team_id = {team_id}
          AND game_date < '{game_date}'
        GROUP BY game_date
        ORDER BY game_date DESC
        LIMIT 5
    """
    game_df = con.execute(game_query).df()
    
    if len(game_df) == 0:
        return 98.0
        
    # Calculate Pace per Game
    # Pace = 48 * ((TeamPoss + OppPoss) / (2 * (TeamMin/5)))
    # We only have Team side.
    # Team Pace ~= 48 * (Poss / (TeamMin/5))
    
    game_df['poss'] = 0.96 * (game_df['team_fga'] + 0.44 * game_df['team_fta'] + game_df['team_tov'])
    game_df['game_pace'] = 48 * (game_df['poss'] / (game_df['team_min'] / 5))
    
    avg_pace = game_df['game_pace'].mean()
    return round(avg_pace, 2)
