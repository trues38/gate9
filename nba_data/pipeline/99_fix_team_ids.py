
import json
import os

# Standard ESPN API Mappings
NAME_TO_ESPN_ID = {
    "Atlanta Hawks": 1, 
    "Boston Celtics": 2, 
    "New Orleans Pelicans": 3, 
    "Chicago Bulls": 4, 
    "Cleveland Cavaliers": 5,
    "Dallas Mavericks": 6, 
    "Denver Nuggets": 7, 
    "Detroit Pistons": 8, 
    "Golden State Warriors": 9, 
    "Houston Rockets": 10,
    "Indiana Pacers": 11, 
    "LA Clippers": 12, 
    "Los Angeles Lakers": 13, 
    "Miami Heat": 14, 
    "Milwaukee Bucks": 15,
    "Minnesota Timberwolves": 16, 
    "Brooklyn Nets": 17, 
    "New York Knicks": 18, 
    "Orlando Magic": 19, 
    "Philadelphia 76ers": 20,
    "Phoenix Suns": 21, 
    "Portland Trail Blazers": 22, 
    "Sacramento Kings": 23, 
    "San Antonio Spurs": 24, 
    "Oklahoma City Thunder": 25,
    "Utah Jazz": 26, 
    "Washington Wizards": 27, 
    "Toronto Raptors": 28, 
    "Memphis Grizzlies": 29, 
    "Charlotte Hornets": 30
}

path = "nba_data/regimes/team_regimes.json"

with open(path, "r") as f:
    data = json.load(f)
    
updated_count = 0
for team in data:
    name = team['team_name']
    if name in NAME_TO_ESPN_ID:
        old_id = team['team_id']
        new_id = NAME_TO_ESPN_ID[name]
        
        if old_id != new_id:
            print(f"🔄 Updating {name}: ID {old_id} -> {new_id}")
            team['team_id'] = new_id
            updated_count += 1
            
print(f"\n✅ Total Updated: {updated_count}")

with open(path, "w") as f:
    json.dump(data, f, indent=2)
print("💾 Processed and saved.")
