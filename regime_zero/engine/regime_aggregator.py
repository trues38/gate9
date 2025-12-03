import json
import os
import pandas as pd
from collections import defaultdict
from regime_zero.engine.config import RegimeConfig

class RegimeAggregator:
    def __init__(self, config: RegimeConfig):
        self.config = config
        self.price_dir = "regime_zero/data/market_data" # Keep this hardcoded for now or move to config if needed
        self.price_data = self._load_price_data()
        
    def _load_price_data(self):
        """Loads price history for assets."""
        price_map = {}
        for asset in self.config.assets:
            if asset == "NEWS": continue # No price for NEWS
            
            # TODO: Make price data path configurable per asset if needed
            filename = os.path.join(self.price_dir, f"{asset}_price_history.csv")
            if os.path.exists(filename):
                df = pd.read_csv(filename)
                # Create a dict: date -> {Close, Change_Pct}
                price_map[asset] = df.set_index('Date')[['Close', 'Change_Pct']].to_dict('index')
        return price_map

    def load_regimes(self):
        """Loads all regime JSONL files and organizes them by date."""
        daily_regimes = defaultdict(dict)
        
        for asset in self.config.assets:
            filename = os.path.join(self.config.output_dir, f"{asset}_regimes.jsonl")
            if not os.path.exists(filename):
                continue
                
            with open(filename, 'r') as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        date = data.get('date')
                        if date:
                            daily_regimes[date][asset] = data
                    except json.JSONDecodeError:
                        continue
                        
        return daily_regimes

    def create_master_records(self):
        """Merges daily regimes into a single master record per day (Hybrid: News + Price)."""
        output_file = os.path.join(self.config.output_dir, "master_regime_history.jsonl")
        daily_regimes = self.load_regimes()
        
        # Get all unique dates from both News and Price
        all_dates = set(daily_regimes.keys())
        for asset_prices in self.price_data.values():
            all_dates.update(asset_prices.keys())
            
        sorted_dates = sorted(list(all_dates))
        
        # Filter for reasonable range (e.g., 2015+)
        sorted_dates = [d for d in sorted_dates if d >= "2015-01-01"]
        
        print(f"🔗 Aggregating {len(sorted_dates)} days (Hybrid Mode) for {self.config.domain_name}...")
        
        with open(output_file, 'w') as f:
            for date in sorted_dates:
                day_data = daily_regimes.get(date, {})
                hybrid_record = {}
                
                for asset in self.config.assets:
                    if asset in day_data:
                        # Priority 1: News Regime
                        hybrid_record[asset] = day_data[asset]
                    elif asset in self.price_data and date in self.price_data[asset]:
                        # Priority 2: Price Regime (Fallback)
                        price_info = self.price_data[asset][date]
                        hybrid_record[asset] = self._generate_price_regime(asset, price_info, date)
                    else:
                        # No Data
                        hybrid_record[asset] = {"regime_label": "No Signal", "source": "Empty"}
                        
                # Create Master Record
                master_record = {
                    "date": date,
                    "regimes": hybrid_record,
                    "summary_text": self._generate_summary_text(date, hybrid_record)
                }
                
                f.write(json.dumps(master_record) + "\n")
                
        print(f"✅ Saved Master Regime History to {output_file}")
        return output_file

    def _generate_price_regime(self, asset, price_info, date):
        """Generates a synthetic regime based on price action."""
        change = price_info.get('Change_Pct', 0)
        close = price_info.get('Close', 0)
        
        # Simple Logic
        if abs(change) < 0.5:
            label = "Consolidation"
            narrative = f"{asset} traded flat ({change:.2f}%) with no major news."
        elif change >= 0.5:
            label = "Bullish Price Action"
            narrative = f"{asset} rose {change:.2f}% on market momentum."
        else:
            label = "Bearish Price Action"
            narrative = f"{asset} fell {change:.2f}% on market momentum."
            
        return {
            "regime_label": label,
            "narrative": narrative,
            "price_change": change,
            "close_price": close,
            "date": date,
            "asset": asset,
            "source": "Market Data"
        }

    def _generate_summary_text(self, date, day_data):
        """Generates a text representation for Vector Embedding."""
        lines = [f"[DATE] {date}"]
        
        for asset in self.config.assets:
            regime = day_data.get(asset, {})
            label = regime.get('regime_label', 'No Signal')
            source = regime.get('source', 'News')
            
            # Extract details
            details = []
            if 'triggers' in regime: details = regime['triggers'][:2]
            elif 'key_signals' in regime: details = regime['key_signals'][:2]
            elif 'supply_shocks' in regime: details = regime['supply_shocks'][:2]
            elif 'price_change' in regime: details = [f"{regime['price_change']:.2f}%"]
            
            detail_str = ", ".join(details) if details else ""
            
            if source == "Market Data":
                lines.append(f"[{asset}] {label} (Price: {detail_str})")
            else:
                lines.append(f"[{asset}] {label} ({detail_str})")
                
        return "\n".join(lines)

if __name__ == "__main__":
    from regime_zero.config.economy_config import ECONOMY_CONFIG
    aggregator = RegimeAggregator(ECONOMY_CONFIG)
    aggregator.create_master_records()
