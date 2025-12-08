import os
import sys
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

load_dotenv()
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

OUTPUT_DIR = "regime_zero/data/multi_asset_history"

def sync_supabase_to_csv():
    print(f"🔄 Syncing Supabase 'ingest_news' to local CSVs in {OUTPUT_DIR}...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Fetch all refined news
    # Note: In production, we might want to filter by date or fetch incrementally.
    # For now, we fetch all refined news to rebuild the history.
    try:
        response = supabase.table("ingest_news").select("*").eq("is_refined", True).execute()
        data = response.data
        
        if not data:
            print("⚠️ No refined news found in Supabase.")
            return

        df = pd.DataFrame(data)
        
        # Map categories to Asset Classes for Unified Builder
        # FED, OIL, GOLD, BTC
        # We need to map 'category' or 'title' content to these assets.
        # Or we can just dump everything into a 'MACRO' file and let Unified Builder handle it?
        # Unified Builder expects specific files: btc_news*.csv, fed_news*.csv, etc.
        
        # Let's split by simple keyword logic or category if available
        
        assets = {
            "FED": df[df['title'].str.contains("Fed|Rate|Powell|FOMC|Inflation", case=False, na=False)],
            "OIL": df[df['title'].str.contains("Oil|Crude|OPEC|Energy", case=False, na=False)],
            "GOLD": df[df['title'].str.contains("Gold|XAU|Precious Metal", case=False, na=False)],
            "BTC": df[df['title'].str.contains("Bitcoin|BTC|Crypto", case=False, na=False)]
        }
        
        # Also save a generic MACRO file for everything else?
        # For now, let's just update the specific asset files.
        
        for asset, asset_df in assets.items():
            if asset_df.empty:
                continue
                
            # Rename columns to match UnifiedBuilder expectation
            # UnifiedBuilder expects: published, title, source, link
            asset_df = asset_df.rename(columns={
                "published_at": "published",
                "url": "link"
            })
            
            filename = f"{OUTPUT_DIR}/{asset.lower()}_news_supabase.csv"
            asset_df.to_csv(filename, index=False)
            print(f"✅ Saved {len(asset_df)} rows to {filename}")
            
    except Exception as e:
        print(f"❌ Error syncing Supabase: {e}")

if __name__ == "__main__":
    sync_supabase_to_csv()
