import pandas as pd
import numpy as np

CSV_FILE = 'processed/rdata_treasury.csv'

def scan_regimes():
    print(f"🚀 Loading Treasure from {CSV_FILE}...")
    try:
        df = pd.read_csv(CSV_FILE)
        print(f"✅ Loaded {len(df)} games.")
        
        # Identify columns
        cols = df.columns.tolist()
        
        # Try to find 'Result' column
        # Candidates: 'outcome', 'win', 'result', 'spread_cover'
        # Let's inspect important columns
        print(f"📋 Key Columns Identified: {cols[:10]} ...")
        
        # User Logic:
        # "Fatigue Trap": days_since_last 
        # "Momentum Shift": avg_V_4
        
        # Let's create a hypothetical 'Upset Signal' if we can find the 'Odds' column.
        # User said "It has Odds".
        odds_col = next((c for c in cols if 'odds' in c.lower() or 'line' in c.lower() or 'payout' in c.lower()), None)
        
        if odds_col:
            print(f"💰 Odds Column Found: {odds_col}")
        else:
            print("⚠️ No explicit 'Odds' column found by name. Checking Sample data for values like -150, 1.90...")
            
        # 1. Fatigue Analysis (Back-to-Back Upset Rate)
        if 'days_since_last' in df.columns:
            print("\n💤 Fatigue Analysis (0 Days Rest):")
            b2b = df[df['days_since_last'] <= 1]
            print(f"   - Games with <=1 Day Rest: {len(b2b)}")
            
            # Assuming 'n_victorias' correlates with strength?
            # Or 'result_home' / 'home_win'?
            # We need to find the Target variable.
            # I will print the first row dict to debug mapping.
            print(df.iloc[0].to_dict())
            
    except Exception as e:
        print(f"🚨 Error: {e}")

if __name__ == "__main__":
    scan_regimes()
