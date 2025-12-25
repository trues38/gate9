import duckdb

CON = duckdb.connect("nba_analytics.duckdb")

# 1. FACT_GAME_RESULTS
CON.execute("DROP TABLE IF EXISTS fact_game_results")
CON.execute("""
CREATE TABLE fact_game_results (
    game_id VARCHAR,
    game_date DATE,
    home_team VARCHAR,
    away_team VARCHAR,
    home_score INTEGER,
    away_score INTEGER,
    closing_spread DOUBLE,
    closing_total DOUBLE,
    spread_result VARCHAR, -- "Cover", "Fail", "Push"
    total_result VARCHAR   -- "Over", "Under", "Push"
)
""")

# 2. FACT_ACCURACY (The Learning Layer)
CON.execute("DROP TABLE IF EXISTS fact_accuracy")
CON.execute("""
CREATE TABLE fact_accuracy (
    game_id VARCHAR,
    prediction_winner VARCHAR,
    actual_winner VARCHAR,
    winner_correct BOOLEAN,
    
    prediction_spread DOUBLE,
    actual_margin DOUBLE,
    spread_error DOUBLE,
    
    regime_confidence INTEGER,
    accuracy_score DOUBLE, -- 0.0 to 1.0
    
    error_audit JSON -- Detailed breakdowns (L1 Error, L2 Error...)
)
""")

# 3. INSERT GROUND TRUTH (TOR vs NYK)
# Game ID? 401810212 (from earlier searches)
# Result: TOR 101 - NYK 117. Spread: TOR +5.5 (NYK -5.5). Total: 227.5.
# Margin: NYK +16. (Covered -5.5).
# Total: 218 (Under 227.5).

CON.execute("""
INSERT INTO fact_game_results VALUES (
    '401810212', '2025-12-10', 'TOR', 'NYK', 101, 117, -5.5, 227.5, 'NYK Covers', 'Under'
)
""")

print("✅ Database Updated with Ground Truth Tables & TOR/NYK Result.")
CON.close()
