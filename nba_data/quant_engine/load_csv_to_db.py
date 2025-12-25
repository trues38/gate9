import duckdb
import os
import glob

DB_PATH = "nba_analytics.duckdb"
CSV_DIR = "nba_data/processed/csv"

def init_db(con):
    # Dims
    con.sql("""
        CREATE TABLE IF NOT EXISTS dim_team (
            team_id INTEGER PRIMARY KEY,
            name VARCHAR,
            abbreviation VARCHAR,
            logo_url VARCHAR
        );
        CREATE TABLE IF NOT EXISTS dim_player (
            player_id INTEGER PRIMARY KEY,
            full_name VARCHAR,
            team_id INTEGER,
            position VARCHAR,
            headshot_url VARCHAR
        );
    """)
    
    # Facts - Drop first to ensure clean load from CSV
    con.sql("DROP TABLE IF EXISTS fact_game")
    con.sql("DROP TABLE IF EXISTS fact_boxscore")
    con.sql("DROP TABLE IF EXISTS fact_injury")
    con.sql("DROP TABLE IF EXISTS fact_team_stats")
    
    con.sql("""
        CREATE TABLE fact_game AS SELECT * FROM read_csv_auto('nba_data/processed/csv/clean_games.csv');
        CREATE TABLE fact_boxscore AS SELECT * FROM read_csv_auto('nba_data/processed/csv/clean_boxscores.csv');
        CREATE TABLE fact_injury AS SELECT * FROM read_csv_auto('nba_data/processed/csv/clean_injuries.csv');
        
        -- Add PKs (Optional execution if needed, but CREATE AS SELECT creates implicit types)
        -- We can ALTER TABLE or CREATE INDEX if performance needed.
    """)
    
def create_aggregates(con):
    print("📊 Creating Aggregates (fact_team_stats)...")
    
    # 1. Team Daily Sum
    # Boxscore columns are clean now: min, pts, fga, fta, oreb, tov, dreb, fgm
    con.sql("""
        CREATE OR REPLACE TEMP TABLE team_daily_sum AS
        SELECT 
            game_id, 
            team_id,
            SUM(pts) as pts,
            SUM(fga) as fga,
            SUM(fta) as fta,
            SUM(oreb) as oreb,
            SUM(tov) as tov,
            SUM(dreb) as dreb,
            SUM(fgm) as fgm,
            SUM(min) as min_total
        FROM fact_boxscore
        GROUP BY game_id, team_id
    """)
    
    # 2. Join with Game
    con.sql("""
        CREATE TABLE fact_team_stats AS
        WITH match_stats AS (
            SELECT 
                t.game_id,
                t.team_id,
                CASE WHEN g.home_team_id = t.team_id THEN g.away_team_id ELSE g.home_team_id END as opponent_id,
                CASE WHEN g.home_team_id = t.team_id THEN TRUE ELSE FALSE END as is_home,
                t.pts,
                t.fga, t.fta, t.oreb, t.tov, t.dreb, t.min_total
            FROM team_daily_sum t
            JOIN fact_game g ON t.game_id = g.game_id
        ),
        full_match AS (
            SELECT
                m1.game_id,
                m1.team_id,
                m1.opponent_id,
                m1.is_home,
                m1.pts as tm_pts,
                m2.pts as opp_pts,
                
                -- Simple Possessions Calculation
                (m1.fga + 0.44 * m1.fta - m1.oreb + m1.tov) as tm_poss_est,
                (m2.fga + 0.44 * m2.fta - m2.oreb + m2.tov) as opp_poss_est,
                
                m1.min_total,
                m2.min_total as opp_min_total,
                
                m1.oreb as tm_oreb,
                m1.tov as tm_tov
            FROM match_stats m1
            JOIN match_stats m2 ON m1.game_id = m2.game_id AND m1.opponent_id = m2.team_id
        )
        SELECT
            game_id,
            team_id,
            opponent_id,
            is_home,
            tm_pts as pts,
            
            -- Average Possessions
            (tm_poss_est + opp_poss_est) / 2.0 as possessions,
            
            -- ORTG (Pts / 100 Poss)
            CASE WHEN (tm_poss_est + opp_poss_est) > 0 
                THEN 100.0 * tm_pts / ((tm_poss_est + opp_poss_est) / 2.0) 
                ELSE 0 END as ortg,
                
            -- DRTG (Opp Pts / 100 Poss)
            CASE WHEN (tm_poss_est + opp_poss_est) > 0 
                THEN 100.0 * opp_pts / ((tm_poss_est + opp_poss_est) / 2.0) 
                ELSE 0 END as drtg,
            
            -- Pace (Poss / 48min)
            CASE WHEN (min_total + opp_min_total) > 0
                THEN 48.0 * ((tm_poss_est + opp_poss_est) / 2.0) / ((min_total + opp_min_total) / 10.0)
                ELSE 0 END as pace,
                
            0.0 as oreb_pct, 
            
            -- TOV% (TOV / Poss)
            CASE WHEN tm_poss_est > 0 THEN 100.0 * tm_tov / tm_poss_est ELSE 0 END as tov_pct
            
        FROM full_match
    """)
    print("   Aggregates calculated.")

def main():
    print("📥 Loading CSVs to DuckDB...")
    con = duckdb.connect(DB_PATH)
    init_db(con)
    create_aggregates(con)
    con.close()
    print("✅ DB Reload Complete (Clean CSV Source).")

if __name__ == "__main__":
    main()
