
import duckdb
import pandas as pd

con = duckdb.connect("nba_analytics.duckdb")

# Calculate Avg Stats per player
query = """
SELECT 
    player_id,
    AVG(pts) as pts,
    AVG(fgm) as fgm, AVG(fga) as fga,
    AVG(ftm) as ftm, AVG(fta) as fta,
    AVG(oreb) as oreb,
    AVG(dreb) as dreb,
    AVG(ast) as ast,
    AVG(stl) as stl,
    AVG(blk) as blk,
    AVG(pf) as pf,
    AVG(tov) as tov,
    AVG(plus_minus) as avg_pm,
    COUNT(*) as games
FROM fact_boxscore
GROUP BY player_id
HAVING games > 5
"""

df = con.sql(query).df()

# Calculate GameScore
# GmSc = PTS + 0.4*FG - 0.7*FGA - 0.4*(FTA-FT) + 0.7*ORB + 0.3*DRB + STL + 0.7*AST + 0.7*BLK - 0.4*PF - TOV
df['gmsc'] = (
    df['pts'] + 
    0.4 * df['fgm'] - 
    0.7 * df['fga'] - 
    0.4 * (df['fta'] - df['ftm']) + 
    0.7 * df['oreb'] + 
    0.3 * df['dreb'] + 
    df['stl'] + 
    0.7 * df['ast'] + 
    0.7 * df['blk'] - 
    0.4 * df['pf'] - 
    df['tov']
)

# Join with player names (dim_player if exists, or just show ID)
# Assuming dim_player might not be fully populated or linked, we'll try to just show top IDs.
# Or if we have player_id in dim_player?

print("Top 10 by Game Score:")
print(df.sort_values('gmsc', ascending=False).head(10)[['player_id', 'gmsc', 'avg_pm', 'games']])

print("\nTop 10 by Plus/Minus:")
print(df.sort_values('avg_pm', ascending=False).head(10)[['player_id', 'gmsc', 'avg_pm', 'games']])

# Calculate correlation
print(f"\nCorrelation GmSc vs +/-: {df['gmsc'].corr(df['avg_pm']):.3f}")

# Distribution Logic Proposal
# If SGA (GmSc ~25) -> Penalty -8.
# Ratio: -8 / 25 = -0.32
# If Role (GmSc ~10) -> Penalty -1.5.
# Ratio: -1.5 / 10 = -0.15
# It seems non-linear or just a tiering.
# Maybe: Penalty = (GmSc - 8) * 0.4?
# If 25: (17)*0.4 = 6.8 (Close to 8)
# If 10: (2)*0.4 = 0.8 (Close to 1.5)
# If 5: (-3)*0.4 = -1.2 (Negative penalty? No.)
# So maybe max(0, (GmSc - ReplacementLevel) * Factor).
