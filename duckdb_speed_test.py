import duckdb
import time

def run_benchmark():
    print("🦆 Connecting to DuckDB (nba_analytics.db)...")
    con = duckdb.connect("nba_analytics.db")
    
    # Target Teams: SAC (Kings) vs IND (Pacers)
    # We look for MATCHUP containing 'SAC' or 'IND'
    
    print("\n🏎️  STARTING SPEED TEST: Analyzing Last 10 Seasons Data...")
    start_time = time.time()
    
    # QUERY EXPLANATION:
    # 1. Filter gamelogs for SAC/IND matchups.
    # 2. Group by Game_ID and Matchup to sum Player Stats into Team Stats.
    # 3. Calculate Rolling Average (Momentum) of Points directly in SQL.
    
    query = """
    WITH team_games AS (
        SELECT 
            Game_ID,
            GAME_DATE,
            SUBSTR(MATCHUP, 1, 3) as Team,
            SUM(PTS) as Team_PTS,
            SUM(AST) as Team_AST,
            SUM(PLUS_MINUS) as Team_PM
        FROM gamelogs
        WHERE MATCHUP LIKE '%SAC%' OR MATCHUP LIKE '%IND%'
        GROUP BY Game_ID, GAME_DATE, Team
    ),
    momentum_stats AS (
        SELECT
            Team,
            GAME_DATE,
            Team_PTS,
            AVG(Team_PTS) OVER (
                PARTITION BY Team 
                ORDER BY GAME_DATE 
                ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
            ) as Momentum_PTS_10G
        FROM team_games
    )
    SELECT 
        Team,
        COUNT(*) as Games_Analyzed,
        AVG(Team_PTS) as Avg_PTS_All_Time,
        AVG(Momentum_PTS_10G) as Avg_Momentum,
        MAX(Team_PTS) as Max_PTS
    FROM momentum_stats
    GROUP BY Team
    ORDER BY Team;
    """
    
    results = con.execute(query).fetchall()
    end_time = time.time()
    duration_ms = (end_time - start_time) * 1000
    
    print(f"\n✅ QUERY COMPLETE in {duration_ms:.2f} ms")
    print("-" * 60)
    print(f"{'TEAM':<10} | {'GAMES':<10} | {'AVG PTS':<10} | {'MOMENTUM':<10} | {'MAX PTS':<10}")
    print("-" * 60)
    for row in results:
        # row: (Team, Games, Avg_Pts, Avg_Mom, Max_Pts)
        print(f"{row[0]:<10} | {row[1]:<10} | {row[2]:.2f}       | {row[3]:.2f}       | {row[4]:<10}")
    print("-" * 60)
    
    con.close()

if __name__ == "__main__":
    run_benchmark()
