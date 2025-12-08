import pandas as pd
import json
import os
from datetime import datetime, timedelta
from regime_zero.engine.config import RegimeConfig
from utils.openrouter_client import ask_llm

class RegimeGenerator:
    def __init__(self, config: RegimeConfig):
        self.config = config
        self.df = self._load_history()
        
    def _load_history(self):
        if os.path.exists(self.config.history_file):
            df = pd.read_csv(self.config.history_file)
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
            return df
        return pd.DataFrame()

    def get_news_context(self, asset, target_date, window_days=None):
        """Retrieves news for the asset around the target date."""
        if self.df.empty:
            return ""
            
        # Default windows from config or fallback
        if window_days is None:
            window_days = self.config.window_days.get(asset, 3)
            
        target_dt = pd.to_datetime(target_date)
        start_dt = target_dt - timedelta(days=window_days)
        
        # Filter by Asset and Date
        if asset == "NEWS" and self.config.domain_name == "economy":
            # NEWS Regime = Global Macro (FED + OIL + GOLD)
            # We exclude BTC to keep "Macro" distinct from "Crypto"
            # TODO: Make this logic generic via config if needed for other domains
            mask = (self.df['asset_class'].isin(["FED", "OIL", "GOLD"])) & \
                   (self.df['date'] >= start_dt) & \
                   (self.df['date'] <= target_dt)
        else:
            # Specific Asset Regime
            mask = (self.df['asset_class'] == asset) & \
                   (self.df['date'] >= start_dt) & \
                   (self.df['date'] <= target_dt)
               
        news_df = self.df.loc[mask].sort_values('date', ascending=False).head(15)
        
        if news_df.empty:
            return "No news found."
            
        context = []
        for _, row in news_df.iterrows():
            date_str = row['date'].strftime("%Y-%m-%d")
            context.append(f"- [{date_str}] {row['title']}")
            
        return "\n".join(context)

    def generate_regime(self, asset, target_date):
        """Generates a Regime Snapshot for the asset on the target date."""
        print(f"⚙️ Generating {asset} Regime for {target_date}...")
        
        news_context = self.get_news_context(asset, target_date)
        if news_context == "No news found." or not news_context:
            print(f"⚠️ No news for {asset} on {target_date}. Skipping.")
            return None
            
        prompt_template = self.config.prompts.get(asset)
        if not prompt_template:
            print(f"❌ No prompt for {asset}")
            return None
            
        prompt = prompt_template.format(date=target_date, news_context=news_context, asset=asset)
        
        try:
            # Call LLM
            # Using ask_llm from utils (Defaults to Grok/Free model)
            response = ask_llm(prompt, system_prompt="You are a specialized Regime Engine. Output ONLY valid JSON.")
            
            # Robust JSON Cleaning
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                clean_resp = json_match.group(0)
            else:
                clean_resp = response
                
            regime_data = json.loads(clean_resp)
            
            regime_data['date'] = target_date
            regime_data['asset'] = asset
            
            # Save to disk
            self._save_regime(regime_data)
            
            return regime_data
        except Exception as e:
            print(f"❌ Error generating regime: {e}")
            print(f"DEBUG RESP: {response}")
            return None

    def _save_regime(self, regime_data):
        """Saves regime data to a JSONL file."""
        os.makedirs(self.config.output_dir, exist_ok=True)
        filename = f"{self.config.output_dir}/{regime_data['asset']}_regimes.jsonl"
        
        with open(filename, 'a') as f:
            f.write(json.dumps(regime_data) + "\n")
        print(f"💾 Saved {regime_data['asset']} regime to {filename}")

if __name__ == "__main__":
    # Test Run with Economy Config
    from regime_zero.config.economy_config import ECONOMY_CONFIG
    generator = RegimeGenerator(ECONOMY_CONFIG)
    
    # Test Date: 2025-12-02
    test_date = "2025-12-02"
    
    for asset in ECONOMY_CONFIG.assets:
        if asset == "NEWS": continue # Skip NEWS for simple test
        regime = generator.generate_regime(asset, test_date)
        if regime:
            print(f"\n[{asset} REGIME]")
            print(json.dumps(regime, indent=2))
