
import json
import os

# Known Mismatches from "Old 24 -> New 21" Error
# These players were at Old 24 (likely Houston) but got moved to 21 (Phoenix)
# We move them to 10 (Houston)
HOUSTON_PLAYERS = [
    "Jalen Green",
    "Dillon Brooks",
    "Alperen Sengun",
    "Fred VanVleet",
    "Jabari Smith Jr",
    "Amen Thompson",
    "Cam Whitmore"
]

# ID 10 is Houston Rockets
TARGET_ID = 10

path = "nba_data/players/top_250_active.json"

print("🔄 Loading Player Database...")
with open(path, "r") as f:
    data = json.load(f)
    
updated_count = 0
for player in data:
    name = player.get('name')
    current_id = player.get('team_id')
    
    if name in HOUSTON_PLAYERS:
        if current_id != TARGET_ID:
            print(f"✅ Fixing {name}: ID {current_id} -> {TARGET_ID} (Houston)")
            player['team_id'] = TARGET_ID
            updated_count += 1
            
print(f"\n✅ Total Manually Fixed: {updated_count}")

with open(path, "w") as f:
    json.dump(data, f, indent=2)
print("💾 Processed and saved.")
