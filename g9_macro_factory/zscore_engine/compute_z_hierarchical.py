import os
import sys
import pandas as pd
import numpy as np
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from g9_macro_factory.config import get_supabase_client, TABLE_NEWS

# Load environment variables
load_dotenv(override=True)

def compute_z_hierarchical():
    supabase = get_supabase_client()
    print("📊 Fetching Daily News Counts...")
    
    # Fetch all dates using standard client (bypassing broken RPC)
    # We use pagination to fetch all rows if needed, but for now let's try fetching a large batch.
    # Supabase default limit is usually 1000. We need to loop.
    
    all_dates = []
    last_count = 0
    batch_size = 10000
    offset = 0
    
    # Actually, fetching 1M rows is too slow.
    # Let's try to fetch just the 'published_at' column with a high limit.
    # If we hit the limit, we might need a better strategy (e.g. cursor).
    # For this task, let's assume < 100,000 rows for the test dataset.
    
    try:
        # Client-side fetch with robust pagination
        all_dates = []
        batch_size = 1000 # Safe limit for Supabase
        offset = 0
        
        print(f"   🚀 Fetching data in batches of {batch_size}...")
        
        while True:
            # print(f"   Fetching batch starting at {offset}...", end='\r')
            # Use count='exact' only on first batch if needed, but let's skip for speed
            res = supabase.table("global_news_all").select("published_at").range(offset, offset + batch_size - 1).execute()
            batch = res.data
            
            if not batch:
                break
            
            dates = [item['published_at'].split('T')[0] for item in batch if item.get('published_at')]
            all_dates.extend(dates)
            
            # If we got less than requested, we might be at the end, 
            # BUT Supabase might return less than batch_size even if more exist (soft limit).
            # However, usually range() works.
            # Let's just increment offset.
            # Optimization: If len(batch) < batch_size, we are likely done.
            if len(batch) < batch_size:
                break
                
            offset += batch_size
            
            # Safety break for testing (remove for production)
            # if len(all_dates) > 100000: 
            #     print("\n   ⚠️ Limit reached (100k). Stopping.")
            #     break
                
        print(f"\n   Fetched {len(all_dates)} total records.")
        
        # Aggregate
        from collections import Counter
        counts = Counter(all_dates)
        data = [{"date": k, "count": v} for k, v in counts.items()]
        
    except Exception as e:
        print(f"❌ Error fetching dates: {e}")
        return

    if not data:
        print("⚠️ No data found.")
        return

    if not data:
        print("⚠️ No data found.")
        return

    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'])
    df['count'] = df['count'].astype(int)
    df = df.sort_values('date')
    
    print(f"   Loaded {len(df)} daily records.")
    
    # Feature Engineering
    df['year'] = df['date'].dt.year
    df['month'] = df['date'].dt.to_period('M')
    
    # 1. Year Stats (Baseline for Month)
    year_stats = df.groupby('year')['count'].agg(['mean', 'std']).rename(columns={'mean': 'year_avg', 'std': 'year_std'})
    df = df.merge(year_stats, on='year', how='left')
    
    # 2. Month Stats (Baseline for Day)
    month_stats = df.groupby('month')['count'].agg(['mean', 'std']).rename(columns={'mean': 'month_avg', 'std': 'month_std'})
    df = df.merge(month_stats, on='month', how='left')
    
    # 3. Calculate Z-Scores
    # Z_Year: How busy is this month compared to the year's average?
    # (Month_Avg - Year_Avg) / Year_Std
    df['z_year'] = (df['month_avg'] - df['year_avg']) / df['year_std'].replace(0, 1)
    
    # Z_Day_Local: How busy is today compared to this month's average?
    # (Day_Count - Month_Avg) / Month_Std
    df['z_day_local'] = (df['count'] - df['month_avg']) / df['month_std'].replace(0, 1)
    
    # 4. Hybrid Impact Score
    # Impact = Z-Score * ln(1 + Volume)
    # This boosts high-volume days even if Z-score is moderate, and suppresses low-volume noise.
    df['impact_score'] = df['z_day_local'] * np.log(1 + df['count'])
    
    # Handle NaNs
    df = df.fillna(0)
    
    # Prepare for Upsert
    records = []
    for _, row in df.iterrows():
        records.append({
            "date": row['date'].strftime('%Y-%m-%d'),
            "count": int(row['count']),
            "z_score": float(row['z_day_local']), # Default to local for backward compatibility
            "z_year": float(row['z_year']),
            "z_day_local": float(row['z_day_local']),
            "impact_score": float(row['impact_score'])
        })
        
    print(f"💾 Upserting {len(records)} records to zscore_daily...")
    
    # Batch Upsert
    batch_size = 1000
    upsert_success = False
    for i in range(0, len(records), batch_size):
        batch = records[i:i+batch_size]
        try:
            supabase.table("zscore_daily").upsert(batch).execute()
            print(f"   Upserted batch {i//batch_size + 1}...", end='\r')
            upsert_success = True
        except Exception as e:
            print(f"   ❌ Batch Error: {e}")
            
    if not upsert_success:
        print("\n⚠️ DB Upsert failed. Saving to local CSV.")
        df.to_csv("zscore_daily.csv", index=False)
        print("✅ Saved to zscore_daily.csv")
    else:
        print("\n✅ Hierarchical Z-Scores Computed and Saved to DB.")

if __name__ == "__main__":
    compute_z_hierarchical()
