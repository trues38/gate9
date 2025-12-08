import json
import os
import re

class TickerStandardizer:
    def __init__(self, map_path=None):
        if map_path is None:
            # Default to project path
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            map_path = os.path.join(base_dir, "ticker_global", "master_ticker_map.json")
        
        self.map_path = map_path
        self.ticker_map = {}
        self.load_map()

    def load_map(self):
        if not os.path.exists(self.map_path):
            print(f"⚠️ Ticker Map not found at {self.map_path}")
            return
        
        try:
            with open(self.map_path, 'r', encoding='utf-8') as f:
                self.ticker_map = json.load(f)
            print(f"✅ Loaded Ticker Map ({len(self.ticker_map)} entries)")
        except Exception as e:
            print(f"❌ Error loading Ticker Map: {e}")

    def standardize(self, input_ticker):
        """
        Converts input (e.g. "US:AMZN", "AMZN", "Amazon") to "EXCHANGE:TICKER" (e.g. "NASDAQ:AMZN").
        Returns None if not found.
        """
        if not input_ticker:
            return None
            
        input_ticker = input_ticker.strip().upper()
        
        # 1. Direct Lookup in Keys (e.g. "US:AMZN")
        if input_ticker in self.ticker_map:
            entry = self.ticker_map[input_ticker]
            return f"{entry['exchange']}:{entry['ticker'].split(':')[-1]}"
            
        # 2. Lookup by Ticker Suffix (e.g. "AMZN")
        # This is ambiguous if multiple exchanges have same ticker.
        # We prioritize US > JP > Others.
        candidates = []
        for key, entry in self.ticker_map.items():
            if key.split(':')[-1] == input_ticker:
                candidates.append(entry)
        
        if candidates:
            # Sort/Filter candidates
            # Priority: NASDAQ, NYSE, AMEX, JPX...
            priority = {"NASDAQ": 1, "NYSE": 2, "AMEX": 3, "JPX": 4}
            candidates.sort(key=lambda x: priority.get(x['exchange'], 99))
            best = candidates[0]
            # Return Yahoo Ticker format
            # For US, it's just the ticker. For others, it might need suffix.
            # But our map keys are like "US:SPY", "KR:005930".
            # If we want to match price_daily, we should use what we fetched.
            # In fetch_price_data.py, we used keys: SPY, QQQ, KOSPI (^KS11), 005930.KS
            
            # Let's try to map back to these known keys if possible.
            # Or just return the ticker part for US.
            
            ticker_part = best['ticker'].split(':')[-1]
            exchange = best['exchange']
            
            if exchange in ["NYSE", "NASDAQ", "AMEX"]:
                return ticker_part
            elif exchange == "KRX":
                return f"{ticker_part}.KS" # Yahoo format for Korea
            else:
                return f"{exchange}:{ticker_part}" # Default fallback
            
        # 3. Lookup by Name/Alias (Fuzzy) - Optional, maybe overkill for now
        # Let's stick to Ticker-based standardization first.
        
        return None

# Singleton instance
_standardizer = None

def get_standardizer():
    global _standardizer
    if _standardizer is None:
        _standardizer = TickerStandardizer()
    return _standardizer

if __name__ == "__main__":
    ts = TickerStandardizer()
    print(f"US:AMZN -> {ts.standardize('US:AMZN')}")
    print(f"AMZN -> {ts.standardize('AMZN')}")
    print(f"JP:7203 -> {ts.standardize('JP:7203')}")
    print(f"7203 -> {ts.standardize('7203')}")
