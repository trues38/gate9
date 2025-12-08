import argparse
import sys
from regime_zero.engine.regime_generator import RegimeGenerator
from regime_zero.engine.regime_aggregator import RegimeAggregator
from regime_zero.config.economy_config import ECONOMY_CONFIG
from regime_zero.config.sports_config import SPORTS_CONFIG

def get_config(domain):
    if domain == "economy":
        return ECONOMY_CONFIG
    elif domain == "sports":
        return SPORTS_CONFIG
    else:
        print(f"❌ Unknown domain: {domain}")
        sys.exit(1)

def run_pipeline(domain, target_date=None):
    config = get_config(domain)
    print(f"🚀 Starting Regime Engine for Domain: {domain.upper()}")
    
    # 1. Generate Regimes
    generator = RegimeGenerator(config)
    
    # If target_date is provided, run for that date. Otherwise, could run for a range or "today"
    # For this POC, let's default to a specific test date if not provided, or "today"
    if not target_date:
        target_date = "2025-12-02" # Default test date
        
    print(f"📅 Target Date: {target_date}")
    
    for asset in config.assets:
        # Skip NEWS for Economy if we want to treat it specially, but for now let's run it if it's in assets
        # Note: In Economy config, NEWS is an asset.
        generator.generate_regime(asset, target_date)
        
    # 2. Aggregate Regimes
    aggregator = RegimeAggregator(config)
    aggregator.create_master_records()
    
    print(f"✅ Pipeline Complete for {domain}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Regime Zero Engine CLI")
    parser.add_argument("--domain", type=str, required=True, choices=["economy", "sports"], help="Domain to run (economy or sports)")
    parser.add_argument("--date", type=str, help="Target date (YYYY-MM-DD)")
    
    args = parser.parse_args()
    
    run_pipeline(args.domain, args.date)
