import pandas as pd
import os
import glob
from typing import List, Tuple

class UnifiedBuilder:
    def __init__(self, data_dir: str, output_file: str):
        self.data_dir = data_dir
        self.output_file = output_file

    def load_and_label(self, pattern: str, asset_class: str) -> pd.DataFrame:
        files = glob.glob(f"{self.data_dir}/{pattern}")
        dfs = []
        for f in files:
            try:
                df = pd.read_csv(f)
                # Ensure columns exist
                if 'published' not in df.columns:
                    print(f"⚠️ Skipping {f}: Missing 'published' column")
                    continue
                    
                # Normalize Date
                df['date'] = pd.to_datetime(df['published'], errors='coerce').dt.strftime('%Y-%m-%d')
                
                # Add Asset Class
                df['asset_class'] = asset_class
                
                # Select relevant columns
                cols = ['date', 'title', 'source', 'link', 'asset_class']
                # Handle missing columns gracefully
                for c in cols:
                    if c not in df.columns:
                        df[c] = ""
                
                dfs.append(df[cols])
                print(f"✅ Loaded {len(df)} rows from {os.path.basename(f)} ({asset_class})")
            except Exception as e:
                print(f"❌ Error loading {f}: {e}")
                
        if dfs:
            return pd.concat(dfs, ignore_index=True)
        return pd.DataFrame()

    def build(self, sources: List[Tuple[str, str]]):
        """
        sources: List of (pattern, asset_class) tuples.
        """
        print(f"🚀 Starting Unified Build for {self.output_file}...")
        
        all_dfs = []
        for pattern, asset in sources:
            df = self.load_and_label(pattern, asset)
            if not df.empty:
                all_dfs.append(df)
        
        if not all_dfs:
            print("⚠️ No data found.")
            return

        # Combine All
        all_df = pd.concat(all_dfs, ignore_index=True)
        
        # Drop Invalid Dates
        all_df = all_df.dropna(subset=['date'])
        all_df = all_df[all_df['date'] != "NaT"]
        
        # Sort by Date (Descending)
        all_df = all_df.sort_values(by='date', ascending=False)
        
        # Deduplicate (Title + Date)
        before_len = len(all_df)
        all_df.drop_duplicates(subset=['title', 'date'], inplace=True)
        after_len = len(all_df)
        print(f"🧹 Deduplicated: {before_len} -> {after_len} (Removed {before_len - after_len})")
        
        # Save
        os.makedirs(os.path.dirname(self.output_file), exist_ok=True)
        all_df.to_csv(self.output_file, index=False)
        print(f"\n💾 Unified History Saved: {self.output_file}")
        print(f"📊 Total Records: {len(all_df)}")
        print(all_df['asset_class'].value_counts())

if __name__ == "__main__":
    # Example Usage (Economy)
    builder = UnifiedBuilder("regime_zero/data/multi_asset_history", "regime_zero/data/multi_asset_history/unified_history.csv")
    builder.build([
        ("btc_news*.csv", "BTC"),
        ("fed_news*.csv", "FED"),
        ("oil_news*.csv", "OIL"),
        ("gold_news*.csv", "GOLD")
    ])
