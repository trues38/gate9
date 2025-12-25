
import duckdb
import pandas as pd
import os

# Paths
DB_PATH = 'nba_sql.duckdb'
OUTPUT_CSV = 'g9_core_export/INPUTS/daily_rdata.csv'

def calculate_edge_score(row):
    # Simplified Logic for v1.0
    # Edge = (NetRtg_L10 * 0.5) + (Pace_L4 * 0.1) - (Volatility * 2)
    # This is a placeholder for the Real Quant Formula.
    try:
        net = row.get('NetRtg_L10', 0) or 0
        pace = row.get('avg_P_4', 98) or 98
        vol = row.get('avg_V_o_8', 0) or 10 # Volatility opponent? Or self?
        
        # Sanctuary logic: High Stable Performance
        score = 50 + (net * 2)
        if score > 99: score = 99
        if score < 1: score = 1
        return round(score, 1)
    except:
        return 50.0

def determine_flow_state(row):
    # Logic: if NetRtg_L10 > NetRtg_Sea + 5 -> STRONG_UP
    try:
        l10 = row.get('NetRtg_L10', 0) or 0
        sea = row.get('NetRtg_Sea', 0) or 0
        
        if l10 > sea + 5: return "STRONG_UP"
        if l10 < sea - 5: return "STRONG_DOWN"
        return "STABLE"
    except:
        return "UNKNOWN"

def generate_intelligence():
    print("🧠 Generating Daily Intelligence Input from DuckDB...")
    
    if not os.path.exists(DB_PATH):
        print("❌ DB not found.")
        return

    con = duckdb.connect(DB_PATH)
    
    # 1. Get Latest State for Every Team
    # We query the MOST RECENT row for each team to get their "Current Stats".
    query = """
        SELECT 
            Team, 
            Date,
            NetRtg_L10,
            NetRtg_Sea,
            Pace_Sea,
            avg_P_4,
            avg_V_8,
            days_since_last as RestDays,
            Diff as RestDiff
        FROM rdata_treasury r1
        WHERE Date = (
            SELECT MAX(Date) FROM rdata_treasury r2 WHERE r2.Team = r1.Team
        )
        ORDER BY Team
    """
    
    try:
        df = con.execute(query).df()
        
        # 2. Compute Derived Metrics (Edge, Flow)
        metrics = []
        for idx, row in df.iterrows():
            edge = calculate_edge_score(row)
            flow = determine_flow_state(row)
            
            metrics.append({
                'Team': row['Team'].upper(),
                'Edge': edge,
                'Flow': flow,
                'Def': 'AVG',
                'NetRtg_L10': row.get('NetRtg_L10'),
                'Pace_L4': row.get('avg_P_4'),
                'Vol_Opp': row.get('avg_V_8'),
                'RestDays': row.get('RestDays'),
                'RestDiff': row.get('RestDiff')
            })
            
        # 3. Save to INPUTS
        out_df = pd.DataFrame(metrics)
        out_df.to_csv(OUTPUT_CSV, index=False)
        print(f"✅ Generated {OUTPUT_CSV} with {len(out_df)} teams.")
        print("🚀 Ready for g9_pipeline execution.")
        
    except Exception as e:
        print(f"❌ Generation Failed: {e}")
    finally:
        con.close()

if __name__ == "__main__":
    generate_intelligence()
