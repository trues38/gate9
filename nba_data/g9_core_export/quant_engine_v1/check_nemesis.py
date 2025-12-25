import duckdb
import pandas as pd

DB_PATH = '/Users/js/g9/nba_analytics.duckdb'

def check_nemesis():
    con = duckdb.connect(DB_PATH)
    
    matchups = [
        ("Orlando Magic", "New York Knicks"), # Home, Away
        ("Oklahoma City Thunder", "San Antonio Spurs")
    ]
    
    print("💀 Regimes Check: Nemesis Analysis (History up to June 2024)\n")
    
    for home, away in matchups:
        # Get the MOST RECENT record of this matchup to see the 'score_last_10_between'
        # Note: 'score_last_10_between' is likely from the perspective of the HOME team? Or the Row Team?
        # The sample showed 'Team' and 'Opponent'.
        # Let's query by Team='Orlando Magic' and Opponent='New York Knicks'.
        
        query = f"""
            SELECT Date, Team, Opponent, score_last_10_between, n_victorias, n_victorias_o
            FROM fact_features
            WHERE Team = '{home}' AND Opponent = '{away}'
            ORDER BY Date DESC
            LIMIT 1
        """
        
        try:
            df = con.execute(query).df()
            if df.empty:
                print(f"⚠️ No history found for {home} vs {away}")
                continue
                
            rec = df.iloc[0]
            score_diff = rec['score_last_10_between']
            val_date = rec['Date']
            
            print(f"🏀 {home} vs {away}")
            print(f"   Last Recorded Meeting: {val_date}")
            print(f"   Historical Score Gap (Last 10): {score_diff:.1f} pts")
            
            # Nemesis Threshold: < -5.0 (Meaning 'Team' loses by 5+ avg)
            if score_diff < -5.0:
                print(f"   🚨 NEMESIS ALERT: {home} struggles against {away}. (Gap {score_diff:.1f} < -5.0)")
                print(f"   👉 Implication: {away} likely to cover/win.")
            elif score_diff > 5.0:
                 print(f"   🛡️ DOMINANCE ALERT: {home} owns {away}. (Gap +{score_diff:.1f} > 5.0)")
            else:
                print(f"   ✅ Neutral History. (Gap {score_diff:.1f})")
                
            print("-" * 40)
            
        except Exception as e:
            print(f"Error querying {home} vs {away}: {e}")

if __name__ == "__main__":
    check_nemesis()
