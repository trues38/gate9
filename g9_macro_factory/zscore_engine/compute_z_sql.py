import os
import sys
import pandas as pd
import numpy as np
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from g9_macro_factory.config import get_supabase_client

def compute_z_sql():
    supabase = get_supabase_client()
    print("📊 Computing Daily Counts via SQL...")
    
    all_data = []
    years = range(2000, 2025)
    
    print(f"   🚀 Aggregating by year (2000-2024)...")
    
    for year in years:
        # print(f"   Processing {year}...", end='\r')
        sql = f"""
        SELECT 
            (published_at AT TIME ZONE 'UTC')::date as date, 
            count(*) as count 
        FROM global_news_all 
        WHERE published_at >= '{year}-01-01' AND published_at < '{year+1}-01-01'
        GROUP BY (published_at AT TIME ZONE 'UTC')::date 
        ORDER BY date
        """
        
        try:
            res = supabase.rpc("run_sql", {"query": sql}).execute()
            if res.data:
                # print(f"   {year}: Fetched {len(res.data)} rows. Sample: {res.data[0]}")
                all_data.extend(res.data)
            # else:
                # print(f"   {year}: No data.")
        except Exception as e:
            print(f"   ❌ Error for {year}: {e}")
            
    data = all_data
    
    if not data:
        print("⚠️ No data returned from SQL.")
        return

    print(f"\n   Fetched {len(data)} daily aggregated records.")
    if data:
        print(f"   First record keys: {data[0].keys()}")
        if 'error' in data[0]:
            print(f"   ❌ SQL ERROR: {data[0]['error']}")
            return
    
    try:
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        df['count'] = df['count'].astype(int)
        df = df.sort_values('date')
        
        # ==========================================
        # 📐 G9 Signal Detection Formulas (v1.0)
        # ==========================================
        
        # 1. Daily Z-Score (Rolling 30 Days)
        # Z_day = (Today - Avg_30d) / Std_30d
        # We use shift(1) to exclude today from the baseline (strictly past data), 
        # OR include today? Spec says "Last 30 Days". Usually implies past window.
        # But for anomaly detection of *today*, we compare *today* against the *past*.
        # So rolling window should be closed='left' or shift(1).
        # Let's use shift(1) to avoid look-ahead bias even in Z-score (comparing to previous 30 days).
        
        # Rolling mean/std of previous 30 days
        rolling_30 = df['count'].rolling(window=30, min_periods=10).agg(['mean', 'std']).shift(1)
        df['day_avg_30'] = rolling_30['mean']
        df['day_std_30'] = rolling_30['std']
        
        df['z_day_local'] = (df['count'] - df['day_avg_30']) / df['day_std_30'].replace(0, 1)
        
        # 2. Monthly Z-Score (Rolling 12 Months)
        # First aggregate to monthly
        df['month_period'] = df['date'].dt.to_period('M')
        monthly_df = df.groupby('month_period')['count'].sum().reset_index()
        monthly_df = monthly_df.sort_values('month_period')
        
        # Rolling 12 months (shift 1 to compare this month vs previous 12 months)
        rolling_12m = monthly_df['count'].rolling(window=12, min_periods=3).agg(['mean', 'std']).shift(1)
        monthly_df['month_avg_12'] = rolling_12m['mean']
        monthly_df['month_std_12'] = rolling_12m['std']
        
        monthly_df['z_month'] = (monthly_df['count'] - monthly_df['month_avg_12']) / monthly_df['month_std_12'].replace(0, 1)
        
        # Merge monthly z-score back to daily
        df = df.merge(monthly_df[['month_period', 'z_month']], on='month_period', how='left')
        
        # 3. Yearly Relative Z-Score (Month vs That Year)
        # Z_year_rel = (Month - Avg_Year) / Std_Year
        # This requires full year data (Look-ahead allowed for historical analysis, but for live trading?)
        # Spec says "50년 역사 중 언제가 가장 뜨거웠나?". This is a historical relative metric.
        # We calculate it based on the *entire* year's stats.
        df['year'] = df['date'].dt.year
        year_stats = monthly_df.copy()
        year_stats['year'] = year_stats['month_period'].dt.year
        year_stats = year_stats.groupby('year')['count'].agg(['mean', 'std']).rename(columns={'mean': 'year_avg', 'std': 'year_std'})
        
        # Merge year stats to monthly_df to calc z_year_rel
        monthly_df['year'] = monthly_df['month_period'].dt.year
        monthly_df = monthly_df.merge(year_stats, on='year', how='left')
        monthly_df['z_year_rel'] = (monthly_df['count'] - monthly_df['year_avg']) / monthly_df['year_std'].replace(0, 1)
        
        # Merge z_year_rel back to daily
        df = df.merge(monthly_df[['month_period', 'z_year_rel']], on='month_period', how='left')
        
        # 4. Hybrid Impact Score
        # Score = Z_score(Daily) * ln(1 + Volume)
        df['impact_score'] = df['z_day_local'] * np.log1p(df['count'])
        
        # Cleanup
        df = df.fillna(0)
        
        # Prepare for Upsert
        records = []
        for _, row in df.iterrows():
            records.append({
                "date": row['date'].strftime('%Y-%m-%d'),
                "count": int(row['count']),
                "z_score": float(row['z_day_local']), # Daily Z-Score
                "z_year": float(row['z_year_rel']),   # Yearly Relative
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
        else:
            print("\n✅ Rolling Z-Scores Computed and Saved.")
            # Also save CSV for local usage
            df.to_csv("zscore_daily.csv", index=False)
            print("✅ Also saved to zscore_daily.csv for local cache.")

    except Exception as e:
        print(f"❌ Error processing data: {e}")

if __name__ == "__main__":
    compute_z_sql()
