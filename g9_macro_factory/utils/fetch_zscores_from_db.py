import os
import sys
import pandas as pd
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from g9_macro_factory.config import get_supabase_client

def fetch_zscores_to_csv(output_path="zscore_daily.csv"):
    supabase = get_supabase_client()
    print("📊 Fetching Z-Scores from DB...")
    
    try:
        # Fetch all records
        # Use pagination if needed, but let's try fetching a large batch
        # Supabase limit is usually 1000. We need to loop.
        
        all_data = []
        offset = 0
        batch_size = 10000
        
        while True:
            print(f"   Fetching batch starting at {offset}...", end='\r')
            res = supabase.table("zscore_daily").select("*").range(offset, offset + batch_size - 1).execute()
            batch = res.data
            if not batch:
                break
            all_data.extend(batch)
            if len(batch) < batch_size:
                break
            offset += batch_size
            
        print(f"\n   Fetched {len(all_data)} records.")
        
        if not all_data:
            print("⚠️ No data found in DB.")
            return

        df = pd.DataFrame(all_data)
        df = df.sort_values('date')
        
        # Ensure impact_score exists
        if 'impact_score' not in df.columns:
            print("⚠️ 'impact_score' column missing in DB data. Recalculating locally...")
            # Recalculate if missing (fallback)
            # impact = z_day_local * ln(1 + count)
            # Assuming columns exist
            if 'z_day_local' in df.columns and 'count' in df.columns:
                import numpy as np
                df['impact_score'] = df['z_day_local'] * np.log(1 + df['count'])
            else:
                df['impact_score'] = 0.0
        
        df.to_csv(output_path, index=False)
        print(f"✅ Saved to {output_path}")
        
        # Show sample
        print(df[['date', 'z_score', 'impact_score']].tail())
        
    except Exception as e:
        print(f"❌ Error fetching Z-Scores: {e}")

if __name__ == "__main__":
    fetch_zscores_to_csv()
