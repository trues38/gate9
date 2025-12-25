
import json
import pandas as pd

FILE = "/Users/js/g9/nba_data/regimes/historical_odds_regimes.json"

with open(FILE, 'r') as f:
    data = json.load(f)
    
df = pd.DataFrame(data)

print(f"Total Games Loaded: {len(df)}")
print("\nTier Assessment:")

tiers = ["Tier 1 (Trap)", "Tier 2 (Caution)", "Tier 3 (Danger)", "Tier 4 (Miracle)"]

for tier in tiers:
    subset = df[df['tier'] == tier]
    count = len(subset)
    upsets = len(subset[subset['is_upset'] == True])
    rate = (upsets / count * 100) if count > 0 else 0
    
    print(f"\n[{tier}]")
    print(f" - Count: {count}")
    print(f" - Upsets: {upsets}")
    print(f" - Upset Rate: {rate:.1f}%")
