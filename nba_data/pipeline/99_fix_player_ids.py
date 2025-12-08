
import json
import os

# MAPPING FROM OLD (Arbitrary) -> NEW (ESPN)
# Derived from previous fix logic
OLD_TO_NEW_MAP = {
    18: 16, # Min
    15: 29, # Mem
    3: 17,  # Bkn
    22: 19, # Orl
    6: 5,   # Cle
    27: 24, # SAS
    10: 9,  # GSW
    16: 14, # Mia
    13: 12, # LAC
    20: 18, # NYK
    17: 15, # Mil
    11: 10, # Hou
    23: 20, # Phi
    25: 22, # Por
    29: 26, # Uta
    24: 21, # Phx
    21: 25, # OKC
    5: 4,   # Chi
    19: 3,  # NOP
    14: 13, # LAL
    26: 23, # Sac
    12: 11, # Ind
    9: 8    # Det
}

path = "nba_data/players/top_250_active.json"

print("🔄 Loading Player Database...")
with open(path, "r") as f:
    data = json.load(f)
    
updated_count = 0
for player in data:
    old_id = player.get('team_id')
    if old_id in OLD_TO_NEW_MAP:
        new_id = OLD_TO_NEW_MAP[old_id]
        player['team_id'] = new_id
        updated_count += 1
            
print(f"\n✅ Total Updated Players: {updated_count}")
print(f"Example: Jalen Green ID changed from 24 -> {OLD_TO_NEW_MAP.get(24)} (Should be 21)")

with open(path, "w") as f:
    json.dump(data, f, indent=2)
print("💾 Processed and saved.")
