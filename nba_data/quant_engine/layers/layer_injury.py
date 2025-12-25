
import duckdb

# Layer 5: Injury Impact
# Logic: VORP Replacement.
# Since we don't have dynamic injury data yet, we check "Did Top 3 Players play last game?"
# If a Key Player missed last game, we assume Injured/Out -> Impact Score.

def calculate_injury_impact(game_date, team_id, con):
    # 1. Identify Starters / Top Players (Avg Minutes > 25 in season)
    # Using L30 games to establish "Rotation"
    
    roster_query = f"""
        SELECT person_id, AVG(pts) as avg_pts
        FROM fact_gamelogs
        WHERE team_id = {team_id}
          AND game_date < '{game_date}'
        GROUP BY person_id
        HAVING AVG(min) > 25
    """
    core_rotation = con.execute(roster_query).df()
    
    if len(core_rotation) == 0:
        return 0
        
    core_ids = core_rotation['person_id'].tolist()
    
    # 2. Check Last Game Roster
    last_game_query = f"""
        SELECT person_id
        FROM fact_gamelogs
        WHERE team_id = {team_id}
          AND game_date = (
            SELECT MAX(game_date) FROM fact_gamelogs 
            WHERE team_id = {team_id} AND game_date < '{game_date}'
          )
    """
    last_game_roster = con.execute(last_game_query).df()['person_id'].tolist()
    
    # 3. Who is missing?
    missing_stars = [pid for pid in core_ids if pid not in last_game_roster]
    
    # 4. Calculate Impact
    # Sum of Avg PTS of missing players
    impact_score = 0
    for pid in missing_stars:
        # Get their avg pts
        pts = core_rotation[core_rotation['person_id'] == pid]['avg_pts'].iloc[0]
        impact_score += pts
        
    return round(impact_score, 2)
