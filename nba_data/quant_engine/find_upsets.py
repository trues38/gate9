
import duckdb
import pandas as pd
from nba_data.quant_engine.quant_core import QuantDataManager, TeamStrengthEngine

# Connect
con = duckdb.connect("nba_analytics.duckdb")

def find_structural_upsets(threshold_net_rtg=5.0):
    print(f"🚀 Hunting for 'Structural Upsets' (NetRating Gap > {threshold_net_rtg})...")
    
    dm = QuantDataManager()
    
    # 1. Get All Games
    query = """
    SELECT game_id, date, home_team_id, away_team_id, home_score, away_score
    FROM fact_game
    WHERE status = 'STATUS_FINAL'
    ORDER BY date
    """
    games = con.sql(query).df()
    
    # 2. Get Team Names
    team_names_query = "SELECT team_id, name FROM dim_team"
    team_names_df = con.sql(team_names_query).df()
    team_names = team_names_df.set_index('team_id')['name'].to_dict()
    
    # 3. Get Season Stats
    # Note: Using Reset Index to ensure columns are accessible if needed
    stats_df = dm.get_season_stats().reset_index()
    # Ensure team_id is the index for lookup
    team_stats = stats_df.set_index('team_id')['net_rating'].to_dict()
    
    upsets = []
    
    for _, row in games.iterrows():
        gid = row['game_id']
        date = row['date']
        hid = row['home_team_id']
        aid = row['away_team_id']
        h_score = row['home_score']
        a_score = row['away_score']
        
        if hid not in team_stats or aid not in team_stats:
            continue
            
        h_net = team_stats[hid]
        a_net = team_stats[aid]
        
        # Calculate Expectation
        if h_net > a_net + threshold_net_rtg:
            # Home is Giant
            favorite = hid
            underdog = aid
            fav_net = h_net
            und_net = a_net
            gap = h_net - a_net
            did_fav_win = h_score > a_score
        elif a_net > h_net + threshold_net_rtg:
            # Away is Giant
            favorite = aid
            underdog = hid
            fav_net = a_net
            und_net = h_net
            gap = a_net - h_net
            did_fav_win = a_score > h_score
        else:
            # Close game, not an structural mismatch
            continue
            
        if not did_fav_win:
            # UPSET!
            winner = underdog
            loser = favorite
            margin = abs(h_score - a_score)
            
            upsets.append({
                "game_id": gid,
                "date": str(date),
                "winner": team_names.get(winner, f"ID_{winner}"),
                "loser": team_names.get(loser, f"ID_{loser}"),
                "winner_net": round(und_net, 1),
                "loser_net": round(fav_net, 1),
                "net_gap": round(gap, 1),
                "score": f"{h_score}-{a_score}",
                "margin": margin
            })
            
    upset_df = pd.DataFrame(upsets)
    print(f"🔥 Found {len(upset_df)} Structural Upsets out of {len(games)} games.")
    
    # Sort by 'Shock Value' (Gap)
    upset_df = upset_df.sort_values(by='net_gap', ascending=False)
    
    # Print Top 20 Upsets
    print(upset_df.head(20).to_string(index=False))
    
    upset_df.to_csv("nba_data/processed/structural_upsets.csv", index=False)
    print("✅ Saved to nba_data/processed/structural_upsets.csv")

if __name__ == "__main__":
    find_structural_upsets()
