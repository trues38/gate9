
import duckdb
import pandas as pd

# Layer 4: Matchup Profile
# Logic: Compare Team A's Offense Style (e.g. 3P Heavy) vs Team B's Defense Weakness (e.g. Allows many 3s)

def calculate_matchup(game_date, team_id, opp_id, con):
    # 1. Get Team Offense Profile (L10)
    # - 3PA Rate (3PA / FGA)
    # - Paint Rate (Assume 2PA is Paint for simplicity in basic logs? No, 2PA includes mid-range. 
    #   Basic log doesn't have Paint. We stick to 3P vs 2P).
    
    off_query = f"""
        SELECT 
            SUM(fg3a) as fg3a,
            SUM(fga) as fga
        FROM fact_gamelogs
        WHERE team_id = {team_id}
          AND game_date < '{game_date}'
        GROUP BY team_id
        ORDER BY game_date DESC
        LIMIT 10
    """ # Note: LIMIT on aggregation works if we group by game previously?
    # Correct: We need subquery or just sum last N games.
    
    # Let's simple sum last 10 games
    off_query = f"""
        SELECT 
            SUM(fg3a) as total_3pa,
            SUM(fga) as total_fga
        FROM (
            SELECT game_date, SUM(fg3a) as fg3a, SUM(fga) as fga
            FROM fact_gamelogs
            WHERE team_id = {team_id} AND game_date < '{game_date}'
            GROUP BY game_date
            ORDER BY game_date DESC
            LIMIT 10
        )
    """
    off_stats = con.execute(off_query).df()
    if len(off_stats) == 0 or off_stats['total_fga'].iloc[0] == 0:
        return 0.5
        
    rate_3p = off_stats['total_3pa'].iloc[0] / off_stats['total_fga'].iloc[0]
    
    # 2. Get Opponent Defense Profile (L10)
    # Using `matchup` string or Opponent ID?
    # Since we have `opponent` in metadata, we can find games where `team_id` was the opponent.
    # But `fact_gamelogs` is indexed by player/team.
    # To find "Points Allowed" or "3PA Allowed", we look at the games the OPPONENT played, 
    # and verify THEIR opponent's stats?
    # Or simpler: Look at `fact_gamelogs` for the OPPONENT's opponents.
    # That requires joining game_id.
    
    # Approach: Get Opponent's Game IDs (L10) -> Get stats of the TEAMS they played against.
    
    opp_games_query = f"""
        WITH opp_games AS (
            SELECT DISTINCT game_id
            FROM fact_gamelogs
            WHERE team_id = {opp_id} AND game_date < '{game_date}'
            ORDER BY game_date DESC
            LIMIT 10
        )
        SELECT 
            SUM(fg3a) as allowed_3pa,
            SUM(fga) as allowed_fga
        FROM fact_gamelogs
        WHERE game_id IN (SELECT game_id FROM opp_games)
          AND team_id != {opp_id} -- The opponents
    """
    
    def_stats = con.execute(opp_games_query).df()
    if len(def_stats) == 0 or def_stats['allowed_fga'].iloc[0] == 0:
        return 0.5
        
    allowed_rate_3p = def_stats['allowed_3pa'].iloc[0] / def_stats['allowed_fga'].iloc[0]
    
    # 3. Compare
    # If Team A shoots lots of 3s (High Rate) AND Team B allows lots of 3s (High Rate) -> Advantage A.
    # Score > 0.5 means Advantage for Team A.
    
    # Simple Heuristic:
    # Score = 0.5 + (OffRate - LeagueAvg) + (DefRate - LeagueAvg)
    # Assume Avg 3P rate is 0.4
    
    baseline = 0.4
    off_dev = rate_3p - baseline
    def_dev = allowed_rate_3p - baseline
    
    # If both positive -> Huge Advantage.
    # If Off positive, Def negative (Good 3P def) -> Disadvantage.
    
    score = 0.5 + (off_dev + def_dev) 
    
    return round(score, 2)
