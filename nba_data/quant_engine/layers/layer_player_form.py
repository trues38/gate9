
import duckdb
import pandas as pd

# Layer 3: Player Momentum
# Formula: Top 3 Players Form Rating (PTS + Impact)

def calculate_player_form(game_date, team_id, con):
    # Identify Top 3 Players by average extraction (last 10 games usage?)
    # Then calc their L3 form.
    
    # 1. Get Roster's recent performance (L10)
    query = f"""
        SELECT 
            person_id,
            AVG(pts) as avg_pts,
            AVG(plus_minus) as avg_pm,
            COUNT(*) as games
        FROM fact_gamelogs
        WHERE team_id = {team_id}
          AND game_date < '{game_date}'
        GROUP BY person_id
        HAVING games >= 5
        ORDER BY avg_pts DESC
        LIMIT 3
    """
    top_players = con.execute(query).df()
    
    if len(top_players) == 0:
        return 0.0
        
    top_ids = tuple(top_players['person_id'].tolist())
    if len(top_ids) == 1:
        top_ids = f"({top_ids[0]})"
        
    # 2. Get L3 Form for these stars
    # Use Pts + Reb + Ast as simple Game Score proxy since +/- is missing
    full_form_query = f"""
        WITH ranked AS (
            SELECT 
                person_id, pts, reb, ast,
                ROW_NUMBER() OVER (PARTITION BY person_id ORDER BY game_date DESC) as rn
            FROM fact_gamelogs
            WHERE person_id IN {top_ids}
              AND game_date < '{game_date}'
        )
        SELECT 
            person_id,
            AVG(pts + reb + ast) as form_val
        FROM ranked
        WHERE rn <= 3
        GROUP BY person_id
    """
    
    form_df = con.execute(full_form_query).df()
    
    # Calculate aggregate score
    # Score = Sum of Top 3 Players' avg production (PTS+REB+AST)
    if len(form_df) == 0: return 0.0
    
    total_form_val = form_df['form_val'].sum()
    
    # Normalize? A star produces ~30-40. 3 stars ~100.
    # Return raw value for now, or scaled to 0-1?
    # Report expects radar like value? 0.0 displayed in previous report.
    # Let's return raw value, user can interpret or we scale later.
    # Actually current report shows 0.0. If we return 85.5 it might look weird if others are 0-1.
    # But Pace is 98.0. So 85.5 is fine.
    
    return round(total_form_val, 1)
