import os
import pandas as pd
import numpy as np

class MacroProcessor:
    def __init__(self, csv_path=None):
        if csv_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            csv_path = os.path.join(base_dir, "data", "macro_indicators.csv")
        
        self.csv_path = csv_path
        self.df = None
        self.load_data()

    def load_data(self):
        if not os.path.exists(self.csv_path):
            print(f"⚠️ Macro Data not found at {self.csv_path}")
            return

        try:
            df = pd.read_csv(self.csv_path)
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').set_index('date')
            
            # Precompute Metrics
            indicators = ['us10y', 'dxy', 'usdkrw', 'wti', 'vix', 'cpi']
            
            for col in indicators:
                if col not in df.columns:
                    continue
                    
                # 1. Trend (1 week change)
                df[f'{col}_change_1w'] = df[col].pct_change(periods=5)
                
                # 2. Level (vs 1 Year MA)
                df[f'{col}_ma_1y'] = df[col].rolling(window=252, min_periods=1).mean()
                
                # 3. Volatility (20 day Std Dev)
                df[f'{col}_vol'] = df[col].rolling(window=20, min_periods=1).std()
                df[f'{col}_vol_ma'] = df[f'{col}_vol'].rolling(window=252, min_periods=1).mean()
                
            self.df = df
            print(f"✅ Loaded Macro Data ({len(df)} rows)")
            
        except Exception as e:
            print(f"❌ Error loading Macro Data: {e}")

    def get_state(self, date_str):
        """
        Returns the Macro State for a given date.
        """
        if self.df is None:
            return None
            
        try:
            target_date = pd.to_datetime(date_str)
            # Find closest date (asof)
            idx = self.df.index.get_indexer([target_date], method='pad')[0]
            if idx == -1:
                return None
                
            row = self.df.iloc[idx]
            
            state = {}
            indicators = ['us10y', 'dxy', 'usdkrw', 'wti', 'vix', 'cpi']
            
            for col in indicators:
                if col not in self.df.columns:
                    continue
                
                val = row[col]
                change = row.get(f'{col}_change_1w', 0)
                ma = row.get(f'{col}_ma_1y', val)
                vol = row.get(f'{col}_vol', 0)
                vol_ma = row.get(f'{col}_vol_ma', 1) # Avoid div by zero
                
                # Determine Level
                if val > ma * 1.05:
                    level = "High"
                elif val < ma * 0.95:
                    level = "Low"
                else:
                    level = "Neutral"
                    
                # Determine Volatility State
                if vol > vol_ma * 1.5:
                    vol_state = "High"
                elif vol < vol_ma * 0.5:
                    vol_state = "Low"
                else:
                    vol_state = "Normal"
                
                state[col.upper()] = {
                    "value": round(val, 2),
                    "change_1w": f"{change*100:+.1f}%",
                    "level": level,
                    "volatility": vol_state
                }
                
            return state
            
        except Exception as e:
            print(f"⚠️ Error getting macro state for {date_str}: {e}")
            return None

# Singleton
_processor = None

def get_macro_processor():
    global _processor
    if _processor is None:
        _processor = MacroProcessor()
    return _processor

if __name__ == "__main__":
    mp = MacroProcessor()
    print(mp.get_state("2018-01-05"))
