import pandas as pd
from datetime import datetime, timedelta
import os

class MacroContextLoader:
    def __init__(self, data_dir="regime_zero/data/multi_asset_history"):
        self.data_dir = data_dir
        self.unified_file = f"{data_dir}/unified_history.csv"
        self.data = {}
        self._load_data()

    def _load_data(self):
        """Loads unified history CSV into memory."""
        if os.path.exists(self.unified_file):
            try:
                print(f"🔄 Loading Unified Macro History from {self.unified_file}...")
                df = pd.read_csv(self.unified_file)
                # Ensure date is datetime
                df['date'] = pd.to_datetime(df['date'], errors='coerce')
                
                # Split by Asset Class
                for asset in ['FED', 'OIL', 'GOLD']:
                    self.data[asset] = df[df['asset_class'] == asset].copy()
                    
                print(f"✅ Loaded Macro Context: FED({len(self.data.get('FED', []))}), OIL({len(self.data.get('OIL', []))}), GOLD({len(self.data.get('GOLD', []))})")
            except Exception as e:
                print(f"⚠️ Failed to load unified history: {e}")
                self.data = {}
        else:
            print(f"⚠️ Unified History not found at {self.unified_file}. Macro Context will be empty.")
            self.data = {}

    def get_macro_context(self, target_date_str, window_days=3):
        """
        Returns a summary of macro news around the target date.
        Window: Lookback 'window_days' to capture recent context.
        """
        try:
            target_date = pd.to_datetime(target_date_str)
        except:
            return "No valid date provided for Macro Context."

        start_date = target_date - timedelta(days=window_days)
        end_date = target_date # Up to today

        context_lines = []
        
        for asset, df in self.data.items():
            if df.empty:
                continue
                
            # Filter by date range
            mask = (df['date'] >= start_date) & (df['date'] <= end_date)
            recent_news = df.loc[mask].sort_values('date', ascending=False).head(5) # Top 5 most recent
            
            if not recent_news.empty:
                context_lines.append(f"[{asset} News (Last {window_days} Days)]")
                for _, row in recent_news.iterrows():
                    date_str = row['date'].strftime("%Y-%m-%d")
                    context_lines.append(f"- ({date_str}) {row['title']}")
                context_lines.append("") # Spacer

        if not context_lines:
            return "No significant Macro News (FED/OIL/GOLD) found in the last 3 days."
            
        return "\n".join(context_lines)

if __name__ == "__main__":
    # Test
    loader = MacroContextLoader()
    # Use a date we know exists from the recent fetch (e.g., today)
    today = datetime.now().strftime("%Y-%m-%d")
    print(loader.get_macro_context(today))
